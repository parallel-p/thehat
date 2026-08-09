#!/usr/bin/env python3
"""Driver for the LLM vetting run over the Wiktionary candidates.

The run is chunked and resumable: candidates.ru.jsonl (+ diminutives) is
split deterministically into fixed chunks; each chunk's verdicts land in
words/wiktionary/vetting/verdicts-NNN.json, and a chunk is done when its
file exists and validates. Orchestration (spawning the vetting agents) is
external; this script only renders prompts, validates results, and reports.

Usage:
    python3 tools/vet_words.py status
    python3 tools/vet_words.py render NNN OUTFILE   # prompt for chunk NNN
    python3 tools/vet_words.py validate             # check all verdict files
    python3 tools/vet_words.py merge OUTFILE        # merged verdicts jsonl
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
WIKT = os.path.join(ROOT, "words", "wiktionary")
VET = os.path.join(WIKT, "vetting")
CHUNK = 250
VALID_KEEP = {"keep"}
VALID_WHY = {"UNK", "DER", "NON", "OFF", "SLG", "PRP", "BAD"}


def load_words():
    # Diminutives are deliberately excluded from the run (Nikolay, 2026-08-08).
    words = []
    with open(os.path.join(WIKT, "candidates.ru.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            words.append({
                "w": r["word"],
                "gloss": [g[:120] for g in r.get("glosses", [])[:2]],
                "labels": r.get("labels", []),
            })
    return words


def chunks():
    words = load_words()
    return [words[i:i + CHUNK] for i in range(0, len(words), CHUNK)]


def verdict_path(i):
    return os.path.join(VET, f"verdicts-{i:03d}.json")


def validate_chunk(i, chunk):
    path = verdict_path(i)
    if not os.path.exists(path):
        return "missing"
    try:
        verdicts = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError:
        return "unparseable"
    if {v["w"] for v in verdicts} != {c["w"] for c in chunk}:
        return "word mismatch"
    for v in verdicts:
        if v["v"] == "keep":
            if v.get("d") not in (1, 2, 3, 4, 5):
                return f"bad difficulty on {v['w']}"
        elif v["v"] == "drop":
            if v.get("why") not in VALID_WHY:
                return f"bad reason on {v['w']}"
        elif v["v"] != "unsure":
            return f"bad verdict on {v['w']}"
    return "ok"


def main():
    cmd = sys.argv[1]
    cs = chunks()
    if cmd == "render":
        i = int(sys.argv[2])
        tpl = open(os.path.join(WIKT, "vetting-prompt.md"), encoding="utf-8").read()
        body = tpl.split("---\n", 1)[1]
        lines = "\n".join(json.dumps(c, ensure_ascii=False) for c in cs[i])
        open(sys.argv[3], "w", encoding="utf-8").write(
            body.replace("{{WORDS_JSONL}}", lines + "\n"))
        print(f"chunk {i}: {len(cs[i])} words -> {sys.argv[3]}")
    elif cmd == "status":
        states = [validate_chunk(i, c) for i, c in enumerate(cs)]
        done = sum(1 for s in states if s == "ok")
        print(f"{done}/{len(cs)} chunks done "
              f"({sum(len(c) for c in cs)} words total, {CHUNK}/chunk)")
        pending = [i for i, s in enumerate(states) if s != "ok"]
        if pending:
            print("pending:", ",".join(map(str, pending[:40])),
                  "..." if len(pending) > 40 else "")
    elif cmd == "validate":
        bad = {i: s for i, c in enumerate(cs)
               if (s := validate_chunk(i, c)) not in ("ok", "missing")}
        print(json.dumps(bad) if bad else "all present files valid")
    elif cmd == "merge":
        with open(sys.argv[2], "w", encoding="utf-8") as out:
            for i, c in enumerate(cs):
                if validate_chunk(i, c) != "ok":
                    continue
                for v in json.load(open(verdict_path(i), encoding="utf-8")):
                    out.write(json.dumps(v, ensure_ascii=False) + "\n")
        print("merged")


if __name__ == "__main__":
    main()
