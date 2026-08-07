# -*- coding: utf-8 -*-
"""«Что сложнее?» -- the daily word duel at /duel.

Ten pairs of words a day, drawn from the words real games have played enough
for the rating to mean something. You pick the one you think is harder to
explain; the answer is what the dictionary has measured, not an opinion.

Three properties make it the kind of thing people come back to:

* **One puzzle a day, the same for everyone.** The day is the entity id, so
  there is no way to hold two puzzles for one date, and what a reader shares
  is what their friends will get. A day is a day in `DUEL_TZ`, not UTC --
  the audience is Russian-speaking and a puzzle that turns over at three in
  the morning turns over in the middle of the evening's game.
* **No word is asked twice.** Every past puzzle is the record of which words
  have been spent, and generation draws only from the rest. The dictionary is
  finite, so when the unspent pool runs thin the oldest puzzles are forgiven
  first (see `_fresh_words`) -- which is a slow recycle, not a repeat.
* **The answer is defensible.** A pair is only used when the two words are far
  enough apart *and* measured well enough that the harder one is harder with
  at least `_CONFIDENCE` probability. Both halves matter: see `_separated`.
* **It gets harder as it goes, along two axes at once.** The ten pairs are
  drawn one per band of `_GAP_BANDS`, widest gap first, and from the sixth on
  the two words must also be about equally common -- so the gap closes towards
  the floor and the one cue a reader has that is not the rating is taken away
  at the same time. The score is then a statement about where you stopped
  seeing it rather than ten flips of the same coin, and the shared grid says
  so at a glance.

The expensive part -- reading the dictionary -- is not done here. It is the
`duel_pool` value in `app.web`, refreshed by the same daily cron as everything
else, so generating a day's puzzle is one cached read and a few hundred
microseconds of sampling.
"""

import datetime
import hashlib
import json
import logging
import math
import os
import random

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from google.cloud import ndb

from app.models import WordDuel
from app.web import cached

logger = logging.getLogger(__name__)

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# Moscow. The game is played in Russian and mostly in this timezone, and a
# daily puzzle has to turn over while its readers are asleep. Fixed rather
# than a named zone: it has had no DST since 2014 and a fixed offset cannot
# be wrong about a rule that does not exist.
DUEL_TZ = datetime.timezone(datetime.timedelta(hours=3))

# Puzzle #1. The number is what a share names, so this date is now permanent.
EPOCH = datetime.date(2026, 8, 3)

# How sure we are that the word we call harder is harder. E and D are a word's
# TrueSkill mu and sigma, so the difference of two words' true difficulties is
# itself normal with variance Da^2 + Db^2, and this is the mass of it that has
# to be on one side of zero. This is the promise the page makes, and it is a
# floor rather than a target: on the live dictionary D has converged to ~1.23
# for every played word, so the gap bands below are what actually select, and
# every pair that ships is far past 90%. The test still earns its keep -- it
# is what rejects a word that has only just entered the dictionary and whose
# sigma has not come down yet.
_CONFIDENCE = 0.9

# The narrowest gap that may ever be asked about, whatever the sigmas say.
# This is the floor, not a preference: at the live spread it is 90.7% certain,
# and one tenth of a point lower the page would be promising something it
# cannot deliver. Measured, not guessed -- see the confidence table in
# `_phi`'s terms: 3.4 -> 97.5%, 3.0 -> 95.8%, 2.3 -> 90.7%, 2.0 -> 87.5%.
_MIN_GAP = 2.3

# How close in corpus frequency two words must be before "which of these do I
# hear more often?" stops being worth anything. A factor rather than a
# difference, because frequency runs over four orders of magnitude.
#
# This is the second axis of the ramp, and on live data it matters more than
# the first. Left alone, the rarer word is the harder one 61% of the time at a
# four-point gap and 90% at a twenty-point one, so a reader who knows nothing
# about the ratings can play well by asking which word sounds more obscure.
# Held inside this factor, that drops to ~51% -- a coin flip, and the rating
# is the only thing left to go on. Measured over the live dictionary; about a
# quarter of the pairs in every band qualify, so there is no shortage.
_NEAR_RATIO = 1.6

# The ramp: one band per question, as (narrowest gap, widest gap, frequency
# must be uninformative). Hardest last.
#
# This is the shape of the game. A flat run of ten comparable pairs is ten
# coin-flips of the same weight, and the score out of it says only how lucky
# you were; ordered, the run of ten reads as how far you got before the
# difference stopped being visible, and the shared grid says the same thing at
# a glance.
#
# It ramps along both axes at once. The first half hands over gaps a reader
# can feel and lets the frequency cue help; the second half takes the cue away
# and closes the gap towards the floor, so the last question is two words that
# are equally common and three tenths of a point apart -- which is to say, two
# words nobody can separate without having measured them.
_GAP_BANDS = [
    (6.6, 7.6, False),
    (5.8, 6.6, False),
    (5.1, 5.8, False),
    (4.5, 5.1, False),
    (4.0, 4.5, False),
    (3.6, 4.0, True),
    (3.2, 3.6, True),
    (2.9, 3.2, True),
    (2.6, 2.9, True),
    (_MIN_GAP, 2.6, True),
]

PAIRS_PER_DAY = len(_GAP_BANDS)

# Leave this many unspent words in the pool. Ten pairs need twenty words, but
# they need to be twenty words that pair up, so the reserve is ten days' worth
# rather than one -- the recycle starts gently and long before it has to.
_RESERVE = 200

# Rejection sampling, per band. The narrowest band catches about one draw in
# twenty on live data, so a few dozen attempts is the usual cost and this cap
# is only here so that a pool which cannot fill a band gives up in
# milliseconds rather than spinning.
_DRAWS_PER_BAND = 600

# How many times a band that cannot be filled is allowed to open up before the
# day is declared impossible. A band widens rather than failing outright
# because the alternative is no puzzle at all: a ramp with one rung slightly
# out of place is still a ramp, and `_MIN_GAP` and the confidence test hold
# throughout regardless of how far a band has opened.
_WIDENINGS = 4


class NotEnoughWords(Exception):
    """The pool cannot make a full puzzle. The page says so; nothing is stored.

    Storing a short puzzle would be storing it for good -- the entity is
    written once by design -- so a day the dictionary cannot fill is better
    left empty and retried.
    """


# --------------------------------------------------------------------------
# The bar a pair has to clear
# --------------------------------------------------------------------------


def _phi(z):
    """The standard normal CDF, out of the standard library."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _z_for(probability):
    """The z at which `_phi` reaches `probability`. Bisection, once, at import.

    Written out rather than pasted in as 1.2816 so that `_CONFIDENCE` above is
    the number a reader has to agree with, and changing it needs no second
    edit somewhere else.
    """
    low, high = 0.0, 10.0
    for _ in range(60):
        middle = (low + high) / 2.0
        if _phi(middle) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


_Z = _z_for(_CONFIDENCE)


def _separated(first, second):
    """True when one of these two words is reliably harder than the other.

    `first` and `second` are (word, E, D). Both tests have to pass: the gap
    has to be big enough to be worth asking about, and big enough relative to
    how well the two ratings are known to be more than noise.
    """
    gap = abs(first[1] - second[1])
    if gap < _MIN_GAP:
        return False
    spread = math.sqrt(first[2] ** 2 + second[2] ** 2)
    if spread <= 0:
        return True
    return gap / spread >= _Z


# --------------------------------------------------------------------------
# Which day it is
# --------------------------------------------------------------------------


def today():
    """The date the puzzle on offer right now belongs to."""
    return datetime.datetime.now(DUEL_TZ).date()


def day_number(date):
    """The number a share names: 1 on `EPOCH`, and up from there."""
    return (date - EPOCH).days + 1


# --------------------------------------------------------------------------
# Generating a day
# --------------------------------------------------------------------------


def _pool():
    """[(word, E, D, frequency), ...] -- every word the duel may draw on.

    Padded to width, because the stored blob outlives the deploy that wrote
    it: `web.cached` will serve a value up to two days old, so the first
    generation after a column is added here reads rows written by the version
    before it. A short row means the frequency is not known, which is exactly
    what `None` says and what `_similarly_common` already refuses to call
    neutral -- so the day comes out easier and comes out, rather than failing
    on an index error until the next refresh.
    """
    return [tuple(row) + (None,) * (4 - len(row))
            for row in cached("duel_pool")]


def _past_puzzles():
    """Every puzzle written so far, oldest first."""
    return WordDuel.query().order(WordDuel.day).fetch()


def _fresh_words(pool, past):
    """The words that have not been asked yet -- topped up if too few remain.

    The dictionary is finite and the puzzle spends twenty words a day, so
    "never repeat" cannot hold for ever. What holds instead: a word only comes
    back once the pool has been worked through, and the puzzle it appeared in
    is the oldest one still remembered. Days are forgiven whole and oldest
    first, one at a time, and only until there is room again -- so on a real
    dictionary this is a slow rotation, and a word a reader saw yesterday
    cannot turn up today.

    Where a whole pool is smaller than the reserve -- an empty staging
    project, a dictionary nobody has played yet -- every day gets forgiven and
    words do repeat. There is no way around that one: twenty words a day out
    of sixty is repetition however it is arranged, and refusing to draw would
    mean no puzzle at all.
    """
    spent_on = {}
    for puzzle in past:
        for pair in puzzle.pairs or []:
            spent_on[pair[0]] = puzzle.day
            spent_on[pair[1]] = puzzle.day

    fresh = [row for row in pool if row[0] not in spent_on]
    if len(fresh) >= _RESERVE or not spent_on:
        return fresh

    # Forgive whole puzzles, oldest first, until there is room to play again.
    logger.info("duel: only %d unspent words of %d; recycling the oldest",
                len(fresh), len(pool))
    forgiven = set()
    for day in sorted(set(spent_on.values())):
        forgiven.add(day)
        fresh = [row for row in pool
                 if row[0] not in spent_on or spent_on[row[0]] in forgiven]
        if len(fresh) >= _RESERVE:
            break
    return fresh


def _seed(date):
    """A per-day seed, so that regenerating a lost day gives it back.

    The pool moves as games are played, so this is not a promise that the same
    date always yields the same puzzle -- the stored entity is what makes that
    true. It does mean the choice is a function of the day rather than of when
    during the day the first reader happened to arrive.
    """
    digest = hashlib.sha256(date.isoformat().encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _similarly_common(first, second, ratio):
    """True when these two words are heard about equally often.

    False when either has no corpus frequency at all: a cue cannot be shown
    to be worthless without the number that would show it.
    """
    one, other = first[3], second[3]
    if not one or not other:
        return False
    return max(one, other) / min(one, other) <= ratio


def _sample_band(fresh, taken, rng, low, high, neutral):
    """Rejection-sample a pair, opening the band up if nothing is found.

    Draw two words at random and keep the draw if it lands in the band. That
    is uniform over the pairs that qualify, which picking one word and then a
    partner for it is not -- doing it that way would over-represent words with
    few possible partners, which is to say the words at either extreme, which
    is to say the easiest questions.

    A band that cannot be filled opens up and is tried again -- the gap
    stretches and the frequency test loosens together, because a question
    that has to give ground should give it on both axes rather than becoming
    a wide-open gap that is still perfectly neutral, or the reverse. What
    never gives ground is `_MIN_GAP` and the confidence test: a band may
    move, the promise about the answer may not.
    """
    ratio = _NEAR_RATIO
    for _ in range(_WIDENINGS):
        for _draw in range(_DRAWS_PER_BAND):
            first, second = rng.sample(fresh, 2)
            if first[0] in taken or second[0] in taken:
                continue
            if not low <= abs(first[1] - second[1]) < high:
                continue
            if neutral and not _similarly_common(first, second, ratio):
                continue
            if not _separated(first, second):
                continue
            return first, second
        low = max(_MIN_GAP, low * 0.85)
        high = high * 1.15
        ratio *= 1.5
    return None


def _draw_in_band(fresh, taken, rng, band):
    """Two unused words matching `band`, or None.

    The frequency half of a band is given up rather than allowed to end the
    day. `_similarly_common` is False whenever either word has no corpus
    frequency at all, and no amount of loosening the ratio changes that -- so
    if the `WordFrequency` kind ever goes away, or a pool is thin enough that
    the neutral bands cannot be filled, every day after it would be a page
    with no puzzle on it. An easier question is worth more than no question,
    and the log line says which happened.
    """
    low, high, neutral = band
    drawn = _sample_band(fresh, taken, rng, low, high, neutral)
    if drawn is None and neutral:
        logger.info("duel: no frequency-neutral pair in %s; asking anyway",
                    (low, high))
        drawn = _sample_band(fresh, taken, rng, low, high, False)
    return drawn


def choose_pairs(pool, past, date):
    """`PAIRS_PER_DAY` pairs, as [left, right, harder, E_left, E_right].

    One pair per band of `_GAP_BANDS`, in that order -- so the day arrives as
    a ramp, obvious first and barely-there last, and the position of a pair in
    the list is the order it is asked in.
    """
    fresh = _fresh_words(pool, past)
    if len(fresh) < 2 * PAIRS_PER_DAY:
        raise NotEnoughWords(
            "{} words available, need {}".format(len(fresh), 2 * PAIRS_PER_DAY))

    rng = random.Random(_seed(date))
    pairs = []
    taken = set()
    for index, band in enumerate(_GAP_BANDS):
        drawn = _draw_in_band(fresh, taken, rng, band)
        if drawn is None:
            raise NotEnoughWords(
                "nothing in band {} ({}) of {} words".format(
                    index + 1, band, len(fresh)))
        first, second = drawn
        harder, easier = ((first, second) if first[1] > second[1]
                          else (second, first))
        # Which side the harder word shows on, so the answer is not a habit.
        # The ratings travel with the pair: see the note on WordDuel.pairs.
        if rng.random() < 0.5:
            pairs.append([harder[0], easier[0], 0,
                          round(harder[1], 1), round(easier[1], 1)])
        else:
            pairs.append([easier[0], harder[0], 1,
                          round(easier[1], 1), round(harder[1], 1)])
        taken.add(first[0])
        taken.add(second[0])
    return pairs


@ndb.transactional()
def _claim(date, pairs):
    """Store this puzzle for `date`, unless someone got there first.

    Two readers arriving in the same second on a day nobody has opened yet
    would otherwise write two different puzzles, and the second would silently
    replace the first -- including for whoever had already started playing it.
    The loser of the race throws its work away and plays the winner's puzzle.
    """
    key = ndb.Key(WordDuel, date.isoformat())
    existing = key.get()
    if existing is not None:
        return existing
    puzzle = WordDuel(key=key, day=day_number(date), pairs=pairs,
                      created=datetime.datetime.now(datetime.timezone.utc)
                      .replace(tzinfo=None))
    puzzle.put()
    return puzzle


def puzzle_for(date):
    """The puzzle for `date`, generating and storing it if it is new."""
    existing = ndb.Key(WordDuel, date.isoformat()).get()
    if existing is not None:
        return existing
    pairs = choose_pairs(_pool(), _past_puzzles(), date)
    puzzle = _claim(date, pairs)
    logger.info("duel: day %d (%s) ready, %d pairs", puzzle.day,
                date.isoformat(), len(puzzle.pairs))
    return puzzle


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------


def payload_json(payload):
    """`payload` as JSON that is safe to drop into a <script> element.

    The content of a script element is raw text: the browser does not decode
    entities in it, so Jinja's escaping would corrupt the JSON rather than
    protect it, and `|safe` alone would let a word containing `</script` end
    the element early. Escaping the three characters that can start something
    in HTML leaves valid JSON that cannot.
    """
    return (json.dumps(payload, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


@router.get("/duel", response_class=HTMLResponse)
def duel(request: Request):
    """Today's puzzle.

    A program, not a document -- it keeps a score and shares it, which is
    script, and the site's pages carry none. It takes `hat.css` whole the way
    /play does; `duel.css` adds layout and nothing else.
    """
    date = today()
    try:
        puzzle = puzzle_for(date)
    except NotEnoughWords:
        logger.warning("duel: no puzzle for %s", date.isoformat())
        puzzle = None
    except Exception:  # noqa: BLE001 -- an empty page beats a 500, and the
        # next request tries again: nothing has been stored.
        logger.exception("duel: could not build %s", date.isoformat())
        puzzle = None

    payload = {"day": puzzle.day, "date": date.isoformat(),
               "pairs": puzzle.pairs} if puzzle else None
    response = templates.TemplateResponse(request, "duel.html", {
        "day": puzzle.day if puzzle else day_number(date),
        "payload": payload_json(payload) if payload else "null",
        "has_puzzle": puzzle is not None,
    })
    # The puzzle changes at midnight in DUEL_TZ, and a reader served a cached
    # copy after that would play yesterday's and share the wrong number.
    # Revalidate rather than no-store: a 304 is cheap and the page is small.
    response.headers["Cache-Control"] = "no-cache"
    return response
