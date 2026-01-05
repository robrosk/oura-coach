"""Oura OAuth 2.0 Authorization Code flow implementation."""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx

from ..core.config import get_settings
from ..core.logging import logger

settings = get_settings()


class OAuthError(Exception):
    """OAuth-related errors."""

    pass


def generate_auth_url(state: Optional[str] = None) -> tuple[str, str]:
    """Generate Oura OAuth authorization URL.

    Returns:
        Tuple of (auth_url, state) where state should be stored for CSRF validation.
    """
    if state is None:
        state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": settings.oura_client_id,
        "redirect_uri": settings.oura_redirect_uri,
        "scope": settings.oura_scopes,
        "state": state,
    }

    auth_url = f"{settings.oura_auth_url}?{urlencode(params)}"
    return auth_url, state


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from OAuth callback.

    Returns:
        Token response dict with access_token, refresh_token, expires_in, etc.

    Raises:
        OAuthError: If token exchange fails.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.oura_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.oura_redirect_uri,
                    "client_id": settings.oura_client_id,
                    "client_secret": settings.oura_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise OAuthError(f"Token exchange failed: {response.status_code}")

            token_data = response.json()
            logger.info("Successfully exchanged code for tokens")
            return token_data

        except httpx.RequestError as e:
            logger.error(f"Token exchange request failed: {e}")
            raise OAuthError(f"Token exchange request failed: {e}")


async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token using the refresh token.

    Args:
        refresh_token: Current refresh token.

    Returns:
        New token response dict with access_token, refresh_token (rotated), expires_in.

    Raises:
        OAuthError: If token refresh fails.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.oura_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.oura_client_id,
                    "client_secret": settings.oura_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                raise OAuthError(f"Token refresh failed: {response.status_code}")

            token_data = response.json()
            logger.info("Successfully refreshed access token")
            return token_data

        except httpx.RequestError as e:
            logger.error(f"Token refresh request failed: {e}")
            raise OAuthError(f"Token refresh request failed: {e}")


def calculate_token_expiry(expires_in: int) -> datetime:
    """Calculate token expiry datetime from expires_in seconds."""
    return datetime.utcnow() + timedelta(seconds=expires_in)


def is_token_expired(expires_at: Optional[datetime], buffer_minutes: int = 5) -> bool:
    """Check if token is expired or will expire soon.

    Args:
        expires_at: Token expiry datetime.
        buffer_minutes: Consider expired if expiring within this many minutes.

    Returns:
        True if token is expired or expiring soon.
    """
    if expires_at is None:
        return True
    return datetime.utcnow() >= expires_at - timedelta(minutes=buffer_minutes)
