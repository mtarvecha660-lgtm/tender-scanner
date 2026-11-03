"""Reader for GeM BidPlus (bidplus.gem.gov.in) public bid search.

IMPORTANT: GeM only answers Indian internet connections. GitHub's free servers are in
the USA, so this part must run on a computer in India (see README: "GeM on your PC").

Collects ongoing bids whose consignee (delivery place) is in the chosen states, tags the
district from the consignee city, and runs extra keyword searches so grocery items hidden
inside long multi-item bids are found.
"""
import json, re, time, logging
from datetime import datetime, timezone
import requests

log = logging.getLogger("gem")
BASE = "https://bidplus.gem.gov.in"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


class GeM:
    def __init__(self, delay=0.4):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"})
        self.delay = delay
        self.csrf = None

    def start(self):
        r = self.s.get(BASE + "/advance-search", timeout=60)
        r.raise_for_status()
        m = re.search(r"csrf_bd_gem_nk'\s*:\s*'([0-9a-f]+)'", r.text)
        if not m:
            raise RuntimeError("GeM: could not find the page token (site layout changed?)")
        self.csrf = m.group(1)

    def post(self, path, data, tries=4):
        last = None
        for i in range(tries):
            try:
                d = dict(data); d["csrf_bd_gem_nk"] = self.csrf
                r = self.s.post(BASE + path, data=d, timeout=60, headers={"X-Requested-With": "XMLHttpRequest", "Referer": BASE + "/advance-search"})
                time.sleep(self.delay)
                if r.status_code == 200:
                    return json.loads(r.text)
                last = f"HTTP {r.status_code}"
                if r.status_code in (401, 403, 419):
                    self.start()
            except (requests.RequestException, ValueError) as e:
                last = str(e)
            time.sleep(3 * (i + 1))
        raise RuntimeError(f"GeM POST {path} failed: {last}")

    def _pages(self, path, payload_fn, max_pages=400):
        page, docs, total = 1, [], None
        while page <= max_pages:
            j = self.post(path, {"payload": json.dumps(payload_fn(page))})
            resp = (j.get("response") or {}).get("response") or {}
            total = resp.get("numFound", 0)
            batch = resp.get("docs") or []
            docs += batch
            if not batch or len(docs) >= total:
                break
            page += 1
        return docs, total

    def by_consignee(self, state, city=""):
        return self._pages("/search-bids", lambda p: {"searchType": "con", "state_name_con": state.upper(), "city_name_con": city,
                                                       "bidEndFromCon": "", "bidEndToCon": "", "page": p})

    def cities(self, state):
        j = self.post("/city-list-adv", {"state_name": state.upper()})
        return sorted({c["city_name"] for c in j.get("data", []) if c.get("city_name")})

    def keyword(self, kw):
        def pl(p):
            return {"page": p, "param": {"searchBid": kw, "searchType": "fullText"},
                    "filter": {"bidStatusType": "ongoing_bids", "byType": "all", "highBidValue": "",
                               "byEndDate": {"from": "", "to": ""}, "sort": "Bid-End-Date-Oldest"}}
        return self._pages("/all-bids-data", pl, max_pages=80)


KEEP = ("b_id", "b_bid_number", "b_category_name", "bd_category_name", "b_total_quantity", "b_bid_type", "b_cat_id",
        "final_start_date_sort", "final_end_date_sort", "is_high_value", "ba_is_global_tendering",
        "ba_is_limited_tendering", "ba_official_details_minName", "ba_official_details_deptName")


def slim(d):
    """Keep only the fields the dashboard uses (keeps the upload small)."""
    return {k: d[k] for k in KEEP if k in d}


def _v(d, k):
    v = d.get(k)
    return v[0] if isinstance(v, list) and v else v


def collect(states, keywords, out_path):
    g = GeM(); g.start()
    raw = {}
    for st in states:
        docs, total = g.by_consignee(st)
        log.info("GeM %s: %d of %d bids", st, len(docs), total)
        for d in docs:
            raw.setdefault(str(_v(d, "b_id")), {"doc": slim(d), "state": st, "districts": [], "kw": []})
        for city in g.cities(st):
            try:
                cd, _ = g.by_consignee(st, city)
            except Exception as e:
                log.warning("GeM city %s failed: %s", city, e); continue
            for d in cd:
                e = raw.setdefault(str(_v(d, "b_id")), {"doc": slim(d), "state": st, "districts": [], "kw": []})
                if city not in e["districts"]:
                    e["districts"].append(city)
    for kw in keywords:
        try:
            kd, total = g.keyword(kw)
        except Exception as e:
            log.warning("GeM keyword %s failed: %s", kw, e); continue
        hits = 0
        for d in kd:
            e = raw.get(str(_v(d, "b_id")))
            if e is not None and kw not in e["kw"]:
                e["kw"].append(kw); hits += 1
        log.info("GeM keyword '%s': %d bids in India, %d in your states", kw, total, hits)
    data = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "via": "requests", "bids": raw}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data
