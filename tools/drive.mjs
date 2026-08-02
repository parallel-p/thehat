// Drive /play in a headless Chrome over DevTools Protocol, and print TEXT.
//
//   make browser                       # once: a headless Chrome that stays up
//   node tools/drive.mjs http://localhost:8901/play click:new-game back
//
// Steps: click:ACT  sel:CSS  set:id=value  back  wait:MS  eval:JS  shot:FILE
//        theme:dark|light  media:FEATURE=VALUE  pre:matchMedia=QUERY  reload
//        hover:CSS  press:CSS  release  drag:CSS=dy  run:FILE.js
//        sw:on|off  net:on|off
// Output: one line per step — the step, the screen it landed on, and
// history.length, which is what catches a back-button stack that grows.
//
// `eval:` runs in the page and prints the value, so app state can be read
// straight out of IndexedDB:
//
//   eval:(await (await import('/play/js/db.js')).keys('outbox')).length
//
// Why this exists: the obvious way to observe a headless page is
// --screenshot, but it fires at the load event, before any async work. The
// workaround — render values into the DOM, hold the load event open with a
// sleeping endpoint, screenshot, then read a picture of the text — costs
// ~25s per look and cannot see anything that is not on screen. This costs
// ~2s, answers in text, and can reach into storage. Screenshots are then
// only for what they are actually good at, which is looking at the design.
//
// Node 22+ only (it uses the global WebSocket). Development only: nothing
// the app or the deploy needs.

import { readFileSync, writeFileSync } from 'node:fs';

const PORT = 9222;

async function rpc(ws, method, params = {}, sessionId) {
  const id = rpc.n = (rpc.n || 0) + 1;
  const message = { id, method, params };
  if (sessionId) message.sessionId = sessionId;
  ws.send(JSON.stringify(message));
  return new Promise((resolve, reject) => {
    // Cleared on reply, and unref'd besides: a live timer per call would keep
    // the event loop open long after the work is done, which is how a
    // two-second run bills itself as thirty.
    const timer = setTimeout(() => reject(new Error(method + ' timed out')), 30000);
    timer.unref();
    const onMessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id !== id) return;
      clearTimeout(timer);
      ws.removeEventListener('message', onMessage);
      data.error ? reject(new Error(data.error.message)) : resolve(data.result);
    };
    ws.addEventListener('message', onMessage);
  });
}

const [, , url, ...steps] = process.argv;

const version = await (await fetch(`http://localhost:${PORT}/json/version`)).json();
const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));

const { targetId } = await rpc(ws, 'Target.createTarget', { url: 'about:blank' });
const { sessionId } = await rpc(ws, 'Target.attachToTarget', { targetId, flatten: true });
await rpc(ws, 'Page.enable', {}, sessionId);
await rpc(ws, 'Runtime.enable', {}, sessionId);
await rpc(ws, 'Emulation.setDeviceMetricsOverride',
  { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }, sessionId);

const evaluate = async (expression) => {
  const { result, exceptionDetails } = await rpc(ws, 'Runtime.evaluate', {
    expression, awaitPromise: true, returnByValue: true,
  }, sessionId);
  if (exceptionDetails) throw new Error(exceptionDetails.text + ' :: '
    + (exceptionDetails.exception && exceptionDetails.exception.description || ''));
  return result.value;
};

// The app installs a service worker that answers from cache and refreshes
// behind the reader's back — correct for a deploy, wrong for a dev loop,
// where it silently drives the *previous* edit and reports it as the current
// one. Requests go straight to the server here; the worker is still
// registered, it just does not get to answer.
// The HTTP cache is the same trap one level down: the dev server sends no
// cache headers, so Chrome is free to reuse a js file it fetched a minute
// ago — and a `reload` step then re-runs the edit before last.
await rpc(ws, 'Network.enable', {}, sessionId);
await rpc(ws, 'Network.setBypassServiceWorker', { bypass: true }, sessionId);
await rpc(ws, 'Network.setCacheDisabled', { cacheDisabled: true }, sessionId);

// Wait for the app to boot — a real condition, not a guessed sleep.
const boot = async () => {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    const screen = await evaluate('document.body.dataset.screen || ""').catch(() => '');
    if (screen && screen !== 'loading') return;
    await new Promise(r => setTimeout(r, 100));
  }
};

await rpc(ws, 'Page.navigate', { url }, sessionId);
await boot();

// Only the countdown on the screen you can actually see. Querying all of them
// reported one left visible on a screen that had been switched away from —
// an instrument telling you about state nobody can observe is worse than no
// instrument.
const state = `(() => {
  const on = document.querySelector('.screen[data-for="' + document.body.dataset.screen + '"]');
  const cd = on && [...on.querySelectorAll('.countdown')].some(e => !e.hidden);
  return document.body.dataset.screen + (cd ? ' [countdown]' : '')
    + ' len=' + history.length;
})()`;

console.log('boot            -> ' + await evaluate(state));

const media = new Map();
let serviceWorker = false;   // is the app's own worker allowed to answer?

for (const step of steps) {
  const at = step.indexOf(':');
  const kind = at < 0 ? step : step.slice(0, at);
  const arg = at < 0 ? '' : step.slice(at + 1);
  try {
    if (kind === 'click') {
      const ok = await evaluate(
        `(() => { const e = document.querySelector('[data-act="${arg}"]');
                  if (!e) return false; e.click(); return true; })()`);
      if (!ok) console.log(`  !! no [data-act="${arg}"]`);
    } else if (kind === 'sel') {
      await evaluate(`document.querySelector(${JSON.stringify(arg)}).click()`);
    } else if (kind === 'set') {
      const eq = arg.indexOf('=');
      const id = arg.slice(0, eq), value = arg.slice(eq + 1);
      await evaluate(`(() => { const e = document.getElementById('${id}');
        if (e.type === 'checkbox') e.checked = ${value === '1'};
        else e.value = ${JSON.stringify(value)};
        e.dispatchEvent(new Event('input', { bubbles: true })); })()`);
    } else if (kind === 'back') {
      await evaluate('history.back()');
    } else if (kind === 'hover' || kind === 'press' || kind === 'release') {
      // A real mouse over a real element, so :hover and :active are the
      // browser's own doing — the states cannot be reproduced by adding a
      // class, and they are where unreadable text hides. press holds the
      // button down until release.
      const at = kind === 'release' ? [0, 0] : await evaluate(
        `(() => { const e = document.querySelector(${JSON.stringify(arg)});
                  if (!e) return null; const r = e.getBoundingClientRect();
                  return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
      if (!at) { console.log(`  !! no ${arg}`); }
      else {
        const [x, y] = at;
        if (kind !== 'release') {
          await rpc(ws, 'Input.dispatchMouseEvent',
            { type: 'mouseMoved', x, y, buttons: 0 }, sessionId);
        }
        if (kind !== 'hover') {
          await rpc(ws, 'Input.dispatchMouseEvent', {
            type: kind === 'press' ? 'mousePressed' : 'mouseReleased',
            x, y, button: 'left', buttons: kind === 'press' ? 1 : 0, clickCount: 1,
          }, sessionId);
        }
      }
    } else if (kind === 'drag') {
      // drag:SEL=dy — press an element and pull it dy pixels down the screen
      // in steps, then let go. Chrome synthesizes pointer events from these,
      // which is what a drag handle actually listens to.
      const [selector, delta] = arg.split('=');
      const at = await evaluate(
        `(() => { const e = document.querySelector(${JSON.stringify(selector)});
                  if (!e) return null; const r = e.getBoundingClientRect();
                  return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
      if (!at) { console.log(`  !! no ${selector}`); }
      else {
        const [x, y] = at;
        const dy = parseInt(delta, 10);
        const send = (type, py, buttons) => rpc(ws, 'Input.dispatchMouseEvent',
          { type, x, y: py, button: 'left', buttons, clickCount: 1 }, sessionId);
        await send('mouseMoved', y, 0);
        await send('mousePressed', y, 1);
        for (let step = 1; step <= 8; step++) await send('mouseMoved', y + dy * step / 8, 1);
        await send('mouseReleased', y + dy, 0);
      }
    } else if (kind === 'sw' || kind === 'net') {
      // The two things this tool switches off for a dev loop, back on when
      // what is under test IS them: sw:on lets the service worker answer,
      // net:off pulls the plug. Together they are the offline story.
      if (kind === 'sw') {
        serviceWorker = arg === 'on';
        await rpc(ws, 'Network.setBypassServiceWorker',
          { bypass: !serviceWorker }, sessionId);
        await rpc(ws, 'Network.setCacheDisabled',
          { cacheDisabled: !serviceWorker }, sessionId);
      } else {
        await rpc(ws, 'Network.emulateNetworkConditions', {
          offline: arg === 'off', latency: 0,
          downloadThroughput: -1, uploadThroughput: -1,
        }, sessionId);
      }
    } else if (kind === 'run') {
      // run:FILE — evaluate a local script inside the page. For work too long
      // to pass as an argument: it imports the app's own modules and plays
      // thousands of games against them (tools/stress.js).
      const source = readFileSync(arg, 'utf8');
      const value = await evaluate(source);
      console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 1));
    } else if (kind === 'pre') {
      // Runs before the app's own scripts on the next load — for the things
      // it reads once at boot and that DevTools cannot emulate, chiefly
      // whether the browser thinks it is running as an installed app:
      //   'pre:matchMedia=display-mode: standalone' reload
      const [name, value] = arg.split('=');
      const source = name === 'matchMedia'
        ? `const real = window.matchMedia.bind(window);
           window.matchMedia = q => q.includes(${JSON.stringify(value)})
             ? { matches: true, media: q, addEventListener() {}, removeEventListener() {} }
             : real(q);`
        : arg;
      await rpc(ws, 'Page.addScriptToEvaluateOnNewDocument', { source }, sessionId);
    } else if (kind === 'reload') {
      // For anything the app only reads once, at boot — an emulated
      // display-mode, a stored setting written by an earlier step.
      // ignoreCache is a hard reload, and Chrome deliberately does not let a
      // service worker answer one — which is why a page reloaded this way
      // comes back uncontrolled. With the worker under test, reload softly.
      await rpc(ws, 'Page.reload', { ignoreCache: !serviceWorker }, sessionId);
      await boot();
    } else if (kind === 'wait') {
      await new Promise(r => setTimeout(r, parseInt(arg, 10)));
    } else if (kind === 'eval') {
      // Wrapped, so the expression may await — which is the whole point when
      // the thing worth inspecting is in IndexedDB.
      console.log('  = ' + JSON.stringify(
        await evaluate(`(async () => (${arg}))()`)));
    } else if (kind === 'theme' || kind === 'media') {
      // theme:dark — evening is the app's primary theme and a headless
      // Chrome is always in day. media:NAME=VALUE reaches the rest of what
      // Chrome can emulate (prefers-reduced-motion, forced-colors); the map
      // accumulates because one call replaces the whole list. display-mode
      // is NOT among them — for "is it installed", see pre: above.
      const [name, value] = kind === 'theme'
        ? ['prefers-color-scheme', arg] : arg.split('=');
      media.set(name, value);
      await rpc(ws, 'Emulation.setEmulatedMedia', {
        features: [...media].map(([n, v]) => ({ name: n, value: v })),
      }, sessionId);
    } else if (kind === 'shot') {
      const { data } = await rpc(ws, 'Page.captureScreenshot', {}, sessionId);
      writeFileSync(arg, Buffer.from(data, 'base64'));
    }
  } catch (error) {
    console.log('  !! ' + error.message.split('\n')[0]);
  }
  await new Promise(r => setTimeout(r, 120));
  console.log(step.padEnd(15) + ' -> ' + await evaluate(state));
}

// Anything the page shouted about while we were driving it.
const errors = await evaluate('window.__errs ? window.__errs.join(" | ") : ""');
if (errors) console.log('PAGE ERRORS: ' + errors);

await rpc(ws, 'Target.closeTarget', { targetId });
ws.close();
