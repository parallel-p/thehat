// Timers that survive a locked screen, and keeping the screen unlocked.
//
// setInterval is throttled in a background tab and stops outright when an iOS
// screen locks, so counting ticks loses time exactly when a round is being
// played. Everything here is derived from Date.now() against a start stamp;
// the interval only decides how often to repaint.

/**
 * Call `onTick(elapsedMs)` about every `everyMs` until stop() is called.
 * The elapsed time is measured, never accumulated.
 */
export function ticker(onTick, everyMs = 100) {
  const started = Date.now();
  let handle = setInterval(() => onTick(Date.now() - started), everyMs);
  let stopped = false;

  // Coming back from a locked screen: repaint at once rather than waiting for
  // the next tick, so the clock is never seen showing a stale number.
  const onVisible = () => {
    if (!stopped && document.visibilityState === 'visible') {
      onTick(Date.now() - started);
    }
  };
  document.addEventListener('visibilitychange', onVisible);

  return {
    elapsed: () => Date.now() - started,
    stop() {
      if (stopped) return;
      stopped = true;
      clearInterval(handle);
      document.removeEventListener('visibilitychange', onVisible);
    },
  };
}

// -- wake lock -------------------------------------------------------------
// Chrome on Android and Safari from 16.4. The lock is dropped whenever the tab
// hides, so it has to be re-taken on the way back; below 16.4 there is no
// fallback worth having, and a 20-second round usually beats the display
// timeout anyway.

let lock = null;
let wanted = false;

async function take() {
  if (!wanted || !navigator.wakeLock || lock) return;
  try {
    lock = await navigator.wakeLock.request('screen');
    lock.addEventListener('release', () => { lock = null; });
  } catch (_) { /* denied, or the tab is hidden; not worth reporting */ }
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') take();
});

export function keepAwake(on) {
  wanted = on;
  if (on) {
    take();
  } else if (lock) {
    lock.release().catch(() => {});
    lock = null;
  }
}
