// Poolette — logique pure (sans DOM). Utilisée par l'appli et par tests/logic.test.html.
// Toutes les dates/heures sont raisonnées à l'heure de Paris, jamais à celle du téléphone.

export const KEYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
export const STALE_HOURS = 48;

// Enchaînement des périodes quand une piscine n'a pas de tableau dédié à une vacance.
const CHAIN = {
  toussaint: ['automne_hiver', 'vacances'],
  hiver: ['automne_hiver', 'vacances'],
  noel: ['noel', 'automne_hiver', 'vacances'],
  printemps: ['printemps', 'vacances'],
  ete: ['ete'],
};

export const toMin = (s) => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };

export function fmtMin(min) {
  const h = Math.floor(min / 60), m = min % 60;
  return m ? `${h}h${String(m).padStart(2, '0')}` : `${h}h`;
}

export const rangeText = ([s, e]) => `${fmtMin(s)}–${fmtMin(e)}`;
export const slotsText = (slots) => slots.map(rangeText).join(' · ');

export function parisNow(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date);
  const g = (t) => parts.find((p) => p.type === t).value;
  return { dateStr: `${g('year')}-${g('month')}-${g('day')}`, min: Number(g('hour')) * 60 + Number(g('minute')) };
}

const utc = (dateStr, add = 0) => {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + add));
};
export const dowOf = (dateStr) => utc(dateStr).getUTCDay();
export const addDays = (dateStr, n) => utc(dateStr, n).toISOString().slice(0, 10);

export function vacationKind(dateStr, cal) {
  const v = (cal?.vacances || []).find((x) => x.start <= dateStr && dateStr < x.end);
  return v ? v.kind : null;
}

/** Horaires d'une piscine pour un jour. -> { known, slots (minutes), reason, note } */
export function scheduleFor(pool, h, exceptions, dateStr, cal) {
  const ex = (exceptions || []).find((e) => e.pool_id === pool.id && e.from <= dateStr && dateStr <= e.to);
  if (ex) {
    return ex.type === 'closed'
      ? { known: true, slots: [], note: ex.note || 'Fermeture exceptionnelle', exceptional: true }
      : { known: true, slots: (ex.slots || []).map(([a, b]) => [toMin(a), toMin(b)]), note: ex.note, exceptional: true };
  }
  const kind = vacationKind(dateStr, cal);
  const periods = h?.periods || {};
  if (pool.saison === 'ete' && kind !== 'ete' && !Object.keys(periods).length) {
    return { known: true, slots: [], note: "Piscine d'été : fermée hors saison estivale" };
  }
  const ferie = cal?.feries?.[dateStr];
  if (ferie) return { known: false, reason: `Jour férié (${ferie}) : horaires non publiés` };
  const chain = kind ? CHAIN[kind] : ['scolaire'];
  const id = chain.find((c) => periods[c]);
  if (!id) {
    return { known: false, reason: kind === 'ete' ? "Horaires d'été non publiés" : 'Horaires de cette période non publiés' };
  }
  const slots = (periods[id].schedule[KEYS[dowOf(dateStr)]] || []).map(([a, b]) => [toMin(a), toMin(b)]);
  return { known: true, slots };
}

export function isStale(h, now = new Date()) {
  if (!h?.checked_at) return true;
  return now - new Date(h.checked_at) > STALE_HOURS * 3600 * 1000;
}

/**
 * Statut d'une piscine pour une requête.
 * q = { mode: 'now' | 'day' | 'range', dateStr, from?, to? }  (from/to en minutes)
 * état : open (vert) | soon (orange) | later (ouvre plus tard) | closed (rouge) | unknown (gris)
 */
export function evaluate({ pool, h, exceptions, cal, q, now = new Date(), threshold = 60 }) {
  const np = parisNow(now);
  const warnings = (pool.warnings || [])
    .filter((w) => (!w.from || w.from <= q.dateStr) && (!w.until || q.dateStr <= w.until))
    .map((w) => w.text);
  const out = (state, headline, extra = {}) => ({ state, headline, warnings, slots: [], ...extra });

  if (!h) return out('unknown', 'Horaires indisponibles', { detail: 'Source non lue pour le moment' });
  if (isStale(h, now)) {
    return out('unknown', 'Horaires non vérifiés', {
      detail: h.checked_at ? `Dernière vérification : ${new Date(h.checked_at).toLocaleDateString('fr-FR')}` : 'Jamais vérifiés',
    });
  }
  const sch = scheduleFor(pool, h, exceptions, q.dateStr, cal);
  if (!sch.known) return out('unknown', 'Horaires non vérifiés', { detail: sch.reason });

  const slots = sch.slots;
  const base = { slots, note: sch.note, exceptional: !!sch.exceptional };
  const isToday = q.dateStr === np.dateStr;
  const m = np.min;

  const live = () => { // statut à l'instant présent
    const cur = slots.find(([s, e]) => s <= m && m < e);
    if (cur) {
      const rem = cur[1] - m;
      return rem >= threshold
        ? out('open', `Ouvert jusqu'à ${fmtMin(cur[1])}`, { ...base, cur, remaining: rem })
        : out('soon', `Ferme bientôt · à ${fmtMin(cur[1])}`, { ...base, cur, remaining: rem, detail: `Dans ${rem} min` });
    }
    const next = slots.find(([s]) => s > m);
    if (next) return out('closed', 'Fermé', { ...base, detail: `Rouvre à ${fmtMin(next[0])}`, next });
    return out('closed', 'Fermé', { ...base, detail: slots.length ? "Plus d'ouverture aujourd'hui" : 'Fermé toute la journée' });
  };

  if (q.mode === 'now') return live();

  if (q.mode === 'day') {
    if (isToday) {
      const r = live();
      if (r.state === 'closed' && r.next) return { ...r, state: 'later', headline: `Ouvre à ${fmtMin(r.next[0])}`, detail: undefined };
      return r;
    }
    return slots.length
      ? out('open', 'Ouvert ce jour', base)
      : out('closed', 'Fermé', { ...base, detail: sch.note || 'Fermé toute la journée' });
  }

  // plage horaire
  const [a, b] = [q.from, q.to];
  const cover = slots.find(([s, e]) => s <= a && e >= b);
  if (cover) return out('open', `Ouvert sur ta plage · jusqu'à ${fmtMin(cover[1])}`, { ...base, cur: cover });
  const overlap = slots.filter(([s, e]) => s < b && e > a);
  if (overlap.length) {
    const clipped = overlap.map(([s, e]) => [Math.max(s, a), Math.min(e, b)]);
    return out('soon', 'Ouvert en partie sur ta plage', { ...base, detail: slotsText(clipped) });
  }
  return out('closed', 'Fermé sur ta plage', { ...base, detail: slots.length ? undefined : (sch.note || 'Fermé toute la journée') });
}

/** Distance à vol d'oiseau en km. */
export function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371, rad = (x) => (x * Math.PI) / 180;
  const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}
