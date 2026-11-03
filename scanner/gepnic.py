"""Reader for NIC eProcurement (GePNIC) portals such as mptenders.gov.in and eproc.rajasthan.gov.in.

Uses only the public "Tenders by Organisation" pages, which need no login and no CAPTCHA.
"""
import re, time, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests
from lxml import html as LH

log = logging.getLogger("gepnic")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"})
    return s


def _get(s, url, tries=4, timeout=90):
    last = None
    for i in range(tries):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 500:
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url[:120]} ({last})")


def _date(txt):
    txt = (txt or "").strip()
    for fmt in ("%d-%b-%Y %I:%M %p", "%d-%b-%Y"):
        try:
            return datetime.strptime(txt, fmt).strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            pass
    return None


def _clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def list_tenders(base, source, state):
    """Return (tenders, session). Each tender is a dict; detail_url is session-bound."""
    s = _session()
    r = _get(s, f"{base}/nicgep/app?page=FrontEndTendersByOrganisation&service=page")
    d = LH.fromstring(r.content)
    orgs = []
    for tr in d.xpath('//table[@id="table"]//tr'):
        tds = tr.xpath("./td")
        href = tr.xpath(".//a/@href")
        if len(tds) == 3 and href and _clean(tds[2].text_content()).isdigit():
            orgs.append((_clean(tds[1].text_content()), int(_clean(tds[2].text_content())), href[0]))
    if not orgs:
        raise RuntimeError(f"{source}: organisation list is empty — the page layout may have changed")
    log.info("%s: %d organisations, %d tenders listed", source, len(orgs), sum(o[1] for o in orgs))
    out, failed = [], []
    for name, count, href in orgs:
        try:
            rr = _get(s, base + href, timeout=180)
        except Exception as e:
            log.warning("%s: org %s failed: %s", source, name, e)
            failed.append(name)
            continue
        dd = LH.fromstring(rr.content)
        for tr in dd.xpath('//table[@id="table"]//tr'):
            tds = tr.xpath("./td")
            if len(tds) < 6 or not _clean(tds[0].text_content()).isdigit():
                continue
            raw = _clean(tds[4].text_content())
            parts = re.findall(r"\[([^\]]*)\]", raw)
            tid = parts[-1] if parts else raw
            title = parts[0] if len(parts) >= 3 else (raw.split("[")[0] or raw)
            ref = parts[-2] if len(parts) >= 2 else ""
            a = tds[4].xpath(".//a/@href")
            out.append({
                "source": source, "state": state, "id": tid, "ref": ref, "title": _clean(title),
                "org": _clean(tds[5].text_content()), "published": _date(tds[1].text_content()),
                "closing": _date(tds[2].text_content()), "opening": _date(tds[3].text_content()),
                "detail_url": base + a[0] if a else None,
            })
    log.info("%s: %d tenders read (%d organisations failed)", source, len(out), len(failed))
    return out, s, failed


FIELDS = {
    "Tender Value in ₹": "value", "EMD Amount in ₹": "emd", "Tender Fee in ₹": "fee", "Location": "location",
    "Pincode": "pincode", "Product Category": "product_category", "Sub category": "sub_category",
    "Work Description": "description", "Tender Category": "tender_category", "NDA/Pre Qualification": "prequal",
    "Tender Type": "tender_type", "Form Of Contract": "contract_form", "EMD Exemption Allowed": "emd_exempt",
    "Period Of Work(Days)": "period_days", "Allow Preferential Bidder": "preferential",
}


def _detail(s, url):
    r = _get(s, url, tries=3, timeout=60)
    d = LH.fromstring(r.content)
    info = {}
    for cap in d.xpath('//td[contains(@class,"td_caption")]'):
        key = _clean(cap.text_content())
        key = re.sub(r"\(.*?\)", "", key).strip() if key.startswith("Processing Fee") else key
        if key in FIELDS:
            nxt = cap.getnext()
            if nxt is not None:
                v = _clean(nxt.text_content())
                if v and v.upper() not in ("NA", "NIL", "N/A"):
                    info[FIELDS[key]] = v[:600]
    return info


def fetch_details(session, tenders, max_fetch=3000, workers=6):
    """Fill detail fields in place for tenders that do not have them yet. Returns how many were fetched."""
    todo = [t for t in tenders if t.get("detail_url") and not t.get("_details")][:max_fetch]
    done = 0
    def work(t):
        return t, _detail(session, t["detail_url"])
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(work, t) for t in todo]
        for f in as_completed(futs):
            try:
                t, info = f.result()
                t.update(info)
                t["_details"] = True
                done += 1
            except Exception as e:
                log.debug("detail failed: %s", e)
    return done


def money(v):
    """'1,50,000' -> 150000.0 ; returns None if not a number."""
    if not v:
        return None
    m = re.search(r"[\d,]+(?:\.\d+)?", str(v))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None
