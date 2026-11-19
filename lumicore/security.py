from pwdlib import PasswordHash
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from lumicore.config import settings
from typing import Any
import hashlib

JWT_ALGORITHM = "HS256"

password_hasher = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)

def hash_token(token:str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

def _create_token(
    user_id: uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured")
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=JWT_ALGORITHM,
    )

def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes,
        ),
    )
def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days,
        ),
    )
def _decode_token(
    token:str,
    expected_type:str,
) -> dict[str, Any]:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError as exception:
        raise ValueError("Invalid access token") from exception
    if payload.get("type") != expected_type:
        raise ValueError("Invalid access token type")
    if not payload.get("sub"):
        raise ValueError("Access token has no subject")
    return payload

def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_token(token, "access")
def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode_token(token, "refresh")
