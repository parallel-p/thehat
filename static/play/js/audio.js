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

function tone({ from, to = from, duration, type = 'sine', gain = 0.22,
                at = 0, attack = 0.012 }) {
  if (!ctx || ctx.state !== 'running') return;
  const now = ctx.currentTime + at;
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(from, now);
  if (to !== from) osc.frequency.exponentialRampToValueAtTime(to, now + duration);
  // A short attack and an exponential tail: a raw gate would click. A longer
  // attack is how a note is made to arrive rather than to strike.
  amp.gain.setValueAtTime(0.0001, now);
  amp.gain.exponentialRampToValueAtTime(gain, now + attack);
  amp.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  osc.connect(amp).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + duration + 0.02);
}

export const sounds = {
  tick:    () => tone({ from: 660, duration: 0.07, type: 'square', gain: 0.10 }),
  // The end of the 3-2-1, and the only sound that means "go ahead" — so it
  // opens rather than announces: a major triad whose notes arrive one after
  // another and are left ringing together, in place of the siren-like octave
  // glide this used to be. Each note is quiet enough that the three of them
  // together stay well under one.
  start:   () => [523.25, 659.25, 783.99].forEach((hz, step) => tone({
    from: hz, duration: 0.6 - step * 0.05, at: step * 0.075,
    gain: 0.13, attack: 0.022,
  })),
  ok:      () => tone({ from: 880, to: 1320, duration: 0.16 }),
  fail:    () => tone({ from: 220, to: 110, duration: 0.28, type: 'sawtooth', gain: 0.16 }),

  // The bell, when the main time runs out. The turn is NOT over here — the
  // guesser still has the extra seconds and one word — so this had to stop
  // sounding like a conclusion. Three fast strikes, which no room mistakes
  // for anything but "time"; each is a hard strike over three partials at a
  // bell's own spacing (the octave, and one just under three times the
  // fundamental), and only the last is left to ring.
  timeout: () => [0, 0.19, 0.38].forEach((at, strike) => {
    const last = strike === 2;
    for (const part of [
      { from: 660, gain: 0.17, duration: last ? 1.15 : 0.42 },
      { from: 1320, gain: 0.07, duration: last ? 0.8 : 0.28 },
      { from: 1848, gain: 0.035, duration: last ? 0.45 : 0.18 },
    ]) tone({ ...part, at, attack: 0.004 });
  }),

  // The turn is over, and nothing good happened: the triad the countdown
  // opens with, coming back down and coming down MINOR — the E flat is the
  // whole difference between "well played" and "that's it". Quick about it,
  // too; a long farewell for a turn that ran out of time is a joke at the
  // players' expense.
  over:    () => [783.99, 622.25, 523.25].forEach((hz, step) => tone({
    from: hz, duration: 0.4 + step * 0.22, at: step * 0.085,
    gain: 0.14, attack: 0.012,
  })),

  // Giving a word back is not the end of anything: a small, low, downward
  // pair of notes — the sound of putting something down.
  back:    () => [330, 247].forEach((hz, step) => tone({
    from: hz, duration: 0.3, at: step * 0.09, gain: 0.13, type: 'triangle',
  })),
};

export function play(name) {
  const sound = sounds[name];
  if (sound) { try { sound(); } catch (_) { /* never break a round for audio */ } }
}
