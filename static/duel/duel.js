// «Что сложнее?» — the daily word duel.
//
// The whole program: read the day's ten pairs out of the JSON the server put
// in the page, ask them one at a time, remember where you got to, and write a
// line you can paste into a chat.
//
// It keeps no account and sends nothing back. What you answered lives in this
// browser's localStorage and nowhere else, which is also why the answers are
// in the page: scoring you here means there is nothing to ask the server.
// Anyone who opens the developer tools can read them, exactly as they could
// in the game this is modelled on.

// One key per concern: the day in progress, and the record across days. Both
// are optional — a browser that refuses storage plays fine, it just forgets.
const DAY_KEY = 'hat-duel-day';
const LOG_KEY = 'hat-duel-log';

const HIT = '\u{1F7E9}';    // 🟩 — got it
const MISS = '⬜';      // ⬜ — did not

// The four papers and the five tears, so that no two rounds look alike.
// Picked from the day and the number of the pair rather than at random: a
// reload has to give back the same two slips, or coming back to a puzzle you
// half-played would re-paper it under you.
const SLIPS = ['rose', 'honey', 'sky', 'lilac'];
const RIPS = 5;

function paper(day, index, side) {
  // The two slips of a pair are always different papers, and the offset
  // between them turns as well, so the same colour does not keep the same
  // partner.
  const first = (day * 3 + index * 7) % SLIPS.length;
  const apart = 1 + (day + index) % (SLIPS.length - 1);
  return {
    slip: SLIPS[side === 0 ? first : (first + apart) % SLIPS.length],
    rip: 1 + (day * 2 + index * 3 + side) % RIPS,
  };
}

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (e) {
    return fallback;             // private mode, or something else's data
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) { /* nothing to do about it, and nothing that needs doing */ }
}

function start(day) {
  const $ = id => document.getElementById(id);
  const pairs = day.pairs;
  const root = $('duel');

  // picks[i] is the side this reader chose for pair i; undefined until asked.
  let picks = [];
  const saved = read(DAY_KEY, null);
  if (saved && saved.day === day.day && Array.isArray(saved.picks)) {
    picks = saved.picks.slice(0, pairs.length);
  }

  let at = picks.length;          // the pair on the table
  let revealed = false;           // ...and whether it has been answered

  root.hidden = false;

  // -- the run of ten ------------------------------------------------------

  const pips = $('pips');
  pairs.forEach(() => pips.append(document.createElement('li')));

  function paintPips() {
    [...pips.children].forEach((pip, i) => {
      const answered = picks[i] !== undefined;
      const hit = answered && picks[i] === pairs[i][2];
      pip.className = 'pip'
        + (answered ? (hit ? ' pip--hit' : ' pip--miss') : '')
        + (i === at && !finished() ? ' pip--now' : '');
      pip.setAttribute('aria-label',
        `Пара ${i + 1}: ` + (!answered ? 'впереди' : hit ? 'верно' : 'мимо'));
    });
  }

  const finished = () => at >= pairs.length;

  // -- one pair ------------------------------------------------------------

  function drawPair() {
    const pair = pairs[at];
    const holder = $('pair');
    holder.textContent = '';
    for (let side = 0; side < 2; side++) {
      const { slip: colour, rip } = paper(day.day, at, side);
      const slip = document.createElement('button');
      slip.className = `ws ws--${colour} duel__slip`;
      slip.style.setProperty('--tear', `var(--rip-${rip})`);
      slip.type = 'button';
      slip.dataset.side = String(side);

      const word = document.createElement('span');
      word.className = 'duel__word';
      word.textContent = pair[side];

      // Both of these are in the markup from the start and revealed by CSS:
      // building them on the answer would move the paper under the reader's
      // finger at the moment they press it.
      const reveal = document.createElement('span');
      reveal.className = 'duel__reveal';

      const tag = document.createElement('span');
      tag.className = 'duel__tag';
      tag.textContent = 'труднее';

      const rating = document.createElement('span');
      rating.className = 'duel__rating';
      rating.textContent = `сложность ${format(pair[3 + side])}`;

      reveal.append(tag, rating);
      slip.append(word, reveal);
      slip.addEventListener('click', () => answer(side));
      holder.append(slip);
    }
    $('verdict').textContent = '';
    $('next').hidden = true;
    revealed = false;
    paintPips();
  }

  function slips() {
    return [...$('pair').querySelectorAll('.duel__slip')];
  }

  function answer(side) {
    if (revealed || finished()) return;
    revealed = true;
    picks[at] = side;
    write(DAY_KEY, { day: day.day, picks });

    const pair = pairs[at];
    const right = pair[2];
    slips().forEach((slip, index) => {
      slip.disabled = true;
      slip.dataset.answer = index === right ? 'harder' : 'easier';
      if (index === side) slip.dataset.picked = '';
    });

    const verdict = $('verdict');
    verdict.textContent = '';
    const lead = document.createElement('em');
    lead.textContent = side === right ? 'Верно' : 'Мимо';
    verdict.append(lead, document.createTextNode(
      `. «${pair[right]}» объясняют дольше.`));

    const next = $('next');
    next.textContent = at === pairs.length - 1 ? 'Итог' : 'Дальше';
    next.hidden = false;
    next.focus({ preventScroll: true });
    paintPips();
  }

  function advance() {
    if (!revealed) return;
    at += 1;
    write(DAY_KEY, { day: day.day, picks });
    if (finished()) finish(); else drawPair();
  }

  $('next').addEventListener('click', advance);

  // 1 and 2 pick a slip, Left and Right do the same, Enter moves on. A quiz
  // played ten times a week is a quiz somebody will want to play with a
  // keyboard.
  document.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (finished()) return;
    if (!revealed && (event.key === '1' || event.key === 'ArrowLeft')) {
      answer(0);
    } else if (!revealed && (event.key === '2' || event.key === 'ArrowRight')) {
      answer(1);
    } else {
      return;
    }
    event.preventDefault();
  });

  // -- the result ----------------------------------------------------------

  const score = () => picks.filter((side, i) => side === pairs[i][2]).length;

  const gridLine = () => picks
    .map((side, i) => (side === pairs[i][2] ? HIT : MISS)).join('');

  function finish() {
    $('round').hidden = true;
    $('done').hidden = false;
    paintPips();

    $('score').textContent = String(score());
    $('streak').textContent = record();
    $('next-at').textContent =
      'Следующие десять пар — в полночь по Москве.';
    drawReview();
  }

  // The record across days, updated the once — on the run that completes the
  // day. Re-opening a finished puzzle must not count it again, which is what
  // `last` guards.
  function record() {
    const log = read(LOG_KEY, { last: 0, streak: 0, best: 0, played: 0, total: 0 });
    if (log.last !== day.day) {
      log.streak = log.last === day.day - 1 ? log.streak + 1 : 1;
      log.best = Math.max(log.best || 0, log.streak);
      log.played = (log.played || 0) + 1;
      log.total = (log.total || 0) + score();
      log.last = day.day;
      write(LOG_KEY, log);
    }
    if (log.played < 2) return '';
    const average = (log.total / log.played).toFixed(1).replace('.', ',');
    const said = [
      plural(log.played, 'выпуск', 'выпуска', 'выпусков'),
      `в среднем ${average} из ${pairs.length}`,
    ];
    if (log.streak > 1) {
      said.push(plural(log.streak, 'день', 'дня', 'дней') + ' подряд');
    }
    return said.join(', ') + '.';
  }

  // Each pair is two rows sharing one numbered cell: the harder word above
  // the easier one, in the order the answer was. A word links to everything
  // the dictionary knows about it, which is where this rating comes from.
  function drawReview() {
    const body = document.querySelector('#review tbody');
    body.textContent = '';
    pairs.forEach((pair, i) => {
      const harder = pair[2];

      [harder, 1 - harder].forEach((side, which) => {
        const row = document.createElement('tr');
        if (which === 0) {
          row.className = 'review__pair';
          const rank = document.createElement('td');
          rank.className = 'rank';
          rank.rowSpan = 2;
          const pip = document.createElement('span');
          pip.className = 'pip '
            + (picks[i] === harder ? 'pip--hit' : 'pip--miss');
          rank.append(pip, document.createTextNode(String(i + 1)));
          row.append(rank);
        }

        const word = document.createElement('td');
        word.className = 'word';
        const link = document.createElement('a');
        link.href = '/statistics/word_statistics?word='
          + encodeURIComponent(pair[side]);
        link.textContent = pair[side];
        word.append(link);
        if (which === 0) {
          const tag = document.createElement('span');
          tag.className = 'review__tag';
          tag.textContent = 'труднее';
          word.append(' ', tag);
        }

        const rating = document.createElement('td');
        rating.className = 'num';
        rating.textContent = format(pair[3 + side]);

        row.append(word, rating);
        body.append(row);
      });
    });
  }

  // -- sharing -------------------------------------------------------------

  function shareText() {
    return `Что сложнее? №${day.day} — ${score()}/${pairs.length}\n`
      + `${gridLine()}\n${location.origin}/duel`;
  }

  $('share').addEventListener('click', async () => {
    const button = $('share');
    const text = shareText();
    // The share sheet where there is one — that is the whole point on a
    // phone. It rejects when the reader dismisses it, which is not an error
    // and must not fall through to quietly copying instead.
    if (navigator.share) {
      try {
        await navigator.share({ text });
        return;
      } catch (e) {
        if (e && e.name === 'AbortError') return;
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      say(button, 'Скопировано');
    } catch (e) {
      say(button, 'Не вышло скопировать');
    }
  });

  function say(button, message) {
    const was = button.textContent;
    button.textContent = message;
    setTimeout(() => { button.textContent = was; }, 1800);
  }

  // -- start where we left off ---------------------------------------------

  if (finished()) finish(); else drawPair();
}

// 62.5 -> "62,5"; 62.0 -> "62". A page in Russian writes its decimals with a
// comma, and the site's other numbers already do.
function format(value) {
  return String(Math.round(value * 10) / 10).replace('.', ',');
}

function plural(count, one, few, many) {
  const mod100 = count % 100;
  const mod10 = count % 10;
  let word = many;
  if (mod100 < 11 || mod100 > 14) {
    if (mod10 === 1) word = one;
    else if (mod10 >= 2 && mod10 <= 4) word = few;
  }
  return `${count} ${word}`;
}

// Last, not first: everything above has to have been evaluated before the
// puzzle can be played, and a module's declarations are not in scope until
// the line that declares them has run.
const puzzle = JSON.parse(document.getElementById('puzzle').textContent);
if (puzzle) start(puzzle);
