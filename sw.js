/* Offline support + update detection.
   App files are served from the cache so the app opens instantly and works offline.
   The page asks for a check when it opens (and when it comes back to the foreground); the worker then
   re-downloads the app files, and if any of them changed it stores the new copies and tells the page,
   which shows "새 버전이 있어요". No version number has to be bumped by hand: editing words.json or
   index.html and redeploying is enough. */
const CACHE = 'evb-app';
const FONT_CACHE = 'evb-fonts';
const CORE = ['./', 'words.json', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png', 'icons/favicon-32.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE.map(u => new Request(u, { cache: 'no-cache' })))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== FONT_CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// the page's address may be "./", "./index.html" or carry a #hash; all of them are the same app page
const keyFor = req => {
  const u = new URL(req.url);
  if (req.mode === 'navigate' || u.pathname.endsWith('/index.html')) return new URL('./', self.registration.scope).href;
  u.hash = ''; u.search = '';
  return u.href;
};

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  if (u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com') {
    e.respondWith(caches.open(FONT_CACHE).then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok || res.type === 'opaque') c.put(req, res.clone());
      return res;
    }).catch(() => Response.error()));
    return;
  }
  if (u.origin !== self.location.origin || u.pathname.endsWith('/sw.js')) return;
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const key = keyFor(req);
    const hit = await c.match(key);
    if (hit) return hit;
    const res = await fetch(req, { cache: 'no-cache' });
    if (res.ok) c.put(key, res.clone());
    return res;
  })().catch(() => caches.match(keyFor(req)).then(r => r || Response.error())));
});

async function bodyOf(res) { return res ? new Uint8Array(await res.clone().arrayBuffer()) : null; }
const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => v === b[i]);

// download every app file again; store and report the ones that changed
async function checkForUpdate() {
  const c = await caches.open(CACHE);
  const changed = [];
  await Promise.all(CORE.map(async path => {
    const key = new URL(path, self.registration.scope).href;
    try {
      const res = await fetch(key, { cache: 'no-cache' });
      if (!res.ok) return;
      // a broken words.json must never replace a working one (the app would stop opening, even offline)
      if (path === 'words.json') {
        try { const d = await res.clone().json(); if (!d || !Array.isArray(d.words) || !d.words.length) return; } catch (err) { return; }
      }
      const old = await c.match(key);
      if (!same(await bodyOf(old), await bodyOf(res))) {
        if (old) changed.push(path);
        await c.put(key, res);
      }
    } catch (err) { /* offline: keep what we have */ }
  }));
  return changed;
}

self.addEventListener('message', e => {
  if (!e.data || e.data.type !== 'check') return;
  const port = e.ports && e.ports[0];
  e.waitUntil(checkForUpdate().then(changed => { if (port) port.postMessage({ type: 'checked', changed }); }));
});
