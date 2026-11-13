// Service worker Poolette : l'appli s'ouvre hors ligne avec les dernières données connues.
const VERSION = 'poolette-v3';
const SHELL = ['./', 'index.html', 'styles.css', 'js/app.js', 'js/logic.js', 'js/config.js',
  'manifest.webmanifest', 'icons/icon.svg', 'pools.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const isData = new URL(req.url).pathname.includes('/data/') || req.url.endsWith('pools.json');
  // Données : réseau d'abord (fraîcheur), cache en secours. Reste : cache d'abord, mise à jour en arrière-plan.
  e.respondWith(isData ? networkFirst(req) : staleWhileRevalidate(req));
});

async function networkFirst(req) {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch {
    return (await cache.match(req)) || Response.error();
  }
}

async function staleWhileRevalidate(req) {
  const cache = await caches.open(VERSION);
  const hit = await cache.match(req);
  const net = fetch(req).then((res) => { if (res.ok) cache.put(req, res.clone()); return res; }).catch(() => null);
  return hit || (await net) || Response.error();
}
