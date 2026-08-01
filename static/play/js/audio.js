// The six sounds, synthesised.
//
// beret ships six wav files. Generating the equivalents from oscillators keeps
// the app free of binary assets and of the licence question that comes with
// copying someone else's, and the whole file is smaller than one of the wavs.
//
// iOS will not make a sound until an AudioContext has been resumed inside a
// user gesture, so unlock() is wired to the first touch anywhere. Every sound
// also has something visible behind it: the silent switch must not be able to
// hide the end of a round.

let ctx = null;

export function unlock() {
  if (!ctx) {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return;
    ctx = new Ctor();
  }
  if (ctx.state === 'suspended') ctx.resume();
}

function tone({ from, to = from, duration, type = 'sine', gain = 0.22 }) {
  if (!ctx || ctx.state !== 'running') return;
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(from, now);
  if (to !== from) osc.frequency.exponentialRampToValueAtTime(to, now + duration);
  // A short attack and an exponential tail: a raw gate would click.
  amp.gain.setValueAtTime(0.0001, now);
  amp.gain.exponentialRampToValueAtTime(gain, now + 0.012);
  amp.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  osc.connect(amp).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + duration + 0.02);
}

export const sounds = {
  tick:    () => tone({ from: 660, duration: 0.07, type: 'square', gain: 0.10 }),
  start:   () => tone({ from: 440, to: 880, duration: 0.22 }),
  ok:      () => tone({ from: 880, to: 1320, duration: 0.16 }),
  fail:    () => tone({ from: 220, to: 110, duration: 0.28, type: 'sawtooth', gain: 0.16 }),
  timeout: () => tone({ from: 520, to: 180, duration: 0.5, type: 'triangle' }),
  over:    () => { tone({ from: 400, to: 160, duration: 0.7, type: 'triangle' }); },
};

export function play(name) {
  const sound = sounds[name];
  if (sound) { try { sound(); } catch (_) { /* never break a round for audio */ } }
}
