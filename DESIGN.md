# Design language — paper & ink

One stylesheet, `assets/hat.css`, covers every page the site serves: the landing
page, the two beta pages, the two privacy policies, and the two statistics pages.
Before this there were four unrelated looks (Bootstrap 3.0.0 from a CDN, a bare
`<style>` block, an unstyled policy page, and the stats templates).

## The idea

The game is slips of paper in a hat, so the site is paper and ink: a warm page,
near-black text, hairline rules, and a single accent borrowed from a hat band.

**Serif for anything that speaks, sans for anything that measures.** Prose,
headings and the words themselves are Georgia; labels, tables, statistics and
chart furniture are the system sans with tabular figures. That split is the whole
system — it is what keeps a marketing page and a statistics table looking like
the same site without either one pretending to be the other.

## Constraints it was built under

- **No external requests.** No CDN, no webfont, no JavaScript. The old pages
  pulled Bootstrap and jQuery from third-party hosts over `http://` in one case;
  the app itself takes no external dependencies, and now neither does the site.
- **Cyrillic first.** Georgia has strong Cyrillic coverage and is near-universal;
  Android falls through to Noto Serif, which is close in colour. Russian words
  are long, so `overflow-wrap: break-word` is set globally — a single word must
  never push the page wider than the viewport.
- **Both schemes are designed, not flipped.** The night palette re-picks the
  accent for the dark surface rather than inverting the light one.

## Tokens

Everything is a custom property on `:root`; the dark block re-declares the same
names. Nothing in the components hard-codes a colour.

| role | light | night |
|---|---|---|
| page | `#FBF7EF` | `#17140F` |
| raised / sunk | `#FFFDF8` / `#F4EEE2` | `#1F1B15` / `#120F0B` |
| ink | `#1C1917` (16.4:1) | `#EFE7D9` (15.0:1) |
| muted ink | `#6E655B` (5.4:1) | `#A79C8C` (6.8:1) |
| rule | `#E2D9C8` | `#332C22` |
| accent (hat band) | `#A02C2C` (6.8:1) | `#E0837A` (6.7:1) |
| chart mark | `#A02C2C` | `#CC6058` |

Every text pair above clears WCAG AA for body text; the contrast numbers are the
measured ratios against that mode's page colour, not estimates.

Type is a fluid scale (`--t-display` … `--t-micro`), spacing is a 4px scale
(`--s1` … `--s9`), prose is capped at `--measure` (34rem, ~70 characters) and the
page at `--page` (68rem).

## Recurring motifs

- **The numbered eyebrow** — `01 — ЧТО ТАКОЕ ШЛЯПА` with a hairline running to
  the right margin. It is the site's main structural device.
- **Hairlines, not boxes.** Sections separate with a 1px rule and alternating
  `--paper` / `--paper-sunk`; the only bordered surface is `.slip`, where the
  paper metaphor is literal.
- **Crisp corners.** `--radius` is 3px. Paper is cut, not moulded.

## Charts

The statistics pages carry data, so the chart rules are followed rather than
improvised. All of these charts are **single-series magnitude**, which decides
almost everything:

- **One hue, no legend.** A legend with a single swatch would just restate the
  caption. Identity comes from the caption; magnitude comes from length.
- **Marks are capped at 24px** and never fill their slot — the leftover band is
  air. Adjacent marks are separated by a **2px gap in the surface colour**, never
  by a stroke.
- **Data ends are rounded (3px), baselines are square.**
- **Values are direct-labelled at the tip**, so the charts need no axis ticks;
  hour labels appear every third column because all 24 would collide.
- **Tabular figures in columns only.** Standalone numbers — the hero figure, stat
  tile values — use proportional figures, because `tabular-nums` makes a large
  number like `121` look loose.
- **Text never wears the data colour.** Labels and values are ink or muted ink;
  the coloured mark beside them carries the meaning.
- Charts built from more than a few marks ship a `<details>` **table view**, and
  the column charts carry `role="img"` with a describing label.

The ordinal ramp (`--ramp-1` … `--ramp-4`) exists for a future ordered scale. It
was validated as a ramp — monotone lightness, ≥0.06 ΔL per step, light end 2.53:1
on paper, 7° hue spread — but nothing uses it yet.

There are deliberately **no pie charts, no dual axes, and no images**: the
matplotlib-rendered PNGs the old site served are gone and are not coming back.

## Components

`masthead` · `footer` · `hero` · `section` (+ `--sunk`) · `split` (+ `--flip`) ·
`slip` · `eyebrow` · `btn` (`--primary`, `--ghost`) · `prose` · `table` ·
`tiles`/`tile` · `hero-figure` · `bars`/`bar` · `columns`/`column` · `search` ·
`empty`.

## Working on it

The statistics pages are server-rendered Jinja2 (`templates/`); the rest are
static files served by `app.yaml` handlers. `/` and `/landing` must stay
byte-identical — `/` serves the file rather than rendering it, and a test asserts
this.

To see changes locally, `make serve` mounts `/assets`, `/tos` and the single-file
static handlers so local URLs match production (App Engine serves those
off-instance, so without the mount every local page renders unstyled).

Note when screenshotting: headless Chrome on macOS clamps the window width, so
`--window-size=390` crops a wider layout instead of rendering a narrow one. Load
the page in a 390px `<iframe>` to get a true phone viewport.
