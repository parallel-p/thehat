// Just enough browser for /play's storage layer to run in node.
//
// The alternative was to mock db.js away and test dictionary.js and log.js
// against a stub, which would have tested the stub: both modules are almost
// entirely *about* what they read back out of storage — the ring that stops a
// word repeating, the outbox that must not lose a game — and a Map pretending
// to be IndexedDB shares none of the properties that make those hard. So db.js
// is left alone and given a store to talk to.
//
// Three of its properties are load-bearing and reproduced on purpose:
//
//   * **keys come back sorted, numbers before strings.** dictionary.js writes
//     the 101 buckets under keys 0..100 and reads them back with getAll(),
//     positionally — `stored[index]` is bucket `index`. A store that answered
//     in insertion order would pass every test here and shuffle the dictionary
//     in a browser.
//   * **values are copied in and out.** Real IndexedDB structured-clones, so
//     the ring dictionary.js holds is not the ring on disk. Handing back the
//     same object would let a read-modify-write "work" without the write.
//   * **completion is asynchronous.** db.js assigns `tx.oncomplete` after
//     running the request, which only works if completion cannot fire during
//     the call. Firing synchronously would hang every read.
//
// Node runs each test file in its own process, so installing globals here is
// not something one test file can do to another.

// -- IndexedDB ---------------------------------------------------------------

const stores = new Map();       // name -> Map(key, structured-cloned value)
let version = 0;

/** IndexedDB's key order, for the keys this app actually uses. */
function compareKeys(a, b) {
  const rank = key => (typeof key === 'number' ? 0 : 1);
  if (rank(a) !== rank(b)) return rank(a) - rank(b);
  return a < b ? -1 : a > b ? 1 : 0;
}

function sortedKeys(data) {
  return [...data.keys()].sort(compareKeys);
}

/** A request whose `result` is already known — which, in memory, it is. */
function request(result) {
  return { result, error: null };
}

function connection() {
  return {
    objectStoreNames: { contains: name => stores.has(name) },
    createObjectStore(name) { stores.set(name, new Map()); },
    transaction(name) {
      // Real IndexedDB throws NotFoundError here and now, not on the request,
      // which is what turns a typo'd store name into a rejected promise
      // instead of a hang.
      const data = stores.get(name);
      if (!data) throw new Error(`NotFoundError: no object store ${name}`);
      const tx = { oncomplete: null, onerror: null, onabort: null, error: null };
      queueMicrotask(() => { if (tx.oncomplete) tx.oncomplete(); });
      tx.objectStore = () => ({
        get: key => request(structuredClone(data.get(key))),
        put: (value, key) => {
          data.set(key, structuredClone(value));
          return request(undefined);
        },
        delete: (key) => { data.delete(key); return request(undefined); },
        clear: () => { data.clear(); return request(undefined); },
        getAll: () => request(
          sortedKeys(data).map(key => structuredClone(data.get(key)))),
        getAllKeys: () => request(sortedKeys(data)),
      });
      return tx;
    },
  };
}

const indexedDB = {
  open(_name, wanted) {
    const req = { result: connection(), error: null,
                  onupgradeneeded: null, onsuccess: null, onerror: null };
    const upgrading = wanted > version;
    version = Math.max(version, wanted);
    queueMicrotask(() => {
      if (upgrading && req.onupgradeneeded) req.onupgradeneeded();
      if (req.onsuccess) req.onsuccess();
    });
    return req;
  },
};

/** Everything in a store, as plain data — for asserting on what was written. */
export function stored(name) {
  const data = stores.get(name);
  if (!data) return new Map();
  return new Map(sortedKeys(data).map(key => [key, structuredClone(data.get(key))]));
}

/** Empty every store, keeping them in existence: db.js only upgrades once. */
export function wipe() {
  for (const data of stores.values()) data.clear();
}

// -- fetch -------------------------------------------------------------------

let responder = () => { throw new Error('no fetch handler installed'); };

/** The requests fetch has been asked for, newest last. */
export const calls = [];

/**
 * Answer fetch with `handler(url, options)`. Return a `{status, body, headers}`
 * shape, or throw to be the network being gone.
 */
export function serve(handler) {
  responder = handler;
  calls.length = 0;
}

/** A response body with the two fields the app reads off it. */
export function reply(status, body, headers = {}) {
  const lower = new Map(
    Object.entries(headers).map(([key, value]) => [key.toLowerCase(), value]));
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: name => lower.get(name.toLowerCase()) ?? null },
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

// -- installation ------------------------------------------------------------

let online = true;

/** What the app thinks of the network. log.js will not flush offline. */
export function setOnline(value) { online = value; }

/**
 * Put the lot on globalThis. Call once, at the top of a test file, before the
 * first call into the app — the modules touch none of this at import time, so
 * "before the first call" is all that is required.
 */
export function install() {
  globalThis.indexedDB = indexedDB;
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options: options || {} });
    return responder(String(url), options || {});
  };
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    get: () => ({ onLine: online, userAgent: 'node', storage: undefined }),
  });
  // clock.js listens for visibilitychange at module scope, so a document has
  // to exist before it is imported. Nothing here dispatches one; the timing
  // tests drive Date.now instead, which is what the module is built on.
  globalThis.document = {
    visibilityState: 'visible',
    addEventListener() {},
    removeEventListener() {},
  };
}

// -- time --------------------------------------------------------------------

const realNow = Date.now;

/**
 * A clock the test moves by hand.
 *
 * clock.js exists because counting ticks loses time when a screen locks, and
 * everything in it is derived from Date.now() instead. Testing that claim
 * means being able to jump the clock without waiting out a round in real time.
 */
export function fakeClock(start = 1_700_000_000_000) {
  let at = start;
  Date.now = () => at;
  return {
    advance(ms) { at += ms; },
    restore() { Date.now = realNow; },
  };
}
