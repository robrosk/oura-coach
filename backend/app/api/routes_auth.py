"""Authentication routes for Google OAuth."""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from ..core.security import create_jwt_token
from ..storage.db import get_db
from ..storage import repo
from ..storage.models import User
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

# In-memory state storage for CSRF (MVP - use Redis in production)
_oauth_states: dict[str, str] = {}

# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# =============================================================================
# Response Models
# =============================================================================


class AuthStartResponse(BaseModel):
    """Response for OAuth start endpoint."""
    auth_url: str
    state: str


class UserResponse(BaseModel):
    """User info response."""
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class LogoutResponse(BaseModel):
    """Logout response."""
    success: bool
    message: str


# =============================================================================
# OAuth Flow
# =============================================================================


@router.get("/google/start", response_model=AuthStartResponse)
async def start_google_oauth():
    """Start Google OAuth flow.

    Returns the Google authorization URL for the user to visit.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = state

    # Build authorization URL
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Always show consent screen to get refresh token
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    logger.info("Generated Google OAuth URL")

    return AuthStartResponse(auth_url=auth_url, state=state)


@router.get("/google/callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback.

    Exchanges the authorization code for tokens, creates/updates the user,
    generates a JWT, and redirects to the frontend with the token.
    """
    # Check for error from Google
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(f"{settings.web_app_url}/login?error={error}")

    # Validate required params
    if not code or not state:
        logger.error("Missing code or state in OAuth callback")
        return RedirectResponse(f"{settings.web_app_url}/login?error=missing_params")

    # Validate state (CSRF protection)
    if state not in _oauth_states:
        logger.error("Invalid OAuth state")
        return RedirectResponse(f"{settings.web_app_url}/login?error=invalid_state")

    # Remove used state
    del _oauth_states[state]

    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_redirect_uri,
                },
            )

            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return RedirectResponse(f"{settings.web_app_url}/login?error=token_exchange_failed")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                logger.error(f"Failed to get user info: {userinfo_response.text}")
                return RedirectResponse(f"{settings.web_app_url}/login?error=userinfo_failed")

            userinfo = userinfo_response.json()

        # Extract user data
        google_id = userinfo.get("id")
        email = userinfo.get("email")
        name = userinfo.get("name")
        picture = userinfo.get("picture")

        if not email:
            logger.error("No email in Google userinfo")
            return RedirectResponse(f"{settings.web_app_url}/login?error=no_email")

        # Get or create user
        user, created = repo.get_or_create_user_by_google(
            db=db,
            email=email,
            google_id=google_id,
            name=name,
            picture=picture,
        )

        if created:
            logger.info(f"Created new user from Google OAuth: {user.id}")
        else:
            logger.info(f"Existing user logged in via Google: {user.id}")

        # Create JWT token
        jwt_token = create_jwt_token(user.id, user.email)

        # Redirect to frontend with token
        redirect_url = f"{settings.web_app_url}/login/callback?token={jwt_token}"
        return RedirectResponse(redirect_url)

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(f"{settings.web_app_url}/login?error=callback_failed")


# =============================================================================
# User Info
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """Get current authenticated user's info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
    )


# =============================================================================
# Logout (optional - JWT is stateless)
# =============================================================================


@router.post("/logout", response_model=LogoutResponse)
async def logout():
    """Logout endpoint.

    Since JWT is stateless, this just returns success.
    The frontend should clear the stored token.
    For proper session invalidation, would need a token blocklist.
    """
    return LogoutResponse(success=True, message="Logged out successfully")
