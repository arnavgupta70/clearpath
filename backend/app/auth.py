"""Email + password login.

Passwords are stored as salted scrypt hashes. The token is "<user id>.<expiry>.<signature>",
signed with SECRET_KEY, so the API doesn't need a sessions table.
"""

import hashlib
import hmac
import os
import secrets
import time

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret").encode()
TOKEN_TTL = 7 * 24 * 3600
DEMO_PASSWORD = "clearpath"  # every seeded user has this one


def _scrypt(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}${_scrypt(password, salt)}"


def check_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    return hmac.compare_digest(_scrypt(password, salt), digest)


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()


def make_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + TOKEN_TTL}"
    return f"{payload}.{_sign(payload)}"


def read_token(token: str) -> int | None:
    try:
        user_id, expires, signature = token.split(".")
        valid = hmac.compare_digest(signature, _sign(f"{user_id}.{expires}")) and int(expires) > time.time()
    except ValueError:
        return None
    return int(user_id) if valid else None
