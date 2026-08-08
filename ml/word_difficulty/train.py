# -*- coding: utf-8 -*-
"""Finetune a difficulty (E) regressor: rubert-base + log-frequency feature.

Reads prod_dictionary.jsonl and prod_frequency.jsonl produced by the dump
scripts next to this file. The train/val/test split is fixed by random.seed(42)
regardless of TRAIN_SEED, which varies only initialization and batch order —
so runs with different TRAIN_SEEDs are ensembleable and comparable.

    TRAIN_SEED=3 python ml/word_difficulty/train.py
"""

import json
import os
import random

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_NAME = os.environ.get("MODEL_NAME", "DeepPavlov/rubert-base-cased")
TRAIN_SEED = int(os.environ.get("TRAIN_SEED", "1"))
TAG = os.environ.get("TAG", f"v2_s{TRAIN_SEED}")
MAX_LEN = 16
BATCH = 32
EPOCHS = 8
PATIENCE = 3
LR = 3e-5
HEAD_LR = 1e-3

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


def load_freq():
    freq = {}
    for line in open(os.path.join(HERE, "prod_frequency.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        w = (r["word"] or r["key"] or "").strip().lower()
        if w and r["frequency"] is not None:
            freq[w] = r["frequency"]
    return freq


class WordDataset(Dataset):
    def __init__(self, rows, tokenizer, mean, std, freq, lf_mean, lf_std):
        self.enc = tokenizer([r["word"] for r in rows], truncation=True,
                             max_length=MAX_LEN, padding="max_length",
                             return_tensors="pt")
        self.y = torch.tensor([(r["E"] - mean) / std for r in rows],
                              dtype=torch.float32)
        feats = []
        for r in rows:
            f = freq.get(r["word"])
            has = 1.0 if f is not None else 0.0
            lf = (np.log1p(f) - lf_mean) / lf_std if f is not None else 0.0
            feats.append([lf, has])
        self.x = torch.tensor(feats, dtype=torch.float32)
        self.words = [r["word"] for r in rows]
        self.raw_e = [r["E"] for r in rows]

    def __len__(self):
        return len(self.y)

    def __getitem__(self, i):
        return (self.enc["input_ids"][i], self.enc["attention_mask"][i],
                self.x[i], self.y[i])


class BertFreqRegressor(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.bert = AutoModel.from_pretrained(MODEL_NAME)
        hidden = self.bert.config.hidden_size
        self.head = torch.nn.Sequential(
            torch.nn.Linear(hidden + 2, 128),
            torch.nn.GELU(),
            torch.nn.Dropout(0.1),
            torch.nn.Linear(128, 1),
        )

    def forward(self, ids, mask, extra):
        out = self.bert(input_ids=ids, attention_mask=mask)
        m = mask.unsqueeze(-1).float()
        pooled = (out.last_hidden_state * m).sum(1) / m.sum(1).clamp(min=1)
        return self.head(torch.cat([pooled, extra], dim=-1)).squeeze(-1)


def run_eval(model, loader):
    model.eval()
    preds, ys = [], []
    with torch.no_grad():
        for ids, mask, x, y in loader:
            p = model(ids.to(device), mask.to(device), x.to(device))
            preds.append(p.cpu())
            ys.append(y)
    return torch.cat(preds).numpy(), torch.cat(ys).numpy()


def main():
    rows = [json.loads(l) for l in open(os.path.join(HERE, "prod_dictionary.jsonl"),
                                        encoding="utf-8")]
    rows = [r for r in rows if r["word"] and not r["deleted"]]
    random.seed(42)
    random.shuffle(rows)
    n = len(rows)
    n_test, n_val = int(n * 0.1), int(n * 0.1)
    test, val, train = rows[:n_test], rows[n_test:n_test + n_val], rows[n_test + n_val:]

    random.seed(TRAIN_SEED)
    np.random.seed(TRAIN_SEED)
    torch.manual_seed(TRAIN_SEED)

    mean = float(np.mean([r["E"] for r in train]))
    std = float(np.std([r["E"] for r in train]))
    freq = load_freq()
    train_lf = [np.log1p(freq[r["word"]]) for r in train if r["word"] in freq]
    lf_mean, lf_std = float(np.mean(train_lf)), float(np.std(train_lf))
    print(f"n={n} device={device} seed={TRAIN_SEED} model={MODEL_NAME} "
          f"freq_cov={len(train_lf)/len(train):.1%}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    args = (tokenizer, mean, std, freq, lf_mean, lf_std)
    dl_train = DataLoader(WordDataset(train, *args), batch_size=BATCH, shuffle=True)
    ds_val = WordDataset(val, *args)
    ds_test = WordDataset(test, *args)
    dl_val = DataLoader(ds_val, batch_size=256)
    dl_test = DataLoader(ds_test, batch_size=256)

    model = BertFreqRegressor().to(device)
    opt = torch.optim.AdamW([
        {"params": model.bert.parameters(), "lr": LR},
        {"params": model.head.parameters(), "lr": HEAD_LR},
    ], weight_decay=0.01)
    steps = len(dl_train) * EPOCHS
    sched = get_linear_schedule_with_warmup(opt, int(steps * 0.06), steps)
    loss_fn = torch.nn.MSELoss()

    best_val, best_state, bad = float("inf"), None, 0
    for epoch in range(EPOCHS):
        model.train()
        total = 0.0
        for ids, mask, x, y in dl_train:
            opt.zero_grad()
            pred = model(ids.to(device), mask.to(device), x.to(device))
            loss = loss_fn(pred, y.to(device))
            loss.backward()
            opt.step()
            sched.step()
            total += loss.item() * len(y)
        p, y = run_eval(model, dl_val)
        val_mae = float(np.mean(np.abs(p - y))) * std
        print(f"epoch {epoch + 1}: train_mse={total / len(dl_train.dataset):.4f} "
              f"val_MAE={val_mae:.3f}", flush=True)
        if val_mae < best_val:
            best_val, bad = val_mae, 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                print("early stop")
                break

    model.load_state_dict(best_state)
    torch.save({"state_dict": best_state, "mean": mean, "std": std,
                "lf_mean": lf_mean, "lf_std": lf_std, "model_name": MODEL_NAME},
               os.path.join(HERE, f"bert_e_model_{TAG}.pt"))
    p, y = run_eval(model, dl_test)
    pred_e = p * std + mean
    np.save(os.path.join(HERE, f"test_pred_{TAG}.npy"), pred_e)
    true_e = y * std + mean

    from scipy.stats import pearsonr, spearmanr
    mae = float(np.mean(np.abs(pred_e - true_e)))
    print(f"\n=== TEST ({TAG}) ===")
    print(f"MAE {mae:.3f}  RMSE {float(np.sqrt(np.mean((pred_e-true_e)**2))):.3f}  "
          f"r {pearsonr(pred_e, true_e)[0]:.3f}  rho {spearmanr(pred_e, true_e)[0]:.3f}")


if __name__ == "__main__":
    main()
