// Режим для двоих — the endurance mode.
//
// Ported from beret's deathmatch_state.dart. One minute on the main clock, a
// bonus clock per word on top of it, and every fifth word the game takes
// something away: either the words get harder or the bonus gets shorter,
// chosen at random, until the difficulty is pinned at 100 and only the bonus
// can go.

import * as dict from './dictionary.js';
import * as logs from './log.js';

export const START = {
  difficulty: 15,
  bonus: 10,          // seconds added per word
  main: 60,           // seconds of main clock
  step: 5,            // words between escalations
};

export class Deathmatch {
  constructor() {
    this.difficulty = START.difficulty;
    this.bonus = START.bonus;
    this.score = 0;
    this.word = null;
    this.log = logs.newLog();
    this.finished = false;
    // What changed at the last escalation, so the display can blink it.
    this.changed = null;
  }

  async begin() {
    this.log.start_timestamp = Date.now();
    this.word = (await dict.getWords(1, this.difficulty, 5))[0];
  }

  async guessed(timeMs) {
    this.log.attempts.push(logs.attempt({
      word: this.word, from: 0, to: 1, time: timeMs, outcome: 'guessed',
    }));
    this.score += 1;
    this.changed = null;

    if (this.score % START.step === 0) {
      // Once difficulty is maxed only the bonus can be taken; once the bonus is
      // gone only difficulty can rise. In between it is a coin toss.
      let takeBonus;
      if (this.bonus === 0) takeBonus = false;
      else if (this.difficulty >= 100) takeBonus = true;
      else takeBonus = Math.random() < 0.5;

      if (takeBonus) {
        this.bonus -= 1;
        this.changed = 'bonus';
      } else if (this.difficulty < 100) {
        this.difficulty += 5;
        this.changed = 'difficulty';
      }
    }

    this.word = (await dict.getWords(1, this.difficulty, 5))[0];
    return this.bonus;
  }

  /** The word in hand when the clock ran out or the player gave up. */
  async end(timeMs) {
    if (this.finished) return;
    this.finished = true;
    this.log.attempts.push(logs.attempt({
      word: this.word, from: 0, to: 1, time: timeMs,
    }));
    await logs.finish(this.log);
  }
}
