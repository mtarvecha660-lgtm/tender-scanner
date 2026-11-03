"""Tender Scanner — main program.

Run:  python -m scanner.main            (MP + Rajasthan portals; used on GitHub Actions)
      python -m scanner.main --gem      (also fetch GeM; needs an Indian internet connection)
"""
import argparse, json, logging, os, re, sys, time
from datetime import datetime, timedelta, timezone
import yaml

from . import gepnic, secure
from .districts import STATE_DISTRICTS, PIN3, PIN4

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DATA = os.path.join(ROOT, "docs", "data")
DATA = os.path.join(ROOT, "data")
IST = timezone(timedelta(hours=5, minutes=30))
log = logging.getLogger("scanner")

SOURCES = {
    "mptenders": {"base": "https://mptenders.gov.in", "state": "Madhya Pradesh", "name": "MP Tenders"},
    "rajasthan": {"base": "https://eproc.rajasthan.gov.in", "state": "Rajasthan", "name": "Rajasthan eProc"},
}
GEM_BASE = "https://bidplus.gem.gov.in"


def now_ist():
    return datetime.now(IST).replace(tzinfo=None)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ---------------------------------------------------------------- classify
class Classifier:
    def __init__(self, cfg):
        self.cats = []
        for name, words in (cfg.get("categories") or {}).items():
            words = [str(w).strip().lower() for w in (words or []) if str(w).strip()]
            if words:
                pat = r"(?<![a-z0-9])(" + "|".join(sorted((re.escape(w) for w in set(words)), key=len, reverse=True)) + r")(?![a-z0-9])"
                self.cats.append((name, re.compile(pat)))
        self.grocery = next((n for n, _ in self.cats if n.lower().startswith("grocery")), "Grocery")
        self.excl = [str(p).lower() for p in cfg.get("grocery_exclude_phrases") or []]
        self.block = [str(p).lower() for p in cfg.get("grocery_block_if") or []]
        self.block_cats = set(cfg.get("grocery_block_if_category") or [])

    def classify(self, text, extra_grocery_hits=(), is_works=False):
        t = " " + (text or "").lower() + " "
        cats, hits = [], {}
        gt = t
        for p in self.excl:
            gt = gt.replace(p, " ")
        blocked = any(b in t for b in self.block)
        for name, rx in self.cats:
            src = gt if name == self.grocery else t
            found = sorted(set(m.group(1) for m in rx.finditer(src)))
            if name == self.grocery:
                if blocked:
                    found = []
                elif extra_grocery_hits:
                    found = sorted(set(found) | set(extra_grocery_hits))
            if found:
                cats.append(name); hits[name] = found[:6]
        if self.grocery in cats and (is_works or self.block_cats & set(cats)):
            cats.remove(self.grocery); hits.pop(self.grocery, None)
        if not cats:
            cats = ["Other"]
        return cats, hits


# ---------------------------------------------------------------- districts
def find_district(state, *texts):
    table = STATE_DISTRICTS.get(state, {})
    blob = " " + " ".join(t or "" for t in texts).lower() + " "
    best = None
    for dist, aliases in table.items():
        for a in aliases:
            m = re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", blob)
            if m and (best is None or m.start() < best[1]):
                best = (dist, m.start())
    return best[0] if best else "Unknown"


# ---------------------------------------------------------------- eligibility flags
FLAG_RULES = [
    ("Turnover required", r"turnover"),
    ("Experience required", r"experience|similar work|past performance"),
    ("MSE / Startup terms", r"\bmse\b|msme|startup|start-up|udyam|nsic"),
    ("OEM / Authorisation", r"\boem\b|authori[sz]ation|manufacturer"),
    ("Registration / Class", r"class\s*[a-e]\b|registered contractor|registration"),
]


def flags_for(t):
    fl = []
    txt = " ".join(str(t.get(k) or "") for k in ("prequal", "description", "title")).lower()
    for name, rx in FLAG_RULES:
        if re.search(rx, txt):
            fl.append(name)
    if (t.get("emd") or 0) > 0:
        fl.append("EMD ₹" + inr(t["emd"]))
    return fl


# ---------------------------------------------------------------- normalise
def norm_gepnic(t, src):
    out = {k: t.get(k) for k in ("source", "state", "id", "ref", "title", "org", "published", "closing", "opening",
                                    "location", "pincode", "product_category", "sub_category", "description",
                                    "tender_category", "prequal", "tender_type", "period_days")}
    out["value"] = gepnic.money(t.get("value"))
    out["emd"] = gepnic.money(t.get("emd"))
    out["fee"] = gepnic.money(t.get("fee"))
    out["url"] = SOURCES[src]["base"] + "/nicgep/app"
    out["url_note"] = "Search this Tender ID on the site (Search box, top left)."
    out["_details"] = bool(t.get("_details"))
    return out


def norm_gem(bid_id, e):
    d = e["doc"]
    v = lambda k: (d.get(k)[0] if isinstance(d.get(k), list) and d.get(k) else d.get(k))
    btype = v("b_bid_type") or 1
    path = "showbidDocument"
    if btype == 5:
        path = "showdirectradocumentPdf"
    elif btype == 2:
        path = "showradocumentPdf"
    items = v("b_category_name") or v("bd_category_name") or ""
    items = re.sub(r"\s*\(\?{2,}[\s?]*\)", "", items)   # Hindi names arrive from GeM as "(?????)"
    items = re.sub(r"\?{3,}", "", items).strip()
    dists = []
    for c in e.get("districts") or []:
        dd = find_district(e["state"], c)
        dists.append(dd if dd != "Unknown" else c.title())
    flags = []
    if v("is_high_value"):
        flags.append("High value bid")
    if v("ba_is_global_tendering"):
        flags.append("Global tender")
    if v("ba_is_limited_tendering"):
        flags.append("Limited tender")
    if btype in (2, 5):
        flags.append("Reverse auction")
    def dt(x):
        return (x or "")[:16] or None
    return {
        "source": "gem", "state": e["state"], "id": v("b_bid_number"), "ref": "", "title": items,
        "org": " / ".join(x for x in [v("ba_official_details_minName"), v("ba_official_details_deptName")] if x),
        "published": dt(v("final_start_date_sort")), "closing": dt(v("final_end_date_sort")), "opening": None,
        "location": ", ".join(sorted(set(dists))) or None, "quantity": v("b_total_quantity"),
        "value": None, "emd": None, "url": f"{GEM_BASE}/{path}/{bid_id}", "gem_flags": flags,
        "gem_kw": e.get("kw") or [], "_districts": sorted(set(dists)) or ["Unknown"], "_details": True,
    }



def inr(n):
    """150000 -> '1,50,000' (Indian grouping)."""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
    return head + "," + tail


def fmt_close(c):
    try:
        return datetime.strptime(c, "%Y-%m-%dT%H:%M").strftime("%d %b %Y %I:%M %p")
    except Exception:
        return c or "?"


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="mptenders,rajasthan", help="comma list: mptenders,rajasthan (use '' for none)")
    ap.add_argument("--gem", action="store_true", help="fetch GeM now (needs an Indian internet connection)")
    ap.add_argument("--max-details", type=int, default=3500)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    t0 = time.time()
    # Both secrets are required. Without them the run stops here and nothing is published.
    dkey = secure.data_key()
    users = secure.parse_users()
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yml"), encoding="utf-8")) or {}
    states = cfg.get("states") or ["Madhya Pradesh", "Rajasthan"]
    clf = Classifier(cfg)
    now = now_ist()

    enc_path = os.path.join(DOCS_DATA, "tenders.enc")
    try:
        prev = secure.read_enc(dkey, enc_path, None)
    except Exception:
        # wrong/changed TS_DATA_KEY: start fresh instead of crashing (old file can't be read without the old key)
        log.warning("tenders.enc could not be opened with the current TS_DATA_KEY (key changed?) - starting fresh")
        prev = None
    if prev is None:   # one-time migration from the old plaintext file
        prev = load_json(os.path.join(DOCS_DATA, "tenders.json"), {"tenders": []})
    prev_by_key = {(t["source"], t["id"]): t for t in prev.get("tenders", [])}
    meta_prev = prev.get("meta") or load_json(os.path.join(DOCS_DATA, "meta.json"), {})
    status = dict(meta_prev.get("sources") or {})
    fresh = {}
    ran_now = set()

    # --- GePNIC portals
    for src in [s for s in a.sources.split(",") if s.strip()]:
        info = SOURCES[src]
        if info["state"] not in states:
            continue
        st = {"name": info["name"], "url": info["base"], "ok": False, "at": now.strftime("%Y-%m-%dT%H:%M")}
        try:
            rows, sess, failed_orgs = gepnic.list_tenders(info["base"], src, info["state"])
            for r in rows:   # carry details from earlier runs
                old = prev_by_key.get((src, r["id"]))
                if old and old.get("_details"):
                    for k in ("location", "pincode", "product_category", "sub_category", "description", "tender_category",
                              "prequal", "tender_type", "period_days", "value", "emd", "fee"):
                        if old.get(k) is not None:
                            r[k] = old[k]
                    r["_details"] = True
            # fetch details: grocery-looking first, then the rest
            rows.sort(key=lambda r: 0 if clf.classify(r["title"] + " " + r["org"])[0][0] == clf.grocery else 1)
            n = gepnic.fetch_details(sess, rows, max_fetch=a.max_details)
            for r in rows:
                fresh[(src, r["id"])] = norm_gepnic(r, src)
            st.update(ok=True, count=len(rows), details_fetched=n, failed_orgs=len(failed_orgs))
            if not failed_orgs:
                ran_now.add(src)
            log.info("%s: %d tenders, %d new detail pages", src, len(rows), n)
        except Exception as e:
            st["error"] = str(e)[:300]
            log.error("%s FAILED: %s — keeping previous data for this source", src, e)
        status[src] = st

    # --- GeM (fetched now, or from the last file a PC in India uploaded)
    gem_enc = os.path.join(DATA, "gem_raw.enc")
    gem_path = os.path.join(DATA, "gem_raw.local.json")   # plaintext only in memory/on your PC, never committed
    gem_raw = None
    if a.gem:
        st = {"name": "GeM", "url": GEM_BASE, "ok": False, "at": now.strftime("%Y-%m-%dT%H:%M")}
        try:
            from . import gem
            gem_raw = gem.collect(states, cfg.get("gem_grocery_searches") or [], gem_path)
            os.remove(gem_path)
            st["ok"] = True
        except Exception as e:
            st["error"] = str(e)[:300]
            log.error("GeM FAILED: %s", e)
        status["gem"] = st
    if gem_raw is None and os.path.exists(gem_enc):
        try:
            gem_raw = secure.read_enc(dkey, gem_enc)
        except Exception:
            log.error("data/gem_raw.enc could not be opened: the PC's data key is not the same as TS_DATA_KEY. "
                      "Run gem_pc/setup.bat on the PC and paste the current key.")
    if gem_raw is None:   # one-time migration from the old plaintext upload
        gem_raw = load_json(os.path.join(DATA, "gem_raw.json"), None)
    gem_loaded = False
    if gem_raw and gem_raw.get("bids"):
        for bid_id, e in gem_raw["bids"].items():
            if e.get("state") in states:
                g = norm_gem(bid_id, e)
                fresh[("gem", g["id"])] = g
        gem_loaded = True
        ran_now.add("gem")
        s = status.get("gem") or {"name": "GeM", "url": GEM_BASE}
        s.update(ok=True, count=len(gem_raw["bids"]), data_from=gem_raw.get("fetched_at"), via=gem_raw.get("via"))
        status["gem"] = s

    # --- merge with previous: keep sources that failed this run, mark closed ones
    ran_ok = ran_now
    merged = {}
    for key, t in prev_by_key.items():
        src = key[0]
        if key in fresh:
            continue
        if src in ran_ok:   # source read fine but tender no longer listed -> closed/withdrawn
            t = dict(t); t["status"] = "closed"
        merged[key] = t
    for key, t in fresh.items():
        old = prev_by_key.get(key)
        t["first_seen"] = (old or {}).get("first_seen") or now.strftime("%Y-%m-%dT%H:%M")
        t["status"] = "open"
        merged[key] = t

    keep_days = int(cfg.get("keep_closed_days", 30))
    home = [d.lower() for d in cfg.get("home_districts") or []]
    out = []
    for t in merged.values():
        c = t.get("closing")
        try:
            cdt = datetime.strptime(c, "%Y-%m-%dT%H:%M") if c else None
        except ValueError:
            cdt = None
        if cdt and cdt < now:
            t["status"] = "closed"
        if t.get("status") == "closed" and cdt and cdt < now - timedelta(days=keep_days):
            continue
        text = " ".join(str(t.get(k) or "") for k in ("title", "description", "product_category", "sub_category"))
        # GeM keyword searches match parts of words ("ration" finds "operation"), so they are only a hint
        cats, hits = clf.classify(text, is_works=str(t.get("tender_category") or "").lower() == "works")
        t["hint"] = [] if clf.grocery in cats else [k for k in (t.get("gem_kw") or []) if len(k) >= 5 and k not in ("ration",)]
        t["cats"], t["hits"] = cats, hits
        t["mixed"] = clf.grocery in cats and len([x for x in cats if x != clf.grocery]) > 0
        if t["source"] == "gem":
            t["districts"] = t.get("_districts") or ["Unknown"]
            t["flags"] = t.get("gem_flags") or []
        else:
            dd = find_district(t["state"], t.get("location"), t.get("org"), t.get("title"), t.get("description"))
            pin = re.sub(r"\D", "", str(t.get("pincode") or ""))
            if dd == "Unknown" and len(pin) == 6:
                dd = PIN4.get(pin[:4]) or PIN3.get(pin[:3]) or "Unknown"
            t["districts"] = [dd]
            t["flags"] = flags_for(t)
        t["near"] = any(d.lower() in home for d in t["districts"])
        out.append(t)
    out.sort(key=lambda t: (t.get("status") != "open", t.get("closing") or "9999"))

    # --- write dashboard data (encrypted)
    opens = [t for t in out if t["status"] == "open"]
    meta = {
        "updated": now.strftime("%Y-%m-%dT%H:%M"), "run_seconds": round(time.time() - t0),
        "sources": status, "open": len(opens),
        "open_by_source": {s: sum(1 for t in opens if t["source"] == s) for s in ("mptenders", "rajasthan", "gem")},
        "grocery_open": sum(1 for t in opens if clf.grocery in t["cats"]),
        "categories": [n for n, _ in clf.cats] + ["Other"], "grocery_name": clf.grocery,
        "closing_soon_days": cfg.get("closing_soon_days", 3), "home_districts": cfg.get("home_districts") or [],
    }
    rows = []
    for t in out:
        p = {k: v for k, v in t.items() if not k.startswith("_") and k not in ("gem_flags", "gem_kw") and v not in (None, "", [])}
        p["_details"] = t.get("_details", False)   # cache fields for the next run
        if t["source"] == "gem":
            p.update(gem_kw=t.get("gem_kw"), gem_flags=t.get("gem_flags"), _districts=t.get("_districts"))
        rows.append(p)
    secure.write_enc(dkey, enc_path, {"generated": now.strftime("%Y-%m-%dT%H:%M"), "meta": meta, "tenders": rows})
    save_json(os.path.join(DOCS_DATA, "users.json"), secure.build_users(dkey, users))
    # only harmless status in the clear (times + OK flags), so the login page can show "last updated"
    save_json(os.path.join(DOCS_DATA, "meta.json"), {
        "updated": meta["updated"],
        "sources": {k: {"name": v.get("name"), "ok": bool(v.get("ok")), "at": v.get("at") or v.get("data_from")} for k, v in status.items()},
    })
    # never leave plaintext tender data behind
    for old in (os.path.join(DOCS_DATA, "tenders.json"), os.path.join(DATA, "gem_raw.json"),
                os.path.join(DATA, "alerted.json"), gem_path):
        if os.path.exists(old):
            os.remove(old)
    log.info("DONE in %ss: %d open tenders (%s), %d grocery, %d login(s)",
             meta["run_seconds"], len(opens), meta["open_by_source"], meta["grocery_open"], len(users))
    return 0


if __name__ == "__main__":
    sys.exit(main())
