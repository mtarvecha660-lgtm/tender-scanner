"""Run:  python -m pytest tests   (needs: pip install -r requirements.txt pytest)"""
import base64, os, pytest
from cryptography.exceptions import InvalidTag
from scanner import secure, main as scan_main

KEY = os.urandom(32)
SAMPLE = {"tenders": [{"title": "Supply of Atta, Rice and Dal for hostel", "cats": ["Grocery"]}]}


def users_json(raw):
    return secure.build_users(KEY, secure.parse_users(raw))


def remembered_kek(uj, name, pw):
    u = uj["users"][secure.user_id(name)]
    return secure.kek(pw, base64.b64decode(u["salt"]), u["iterations"])


def unwrap_with_kek(uj, name, kek):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    u = uj["users"].get(secure.user_id(name))
    if not u:
        return None
    try:
        return AESGCM(kek).decrypt(base64.b64decode(u["iv"]), base64.b64decode(u["wrappedKey"]), b"tender-scanner-key")
    except InvalidTag:
        return None


def test_right_password_opens_data():
    uj = users_json("moksh:Right-Pass-123;papa:Papa-Pass-456")
    dk = secure.unwrap(uj, "Moksh", "Right-Pass-123")
    assert dk == KEY
    assert secure.decrypt_json(dk, secure.encrypt_json(KEY, SAMPLE)) == SAMPLE


def test_wrong_password_or_user_fails():
    uj = users_json("moksh:Right-Pass-123")
    assert secure.unwrap(uj, "moksh", "wrong-pass-123") is None
    assert secure.unwrap(uj, "stranger", "Right-Pass-123") is None


def test_removed_user_and_changed_password_locked_out_after_next_run():
    run1 = users_json("moksh:Right-Pass-123;papa:Papa-Pass-456")
    papa_device = remembered_kek(run1, "papa", "Papa-Pass-456")      # papa ticked "remember me"
    moksh_device = remembered_kek(run1, "moksh", "Right-Pass-123")
    run2 = users_json("moksh:Right-Pass-123")                          # papa removed from TS_USERS
    assert secure.unwrap(run2, "papa", "Papa-Pass-456") is None
    assert unwrap_with_kek(run2, "papa", papa_device) is None          # remembered device logged out too
    assert unwrap_with_kek(run2, "moksh", moksh_device) == KEY         # unchanged user stays logged in
    run3 = users_json("moksh:Brand-New-Pass-789")                      # password changed
    assert secure.unwrap(run3, "moksh", "Right-Pass-123") is None
    assert unwrap_with_kek(run3, "moksh", moksh_device) is None
    assert secure.unwrap(run3, "moksh", "Brand-New-Pass-789") == KEY


def test_raw_file_is_unreadable():
    blob = secure.encrypt_json(KEY, SAMPLE)
    assert blob[:4] == b"TSE1"
    for word in (b"Atta", b"Rice", b"Grocery", b"tenders", b"hostel"):
        assert word not in blob
    with pytest.raises(InvalidTag):
        secure.decrypt_json(os.urandom(32), blob)


@pytest.mark.parametrize("missing", ["TS_DATA_KEY", "TS_USERS"])
def test_missing_secret_fails_and_publishes_nothing(tmp_path, monkeypatch, missing):
    monkeypatch.setenv("TS_DATA_KEY", base64.b64encode(KEY).decode())
    monkeypatch.setenv("TS_USERS", "moksh:Right-Pass-123")
    monkeypatch.delenv(missing)
    monkeypatch.setattr(scan_main, "DOCS_DATA", str(tmp_path / "docs"))
    monkeypatch.setattr(scan_main, "DATA", str(tmp_path / "data"))
    with pytest.raises(SystemExit) as e:
        scan_main.main(["--sources", ""])
    assert missing in str(e.value)
    assert list(tmp_path.iterdir()) == []


def test_bad_users_format_rejected():
    for bad in ["moksh", "moksh:pa:ss123456", "moksh:short", "a:Long-Pass-1;a:Long-Pass-2", " "]:
        with pytest.raises(SystemExit):
            secure.parse_users(bad)
