"""Password hashing helpers for InvoiceX member sign-in."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

_ALGORITHM = "scrypt"
_N = 2**14
_R = 8
_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32


def hash_password(password: str) -> str:
    """Return a self-describing, salted scrypt password hash."""

    salt = os.urandom(_SALT_BYTES)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_KEY_BYTES,
    )
    return "$".join(
        (
            _ALGORITHM,
            str(_N),
            str(_R),
            str(_P),
            _encode(salt),
            _encode(derived_key),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without exposing parsing or hash failures to callers."""

    try:
        algorithm, raw_n, raw_r, raw_p, raw_salt, raw_expected = encoded_hash.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = _decode(raw_salt)
        expected = _decode(raw_expected)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(raw_n),
            r=int(raw_r),
            p=int(raw_p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(f"{value}{'=' * (-len(value) % 4)}")
