# -*- coding: utf-8 -*-
"""Generate synthetic game logs that stress the python2/python3 differences.

Real production payloads are the primary fixture (scripts/export_prod_logs.py),
but they do not reliably hit the cases that break a naive port, so these are
generated on purpose:

* explanation times ending in 500 ms, where ``round()`` differs between the two
  python versions;
* many words sharing the same total explanation time, so that rating groups are
  full of ties and the dict iteration order decides the ranking;
* word counts either side of CPython 2.7's dict resize thresholds (6, 22, 86
  entries), where the slot layout -- and therefore the iteration order -- changes.

    python scripts/make_test_logs.py --out tests/fixtures/synthetic_logs.jsonl \\
        --words-out tests/fixtures/word_ratings.json
"""

import argparse
import json
import random

WORDS = [
    "кот", "дом", "мост", "лес", "река", "гора", "стол", "окно", "книга", "перо",
    "поезд", "море", "снег", "ветер", "камень", "дерево", "птица", "рыба", "хлеб",
    "молоко", "сахар", "чай", "кофе", "город", "село", "дорога", "мышь", "слон",
    "тигр", "волк", "лиса", "заяц", "медведь", "олень", "лошадь", "корова", "овца",
    "коза", "свинья", "курица", "утка", "гусь", "индюк", "голубь", "воробей",
    "ворона", "сорока", "дятел", "сова", "орёл", "сокол", "чайка", "пингвин",
    "кит", "дельфин", "акула", "осьминог", "краб", "рак", "улитка", "паук",
    "муравей", "пчела", "оса", "муха", "комар", "бабочка", "жук", "кузнечик",
    "стрекоза", "червь", "ёж", "крот", "белка", "бобр", "барсук", "куница",
    "выдра", "норка", "хорёк", "ласка", "рысь", "пума", "ягуар", "леопард",
    "гепард", "лев", "зебра", "жираф", "бегемот", "носорог", "буйвол", "антилопа",
    "газель", "верблюд", "лама", "альпака", "як", "бизон", "зубр",
]

# Times chosen so that ms/1000.0 lands on .5 (python2 rounds up, python3 to even)
# as well as ordinary values.
HALF_TIMES = [1500, 2500, 3500, 4500, 5500, 6500, 7500, 8500, 10500, 12500]
PLAIN_TIMES = [1200, 2000, 3300, 4800, 6100, 7700, 9000, 11000, 15000, 23000]


def pick_time(rng):
    pool = HALF_TIMES if rng.random() < 0.5 else PLAIN_TIMES
    return rng.choice(pool)


def make_v2_log(rng, game_id, word_count, player_count):
    players = ["p{}".format(i) for i in range(player_count)]
    words = WORDS[:word_count]
    start = 1700000000000 + rng.randint(0, 10 ** 7)
    attempts = []
    for index, word in enumerate(words):
        explainer = players[index % player_count]
        guesser = players[(index + 1) % player_count]
        outcome = "guessed"
        roll = rng.random()
        if roll < 0.12:
            outcome = "failed"
        elif roll < 0.18:
            outcome = "not_explained"
        attempts.append({
            "word": word,
            "from": explainer,
            "to": guesser,
            "time": pick_time(rng),
            "extra_time": rng.choice([0, 0, 0, 500, 1000]),
            "outcome": outcome,
        })
    # A few words explained twice, which exercises the seen_by_player branches.
    for _ in range(max(1, word_count // 10)):
        source = rng.choice(attempts)
        attempts.append(dict(source, **{
            "from": rng.choice(players),
            "to": rng.choice(players),
            "time": pick_time(rng),
        }))
    rng.shuffle(attempts)
    return {
        "version": "2.0",
        "start_timestamp": start,
        "end_timestamp": start + rng.randint(600, 3600) * 1000,
        "time_zone_offset": rng.choice([0, 3 * 3600 * 1000, 4 * 3600 * 1000]),
        "attempts": attempts,
        "id": game_id,
    }


def make_v1_log(rng, game_id, word_count, player_count):
    players = ["p{}".format(i) for i in range(player_count)]
    words = WORDS[:word_count]
    start = 1500000000000 + rng.randint(0, 10 ** 7)
    events = [{"type": "start_game", "time": start}]

    remaining = list(range(word_count))
    rng.shuffle(remaining)
    round_index = 0
    clock = start
    while remaining:
        explainer = players[round_index % player_count]
        guesser = players[(round_index + 1) % player_count]
        events.append({"type": "round_start", "from": explainer, "to": guesser,
                       "time": clock})
        for _ in range(min(len(remaining), rng.randint(1, 5))):
            word_index = remaining.pop()
            outcome = "guessed" if rng.random() > 0.2 else "failed"
            events.append({
                "type": "stripe_outcome",
                "word": word_index,
                "outcome": outcome,
                "time": pick_time(rng),
                "timeExtra": rng.choice([0, 0, 500]),
            })
            if rng.random() < 0.08:
                events.append({"type": "outcome_override", "word": word_index,
                               "outcome": "guessed"})
        events.append({"type": "finish_round", "time": clock})
        clock += rng.randint(60, 180) * 1000
        round_index += 1
    events.append({"type": "end_game", "time": clock})

    return {
        "setup": {
            "type": "hat",
            "meta": {"game.id": game_id, "time.offset": "14400000"},
            "words": [{"word": w} for w in words],
            "players": players,
        },
        "events": events,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--words-out", required=True)
    parser.add_argument("--seed", type=int, default=20260801)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    logs = []
    # Word counts straddle CPython 2.7's dict resize thresholds.
    for word_count in [4, 5, 6, 7, 12, 21, 22, 23, 40, 60, 84, 85, 86, 87, 100]:
        for player_count in [2, 3, 5]:
            game_id = "v2-{}-{}".format(word_count, player_count)
            logs.append((game_id, make_v2_log(rng, game_id, word_count, player_count)))
            game_id = "v1-{}-{}".format(word_count, player_count)
            logs.append((game_id, make_v1_log(rng, game_id, word_count, player_count)))

    with open(args.out, "w", encoding="utf-8") as handle:
        for game_id, payload in logs:
            handle.write(json.dumps(
                {"id": game_id, "json": json.dumps(payload, ensure_ascii=False)},
                ensure_ascii=False) + "\n")

    # A rating table covering most, but deliberately not all, of the words: an
    # unknown word must stay unrated (`ratings[i] is None`).
    ratings = {}
    for index, word in enumerate(WORDS):
        if index % 11 == 5:
            continue  # not in the global dictionary
        ratings[word] = {
            "E": round(rng.uniform(20.0, 80.0), 6),
            "D": round(rng.uniform(2.0, 16.0), 6),
            "lang": "ru",
        }
    with open(args.words_out, "w", encoding="utf-8") as handle:
        json.dump(ratings, handle, ensure_ascii=False, indent=1, sort_keys=True)

    print("wrote {} logs and {} words".format(len(logs), len(ratings)))


if __name__ == "__main__":
    main()
