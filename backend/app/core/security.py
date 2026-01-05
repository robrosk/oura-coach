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
