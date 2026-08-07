// The hat's bookkeeping, in node. `node --test tests/play`, or `make test`.
//
// This is the one part of /play that is pure enough to test without a browser,
// and the one part where a mistake leaves no mark: a word can walk out of the
// hat and never come back while every screen still looks right. The rule the
// whole file is about — **every word is either in the hat, or in the log, and
// never neither** — is therefore asserted directly rather than through the six
// transitions that produce it.
//
// game.js is imported as it ships. Its own imports (dictionary.js, log.js, and
// db.js behind them) touch nothing browser-shaped until they are called, and
// `fill()` is the only method that calls them — so the hat is set by hand and
// the drawing is left to the app.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { Game } from '../../static/play/js/game.js';
import * as logs from '../../static/play/js/log.js';

const WORDS = ['раз', 'два', 'три', 'четыре', 'пять'];

function table(hat = WORDS) {
  const game = new Game({}, ['Аня', 'Боря']);
  game.hat = [...hat];
  return game;
}

/** Nothing lost and nothing conjured, whatever the turn did. */
function accountsFor(game, words) {
  const held = game.word && !game.log.attempts.some(a => a.word === game.word)
    ? [game.word] : [];
  const all = [...game.hat, ...game.log.attempts.map(a => a.word), ...held];
  assert.deepEqual(all.slice().sort(), [...words].sort());
}

test('a guess before the bell hands back the next word', () => {
  const game = table();
  game.startTurn();
  const next = game.record('guessed', 9000, 0, true);
  assert.ok(next);
  assert.equal(next, game.word);
  assert.equal(game.hat.length, 3);      // one played, one in hand
});

test('a guess after the bell ends the turn without touching the hat', () => {
  const game = table();
  game.startTurn();
  assert.equal(game.hat.length, 4);
  // The bell has rung and the guesser lands the word in the extra seconds.
  const next = game.record('guessed', 12000, 1500, false);
  assert.equal(next, null);
  assert.equal(game.hat.length, 4,
    'the next word was drawn and dropped: it is gone from the game');
});

test('a whole turn accounts for every word', () => {
  const game = table();
  game.startTurn();
  game.record('guessed', 9000, 0, true);
  game.record('guessed', 8000, 0, true);
  game.record('guessed', 7000, 1200, false);   // the bell decided this one
  game.commitTurn();
  assert.equal(game.log.attempts.length, 3);
  assert.equal(game.hat.length, 2);
  accountsFor(game, WORDS);
});

test('an error burns the word and a surrender returns it', () => {
  const burnt = table();
  burnt.startTurn();
  const gone = burnt.word;
  assert.equal(burnt.record('failed', 9000, 0, true), null);
  assert.ok(!burnt.hat.includes(gone));
  assert.equal(burnt.turnLog[0].outcome, 'failed');

  const given = table();
  given.startTurn();
  const back = given.word;
  assert.equal(given.record(null, 9000, 0, true), null);
  assert.ok(given.hat.includes(back));
  // No outcome key at all, which is how the parser is told "back in the hat".
  assert.ok(!('outcome' in given.turnLog[0]));
});

test('the last word of the hat ends the turn', () => {
  const game = table(['одно']);
  game.startTurn();
  assert.equal(game.record('guessed', 9000, 0, true), null);
  assert.ok(game.empty);
});

test('amending a verdict keeps the hat and the score honest', () => {
  const game = table();
  game.startTurn();
  const word = game.word;
  game.record('failed', 9000, 0, true);

  game.amend(0, null);                   // «Ошибка» -> «Вернулось в шляпу»
  assert.ok(game.hat.includes(word));
  assert.equal(game.players[0].explained, 0);

  game.amend(0, 'guessed');              // and on to «Угадано»
  assert.ok(!game.hat.includes(word));
  assert.equal(game.players[0].explained, 1);
  assert.equal(game.players[1].guessed, 1);

  game.amend(0, 'failed');               // and back
  assert.ok(!game.hat.includes(word));
  assert.equal(game.players[0].explained, 0);
  assert.equal(game.players[1].guessed, 0);

  accountsFor(game, WORDS);
});

test('a game nobody played is never queued', async () => {
  const game = table();
  // Straight from the handoff screen to «Закончить игру». finish() returns
  // false without reaching IndexedDB, which is also why this runs in node.
  assert.equal(await game.finish(), false);
  assert.equal(await logs.finish({ attempts: [] }), false);
});
