# Login & passwords — how to control who can see the dashboard

The dashboard is locked. The tender data in this repo is **encrypted** (`docs/data/tenders.enc`),
so even someone who opens the GitHub files sees only scrambled bytes. Only a correct
username + password opens it, and the opening happens inside your own phone/browser.

You control everything with **two GitHub Secrets**. Only you (the repo owner) can see or change them,
and nobody can read a secret back, not even you. So keep your own copy somewhere private.

| Secret | What it is | Example |
|---|---|---|
| `TS_USERS` | everyone who may log in | `moksh:Mango-Tiger-4821;papa:Rain-Bottle-7730` |
| `TS_DATA_KEY` | the master key that encrypts the data (44 characters, ends with `=`) | made by `newkey.html` |

## TS_USERS format
- `username:password`, people separated by `;`  →  `moksh:Pass1;papa:Pass2;ravi:Pass3`
- Username: small letters / numbers / `.` `_` `-`. Login is not case-sensitive for the username.
- Password: at least 8 characters, **no `;` and no `:`** inside it. Spaces at the start/end are removed.
- Use long passwords (12+ characters, e.g. three random words + a number: `Mango-Tiger-4821`).
  The lock is strong, but the encrypted files are public, so a short/common password could be guessed offline.

## Change a password, add or remove a person (2 minutes)
1. Open **github.com/mtarvecha660-lgtm/tender-scanner**
2. **Settings** (top menu of the repo; on phone: tap ⋯ then Settings)
3. Left side: **Secrets and variables → Actions**
4. Find **TS_USERS** → tap the ✏️ pencil (**Update**)
5. Type the full new list, e.g. `moksh:NewPassword-123;papa:Another-Pass-456` → **Update secret**
   (the old value is not shown; you always type the whole list again)
6. Top menu: **Actions** → left side **scan** → **Run workflow** → green **Run workflow**
7. Wait ~5 minutes until the run shows a green ✓. New passwords work now; old ones stop working.
   (If you skip step 6, it happens by itself at the next scan, within 3 hours.)

## "Remember me on this device"
- Ticked: that phone stays logged in until someone presses **Logout**.
- If you **remove a person or change their password**, their remembered device is logged out at the next update too
  (it shows "Your login has changed. Please log in again.").
- Only one case needs more: if you think someone **copied the key out of their browser** (needs technical skill),
  or a phone was lost while logged in, change the master key below. That locks out every device at once.

## Change the master key (TS_DATA_KEY) — lock out every device
1. Open **https://mtarvecha660-lgtm.github.io/tender-scanner/newkey.html** → it makes a random key on your phone (not sent anywhere) → **Copy key**. Save it privately.
2. Repo → **Settings → Secrets and variables → Actions → TS_DATA_KEY → ✏️ Update** → paste → **Update secret**.
3. **Actions → scan → Run workflow**. After ~5 min everyone logs in again with their normal password.
4. GeM PC: double-click `gem_pc\setup.bat` → Enter (keeps the token) → paste the new key.
   Until you do this, GeM tenders are missing from the dashboard (MP + Rajasthan keep working).
- Note: after a key change the scanner starts its history fresh ("NEW" badges show for a day).

## Safety rules built in
- If `TS_DATA_KEY` or `TS_USERS` is missing or wrong, the scan **fails and publishes nothing**. It never falls back to plain data.
- Before every publish a check stops the run if any plain tender file exists.
- Passwords are never stored in the repo. `docs/data/users.json` only holds each person's
  password-locked copy of the master key (PBKDF2-SHA256, 600,000 rounds + AES-256-GCM), and usernames are stored as hashes.
- Tender data: AES-256-GCM. The GeM PC encrypts its list before uploading.
