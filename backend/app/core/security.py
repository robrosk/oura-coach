"""JWT token creation and validation for authentication."""

from datetime import datetime, timedelta
from typing import Optional

import jwt

from .config import get_settings
from .logging import logger

settings = get_settings()


def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token for a user.

    Args:
        user_id: The user's unique ID.
        email: The user's email address.

    Returns:
        Encoded JWT token string.
    """
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    logger.debug(f"Created JWT token for user {user_id}, expires at {expire}")
    return token


def decode_jwt_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        Decoded payload dict if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid JWT token: {e}")
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiry time of a JWT token without full validation.

    Args:
        token: The JWT token string.

    Returns:
        Expiry datetime if token can be decoded, None otherwise.
    """
    try:
        # Decode without verification to get expiry
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp)
        return None
    except jwt.InvalidTokenError:
        return None


def create_oauth_state(payload: dict, expires_minutes: Optional[int] = None) -> str:
    """Create a signed, expiring OAuth state token.

    Args:
        payload: Extra fields to include (e.g., purpose, user_id).
        expires_minutes: Override expiry window in minutes.

    Returns:
        Encoded state token.
    """
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.oauth_state_expire_minutes
    )
    token_payload = {
        **payload,
        "typ": "oauth_state",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(token_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_oauth_state(token: str) -> Optional[dict]:
    """Decode and validate an OAuth state token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        logger.debug("OAuth state token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid OAuth state token: {e}")
        return None

    if payload.get("typ") != "oauth_state":
        return None

    return payload
