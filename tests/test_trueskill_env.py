# -*- coding: utf-8 -*-
"""The PyPI trueskill + partial_update subclass must match the vendored fork.

``tests/reference_trueskill/`` is the trueskill 0.4.1 tree the python27 app
vendored (including the 2014 ``partial_update`` patch, commit 07c69e8), ported
to python3 by nothing more than ``izip``/``imap``/``xrange`` substitutions. It
exists only as a test oracle -- production uses PyPI trueskill 0.4.5 plus
:class:`app.trueskill_env.PartialUpdateTrueSkill`.
"""

import random

import pytest

from app.trueskill_env import TRUESKILL_ENVIRONMENT
from tests import reference_trueskill

TOLERANCE = 1e-9

REFERENCE = reference_trueskill.TrueSkill(
    mu=50.0, sigma=50.0 / 3, beta=50.0 / 6, tau=50.0 / 300, draw_probability=0,
)


@pytest.mark.parametrize("coef", [None, 0.3, 0.6, 0.8, 1.0])
def test_matches_the_vendored_fork(coef):
    rng = random.Random(7)
    worst = 0.0
    for _ in range(120):
        size = rng.randint(2, 6)
        values = [(rng.uniform(5, 95), rng.uniform(1, 20)) for _ in range(size)]

        expected = REFERENCE.rate(
            [{i: REFERENCE.create_rating(mu, sigma)}
             for i, (mu, sigma) in enumerate(values)], partial_update=coef)
        actual = TRUESKILL_ENVIRONMENT.rate(
            [{i: TRUESKILL_ENVIRONMENT.create_rating(mu, sigma)}
             for i, (mu, sigma) in enumerate(values)], partial_update=coef)

        for want, got in zip(expected, actual):
            want_rating = next(iter(want.values()))
            got_rating = next(iter(got.values()))
            worst = max(worst, abs(want_rating.mu - got_rating.mu),
                        abs(want_rating.sigma - got_rating.sigma))
    assert worst < TOLERANCE, "largest divergence {}".format(worst)


def test_partial_update_damps_towards_the_prior():
    """A small coefficient must move ratings less than a full update."""
    groups = [{"a": TRUESKILL_ENVIRONMENT.create_rating(50.0, 50.0 / 3)},
              {"b": TRUESKILL_ENVIRONMENT.create_rating(40.0, 5.0)}]

    full = TRUESKILL_ENVIRONMENT.rate(groups)[0]["a"].mu
    damped = TRUESKILL_ENVIRONMENT.rate(groups, partial_update=0.3)[0]["a"].mu
    unchanged = TRUESKILL_ENVIRONMENT.rate(groups, partial_update=1.0)[0]["a"].mu

    assert 50.0 < damped < full
    assert abs(unchanged - full) < TOLERANCE


@pytest.mark.parametrize("coef", [-0.1, 1.5, 2])
def test_rejects_out_of_range_coefficients(coef):
    groups = [{"a": TRUESKILL_ENVIRONMENT.create_rating(50.0, 5.0)},
              {"b": TRUESKILL_ENVIRONMENT.create_rating(40.0, 5.0)}]
    with pytest.raises(ValueError):
        TRUESKILL_ENVIRONMENT.rate(groups, partial_update=coef)
    with pytest.raises(ValueError):
        REFERENCE.rate(groups, partial_update=coef)


def test_zero_means_no_partial_update_not_an_error():
    """The vendored patch guarded on truthiness, so 0 is silently ignored."""
    groups = [{"a": TRUESKILL_ENVIRONMENT.create_rating(50.0, 5.0)},
              {"b": TRUESKILL_ENVIRONMENT.create_rating(40.0, 5.0)}]
    assert (TRUESKILL_ENVIRONMENT.rate(groups, partial_update=0)[0]["a"].mu ==
            TRUESKILL_ENVIRONMENT.rate(groups)[0]["a"].mu)
