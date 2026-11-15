"""Password hashing and JWT helpers.

Both token types carry ``type`` so neither can stand in for the other, and
``jti`` so refresh tokens can be tracked and revoked server-side.
"""
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from esone_api.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


class TokenError(Exception):
    """Raised when a token is malformed, expired or of the wrong type."""


def _encode(claims: dict, expires: timedelta, token_type: str) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + expires
    jti = uuid.uuid4().hex
    payload = {**claims, "iat": now, "exp": exp, "type": token_type, "jti": jti}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti, exp


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    settings = get_settings()
    delta = timedelta(minutes=settings.access_token_expire_minutes)
    token, _, _ = _encode({"sub": str(user_id), "role": role}, delta, "access")
    return token, int(delta.total_seconds())


def create_refresh_token(user_id: int, role: str) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at)."""
    settings = get_settings()
    delta = timedelta(days=settings.refresh_token_expire_days)
    return _encode({"sub": str(user_id), "role": role}, delta, "refresh")


def decode_token(token: str, expected_type: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise TokenError("Token is invalid or expired") from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token")
    if "sub" not in payload or "jti" not in payload:
        raise TokenError("Token is missing required claims")
    return payload
