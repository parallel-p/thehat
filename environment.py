__author__ = 'nikolay'

import trueskill

TRUESKILL_ENVIRONMENT = trueskill.TrueSkill(
    mu=50.0,
    sigma=50.0 / 3,
    beta=50.0 / 6,
    tau=50.0 / 300,
    draw_probability=0,
)