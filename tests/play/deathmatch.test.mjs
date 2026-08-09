// Режим для двоих — deathmatch.js, over the real dictionary and the real db.
//
// The escalation is the mode: every fifth word the game takes something away,
// and which of the two it takes is a coin toss with two floors under it. A
// game that stopped escalating early, or escalated past a floor, would still
// look exactly right on screen — the score would just be someone else's.

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

import { install, serve, reply, stored, wipe } from './helpers/browser.mjs';

install();

const { Deathmatch, BANDS, BONUS_FLOOR, START } =
  await import('../../static/play/js/deathmatch.js');
const dict = await import('../../static/play/js/dictionary.js');

function corpus() {
  const words = [];
  for (let diff = 0; diff <= 100; diff++) {
    for (let n = 0; n < 40; n++) words.push({ word: `w${diff}_${n}`, diff });
  }
  return words;
}

const bucketOf = word => Number(word.split('_')[0].slice(1));

beforeEach(async () => {
  serve((url) => url.includes('/api/v2/dictionary')
    ? reply(200, corpus(), { ETag: '"v1"' })
    : reply(202, null));
  wipe();
  await dict.load();
});

/** Guess `n` words, one after another, as the round screen does. */
async function run(game, n) {
  await game.begin();
  for (let i = 0; i < n; i++) await game.guessed(4000);
  return game;
}

// -- the bands ---------------------------------------------------------------

test('the bands tile the dictionary from 0 to 100 with no gap or overlap', () => {
  assert.equal(BANDS[0][0], 0);
  assert.equal(BANDS[BANDS.length - 1][1], 100);
  for (const [index, [low, high]] of BANDS.entries()) {
    assert.ok(low <= high, `band ${index} is ${low}–${high}`);
    if (index) assert.equal(low, BANDS[index - 1][1] + 1,
      `band ${index} does not start where band ${index - 1} ended`);
  }
});

test('the steps get smaller towards the top, where a bucket costs the most', () => {
  const width = ([low, high]) => high - low + 1;
  assert.ok(width(BANDS[0]) > width(BANDS[BANDS.length - 1]));
});

test('the band is an index the round screen can count slits from', () => {
  // It used to be printed as "сложность 21–30", and a `label` getter turned
  // the pair into that string. Nothing shows the numbers now — the band is
  // how many slits are cut into the slip (nick.js) — so what matters is that
  // it stays a plain 0-based index into BANDS.
  const game = new Deathmatch();
  assert.equal(game.band, 0);
  assert.ok(Number.isInteger(game.band));
  game.band = BANDS.length - 1;
  assert.ok(game.band < BANDS.length);
});

// -- escalation --------------------------------------------------------------

test('nothing is taken away before the fifth word', async () => {
  const game = await run(new Deathmatch(), START.step - 1);
  assert.equal(game.score, 4);
  assert.equal(game.band, 0);
  assert.equal(game.bonus, START.bonus);
  assert.equal(game.changed, null);
});

test('the fifth word takes exactly one of the two', async () => {
  const game = await run(new Deathmatch(), START.step);
  assert.equal(game.score, 5);
  assert.ok(game.changed === 'bonus' || game.changed === 'difficulty');
  const movedBand = game.band === 1;
  const cutBonus = game.bonus === START.bonus - 1;
  assert.ok(movedBand !== cutBonus, 'both moved, or neither did');
  assert.equal(game.changed, movedBand ? 'difficulty' : 'bonus');
});

test('`changed` is cleared by the next word, so the blink is not repeated',
     async () => {
  const game = await run(new Deathmatch(), START.step);
  assert.ok(game.changed);
  await game.guessed(4000);
  assert.equal(game.changed, null);
});

test('every fifth word escalates, and only every fifth', async () => {
  const game = new Deathmatch();
  await game.begin();
  for (let word = 1; word <= 40; word++) {
    await game.guessed(4000);
    const due = word % START.step === 0;
    assert.equal(Boolean(game.changed), due,
      `word ${word} ${game.changed ? 'escalated' : 'did not escalate'}`);
  }
});

test('the bonus stops at its floor and the band stops at the top', async () => {
  // Long enough that both must have run out of room several times over.
  const game = await run(new Deathmatch(), START.step * (BANDS.length + 20));
  assert.equal(game.band, BANDS.length - 1);
  assert.equal(game.bonus, BONUS_FLOOR);
});

test('the bonus never dips below the floor on the way', async () => {
  const game = new Deathmatch();
  await game.begin();
  for (let word = 0; word < 300; word++) {
    await game.guessed(4000);
    assert.ok(game.bonus >= BONUS_FLOOR, `bonus fell to ${game.bonus}`);
    assert.ok(game.band < BANDS.length, `band ran off the end at ${game.band}`);
  }
});

test('once the band is at the top only the bonus can be taken', async () => {
  const game = new Deathmatch();
  await game.begin();
  game.band = BANDS.length - 1;
  game.score = START.step - 1;
  await game.guessed(4000);
  assert.equal(game.band, BANDS.length - 1);
  assert.equal(game.bonus, START.bonus - 1);
  assert.equal(game.changed, 'bonus');
});

test('once the bonus is at its floor only the band can move', async () => {
  const game = new Deathmatch();
  await game.begin();
  game.bonus = BONUS_FLOOR;
  game.score = START.step - 1;
  await game.guessed(4000);
  assert.equal(game.bonus, BONUS_FLOOR);
  assert.equal(game.band, 1);
  assert.equal(game.changed, 'difficulty');
});

test('when neither can give, the game simply stays as hard as it has become',
     async () => {
  const game = new Deathmatch();
  await game.begin();
  game.band = BANDS.length - 1;
  game.bonus = BONUS_FLOOR;
  game.score = START.step - 1;
  const bonus = await game.guessed(4000);
  assert.equal(game.changed, null);
  assert.equal(bonus, BONUS_FLOOR);
  assert.equal(game.band, BANDS.length - 1);
});

test('the words come from the band the game has climbed to', async () => {
  const game = new Deathmatch();
  await game.begin();
  game.band = 8;
  game.word = await game.draw();
  const [low, high] = BANDS[8];
  assert.ok(bucketOf(game.word) >= low && bucketOf(game.word) <= high,
    `${game.word} is not from ${low}–${high}`);
});

// -- the double tap ----------------------------------------------------------

test('a tap that lands with no word in hand scores nothing', async () => {
  const game = new Deathmatch();
  await game.begin();
  game.word = null;                       // mid-draw, as the round screen sees it
  assert.equal(await game.guessed(4000), null);
  assert.equal(game.score, 0);
  assert.equal(game.log.attempts.length, 0);
});

test('two taps a millisecond apart score one word, not one word twice', async () => {
  // The word is taken out of hand before the draw at the end precisely so that
  // this cannot double-count: sixteen taps on eight words once scored 16 and
  // sent a log with every word in it twice.
  const game = new Deathmatch();
  await game.begin();
  const [first, second] = await Promise.all([
    game.guessed(4000), game.guessed(4000),
  ]);
  assert.equal(game.score, 1);
  assert.equal(second, null);
  assert.ok(first !== null);
  assert.equal(game.log.attempts.length, 1);
});

// -- the log -----------------------------------------------------------------

test('a guessed word is logged as guessed, with its time', async () => {
  const game = new Deathmatch();
  await game.begin();
  const word = game.word;
  await game.guessed(4321.6);
  assert.deepEqual(game.log.attempts[0],
    { word, from: 0, to: 1, time: 4322, extra_time: 0, outcome: 'guessed' });
});

test('the word in hand when the clock runs out has no outcome at all', async () => {
  const game = await run(new Deathmatch(), 2);
  const held = game.word;
  await game.end(1500);
  const last = game.log.attempts[game.log.attempts.length - 1];
  assert.equal(last.word, held);
  assert.ok(!('outcome' in last), 'a word still in hand was logged as failed');
});

test('no word in hand is nothing at all, not a word returned', async () => {
  const game = new Deathmatch();
  await game.begin();
  game.word = null;                       // the clock ran out inside a draw
  await game.end(1500);
  assert.equal(game.log.attempts.length, 0);
});

test('ending twice does not send the game twice', async () => {
  const game = await run(new Deathmatch(), 3);
  await game.end(1500);
  const queued = stored('outbox').size;
  const attempts = game.log.attempts.length;
  await game.end(1500);
  assert.equal(stored('outbox').size, queued);
  assert.equal(game.log.attempts.length, attempts);
});

test('a finished run reaches the outbox as one log', async () => {
  const game = await run(new Deathmatch(), 6);
  await game.end(1500);
  const logs = [...stored('outbox').values()];
  assert.equal(logs.length, 1);
  assert.equal(logs[0].version, '2.0');
  assert.equal(logs[0].attempts.length, 7);      // six guessed, one in hand
  assert.ok(logs[0].end_timestamp >= logs[0].start_timestamp);
  // The words a run played must be distinct, or the ratings pass ranks the
  // same word against itself.
  const words = logs[0].attempts.map(a => a.word);
  assert.equal(new Set(words).size, words.length);
});

// -- the per-word times for the end screen --------------------------------

test('wordTimes returns one entry per logged attempt, with its guessed flag', async () => {
  const game = new Deathmatch();
  await game.begin();
  const first = game.word;
  await game.guessed(3000);
  await game.guessed(5000);
  const times = game.wordTimes();
  // Two words guessed, the word now in hand not yet logged.
  assert.equal(times.length, 2);
  assert.equal(times[0].word, first);
  assert.equal(times[0].time, 3000);
  assert.equal(times[0].guessed, true);
  assert.equal(times[1].time, 5000);
  assert.equal(times[1].guessed, true);
});

test('wordTimes marks the word the clock caught in hand as not guessed', async () => {
  const game = new Deathmatch();
  await game.begin();
  await game.guessed(3000);
  const held = game.word;
  await game.end(1500);
  const times = game.wordTimes();
  assert.equal(times.length, 2);
  assert.equal(times[0].guessed, true);
  assert.deepEqual(times[1], { word: held, time: 1500, guessed: false });
});

test('wordTimes is empty before any word is logged', async () => {
  const game = new Deathmatch();
  // begin has not been called: no attempts, no word in hand.
  assert.deepEqual(game.wordTimes(), []);
});
