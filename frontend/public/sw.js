const CACHE_NAME = 'ovelhainvest-v1';
const SHELL_URLS = [
  '/',
  '/dashboard',
  '/signals',
  '/assets',
  '/performance',
  '/projections',
  '/tax',
  '/journal',
  '/config',
  '/reports',
  '/manifest.json',
];

// On install: cache shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(SHELL_URLS).catch((err) => {
        console.warn('[SW] Shell pre-cache failed (some URLs may not exist yet):', err);
      });
    })
  );
  self.skipWaiting();
});

// On activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// On fetch
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API calls — network only, never cache
  if (
    url.pathname.startsWith('/api/') ||
    (url.hostname === 'localhost' && url.port === '8000') ||
    url.hostname.includes('supabase.co')
  ) {
    return; // let it fall through to network
  }

  // Static assets — cache first
  if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Navigation requests — network first, fallback to cached shell
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match('/dashboard') || caches.match('/');
        })
    );
    return;
  }

  // Images — cache first
  if (event.request.destination === 'image') {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
            }
            return response;
          })
          .catch(() => cached);
      })
    );
    return;
  }
});
