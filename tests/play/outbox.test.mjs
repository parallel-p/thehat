// Getting a game to the server eventually — log.js, over the real db.js.
//
// This is the only part of the app that can lose an evening. The rules it
// follows are not obvious from either end: a log is deleted on any 2xx (the
// server answers 202, and beret checked for 201, which is why every game it
// played was sent twice), a 4xx is dropped rather than retried forever, and a
// 5xx stops the queue where it stands instead of skipping ahead.

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

import { install, serve, reply, stored, wipe, setOnline, calls }
  from './helpers/browser.mjs';

install();

const logs = await import('../../static/play/js/log.js');

/** Let an un-awaited flush finish. `finish` starts one deliberately. */
const settle = () => new Promise(resolve => setTimeout(resolve, 5));

/** A log with `n` attempts in it, ready to be queued. */
function log(n = 1) {
  const entry = logs.newLog();
  for (let i = 0; i < n; i++) {
    entry.attempts.push(logs.attempt({
      word: `слово${i}`, from: 0, to: 1, time: 9000,
    }));
  }
  return entry;
}

/** The game_ids that actually went over the wire, in the order they went. */
const sent = () => calls.map(call => JSON.parse(call.options.body).game_id);

beforeEach(() => {
  wipe();
  setOnline(true);
  serve(() => reply(202, null));
});

// -- the shapes the parser is unforgiving about ------------------------------

test('a new log names itself and says which evening it belongs to', () => {
  const entry = logs.newLog();
  assert.equal(entry.version, '2.0');
  assert.match(entry.game_id, /^[0-9a-f-]{36}$/);
  assert.deepEqual(entry.attempts, []);
  assert.equal(typeof entry.start_timestamp, 'number');
  // The offset is added server-side before the hour-of-week is taken, which is
  // what makes the statistics pages show each player's own evening.
  assert.equal(entry.time_zone_offset,
               -new Date().getTimezoneOffset() * 60 * 1000);
});

test('two logs are two games', () => {
  assert.notEqual(logs.newLog().game_id, logs.newLog().game_id);
});

test('a word that went back in the hat carries no outcome key at all', () => {
  const entry = logs.attempt({ word: 'шляпа', from: 1, to: 0, time: 3000 });
  assert.ok(!('outcome' in entry),
    'absent and "failed" are read differently, and must not be confused');
  assert.equal(entry.extra_time, 0);
});

test('times are whole milliseconds, extra time included', () => {
  const entry = logs.attempt({
    word: 'шляпа', from: 0, to: 1, time: 8600.4, extraTime: 2900.5,
    outcome: 'guessed',
  });
  assert.deepEqual(entry, {
    word: 'шляпа', from: 0, to: 1, time: 8600, extra_time: 2901,
    outcome: 'guessed',
  });
});

// -- queueing ----------------------------------------------------------------

test('a game nobody played is not queued and does not claim to be', async () => {
  assert.equal(await logs.finish(logs.newLog()), false);
  assert.equal(stored('outbox').size, 0);
  assert.equal(calls.length, 0);
});

test('a finished game is stamped, queued under its own id, and sent', async () => {
  const entry = log(3);
  assert.equal(await logs.finish(entry), true);
  assert.ok(entry.end_timestamp >= entry.start_timestamp);
  await settle();
  assert.deepEqual(sent(), [entry.game_id]);
  assert.equal(stored('outbox').size, 0, 'a sent game was left in the outbox');
});

test('pending() counts what is still waiting', async () => {
  setOnline(false);
  await logs.finish(log());
  await logs.finish(log());
  assert.equal(await logs.pending(), 2);
});

// -- what the server says ----------------------------------------------------

test('202 is success — the status the server actually answers', async () => {
  await logs.finish(log());
  await settle();
  assert.equal(await logs.pending(), 0,
    'a 202 left the game queued, and it will be sent a second time');
});

test('a 4xx is dropped rather than retried forever', async () => {
  serve(() => reply(400, null));
  await logs.finish(log());
  await settle();
  assert.equal(await logs.pending(), 0,
    'the server will never take this one, and it would wedge the queue');
});

test('a 5xx keeps the game for later', async () => {
  serve(() => reply(503, null));
  const entry = log();
  await logs.finish(entry);
  await settle();
  assert.equal(await logs.pending(), 1);
  assert.deepEqual([...stored('outbox').keys()], [entry.game_id]);
});

test('a 5xx stops the queue where it stands rather than skipping ahead',
     async () => {
  setOnline(false);
  const first = log(), second = log();
  await logs.finish(first);
  await logs.finish(second);

  setOnline(true);
  serve(() => reply(500, null));
  await logs.flush();
  assert.equal(calls.length, 1, 'the queue carried on past a game it still owes');
  assert.equal(await logs.pending(), 2);
});

test('the network going away stops the queue and loses nothing', async () => {
  setOnline(false);
  await logs.finish(log());
  await logs.finish(log());

  setOnline(true);
  serve(() => { throw new Error('network gone'); });
  await logs.flush();
  assert.equal(await logs.pending(), 2);
});

test('nothing is sent while the app believes it is offline', async () => {
  setOnline(false);
  await logs.finish(log());
  await logs.flush();
  assert.equal(calls.length, 0);
  assert.equal(await logs.pending(), 1);
});

// -- retries -----------------------------------------------------------------

test('a retry sends the same game_id, so the server can tell it apart',
     async () => {
  // Ratings are cumulative and never recomputed: a game counted twice moves
  // every word in it twice, and nothing later puts it back.
  serve(() => reply(503, null));
  const entry = log();
  await logs.finish(entry);
  await settle();

  serve(() => reply(202, null));
  await logs.flush();
  assert.deepEqual(sent(), [entry.game_id]);
  assert.equal(await logs.pending(), 0);
});

test('a queued game survives with its words intact', async () => {
  setOnline(false);
  const entry = log(4);
  await logs.finish(entry);
  const [queued] = [...stored('outbox').values()];
  assert.deepEqual(queued.attempts, entry.attempts);
  assert.equal(queued.version, '2.0');
});

test('an evening of games all reach the server', async () => {
  setOnline(false);
  const ids = [];
  for (let game = 0; game < 5; game++) {
    const entry = log(2);
    ids.push(entry.game_id);
    await logs.finish(entry);
  }
  assert.equal(await logs.pending(), 5);

  setOnline(true);
  await logs.flush();
  assert.equal(await logs.pending(), 0);
  assert.deepEqual(sent().slice().sort(), ids.slice().sort());
});
