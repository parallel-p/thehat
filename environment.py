__author__ = 'nikolay'

import os

import jinja2
import trueskill

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape']
)

TRUESKILL_ENVIRONMENT = trueskill.TrueSkill(
    mu=50.0,
    sigma=50.0 / 3,
    beta=50.0 / 6,
    tau=50.0 / 300,
    draw_probability=0,
)