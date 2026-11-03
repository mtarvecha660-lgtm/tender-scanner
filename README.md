# Tender Scanner — MP, Rajasthan & GeM (private, password-protected)

**Dashboard:** https://mtarvecha660-lgtm.github.io/tender-scanner/

A free robot that checks government tender websites every 3 hours, keeps every open
tender located in **Madhya Pradesh** and **Rajasthan**, sorts them into categories
(Grocery, Furniture, Medical…), and shows them on a **private dashboard that needs a login**.
No emails or GitHub issues are sent.

| Website | How it is read | Runs on |
|---|---|---|
| mptenders.gov.in | public "Tenders by Organisation" pages (no login, no captcha) | GitHub, every 3 hours |
| eproc.rajasthan.gov.in | same system as MP, same public pages | GitHub, every 3 hours |
| bidplus.gem.gov.in (GeM) | public bid search, filtered by delivery state (MP / Rajasthan) | **your PC** (GeM blocks foreign servers — see below) |

It never logs in and never submits anything. Always read the official tender document before bidding.

## The dashboard
- Opens on **Grocery** tenders. Change the Category box to see Furniture, Medical, Works… or "All categories".
- Filters: Category, State, District, Source, Show (Open / New / Closing soon / Near you / Closed), Sort (newest, closing soonest, value).
- Badges: **NEW** (found in the last 2 days), **Closing in N days**, **📍 Near you** (your home districts), **mixed** (grocery + other items in one tender).
- ⚠ yellow tags warn about special conditions written in the tender (turnover, experience, MSE, OEM, EMD).
- MP / Rajasthan portal links can't open one tender directly (the site doesn't allow it), so press **Copy ID** and paste it into the portal's search box.
- GeM cards open the official bid PDF.

## Login & privacy
- The dashboard asks for a **username + password**. Each person (you, papa…) has their own.
- The tender data in this repo is **encrypted** (`docs/data/tenders.enc`). Without a password the GitHub files are unreadable.
- Passwords live only in your GitHub **Secrets** (`TS_USERS`, `TS_DATA_KEY`). Change, add or remove people:
  **[LOGIN_SETUP.md](LOGIN_SETUP.md)** (2 minutes).
- If a secret is missing, the scan stops and publishes nothing.

## Change what it looks for (no coding)
Open **config.yml** in this repo → pencil icon ✏️ → edit → **Commit changes**. The next scan uses it.
- Add a grocery word: add a line like `    - kaju` under `Grocery:`.
- Stop a wrong match: add the phrase under `grocery_exclude_phrases` or `grocery_block_if`.
- Change your home area: edit `home_districts`.
- States: `states: [Madhya Pradesh, Rajasthan]`.

## Pause or stop
- **Pause:** repo → **Actions** → "scan" (left side) → "…" (top right) → **Disable workflow**. Enable it again the same way.
- **Run now:** Actions → scan → **Run workflow**.
- **GeM on your PC:** open Task Scheduler → delete or disable "TenderScanner GeM".

## GeM on your PC (Windows)
GeM only answers internet connections from India. GitHub's free servers are in the USA, so GeM
runs on your PC every 3 hours while it is on, encrypts the result and uploads it here. Setup is in
**[GEM_SETUP.md](GEM_SETUP.md)** (about 10 minutes, one time). The dashboard shows how old the GeM data is.

## How it works (for the curious)
- `scanner/gepnic.py` reads MP + Rajasthan portals; `scanner/gem.py` reads GeM; `scanner/main.py` categorises, finds the district, merges, and writes the encrypted `docs/data/tenders.enc` (+ `users.json` with each person's password-locked key; `scanner/secure.py`).
- `.github/workflows/scan.yml` runs it every 3 hours (GitHub may start it a few minutes late), saves results, and publishes the dashboard. It sends no emails and opens no issues.
- If a website is down, the last good data for that site is kept and the dashboard shows the problem.
- Closed tenders stay visible under "Closed (history)" for 30 days.
- Run log: `data/last_run.log` (counts only, no tender details).
- Tests: `python -m pytest tests` (login, wrong password, removed user, missing secret).
