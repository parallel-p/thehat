// nick.js — the slits that carry a deathmatch word's difficulty.
//
// The count is the whole signal: a player reads "more tears than the last
// one", not a depth or a roughness. So what is worth pinning down is that the
// level really does produce that many separable slits, that they stay inside
// the paper, and that the same word is cut the same way twice — a slip
// recut on a phone turning over must not reshuffle mid-round.

import { test } from 'node:test';
import assert from 'node:assert/strict';

const { nicked, parse } = await import('../../static/play/js/nick.js');

// The five rips from hat.css verbatim — the app cycles four of them across
// its slips, and the corner detection in nick.js reads the polygon, so every
// one of them is a different input to it.
const RIPS = [
  'polygon(0% 2.2%, 11.1% 2%, 22.2% 4.2%, 33.3% 4.3%, 44.4% 3.6%, 55.6% 1.5%, 66.7% 1.8%, 77.8% 1.8%, 88.9% 4.5%, 100% 4.4%, 99.6% 33.3%, 99.4% 66.7%, 100% 96.2%, 88.9% 99.1%, 77.8% 99.2%, 66.7% 95.9%, 55.6% 97.2%, 44.4% 95.4%, 33.3% 99.1%, 22.2% 98%, 11.1% 96.3%, 0% 97.4%, 0.1% 66.7%, 0.1% 33.3%)',
  'polygon(0% 2%, 12.5% 0.3%, 25% 3%, 37.5% 4.3%, 50% 2.5%, 62.5% 3.1%, 75% 1.6%, 87.5% 4.6%, 100% 4.4%, 98.3% 25%, 99.9% 50%, 98.7% 75%, 100% 97.6%, 87.5% 98.8%, 75% 98.5%, 62.5% 98.5%, 50% 99.7%, 37.5% 95.6%, 25% 97.2%, 12.5% 96.6%, 0% 97.2%, 0.5% 75%, 0.6% 50%, 1.2% 25%)',
  'polygon(0% 1%, 9.1% 1.6%, 18.2% 1.5%, 27.3% 2.3%, 36.4% 1%, 45.5% 1.3%, 54.5% 0.8%, 63.6% 4.1%, 72.7% 4.1%, 81.8% 2.4%, 90.9% 4.3%, 100% 2.2%, 99.3% 33.3%, 99.1% 66.7%, 100% 99.9%, 90.9% 99.7%, 81.8% 99.5%, 72.7% 95.7%, 63.6% 96.5%, 54.5% 96.9%, 45.5% 96.8%, 36.4% 95.3%, 27.3% 97.6%, 18.2% 98.7%, 9.1% 99.1%, 0% 98.9%, 1.6% 66.7%, 0.1% 33.3%)',
  'polygon(0% 4%, 14.3% 4.3%, 28.6% 2.5%, 42.9% 4%, 57.1% 0.1%, 71.4% 3.9%, 85.7% 3.2%, 100% 2.2%, 98.7% 33.3%, 99.5% 66.7%, 100% 98%, 85.7% 96%, 71.4% 95%, 57.1% 95.2%, 42.9% 96.3%, 28.6% 96.8%, 14.3% 99.2%, 0% 96.2%, 0% 66.7%, 0.4% 33.3%)',
  'polygon(0% 2.2%, 10% 1.8%, 20% 3.5%, 30% 2.3%, 40% 1.1%, 50% 3.4%, 60% 3.8%, 70% 3.6%, 80% 3.1%, 90% 0.2%, 100% 1.4%, 98.3% 25%, 98.7% 50%, 98.5% 75%, 100% 97.7%, 90% 97.3%, 80% 97.1%, 70% 99.1%, 60% 98.3%, 50% 98%, 40% 95.3%, 30% 96.8%, 20% 96.9%, 10% 97%, 0% 96.2%, 1.8% 75%, 0.3% 50%, 0.2% 25%)',
];
const RIP = RIPS[0];

const W = 300, H = 112;                 // a slip at the size the round draws

/** How far a point sits inside the box, in px, negative if it is outside. */
const inset = ([x, y]) =>
  Math.min(x * W / 100, y * H / 100, (100 - x) * W / 100, (100 - y) * H / 100);

test('the first band is the app\'s own paper, untouched', () => {
  assert.equal(nicked(RIP, W, H, 0, 1), RIP);
});

test('each level adds one slit, and each slit three vertices', () => {
  const base = parse(RIP).length;
  for (let level = 0; level < 15; level++) {
    const pts = parse(nicked(RIP, W, H, level, level + 1)).length;
    // Three per slit, less any original vertex swallowed by a mouth.
    assert.ok(pts >= base + level * 3 - level * 2 && pts <= base + level * 3,
      `level ${level}: ${pts} vertices against a base of ${base}`);
  }
});

test('a slit is a spike, not a dent', () => {
  // The DEEPEST point of a nicked outline has to be markedly deeper than
  // anything the plain rip reaches, or the slits are not reading as cuts.
  // (Deepest is the max inset; the min is 0 on both, because a slip's outline
  // touches its own box.)
  const plain = Math.max(...parse(RIP).map(inset));
  const deep = Math.max(...parse(nicked(RIP, W, H, 8, 7)).map(inset));
  assert.ok(deep > plain + 8, `nicked reached ${deep.toFixed(1)}px, plain ${plain.toFixed(1)}px`);
});

test('nothing is cut outside the paper', () => {
  for (const rip of RIPS) {
    for (let seed = 1; seed <= 40; seed++) {
      for (const [x, y] of parse(nicked(rip, W, H, 14, seed))) {
        assert.ok(x >= -0.01 && x <= 100.01 && y >= -0.01 && y <= 100.01,
          `seed ${seed}: point ${x}% ${y}% is off the slip`);
      }
    }
  }
});

test('no slit reaches more than a third of the way in', () => {
  // The ink lives in the middle. A slit deeper than this would cross it
  // whatever padding the slip is given.
  for (const rip of RIPS) {
    for (let seed = 1; seed <= 40; seed++) {
      for (const p of parse(nicked(rip, W, H, 14, seed))) {
        assert.ok(inset(p) < Math.min(W, H) / 3,
          `seed ${seed}: a cut reached ${inset(p).toFixed(1)}px in`);
      }
    }
  }
});

test('the same word is cut the same way twice', () => {
  assert.equal(nicked(RIP, W, H, 9, 42), nicked(RIP, W, H, 9, 42));
  assert.notEqual(nicked(RIP, W, H, 9, 42), nicked(RIP, W, H, 9, 43));
});

/** Every pair of non-adjacent edges, checked for a proper crossing.
 *
 *  This started life as a turning-number check, which is neater to write and
 *  wrong: the turn at a zero-length edge is atan2(0, 0), and the output
 *  rounds to hundredths of a percent, so two points a hair apart round onto
 *  each other and the number collapses on a polygon that is perfectly fine.
 *  It reported a fold at 13 nicks that a crossing test says is not there.
 *  Self-intersection is the property that actually matters, so test that. */
function crosses(polygon) {
  const p = parse(polygon).map(([x, y]) => [x * W / 100, y * H / 100]);
  const side = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  // Strictly opposite signs on both, which is a proper crossing. Written as
  // `(d1 > 0) !== (d2 > 0)` it counts d == 0 as a side and cries crossing at
  // every collinear touch — and a slip's top edge is a long row of very nearly
  // collinear points, so it reported tangles all over an untangled polygon.
  const hit = (p1, p2, p3, p4) => {
    const d1 = side(p3, p4, p1), d2 = side(p3, p4, p2);
    const d3 = side(p1, p2, p3), d4 = side(p1, p2, p4);
    return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0))
        && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0));
  };
  const n = p.length;
  for (let i = 0; i < n; i++) {
    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue;         // adjacent round the seam
      if (hit(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n])) return `${i}×${j}`;
    }
  }
  return null;
}

test('the outline never crosses itself', () => {
  // Swept rather than spot-checked, because the first two versions of this
  // failed on some seeds and passed on others. Slits placed closer than one
  // mouth is wide interleaved their vertices; then slits whose mouth straddled
  // a corner aimed their apex along one of the two edges and overshot past
  // their own far mouth point. Both folded the outline and clipped away part
  // of the slip — for some words only, which is the kind of bug that ships.
  for (const [variant, rip] of RIPS.entries()) {
    for (let count = 1; count <= 14; count++) {
      for (let seed = 1; seed <= 60; seed++) {
        const at = crosses(nicked(rip, W, H, count, seed));
        assert.equal(at, null,
          `rip-${variant + 1}, ${count} nicks, seed ${seed}: edges ${at} cross`);
      }
    }
  }
});

test('cutting paper only ever removes it', () => {
  // Signed area, which a fold would inflate as readily as shrink.
  const areaOf = (polygon) => {
    const p = parse(polygon).map(([x, y]) => [x * W / 100, y * H / 100]);
    let a = 0;
    for (let i = 0; i < p.length; i++) {
      const [x1, y1] = p[i], [x2, y2] = p[(i + 1) % p.length];
      a += x1 * y2 - x2 * y1;
    }
    return Math.abs(a / 2);
  };
  const plain = areaOf(RIP);
  let last = plain;
  for (let count = 1; count <= 14; count++) {
    const area = areaOf(nicked(RIP, W, H, count, 11));
    assert.ok(area < last, `${count} nicks: ${area.toFixed(0)} is not less than ${last.toFixed(0)}`);
    assert.ok(area > plain * 0.7, `${count} nicks ate ${(100 - area / plain * 100).toFixed(0)}% of the slip`);
    last = area;
  }
});
