#!/usr/bin/env python3
"""Extract hat-game noun candidates from a ruwiktionary wiktextract raw dump.

A word qualifies if at least one of its noun entries has at least one
qualifying sense: a real gloss (not a form-of reference) carrying none of the
hard-disqualifying labels. Colloquial/slang/domain-term senses DO qualify —
obscurity is judged by a later LLM pass, not here.

Usage:
    curl -sLo ruwikt-raw.jsonl.gz https://kaikki.org/ruwiktionary/raw-wiktextract-data.jsonl.gz
    curl -so prod-dictionary.json https://the-hat.appspot.com/api/v2/dictionary/ru
    python3 scripts/extract_wiktionary_candidates.py [dump.jsonl.gz] [prod.json]

Outputs candidates.jsonl, candidates.txt and candidates-diminutives.jsonl in
the current directory; see words/wiktionary/README.md for the full rubric.
"""
import gzip, json, os, re, sys
from collections import defaultdict

DUMP = sys.argv[1] if len(sys.argv) > 1 else "ruwikt-raw.jsonl.gz"
PROD = sys.argv[2] if len(sys.argv) > 2 else "prod-dictionary.json"
SEED = os.path.join(os.path.dirname(__file__), "..", "words", "dictionary.ru.txt")

WORD_RE = re.compile(r"^[а-яё]+(?:-[а-яё]+)*$")
FORM_GLOSS_RE = re.compile(r"^форма\s.*\b(падежа|числа)\b")

# Derivational size/affection senses: «уменьш.-ласк. к борщ», «презр. аэропорт».
# Such a sense doesn't qualify a word on its own; words with ONLY such senses
# go to a separate diminutives list for a later commonness judgment.
DIM_MARK_RE = re.compile(r"уменьш|ласк|увелич|пренебр|уничиж|презр")
DIM_REF_RE = re.compile(r"\b(?:к|от)\s+[а-яё]")

def is_derivational_dim(gloss, cats):
    marked = (DIM_MARK_RE.search(gloss[:50]) or
              any(DIM_MARK_RE.search(c.lower()) for c in cats))
    if not marked:
        return False
    return bool(DIM_REF_RE.search(gloss[:80]) or "то же, что" in gloss
                or len(gloss.split()) <= 4)

# Obscenity attaches to the word form, not a sense: one obscene/vulgar sense
# (or gloss label) disqualifies the whole word, so a mat word can't be rescued
# by its criminal-jargon or Church Slavonic senses.
WORD_DISQ_CATS = ["Матерные", "Обсценные", "Нецензурные", "Вульгаризмы"]
WORD_DISQ_GLOSS = ["вульг.", "обсц.", "неценз.", "матерн."]

# A sense with any of these substrings in its categories does not qualify.
SENSE_DISQ = [
    "Бранные", "Грубые", "Оскорбления", "Церковнославянизмы",
    "Устаревшие выражения", "Старинные выражения",
    "Диалектизмы", "Регионализмы", "помете рег", "Проверить регион",
    "Гипокористические", "отчества", "Мужские имена", "Женские имена",
    "Фамилии", "Прозвища", "Эрративы",
]
# Inline gloss-prefix labels (dotted, to avoid matching real definition text);
# ruwiktionary renders помета templates into the gloss, and sense categories
# are sometimes incomplete, so this is the belt to the categories' braces.
GLOSS_DISQ = ["вульг.", "обсц.", "неценз.", "бран.", "груб.", "табу.",
              "устар.", "старин.", "диал.", "рег.", "эррат."]
# An entry with any of these in its entry-level categories is skipped outright.
ENTRY_DISQ = ["Мужские имена", "Женские имена", "Фамилии", "отчества",
              "Гипокористические", "Оскорбления"]

# Labels worth carrying into the output for the later LLM/difficulty stages.
LABEL_MAP = [
    ("Разговорные", "разг"), ("Просторечные", "прост"),
    ("Жаргон", "жарг"), ("жаргон", "жарг"), ("Жаргонизмы", "жарг"),
    ("Сленговые", "сленг"), ("Молодёжные", "сленг"),
    ("Уменьшительные", "уменьш"), ("Ласкательные", "ласк"),
    ("Увеличительные", "увелич"),
    ("Исторические термины", "истор"), ("Советизмы", "истор"),
    ("Неологизмы", "неол"), ("Редкие выражения", "редк"),
    ("Книжные", "книжн"), ("Поэтические", "поэт"), ("Возвышенные", "поэт"),
    ("Специальные термины", "спец"), ("Профессионализмы", "спец"),
    ("термины", "терм"),  # any "... термины/ru" domain category
    ("Аббревиатуры", "аббр"),
    ("Nomina feminina", "феминитив"),
]

def norm(w):
    return w.strip().lower().replace("ё", "е")

def existing_words():
    seen = set()
    for row in json.load(open(PROD)):
        seen.add(norm(row["word"]))
    with open(SEED, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if parts:
                seen.add(norm(parts[0]))
    return seen

def sense_labels(cats):
    labs = set()
    for c in cats:
        for sub, lab in LABEL_MAP:
            if sub in c:
                labs.add(lab)
                break
    return labs

def main():
    existing = existing_words()
    # word -> aggregated info across entries
    agg = defaultdict(lambda: {"glosses": [], "labels": set(), "obscene": False,
                               "n_senses": 0, "n_qual": 0, "pos": set(),
                               "n_dim": 0, "dim_glosses": []})
    n_lines = n_noun = 0
    with gzip.open(DUMP, "rt", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("lang_code") != "ru" or e.get("pos") not in ("noun", "abbrev"):
                continue
            word = e.get("word", "")
            if not WORD_RE.match(word):
                continue
            if len(word) < 2 or len(word) > 24:
                continue
            ecats = e.get("categories") or []
            if any(d in c for c in ecats for d in ENTRY_DISQ):
                continue
            n_noun += 1
            key = norm(word)
            info = agg[key]
            info["pos"].add(e["pos"])
            for s in e.get("senses") or []:
                cats = s.get("categories") or []
                gloss = (s.get("glosses") or [""])[0]
                if any(d in c for c in cats for d in WORD_DISQ_CATS) or \
                   any(d in gloss[:60] for d in WORD_DISQ_GLOSS):
                    info["obscene"] = True
            for s in e.get("senses") or []:
                tags = s.get("tags") or []
                glosses = s.get("glosses") or []
                if not glosses or "no-gloss" in tags:
                    continue
                info["n_senses"] += 1
                gloss = glosses[0]
                if "form-of" in tags or s.get("form_of") or FORM_GLOSS_RE.match(gloss):
                    continue
                cats = s.get("categories") or []
                info["labels"] |= sense_labels(cats)
                if any(d in c for c in cats for d in SENSE_DISQ):
                    continue
                if any(d in gloss[:60] for d in GLOSS_DISQ):
                    continue
                if is_derivational_dim(gloss, cats):
                    info["n_dim"] += 1
                    if len(info["dim_glosses"]) < 2:
                        info["dim_glosses"].append(gloss[:200])
                    continue
                info["n_qual"] += 1
                if len(info["glosses"]) < 3:
                    info["glosses"].append(gloss[:200])

    out_new, out_all, out_dim = [], [], []
    for word in sorted(agg):
        info = agg[word]
        if info["obscene"]:
            continue
        dim_only = info["n_qual"] == 0 and info["n_dim"] > 0
        if info["n_qual"] == 0 and not dim_only:
            continue
        rec = {
            "word": word,
            "glosses": info["glosses"] or info["dim_glosses"],
            "labels": sorted(info["labels"]),
            "senses": info["n_senses"],
            "qual_senses": info["n_qual"],
        }
        if "abbrev" in info["pos"]:
            rec["labels"] = sorted(set(rec["labels"]) | {"аббр"})
        if dim_only:
            if word not in existing:
                out_dim.append(rec)
            continue
        out_all.append(rec)
        if word not in existing:
            out_new.append(rec)

    with open("candidates.jsonl", "w", encoding="utf-8") as f:
        for rec in out_new:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open("candidates.txt", "w", encoding="utf-8") as f:
        for rec in out_new:
            f.write(rec["word"] + "\n")
    with open("candidates-diminutives.jsonl", "w", encoding="utf-8") as f:
        for rec in out_dim:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"dump lines: {n_lines}, accepted noun entries: {n_noun}")
    print(f"words with >=1 qualifying sense: {len(out_all)}")
    print(f"new candidates (not in prod/seed): {len(out_new)}")
    print(f"derivational-diminutive-only side list: {len(out_dim)}")
    covered = sum(1 for r in out_all if r["word"] in existing)
    print(f"existing words also found in wiktionary: {covered} / {len(existing)}")

if __name__ == "__main__":
    main()
