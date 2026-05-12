{% load static %}// 1983 Law — service worker
// Version {{ cache_version }}
//
// Strategy:
//   * App shell (CSS/JS/icons + a few key pages) precached on install.
//   * Navigation requests: network-first, fall back to cache, then to the
//     /documents/start/ entry page if we're offline and have nothing cached
//     for the requested URL.
//   * Same-origin static assets: cache-first, populate on miss.
//   * /admin/, /api/, /stripe/, and any non-GET requests are ignored — they
//     pass through unmodified.
//
// The outbox (offline POST replay) lives in the page, not the SW, because
// quick-add submits need session cookies + CSRF tokens that are easier to
// reason about from the page context.

const CACHE = 'auditfile-{{ cache_version }}';
const APP_SHELL = [
    '/documents/start/',
    '/documents/',
    '/accounts/login/',
    '{% static "css/app-theme.css" %}',
    '{% static "manifest.webmanifest" %}',
    '{% static "images/pwa/icon-192.png" %}',
    '{% static "images/pwa/icon-512.png" %}',
    '{% static "images/pwa/icon-512-maskable.png" %}',
    '{% static "images/pwa/apple-touch-icon.png" %}',
    '{% static "images/favicon.svg" %}',
    '{% static "images/gavel-icon.svg" %}',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE).then((cache) =>
            // Best-effort: a single 404 inside addAll() would otherwise reject
            // the entire install. Add each URL independently and swallow misses.
            Promise.all(APP_SHELL.map((u) =>
                cache.add(u).catch(() => null)
            ))
        )
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;

    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;
    if (url.pathname.startsWith('/admin/')) return;
    if (url.pathname.startsWith('/api/')) return;
    if (url.pathname.startsWith('/stripe/')) return;
    if (url.pathname === '/sw.js') return;

    // Navigation requests — network-first so live data stays fresh.
    if (req.mode === 'navigate') {
        event.respondWith(
            fetch(req)
                .then((res) => {
                    if (res && res.ok) {
                        const copy = res.clone();
                        caches.open(CACHE).then((c) => c.put(req, copy));
                    }
                    return res;
                })
                .catch(() =>
                    caches.match(req).then((cached) =>
                        cached || caches.match('/documents/start/')
                    )
                )
        );
        return;
    }

    // Static / same-origin asset — cache-first.
    event.respondWith(
        caches.match(req).then((cached) => {
            if (cached) return cached;
            return fetch(req).then((res) => {
                if (res && res.ok && res.type === 'basic') {
                    const copy = res.clone();
                    caches.open(CACHE).then((c) => c.put(req, copy));
                }
                return res;
            }).catch(() => cached);
        })
    );
});

// Allow the page to ask the SW to refresh its cache version on demand.
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
