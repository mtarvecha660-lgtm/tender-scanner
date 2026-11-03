"""GeM scan for your Windows PC (GeM only works from an Indian internet connection).

What it does, every time it runs:
 1. downloads the latest config.yml from your GitHub repo (so keyword edits on GitHub apply here too)
 2. reads all ongoing GeM bids delivered to your states (MP + Rajasthan), with district,
    plus grocery keyword searches across every item line
 3. ENCRYPTS the list with your data key and uploads data/gem_raw.enc -> GitHub merges it into the dashboard

Needs: token.txt and datakey.txt next to this file (both made by setup.bat; never uploaded).
The plain list stays only on this PC; GitHub only ever receives the encrypted file.
"""
import base64, json, logging, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import requests, yaml
from scanner import gem, secure

REPO = "mtarvecha660-lgtm/tender-scanner"
API = f"https://api.github.com/repos/{REPO}"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(HERE, "gem.log"), encoding="utf-8")])
log = logging.getLogger("gem_pc")


def token():
    p = os.path.join(HERE, "token.txt")
    if not os.path.exists(p):
        sys.exit("token.txt not found. Run setup.bat first.")
    return open(p, encoding="utf-8").read().strip()


def datakey():
    p = os.path.join(HERE, "datakey.txt")
    if not os.path.exists(p):
        sys.exit("datakey.txt not found. Run setup.bat and paste your TS_DATA_KEY.")
    os.environ["TS_DATA_KEY"] = open(p, encoding="utf-8").read().strip()
    try:
        return secure.data_key()
    except SystemExit as e:
        sys.exit(f"datakey.txt is not right: {e}. Run setup.bat again and paste the TS_DATA_KEY value.")


def gh(method, url, tok, **kw):
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    return requests.request(method, url, headers=h, timeout=60, **kw)


def main():
    if "--check-key" in sys.argv:
        datakey(); print("Data key OK."); return 0
    key = datakey()
    tok = token()
    # 1. latest settings
    try:
        r = gh("GET", f"{API}/contents/config.yml", tok, params={"ref": "main"})
        if r.ok:
            open(os.path.join(ROOT, "config.yml"), "wb").write(base64.b64decode(r.json()["content"]))
            log.info("config.yml updated from GitHub")
        elif r.status_code in (401, 403):
            log.error("GitHub refused the token (HTTP %s). Make a new token and run setup.bat again.", r.status_code)
    except Exception as e:
        log.warning("could not refresh config.yml (%s) — using the local copy", e)
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yml"), encoding="utf-8")) or {}
    states = cfg.get("states") or ["Madhya Pradesh", "Rajasthan"]
    # 2. scan GeM
    out = os.path.join(HERE, "gem_raw.local.json")   # plain copy on this PC only (never uploaded)
    t0 = time.time()
    data = gem.collect(states, cfg.get("gem_grocery_searches") or [], out)
    data["via"] = "windows-pc"
    body = secure.encrypt_json(key, data)
    log.info("GeM: %d bids for %s in %.0fs (%.1f MB encrypted)", len(data["bids"]), ", ".join(states), time.time() - t0, len(body) / 1e6)
    if not data["bids"]:
        log.error("GeM returned no bids — not uploading (would wipe the dashboard).")
        return 1
    # 3. upload
    for attempt in range(5):
        sha = None
        r = gh("GET", f"{API}/contents/data", tok, params={"ref": "main"})
        if r.ok:
            sha = next((f["sha"] for f in r.json() if f["name"] == "gem_raw.enc"), None)
        payload = {"message": "GeM data from PC (encrypted)", "content": base64.b64encode(body).decode(), "branch": "main"}
        if sha:
            payload["sha"] = sha
        r = gh("PUT", f"{API}/contents/data/gem_raw.enc", tok, json=payload)
        if r.status_code in (200, 201):
            log.info("Uploaded to GitHub. The dashboard updates in about 2 minutes.")
            return 0
        log.warning("upload try %d failed: HTTP %s %s", attempt + 1, r.status_code, r.text[:200])
        if r.status_code in (401, 403, 404):
            log.error("Token problem: it needs access to the tender-scanner repo with Contents = Read and write.")
            return 1
        time.sleep(10 * (attempt + 1))
    return 1


if __name__ == "__main__":
    sys.exit(main())
