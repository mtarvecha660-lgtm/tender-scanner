"""Encryption for the Tender Scanner (AES-256-GCM, PBKDF2-SHA256).

Nothing here ever writes plaintext tender data to the repo.

  TS_DATA_KEY  GitHub Secret: 32 random bytes, base64. Encrypts all tender data.
  TS_USERS     GitHub Secret: "moksh:Password1;papa:Password2" (no ";" or ":" inside a password).

File format of every .enc file:  b"TSE1" + 12-byte nonce + AES-GCM(gzip(json)).
users.json:  {"v":1, "users": {sha256("tender-scanner:"+username): {salt, iterations, iv, wrappedKey}}}
  - the password-derived key (PBKDF2-SHA256) encrypts the data key with AES-GCM.
  - salt = HMAC(data key, username + password), so it only changes when the password (or data key) changes.
    A device that ticked "remember me" keeps the password-derived key and re-opens users.json on every
    visit: if that person is removed or their password changes, the device is logged out at the next update.
"""
import base64, gzip, hashlib, hmac, json, os, re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

MAGIC = b"TSE1"
ITERATIONS = 600_000          # OWASP 2023 recommendation for PBKDF2-SHA256
USER_RE = re.compile(r"^[a-z0-9._-]{1,40}$")


class SecretError(SystemExit):
    pass


def data_key(required=True):
    raw = (os.environ.get("TS_DATA_KEY") or "").strip()
    if not raw:
        if required:
            raise SecretError("TS_DATA_KEY secret is missing. Nothing was published. See LOGIN_SETUP.md.")
        return None
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception:
        raise SecretError("TS_DATA_KEY is not valid base64. Nothing was published. See LOGIN_SETUP.md.")
    if len(key) != 32:
        raise SecretError("TS_DATA_KEY must be 32 bytes (44 base64 characters). Nothing was published.")
    return key


def encrypt_bytes(key, plain: bytes) -> bytes:
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, gzip.compress(plain, 9, mtime=0), MAGIC)


def decrypt_bytes(key, blob: bytes) -> bytes:
    if blob[:4] != MAGIC:
        raise ValueError("not a Tender Scanner encrypted file")
    return gzip.decompress(AESGCM(key).decrypt(blob[4:16], blob[16:], MAGIC))


def encrypt_json(key, obj) -> bytes:
    return encrypt_bytes(key, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def decrypt_json(key, blob: bytes):
    return json.loads(decrypt_bytes(key, blob).decode("utf-8"))


def read_enc(key, path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "rb") as f:
        return decrypt_json(key, f.read())


def write_enc(key, path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(encrypt_json(key, obj))
    os.replace(tmp, path)


def parse_users(raw=None):
    """'moksh:Pass1;papa:Pass2' -> {'moksh': 'Pass1', 'papa': 'Pass2'}"""
    raw = os.environ.get("TS_USERS") if raw is None else raw
    raw = (raw or "").strip()
    if not raw:
        raise SecretError("TS_USERS secret is missing. Nothing was published. See LOGIN_SETUP.md.")
    users = {}
    for i, part in enumerate([p for p in raw.replace("\n", ";").split(";") if p.strip()], 1):
        if part.count(":") != 1:
            raise SecretError(f"TS_USERS entry #{i} must look like name:password (one ':' and no ';' in the password).")
        name, pw = part.split(":")
        name = name.strip().lower()
        pw = pw.strip()
        if not USER_RE.match(name):
            raise SecretError(f"TS_USERS entry #{i}: username may use only a-z, 0-9, . _ - (max 40).")
        if len(pw) < 8:
            raise SecretError(f"TS_USERS entry #{i} ({name}): password must be at least 8 characters.")
        if name in users:
            raise SecretError(f"TS_USERS: username '{name}' appears twice.")
        users[name] = pw
    if not users:
        raise SecretError("TS_USERS has no users. Nothing was published.")
    return users


def user_id(name):
    return hashlib.sha256(("tender-scanner:" + name.strip().lower()).encode()).hexdigest()


def kek(password, salt, iterations=ITERATIONS):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations).derive(password.encode("utf-8"))


def build_users(key, users):
    out = {}
    for name, pw in users.items():
        salt = hmac.new(key, ("salt:" + name + "\x00" + pw).encode("utf-8"), hashlib.sha256).digest()[:16]
        iv = os.urandom(12)
        wrapped = AESGCM(kek(pw, salt)).encrypt(iv, key, b"tender-scanner-key")
        out[user_id(name)] = {"salt": base64.b64encode(salt).decode(), "iterations": ITERATIONS,
                              "iv": base64.b64encode(iv).decode(), "wrappedKey": base64.b64encode(wrapped).decode()}
    return {"v": 1, "users": out}


def unwrap(users_json, name, password):
    """Python twin of the browser login (used by the tests)."""
    u = users_json["users"].get(user_id(name))
    if not u:
        return None
    try:
        k = kek(password, base64.b64decode(u["salt"]), u["iterations"])
        return AESGCM(k).decrypt(base64.b64decode(u["iv"]), base64.b64decode(u["wrappedKey"]), b"tender-scanner-key")
    except Exception:
        return None
