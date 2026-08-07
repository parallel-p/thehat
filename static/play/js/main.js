// Screens, and the wiring between them.

import * as db from './db.js';
import * as dict from './dictionary.js';
import * as logs from './log.js';
import * as audio from './audio.js';
import { ticker, keepAwake } from './clock.js';
import { Game, DEFAULTS } from './game.js';
import { Deathmatch, START as DM } from './deathmatch.js';
import { nicked } from './nick.js';

const $ = id => document.getElementById(id);
const body = document.body;

let settings = { ...DEFAULTS };
let names = ['Игрок 1', 'Игрок 2'];
let game = null;
let dm = null;
let clock = null;          // the running turn's ticker, if any

// -- navigation and the Android back button --------------------------------
//
// An installed app is judged on this: Back has to mean "up one", and only at
// the top may it mean "close". A one-document app has no history of its own,
// so without this every Back — from the lobby, from the middle of a round —
// closes the whole thing. What we have instead is a number of spare entries
// pushed above the one the app was launched on; Back spends them one at a
// time, and each is spent for a reason:
//
//   * outside a game, the screen's own entry: lobby and the scoreboards
//     return home, and home belongs to the browser, so one more Back closes
//     an installed app.
//   * inside a game, two spares that absorb the press and do nothing. A phone
//     gets passed around a table and pressed against a lot of hands; a stray
//     Back must not be able to end a game people are playing. The ways out
//     are on the screen.
//   * while a countdown runs, its own entry on top: spending it stops the
//     countdown, which is the one case where the reader clearly means "wait,
//     not yet".
//
// Every one of those entries is pushed while the app has the user's gesture —
// never from inside the popstate handler, which is what the old version did
// to re-arm itself. Chromium's history manipulation intervention treats a
// same-document Back as ending the document's user activation, so that push
// counted as one made without a gesture, and the punishment for it is not
// aimed at the new entry alone: *every* same-document entry, the launch entry
// included, is marked skippable. The next Back then skipped the lot and shut
// the app — one press after a countdown was dismissed. So arming happens on
// taps (which also clears any such mark), and popstate only ever spends.
const IN_GAME = new Set(['handoff', 'round', 'verdict', 'dm-round']);

let spares = 0;             // history entries we have pushed above the launch one
let settling = false;       // a traversal we asked for ourselves, not the reader
let countdown = null;       // the 3-2-1 interval, when one is running
let counting = null;        // the number it is counting on

/** How many presses the situation on screen has to be able to absorb. */
function wanted() {
  const screen = body.dataset.screen;
  if (screen === 'home' || screen === 'loading') return 0;
  return (IN_GAME.has(screen) ? 2 : 1) + (countdown ? 1 : 0);
}

/** Top the stack back up. Only ever called with a gesture in hand. */
function arm() {
  while (spares < wanted()) {
    spares += 1;
    // Each entry carries its own count, so the tally is read back off the
    // entry we land on rather than inferred — a Forward press in a browser
    // tab would otherwise be counted as a Back.
    history.pushState({ spare: spares }, '');
  }
}

function render(screen) {
  body.dataset.screen = screen;
  const isRound = screen === 'round' || screen === 'dm-round';
  keepAwake(isRound);
  if (!isRound) body.removeAttribute('data-phase');
  // Whenever the home screen appears — by button, by Back, or on boot — the
  // outbox count is re-read. A game finishing kicks off its upload without
  // waiting for it, so any count taken at that moment is a guess.
  if (screen === 'home') refreshOutbox();
}

/** Home, and every spare spent — so the next Back closes an installed app. */
function goHome() {
  render('home');
  if (spares === 0) return;
  const spent = spares;
  spares = 0;
  settling = true;
  history.go(-spent);
}

function show(screen) {
  if (screen === 'home') { goHome(); return; }
  render(screen);
  arm();
}

/**
 * Put the 3-2-1 away, however it ended. Every screen that can count down
 * goes through here, because a number left on screen belongs to a screen
 * nobody is looking at yet: the one that showed "1" as the turn started is
 * the one you come back to, and it would greet you with a stale 1 over the
 * whole panel.
 */
function clearCountdown() {
  if (counting) { counting.hidden = true; counting = null; }
  $('h-hint').hidden = false;
}

/** Stop a running 3-2-1 and put its screen back the way it was. */
function cancelCountdown() {
  if (!countdown) return false;
  clearInterval(countdown);
  countdown = null;
  clearCountdown();
  return true;
}

window.addEventListener('popstate', (event) => {
  const landed = (event.state && event.state.spare) || 0;
  const wentBack = landed < spares;
  spares = landed;
  if (settling) { settling = false; return; }
  if (!wentBack) return;              // Forward, in a tab: nothing to undo.
  const from = body.dataset.screen;

  // "Wait, not yet" — the countdown stops and the screen waits to be tapped
  // again. Checked before anything else, since a countdown runs on top of a
  // screen that would otherwise be blocked or would go home.
  if (cancelCountdown()) return;

  if (IN_GAME.has(from)) return;      // absorbed; the next tap arms another

  goHome();                           // lobby, a scoreboard, or the unforeseen
});

// -- settings -------------------------------------------------------------

async function loadSettings() {
  const stored = await db.get('meta', 'settings');
  if (stored) settings = { ...DEFAULTS, ...stored };
  const storedNames = await db.get('meta', 'players');
  if (Array.isArray(storedNames) && storedNames.length >= 2) names = storedNames;
}

function saveSettings() {
  db.put('meta', 'settings', settings);
  db.put('meta', 'players', names);
}

// -- lobby ----------------------------------------------------------------

/**
 * The player list. Order matters twice over — fixed pairs are neighbours in
 * it, and a personal game passes the turn down it — so rows can be moved,
 * and `focus` says what to put the cursor back on once they have been.
 */
function renderPlayers(focus = null) {
  const list = $('players');
  list.textContent = '';
  const paired = $('s-teams').checked;
  const colours = ['--slip-honey', '--slip-sky', '--slip-lilac', '--slip-rose'];

  names.forEach((name, index) => {
    const li = document.createElement('li');
    li.className = 'player';
    if (paired) {
      li.classList.add('player--paired',
        index % 2 === 0 ? 'player--pair-top' : 'player--pair-bottom');
      li.style.setProperty('--pair', `var(${colours[Math.floor(index / 2) % 4]})`);
    }

    const input = document.createElement('input');
    input.className = 'player__input';
    input.value = name;
    input.setAttribute('aria-label', `Игрок ${index + 1}`);
    input.addEventListener('input', () => { names[index] = input.value; });
    li.append(input);

    const grip = document.createElement('button');
    grip.className = 'player__grip';
    grip.type = 'button';
    grip.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
      + '<path d="M3 5h10M3 8h10M3 11h10"/></svg>';
    grip.setAttribute('aria-label', `Переместить ${name}`);
    grip.title = 'Перетащите, чтобы поменять порядок';
    grip.addEventListener('pointerdown', event => startDrag(event, index));
    // The same move by keyboard, since a drag is not something every reader
    // can do — and it is how the order is checked in tests.
    grip.addEventListener('keydown', (event) => {
      const step = event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0;
      if (!step) return;
      event.preventDefault();
      movePlayer(index, index + step);
    });
    li.append(grip);

    if (names.length > 2) {
      const drop = document.createElement('button');
      drop.className = 'player__drop';
      drop.type = 'button';
      drop.textContent = '×';
      drop.setAttribute('aria-label', `Убрать игрока ${index + 1}`);
      drop.addEventListener('click', () => {
        names.splice(index, 1);
        allowTeams();
        renderPlayers();
      });
      li.append(drop);
    }
    list.append(li);
  });

  if (focus) {
    const row = list.children[focus.index];
    if (!row) return;
    if (focus.what === 'input') {
      const input = row.querySelector('.player__input');
      input.focus();
      // A fresh player is called «Игрок 3» — a placeholder, not a name. Select
      // it, so the first keystroke replaces it instead of appending to it.
      input.select();
    } else {
      row.querySelector('.player__grip').focus();
    }
  }
}

/**
 * Dragging a row by its grip. Nothing in the DOM moves while the finger is
 * down: the row being carried is translated under it, the rows it has passed
 * shift by one place to open the gap, and only on release does the list get
 * rebuilt in the new order. Moving nodes mid-drag would pull the element that
 * holds the pointer capture out from under the drag.
 */
function startDrag(event, from) {
  if (event.button !== undefined && event.button !== 0) return;
  const list = $('players');
  const rows = [...list.children];
  const rects = rows.map(row => row.getBoundingClientRect());
  if (rows.length < 2) return;
  // The real distance between two rows, which is not the row height: pairs
  // put a margin under every second one.
  const step = from + 1 < rows.length
    ? rects[from + 1].top - rects[from].top
    : rects[from].top - rects[from - 1].top;
  const middle = rects[from].top + rects[from].height / 2;
  const grip = event.currentTarget;
  let to = from;

  event.preventDefault();
  grip.setPointerCapture(event.pointerId);
  rows[from].classList.add('player--lifted');

  const onMove = (move) => {
    const dy = move.clientY - event.clientY;
    rows[from].style.transform = `translateY(${dy}px)`;
    // Wherever the carried row's middle now is, the row whose own middle is
    // nearest is the place it would land.
    let nearest = from;
    let best = Infinity;
    rects.forEach((rect, index) => {
      const distance = Math.abs(rect.top + rect.height / 2 - (middle + dy));
      if (distance < best) { best = distance; nearest = index; }
    });
    to = nearest;
    rows.forEach((row, index) => {
      if (index === from) return;
      const shift = (from < to && index > from && index <= to) ? -step
        : (from > to && index >= to && index < from) ? step : 0;
      row.style.transform = shift ? `translateY(${shift}px)` : '';
    });
  };

  const onUp = () => {
    grip.removeEventListener('pointermove', onMove);
    grip.removeEventListener('pointerup', onUp);
    grip.removeEventListener('pointercancel', onUp);
    for (const row of rows) { row.style.transform = ''; row.classList.remove('player--lifted'); }
    if (to !== from) movePlayer(from, to);
    else renderPlayers({ index: from, what: 'grip' });
  };

  grip.addEventListener('pointermove', onMove);
  grip.addEventListener('pointerup', onUp);
  grip.addEventListener('pointercancel', onUp);
}

function movePlayer(from, to) {
  if (to < 0 || to >= names.length) return;
  const [moved] = names.splice(from, 1);
  names.splice(to, 0, moved);
  renderPlayers({ index: to, what: 'grip' });
}

/**
 * Fixed pairs are made of neighbours two by two, so an odd number of players
 * cannot be paired at all. The old screen accepted the setting and then
 * refused to start the game; this one does not offer it in the first place.
 */
function allowTeams() {
  const even = names.length % 2 === 0;
  const box = $('s-teams');
  box.disabled = !even;
  if (!even && box.checked) box.checked = false;
  $('teams-note').hidden = even;
}

function fillSettingsForm() {
  $('s-words').value = settings.wordsPerPlayer;
  $('s-round').value = settings.roundLength;
  $('s-extra').value = settings.extraLength;
  $('s-diff').value = settings.difficulty;
  $('s-disp').value = settings.dispersion;
  $('s-teams').checked = settings.fixedTeams;
  allowTeams();
  paintBand();
}

function readSettingsForm() {
  const int = (el, min, max, fallback) => {
    const value = parseInt(el.value, 10);
    return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
  };
  settings.wordsPerPlayer = int($('s-words'), 1, 50, DEFAULTS.wordsPerPlayer);
  settings.roundLength = int($('s-round'), 5, 120, DEFAULTS.roundLength);
  settings.extraLength = int($('s-extra'), 0, 30, DEFAULTS.extraLength);
  settings.difficulty = int($('s-diff'), 0, 100, DEFAULTS.difficulty);
  settings.dispersion = int($('s-disp'), 0, 45, DEFAULTS.dispersion);
  settings.fixedTeams = $('s-teams').checked;
}

// How long a word of a given difficulty takes, in seconds.
//
// The rating is dimensionless by construction: every pass of the statistics
// pipeline ranks the words of ONE game by explanation time and keeps only that
// order, because absolute seconds are not comparable between one pair and
// another. So the app cannot work this out — it asks /api/v2/word_seconds,
// built from the same projection as the statistics page, and keeps the answer
// so an evening with no signal still has one.
//
// Its `d` is the difficulty bucket this app draws on — the `diff` in the
// dictionary blob, a rank out of 100 — and not E, which the curve was keyed on
// until 2026-08-04 and which made every reading here answer about words other
// than the ones being drawn.
//
// FALLBACK is what a first run offline shows: measured 2026-08-04, and wrong
// only in the way any number is before it has been refreshed.
const FALLBACK_SECONDS = [
  { d: 0, avg: 5.8 }, { d: 10, avg: 8.0 }, { d: 20, avg: 9.3 },
  { d: 30, avg: 10.6 }, { d: 40, avg: 11.9 }, { d: 50, avg: 13.1 },
  { d: 60, avg: 14.4 }, { d: 70, avg: 15.7 }, { d: 80, avg: 17.6 },
  { d: 90, avg: 19.5 }, { d: 100, avg: 24.1 },
];

let secondsTable = FALLBACK_SECONDS;

async function loadSeconds() {
  const stored = await db.get('meta', 'seconds');
  if (Array.isArray(stored) && stored.length) secondsTable = stored;
  try {
    const response = await fetch('/api/v2/word_seconds', { cache: 'no-cache' });
    if (!response.ok) return;
    const rows = await response.json();
    if (!Array.isArray(rows) || !rows.length) return;   // no clock data yet
    secondsTable = rows;
    await db.put('meta', 'seconds', rows);
  } catch (_) {
    // Offline, or the server has nothing to say. The stored table stands.
  }
}

/** Seconds at a difficulty: the curve's own reading, between its points. */
function secondsAt(difficulty) {
  const table = secondsTable;
  if (difficulty <= table[0].d) return table[0].avg;
  for (let i = 1; i < table.length; i++) {
    if (difficulty > table[i].d) continue;
    const before = table[i - 1], after = table[i];
    const span = after.d - before.d;
    if (!span) return after.avg;
    const t = (difficulty - before.d) / span;
    return before.avg + t * (after.avg - before.avg);
  }
  return table[table.length - 1].avg;
}

/** The scale over the sliders: where the words come from, and what it costs. */
function paintBand() {
  const difficulty = parseInt($('s-diff').value, 10);
  const dispersion = parseInt($('s-disp').value, 10);
  $('s-diff-val').textContent = difficulty;
  $('s-disp-val').textContent = dispersion;

  // Words are drawn from Normal(difficulty, (dispersion / 3)²) — see
  // dictionary.js — so ±2σ is the range all but a twentieth of them land in.
  // The same interval the statistics pages wash in for a word's own rating.
  const sigma = dispersion / 3;
  const low = Math.max(0, difficulty - 2 * sigma);
  const high = Math.min(100, difficulty + 2 * sigma);
  $('band-wash').style.left = `${low}%`;
  $('band-wash').style.width = `${high - low}%`;

  // What the words in that band cost, at both of its ends — a single number
  // taken at the centre would be a poor description of a wide band.
  const easy = Math.round(secondsAt(low));
  const hard = Math.round(secondsAt(high));
  $('s-secs').textContent = easy === hard ? `${easy} с` : `${easy}–${hard} с`;
}

function lobbyProblem() {
  const trimmed = names.map(n => n.trim());
  if (trimmed.some(n => !n)) return 'У каждого игрока должно быть имя.';
  if (new Set(trimmed).size !== trimmed.length) return 'Имена должны различаться.';
  return null;
}

// -- a turn ---------------------------------------------------------------

function showHandoff() {
  $('h-explainer').textContent = game.players[game.explainer].name;
  $('h-guesser').textContent = game.players[game.guesser].name;
  show('handoff');
}

function beginTurn() {
  if (body.dataset.screen !== 'handoff' || countdown) return;
  $('h-hint').hidden = true;
  countdown = tick($('h-count'), () => runTurn());
}

/**
 * The 3-2-1 shared by both modes. The handle is module-scoped so that Back
 * can stop it; a countdown is the one thing in a game Back may interrupt.
 */
function tick(counter, then) {
  let left = 3;
  counting = counter;
  counter.textContent = left;
  counter.hidden = false;
  audio.play('tick');
  return setInterval(() => {
    left -= 1;
    if (left > 0) {
      counter.textContent = left;
      audio.play('tick');
    } else {
      clearInterval(countdown);
      countdown = null;
      clearCountdown();          // the number goes before the screen changes
      audio.play('start');
      then();
    }
  }, 1000);
}

// -- the word on its slip ---------------------------------------------------

const SLIPS = ['rose', 'honey', 'sky', 'lilac'];
let slipsDrawn = 0;         // how many words have been shown, ever
let onScreen = null;        // the slip being read right now, for a refit

/**
 * Show a word: the next slip out of the hat, sized so that it stays on one
 * line. Russian words run long and the display size is large, so at the size
 * the round screen wants, "достопримечательность" would set as three lines
 * of a slip nobody can read across a table. It shrinks instead — and because
 * the slip's padding is in em, the whole piece of paper shrinks with it.
 */
function showWord(slip, word, nicks = 0) {
  const text = slip.firstElementChild;
  text.textContent = word;
  slip.className = `word torn word--${SLIPS[slipsDrawn % SLIPS.length]}`;
  slipsDrawn += 1;
  // Kept on the element rather than in a variable, because a refit has to be
  // able to cut the same slip the same way without knowing how it got there.
  slip.dataset.nicks = nicks;
  slip.dataset.seed = slipsDrawn;
  onScreen = slip;
  fitWord(slip);
  cutNicks(slip);
}

/**
 * The slits that carry a deathmatch word's difficulty, cut into the slip the
 * app already draws — see nick.js. Nought of them is the ordinary paper, and
 * the ordinary paper is then left exactly alone: no inline clip-path, so the
 * stylesheet's --rip is what a level-1 slip wears, same as everywhere else.
 */
function cutNicks(slip) {
  const nicks = Number(slip.dataset.nicks) || 0;
  // Cleared first whatever happens, so the read below is the stylesheet's rip
  // and not the last cut of this same slip — otherwise a refit nicks the
  // nicks, and the paper dissolves a little more every time the phone turns.
  slip.style.clipPath = '';
  if (!nicks) return;
  const box = slip.getBoundingClientRect();
  if (box.width <= 0) return;
  slip.style.clipPath = nicked(getComputedStyle(slip).clipPath,
                               box.width, box.height, nicks,
                               Number(slip.dataset.seed) || 1);
}

function fitWord(slip) {
  const text = slip.firstElementChild;
  // 0.97, because a slip is laid down at an angle and a tilted box reaches a
  // little wider than it measures. The slot's own width does not depend on
  // the type inside it, so this can be read before the size is reset.
  const room = slip.parentElement.clientWidth * 0.97;
  // A screen that is not the one on display measures zero, and a slip scaled
  // to fit zero would stay invisible for the rest of the turn: show the
  // screen first, then the word.
  if (room <= 0) return;
  slip.style.fontSize = '';                    // back to the ceiling in the CSS
  const style = getComputedStyle(slip);
  const size = parseFloat(style.fontSize);
  const sides = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
  const want = text.getBoundingClientRect().width + sides;
  if (want > room) slip.style.fontSize = `${size * room / want}px`;
}

// A phone turned on its side mid-turn changes the room a word has.
window.addEventListener('resize', () => {
  if (!onScreen) return;
  fitWord(onScreen);
  cutNicks(onScreen);            // the tear is in px; the box just changed
});

function runTurn() {
  game.startTurn();
  $('r-last').hidden = true;
  $('r-left').textContent = `в шляпе ${game.hat.length + 1}`;
  show('round');                  // on screen first: the slip measures itself
  showWord($('r-word'), game.word);

  const roundMs = settings.roundLength * 1000;
  const extraMs = settings.extraLength * 1000;
  let wordStart = 0;              // ms into the turn when this word appeared
  let phase = 'main';
  let bellAt = null;              // elapsed when the bell rang

  const finishWord = (outcome) => {
    const now = clock.elapsed();
    // In the extra time the clock has already stopped: what the parser calls
    // `time` is the time up to the bell, and the overshoot is `extra_time`.
    const time = phase === 'main' ? now - wordStart : bellAt - wordStart;
    const extra = phase === 'main' ? 0 : now - bellAt;
    // After the bell there is one word and no more, so the turn does not go on
    // however it ends — and the game must not draw the next one, or it leaves
    // the hat unseen. One place decides this, and it is `record`.
    const next = game.record(outcome, Math.max(0, time), Math.max(0, extra),
                             phase === 'main');
    if (next) {
      wordStart = now;
      showWord($('r-word'), next);
      $('r-left').textContent = `в шляпе ${game.hat.length + 1}`;
    } else {
      endTurn();
    }
  };

  const paint = (elapsed) => {
    if (phase === 'main') {
      const left = Math.ceil((roundMs - elapsed) / 1000);
      $('r-timer').textContent = Math.max(0, left);
      if (elapsed >= roundMs) {
        phase = 'last';
        bellAt = roundMs;
        body.dataset.phase = 'last';
        audio.play('timeout');
        if (extraMs === 0) { timeUp(); return; }
        $('r-last').hidden = false;
      }
    } else {
      const left = Math.max(0, Math.ceil((roundMs + extraMs - elapsed) / 1000));
      $('r-timer').textContent = left;
      $('r-last').textContent = left;
      if (elapsed >= roundMs + extraMs) timeUp();
    }
  };

  const timeUp = () => {
    // Out of time with the word still in hand: no outcome at all, which the
    // parser reads as "returned to the hat" rather than as a failure.
    const time = bellAt - wordStart;
    game.record(null, Math.max(0, time), extraMs, false);
    audio.play('over');
    endTurn();
  };

  const endTurn = () => {
    clock.stop();
    clock = null;
    $('r-last').hidden = true;
    showVerdict();
  };

  // The buttons act through this closure, so it is the only place that knows
  // how a word is timed.
  currentWordAction = finishWord;
  clock = ticker(paint, 100);
  paint(0);
}

let currentWordAction = null;

// -- verdict ---------------------------------------------------------------

const OUTCOME_LABEL = {
  guessed: 'Угадано',
  failed: 'Ошибка',
  '': 'Вернулось в шляпу',
};

function showVerdict() {
  const list = $('outcomes');
  list.textContent = '';
  game.turnLog.forEach((entry, index) => {
    const li = document.createElement('li');
    li.className = 'outcome';
    const word = document.createElement('span');
    word.className = 'outcome__word';
    word.textContent = entry.word;
    const pick = document.createElement('select');
    pick.className = 'outcome__pick';
    pick.setAttribute('aria-label', `Итог для слова ${entry.word}`);
    for (const [value, label] of Object.entries(OUTCOME_LABEL)) {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      pick.append(option);
    }
    pick.value = entry.outcome || '';
    pick.addEventListener('change', () => {
      game.amend(index, pick.value || null);
    });
    li.append(word, pick);
    list.append(li);
  });
  show('verdict');
}

function nextTurn() {
  game.commitTurn();
  if (game.empty) { endGame(); return; }
  game.nextTurn();
  showHandoff();
}

// The two halves of a score, as beret drew them: a lightbulb for the word
// you got, a speech bubble for the word you got across. Its icons are
// Material's; these are the same two ideas drawn in this app's own line.
const SCORE_ICONS = {
  guessed: '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
    + '<path d="M8 1.7a4.1 4.1 0 0 0-2.4 7.4c.4.3.7.8.7 1.3v.3h3.4v-.3c0-.5.3-1 .7-1.3A4.1 4.1 0 0 0 8 1.7z"/>'
    + '<path d="M6.3 12.6h3.4M6.9 14.3h2.2"/></svg>',
  explained: '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
    + '<path d="M13.6 3.6a1.5 1.5 0 0 0-1.5-1.5H3.9a1.5 1.5 0 0 0-1.5 1.5v5.1a1.5 1.5 0 0 0 1.5 1.5h1v3l3.3-3h3.9a1.5 1.5 0 0 0 1.5-1.5z"/>'
    + '</svg>',
};

function scoreHead(table) {
  const head = table.createTHead().insertRow();
  const label = (text, className) => {
    const th = document.createElement('th');
    th.textContent = text;
    if (className) th.className = className;
    head.append(th);
    return th;
  };
  label('#');
  label(settings.fixedTeams ? 'Пара' : 'Игрок');
  for (const [key, said] of [['guessed', 'Отгадал'], ['explained', 'Объяснил']]) {
    const th = label('', 'num score__icon');
    th.innerHTML = SCORE_ICONS[key];
    th.title = said;
    const hidden = document.createElement('span');
    hidden.className = 'visually-hidden';
    hidden.textContent = said;
    th.append(hidden);
  }
  label('Σ', 'num').title = 'Всего';
}

async function endGame() {
  game.commitTurn();
  const table = $('score-table');
  table.textContent = '';
  scoreHead(table);

  const bodyEl = table.createTBody();
  game.standings().forEach((row, index) => {
    const tr = bodyEl.insertRow();
    tr.insertCell().textContent = index + 1;
    // A pair is two people: both names, and both of their halves, stacked in
    // their own cells so each column still reads down the table.
    const people = row.members || [row];
    const name = tr.insertCell();
    name.className = 'score__names';
    for (const person of people) {
      const line = document.createElement('span');
      line.textContent = person.name;
      name.append(line);
    }
    for (const key of ['guessed', 'explained']) {
      const cell = tr.insertCell();
      cell.className = 'num score__half';
      for (const person of people) {
        const line = document.createElement('span');
        line.textContent = person[key];
        cell.append(line);
      }
    }
    const score = tr.insertCell();
    score.className = 'num score__total';
    score.textContent = row.score;
  });

  // A game nobody played is not sent, not remembered, and does not claim to
  // be either: backing out of the lobby by way of «Закончить игру» is a normal
  // thing to do, and it should leave nothing behind it.
  const sent = await game.finish();
  if (sent) remember({ at: Date.now(), kind: 'game', rows: game.standings() });
  $('score-note').textContent = !sent
    ? 'В этой игре не сыграно ни одного слова — отправлять нечего.'
    : navigator.onLine
      ? 'Игра отправлена на сервер — из неё считается сложность слов.'
      : 'Игра сохранена и уйдёт на сервер, когда появится сеть.';
  show('score');
  refreshOutbox();
}

// -- deathmatch ------------------------------------------------------------

function beginDeathmatch() {
  if (body.dataset.screen !== 'dm-start' || countdown) return;
  countdown = tick($('d-count'), () => runDeathmatch());
}

async function runDeathmatch() {
  dm = new Deathmatch();
  await dm.begin();

  // Two clocks: the minute, and the bonus that each word buys. The bonus is
  // spent first, so the minute only runs when the bonus is empty.
  let mainLeft = DM.main * 1000;
  let bonusLeft = dm.bonus * 1000;
  let last = 0;
  let wordStart = 0;

  // What the bar is drawn to: the minute plus the bonus at its starting
  // length. The true maximum, because the minute only ever falls — so the bar
  // can never overflow, and the brass segment's width is the bonus in
  // seconds rather than a share of some total that keeps moving.
  const SCALE = (DM.main + DM.bonus) * 1000;
  const CAP = 5;                          // half the bar's height, in px

  const screen = document.querySelector('.screen[data-for="dm-round"]');
  const bar = $('d-bar');

  const paintCount = () => {
    $('d-score').textContent = dm.score;
    $('d-words').textContent = plural(dm.score, 'слово', 'слова', 'слов');
  };

  const paintBar = () => {
    $('d-fill').style.width = `${(mainLeft + bonusLeft) / SCALE * 100}%`;
    // The two split the fill by flex-grow straight off the milliseconds, so
    // their proportions are the clock itself and the join needs no arithmetic
    // to stay put.
    $('d-main').style.flex = `${mainLeft}`;
    $('d-bonus').style.flex = `${bonusLeft}`;
  };

  paintCount();
  paintBar();
  show('dm-round');               // on screen first: the slip measures itself
  showWord($('d-word'), dm.word, dm.band);

  const paint = (elapsed) => {
    const step = elapsed - last;
    last = elapsed;
    if (bonusLeft > 0) bonusLeft = Math.max(0, bonusLeft - step);
    else mainLeft = Math.max(0, mainLeft - step);
    paintBar();
    if (mainLeft === 0 && bonusLeft === 0) finish();
  };

  /** The band moved up: the edge of the screen lights, and the slip that has
   *  already arrived is carrying one more slit than the last one did. */
  const bloom = () => {
    screen.classList.remove('harder');
    void screen.offsetWidth;               // restart the animation
    screen.classList.add('harder');
  };

  /**
   * The bonus was cut. The second that is leaving is drawn over the last
   * second of the bar and held there — `bonusLeft` keeps the old length for
   * now — so what the eye sees is the tip of the clock turning red and
   * breaking off. Shortening the bar first would leave the piece floating
   * past the end with a gap where it broke from.
   */
  const cutSecond = () => {
    $('d-lost').style.left =
      `calc(${(mainLeft + bonusLeft - 1000) / SCALE * 100}% - ${CAP}px)`;
    $('d-lost').style.width = `calc(${1000 / SCALE * 100}% + ${CAP}px)`;
    bar.classList.remove('cut');
    void bar.offsetWidth;
    bar.classList.add('cut');
    // 40% of the 760ms in app.css — the instant the keyframes let go of it.
    // min(), because the ticker may already have drained past the new bonus
    // while it was held, and a cut must never hand a second back.
    setTimeout(() => {
      bonusLeft = Math.min(bonusLeft, dm.bonus * 1000);
      paintBar();
    }, 304);
  };

  currentWordAction = async (outcome) => {
    if (outcome !== 'guessed') { finish(); return; }
    // No word in hand means the previous tap has taken it and the next one is
    // still being drawn. Checked here as well as in `guessed`, and checked
    // synchronously, so that a tap which scores nothing also makes no sound:
    // the click is what the sound is feedback for, and it has to be immediate.
    if (!dm.word) return;
    audio.play('ok');
    const now = clock.elapsed();
    const bonus = await dm.guessed(now - wordStart);
    if (bonus === null) return;
    wordStart = now;
    // A cut refills to the old length and gives the second back a moment
    // later, which is the whole gesture; anything else refills to what the
    // word actually bought.
    bonusLeft = (bonus + (dm.changed === 'bonus' ? 1 : 0)) * 1000;
    showWord($('d-word'), dm.word, dm.band);
    paintCount();
    paintBar();
    if (dm.changed === 'difficulty') bloom();
    if (dm.changed === 'bonus') cutSecond();
  };

  const finish = async () => {
    if (!clock) return;
    clock.stop();
    clock = null;
    audio.play('over');
    await dm.end(Math.max(0, Date.now() - (dm.log.start_timestamp + wordStart)));
    $('d-final').textContent = dm.score;
    remember({ at: Date.now(), kind: 'dm', score: dm.score });
    $('share-btn').hidden = !navigator.share;
    show('dm-score');
    refreshOutbox();
  };

  clock = ticker(paint, 100);
}

// -- history ----------------------------------------------------------------
//
// The app's own memory of the evening. The log it uploads carries the words
// and their timings — it has never carried who won, and the server has
// nowhere to put a scoreboard, so this is the only place a finished game is
// kept. Keyed by when it finished, which is also the order to read it back.

const HISTORY_CAP = 50;      // an evening is ~5 games; this is a year of them

/** слово / слова / слов, the way Russian counts. */
function plural(n, one, few, many) {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return many;
  const mod10 = n % 10;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

async function remember(entry) {
  await db.put('history', entry.at, entry);
  const keys = await db.keys('history');
  // getAllKeys comes back ascending, so the oldest are at the front.
  for (const key of keys.slice(0, Math.max(0, keys.length - HISTORY_CAP))) {
    await db.del('history', key);
  }
}

const WHEN = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit', month: '2-digit', year: 'numeric',
  hour: '2-digit', minute: '2-digit',
});

async function showHistory() {
  const list = $('games');
  list.textContent = '';
  const games = (await db.all('history')).reverse();   // newest first
  $('history-empty').hidden = games.length > 0;

  for (const game of games) {
    const li = document.createElement('li');
    li.className = 'game';
    const when = WHEN.format(new Date(game.at));

    if (game.kind === 'dm') {
      const title = document.createElement('p');
      title.className = 'game__title';
      title.textContent =
        `Режим для двоих — ${game.score} ${plural(game.score, 'слово', 'слова', 'слов')}`;
      const note = document.createElement('p');
      note.className = 'game__when';
      note.textContent = when;
      li.append(title, note);
    } else {
      // The scoreboard is folded away: a list of evenings is what this screen
      // is for, and <details> costs no javascript to open one of them.
      const box = document.createElement('details');
      const summary = document.createElement('summary');
      summary.className = 'game__title';
      const who = document.createElement('span');
      who.textContent = game.rows.map(row => row.name).join(', ');
      // Inside the summary, or the date would be folded away with the
      // scoreboard — and the date is half of what identifies an evening.
      const note = document.createElement('span');
      note.className = 'game__when';
      note.textContent = `${when} · обычная игра`;
      summary.append(who, note);
      const table = document.createElement('table');
      table.className = 'table';
      const tbody = table.createTBody();
      game.rows.forEach((row, index) => {
        const tr = tbody.insertRow();
        tr.insertCell().textContent = index + 1;
        tr.insertCell().textContent = row.name;
        const score = tr.insertCell();
        score.className = 'num';
        score.textContent = row.score;
      });
      box.append(summary, table);
      li.append(box);
    }
    list.append(li);
  }
  show('history');
}

// -- sharing ----------------------------------------------------------------

function shareResult() {
  if (!navigator.share || !dm) return;
  const score = dm.score;
  navigator.share({
    text: `Мы отгадали ${score} ${plural(score, 'слово', 'слова', 'слов')}`
      + ` в «Режиме для двоих» в Шляпе! Попробуйте побить: ${location.origin}/play`,
  }).catch(() => { /* the reader closed the sheet; that is an answer */ });
}

// -- theme ------------------------------------------------------------------
//
// Evening is the design's primary theme and the system's preference is the
// default, so the switch starts at "как в системе" and only remembers a
// choice once one is made. localStorage rather than the app's IndexedDB: the
// inline script in index.html has to read it before the first paint, and it
// cannot wait for a database to open.

const THEMES = ['auto', 'day', 'night'];
let theme = 'auto';

function applyTheme() {
  const root = document.documentElement;
  if (theme === 'auto') root.removeAttribute('data-theme');
  else root.dataset.theme = theme;
  const at = THEMES.indexOf(theme);
  $('theme').style.setProperty('--at', at);
  $('theme').querySelectorAll('input').forEach((radio, index) => {
    radio.checked = index === at;
  });
  // The browser's own furniture — the status bar of an installed app — reads
  // <meta name="theme-color">, which knows nothing about our attribute. Both
  // metas are set to whatever the palette actually resolved to, so whichever
  // one the system matches is the right colour.
  const paper = getComputedStyle(root).getPropertyValue('--paper').trim();
  for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
    meta.content = paper;
  }
}

function setTheme(next) {
  theme = next;
  try {
    if (theme === 'auto') localStorage.removeItem('hat-theme');
    else localStorage.setItem('hat-theme', theme);
  } catch (_) { /* private mode: it lasts as long as the app is open */ }
  applyTheme();
}

function setupTheme() {
  let stored = null;
  try { stored = localStorage.getItem('hat-theme'); } catch (_) { /* ignore */ }
  theme = THEMES.includes(stored) ? stored : 'auto';
  applyTheme();
  // change, not click: the cells are labels over radios, so this is also how
  // the arrow keys arrive.
  $('theme').addEventListener('change', (event) => setTheme(event.target.value));
  // On "как в системе" the phone can still change its mind under us.
  window.matchMedia('(prefers-color-scheme: light)')
    .addEventListener('change', () => { if (theme === 'auto') applyTheme(); });
}

// -- outbox / install ------------------------------------------------------

async function refreshOutbox() {
  const count = await logs.pending();
  const note = $('outbox-note');
  note.hidden = count === 0;
  if (count) {
    note.textContent = count === 1
      ? 'Одна игра ждёт отправки на сервер.'
      : `${count} игр ждут отправки на сервер.`;
  }
}

let installPrompt = null;
let installable = false;    // open in a browser, so the offer means something

/** True when the app was launched from the home screen rather than a tab. */
function installed() {
  return window.navigator.standalone === true
    || ['standalone', 'fullscreen', 'minimal-ui']
      .some(mode => window.matchMedia(`(display-mode: ${mode})`).matches);
}

// iOS cannot prompt: there the banner is an instruction, and it is the whole
// truth on that browser. Kept apart from the prompt path rather than racing
// it, so neither can overwrite the other.
const IOS = /iP(hone|ad|od)/.test(navigator.userAgent);

// At module scope on purpose: Chrome fires this once, and early — while the
// app is still fetching its dictionary and setupInstall has not run. Caught
// here, offered when there is something to offer it on.
window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  installPrompt = event;
  offerInstall();
});
window.addEventListener('appinstalled', () => {
  installPrompt = null;
  $('install').hidden = true;
});

/** The banner with the button behind it: a browser that can install. */
function offerInstall() {
  if (IOS || !installable || !installPrompt) return;
  $('install-text').textContent =
    'Поставьте Шляпу на домашний экран — дальше она играет без интернета.';
  $('install-btn').hidden = false;
  $('install').hidden = false;
}

function setupInstall() {
  // The banner exists if and only if this is the app open in a browser: an
  // installed copy has nothing to offer, and a browser that can neither
  // prompt nor be told how (no Chrome prompt, not iOS) has nothing to say.
  if (installed()) return;
  installable = true;

  if (IOS) {
    $('install-text').textContent =
      'Чтобы играть без интернета: «Поделиться» → «На экран „Домой“».';
    $('install').hidden = false;
    return;                       // no prompt to press, so no button
  }

  $('install-btn').addEventListener('click', () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    installPrompt = null;
    $('install').hidden = true;
  });
  offerInstall();                 // the prompt may already be waiting
}

// -- actions ---------------------------------------------------------------

const actions = {
  // A running countdown covers the screen it belongs to, so nothing here can
  // be pressed while one is going; stopping it is belt and braces, against a
  // countdown ever firing on the home screen.
  home: () => {
    cancelCountdown();
    if (clock) { clock.stop(); clock = null; }
    show('home');
  },
  'new-game': () => { fillSettingsForm(); renderPlayers(); $('players-error').hidden = true; show('lobby'); },
  'add-player': () => {
    names.push(`Игрок ${names.length + 1}`);
    // Pairs first: an odd count turns the setting off, and the list has to be
    // drawn knowing that or it keeps painting pairs that no longer exist.
    allowTeams();
    renderPlayers({ index: names.length - 1, what: 'input' });
  },
  'start-game': async () => {
    readSettingsForm();
    const problem = lobbyProblem();
    const error = $('players-error');
    error.hidden = !problem;
    if (problem) { error.textContent = problem; return; }
    names = names.map(n => n.trim());
    saveSettings();
    game = new Game(settings, names);
    await game.fill();
    showHandoff();
  },
  'begin-turn': beginTurn,
  guessed: () => { audio.play('ok'); currentWordAction('guessed'); },
  failed: () => { audio.play('fail'); currentWordAction('failed'); },
  concede: () => { audio.play('back'); currentWordAction(null); },
  'next-turn': nextTurn,
  'finish-game': endGame,
  'new-dm': () => { cancelCountdown(); show('dm-start'); },
  'begin-dm': beginDeathmatch,
  'dm-guessed': () => currentWordAction('guessed'),
  'dm-concede': () => currentWordAction(null),
  'retry-load': () => start(),
  rules: () => show('rules'),
  history: showHistory,
  share: shareResult,
};

document.addEventListener('click', (event) => {
  audio.unlock();                       // iOS: the first gesture is the one
  const target = event.target.closest('[data-act]');
  const action = target && actions[target.dataset.act];
  if (action) { event.preventDefault(); action(); }
  // Every tap, whether it did anything or not: this is the moment the app is
  // allowed to put entries back on the history stack, and the moment any
  // skippable mark on the entries it already has is cleared.
  arm();
});

$('s-diff').addEventListener('input', paintBand);
$('s-disp').addEventListener('input', paintBand);
$('s-teams').addEventListener('change', () => renderPlayers());

window.addEventListener('online', () => { logs.flush().then(refreshOutbox); });

// -- boot ------------------------------------------------------------------

async function start() {
  // The launch entry. Every spare sits above this one, so Back from the home
  // screen is the browser's to handle — closing an installed app, or
  // returning to whatever page linked here in a tab.
  history.replaceState({ spare: 0 }, '');
  spares = 0;
  setupTheme();
  show('loading');
  $('loading-error').hidden = true;
  $('loading-note').hidden = false;
  try {
    await loadSettings();
    await dict.load();
    // Not awaited: a settings screen with a stale reading beats a game that
    // will not start because a statistics endpoint is slow.
    loadSeconds();
  } catch (_) {
    // No stored dictionary and no network: the one state the app cannot play in.
    $('loading-note').hidden = true;
    $('loading-error').hidden = false;
    return;
  }
  db.persist();
  logs.flush().then(refreshOutbox);
  setupInstall();
  show('home');
  // A link may name the screen to open on: /play#rules is how the site sends
  // a reader to the rules, which have no page of their own since thehat.ru
  // went. render, not show — show would arm, and a pushState here would be
  // one made without a gesture, which is the thing the note at the top of
  // this file is about. Nothing is armed, so Back goes where the reader
  // actually came from: the page that linked here. «← Назад» still reaches
  // the home screen. The hash is left alone, so a reload lands here again.
  if (location.hash === '#rules') render('rules');
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Scope '/play', not '/play/': the document itself is at /play, which a
    // trailing-slash scope does not cover — the worker would install and then
    // never control the one page it exists for. Widening the scope past the
    // worker's own directory needs the Service-Worker-Allowed header, which
    // app.yaml sets. Requests to /assets and /api are intercepted regardless:
    // scope decides which pages are controlled, not which URLs they may fetch.
    navigator.serviceWorker.register('/play/sw.js', { scope: '/play' })
      .catch(() => { /* the app still works, just not offline */ });
  });
}

start();
