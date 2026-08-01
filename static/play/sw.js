// Service worker: the part that makes /play work with no network.
//
// A classic worker, not a module — Safari only learned module workers
// recently and there is nothing here worth an import for.
//
// Bump CACHE whenever a shell file changes. The old cache is deleted on
// activate, so a deploy cannot leave a half-old app behind.

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

  // Navigations always resolve to the shell: the app is one document, so there
  // is no route that can be missing offline.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/play'))
    );
    return;
  }

  if (!url.pathname.startsWith('/play') && !url.pathname.startsWith('/assets')) {
    return;                                      // the rest of the site is not ours
  }

  event.respondWith(
    caches.match(request).then(hit => hit || fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(request, copy));
      }
      return response;
    }))
  );
});
