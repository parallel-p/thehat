// Game logs, and getting them to the server eventually.
//
// The format is a contract, not a convenience: app/stats.py:parse_log_v2 turns
// these into word ratings, and it is unforgiving in ways that are invisible
// from here —
//
//   * `outcome` is 'guessed', 'failed', or ABSENT. Absent means the round ended
//     with the word still in hand; it is not the same as failed and must not be
//     filled in.
//   * time + extra_time outside 500ms..5min silently drops the word.
//   * a game where fewer than half the hat's words were attempted, or where
//     more than half the attempts took under 2s, is thrown away whole.
//   * time_zone_offset is added server-side before the hour-of-week is taken,
//     which is what makes the statistics pages show each player's own evening.

import * as db from './db.js';

const ENDPOINT = '/api/v2/game/log';

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = crypto.getRandomValues(new Uint8Array(1))[0] % 16;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

/** A log the server will accept, with a stable id so a retry is idempotent. */
export function newLog() {
  return {
    version: '2.0',
    game_id: uuid(),
    time_zone_offset: -new Date().getTimezoneOffset() * 60 * 1000,
    start_timestamp: Date.now(),
    attempts: [],
  };
}

/**
 * One word, as the parser wants it.
 *
 * `outcome` is left off entirely when the word went back in the hat.
 */
export function attempt({ word, from, to, time, extraTime = 0, outcome = null }) {
  const entry = {
    word,
    from,
    to,
    time: Math.round(time),
    extra_time: Math.round(extraTime),
  };
  if (outcome) entry.outcome = outcome;
  return entry;
}

/**
 * Queue a finished game for the server. True when there was one to queue.
 *
 * A log with no attempts is not a game that was played, it is somebody who
 * started one and changed their mind — and since «Закончить игру» is the only
 * way off the handoff screen, that is the ordinary way to back out of a game,
 * not an edge case. The parser does not catch it: `2 * len(seen_words_time) <
 * len(words_orig)` is `0 < 0` for a log of nothing, so an empty game passed
 * every check and put a tick on TotalStatistics.games — the number the landing
 * page leads with. Refused here, where the log's own shape is known, rather
 * than in either mode: both of them end this way.
 */
export async function finish(log) {
  if (!log.attempts.length) return false;
  log.end_timestamp = Date.now();
  await db.put('outbox', log.game_id, log);
  flush();                        // deliberately not awaited
  return true;
}

let flushing = false;

/**
 * Send everything queued.
 *
 * A log is deleted only on a 2xx. beret checked for 201 while the server
 * answers 202, so every game it ever played was queued as failed and sent a
 * second time — which is half of why the server now takes a game_id.
 */
export async function flush() {
  if (flushing || !navigator.onLine) return;
  flushing = true;
  try {
    const ids = await db.keys('outbox');
    for (const id of ids) {
      const log = await db.get('outbox', id);
      if (!log) continue;
      let response;
      try {
        response = await fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(log),
        });
      } catch (_) {
        break;                    // network gone; the rest can wait
      }
      if (response.ok) {
        await db.del('outbox', id);
      } else if (response.status >= 400 && response.status < 500) {
        // The server will never take this one. Keeping it would mean retrying
        // forever, so drop it rather than wedge the queue behind it.
        await db.del('outbox', id);
      } else {
        break;                    // 5xx: try again later, in order
      }
    }
  } finally {
    flushing = false;
  }
}

export async function pending() {
  const ids = await db.keys('outbox');
  return ids ? ids.length : 0;
}
