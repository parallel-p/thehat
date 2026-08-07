// Timers that survive a locked screen — clock.js.
//
// The module exists for one claim: setInterval is throttled in a background
// tab and stops outright when an iOS screen locks, so a clock that counts
// ticks loses time exactly when a round is being played. Everything here is
// derived from Date.now() against a start stamp instead. That claim is worth a
// test because the failure is invisible on a desk — it only shows up on a
// phone that went dark mid-turn, and then it shows up as a round that lasted
// twice as long as it said.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { install, fakeClock } from './helpers/browser.mjs';

install();

const { ticker, keepAwake } = await import('../../static/play/js/clock.js');

/** Wait for a real interval or two to fire. */
const tickOrTwo = () => new Promise(resolve => setTimeout(resolve, 60));

test('elapsed time is measured, never accumulated', async () => {
  const clock = fakeClock();
  const seen = [];
  const running = ticker(ms => seen.push(ms), 10);
  try {
    // The screen locks for half a minute: no intervals fire, and then the
    // phone comes back. A clock counting its own ticks would report the two or
    // three it managed; this one reports the half minute that passed.
    clock.advance(30_000);
    await tickOrTwo();
    assert.ok(seen.length > 0, 'the ticker never fired');
    assert.equal(seen[seen.length - 1], 30_000);
    assert.equal(running.elapsed(), 30_000);
  } finally {
    running.stop();
    clock.restore();
  }
});

test('elapsed() can be read without waiting for a tick', () => {
  const clock = fakeClock();
  const running = ticker(() => {}, 10_000);
  try {
    clock.advance(4321);
    assert.equal(running.elapsed(), 4321);
  } finally {
    running.stop();
    clock.restore();
  }
});

test('a stopped ticker stops', async () => {
  const clock = fakeClock();
  let ticks = 0;
  const running = ticker(() => { ticks += 1; }, 10);
  try {
    await tickOrTwo();
    assert.ok(ticks > 0);
    running.stop();
    const after = ticks;
    clock.advance(10_000);
    await tickOrTwo();
    assert.equal(ticks, after, 'a stopped ticker went on ticking');
  } finally {
    running.stop();
    clock.restore();
  }
});

test('stopping twice is stopping once', () => {
  const running = ticker(() => {}, 10_000);
  running.stop();
  assert.doesNotThrow(() => running.stop());
});

test('two tickers keep their own start stamps', async () => {
  const clock = fakeClock();
  const first = ticker(() => {}, 10_000);
  clock.advance(5_000);
  const second = ticker(() => {}, 10_000);
  clock.advance(2_000);
  try {
    assert.equal(first.elapsed(), 7_000);
    assert.equal(second.elapsed(), 2_000);
  } finally {
    first.stop();
    second.stop();
    clock.restore();
  }
});

test('keeping the screen awake is never fatal where it is not supported', () => {
  // Below Safari 16.4 there is no wake lock and no fallback worth having; a
  // 20-second round usually beats the display timeout anyway.
  assert.ok(!('wakeLock' in navigator));
  assert.doesNotThrow(() => keepAwake(true));
  assert.doesNotThrow(() => keepAwake(false));
});
