"""Password and bearer-token primitives with no external service dependency."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


_N = 2**14
_R = 8
_P = 1
_DKLEN = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return "$".join(("scrypt", str(_N), str(_R), str(_P), _b64(salt), _b64(digest)))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_value, digest_value = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = _unb64(salt_value)
        expected = _unb64(digest_value)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError, AttributeError):
        return False


def is_valid_password_hash(encoded: str) -> bool:
    """Accept only canonical hashes produced by this service's scrypt settings."""
    try:
        algorithm, n, r, p, salt_value, digest_value = encoded.split("$")
        if (algorithm, n, r, p) != ("scrypt", str(_N), str(_R), str(_P)):
            return False
        salt = _unb64(salt_value)
        digest = _unb64(digest_value)
        return (
            len(salt) == 16
            and len(digest) == _DKLEN
            and _b64(salt) == salt_value
            and _b64(digest) == digest_value
        )
    except (TypeError, ValueError, AttributeError):
        return False


def issue_token() -> str:
    return secrets.token_urlsafe(32)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
