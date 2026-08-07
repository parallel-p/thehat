// Режим для двоих — the endurance mode.
//
// After beret's deathmatch_state.dart, and no longer the same game: beret
// stood at one difficulty and moved it five points at a time, which on a
// dictionary whose ratings all sit near the middle meant the first half of
// the climb was barely felt. This walks *bands* of buckets instead, taking
// every word in a band as equally likely.
//
// One minute on the main clock, a bonus clock per word on top of it, and
// every fifth word the game takes something away: either the band moves up or
// the bonus gets shorter, chosen at random. Both stop — the band at the top of
// the dictionary, the bonus at BONUS_FLOOR — and from there the game simply
// stays as hard as it has become.

import * as dict from './dictionary.js';
import * as logs from './log.js';

// Where each band ends; the next one starts one bucket above it. Tens up to
// 50 and fives after, because the top of the dictionary is where a bucket
// costs the most seconds — the steps get smaller exactly where each one hurts.
const BAND_ENDS = [10, 20, 30, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100];

export const BANDS = BAND_ENDS.map(
  (high, index) => [index ? BAND_ENDS[index - 1] + 1 : 0, high]);

// The bonus stops here rather than at zero. At zero every word after the last
// escalation came out of the minute alone, so the end of a good run was not a
// harder game but a shorter one — three seconds still buys a word back.
export const BONUS_FLOOR = 3;

export const START = {
  bonus: 10,          // seconds added per word
  main: 60,           // seconds of main clock
  step: 5,            // words between escalations
};

export class Deathmatch {
  constructor() {
    this.band = 0;                     // index into BANDS
    this.bonus = START.bonus;
    this.score = 0;
    this.word = null;
    this.log = logs.newLog();
    this.finished = false;
    // What the last escalation took: 'difficulty' or 'bonus'. The round
    // screen shows the two in different places — a band move arrives as an
    // extra slit in the next slip and a halo round the edge, a bonus cut as
    // a second breaking off the end of the bar — so it has to know which.
    this.changed = null;
  }

  async begin() {
    this.log.start_timestamp = Date.now();
    this.word = await this.draw();
  }

  async draw() {
    return (await dict.getWordsInBand(1, ...BANDS[this.band]))[0];
  }

  /**
   * A word guessed. Returns the bonus the next one buys, or null when there
   * was no word in hand to guess.
   *
   * The word is taken out of hand *before* the draw at the end, and that
   * ordering is the whole point. Drawing is asynchronous — a read and a write
   * of the ring in IndexedDB — while the button is not awaited anywhere
   * (`main.js`'s action table calls this and returns), so two taps a few
   * milliseconds apart both arrive here. Reading `this.word` at the top and
   * only replacing it after the await meant the second tap scored and logged
   * the word the first had already taken: sixteen taps on eight words scored
   * 16 and sent the server a log with every word in it twice, which the
   * ratings pass then ranks against itself.
   */
  async guessed(timeMs) {
    const word = this.word;
    if (!word) return null;            // a tap that landed mid-draw
    this.word = null;

    this.log.attempts.push(logs.attempt({
      word, from: 0, to: 1, time: timeMs, outcome: 'guessed',
    }));
    this.score += 1;
    this.changed = null;

    if (this.score % START.step === 0) {
      // Once the band is at the top only the bonus can be taken; once the
      // bonus is at its floor only the band can move. In between it is a coin
      // toss, and when neither can go the game has finished escalating.
      const canMove = this.band < BANDS.length - 1;
      const canCut = this.bonus > BONUS_FLOOR;
      const takeBonus = canCut && (!canMove || Math.random() < 0.5);

      if (takeBonus) {
        this.bonus -= 1;
        this.changed = 'bonus';
      } else if (canMove) {
        this.band += 1;
        this.changed = 'difficulty';
      }
    }

    this.word = await this.draw();
    return this.bonus;
  }

  /** The word in hand when the clock ran out or the player gave up. */
  async end(timeMs) {
    if (this.finished) return;
    this.finished = true;
    // There may be no word in hand: `guessed` empties it while the next one
    // is drawn, and the clock can run out in that gap. An attempt with no
    // word is not a word returned to the hat, it is nothing at all.
    if (this.word) {
      this.log.attempts.push(logs.attempt({
        word: this.word, from: 0, to: 1, time: timeMs,
      }));
    }
    await logs.finish(this.log);
  }
}
