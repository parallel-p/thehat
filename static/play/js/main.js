// Screens, and the wiring between them.

import * as db from './db.js';
import * as dict from './dictionary.js';
import * as logs from './log.js';
import * as audio from './audio.js';
import { ticker, keepAwake } from './clock.js';
import { Game, DEFAULTS } from './game.js';
import { Deathmatch, START as DM } from './deathmatch.js';

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
// closes the whole thing.
//
// The stack is kept exactly one entry deep rather than one entry per screen.
// Screens do not form a line you can walk back along: a finished round must
// not be re-enterable, and «назад» from the middle of a game means the same
// thing the on-screen button means, which is to end it and show the score.
// So Back is a decision, not a rewind, and this is the table of decisions.
const BACK = {
  lobby: 'home',
  'dm-start': 'home',
  score: 'home',
  'dm-score': 'home',
  // Mid-game: end the game the same way «Закончить игру» does. Nothing is
  // lost — what was played is committed and uploaded — and the player lands
  // on the scoreboard rather than being dropped out of the app.
  handoff: 'end-game',
  round: 'end-game',
  verdict: 'end-game',
  'dm-round': 'end-dm',
};

let depth = 0;              // history entries we have pushed above the base

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

function show(screen) {
  if (screen === 'home' && depth === 1) {
    // Let the browser do it, so the entry is really gone and one more Back
    // closes the app. popstate below renders the home screen.
    history.back();
    return;
  }
  render(screen);
  if (screen === 'home' || screen === 'loading') return;
  if (depth === 0) { history.pushState({ screen }, ''); depth = 1; }
  else history.replaceState({ screen }, '');
}

window.addEventListener('popstate', () => {
  const from = body.dataset.screen;
  depth = 0;                          // whatever we pushed is gone now
  const target = BACK[from] || 'home';
  if (target === 'end-game') leaveGame();
  else if (target === 'end-dm') leaveDeathmatch();
  else render('home');
});

/** Back out of a game in progress: stop the clock, keep what was played. */
function leaveGame() {
  if (clock) { clock.stop(); clock = null; }
  if (!game || game.finished) { render('home'); return; }
  // The word in hand was never resolved, so it is not recorded — it simply
  // stays in the hat of a game that is now over.
  endGame();
}

function leaveDeathmatch() {
  if (clock) { clock.stop(); clock = null; }
  if (!dm || dm.finished) { render('home'); return; }
  dm.end(0).then(() => {
    $('d-final').textContent = dm.score;
    show('dm-score');
    refreshOutbox();
  });
}

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

function renderPlayers() {
  const list = $('players');
  list.textContent = '';
  names.forEach((name, index) => {
    const li = document.createElement('li');
    li.className = 'player';
    const input = document.createElement('input');
    input.className = 'player__input';
    input.value = name;
    input.setAttribute('aria-label', `Игрок ${index + 1}`);
    input.addEventListener('input', () => { names[index] = input.value; });
    li.append(input);
    if (names.length > 2) {
      const drop = document.createElement('button');
      drop.className = 'player__drop';
      drop.type = 'button';
      drop.textContent = '×';
      drop.setAttribute('aria-label', `Убрать игрока ${index + 1}`);
      drop.addEventListener('click', () => {
        names.splice(index, 1);
        renderPlayers();
      });
      li.append(drop);
    }
    list.append(li);
  });
}

function fillSettingsForm() {
  $('s-words').value = settings.wordsPerPlayer;
  $('s-round').value = settings.roundLength;
  $('s-extra').value = settings.extraLength;
  $('s-diff').value = settings.difficulty;
  $('s-disp').value = settings.dispersion;
  $('s-teams').checked = settings.fixedTeams;
  $('s-diff-val').textContent = settings.difficulty;
  $('s-disp-val').textContent = settings.dispersion;
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

function lobbyProblem() {
  const trimmed = names.map(n => n.trim());
  if (trimmed.some(n => !n)) return 'У каждого игрока должно быть имя.';
  if (new Set(trimmed).size !== trimmed.length) return 'Имена должны различаться.';
  if ($('s-teams').checked && trimmed.length % 2 !== 0) {
    return 'Для игры парами нужно чётное число игроков.';
  }
  return null;
}

// -- a turn ---------------------------------------------------------------

function showHandoff() {
  $('h-explainer').textContent = game.players[game.explainer].name;
  $('h-guesser').textContent = game.players[game.guesser].name;
  $('h-hint').hidden = false;
  $('h-count').hidden = true;
  show('handoff');
}

function beginTurn() {
  if (body.dataset.screen !== 'handoff' || !$('h-count').hidden) return;
  $('h-hint').hidden = true;
  const counter = $('h-count');
  counter.hidden = false;
  let left = 3;
  counter.textContent = left;
  audio.play('tick');
  const countdown = setInterval(() => {
    left -= 1;
    if (left > 0) {
      counter.textContent = left;
      audio.play('tick');
    } else {
      clearInterval(countdown);
      audio.play('start');
      runTurn();
    }
  }, 1000);
}

function runTurn() {
  game.startTurn();
  $('r-word').textContent = game.word;
  $('r-left').textContent = `в шляпе ${game.hat.length + 1}`;
  show('round');

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
    const next = game.record(outcome, Math.max(0, time), Math.max(0, extra));
    if (next && phase === 'main') {
      wordStart = now;
      $('r-word').textContent = next;
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
      }
    } else {
      const left = Math.ceil((roundMs + extraMs - elapsed) / 1000);
      $('r-timer').textContent = Math.max(0, left);
      if (elapsed >= roundMs + extraMs) timeUp();
    }
  };

  const timeUp = () => {
    // Out of time with the word still in hand: no outcome at all, which the
    // parser reads as "returned to the hat" rather than as a failure.
    const time = bellAt - wordStart;
    game.record(null, Math.max(0, time), extraMs);
    audio.play('over');
    endTurn();
  };

  const endTurn = () => {
    clock.stop();
    clock = null;
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

async function endGame() {
  game.commitTurn();
  const table = $('score-table');
  table.textContent = '';
  const head = table.createTHead().insertRow();
  for (const label of ['#', settings.fixedTeams ? 'Пара' : 'Игрок', 'Очки']) {
    const th = document.createElement('th');
    th.textContent = label;
    if (label === 'Очки') th.className = 'num';
    head.append(th);
  }
  const bodyEl = table.createTBody();
  game.standings().forEach((row, index) => {
    const tr = bodyEl.insertRow();
    tr.insertCell().textContent = index + 1;
    tr.insertCell().textContent = row.name;
    const score = tr.insertCell();
    score.className = 'num';
    score.textContent = row.score;
  });
  await game.finish();
  $('score-note').textContent = navigator.onLine
    ? 'Игра отправлена на сервер — из неё считается сложность слов.'
    : 'Игра сохранена и уйдёт на сервер, когда появится сеть.';
  show('score');
  refreshOutbox();
}

// -- deathmatch ------------------------------------------------------------

function beginDeathmatch() {
  if (body.dataset.screen !== 'dm-start' || !$('d-count').hidden) return;
  const counter = $('d-count');
  counter.hidden = false;
  let left = 3;
  counter.textContent = left;
  audio.play('tick');
  const countdown = setInterval(() => {
    left -= 1;
    if (left > 0) {
      counter.textContent = left;
      audio.play('tick');
    } else {
      clearInterval(countdown);
      audio.play('start');
      runDeathmatch();
    }
  }, 1000);
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

  const paintNumbers = () => {
    $('d-score').textContent = dm.score;
    $('d-diff').textContent = dm.difficulty;
    $('d-add').textContent = dm.bonus;
  };

  $('d-word').textContent = dm.word;
  paintNumbers();
  show('dm-round');

  const paint = (elapsed) => {
    const step = elapsed - last;
    last = elapsed;
    if (bonusLeft > 0) bonusLeft = Math.max(0, bonusLeft - step);
    else mainLeft = Math.max(0, mainLeft - step);
    $('d-timer').textContent = Math.ceil((mainLeft + bonusLeft) / 1000);
    if (mainLeft === 0 && bonusLeft === 0) finish();
  };

  const blink = (which) => {
    const el = which === 'bonus' ? $('d-add') : $('d-diff');
    el.classList.remove('blink');
    void el.offsetWidth;                 // restart the animation
    el.classList.add('blink');
  };

  currentWordAction = async (outcome) => {
    if (outcome !== 'guessed') { finish(); return; }
    audio.play('ok');
    const now = clock.elapsed();
    await dm.guessed(now - wordStart);
    wordStart = now;
    bonusLeft = dm.bonus * 1000;
    $('d-word').textContent = dm.word;
    paintNumbers();
    if (dm.changed) blink(dm.changed);
  };

  const finish = async () => {
    if (!clock) return;
    clock.stop();
    clock = null;
    audio.play('over');
    await dm.end(Math.max(0, Date.now() - (dm.log.start_timestamp + wordStart)));
    $('d-final').textContent = dm.score;
    show('dm-score');
    refreshOutbox();
  };

  clock = ticker(paint, 100);
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

function setupInstall() {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    installPrompt = event;
    $('install-btn').hidden = false;
  });
  $('install-btn').addEventListener('click', async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    installPrompt = null;
    $('install-btn').hidden = true;
  });

  // iOS has no install prompt at all: it has to be explained, and only to the
  // people who can act on it — Safari, not already installed.
  const isIOS = /iP(hone|ad|od)/.test(navigator.userAgent);
  const standalone = window.navigator.standalone
    || window.matchMedia('(display-mode: standalone)').matches;
  if (isIOS && !standalone) $('install-note').hidden = false;
}

// -- actions ---------------------------------------------------------------

const actions = {
  home: () => { if (clock) { clock.stop(); clock = null; } show('home'); },
  'new-game': () => { renderPlayers(); fillSettingsForm(); $('players-error').hidden = true; show('lobby'); },
  'add-player': () => { names.push(`Игрок ${names.length + 1}`); renderPlayers(); },
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
  concede: () => { audio.play('timeout'); currentWordAction(null); },
  'next-turn': nextTurn,
  'finish-game': endGame,
  'new-dm': () => { $('d-count').hidden = true; show('dm-start'); },
  'begin-dm': beginDeathmatch,
  'dm-guessed': () => currentWordAction('guessed'),
  'dm-concede': () => currentWordAction(null),
  'retry-load': () => start(),
};

document.addEventListener('click', (event) => {
  audio.unlock();                       // iOS: the first gesture is the one
  const target = event.target.closest('[data-act]');
  if (!target) return;
  const action = actions[target.dataset.act];
  if (action) { event.preventDefault(); action(); }
});

$('s-diff').addEventListener('input', e => { $('s-diff-val').textContent = e.target.value; });
$('s-disp').addEventListener('input', e => { $('s-disp-val').textContent = e.target.value; });

window.addEventListener('online', () => { logs.flush().then(refreshOutbox); });

// -- boot ------------------------------------------------------------------

async function start() {
  // The base entry. Everything the app pushes sits above this one, so Back
  // from the home screen is the browser's to handle — closing an installed
  // app, or returning to whatever page linked here in a tab.
  history.replaceState({ screen: 'home' }, '');
  depth = 0;
  show('loading');
  $('loading-error').hidden = true;
  $('loading-note').hidden = false;
  try {
    await loadSettings();
    await dict.load();
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
