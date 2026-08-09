# -*- coding: utf-8 -*-
"""Predict difficulty E for a word list with the published model.

    python ml/word_difficulty/predict.py --file words.txt --out predictions.jsonl

Reads one word per line (`-` for stdin), writes jsonl rows {"word", "E"}.
Uses the checkpoint from huggingface.co/nzinov/thehat-word-difficulty; needs
torch, transformers, numpy, huggingface_hub.
"""

import argparse
import json
import sys

from huggingface_hub import snapshot_download


def read_words(path):
    stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
    try:
        seen = [w for w in (line.strip() for line in stream)
                if w and not w.startswith("#")]
    finally:
        if stream is not sys.stdin:
            stream.close()
    return list(dict.fromkeys(seen))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="one word per line, or -")
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", type=int, default=256)
    args = parser.parse_args()

    words = read_words(args.file)
    path = snapshot_download("nzinov/thehat-word-difficulty")
    sys.path.insert(0, path)
    from modeling import WordDifficultyPredictor

    predictor = WordDifficultyPredictor.from_dir(path)
    with open(args.out, "w", encoding="utf-8") as out:
        for start in range(0, len(words), args.batch):
            chunk = words[start:start + args.batch]
            for w, e in zip(chunk, predictor.predict(chunk)):
                out.write(json.dumps({"word": w, "E": round(float(e), 2)},
                                     ensure_ascii=False) + "\n")
            print(f"{min(start + args.batch, len(words))}/{len(words)}",
                  file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
