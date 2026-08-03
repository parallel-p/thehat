"""TrueSkill environment used for word ratings.

The python27 app carried a vendored copy of trueskill 0.4.1 patched with a
``partial_update`` argument to :meth:`TrueSkill.rate` (commit 07c69e8, 2014).
Upstream never took that patch, so the PyPI package alone is not a drop-in
replacement: three of the four ``rate()`` calls in the statistics pipeline pass
``coef``.

Rather than keep a forked copy of the library, the patch is reapplied here as a
subclass. Everything else in trueskill 0.4.5 is numerically identical to the
vendored 0.4.1 (the only other differences are py3 syntax, docstrings, and an
algebraically equivalent refactor of ``LikelihoodFactor.calc_a``).
"""

import trueskill
from trueskill import Gaussian, Rating
from trueskill import _team_sizes


class PartialUpdateTrueSkill(trueskill.TrueSkill):
    """``TrueSkill`` with the legacy ``partial_update`` extension."""

    def rate(self, rating_groups, ranks=None, weights=None,
             min_delta=trueskill.DELTA, partial_update=None):
        """Same as :meth:`trueskill.TrueSkill.rate`.

        ``partial_update`` in (0, 1] damps the update: each rating moves only
        that fraction of the way (in natural parameters) towards the value the
        unmodified algorithm would produce.
        """
        # The vendored patch guarded both the validation and the damping with a
        # plain truth test, so 0 (and None) mean "no partial update" rather than
        # "invalid". Kept identical.
        if not partial_update:
            return super().rate(rating_groups, ranks=ranks, weights=weights,
                                min_delta=min_delta)
        if not 0. < partial_update <= 1.:
            raise ValueError('Wrong partial_update value')

        rating_groups, keys = self.validate_rating_groups(rating_groups)
        weights = self.validate_weights(weights, rating_groups, keys)
        group_size = len(rating_groups)
        if ranks is None:
            ranks = range(group_size)
        elif len(ranks) != group_size:
            raise ValueError('Wrong ranks')
        # sort rating groups by rank
        sorting = sorted(enumerate(zip(rating_groups, ranks, weights)),
                         key=lambda x: x[1][1])
        sorted_rating_groups, sorted_ranks, sorted_weights = [], [], []
        for x, (g, r, w) in sorting:
            sorted_rating_groups.append(g)
            sorted_ranks.append(r)
            # make weights to be greater than 0
            sorted_weights.append(max(min_delta, w_) for w_ in w)
        # build factor graph
        args = (sorted_rating_groups, sorted_ranks, sorted_weights)
        builders = self.factor_graph_builders(*args)
        layers = self.run_schedule(*(builders + (min_delta,)))
        # make result
        rating_layer, team_sizes = layers[0], _team_sizes(sorted_rating_groups)
        # --- the vendored patch ---
        for f in rating_layer:
            old_val = Gaussian(f.val.mu, f.val.sigma)
            f.var.pi = old_val.pi + partial_update * (f.var.pi - old_val.pi)
            f.var.tau = old_val.tau + partial_update * (f.var.tau - old_val.tau)
        # --- end patch ---
        transformed_groups = []
        for start, end in zip([0] + team_sizes[:-1], team_sizes):
            group = []
            for f in rating_layer[start:end]:
                group.append(Rating(float(f.var.mu), float(f.var.sigma)))
            transformed_groups.append(tuple(group))
        unsorting = sorted(zip((x for x, __ in sorting), transformed_groups),
                           key=lambda x: x[0])
        if keys is None:
            return [g for x, g in unsorting]
        # restore the structure with input dictionary keys
        return [dict(zip(keys[x], g)) for x, g in unsorting]


# Parameters copied verbatim from the old environment.py.
TRUESKILL_ENVIRONMENT = PartialUpdateTrueSkill(
    mu=50.0,
    sigma=50.0 / 3,
    beta=50.0 / 6,
    tau=50.0 / 300,
    draw_probability=0,
)
