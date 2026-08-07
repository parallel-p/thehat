// Who explains to whom, and who won — game.js's other half.
//
// The two pairing formulas are what make личная игра a different game from
// парная игра, and they are copied verbatim from beret rather than reinvented.
// Neither is readable enough to check by eye, and both fail quietly: a table
// that never pairs two of its players, or a fixed pair that stops flipping
// halfway, looks like an ordinary evening to everyone sitting at it.

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

import { install, serve, reply, wipe } from './helpers/browser.mjs';

install();

const { Game, DEFAULTS } = await import('../../static/play/js/game.js');
const dict = await import('../../static/play/js/dictionary.js');

const NAMES = ['Аня', 'Боря', 'Вера', 'Гоша', 'Даша', 'Егор', 'Женя', 'Зоя'];
const table = n => NAMES.slice(0, n);

/** The (explainer, guesser) the game hands out over `turns` turns. */
function seating(n, turns, settings = {}) {
  const game = new Game(settings, table(n));
  const out = [];
  for (let turn = 0; turn < turns; turn++) {
    out.push([game.explainer, game.guesser]);
    game.nextTurn();
  }
  return out;
}

const tally = (pairs, side) => pairs.reduce(
  (counts, pair) => counts.set(pair[side], (counts.get(pair[side]) || 0) + 1),
  new Map());

// -- личная игра -------------------------------------------------------------

test('everybody explains to everybody, exactly once per cycle', () => {
  for (let n = 2; n <= 8; n++) {
    const cycle = n * (n - 1);
    const pairs = seating(n, cycle);
    const distinct = new Set(pairs.map(pair => pair.join('>')));
    assert.equal(distinct.size, cycle,
      `a table of ${n} covered ${distinct.size} of ${cycle} pairings`);
  }
});

test('nobody ever explains to themselves', () => {
  for (let n = 2; n <= 8; n++) {
    for (const [explainer, guesser] of seating(n, n * (n - 1) * 2)) {
      assert.notEqual(explainer, guesser, `a table of ${n} paired someone with themselves`);
      assert.ok(explainer >= 0 && explainer < n && guesser >= 0 && guesser < n,
        `a table of ${n} named player ${explainer}/${guesser}`);
    }
  }
});

test('a cycle gives everybody the same number of turns on each side', () => {
  for (let n = 2; n <= 8; n++) {
    const pairs = seating(n, n * (n - 1));
    for (const side of [0, 1]) {
      const counts = [...tally(pairs, side).values()];
      assert.equal(new Set(counts).size, 1,
        `a table of ${n} shared side ${side} out as ${counts.join('/')}`);
    }
  }
});

test('the turn passes down the list, one player at a time', () => {
  const pairs = seating(5, 10);
  assert.deepEqual(pairs.map(pair => pair[0]), [0, 1, 2, 3, 4, 0, 1, 2, 3, 4]);
});

// -- парная игра -------------------------------------------------------------

test('fixed pairs are always neighbours two by two', () => {
  for (const n of [2, 4, 6, 8]) {
    for (const [explainer, guesser] of seating(n, n * 3, { fixedTeams: true })) {
      assert.equal(Math.floor(explainer / 2), Math.floor(guesser / 2),
        `a table of ${n} paired ${explainer} with ${guesser}`);
      assert.notEqual(explainer, guesser);
    }
  }
});

test('every pair explains once, then the direction flips', () => {
  const pairs = seating(6, 6, { fixedTeams: true });
  assert.deepEqual(pairs, [[0, 1], [2, 3], [4, 5], [1, 0], [3, 2], [5, 4]]);
});

test('the flip is a cycle, not a one-off', () => {
  const pairs = seating(4, 8, { fixedTeams: true });
  assert.deepEqual(pairs.slice(0, 4), pairs.slice(4));
});

test('an odd table is refused fixed pairs rather than trusting the lobby', () => {
  // The lobby does not offer the setting for an odd number of players, but
  // settings are remembered between evenings and players are not.
  const game = new Game({ fixedTeams: true }, table(5));
  assert.equal(game.settings.fixedTeams, false);
  for (const [explainer, guesser] of seating(5, 20, { fixedTeams: true })) {
    assert.ok(explainer < 5 && guesser < 5);
  }
});

// -- the score ---------------------------------------------------------------

test('a personal score is what you got plus what you got across', () => {
  const game = new Game({}, table(3));
  Object.assign(game.players[0], { explained: 4, guessed: 1 });
  Object.assign(game.players[1], { explained: 2, guessed: 2 });
  Object.assign(game.players[2], { explained: 0, guessed: 3 });
  assert.deepEqual(game.standings(), [
    { name: 'Аня', guessed: 1, explained: 4, score: 5 },
    { name: 'Боря', guessed: 2, explained: 2, score: 4 },
    { name: 'Вера', guessed: 3, explained: 0, score: 3 },
  ]);
});

test('a pair scores the words it got, not those words twice', () => {
  // In fixed pairs the explainer and the guesser are always partners, so a
  // pair's explained and its guessed are the same words seen from either end.
  const game = new Game({ fixedTeams: true }, table(4));
  Object.assign(game.players[0], { explained: 5, guessed: 3 });
  Object.assign(game.players[1], { explained: 3, guessed: 5 });
  Object.assign(game.players[2], { explained: 2, guessed: 4 });
  Object.assign(game.players[3], { explained: 4, guessed: 2 });

  const [first, second] = game.standings();
  assert.equal(first.score, 8);
  assert.equal(second.score, 6);
  assert.equal(first.name, 'Аня и Боря');
  // The members travel with the pair so the scoreboard can show who did which
  // half — the columns are per person, the Σ is per pair.
  assert.deepEqual(first.members.map(person => person.name), ['Аня', 'Боря']);
  assert.deepEqual(first.members.map(person => person.explained), [5, 3]);
});

test('the scoreboard is ordered by score, best first', () => {
  const game = new Game({}, table(4));
  game.players.forEach((player, index) => { player.explained = index; });
  assert.deepEqual(game.standings().map(row => row.score), [3, 2, 1, 0]);
});

// -- filling the hat ---------------------------------------------------------

test('the hat holds words per player, and the first pair is seated', async () => {
  serve(() => reply(200, Array.from({ length: 101 * 40 }, (_, i) => ({
    word: `w${i}`, diff: i % 101,
  })), { ETag: '"v1"' }));
  wipe();
  await dict.load();

  const game = new Game({ wordsPerPlayer: 7 }, table(4));
  await game.fill();
  assert.equal(game.hat.length, 28);
  assert.equal(new Set(game.hat).size, 28, 'the hat holds a word twice');
  assert.deepEqual([game.explainer, game.guesser], [0, 1]);
});

test('the defaults are the game as it is meant to be played', () => {
  assert.equal(DEFAULTS.wordsPerPlayer, 10);
  assert.equal(DEFAULTS.roundLength, 20);
  assert.equal(DEFAULTS.extraLength, 3);
  assert.equal(DEFAULTS.fixedTeams, false);
});
