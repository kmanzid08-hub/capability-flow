import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    subject = payload.get("sub")
    if payload.get("type") != "access" or not isinstance(subject, str):
        raise jwt.InvalidTokenError("Invalid token payload")
    return uuid.UUID(subject)
