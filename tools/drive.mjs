// Drive /play in a headless Chrome over DevTools Protocol, and print TEXT.
//
//   make browser                       # once: a headless Chrome that stays up
//   node tools/drive.mjs http://localhost:8901/play click:new-game back
//
// Steps: click:ACT  sel:CSS  set:id=value  back  wait:MS  eval:JS  shot:FILE
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

import { writeFileSync } from 'node:fs';

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

await rpc(ws, 'Page.navigate', { url }, sessionId);

// Wait for the app to boot — a real condition, not a guessed sleep.
const deadline = Date.now() + 20000;
while (Date.now() < deadline) {
  const screen = await evaluate('document.body.dataset.screen || ""').catch(() => '');
  if (screen && screen !== 'loading') break;
  await new Promise(r => setTimeout(r, 100));
}

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
    } else if (kind === 'wait') {
      await new Promise(r => setTimeout(r, parseInt(arg, 10)));
    } else if (kind === 'eval') {
      // Wrapped, so the expression may await — which is the whole point when
      // the thing worth inspecting is in IndexedDB.
      console.log('  = ' + JSON.stringify(
        await evaluate(`(async () => (${arg}))()`)));
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
