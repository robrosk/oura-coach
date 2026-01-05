"""FastAPI dependencies for authentication and authorization."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..core.logging import logger
from ..core.security import decode_jwt_token
from ..storage.db import get_db
from ..storage.models import User
from ..storage import repo


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token.

    Extracts the Bearer token from Authorization header,
    validates it, and returns the corresponding user.

    Args:
        authorization: The Authorization header value.
        db: Database session.

    Returns:
        The authenticated User object.

    Raises:
        HTTPException: 401 if token is missing, invalid, or user not found.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Decode and validate token
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = repo.get_user_by_id(db, user_id)
    if not user:
        logger.warning(f"User {user_id} from token not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get the current user if authenticated, None otherwise.

    Use this for endpoints that work with or without authentication.

    Args:
        authorization: The Authorization header value.
        db: Database session.

    Returns:
        The authenticated User object, or None if not authenticated.
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None
