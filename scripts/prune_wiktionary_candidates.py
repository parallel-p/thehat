#!/usr/bin/env python3
"""Prune the Wiktionary candidate list: drop junk classes and unreviewed pages.

Second stage after extract_wiktionary_candidates.py. Drops, in this order:
  1. Mechanically identifiable junk classes (see CLASS_RULES below).
  2. Words whose ru.wiktionary page has no moderator-reviewed (stable)
     revision — FlaggedRevs `flaggedpages` joined with `page` for titles.

Usage:
    curl -sLO https://dumps.wikimedia.org/ruwiktionary/latest/ruwiktionary-latest-flaggedpages.sql.gz
    curl -sLO https://dumps.wikimedia.org/ruwiktionary/latest/ruwiktionary-latest-page.sql.gz
    python3 scripts/prune_wiktionary_candidates.py words/wiktionary/candidates.ru.jsonl

Rewrites the jsonl and its .txt sibling in place.
"""
import difflib, gzip, json, re, sys

JSONL = sys.argv[1] if len(sys.argv) > 1 else "words/wiktionary/candidates.ru.jsonl"
FLAGGED = "ruwiktionary-latest-flaggedpages.sql.gz"
PAGES = "ruwiktionary-latest-page.sql.gz"

REDIRECT_RE = re.compile(r"(действие|состояние|свойство) по значению|то же, что")
SAME_AS_RE = re.compile(r"^(?:[а-я.,\s()-]{0,25})?то же, что\s+([а-яё-]+)")
FEM_RE = re.compile(r"^(?:[а-я.,\s]{0,15})?женск\. к\b")


def close_variant(word, gloss):
    m = SAME_AS_RE.match(gloss)
    if not m or m.group(1) == word:
        return False
    diffs = sum(1 for d in difflib.ndiff(word, m.group(1)) if d[0] != " ")
    return 0 < diffs <= 3


def all_redirects(r):
    return bool(r["glosses"]) and all(REDIRECT_RE.search(g) for g in r["glosses"])


def g0(r):
    return r["glosses"][0] if r["glosses"] else ""


CLASS_RULES = [
    ("пол- compound", lambda r: r["word"].startswith("пол-")),
    ("action/state noun", lambda r: all_redirects(r)
        and any("по значению" in g for g in r["glosses"])),
    ("spelling variant", lambda r: all_redirects(r)
        and close_variant(r["word"], g0(r))),
    ("feminitive", lambda r: "феминитив" in r["labels"] or FEM_RE.match(g0(r))),
    ("mineral", lambda r: g0(r).startswith("минер.")),
    ("chem nomenclature", lambda r: re.match(r"(био)?хим\.", g0(r))),
    ("biol taxon", lambda r: re.match(
        r"зоол\.|ботан\.|энтомол\.|орнитол\.|ихтиол\.|(род|вид|семейство)\s", g0(r))),
    ("demonym", lambda r: re.search(r"житель|жительница|уроженец|уроженка", g0(r))),
    ("сокр. compound", lambda r: re.match(r"сокр\.", g0(r))),
    ("sexual/euphemism", lambda r: re.search(r"эвф\.|сексол\.|порно", g0(r)[:40])),
    ("letter name", lambda r: re.search(r"буква |название буквы", g0(r))),
]


def norm(t):
    return t.replace("_", " ").lower().replace("ё", "е")


def patrolled_titles():
    """Normalized ns-0 titles that have a FlaggedRevs stable revision."""
    flagged_ids = set()
    with gzip.open(FLAGGED, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INSERT INTO"):
                flagged_ids.update(int(m) for m in re.findall(r"\((\d+),", line))
    titles = set()
    row_re = re.compile(r"\((\d+),(-?\d+),'((?:[^'\\]|\\.)*)',")
    with gzip.open(PAGES, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("INSERT INTO"):
                continue
            for pid, ns, title in row_re.findall(line):
                if ns == "0" and int(pid) in flagged_ids:
                    titles.add(norm(title))
    return titles


def main():
    recs = [json.loads(l) for l in open(JSONL, encoding="utf-8")]
    print(f"input: {len(recs)}")

    kept = []
    drops = {name: 0 for name, _ in CLASS_RULES}
    for r in recs:
        name = next((n for n, f in CLASS_RULES if f(r)), None)
        if name:
            drops[name] += 1
        else:
            kept.append(r)
    for name, n in drops.items():
        print(f"  dropped {n:6d}  {name}")
    print(f"after class drops: {len(kept)}")

    reviewed = patrolled_titles()
    print(f"patrolled ns-0 titles: {len(reviewed)}")
    kept = [r for r in kept if r["word"] in reviewed]
    print(f"after patrol filter: {len(kept)}")

    with open(JSONL, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(JSONL.replace(".jsonl", ".txt"), "w", encoding="utf-8") as f:
        for r in kept:
            f.write(r["word"] + "\n")


if __name__ == "__main__":
    main()
