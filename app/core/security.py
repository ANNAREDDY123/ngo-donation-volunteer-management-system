from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password before storing it."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    return password_hash.verify(password, hashed_password)


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Create a signed JWT with an expiration time."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def create_access_token(user_id: int) -> str:
    return create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes
        ),
    )


def create_refresh_token(user_id: int) -> str:
    return create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days
        ),
    )


def decode_token(token: str, expected_type: str) -> dict:
    """Decode a JWT and verify its expected token type."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token.") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Incorrect token type.")

    if not payload.get("sub"):
        raise ValueError("Token subject is missing.")

    return payload