import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from argon2.low_level import Type

from app.common.time import utc_now
from app.config import get_settings

password_hasher = PasswordHasher(type=Type.ID)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, VerifyMismatchError):
        return False


def create_access_token(user_id: uuid.UUID, roles: list[str]) -> str:
    settings = get_settings()
    now = utc_now()
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
