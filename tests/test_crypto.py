import os

import pytest

import crypto


def test_encrypt_decrypt_roundtrip():
    key = os.urandom(32)
    for text in ["sk-abc123", "유니코드-값-🔑", ""]:
        assert crypto.decrypt(crypto.encrypt(text, key), key) == text


def test_decrypt_wrong_key_raises():
    key = os.urandom(32)
    blob = crypto.encrypt("secret", key)
    with pytest.raises(ValueError):
        crypto.decrypt(blob, os.urandom(32))


def test_decrypt_tampered_raises():
    key = os.urandom(32)
    blob = crypto.encrypt("secret", key)
    tampered = blob[:-2] + ("AA" if blob[-2:] != "AA" else "BB")
    with pytest.raises(ValueError):
        crypto.decrypt(tampered, key)


def test_password_backup_roundtrip():
    blob = crypto.encrypt_with_password("백업-값", "backup-pass-12345")
    assert crypto.decrypt_with_password(blob, "backup-pass-12345") == "백업-값"


def test_password_backup_wrong_password():
    blob = crypto.encrypt_with_password("값", "backup-pass-12345")
    with pytest.raises(ValueError):
        crypto.decrypt_with_password(blob, "wrong-pass")
