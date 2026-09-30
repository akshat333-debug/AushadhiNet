/**
 * Minimal offline-first service worker (modular-plan.md step 43): caches
 * the officer PWA's app shell so it reloads offline (project.md's
 * offline-tolerant officer PWA requirement). Data (orders, stock) is not
 * cached here -- only the shell needed to show a usable "you're offline"
 * screen rather than a blank tab.
 */
const CACHE_NAME = "aushadhinet-shell-v2";
const SHELL_URLS = ["/", "/orders", "/agent", "/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  // Network first: cache-first pinned visitors to whatever shell they saw first, even after a deploy.
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        if (res.ok && new URL(event.request.url).origin === self.location.origin) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/")))
  );
});
