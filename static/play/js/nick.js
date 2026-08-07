// Надрывы — the difficulty of a deathmatch word, written on its paper.
//
// The band the words are drawn from is a number between 0 and 100, and no
// player has ever had any idea what it means. It used to be printed in the
// corner as "сложность 21–30" and blinked when it moved, which is a caption
// on a screen whose whole point is that the eye is on the word.
//
// So the level is the number of tears in the slip instead: the first band is
// clean paper and every escalation cuts one more into it. What the player is
// asked to perceive is a COUNT — few against many — and not a percentage
// change in roughness, which no eye resolves. It also gives the escalation a
// second home. The slip that arrives after the band moves does not merely
// look worse; it has one more slash in it than the last one did.
//
// The slip's own outline is untouched. hat.css cuts five of them (--rip-1 …
// --rip-5) and they are the site's paper, not this mode's; this takes one of
// those polygons and splices slits into it, so a level-1 deathmatch slip is
// byte for byte the slip the rest of the app draws.

/** How deep a slit goes, as a share of the slip's short side. */
const DEPTH = 0.19;

/** Half a slit's mouth, in px, before the per-slit jitter below. */
const MOUTH = 11;


/**
 * The inward normal of a heading, which is how a slit knows which way is into
 * the paper without being told which side of the box it is on — and what lets
 * this work on an arbitrary polygon rather than on four straight edges.
 *
 * The rips run clockwise in screen coordinates (y down): --rip-1 goes left to
 * right along the top, down the right, back along the bottom, up the left.
 * For that winding the inward normal of a heading (dx, dy) is (-dy, dx) —
 * check it on the top edge, where the heading is (1, 0) and the answer is
 * (0, 1), pointing down into the paper.
 */
function inward(dx, dy) {
  const len = Math.hypot(dx, dy) || 1;
  return [-dy / len, dx / len];
}

/** xorshift — the same word must be cut the same way every time it is drawn,
 *  or a re-layout (a phone turning over) reshuffles the paper mid-round. */
function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => {
    s ^= s << 13; s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5;  s >>>= 0;
    return s / 4294967296;
  };
}

/** `polygon(a% b%, c% d%, …)` -> [[a, b], [c, d], …], in percent. */
export function parse(polygon) {
  const inside = polygon.slice(polygon.indexOf('(') + 1, polygon.lastIndexOf(')'));
  return inside.split(',').map((pair) => pair.trim().split(/\s+/).map(parseFloat));
}

/**
 * `rip` with `count` slits cut into it, for a slip measured w×h.
 *
 * Percentages in a clip-path are per axis, and a word slip is far from
 * square, so every length here is worked in px against the measured box and
 * only converted back at the end. The same 3% is a different bite on the top
 * edge than on the side.
 */
export function nicked(rip, w, h, count, seed) {
  const pts = parse(rip).map(([x, y]) => [x * w / 100, y * h / 100]);
  if (!count) return rip;

  const rand = rng(seed);
  const depth = Math.min(w, h) * DEPTH;

  // Walk the outline once and keep each vertex's distance along it, so a slit
  // can be placed by arc length and land in the right segment whatever shape
  // the polygon is.
  const arc = [0];
  for (let i = 1; i <= pts.length; i++) {
    const [ax, ay] = pts[i - 1];
    const [bx, by] = pts[i % pts.length];
    arc.push(arc[i - 1] + Math.hypot(bx - ax, by - ay));
  }
  const total = arc[pts.length];

  /** The point at distance `d` along the outline, and the segment it is on. */
  const walk = (d) => {
    const at = ((d % total) + total) % total;
    let i = 1;
    while (i < pts.length && arc[i] < at) i += 1;
    const [ax, ay] = pts[i - 1];
    const [bx, by] = pts[i % pts.length];
    const span = arc[i] - arc[i - 1] || 1;
    const k = (at - arc[i - 1]) / span;
    return { x: ax + (bx - ax) * k, y: ay + (by - ay) * k, dx: bx - ax, dy: by - ay };
  };

  // Where the slits go: one per slot of a jittered lattice around the
  // outline, kept clear of the seam where it closes so no mouth has to wrap
  // from the end of the walk back to its start.
  //
  // This began as rejection sampling — try ten spots, keep the one furthest
  // from its neighbours — and that is a preference rather than a guarantee.
  // On a crowded outline the best of ten can still land a pixel from its
  // neighbour, and two mouths that overlap interleave their vertices: the
  // walk goes forward, back, forward, and the polygon crosses itself, folding
  // away half the slip. It happened for some seeds and not others, which is
  // the kind of bug that ships. A lattice makes the separation structural
  // instead of probable, and spreads the tears more evenly besides — which is
  // what a count wants.
  // Corners are excluded, and arc length is why. Separation is measured along
  // the outline, but what has to hold is spatial: two slits either side of a
  // corner can sit 30px apart along the paper's edge and still point their
  // apexes into the same wedge, and their triangles then cross even though
  // neither mouth touches the other. Around a corner, arc distance stops
  // standing in for distance. So the lattice is laid over the parts of the
  // outline that run reasonably straight, and the turns are left alone —
  // which also puts the tears along the edges, where they read as tears.
  const KEEP = 26;                      // px of outline kept clear either side
  const sharp = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[(i - 1 + pts.length) % pts.length], b = pts[i];
    const c = pts[(i + 1) % pts.length];
    const d = Math.atan2(c[1] - b[1], c[0] - b[0]) - Math.atan2(b[1] - a[1], b[0] - a[0]);
    if (Math.abs(Math.atan2(Math.sin(d), Math.cos(d))) > 0.7) sharp.push(arc[i]);
  }

  // What is left once the turns and the closing seam are taken out, as a list
  // of runs the lattice can be laid along end to end.
  const margin = MOUTH * 1.5 + 1;
  const blocked = sharp
    .map((at) => [at - KEEP, at + KEEP])
    .concat([[-Infinity, margin], [total - margin, Infinity]])
    .sort((x, y) => x[0] - y[0]);
  const runs = [];
  let edge = -Infinity;
  for (const [lo, hi] of blocked) {
    if (lo > edge && edge > -Infinity) runs.push([edge, lo]);
    edge = Math.max(edge, hi);
  }
  const free = runs.reduce((sum, [lo, hi]) => sum + (hi - lo), 0);

  /** A position in "free arc" back to a real distance along the outline. */
  const unfold = (u) => {
    let left = Math.min(Math.max(u, 0), free);
    for (const [lo, hi] of runs) {
      if (left <= hi - lo) return lo + left;
      left -= hi - lo;
    }
    return runs.length ? runs[runs.length - 1][1] : margin;
  };

  const slot = free / count;
  const cuts = [];
  for (let n = 0; n < count; n++) {
    cuts.push({
      at: unfold(slot * (n + 0.5) + (rand() - 0.5) * slot * 0.6),
      // Asymmetric on purpose — paper does not tear down the middle.
      l: MOUTH * (0.5 + rand()),
      r: MOUTH * (0.5 + rand()),
      d: depth * (0.75 + rand() * 0.4),
    });
  }

  // The lattice leaves at least 0.4 of a slot between neighbours; each slit
  // may take at most half of whatever that is, so mouths can meet but never
  // cross. On a slip this size the clamp only ever binds at the top of the
  // ladder, where the slots are narrowest.
  for (let i = 0; i < cuts.length; i++) {
    const before = i > 0 ? (cuts[i].at - cuts[i - 1].at) / 2 : cuts[i].at;
    const after = i < cuts.length - 1
      ? (cuts[i + 1].at - cuts[i].at) / 2
      : total - cuts[i].at;
    cuts[i].l = Math.min(cuts[i].l, before - 0.5);
    cuts[i].r = Math.min(cuts[i].r, after - 0.5);
  }

  // Rebuild the outline: original vertices in order, with each slit's three
  // points spliced in at its arc position. Vertices that fall inside a slit's
  // mouth are dropped — left in, the outline's own wander would cross back
  // over the slit and the cut would come out as a lumpy notch.
  const out = [];
  const swallowed = (d) =>
    cuts.some((c) => d > c.at - c.l && d < c.at + c.r);

  // Ordered by where each slit's mouth OPENS, not by its apex. Keyed on the
  // apex, a slit whose mouth began before the previous original vertex was
  // emitted after it, putting one vertex behind another and folding the
  // outline at that point.
  let next = 0;
  const emitCutsBefore = (d) => {
    while (next < cuts.length && cuts[next].at - cuts[next].l <= d) {
      const c = cuts[next];
      const a = walk(c.at - c.l);
      const b = walk(c.at + c.r);

      // The apex hangs off the CHORD between the two mouth points, not off
      // the outline segment the apex happens to sit on. Perpendicular to the
      // segment, a slit whose mouth straddled a corner aimed along one of the
      // two edges and overshot past its own far mouth point: the walk went
      // forward, back, forward, and the outline folded — plus the apex could
      // drift a hair outside the box. Off the chord it is a triangle standing
      // on its own base, which cannot fold however sharply the paper turns
      // underneath it. Struck at l/(l+r) along that base rather than at its
      // middle, which is what keeps the lean the two mouth widths asked for.
      const k = c.l / (c.l + c.r);
      const [nx, ny] = inward(b.x - a.x, b.y - a.y);
      out.push([a.x, a.y],
               [a.x + (b.x - a.x) * k + nx * c.d, a.y + (b.y - a.y) * k + ny * c.d],
               [b.x, b.y]);
      next += 1;
    }
  };

  for (let i = 0; i < pts.length; i++) {
    emitCutsBefore(arc[i]);
    if (!swallowed(arc[i])) out.push(pts[i]);
  }
  emitCutsBefore(total);

  // Rounded to hundredths of a percent, which on a 300px slip is 0.03px — so
  // two points a hair apart can round onto each other and leave a zero-length
  // edge in the string. Harmless to draw and pure noise to read, so they are
  // dropped here rather than shipped.
  const seen = [];
  for (const [x, y] of out) {
    const at = `${(x / w * 100).toFixed(2)}% ${(y / h * 100).toFixed(2)}%`;
    if (at !== seen[seen.length - 1]) seen.push(at);
  }
  if (seen.length > 1 && seen[0] === seen[seen.length - 1]) seen.pop();
  return `polygon(${seen.join(', ')})`;
}
