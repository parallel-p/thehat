// Быстрая игра — the party game.
//
// A port of beret's game_state.dart. The pairing formulas below are copied
// deliberately rather than reinvented: they are what makes the difference
// between личная игра (everybody explains to everybody in turn) and парная
// игра (fixed pairs, direction flipping halfway), and they are load-bearing
// rules of the game rather than an implementation detail.

import * as dict from './dictionary.js';
import * as logs from './log.js';

export const DEFAULTS = {
  wordsPerPlayer: 10,
  roundLength: 20,        // seconds a turn lasts
  extraLength: 3,         // seconds the guesser gets after the bell
  difficulty: 30,
  dispersion: 15,
  fixedTeams: false,
};

export class Game {
  constructor(settings, names) {
    this.settings = { ...DEFAULTS, ...settings };
    this.players = names.map(name => ({
      name, explained: 0, guessed: 0,
    }));
    this.turn = 0;
    this.hat = [];
    this.log = logs.newLog();
    this.turnLog = [];      // the current turn's attempts, still editable
    this.word = null;
    this.explainer = 0;
    this.guesser = 1;
    this.finished = false;
  }

  async fill() {
    const count = this.settings.wordsPerPlayer * this.players.length;
    this.hat = await dict.getWords(
      count, this.settings.difficulty, this.settings.dispersion);
    this.assignPair();
  }

  // -- pairing, verbatim from game_state.dart ------------------------------

  assignPair() {
    const n = this.players.length;
    if (this.settings.fixedTeams) {
      const flipped = Math.floor(this.turn / (n / 2)) % 2 !== 0;
      const even = (2 * this.turn) % n;
      this.explainer = flipped ? even + 1 : even;
      this.guesser = flipped ? even : even + 1;
    } else {
      this.explainer = this.turn % n;
      this.guesser = (1 + Math.floor(this.turn / n) % (n - 1) + this.turn) % n;
    }
  }

  // -- the hat -------------------------------------------------------------

  draw() {
    if (!this.hat.length) return null;
    const at = Math.floor(Math.random() * this.hat.length);
    const word = this.hat[at];
    this.hat[at] = this.hat[this.hat.length - 1];
    this.hat.pop();
    return word;
  }

  putBack(word) { this.hat.push(word); }

  get empty() { return this.hat.length === 0; }

  // -- a turn --------------------------------------------------------------

  startTurn() {
    this.turnLog = [];
    this.word = this.draw();
  }

  /**
   * Record one word and hand back the next, or null when the turn is over.
   *
   * `outcome` is 'guessed', 'failed', or null for a word that went back in the
   * hat — the parser reads all three differently, so the caller must not
   * normalise them.
   */
  record(outcome, timeMs, extraMs) {
    this.turnLog.push(logs.attempt({
      word: this.word,
      from: this.explainer,
      to: this.guesser,
      time: timeMs,
      extraTime: extraMs,
      outcome,
    }));
    if (outcome === 'guessed') {
      this.players[this.explainer].explained += 1;
      this.players[this.guesser].guessed += 1;
    } else if (outcome === null) {
      this.putBack(this.word);
    }
    // Only a guess continues the turn; an error or a surrender ends it, as in
    // the printed rules.
    if (outcome !== 'guessed' || this.empty) return null;
    this.word = this.draw();
    return this.word;
  }

  /** Change a decision on the verdict screen, keeping the score honest. */
  amend(index, outcome) {
    const entry = this.turnLog[index];
    const was = entry.outcome || null;
    if (was === outcome) return;

    if (was === 'guessed') {
      this.players[this.explainer].explained -= 1;
      this.players[this.guesser].guessed -= 1;
      // It was taken out of the hat when guessed; it goes back if it no longer
      // counts, or the word would simply vanish from the game.
      this.putBack(entry.word);
    }
    if (outcome === 'guessed') {
      this.players[this.explainer].explained += 1;
      this.players[this.guesser].guessed += 1;
      const at = this.hat.indexOf(entry.word);
      if (at !== -1) this.hat.splice(at, 1);
    }
    if (outcome) entry.outcome = outcome; else delete entry.outcome;
  }

  /** Close the turn: its words join the log for good. */
  commitTurn() {
    this.log.attempts.push(...this.turnLog);
    this.turnLog = [];
  }

  nextTurn() {
    this.turn += 1;
    this.assignPair();
  }

  async finish() {
    if (this.finished) return;
    this.finished = true;
    await logs.finish(this.log);
  }

  /** Score rows, ordered as the game is scored. */
  standings() {
    if (this.settings.fixedTeams) {
      const teams = [];
      for (let i = 0; i + 1 < this.players.length; i += 2) {
        const a = this.players[i], b = this.players[i + 1];
        teams.push({
          name: `${a.name} и ${b.name}`,
          score: a.explained + b.explained,
        });
      }
      return teams.sort((x, y) => y.score - x.score);
    }
    return this.players
      .map(p => ({ name: p.name, score: p.explained + p.guessed,
                   explained: p.explained, guessed: p.guessed }))
      .sort((x, y) => y.score - x.score);
  }
}
