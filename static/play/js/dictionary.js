// The word list, and how a word is chosen.
//
// Ported from beret's lib/dictionary.dart. The two things that must match are
// the shape of the sampling distribution and the repeat-avoidance ring — get
// either wrong and the game feels different even though every screen looks
// right.

import * as db from './db.js';

const URL = '/api/v2/dictionary/ru';
const BUCKETS = 101;              // difficulty 0..100, inclusive
const RING = 1000;                // words remembered to avoid repeats

let buckets = null;               // [ [word, ...] x 101 ], shuffled
let cursors = null;               // read position per bucket

/** Fisher–Yates. */
function shuffle(list) {
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}

function toBuckets(words) {
  const out = Array.from({ length: BUCKETS }, () => []);
  for (const entry of words) {
    // '-deleted' is how the dictionary generator retires a word without
    // removing it, so it must be dropped here rather than played.
    if (entry.tags === '-deleted') continue;
    const index = entry.diff;
    if (index >= 0 && index < BUCKETS) out[index].push(entry.word);
  }
  return out;
}

async function store(words, etag) {
  const grouped = toBuckets(words);
  await db.putMany('buckets', grouped.map((list, i) => [i, list]));
  await db.put('meta', 'etag', etag || null);
  return grouped;
}

async function fromDb() {
  const stored = await db.all('buckets');
  if (!stored || stored.length !== BUCKETS) return null;
  return stored;
}

async function download(etag) {
  const headers = {};
  if (etag) headers['If-None-Match'] = etag;
  const response = await fetch(URL, { headers, cache: 'no-cache' });
  if (response.status === 304) return null;
  if (!response.ok) throw new Error('dictionary ' + response.status);
  return { words: await response.json(), etag: response.headers.get('ETag') };
}

/**
 * Make the dictionary usable, offline if it has to be.
 *
 * Stored copy first, so a cold start with no network is instant and silent;
 * the network is then consulted in the background and a new list takes effect
 * on the next load, never in the middle of a game.
 */
export async function load() {
  buckets = await fromDb();
  cursors = new Array(BUCKETS).fill(0);

  if (buckets) {
    for (const list of buckets) shuffle(list);
    revalidate();                       // deliberately not awaited
    return;
  }

  const fresh = await download(null);   // nothing stored: this one is required
  buckets = await store(fresh.words, fresh.etag);
  for (const list of buckets) shuffle(list);
}

async function revalidate() {
  try {
    const etag = await db.get('meta', 'etag');
    const fresh = await download(etag);
    if (fresh) await store(fresh.words, fresh.etag);
  } catch (_) {
    // Offline, or the server is unhappy. The stored copy is still good.
  }
}

/** Standard normal, Box–Muller. */
function gauss() {
  let u = 0;
  while (u === 0) u = Math.random();    // log(0) is not a number we want
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * Math.random());
}

/**
 * beret draws the bucket from Normal(difficulty, dispersion² / 9), where the
 * second argument is the variance — so the standard deviation is a third of
 * the dispersion setting, and the default of 15 means σ = 5. Resampling (as
 * opposed to clamping) is also beret's behaviour and matters at the ends of
 * the scale: clamping would pile every out-of-range draw onto bucket 0 or 100.
 */
function drawBucket(difficulty, dispersion) {
  const sigma = dispersion / 3;
  for (let attempt = 0; attempt < 100; attempt++) {
    const value = Math.round(difficulty + gauss() * sigma);
    if (value >= 0 && value < BUCKETS) return value;
  }
  return Math.min(BUCKETS - 1, Math.max(0, Math.round(difficulty)));
}

function nextFromBucket(index) {
  const list = buckets[index];
  if (!list.length) return null;
  if (cursors[index] >= list.length) {
    shuffle(list);
    cursors[index] = 0;
  }
  return list[cursors[index]++];
}

/**
 * Any word outside `avoid`, looked for outward from `difficulty`.
 *
 * The fallback when the band is exhausted. It walks whole buckets rather than
 * sampling, so it finds a word if the dictionary holds one at all — with
 * thousands of words and a hat of at most a few hundred, it always does.
 */
function unusedNear(difficulty, avoid) {
  const taken = new Set(avoid);
  const start = Math.min(BUCKETS - 1, Math.max(0, Math.round(difficulty)));
  for (let step = 0; step < BUCKETS; step++) {
    for (const index of (step === 0 ? [start] : [start - step, start + step])) {
      if (index < 0 || index >= BUCKETS) continue;
      // One pass of the bucket: nextFromBucket advances the cursor, so this
      // sees every word in it exactly once.
      for (let seen = 0; seen < buckets[index].length; seen++) {
        const candidate = nextFromBucket(index);
        if (candidate && !taken.has(candidate)) return candidate;
      }
    }
  }
  return null;
}

// How much of the ring the fallback still respects when the band has nothing
// unplayed left in it. Small: the point is only that a word does not come
// back while the last one is still on screen, or in the deathmatch, in hand.
const IMMEDIATE = 50;

/** The most recently drawn words, newest first. */
function justPlayed(ring) {
  const out = [];
  for (let step = 1; step <= Math.min(IMMEDIATE, ring.words.length); step++) {
    const at = (ring.at - step + RING) % RING;
    if (ring.words[at]) out.push(ring.words[at]);
  }
  return out;
}

async function readRing() {
  const ring = await db.get('meta', 'ring');
  return ring && Array.isArray(ring.words)
    ? ring : { words: [], at: 0 };
}

/**
 * Draw `count` words around `difficulty`.
 *
 * Recently played words are skipped: without this a short dictionary bucket
 * hands out the same word two games running, which is the single most
 * noticeable way a word game can feel cheap.
 */
export async function getWords(count, difficulty, dispersion) {
  const ring = await readRing();
  const recent = new Set(ring.words);
  const drawn = [];

  for (let i = 0; i < count; i++) {
    let word = null;
    // Bounded: a bucket can be entirely recent, and the hat still has to fill.
    for (let attempt = 0; attempt < 60 && word === null; attempt++) {
      const candidate = nextFromBucket(drawBucket(difficulty, dispersion));
      if (candidate && !recent.has(candidate) && !drawn.includes(candidate)) {
        word = candidate;
      }
    }
    if (word === null) {
      // The band has nothing unplayed left in it. Skipping recent words is a
      // nicety; a hat holding the same word twice is a broken game — the
      // players meet it once, guess it, and meet it again — so the second
      // pass gives up the ring and keeps uniqueness instead.
      word = unusedNear(difficulty, [...drawn, ...justPlayed(ring)]) || '—';
    }
    drawn.push(word);
    recent.add(word);
    ring.words[ring.at] = word;
    ring.at = (ring.at + 1) % RING;
  }

  await db.put('meta', 'ring', ring);
  return drawn;
}

export function ready() {
  return buckets !== null;
}
