// How a word is chosen — dictionary.js, over the real db.js.
//
// Two things here decide whether the game feels right, and neither is visible
// on any screen: the shape of the sampling distribution, and the ring that
// stops a word coming round again. The file's own header says as much. The
// statistical assertions below are deliberately loose — they are there to
// catch a formula that is wrong, not to pin a seed.

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

import { install, serve, reply, stored, wipe, calls }
  from './helpers/browser.mjs';

install();

const dict = await import('../../static/play/js/dictionary.js');
const db = await import('../../static/play/js/db.js');

// Roughly the shape of the real thing: about twelve thousand words, evenly
// spread. Tests that want a bucket to run dry ask for more words than a bucket
// holds rather than shrinking the dictionary, so the sampling tests are never
// secretly measuring the exhaustion fallback instead.
const PER_BUCKET = 120;

/** A dictionary with `per` words in every one of the 101 buckets. */
function corpus(per = PER_BUCKET) {
  const words = [];
  for (let diff = 0; diff <= 100; diff++) {
    for (let n = 0; n < per; n++) words.push({ word: `w${diff}_${n}`, diff });
  }
  return words;
}

/** The bucket a word came from, read back off its name. */
const bucketOf = word => Number(word.split('_')[0].slice(1));

const mean = xs => xs.reduce((a, b) => a + b, 0) / xs.length;

function stdev(xs) {
  const m = mean(xs);
  return Math.sqrt(mean(xs.map(x => (x - m) ** 2)));
}

// Every test starts from a cold store and the full corpus. A test that wants
// a different dictionary wipes and re-serves for itself; putting the default
// back here is what keeps one test's network from being the next one's.
beforeEach(async () => {
  serve(() => reply(200, corpus(), { ETag: '"v1"' }));
  wipe();
  await dict.load();
});

// -- loading -----------------------------------------------------------------

test('a first run downloads the dictionary and keeps all 101 buckets', () => {
  const buckets = stored('buckets');
  assert.equal(buckets.size, 101);
  assert.deepEqual([...buckets.keys()], [...Array(101).keys()]);
  assert.ok(dict.ready());
});

test('a retired word is dropped rather than played', async () => {
  wipe();
  serve(() => reply(200, [
    { word: 'живое', diff: 5 },
    { word: 'снятое', diff: 5, tags: '-deleted' },
  ], { ETag: '"v2"' }));
  await dict.load();
  assert.deepEqual(stored('buckets').get(5), ['живое']);
});

test('a word outside 0..100 is dropped rather than misfiled', async () => {
  wipe();
  serve(() => reply(200, [
    { word: 'нормальное', diff: 100 },
    { word: 'слишком', diff: 101 },
    { word: 'отрицательное', diff: -1 },
  ], { ETag: '"v3"' }));
  await dict.load();
  const kept = [...stored('buckets').values()].flat();
  assert.deepEqual(kept, ['нормальное']);
});

test('a stored dictionary is used without waiting for the network', async () => {
  // Second load: the store is warm, so the network is consulted in the
  // background and its answer must not be needed to play.
  serve(() => { throw new Error('offline'); });
  await dict.load();
  assert.ok(dict.ready());
  const words = await dict.getWords(5, 50, 15);
  assert.equal(words.length, 5);
});

test('a revalidation sends the stored etag and a 304 changes nothing', async () => {
  const before = stored('buckets').get(50);
  // Asserted after the fact, not inside the handler: revalidate() swallows
  // everything it throws, so a throw in there would pass silently.
  serve(() => reply(304, null));
  await dict.load();
  // revalidate() is deliberately not awaited by load(); let it land.
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(calls.length, 1, 'the network was never consulted');
  assert.equal(calls[0].options.headers['If-None-Match'], '"v1"');
  assert.deepEqual(stored('buckets').get(50).slice().sort(),
                   before.slice().sort());
});

// -- the hat's sampling ------------------------------------------------------

test('a hat is the size asked for and holds no word twice', async () => {
  const hat = await dict.getWords(120, 30, 15);
  assert.equal(hat.length, 120);
  assert.equal(new Set(hat).size, 120);
});

test('words land around the difficulty, spread by a third of the dispersion',
     async () => {
  // beret draws from Normal(difficulty, dispersion² / 9): σ is a third of the
  // dispersion setting, so the default 15 means σ = 5. Getting this wrong is
  // invisible on every screen and changes the whole feel of a game.
  const buckets = (await dict.getWords(600, 50, 15)).map(bucketOf);
  assert.ok(Math.abs(mean(buckets) - 50) < 2,
    `centred on ${mean(buckets).toFixed(1)}, not 50`);
  assert.ok(Math.abs(stdev(buckets) - 5) < 1.2,
    `σ is ${stdev(buckets).toFixed(1)}, not 5`);
});

test('a wider dispersion is a wider spread, not a different centre', async () => {
  const narrow = stdev((await dict.getWords(600, 50, 6)).map(bucketOf));
  const wide = stdev((await dict.getWords(600, 50, 30)).map(bucketOf));
  assert.ok(wide > narrow * 2, `${wide.toFixed(1)} is not wider than ${narrow.toFixed(1)}`);
});

test('no dispersion means one bucket', async () => {
  const buckets = (await dict.getWords(30, 42, 0)).map(bucketOf);
  assert.deepEqual([...new Set(buckets)], [42]);
});

test('the ends of the scale stay on the scale', async () => {
  for (const difficulty of [0, 100]) {
    const buckets = (await dict.getWords(200, difficulty, 15)).map(bucketOf);
    assert.ok(Math.min(...buckets) >= 0 && Math.max(...buckets) <= 100,
      `difficulty ${difficulty} drew from ${Math.min(...buckets)}..${Math.max(...buckets)}`);
  }
});

test('resampling at the edge does not pile up on one bucket', async () => {
  // Clamping instead of resampling would put every out-of-range draw — at
  // difficulty 0 that is half of them — into bucket 0, where resampling leaves
  // about a sixth. The hat has to stay well inside what one bucket holds, or
  // the bucket running dry caps the count and hides the difference.
  const draws = Math.floor(PER_BUCKET * 0.8);
  const buckets = (await dict.getWords(draws, 0, 15)).map(bucketOf);
  const atZero = buckets.filter(b => b === 0).length;
  assert.ok(atZero < draws * 0.35,
    `${Math.round(100 * atZero / draws)}% of the hat came from bucket 0`);
});

// -- the deathmatch's band ---------------------------------------------------

test('a band draws only from inside itself', async () => {
  const buckets = (await dict.getWordsInBand(200, 55, 60)).map(bucketOf);
  assert.ok(buckets.every(b => b >= 55 && b <= 60),
    `drew ${Math.min(...buckets)}..${Math.max(...buckets)} for the band 55–60`);
});

test('a band is walked evenly, not favoured in the middle', async () => {
  // A normal draw centred on the band would pile up on 57–58, which for a band
  // of six buckets is most of it. 300 words out of the band's 720, so this is
  // the sampling being measured and not the bottom of the barrel.
  const draws = 300;
  const buckets = (await dict.getWordsInBand(draws, 55, 60)).map(bucketOf);
  const expected = draws / 6;
  for (const bucket of [55, 56, 57, 58, 59, 60]) {
    const count = buckets.filter(x => x === bucket).length;
    assert.ok(Math.abs(count - expected) < expected * 0.45,
      `bucket ${bucket} got ${count} of ${draws}, not about ${expected}`);
  }
});

test('a band of one bucket is that bucket', async () => {
  const buckets = (await dict.getWordsInBand(20, 7, 7)).map(bucketOf);
  assert.deepEqual([...new Set(buckets)], [7]);
});

// -- the ring ----------------------------------------------------------------

test('the ring is written, and remembers across calls', async () => {
  const first = await dict.getWords(10, 50, 3);
  const ring = await db.get('meta', 'ring');
  assert.equal(ring.at, 10);
  assert.deepEqual(ring.words.slice(0, 10).sort(), [...first].sort());

  const second = await dict.getWords(10, 50, 3);
  assert.equal((await db.get('meta', 'ring')).at, 20);
  assert.deepEqual(first.filter(word => second.includes(word)), [],
    'a word came back one game later');
});

test('a word does not come round again for a thousand words', async () => {
  const seen = [];
  for (let game = 0; game < 12; game++) {
    seen.push(...await dict.getWords(60, 50, 15));
  }
  assert.equal(new Set(seen).size, seen.length,
    'the ring let a word repeat inside its own length');
});

// Dispersion 0 means bucket 50 and nothing else, so a hat larger than the
// bucket can only be filled by the fallback — which is the point of these two.
const OVERDRAW = PER_BUCKET + 30;

test('a hat still fills, and still holds no duplicate, once the band is spent',
     async () => {
  // The ring is a nicety; a hat holding the same word twice is a broken game —
  // the players meet it once, guess it, and meet it again — so the fallback
  // gives up the ring and keeps uniqueness instead.
  const hat = await dict.getWords(OVERDRAW, 50, 0);
  assert.equal(hat.length, OVERDRAW);
  assert.equal(new Set(hat).size, OVERDRAW);
  assert.ok(!hat.includes('—'), 'the hat fell through to the empty placeholder');
});

test('the fallback looks outward from the difficulty it was given', async () => {
  const strayed = (await dict.getWords(OVERDRAW, 50, 0))
    .map(bucketOf).filter(b => b !== 50);
  const furthest = Math.max(...strayed.map(b => Math.abs(b - 50)));
  assert.ok(strayed.length > 0,
    `bucket 50 cannot have held ${OVERDRAW} of ${PER_BUCKET} words`);
  assert.ok(furthest <= 3, `the fallback wandered ${furthest} buckets away`);
});
