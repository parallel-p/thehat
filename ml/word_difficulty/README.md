# Word difficulty model

A BERT-based regressor that predicts a word's difficulty rating **E** from the
word itself, so new words can get a sensible rating before anyone has played
them. Published at
[huggingface.co/nzinov/thehat-word-difficulty](https://huggingface.co/nzinov/thehat-word-difficulty).

## What it learns from

Two production Datastore tables, both read-only dumps (August 2026):

- `GlobalDictionaryWord` — all 13,799 words, each with its played-in rating E
  (Elo-style, updated after every game by the stats pipeline; mean 52.8,
  sd 5.8, range ~30–68). Median word has 78 plays behind its rating.
- `WordFrequency` — corpus frequency in uses per million, 14,842 entries,
  covering 95% of the dictionary. Log-frequency alone correlates −0.49
  with E, and it is exactly the signal spelling can't provide.

## Architecture and training

`DeepPavlov/rubert-base-cased` → mean pooling → concat `[z-scored log
frequency, has-frequency flag]` → MLP head (770 → 128 → 1), MSE on z-scored E.
AdamW (encoder 3e-5, head 1e-3), batch 32, max 8 epochs with early stopping on
validation MAE — the encoder overfits after epoch ~3 on 11k samples. Split
80/10/10 by word with a fixed seed. ~10 minutes per run on an M-series Mac
(MPS).

## Performance (held-out test, n = 1,379)

| Metric | model | predict-the-mean |
|---|---|---|
| MAE | 3.31 | 4.76 |
| Pearson r | 0.68 | — |
| "which of two words is harder" | 74% | 50% |
| … when the pair differs by > 4 E points | 83% | 50% |

A 3-seed ensemble adds ~1 point of pairwise accuracy (84%); the published
checkpoint is the best single seed. Error analysis: the model nails the
morphology axis (short concrete nouns easy, long abstract derivations hard)
and the frequency axis; what remains is difficulty rooted in in-game
explainability and world knowledge (кадык, тюлька, молотилка), which no
word-level feature sees.

## Using it

```python
from huggingface_hub import snapshot_download
import sys

path = snapshot_download("nzinov/thehat-word-difficulty")
sys.path.insert(0, path)
from modeling import WordDifficultyPredictor

predictor = WordDifficultyPredictor.from_dir(path)
predictor.predict(["кровать", "синоним", "соразмерность"])
# [44.2, 57.6, 59.5]
```

Needs `torch`, `transformers`, `numpy`. The frequency table ships inside the
HF repo; words missing from it fall back to a learned no-frequency path, so
the predictor accepts any Russian word.

## Reproducing

From the repo root, with production access (`gcloud` ADC) and a venv that has
`google-cloud-ndb`:

```bash
python ml/word_difficulty/dump_dictionary.py   # -> prod_dictionary.jsonl
python ml/word_difficulty/dump_frequency.py    # -> prod_frequency.jsonl
```

Then, in a venv with `torch transformers numpy scipy`:

```bash
TRAIN_SEED=3 python ml/word_difficulty/train.py
```

`train.py` prints test metrics at the end and writes the checkpoint next to
the data files. Set `TRAIN_SEED` to 1/2/3 and average the saved test
predictions to reproduce the ensemble numbers.
