# Design language — «Бумажки» (Slips)

One stylesheet, `assets/hat.css`, covers every page the site serves: the landing
page, the two beta pages, the two privacy policies, the two statistics pages,
the daily duel at `/duel`, and the game at `/play`. This language replaced
"paper & ink" (warm cream, one red accent) after it was reviewed as too close
to the default warm-cream-serif look.

**Documents carry no JavaScript; a program is allowed it.** Every page that is
a page renders with markup and CSS alone, and that is not negotiable — it is
why they are fast, printable and legible with anything turned off. Two things
here are not pages: `/play` runs a stopwatch for people sitting around a table,
and `/duel` keeps a score and writes a line you can paste into a chat. Both say
so — `static/play/` and `static/duel/` are the only places in the repo with
script — and both buy back their keep by taking this stylesheet whole rather
than inventing a second look. `static/play/app.css` and `static/duel/duel.css`
add layout and nothing else: no colour, no type, no new tokens.

## The idea

Шляпа is played in the evening: a green felt table, lamplight, and coloured
paper slips — the brightest things on the table. So the site is that evening,
and **evening is the primary theme**. The day theme is the same table by
daylight: a cool porcelain score sheet with spruce ink — cool, never cream.

The core thesis: **ink speaks, slips play**. Text, buttons and data are ink;
colour appears only where the game would produce a slip of paper.

## The four rules

1. **Evening is the primary theme.** `:root` carries the evening palette;
   `@media (prefers-color-scheme: light)` carries the day. The page is a table
   in a room: the `.sheet` element is the felt (evening) or the score sheet
   (day), the body behind it is the room/mat, visible around wide viewports.
   A faint lamplight gradient (`--lamp`) sits over the hero — evening only.

   The system's preference is the default, not the last word: `data-theme` on
   `<html>` overrides it — `"day"`, `"night"`, or absent for "follow the
   system". Only `/play` writes it (a three-state switch on its home screen,
   remembered in `localStorage`); the site's pages carry no JavaScript and so
   have nothing to remember a choice with. The day palette is therefore
   written twice in `hat.css` — once behind the media query, once behind the
   attribute — because CSS cannot share one block between the two. **They
   must stay in step**, and nothing but tokens belongs in either.
2. **Slips don't go dark.** Four slips — rose `#E8A79B`, honey `#E3AC3F`,
   sky `#A9C8D6`, lilac `#BFABD6` — are physical paper: identical in both
   themes. In the evening they are the brightest spots on the felt (≥ 7.6:1);
   their dark text companions (`--*-deep`) exist only in the day theme — at
   night the pastel itself is the text accent. Fixed roles: **rose** —
   navigation and the brand mark, **lilac** — about the game, **honey** —
   words and word statistics, **sky** — time and downloads. (There is no sage
   slip: it camouflaged into the felt.)
3. **The brass band.** The old red hat band became brass `#C9A24B` — small and
   precise: link underlines, active nav, focus rings, the `.eyebrow__num`
   prefix. Never fills, never large surfaces. As running text in the day theme
   it darkens to `#7E621C`.
4. **The game is playful, the score is honest.** Everything that *speaks*
   plays: one accent word per headline is Playfair italic with a wavy brass
   underline (`.display em` etc. — one per headline, never more), eyebrows are
   lowercase Georgia italic rather than letterspaced caps, a link underline
   turns wavy under the cursor, a button tilts −1° on hover. Everything that
   *counts* stays strict: the numbers themselves — table cells, bar values,
   headline figures, axis and unit labels — keep the sans and the tabular
   figures, and never take the display serif.

   The *titles* of those things are not numbers, and they read in Georgia
   like the rest of the page: chart captions, table captions, disclosure
   summaries. A page whose every block is announced by small letterspaced
   uppercase sans stops looking like a sheet of paper and starts looking like
   a dashboard, which is the one thing this site is not.

## Tokens

All measured WCAG ratios, not estimates.

| role | evening (default) | day |
|---|---|---|
| room / mat | `#0B110E` | `#3C4A41` |
| felt / paper | `#17251D` | `#F4F5F1` |
| raised / sunk | `#1E2F25` / `#121C16` | `#FBFCF9` / `#EAEDE6` |
| ink | `#F1EBDC` (13.4:1) | `#1D2823` (13.9:1) |
| muted ink | `#9FAC9C` (6.7:1) | `#5F6B63` (5.1:1) |
| rule | `#2C3C31` | `#D8DED4` |
| brass | `#C9A24B` (6.6:1) | decoration `#C9A24B`, text `#7E621C` (5.3:1) |
| button pill | lamplight `#F1EBDC`, felt text | spruce `#1D2823`, porcelain text |

Slips and their day-theme text companions: rose `#E8A79B` / `#9C4A43` (5.5:1),
honey `#E3AC3F` / `#8A650F` (4.9:1), sky `#A9C8D6` / `#3F6675` (5.7:1),
lilac `#BFABD6` / `#6B5588` (5.9:1). Ink on any slip is `--slip-ink: #322824`
(≥ 6.8:1 everywhere). Chart marks: the pastel itself in the evening; condensed
by day (honey `#A97812` 3.6:1, sky `#567F8E` 4.0:1).

Type is a fluid scale (`--t-display` … `--t-micro`), spacing is a 4px scale
(`--s1` … `--s9`), prose is capped at `--measure` (34rem) and the page at
`--page` (68rem); the sheet itself at 86rem. Radii: buttons and search are
pills, cards are `--r-card` (10px), word slips get an irregular torn cut.

## Typography

- **Playfair Display** (self-hosted variable woff2 in `assets/fonts/`, roman +
  italic × Cyrillic + Latin = 4 files, ~95 KB, OFL) — headlines only, via
  `--display-face`. `unicode-range` keeps a page to the subsets it uses.
- **Georgia** (system) — prose, leads, eyebrows, words on slips (italic — a
  word written in a hurry; `/duel`'s pair of slips is the one exception, and
  is roman, because there the word is being read rather than jotted). Costs
  no bytes.
- **System sans** — everything that measures, with `tabular-nums` in columns
  only; standalone figures stay proportional.

## Recurring motifs

- **The slip tab** (`.eyebrow::before`) replaces the numbered eyebrow: a small
  torn slip in the section's colour. Landing sections are not a sequence, so
  `01 —` encoded nothing there. Where steps *are* a sequence (the beta install
  pages), the number stays, as a brass `.eyebrow__num` prefix.
- **Word slips** (`.ws`, `.ws-row`) — real dictionary words on torn pastel
  slips under the landing hero. Real paper: torn edges (three `--tear-*`
  `clip-path` variants cycled by `nth-child`), a fold crease and paper grain
  (`.ws::after`), and `drop-shadow` filters — never `box-shadow`, which would
  paint a rectangle around the torn contour.
- **The appliqué** (`.decor`) — soft cut-paper silhouettes of hats you could
  play from, bleeding off the hero's edges like the reference collage: a
  rose цилиндр, a sky sombrero (the server's namesake) and a lilac
  fedora-bowler in solid slip colour, plus two halftone-dot hats — a honey
  graduation cap (ЛКШ is a school) and a rose шапка with a pompom. Blobby on
  purpose: each is a handful of smooth beziers, no interior detail — drawn
  for this site (no third-party assets). The shapes are `clip-path`s fed by
  inline `<clipPath clipPathUnits="objectBoundingBox">` defs the landing
  page carries (paths scaled 1/512); sizes are viewport-clamped so the hats
  shrink before they can touch the text. The solid hats are lamplight-modelled
  (`::after` inside the clip): a radial crown gleam, a linear base shade
  angled toward the lamp (the left hat is lit from its right, the right
  cluster from its left), and the slips' paper grain. The lilac hat
  deliberately overlaps the bigger sky sombrero — the same layered pair the
  original blob composition had. Desktop only (`min-width: 60rem`), never
  under text; `--decor-o` dims it to 0.5 in the evening.
- **Prints on the table** (`.split__media--slip`) — by day, images sit on
  white paper cards; the drawings are tilted −1.5°/+1.8° in alternating
  sections. At night the card disappears (`--print-*` tokens) and the
  transparent drawings float directly on the felt. The photograph
  (`.split__media--photo`) keeps its card in both themes — it is a JPEG with
  white baked into its pixels — and it hangs square: it is a picture of a
  room with its own horizon in it, and tilting that tilts the room. A
  borrowed picture carries its credit (`.credit`) under the print: sans,
  `--t-micro`, muted throughout. A licence that asks to be attributed is not
  attributed by a `title` attribute.
- **Motion** is four hover gestures: a slip straightens and lifts, a button
  tilts −1°, a link underline goes wavy, and a duel slip — which lies square
  and so has nothing to straighten — comes up a little instead. Nothing else
  moves; `prefers-reduced-motion` kills the easing on all of it.

## The statistics pages

Everything the python27 site showed publicly is ported, most of it reborn.

**Each page answers one question, and its sections are the parts of the
answer.** They are not organised by where the data comes from or by what
shape of chart it happens to fit — the games page is *how people play*, the
words page is *what makes a word hard*, and a section exists because it is a
step in that argument. This is why «Анатомия сложности» is no longer at the
bottom of the games page: it was never about games.

- **Total — how the game is played**: the headline figures (games, words,
  dictionary + used) set straight on the paper and ruled apart, caption
  underneath — `.figures`, deliberately not a row of bordered cards with the
  label on top, which is a dashboard's idiom; the longest-explained word on
  its honey slip, with a human-readable duration via the ported
  pluralisation macros (which every generated sentence on these pages goes
  through — «23 слов» is how a page announces that a machine wrote it).
  Then three named sections: **«Когда достают шляпу»** — the hour-of-week
  punchcard (`.punch`, the old amCharts bubble chart as a dot grid, size and
  opacity carrying count) with by-hour columns and by-day bars under it,
  since the three answer one question between them. Every punchcard cell
  carries its own `--d` and `--h` and is placed explicitly, so the narrow
  layout transposes it — hours down the page, days across — instead of
  scrolling sideways, which used to hide the evening, the one part of that
  chart anyone reads. **No chart scrolls sideways at any width**; if one
  cannot fit, it changes shape. The hours are each player's own wall clock,
  not UTC — the client sends `time_zone_offset` and the pipeline adds it
  before bucketing, so a game at nine in the evening lands in the 21:00 slot
  wherever it was played, and nothing downstream may shift it again.
  **«Как выглядит одна партия»** — players, words and minutes of an average
  game, from the daily records, over games by player count;
  **«Сколько уже сыграно»** — the daily activity strip (`.columns--dense`,
  one thin column per day over the last 84 days) with the full history as a
  `<details>` table.
- **Words — what makes a word hard**: search; the three hardest words
  showcased on torn slips; the hardest/easiest/random tables; then the
  argument. **«Сколько это в секундах»** reads the rating back out in
  seconds per attempt (on live data the buckets run 4.6 s to 27.1 s). Note
  what this is and is not: every rating pass in `stats` sorts a game's words
  by explanation time, so seconds are the rating's raw material and this
  chart is *not* independent evidence — but only the order *within one game*
  is used, because one pair plays fast and another slow and absolute seconds
  are not comparable across games. The scale is therefore unitless, and this
  is the conversion. **«Частота — не сложность»** shows the words corpus
  frequency gets most wrong, both ways round: the rarest quarter of the
  dictionary sorted by how easy it is, the commonest quarter by how hard.
  Selection is on the conservative bound (`E + 2D` for the easy claim,
  `E − 2D` for the hard one), so no word makes either list on two lucky
  rounds. **«Что ещё видно по словарю»** keeps the relationships
  the old site rendered as matplotlib PNGs (difficulty by corpus frequency,
  by word length) and «Насколько точно мы это знаем» (D by games played,
  which is also the justification for the leaderboard ordering above it).
  All of it comes from one projection pass (`_word_shape`, index-only — the
  heavyweight `used_games` lists never load; see index.yaml) plus the legacy
  `WordFrequency` kind; the frequency sections hide themselves if that kind
  is gone. If the projection is unavailable the page renders without them
  and **nothing is cached**, so it recovers on the next request instead of
  pinning an empty page for the full hour — which is what happens every time
  a composite index is rebuilt.
- **Words, continued**: the legacy «ошибкоопасные слова» table —
  with the error rate computed honestly in Python (the stored `danger`
  property preserves a py27 floor-division bug and is ~always 0, so the old
  page ranked by garbage); per-word view with the old gauge laid flat
  (`.scale`: confidence band E ± 2D, marker at E, a tick at 50 — the average
  word — on an axis that grows past 100 when the rating does, because a
  TrueSkill mu is not bounded and a few words sit above it), outcome bars,
  and the explanation-time histogram.

## «Что сложнее?» — the daily duel

`/duel` is the statistics pages' argument turned into a game: ten pairs of
words a day, and you say which of each takes longer to explain. It is the one
place on the site where the dictionary's ratings are the answer to a question
rather than a table, so it is the one page that has to make them *feel* like
something — and it is a program, because it keeps a score and shares it.

**The day is a ramp, and that is the shape of the game.** The ten pairs are
drawn one per band of `_GAP_BANDS`, widest difference first. A flat run of ten
comparable pairs was the first cut and it was wrong: ten coin-flips of the
same weight, and a score that says only how lucky you were. Ordered, the run
of pips reads as how far you got before the difference stopped being visible,
and the shared grid says the same at a glance.

**It ramps along two axes, and the second one matters more.** The gap closes
from about seven points to under two and a half — the floor, where the answer
is still 90 % certain and a person has no chance of seeing it. But gap alone
was never what made a pair easy. Corpus frequency was: left to itself, "the
rarer word is the harder one" is right 61 % of the time at a four-point gap
and 90 % at a twenty-point one, so a reader who knows nothing about the
ratings can play well by asking which word sounds more obscure. So from the
sixth pair on, the two words must also be within 1.6× of each other in corpus
frequency, which takes that cue down to a coin flip and leaves the rating as
the only thing to go on. This is the site's own «Частота — не сложность»
argument turned into a rule.

Deliberately *not* the harder-looking option, which is to require frequency to
point the *wrong* way. That reads as harder and is in fact easier, because
used systematically it becomes its own tell: a regular learns "on the late
questions, pick the commoner word" and the game is given away again from the
other side. Neutral cannot be gamed; inverted can.

- **Right and wrong have no colours here**, because this design language has
  none: four slips and a brass band, and no green or red anywhere. So a
  correct answer is a slip that is *there* and a wrong one is a slip that is
  *not* — filled honey paper against a struck-through outline (`.pip--hit`,
  `.pip--miss`). That reads the same to someone who cannot tell two hues
  apart, which a green/red pair does not, and it keeps a fifth colour off the
  felt. The share text is the exception and has to be: a messenger cannot
  render the site's paper, so there it is 🟩 and ⬜.
- **The two slips of a pair are two different papers**, picked from the four
  along with one of the five tears. Deterministically, from the day and the
  number of the pair rather than at random — a reload has to give back the
  same two slips, or coming back to a half-played puzzle would re-paper it
  under the reader. The two are never the same colour, and the offset between
  them turns as the day goes on, so a colour does not keep the same partner.
- **They lie square, and come up when noticed.** Everywhere else on the site
  paper is tilted a degree or two, but there the tilt is decoration; here the
  paper is the thing being compared, and two words set at different angles are
  two words where one is easier to read. So the tilt goes, and the gesture
  that replaces it is scale: `1.035` under the cursor, and the slip you
  pressed keeps it afterwards, which is how the page says "this is what you
  said" without moving anything.
- **The word is roman, not the italic the site's word slips wear.** Those are
  words jotted down in a hurry; these are two words being read against each
  other.
- **The word sits centred on the paper.** The two lines under it — the
  `труднее` tag and the rating — are in the markup from the first paint and
  revealed rather than added, so answering does not change the shape of the
  thing under your finger; the same height is reserved *above* the word, which
  is what stops it sitting high on the slip while two invisible lines wait
  below.
- **The tears are `--rip-*`, not `--tear-*`.** The word-slip tears are cut for
  word-sized paper and their percentages are of the box, so at 340px they bite
  pennants out of the sides instead of reading as torn. Both sets live in
  `hat.css`; the `--rip-*` five began in `static/play/app.css` and moved when
  a second program wanted them.
- **The review changes shape rather than scrolling.** Ten pairs are two rows
  each under one numbered cell, not five columns across: at five columns a
  phone cuts the last two off, and nothing here scrolls sideways at any width.
- **The hero is short on purpose.** It is a game, and the game has to be
  reachable on a phone without scrolling past an argument for it first; what
  the lead does say is the part nobody could guess, that the answer is
  measured rather than an opinion.

## Charts

All charts are **single-series magnitude**, and the "paper & ink" discipline
survives verbatim:

- One hue per chart, no legend — the caption names the series. The hue is the
  slip of the subject: words — honey, time — sky, people — lilac
  (`.bars--sky`, `.bars--lilac` modifiers).
- Marks are capped at 24px and never fill their slot; adjacent marks separate
  by a 2px surface gap, never a stroke.
- **No trough behind the mark.** Bars stand on one ruled axis, the way a bar
  chart is set in print; a grey channel per row is chart-widget furniture and
  puts a second, meaningless rectangle on every line.
- **A fixed scale is drawn against itself, not against the tallest bar.**
  Difficulty is 0–100, so `.bars--difficulty` maps the value straight to the
  width and ticks 50 (the average word) above and below each bar —
  peak-normalising a 46-to-58 range would draw a small real difference as a
  dramatic one. Uncertainty D is measured against 50/3, its value for a word
  nobody has played, so a bar reads as the unknown that is left.
- Values are direct-labelled at the tip; hour labels appear every third column.
- Tabular figures in columns only; text never wears the data colour.
- Charts of many marks ship a `<details>` table view; column charts carry
  `role="img"` with a describing label.
- No pie charts, no dual axes, no chart images.

## Working on it

The statistics pages and `/duel` are server-rendered Jinja2 (`templates/`);
the rest are static files served by `app.yaml` handlers. `/duel` is the page
and `/duel/*` its two shell files, the same split `/play` has. `/` and `/landing` must stay
byte-identical — `/` serves the file rather than rendering it, and a test
asserts this. Fonts live in `assets/fonts/` and are served by the `/assets`
static_dir handler.

To see changes locally, `make serve` mounts `/assets`, `/tos`, `/duel` and the
single-file static handlers so local URLs match production.

`tools/drive.mjs` drives any page here, not just `/play`: it waits on
`data-screen` where there is one and on the document's own readiness where
there is not, and prints the path after each step. `/duel` is played from it
with `sel:` and read back with `eval:`.

Screenshotting notes: headless Chrome on macOS clamps the window width, so
`--window-size=390` crops a wider layout — load the page in a 390px `<iframe>`
to get a true phone viewport. `--force-dark-mode` does not reliably flip
`prefers-color-scheme`; to capture a specific theme, inline the stylesheet
with the light media query removed (evening) or rewritten to `@media all`
(day).
