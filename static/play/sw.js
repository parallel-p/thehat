// Service worker: the part that makes /play work with no network.
//
// A classic worker, not a module — Safari only learned module workers
// recently and there is nothing here worth an import for.
//
// To ship a change to the app: deploy. That is the whole procedure. Every
// shell file is refreshed in the background on each open (see the fetch
// handler), so an edit to app.css or any js file reaches an installed app on
// the open after the one where it was picked up.
//
// CACHE only needs bumping when a file is REMOVED from SHELL — renaming it
// drops the old entry, which would otherwise sit in storage forever. Adding a
// file needs nothing: it is fetched and cached the first time it is asked for.

const CACHE = 'hat-play-v1';

// The dictionary is deliberately not here: it is fetched once and kept in
// IndexedDB, because the app needs it bucket by bucket rather than as a blob.
const SHELL = [
  '/play',
  '/play/app.css',
  '/play/manifest.webmanifest',
  '/play/js/main.js',
  '/play/js/db.js',
  '/play/js/dictionary.js',
  '/play/js/log.js',
  '/play/js/audio.js',
  '/play/js/clock.js',
  '/play/js/game.js',
  '/play/js/deathmatch.js',
  '/play/icons/hat-192.png',
  '/play/icons/hat-512.png',
  '/play/icons/hat-maskable-512.png',
  // The site's stylesheet and its fonts: the app borrows the whole design
  // language, so offline has to include it or the app loads unstyled.
  '/assets/hat.css',
  '/assets/fonts/playfair-cyrillic.woff2',
  '/assets/fonts/playfair-latin.woff2',
  '/assets/fonts/playfair-italic-cyrillic.woff2',
  '/assets/fonts/playfair-italic-latin.woff2',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      // Individually, so one 404 cannot fail the whole install.
      .then(cache => Promise.all(SHELL.map(
        url => cache.add(url).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(
        names.filter(name => name !== CACHE).map(name => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;          // uploads are the app's job

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // The dictionary: network first so a fresh list is picked up, falling back to
  // whatever was cached. The app keeps its own copy regardless, so this only
  // matters on a first run.
  if (url.pathname.startsWith('/api/v2/dictionary')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Navigations resolve to the shell: the app is one document, so there is no
  // route that can be missing offline.
  const isShell = request.mode === 'navigate'
    || url.pathname.startsWith('/play') || url.pathname.startsWith('/assets');
  if (!isShell) return;                          // the rest of the site is not ours

  const key = request.mode === 'navigate' ? '/play' : request;

  // Stale while revalidate, and the "revalidate" half is the whole point of
  // deploying anything.
  //
  // Cache-first alone would have been a trap: a browser only re-fetches this
  // worker, so if the worker itself has not changed, nothing would ever
  // invalidate app.css or a js file and an installed app would serve the
  // version it first saw for good. Shipping a fix would then mean remembering
  // to bump CACHE below by hand, every single time, or it silently reaches
  // nobody. Instead every shell response is handed over from cache at once and
  // refreshed behind the reader's back; the new files are on disk before they
  // close the app and are what opens next time.
  //
  // `cache: 'no-cache'` on the refetch, so it is a conditional request against
  // the server rather than a read of App Engine's ten-minute HTTP cache: a
  // 304 costs nothing and an update is never a deploy plus ten minutes.
  event.respondWith(
    caches.match(key).then((hit) => {
      const fresh = fetch(request, { cache: 'no-cache' }).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(key, copy));
        }
        return response;
      });
      // Offline with nothing cached is the only case with nothing to give.
      return hit || fresh;
    }).catch(() => caches.match(key))
  );
});
