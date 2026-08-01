// IndexedDB, wrapped just enough to be readable.
//
// Everything the app keeps lives here rather than half here and half in
// localStorage: Safari evicts a site's storage as one lump, so having one
// store means one recovery path (see dictionary.js) instead of two, and no
// state where the settings survived but the dictionary did not.

const NAME = 'hat';
const VERSION = 1;

// buckets: one record per difficulty 0..100, each { i, words[] }
// meta:    etag, settings, the used-word ring, deviceId
// outbox:  finished game logs waiting to reach the server
const STORES = ['buckets', 'meta', 'outbox'];

let opening = null;

function open() {
  if (opening) return opening;
  opening = new Promise((resolve, reject) => {
    const request = indexedDB.open(NAME, VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      for (const store of STORES) {
        if (!db.objectStoreNames.contains(store)) db.createObjectStore(store);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  return opening;
}

function run(store, mode, body) {
  return open().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode);
    const result = body(tx.objectStore(store));
    tx.oncomplete = () => resolve(result && result.value !== undefined
      ? result.value : (result ? result.result : undefined));
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  }));
}

export function get(store, key) {
  return run(store, 'readonly', s => s.get(key));
}

export function put(store, key, value) {
  return run(store, 'readwrite', s => s.put(value, key));
}

export function del(store, key) {
  return run(store, 'readwrite', s => s.delete(key));
}

export function all(store) {
  return run(store, 'readonly', s => s.getAll());
}

export function keys(store) {
  return run(store, 'readonly', s => s.getAllKeys());
}

/** Write many records in one transaction — used for the 101 buckets. */
export function putMany(store, entries) {
  return open().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const objectStore = tx.objectStore(store);
    objectStore.clear();
    for (const [key, value] of entries) objectStore.put(value, key);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  }));
}

/**
 * Ask the browser not to evict us.
 *
 * Safari clears site data after about a week without a visit, which would
 * silently take the dictionary and any unsent games with it. An installed PWA
 * is usually granted this without a prompt; a tab usually is not, and that is
 * fine — the app recovers by re-downloading, it just cannot do it offline.
 */
export async function persist() {
  try {
    if (navigator.storage && navigator.storage.persist) {
      return await navigator.storage.persist();
    }
  } catch (_) { /* not fatal, ever */ }
  return false;
}
