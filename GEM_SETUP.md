# GeM scan on your Windows PC — one-time setup (about 10 minutes)

GeM blocks servers outside India, so your own PC does the GeM part. It runs every 3 hours while
the PC is on, **encrypts** the bids with your data key and uploads them to your repo. Your dashboard then shows GeM next to MP and Rajasthan.

## 1. Install Python (skip if you have it)
1. Open https://www.python.org/downloads/ → click **Download Python 3.x**.
2. Run it. **Tick "Add python.exe to PATH"** at the bottom → **Install Now**.

## 2. Download the scanner
1. Open https://github.com/mtarvecha660-lgtm/tender-scanner
2. Green **Code** button → **Download ZIP**.
3. Right-click the ZIP → **Extract All…** → choose `C:\` → Extract. You now have `C:\tender-scanner-main`.

## 3. Make a GitHub token (lets the PC upload, only to this one repo)
1. Open https://github.com/settings/personal-access-tokens/new (GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → **Generate new token**).
2. **Token name:** `tender-scanner-pc`. **Expiration:** choose **No expiration** (or 1 year and repeat this step then).
3. **Repository access:** **Only select repositories** → pick **tender-scanner**.
4. **Permissions** → **Repository permissions** → **Contents** → **Read and write**. (Leave everything else.)
5. **Generate token** → **copy** it (starts with `github_pat_`). You will not see it again.

## 4. Have your data key ready
The PC encrypts the GeM list before upload, with the same master key as the dashboard (**TS_DATA_KEY**,
44 characters ending in `=`). GitHub can't show a secret back, so use the key Tab sent you
(or the one you made with newkey.html and saved). Keep it private.

## 5. Run setup
1. Open `C:\tender-scanner-main\gem_pc`.
2. Double-click **setup.bat** (if Windows shows "Windows protected your PC": **More info → Run anyway**).
3. Paste the token (right-click in the black window pastes) → Enter.
4. Paste the **data key** → Enter. It checks the key and says "Data key OK."
5. It installs 4 small packages, schedules the scan every 3 hours, and runs the first scan (5–15 minutes).
6. "Uploaded to GitHub" = done. The dashboard shows GeM about 2 minutes later.

## Good to know
- **Run it now any time:** double-click `run_now.bat`.
- **Log:** `gem_pc\gem.log`.
- **Stop:** Start menu → Task Scheduler → Task Scheduler Library → delete **TenderScanner GeM**.
- Changed the master key (TS_DATA_KEY)? Double-click setup.bat again → Enter for the token → paste the new key.
- The data key is saved only in `gem_pc\datakey.txt` on your PC; it is never uploaded. GitHub only receives `data/gem_raw.enc` (encrypted).
- The token is saved only in `gem_pc\token.txt` on your PC. It can only touch the tender-scanner repo. To cancel it: GitHub → Settings → Developer settings → Fine-grained tokens → Delete.
- PC off or asleep = no GeM update. MP and Rajasthan keep updating from GitHub regardless.
