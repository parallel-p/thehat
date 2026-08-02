// Play the game thousands of times against the app's own modules, and check
// the rules held. Run it inside a loaded /play:
//
//   node tools/drive.mjs http://localhost:8901/play run:tools/stress.js
//
// Not a unit test of a copy of the logic — it imports game.js, dictionary.js
// and deathmatch.js and drives them exactly as the screens do, so anything it
// proves is true of the shipped app. What it cannot see is the screens
// themselves; those are driven by the other steps of drive.mjs.
//
// The invariants are the printed rules, and where beret is the authority its
// file is named next to the check.

(async () => {
  const dict = await import('/play/js/dictionary.js');
  const { Game } = await import('/play/js/game.js');
  const { Deathmatch, START } = await import('/play/js/deathmatch.js');
  const db = await import('/play/js/db.js');

  const problems = [];
  const seen = new Map();          // problem -> how many times
  const fail = (what) => {
    seen.set(what, (seen.get(what) || 0) + 1);
    if (seen.get(what) === 1) problems.push(what);
  };
  const check = (ok, what) => { if (!ok) fail(what); };
  const pick = (n) => Math.floor(Math.random() * n);

  await dict.load();
  const tally = {
    games: 0, turns: 0, words: 0, amends: 0, deathmatches: 0,
    guessed: 0, failed: 0, returned: 0, redraws: 0, repeats: 0,
  };

  // Every word this run has drawn, newest last: the app promises not to draw
  // one again while it is still inside the 1000-word ring (dictionary.js).
  const RING = 1000;
  const history = [];
  const recent = new Set();
  const drewWord = (word) => {
    if (recent.has(word)) tally.repeats += 1;
    history.push(word);
    recent.add(word);
    if (history.length > RING) recent.delete(history[history.length - 1 - RING]);
  };

  // -- обычная игра ---------------------------------------------------------

  for (let round = 0; round < 120; round++) {
    const count = 2 + pick(7);
    const names = Array.from({ length: count }, (_, i) => `И${i}`);
    const settings = {
      wordsPerPlayer: 1 + pick(6),
      difficulty: pick(101),
      dispersion: 3 + pick(43),
      fixedTeams: count % 2 === 0 && Math.random() < 0.5,
    };
    const game = new Game(settings, names);
    await game.fill();
    tally.games += 1;

    const size = settings.wordsPerPlayer * count;
    check(game.hat.length === size, `hat holds ${game.hat.length}, asked for ${size}`);
    check(new Set(game.hat).size === game.hat.length, 'one hat held the same word twice');
    game.hat.forEach(drewWord);
    const inPlay = new Set(game.hat);

    // Play it out. A turn ends on an error, on a surrender, or when the hat
    // runs dry (game_state.dart: error() and concede() both changeState to
    // 'verdict'; only guessedRight draws again).
    let guard = 0;
    while (!game.empty && guard++ < 400) {
      game.startTurn();
      tally.turns += 1;
      check(game.explainer !== game.guesser,
        `turn ${game.turn}: ${count} players, explainer is also the guesser`);
      if (settings.fixedTeams) {
        check(Math.floor(game.explainer / 2) === Math.floor(game.guesser / 2),
          `fixed pairs: ${game.explainer} was paired with ${game.guesser}`);
      }

      // A turn is bounded by the clock, not by the hat: after so many words
      // the time runs out and whatever is in hand goes back. Without this a
      // lucky turn swallows the whole game and the later turns are never
      // played at all.
      let budget = 1 + pick(5);
      let word = game.word;
      let alive = true;
      while (alive) {
        check(word !== null && word !== undefined, 'drew nothing from a full hat');
        check(!game.hat.includes(word), 'the word in hand was also still in the hat');
        tally.words += 1;
        const roll = Math.random();
        const outcome = budget-- <= 0 ? null                    // time up
          : roll < 0.65 ? 'guessed' : roll < 0.85 ? 'failed' : null;
        if (outcome === 'guessed') tally.guessed += 1;
        else if (outcome === 'failed') tally.failed += 1;
        else tally.returned += 1;
        const next = game.record(outcome, 500 + pick(9000), 0);
        if (next === null) alive = false;
        else { word = next; tally.redraws += 1; }
      }

      // The verdict screen: fuzz the outcomes, then hold the rule that owns
      // the hat — a word from this turn is in the hat if and only if its
      // outcome is null (turn.dart's three dropdowns, as one rule).
      for (let i = 0; i < game.turnLog.length; i++) {
        if (Math.random() < 0.5) continue;
        const to = [null, 'guessed', 'failed'][pick(3)];
        game.amend(i, to);
        tally.amends += 1;
      }
      for (const entry of game.turnLog) {
        const shouldBeInHat = !entry.outcome;
        const isInHat = game.hat.includes(entry.word);
        check(isInHat === shouldBeInHat,
          `after amending, «${entry.word}» outcome=${entry.outcome || 'null'} `
          + `${isInHat ? 'was left in' : 'went missing from'} the hat`);
      }
      check(new Set(game.hat).size === game.hat.length,
        'amending put a word in the hat that was already there');

      game.commitTurn();
      if (!game.empty) game.nextTurn();
    }
    check(game.empty, 'the hat never emptied');
    check(guard < 400, 'the game would not end');

    // The score is the log, counted twice: once by the players, once by us.
    const attempts = game.log.attempts;
    const guessedInLog = attempts.filter(a => a.outcome === 'guessed').length;
    const explained = game.players.reduce((sum, p) => sum + p.explained, 0);
    const guessedBy = game.players.reduce((sum, p) => sum + p.guessed, 0);
    check(explained === guessedInLog,
      `explained ${explained} but the log has ${guessedInLog} guessed`);
    check(guessedBy === guessedInLog,
      `guessed ${guessedBy} but the log has ${guessedInLog} guessed`);

    // Every word that ever left the hat came from it, and nothing outlived it.
    for (const attempt of attempts) {
      check(inPlay.has(attempt.word), `logged «${attempt.word}», which was never in the hat`);
    }
    const settled = new Set(attempts.filter(a => a.outcome).map(a => a.word));
    check(settled.size === size,
      `${size} words went in, ${settled.size} came out settled`);

    // Standings add up to the same total, however they are grouped.
    const standings = game.standings();
    const total = standings.reduce((sum, row) => sum + row.score, 0);
    check(total === (settings.fixedTeams ? explained : explained + guessedBy),
      `standings total ${total} does not match the score`);
    if (settings.fixedTeams) {
      check(standings.length === count / 2, 'fixed pairs did not produce n/2 teams');
    }

    // The log the server will parse: no attempt may carry a null outcome key,
    // and times must be inside the window stats.py accepts (log.js).
    for (const attempt of attempts) {
      check(!('outcome' in attempt) || attempt.outcome === 'guessed'
        || attempt.outcome === 'failed', `bad outcome ${attempt.outcome}`);
      check(Number.isInteger(attempt.time) && Number.isInteger(attempt.extra_time),
        'a time was not a whole number of milliseconds');
      check(attempt.from !== attempt.to, 'an attempt was explained to its explainer');
    }
  }

  // -- turn order, exhaustively --------------------------------------------
  //
  // Both formulas come from game_state.dart. Personal play must never pair a
  // player with themselves and must reach everybody; fixed pairs must play
  // both directions and only ever inside a pair.
  for (let count = 2; count <= 10; count++) {
    for (const fixedTeams of (count % 2 === 0 ? [false, true] : [false])) {
      const game = new Game({ fixedTeams }, Array.from({ length: count }, (_, i) => `И${i}`));
      const pairsSeen = new Set();
      for (let turn = 0; turn < count * (count - 1) * 2; turn++) {
        game.turn = turn;
        game.assignPair();
        check(game.explainer !== game.guesser,
          `${count} players${fixedTeams ? ' in pairs' : ''}: turn ${turn} explains to itself`);
        check(game.explainer >= 0 && game.explainer < count
          && game.guesser >= 0 && game.guesser < count,
          `${count} players: turn ${turn} points outside the table`);
        if (fixedTeams) {
          check(Math.floor(game.explainer / 2) === Math.floor(game.guesser / 2),
            `${count} players in pairs: turn ${turn} crossed pairs`);
        }
        pairsSeen.add(`${game.explainer}>${game.guesser}`);
      }
      if (fixedTeams) {
        check(pairsSeen.size === count, `${count} in pairs: ${pairsSeen.size} orderings, expected ${count}`);
      } else {
        check(pairsSeen.size === count * (count - 1),
          `${count} personal: ${pairsSeen.size} orderings, expected ${count * (count - 1)}`);
      }
    }
  }

  // -- режим для двоих ------------------------------------------------------

  for (let round = 0; round < 25; round++) {
    const dm = new Deathmatch();
    await dm.begin();
    tally.deathmatches += 1;
    drewWord(dm.word);
    check(dm.difficulty === START.difficulty && dm.bonus === START.bonus,
      'a deathmatch did not start where it should');

    let previous = { difficulty: dm.difficulty, bonus: dm.bonus };
    for (let word = 0; word < 60; word++) {
      const before = dm.word;
      await dm.guessed(500 + pick(5000));
      drewWord(dm.word);
      check(dm.word !== before, 'the deathmatch handed back the same word');
      check(dm.difficulty >= START.difficulty && dm.difficulty <= 100
        && dm.difficulty % 5 === 0, `difficulty went to ${dm.difficulty}`);
      check(dm.bonus >= 0 && dm.bonus <= START.bonus, `bonus went to ${dm.bonus}`);

      const stepped = dm.score % START.step === 0;
      const moved = (dm.difficulty !== previous.difficulty ? 1 : 0)
        + (dm.bonus !== previous.bonus ? 1 : 0);
      // Every fifth word takes exactly one thing away — unless both are spent.
      const spent = previous.difficulty >= 100 && previous.bonus === 0;
      check(stepped ? (moved === 1 || spent) : moved === 0,
        `at ${dm.score} words, ${moved} things changed`);
      if (stepped && moved === 1) {
        check(dm.changed === (dm.bonus !== previous.bonus ? 'bonus' : 'difficulty'),
          'the deathmatch blinked the wrong number');
      }
      previous = { difficulty: dm.difficulty, bonus: dm.bonus };
    }
    const attempts = dm.log.attempts;
    check(attempts.length === 60, `deathmatch logged ${attempts.length} attempts, played 60`);
    check(attempts.every(a => a.outcome === 'guessed'), 'a guessed word was not logged as guessed');
    check(attempts.every(a => a.from === 0 && a.to === 1), 'deathmatch attempt had odd players');
  }

  // -- the outbox, once -----------------------------------------------------
  //
  // finish() is the one path that touches the network and storage, so it is
  // exercised once rather than three thousand times.
  const before = (await db.keys('outbox')).length;
  const last = new Game({ wordsPerPlayer: 1 }, ['А', 'Б']);
  await last.fill();
  last.startTurn();
  last.record('guessed', 1000, 0);
  last.commitTurn();
  await last.finish();
  const after = await db.all('outbox');
  check(after.length >= before, 'finishing a game lost the outbox');
  const stored = after[after.length - 1];
  if (stored) {
    check(stored.version === '2.0' && typeof stored.game_id === 'string',
      'the stored log is not the shape the server accepts');
    check(Array.isArray(stored.attempts) && stored.attempts.length >= 1,
      'the stored log carries no attempts');
  }

  // -- every table, systematically -----------------------------------------
  //
  // The 120 games above sample; this covers each size once with each mode and
  // at both ends of "words per player", because the bugs that hide in a
  // formula hide at particular sizes rather than on average.
  const tables = {};
  for (const count of [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 20]) {
    for (const fixedTeams of [false, true]) {
      for (const wordsPerPlayer of [1, 4]) {
        const names = Array.from({ length: count }, (_, i) => `И${i}`);
        const game = new Game({ wordsPerPlayer, fixedTeams }, names);
        await game.fill();
        const size = count * wordsPerPlayer;
        const label = `${count}p ${fixedTeams ? 'pairs' : 'personal'} x${wordsPerPlayer}`;
        check(game.hat.length === size, `${label}: hat holds ${game.hat.length}`);
        // Fixed pairs on an odd table are impossible; the game must have
        // dropped the setting rather than pairing player n with player n+1.
        check(game.settings.fixedTeams === (fixedTeams && count % 2 === 0),
          `${label}: fixed pairs survived an odd table`);

        const explainers = new Set();
        let guard = 0;
        while (!game.empty && guard++ < 2000) {
          game.startTurn();
          explainers.add(game.explainer);
          check(game.players[game.explainer] && game.players[game.guesser],
            `${label}: turn ${game.turn} points at a player who is not at the table`);
          check(game.explainer !== game.guesser, `${label}: explains to itself`);
          let budget = 1 + pick(3);
          let alive = true;
          while (alive) {
            const roll = Math.random();
            alive = game.record(budget-- <= 0 ? null
              : roll < 0.7 ? 'guessed' : roll < 0.85 ? 'failed' : null,
              600 + pick(4000), 0) !== null;
          }
          game.commitTurn();
          if (!game.empty) game.nextTurn();
        }
        const turns = game.turn + 1;
        check(game.empty && guard < 2000, `${label}: never finished`);
        // The phone goes round: once a game has run a full lap of the table,
        // everyone at it must have explained.
        if (turns >= count) {
          check(explainers.size === count,
            `${label}: ${turns} turns but only ${explainers.size} of ${count} explained`);
        }
        tables[label] = turns;
      }
    }
  }

  // -- outcome sequences that do not behave ---------------------------------
  const sequences = {};

  {   // Every word conceded: each goes straight back, so the hat never
      // empties and the game cannot end on its own. That is the rule (a word
      // put back is still in play) — what matters is that nothing rots: no
      // duplicates, no growth, and the log keeps every attempt.
    const game = new Game({ wordsPerPlayer: 3 }, ['А', 'Б', 'В', 'Г']);
    await game.fill();
    const size = game.hat.length;
    for (let turn = 0; turn < 40; turn++) {
      game.startTurn();
      game.record(null, 1000, 0);
      game.commitTurn();
      game.nextTurn();
    }
    check(game.hat.length === size, `conceding changed the hat: ${game.hat.length} of ${size}`);
    check(new Set(game.hat).size === size, 'conceding duplicated a word');
    check(game.log.attempts.length === 40, 'conceding lost attempts from the log');
    check(game.players.every(p => p.explained === 0 && p.guessed === 0),
      'conceding scored something');
    sequences.allConceded = `${40} turns, hat still ${game.hat.length}`;
  }

  {   // Every word an error: one word leaves the hat per turn, so the game
      // lasts exactly as many turns as it has words and nobody scores.
    const game = new Game({ wordsPerPlayer: 3 }, ['А', 'Б', 'В', 'Г']);
    await game.fill();
    const size = game.hat.length;
    let turns = 0;
    while (!game.empty && turns < 100) {
      game.startTurn();
      game.record('failed', 1000, 0);
      game.commitTurn();
      turns += 1;
      if (!game.empty) game.nextTurn();
    }
    check(turns === size, `${size} words burnt in ${turns} turns`);
    check(game.players.every(p => p.explained === 0), 'an error scored');
    sequences.allFailed = `${turns} turns for ${size} words`;
  }

  {   // The same entry amended over and over: every transition, in sequence.
    const game = new Game({ wordsPerPlayer: 4 }, ['А', 'Б']);
    await game.fill();
    game.startTurn();
    while (game.record('guessed', 1000, 0) !== null) { /* fill the turn log */ }
    let broken = 0;
    for (let round = 0; round < 60; round++) {
      const index = pick(game.turnLog.length);
      game.amend(index, [null, 'guessed', 'failed'][pick(3)]);
      for (const entry of game.turnLog) {
        if (game.hat.includes(entry.word) !== !entry.outcome) broken += 1;
      }
      if (new Set(game.hat).size !== game.hat.length) broken += 1;
    }
    check(broken === 0, `repeated amending broke the hat ${broken} times`);
    sequences.repeatedAmends = broken === 0 ? '60 amendments, hat intact' : 'BROKEN';
  }

  {   // A deathmatch run until it has nothing left to take away.
    const dm = new Deathmatch();
    await dm.begin();
    for (let word = 0; word < 200; word++) await dm.guessed(800);
    check(dm.difficulty === 100 && dm.bonus === 0,
      `after 200 words the deathmatch is at difficulty ${dm.difficulty}, bonus ${dm.bonus}`);
    sequences.deathmatchFloor = `difficulty ${dm.difficulty}, bonus ${dm.bonus}`;
  }

  // -- the edges of the word supply ----------------------------------------
  //
  // Every check above draws from a comfortable pool. These are the shapes
  // that empty it: one bucket only (dispersion 0), a hat bigger than the
  // bucket, and the same narrow band played over and over until the
  // 1000-word ring covers everything the band can offer.
  const edges = {};

  {   // A hat larger than the single bucket it must come from.
    const game = new Game(
      { wordsPerPlayer: 40, difficulty: 50, dispersion: 0 },
      Array.from({ length: 10 }, (_, i) => `И${i}`));
    await game.fill();
    edges.oneBucketHat = game.hat.length;
    edges.oneBucketDistinct = new Set(game.hat).size;
    edges.oneBucketPlaceholders = game.hat.filter(w => w === '—').length;
  }

  {   // The same narrow band, until the ring holds more than the band has.
    let placeholders = 0, duplicatesInAHat = 0;
    for (let round = 0; round < 12; round++) {
      const game = new Game(
        { wordsPerPlayer: 25, difficulty: 80, dispersion: 3 },
        ['А', 'Б', 'В', 'Г']);
      await game.fill();
      placeholders += game.hat.filter(w => w === '—').length;
      duplicatesInAHat += game.hat.length - new Set(game.hat).size;
    }
    edges.narrowBandPlaceholders = placeholders;
    edges.narrowBandDuplicates = duplicatesInAHat;
  }

  {   // The biggest table the lobby allows to be sensible, played out.
    const game = new Game({ wordsPerPlayer: 50 },
      Array.from({ length: 10 }, (_, i) => `И${i}`));
    await game.fill();
    edges.bigHat = game.hat.length;
    edges.bigHatDistinct = new Set(game.hat).size;
    let guard = 0;
    while (!game.empty && guard++ < 3000) {
      game.startTurn();
      let alive = true;
      while (alive) alive = game.record('guessed', 1000, 0) !== null;
      game.commitTurn();
      if (!game.empty) game.nextTurn();
    }
    // No clock here, so one turn swallows the hat — the point of this case
    // is that 500 words come out unique and the game still terminates.
    edges.bigHatFinished = game.empty;
  }

  {   // Two players, one word each: the smallest game there is. One turn of
      // two guesses empties it, and the second guess must end the turn.
    const game = new Game({ wordsPerPlayer: 1 }, ['А', 'Б']);
    await game.fill();
    game.startTurn();
    const second = game.record('guessed', 1000, 0);
    const third = game.record('guessed', 1000, 0);
    edges.smallestGame = second !== null && third === null && game.empty
      ? 'ends after both words' : 'BROKEN';
  }

  // The ring can only be honoured if the dictionary is bigger than it: with
  // 1077 words (staging's sample) and a 1000-word ring, most draws must
  // repeat something inside the window, and no amount of code fixes that.
  // Production carries ~13 800. The rate is only readable next to this.
  const words = (await db.all('buckets')).reduce((n, b) => n + b.length, 0);

  return {
    ...tally,
    dictionaryWords: words,
    tables: `${Object.keys(tables).length} configurations played out`,
    sequences,
    edges,
    repeatRate: `${tally.repeats} of ${history.length} draws repeated a word `
      + `still inside the ${RING}-word ring`
      + (words <= RING * 1.5 ? ' — expected: the dictionary is barely bigger'
        + ' than the ring, so there is nothing unplayed left to draw' : ''),
    problems: problems.length ? problems.map(p => `${p}  (x${seen.get(p)})`) : 'none',
  };
})()
