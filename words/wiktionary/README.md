# Wiktionary candidate words

Candidate nouns for extending the game dictionary (13.8k words in production
as of 2026-08), extracted from Russian Wiktionary. This is the *mechanical*
stage only: everything here still needs an LLM vetting pass and an initial
difficulty estimate before import (see «Next stages» below).

## Files

| file | contents |
|---|---|
| `candidates.ru.txt` | 92 427 new candidate words, one per line — not present in the production dictionary |
| `candidates.ru.jsonl` | the same words with metadata per word: up to 3 glosses, compact labels (`разг`, `жарг`, `терм`, `истор`, `феминитив`, `аббр`, …), sense counts — input for the LLM pass |
| `diminutives.ru.jsonl` | 3 874 words whose only qualifying senses are derivational diminutives («лучик», «брючки») — excluded from the main list; a later pass may rescue the genuinely common ones |

## What makes a good hat word

From the game rules (`static/play/index.html`): «существительные нарицательные
в единственном числе» — common nouns, singular lemma, pluralia tantum allowed.
The game *measures* difficulty from play (TrueSkill, prior E=50), so the bar is
not «frequent» but «a native speaker can recognize and explain it».

Kept: colloquial/slang/jargon, domain terms, historical terms, neologisms,
lexicalized abbreviations, hyphenated words, lexicalized diminutives with
independent meanings («ножка»).

Dropped: proper nouns; inflected-form pages; multiword phrases; non-Cyrillic;
words whose every sense is obsolete, dialectal/regional, or Church Slavonic;
purely derivational diminutives (side list); obscene/vulgar words — obscenity
disqualifies at the word level, so a мат word cannot be rescued by a
criminal-jargon or historical sense.

Normalization: lowercase, ё→е (production convention), deduped against all
13 799 production words including the 13 soft-deleted ones.

## Source and reproduction

Source: [kaikki.org](https://kaikki.org/ruwiktionary/) weekly wiktextract dump
of Russian Wiktionary (this extraction: dump of 2026-08-04, 2.7M entries,
190.6k Russian noun entries). Register labels live in sense-level `categories`
(«Разговорные выражения/ru», «Устаревшие выражения/ru», …) and, where those
are incomplete, as dotted prefixes inside the gloss text («вульг., бран. …») —
the extractor screens both.

```bash
curl -sLo ruwikt-raw.jsonl.gz https://kaikki.org/ruwiktionary/raw-wiktextract-data.jsonl.gz
curl -so prod-dictionary.json https://the-hat.appspot.com/api/v2/dictionary/ru
python3 scripts/extract_wiktionary_candidates.py
```

Validation: the same filter run over Wiktionary recovers ~95% of the existing
human-curated production dictionary (13 064 / 13 761). The ~350 production
words *not* found in Wiktionary likely include real typos («фейрверк» is one).

## Next stages (not done here)

1. LLM vetting over `candidates.ru.jsonl`: «would a native speaker recognize
   and be able to explain this?» — residual noise is mostly narrow domain
   terms, demonyms, and derivational feminitives/deverbal nouns.
2. Same pass judges commonness for `diminutives.ru.jsonl`.
3. Auto-assign an initial difficulty (E) per word instead of the flat E=50
   prior — a mass import at E=50 floods the mid-difficulty buckets the client
   samples most (`static/play/js/dictionary.js`).
4. Staged import via `scripts/add_words.py` (it skips existing words and never
   resets accumulated ratings), then republish with `python -m app.dictionary_gen`.
