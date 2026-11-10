#!/usr/bin/env python3
"""Poolette - mise à jour des données (horaires des piscines + calendrier).

Lancé chaque jour par GitHub Actions (et à la main : `python scripts/update_data.py`).

- Toulouse : lecture déterministe des pages officielles (aucune IA, aucun coût).
- Exceptions (bandeaux « En bref ») et pages libres (L'Union) : extraction par l'API Claude,
  seulement si ANTHROPIC_API_KEY est défini ET si le contenu a changé depuis la veille.
- Calendrier : vacances scolaires zone C (Éducation nationale) + jours fériés (État).

Stdlib uniquement, aucune dépendance à installer.
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = SITE / "data"
UA = "Poolette/1.0 (usage personnel; mise a jour quotidienne)"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}
MODEL = os.environ.get("POOLETTE_MODEL", "claude-haiku-5-5")


# ---------------------------------------------------------------- utilitaires
def now_utc():
    return datetime.now(timezone.utc)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def html_to_text(fragment):
    fragment = re.sub(r"(?is)<(script|style).*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", fragment)
    text = re.sub(r"(?s)<[^>]+>", " ", fragment)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
            .replace("&rsquo;", "'").replace("&quot;", '"'))
    text = re.sub(r"[ \t\r\f\v ]+", " ", text)
    return re.sub(r"\n\s*", "\n", text).strip()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------- horaires : pages Toulouse
def period_kinds(title):
    """Une section peut couvrir plusieurs vacances (ex. « Toussaint et Noël ») : on renvoie tous les ids."""
    t = strip_accents(title).lower()
    if ("ete" in re.findall(r"[a-z]+", t) or "estival" in t) and "hors ete" not in t and "hors-ete" not in t:
        return ["ete"]
    kinds = []
    if "toussaint" in t or "automne" in t:
        kinds.append("toussaint")
    if "noel" in t:
        kinds.append("noel")
    if "hiver" in t:
        kinds.append("hiver")
    if "automne" in t or "hiver" in t:
        kinds.append("automne_hiver")
    if "printemps" in t:
        kinds.append("printemps")
    if kinds:
        return kinds
    if "vacances" in t:
        return ["vacances"]
    if "scolaire" in t:
        return ["scolaire"]
    return []


TIME = r"(\d{1,2})\s*h\s*(\d{2})?"
SLOT = re.compile(TIME + r"\s*[-–à]\s*" + TIME)


def parse_slots(text):
    text = re.sub(r"\([^)]*\)", " ", text)  # remarques entre parenthèses (ex. petit bassin)
    out = []
    for m in SLOT.finditer(text):
        h1, m1, h2, m2 = m.groups()
        start = int(h1) * 60 + int(m1 or 0)
        end = int(h2) * 60 + int(m2 or 0)
        if end > start and end <= 24 * 60:
            out.append([f"{start // 60:02d}:{start % 60:02d}", f"{end // 60:02d}:{end % 60:02d}"])
    return out


def merge_slots(slots):
    """Fusionne les créneaux qui se chevauchent ou se touchent."""
    out = []
    for s, e in sorted(slots):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def parse_day_line(line):
    """Formats rencontrés : 'Du lundi au jeudi : 12h - 19h', 'Samedi et dimanche : 8h30 - 15h',
    'Le dimanche de 13h30 à 19h30', 'Mardi : fermé'  ->  ([0,1,2,3], [['12:00','19:00']])"""
    line = line.strip()
    digit = re.search(r"\d", line)
    prefix = strip_accents(line[: digit.start()] if digit else line.split(":")[0]).lower()
    names = re.findall(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", prefix)
    if not names:
        return None
    idx = [DAY_NAMES[n] for n in names]
    if re.search(r"\bau\b", prefix) and len(idx) == 2 and idx[0] <= idx[1]:
        days = list(range(idx[0], idx[1] + 1))
    else:
        days = sorted(set(idx))
    if not digit:
        return (days, []) if re.search(r"ferm", strip_accents(line).lower()) else None
    return days, parse_slots(line[digit.start():])


IGNORED_BASINS = ("petit bassin", "ludique", "pataugeoire", "apprentissage")


def parse_toulouse_page(html):
    """Retourne (periods, en_bref_text). Une section d'accordéon = une période."""
    periods = {}
    titles = list(re.finditer(r'<span class="accordion-button__text">(.*?)</span>', html, re.S))
    for i, t in enumerate(titles):
        title = html_to_text(t.group(1))
        kinds = period_kinds(title)
        if not kinds:
            continue
        end = html.find("<!-- fin acc item -->", t.end())
        body = html[t.end(): end if end != -1 else t.end() + 6000]
        # Une section peut contenir plusieurs bassins sous des intertitres (ex. Bellevue) :
        # on garde les bassins de nage et on ignore petit bassin / ludique / apprentissage.
        minutes = {d: [] for d in DAYS}
        heading, found = "", 0
        for line in html_to_text(body).split("\n"):
            line = line.strip()
            if not line:
                continue
            parsed = parse_day_line(line)
            if not parsed:
                heading = strip_accents(line).lower()
                continue
            if any(k in heading for k in IGNORED_BASINS):
                continue
            days, slots = parsed
            for d in days:
                for a, b in slots:
                    minutes[DAYS[d]].append((int(a[:2]) * 60 + int(a[3:]), int(b[:2]) * 60 + int(b[3:])))
            found += 1
        if found:
            schedule = {d: [[f"{s // 60:02d}:{s % 60:02d}", f"{e // 60:02d}:{e % 60:02d}"]
                            for s, e in merge_slots(minutes[d])] for d in DAYS}
            for kind in kinds:
                periods.setdefault(kind, {"label": title, "schedule": schedule})
    en_bref = ""
    s = html.find("block__shorts__list")
    if s != -1:
        e = html.find("field--name-field-chapeau", s)
        en_bref = html_to_text(html[s: e if e != -1 else s + 6000])
    return periods, en_bref


# ------------------------------------------------------------- API Claude
def call_claude(system, prompt, max_tokens=4000):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("réponse sans JSON")
    return json.loads(text[a: b + 1])


ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def valid_slots(slots):
    return isinstance(slots, list) and all(
        isinstance(s, list) and len(s) == 2 and HHMM.match(str(s[0])) and HHMM.match(str(s[1])) and s[0] < s[1]
        for s in slots)


def validate_exceptions(items, known_ids):
    ok = []
    for e in items or []:
        try:
            if e["pool_id"] not in known_ids or not ISO.match(e["from"]) or not ISO.match(e["to"]):
                continue
            if e["type"] == "closed":
                ok.append({"pool_id": e["pool_id"], "from": e["from"], "to": e["to"], "type": "closed",
                           "note": str(e.get("note", ""))[:200], "source": "llm"})
            elif e["type"] == "hours" and valid_slots(e.get("slots")):
                ok.append({"pool_id": e["pool_id"], "from": e["from"], "to": e["to"], "type": "hours",
                           "slots": e["slots"], "note": str(e.get("note", ""))[:200], "source": "llm"})
        except (KeyError, TypeError):
            continue
    return ok


def extract_exceptions(en_bref_blocks, pools, today):
    system = ("Tu extrais des fermetures et horaires exceptionnels de piscines à partir d'annonces. "
              "Réponds uniquement par un objet JSON.")
    pool_list = "\n".join(f"- {p['id']} : {p['nom']} ({p['commune']})" for p in pools)
    prompt = f"""Date du jour : {today}.
Piscines connues (id : nom) :
{pool_list}

Annonces :
{chr(10).join(en_bref_blocks)}

Extrais les fermetures et horaires exceptionnels qui concernent des piscines de la liste.
Règles : ignore les dates passées ; si une piscine est « réservée uniquement à une animation », c'est « closed »
pour la nage ; n'invente rien ; ignore les piscines absentes de la liste.
Format : {{"exceptions":[{{"pool_id":"...","from":"AAAA-MM-JJ","to":"AAAA-MM-JJ","type":"closed" ou "hours",
"slots":[["08:30","15:00"]] (seulement si type=hours),"note":"motif court"}}]}}"""
    data = call_claude(system, prompt)
    return validate_exceptions((data or {}).get("exceptions"), {p["id"] for p in pools})


def extract_periods_llm(pool, html):
    """Pages libres (ex. L'Union) : l'IA lit la page et renvoie des périodes structurées."""
    text = re.sub(r"(?is)<(script|style|svg|noscript).*?</\1>", " ", html)
    text = re.sub(r"\s+", " ", text)[:60000]
    system = "Tu convertis la page d'horaires d'une piscine en JSON strict. Réponds uniquement par un objet JSON."
    prompt = f"""Piscine : {pool['nom']} ({pool['commune']}). Consigne : {pool['source'].get('hint', '')}
Renvoie {{"periods": {{"scolaire": {{"label": "...", "schedule": {{"mon": [["12:00","13:30"]], "tue": [], ...}}}},
"vacances": {{...}}}}}}.
Clés de périodes possibles : scolaire, vacances, noel, automne_hiver, printemps, ete.
Clés de jours : mon,tue,wed,thu,fri,sat,sun (heures au format HH:MM, 24 h).
Si tu ne peux pas attribuer un créneau avec certitude à la catégorie demandée, ne l'inclus pas.
Si une période n'est pas publiée, ne l'invente pas.
Page (HTML) :
{text}"""
    data = call_claude(system, prompt, max_tokens=3000)
    periods = {}
    for kind, p in ((data or {}).get("periods") or {}).items():
        if kind not in ("scolaire", "vacances", "noel", "automne_hiver", "printemps", "ete"):
            continue
        sch = p.get("schedule", {})
        if all(d in sch and valid_slots(sch[d]) for d in DAYS):
            periods[kind] = {"label": str(p.get("label", kind))[:80], "schedule": {d: sch[d] for d in DAYS}}
    return periods


# ------------------------------------------------------------- calendrier
def local_date(iso):
    """Les dates de l'API sont en UTC à 22h/23h la veille (minuit à Paris) : +12 h donne le bon jour."""
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")) + timedelta(hours=12)
    return d.strftime("%Y-%m-%d")


def build_calendar():
    kinds = {"toussaint": "toussaint", "noel": "noel", "hiver": "hiver", "printemps": "printemps", "ete": "ete"}
    q = urllib.parse.urlencode({
        "where": 'zones="Zone C" and start_date>="2026-06-01"', "limit": 100,
        "select": "description,start_date,end_date", "order_by": "start_date"})
    url = ("https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/"
           "fr-en-calendrier-scolaire/records?" + q)
    rows = json.loads(fetch(url))["results"]
    seen = {}
    for r in rows:
        desc = strip_accents(r["description"]).lower()
        kind = next((k for k in kinds if k in desc), None)
        if not kind or "enseignant" in desc:
            continue
        start, end = local_date(r["start_date"]), local_date(r["end_date"])
        if end <= start:
            continue
        key = (kind, start)
        if key not in seen or end > seen[key]["end"]:
            seen[key] = {"kind": kind, "start": start, "end": end}
    year = now_utc().year
    feries = {}
    for y in (year, year + 1):
        feries.update(json.loads(fetch(f"https://calendrier.api.gouv.fr/jours-feries/metropole/{y}.json")))
    return {"generated_at": now_utc().isoformat(timespec="seconds"), "zone": "C",
            "vacances": sorted(seen.values(), key=lambda v: v["start"]), "feries": dict(sorted(feries.items()))}


# ------------------------------------------------------------------- main
def main():
    pools = load_json(SITE / "pools.json", {"pools": []})["pools"]
    prev = load_json(DATA / "horaires.json", {"pools": {}})["pools"]
    state = load_json(DATA / "state.json", {})
    exc_file = load_json(DATA / "exceptions.json", {"exceptions": []})
    today = now_utc().strftime("%Y-%m-%d")
    out, problems, en_brefs = {}, [], []

    for pool in pools:
        pid, src = pool["id"], pool["source"]
        entry = {"periods": {}, "checked_at": None, "status": "missing", "source_urls": src["urls"]}
        try:
            htmls = [fetch(u) for u in src["urls"]]
            if src["type"] == "toulouse_annuaire":
                for html in htmls:
                    periods, en_bref = parse_toulouse_page(html)
                    entry["periods"].update(periods)
                    if en_bref:
                        en_brefs.append(en_bref)
                if not entry["periods"] and not pool.get("saison"):
                    raise ValueError("aucune période d'horaires reconnue (page modifiée ?)")
            elif src["type"] == "llm_page":
                html = htmls[0]
                h = sha(html_to_text(html))
                old = prev.get(pid, {})
                if "Error establishing a database connection" in html:
                    raise ValueError("site en erreur (base de données)")
                if state.get(pid) == h and old.get("periods"):
                    entry = old | {"checked_at": now_utc().isoformat(timespec="seconds")}
                else:
                    periods = extract_periods_llm(pool, html) if os.environ.get("ANTHROPIC_API_KEY") else None
                    if periods is None:
                        raise ValueError("ANTHROPIC_API_KEY absente : extraction IA impossible")
                    if not periods:
                        raise ValueError("l'IA n'a trouvé aucun horaire fiable")
                    entry["periods"] = periods
                    state[pid] = h
            entry["checked_at"] = entry["checked_at"] or now_utc().isoformat(timespec="seconds")
            entry["status"] = "ok"
        except Exception as e:  # noqa: BLE001 - on garde les dernières données connues
            problems.append(f"{pid}: {e}")
            old = prev.get(pid)
            if old and old.get("periods"):
                entry = old | {"status": "stale"}  # checked_at conservé : l'appli passera en « non vérifié »
        out[pid] = entry

    # exceptions : manuelles conservées, extraites par IA remplacées si les annonces ont changé
    manual = [e for e in exc_file["exceptions"] if e.get("source") != "llm"]
    auto = [e for e in exc_file["exceptions"] if e.get("source") == "llm"]
    blocks = sorted(set(en_brefs))
    if blocks and os.environ.get("ANTHROPIC_API_KEY"):
        h = sha("\n".join(blocks))
        if state.get("_en_bref") != h:
            try:
                auto = extract_exceptions(blocks, pools, today)
                state["_en_bref"] = h
            except Exception as e:  # noqa: BLE001
                problems.append(f"exceptions IA: {e}")
    elif blocks:
        print("Annonces « En bref » détectées mais pas de clé API : exceptions manuelles conservées.")
    exceptions = [e for e in manual + auto if e["to"] >= today]
    save_json(DATA / "exceptions.json", {"updated": today, "exceptions": exceptions})

    save_json(DATA / "horaires.json", {"generated_at": now_utc().isoformat(timespec="seconds"), "pools": out})
    save_json(DATA / "state.json", state)
    try:
        save_json(DATA / "calendar.json", build_calendar())
    except Exception as e:  # noqa: BLE001
        problems.append(f"calendrier: {e}")

    ok = sum(1 for p in out.values() if p["status"] == "ok")
    print(f"{ok}/{len(out)} piscines à jour.")
    for p in problems:
        print("::warning::" + p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
