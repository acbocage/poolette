// Poolette — interface (PWA). La logique des statuts est dans logic.js.
import { CONFIG } from './config.js';
import { evaluate, parisNow, addDays, toMin, slotsText, rangeText, haversineKm } from './logic.js';

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// localStorage peut être indisponible (navigation privée, données bloquées) : tout est optionnel.
const store = {
  get(k, d) { try { const v = localStorage.getItem('poolette.' + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('poolette.' + k, JSON.stringify(v)); } catch { /* ignoré */ } },
};

const S = {
  pools: [], hours: {}, exceptions: [], cal: null, generatedAt: null,
  pos: { ...CONFIG.defaultCenter, kind: 'default' }, geoMsg: '',
  moment: 'now', date: '', useRange: false, from: '12:00', to: '14:00',
  radius: Math.min(CONFIG.maxRadiusKm, store.get('radius', 10)),
  threshold: store.get('threshold', 60), onlyOpen: store.get('onlyOpen', false),
  favs: new Set(store.get('favs', [])), view: 'list',
  dist: {}, exactDist: false, map: null, markers: null,
};

const ICONS = {
  open: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M9.500 16.200 5.800 12.500l-1.400 1.400 5.100 5.100L20 8.500l-1.400-1.400-9.100 9.100Z"/></svg>',
  soon: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 5v5.400l4 2.400-.8 1.300L11 13V7h2Z"/></svg>',
  later: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 5v5.400l4 2.400-.8 1.300L11 13V7h2Z"/></svg>',
  closed: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="m6.400 5 5.600 5.600L17.600 5 19 6.400 13.400 12l5.600 5.600-1.400 1.400-5.600-5.600L6.400 19 5 17.600l5.600-5.600L5 6.400 6.400 5Z"/></svg>',
  unknown: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M11 18h2v-2h-2v2Zm1-16a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm0-14a4 4 0 0 0-4 4h2a2 2 0 1 1 4 0c0 2-3 1.800-3 5h2c0-2.200 3-2.500 3-5a4 4 0 0 0-4-4Z"/></svg>',
  star: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="m12 17.300-6.200 3.700 1.600-7L2 9.200l7.200-.6L12 2l2.800 6.600 7.200.6-5.400 4.800 1.600 7z"/></svg>',
  starOff: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" d="m12 17.300-6.200 3.700 1.600-7L2 9.200l7.200-.6L12 2l2.800 6.600 7.200.6-5.400 4.800 1.600 7z"/></svg>',
};
const COLORS = { open: 'var(--open)', soon: 'var(--soon)', later: 'var(--later)', closed: 'var(--closed)', unknown: 'var(--unknown)' };

// ---------------------------------------------------------------- données
async function getJson(url) {
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function loadData() {
  const [pools, hours, exc, cal] = await Promise.all([
    getJson('pools.json'), getJson('data/horaires.json'), getJson('data/exceptions.json'), getJson('data/calendar.json'),
  ]);
  S.pools = pools.pools; S.hours = hours.pools; S.generatedAt = hours.generated_at;
  S.exceptions = exc.exceptions; S.cal = cal;
}

// ---------------------------------------------------------------- distances
function straightDistances() {
  S.exactDist = false;
  S.dist = Object.fromEntries(S.pools.map((p) => [p.id, haversineKm(S.pos.lat, S.pos.lon, p.lat, p.lon)]));
}

async function routeDistances() {
  if (!CONFIG.orsKey) return;
  const near = S.pools.filter((p) => S.dist[p.id] <= CONFIG.maxRadiusKm * 1.6);
  if (!near.length) return;
  try {
    const r = await fetch('https://api.openrouteservice.org/v2/matrix/driving-car', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: CONFIG.orsKey },
      body: JSON.stringify({
        locations: [[S.pos.lon, S.pos.lat], ...near.map((p) => [p.lon, p.lat])],
        sources: [0], destinations: near.map((_, i) => i + 1), metrics: ['distance'], units: 'km',
      }),
    });
    if (!r.ok) throw new Error(String(r.status));
    const { distances } = await r.json();
    near.forEach((p, i) => { if (distances?.[0]?.[i] != null) S.dist[p.id] = distances[0][i]; });
    S.exactDist = true;
    render();
  } catch { /* repli : distance à vol d'oiseau déjà affichée */ }
}

function refreshDistances() { straightDistances(); render(); routeDistances(); }

// ---------------------------------------------------------------- position
function locate() {
  if (!('geolocation' in navigator)) { S.geoMsg = 'Géolocalisation indisponible'; render(); return; }
  $('#locLabel').textContent = 'Localisation…';
  navigator.geolocation.getCurrentPosition(
    (p) => {
      S.pos = { lat: p.coords.latitude, lon: p.coords.longitude, label: 'Ma position', kind: 'gps' };
      S.geoMsg = ''; refreshDistances();
    },
    (e) => {
      S.geoMsg = e.code === 1 ? 'Localisation refusée' : 'Position introuvable';
      render();
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
  );
}

// ---------------------------------------------------------------- requête
function buildQuery() {
  const today = parisNow().dateStr;
  if (S.moment === 'now') return { mode: 'now', dateStr: today };
  const dateStr = S.moment === 'today' ? today : S.moment === 'tomorrow' ? addDays(today, 1) : (S.date || today);
  if (S.useRange && S.from && S.to && toMin(S.to) > toMin(S.from)) {
    return { mode: 'range', dateStr, from: toMin(S.from), to: toMin(S.to) };
  }
  return { mode: 'day', dateStr };
}

function dayLabel(dateStr, today) {
  if (dateStr === today) return "Aujourd'hui";
  if (dateStr === addDays(today, 1)) return 'Demain';
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' })
    .format(new Date(Date.UTC(y, m - 1, d)));
}

const fmtKm = (km) => `${S.exactDist ? '' : '~'}${km < 10 ? km.toFixed(1).replace('.', ',') : Math.round(km)} km`;

// ---------------------------------------------------------------- rendu
function results() {
  const q = buildQuery();
  const rows = S.pools
    .map((pool) => ({ pool, km: S.dist[pool.id] ?? Infinity, r: evaluate({ pool, h: S.hours[pool.id], exceptions: S.exceptions, cal: S.cal, q, threshold: S.threshold }) }))
    .filter((x) => x.km <= S.radius || S.favs.has(x.pool.id)) // un favori s'affiche toujours, même hors rayon
    .filter((x) => !S.onlyOpen || ['open', 'soon', 'later'].includes(x.r.state));
  rows.sort((a, b) => (S.favs.has(b.pool.id) - S.favs.has(a.pool.id)) || a.km - b.km);
  return { q, rows };
}

function cardHtml({ pool, km, r }, q, today) {
  const fav = S.favs.has(pool.id);
  const chips = r.slots.length
    ? r.slots.map((s) => `<span class="chip${r.cur && s[0] === r.cur[0] ? ' on' : ''}">${rangeText(s)}</span>`).join('')
    : '';
  const slotsLine = chips ? `<div class="slots"><span class="when">${esc(dayLabel(q.dateStr, today))} :</span>${chips}</div>` : '';
  return `<article class="card ${r.state}" data-id="${esc(pool.id)}">
    <div class="badge" aria-hidden="true">${ICONS[r.state]}</div>
    <div class="body">
      <h2>${esc(pool.nom)} <span class="commune">(${esc(pool.commune)})</span></h2>
      <p class="headline">${esc(r.headline)}</p>
      ${r.detail ? `<p class="detail">${esc(r.detail)}</p>` : ''}
      ${slotsLine}
      ${r.note && r.note !== r.detail ? `<p class="note">${esc(r.note)}</p>` : ''}
      ${(r.warnings || []).map((w) => `<p class="warn">${esc(w)}</p>`).join('')}
    </div>
    <div class="side">
      <span class="dist">${fmtKm(km)}</span>
      <button class="fav" type="button" data-fav="${esc(pool.id)}" aria-pressed="${fav}" aria-label="${fav ? 'Retirer des favoris' : 'Ajouter aux favoris'} : ${esc(pool.nom)}">${fav ? ICONS.star : ICONS.starOff}</button>
    </div>
  </article>`;
}

function render() {
  const today = parisNow().dateStr;
  const { q, rows } = results();

  $('#locLabel').textContent = S.pos.label;
  $$('#moment button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.m === S.moment)));
  $('#dateRow').hidden = S.moment !== 'date';
  $('#rangeRow').hidden = S.moment === 'now';
  $('#rangeInputs').hidden = !(S.moment !== 'now' && S.useRange);
  $('#radiusOut').textContent = `${S.radius} km`;
  $$('.viewbar button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === S.view)));

  const count = (st) => rows.filter((x) => x.r.state === st).length;
  const bits = [];
  if (count('open')) bits.push(`${count('open')} ouverte${count('open') > 1 ? 's' : ''}`);
  if (count('soon')) bits.push(`${count('soon')} ${q.mode === 'range' ? 'en partie' : 'bientôt fermée' + (count('soon') > 1 ? 's' : '')}`);
  if (count('later')) bits.push(`${count('later')} ouvre${count('later') > 1 ? 'nt' : ''} plus tard`);
  const geo = S.pos.kind === 'default' ? ` · ${S.geoMsg ? S.geoMsg + ', d' : 'd'}istances depuis ${S.pos.label}` : '';
  $('#summary').textContent = rows.length
    ? `${bits.length ? bits.join(' · ') + ' · ' : ''}${rows.length} piscine${rows.length > 1 ? 's' : ''} dans ${S.radius} km${geo}`
    : '';

  $('#list').innerHTML = rows.length
    ? rows.map((x) => cardHtml(x, q, today)).join('')
    : `<p class="empty">Aucune piscine ${S.onlyOpen ? 'ouverte ' : ''}dans ${S.radius} km.<br>Élargis le rayon ou change de moment.</p>`;

  if (S.generatedAt) {
    const d = new Date(S.generatedAt);
    const when = new Intl.DateTimeFormat('fr-FR', { timeZone: 'Europe/Paris', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }).format(d);
    const stale = S.pools.filter((p) => evaluate({ pool: p, h: S.hours[p.id], exceptions: S.exceptions, cal: S.cal, q: { mode: 'now', dateStr: today } }).state === 'unknown').length;
    $('#fresh').textContent = `Horaires vérifiés le ${when}.${stale ? ` ${stale} piscine${stale > 1 ? 's' : ''} non vérifiée${stale > 1 ? 's' : ''} pour ce moment.` : ''}`;
  }
  if (S.view === 'map') renderMap(rows);
}

// ---------------------------------------------------------------- carte (Leaflet chargé à la demande)
let leafletLoading;
function loadLeaflet() {
  if (window.L) return Promise.resolve();
  leafletLoading ??= new Promise((resolve, reject) => {
    const css = document.createElement('link');
    css.rel = 'stylesheet'; css.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
    document.head.append(css);
    const js = document.createElement('script');
    js.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
    js.onload = resolve; js.onerror = () => reject(new Error('Leaflet indisponible'));
    document.head.append(js);
  });
  return leafletLoading;
}

async function renderMap(rows) {
  try { await loadLeaflet(); } catch { $('#map').textContent = 'Carte indisponible hors connexion.'; return; }
  const L = window.L;
  if (!S.map) {
    S.map = L.map('map', { zoomControl: true }).setView([S.pos.lat, S.pos.lon], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '© OpenStreetMap' }).addTo(S.map);
    S.markers = L.layerGroup().addTo(S.map);
  }
  S.markers.clearLayers();
  const style = getComputedStyle(document.documentElement);
  const color = (st) => style.getPropertyValue('--' + st).trim() || '#888';
  const pts = [[S.pos.lat, S.pos.lon]];
  L.circleMarker([S.pos.lat, S.pos.lon], { radius: 7, color: '#fff', weight: 2, fillColor: color('later'), fillOpacity: 1 })
    .bindTooltip('Toi').addTo(S.markers);
  rows.forEach(({ pool, r }) => {
    pts.push([pool.lat, pool.lon]);
    L.circleMarker([pool.lat, pool.lon], { radius: 11, color: '#fff', weight: 2, fillColor: color(r.state), fillOpacity: 1 })
      .bindPopup(`<strong>${esc(pool.nom)} (${esc(pool.commune)})</strong><br>${esc(r.headline)}${r.slots.length ? '<br>' + esc(slotsText(r.slots)) : ''}`)
      .addTo(S.markers);
  });
  setTimeout(() => { S.map.invalidateSize(); if (pts.length > 1) S.map.fitBounds(pts, { padding: [30, 30], maxZoom: 14 }); }, 50);
}

function setView(v) {
  S.view = v;
  $('#list').hidden = v !== 'list';
  $('#map').hidden = v !== 'map';
  render();
}

// ---------------------------------------------------------------- événements
function bind() {
  $('#moment').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-m]'); if (!b) return;
    S.moment = b.dataset.m; render();
  });
  $('#date').addEventListener('change', (e) => { S.date = e.target.value; render(); });
  $('#useRange').addEventListener('change', (e) => { S.useRange = e.target.checked; render(); });
  $('#from').addEventListener('change', (e) => { S.from = e.target.value; render(); });
  $('#to').addEventListener('change', (e) => { S.to = e.target.value; render(); });
  $('#radius').addEventListener('input', (e) => { S.radius = Number(e.target.value); store.set('radius', S.radius); render(); });
  $('#onlyOpen').addEventListener('change', (e) => { S.onlyOpen = e.target.checked; store.set('onlyOpen', S.onlyOpen); render(); });
  $('#threshold').addEventListener('change', (e) => { S.threshold = Number(e.target.value); store.set('threshold', S.threshold); render(); });
  $('#btnLocate').addEventListener('click', locate);
  $('.viewbar').addEventListener('click', (e) => { const b = e.target.closest('button[data-v]'); if (b) setView(b.dataset.v); });
  $('#list').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-fav]'); if (!b) return;
    const id = b.dataset.fav;
    S.favs.has(id) ? S.favs.delete(id) : S.favs.add(id);
    store.set('favs', [...S.favs]); render();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') { locate(); render(); }
  });
  setInterval(render, 60_000);
}

async function init() {
  $('#radius').max = CONFIG.maxRadiusKm; $('#radius').value = S.radius;
  $('#onlyOpen').checked = S.onlyOpen; $('#threshold').value = String(S.threshold);
  $('#date').value = parisNow().dateStr; $('#date').min = parisNow().dateStr;
  bind();
  try {
    await loadData();
  } catch {
    $('#list').innerHTML = '<p class="empty">Impossible de charger les horaires.<br>Vérifie ta connexion puis recharge la page.</p>';
    return;
  }
  straightDistances(); render(); locate();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
}
init();
