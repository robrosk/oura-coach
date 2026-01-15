"""FastAPI routes for Oura OAuth and data operations."""

import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from ..core.security import create_oauth_state, decode_oauth_state
from ..oura import oauth
from ..oura.client import OuraAPIError, OuraClient
from ..oura.endpoints import BACKFILL_ENDPOINTS, get_endpoint_config
from ..oura.sync import SyncService, is_sync_in_progress
from ..storage import repo
from ..storage.db import get_db, SessionLocal
from ..storage.models import User
from .deps import get_current_user

settings = get_settings()
router = APIRouter(prefix="/oura", tags=["oura"])


# =============================================================================
# Response Models
# =============================================================================


class AuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class BackfillResponse(BaseModel):
    success: bool
    counts: dict[str, int]
    errors: list[str]


class RawDataResponse(BaseModel):
    endpoint: str
    count: int
    items: list[dict]


class CleanupResponse(BaseModel):
    deleted_by_fetched_at: int
    deleted_by_day: int
    total_deleted: int


class DisconnectResponse(BaseModel):
    success: bool
    message: str


class SyncResponse(BaseModel):
    success: bool
    mode: str
    message: str
    sync_in_progress: bool = False


class SyncStatusResponse(BaseModel):
    success: bool
    mode: str
    counts: dict[str, int]
    errors: list[str]
    cleanup_stats: Optional[dict[str, int]] = None


class CacheSummaryResponse(BaseModel):
    total_count: int
    endpoints: dict[str, dict]


# =============================================================================
# Background Task Helpers
# =============================================================================


async def _run_background_backfill(user_id: str, days: int):
    """Run backfill in background task."""
    # Create a new session for background task
    db = SessionLocal()
    try:
        sync_service = SyncService(db)
        result = await sync_service.run_backfill(user_id, days=days)
        if result.success:
            logger.info(f"Background backfill complete for user {user_id}: {result.counts}")
        else:
            logger.error(f"Background backfill failed for user {user_id}: {result.errors}")
    finally:
        db.close()


async def _run_background_refresh(user_id: str, days: int):
    """Run refresh in background task."""
    db = SessionLocal()
    try:
        sync_service = SyncService(db)
        result = await sync_service.run_refresh(user_id, days=days)
        if result.success:
            logger.info(f"Background refresh complete for user {user_id}: {result.counts}")
        else:
            logger.error(f"Background refresh failed for user {user_id}: {result.errors}")
    finally:
        db.close()


# =============================================================================
# OAuth Routes
# =============================================================================


@router.get("/connect/start", response_model=AuthUrlResponse)
async def start_oauth_flow(
    user: User = Depends(get_current_user),
):
    """Start Oura OAuth flow.

    Requires authentication. Returns auth URL for the client to redirect to.
    The user's ID is stored with the state for the callback.
    """
    state = create_oauth_state({"purpose": "oura", "user_id": user.id})
    auth_url, _ = oauth.generate_auth_url(state)
    logger.info(f"Generated OAuth URL for user {user.id} with signed state")
    return AuthUrlResponse(auth_url=auth_url, state=state)


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Handle Oura OAuth callback.

    Exchanges code for tokens and stores them for the authenticated user.
    The user_id is retrieved from the state parameter stored during /connect/start.
    Redirects to web app after completion.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return RedirectResponse(
            f"{settings.web_app_url}/app/connect?error={error}"
        )

    # Validate required params
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # CSRF validation and get user_id
    state_payload = decode_oauth_state(state)
    if not state_payload or state_payload.get("purpose") != "oura":
        logger.warning("Invalid OAuth state")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user_id = state_payload.get("user_id")
    if not user_id:
        logger.warning("OAuth state missing user_id")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Verify user exists
    user = repo.get_user_by_id(db, user_id)
    if not user:
        logger.error(f"User {user_id} not found during OAuth callback")
        return RedirectResponse(f"{settings.web_app_url}/login?error=user_not_found")

    try:
        # Exchange code for tokens
        token_data = await oauth.exchange_code_for_tokens(code)

        # Calculate expiry
        expires_at = None
        if "expires_in" in token_data:
            expires_at = oauth.calculate_token_expiry(token_data["expires_in"])

        # Store tokens for this user
        repo.upsert_user_token(
            db=db,
            user_id=user.id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
            scopes=token_data.get("scope"),
        )

        logger.info(f"Oura OAuth complete for user {user.id}")

        # Trigger background backfill
        if background_tasks:
            background_tasks.add_task(
                _run_background_backfill,
                user.id,
                settings.oura_cache_max_days,
            )
            logger.info(f"Queued background backfill for user {user.id}")

        # Redirect to web app
        return RedirectResponse(f"{settings.web_app_url}/app/welcome")

    except oauth.OAuthError as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(
            f"{settings.web_app_url}/app/connect?error=token_exchange_failed"
        )


@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect_oura(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect Oura account by deleting stored tokens and cached data."""
    # Delete cached raw events first
    deleted_events = repo.delete_user_raw_events(db, user.id)
    logger.info(f"Cleared {deleted_events} cached events for user {user.id}")

    # Delete OAuth token
    deleted_token = repo.delete_user_token(db, user.id)

    if deleted_token:
        return DisconnectResponse(
            success=True,
            message=f"Oura account disconnected. Cleared {deleted_events} cached records."
        )
    else:
        return DisconnectResponse(success=False, message="No Oura account connected")


# =============================================================================
# Data Routes
# =============================================================================


async def get_oura_client_for_user(user: User, db: Session) -> OuraClient:
    """Get authenticated Oura client for a user, refreshing token if needed."""
    token = repo.get_user_token(db, user.id)

    if not token:
        raise HTTPException(status_code=401, detail="Oura not connected. Please connect first.")

    # Check if token needs refresh
    if oauth.is_token_expired(token.expires_at):
        logger.info("Access token expired, refreshing...")
        try:
            new_token_data = await oauth.refresh_access_token(token.refresh_token)

            expires_at = None
            if "expires_in" in new_token_data:
                expires_at = oauth.calculate_token_expiry(new_token_data["expires_in"])

            token = repo.upsert_user_token(
                db=db,
                user_id=user.id,
                access_token=new_token_data["access_token"],
                refresh_token=new_token_data["refresh_token"],
                expires_at=expires_at,
                scopes=new_token_data.get("scope"),
            )
        except oauth.OAuthError as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(status_code=401, detail="Token refresh failed. Please reconnect.")

    return OuraClient(token.access_token)


@router.get("/backfill", response_model=BackfillResponse)
async def backfill_data(
    days: int = Query(default=60, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger backfill of Oura data for the last N days.

    Fetches all configured endpoints and stores raw JSON in the database.
    """
    client = await get_oura_client_for_user(user, db)

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    counts: dict[str, int] = {}
    errors: list[str] = []

    for endpoint_name in BACKFILL_ENDPOINTS:
        try:
            config = get_endpoint_config(endpoint_name)

            # Fetch data
            if config.date_param_type is None:
                # No date filtering (e.g., personal_info)
                items = await client.get_collection(endpoint_name)
            else:
                items = await client.get_collection(endpoint_name, start_date, end_date)

            # Store each item
            for item in items:
                record_id = item.get("id")
                day = item.get("day")
                start_datetime = item.get("start_datetime")

                repo.upsert_raw_event(
                    db=db,
                    user_id=user.id,
                    endpoint=endpoint_name,
                    payload=item,
                    record_id=record_id,
                    day=day,
                    start_datetime=start_datetime,
                )

            counts[endpoint_name] = len(items)
            logger.info(f"Backfilled {len(items)} items from {endpoint_name}")

        except OuraAPIError as e:
            error_msg = f"{endpoint_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Backfill error for {endpoint_name}: {e}")
            counts[endpoint_name] = 0

    return BackfillResponse(
        success=len(errors) == 0,
        counts=counts,
        errors=errors,
    )


@router.get("/raw", response_model=RawDataResponse)
async def get_raw_data(
    endpoint: str = Query(..., description="Endpoint name (e.g., 'daily_sleep')"),
    days: int = Query(default=14, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get cached raw data for a specific endpoint."""
    # Validate endpoint
    try:
        get_endpoint_config(endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    events = repo.get_raw_events(db, user.id, endpoint, days=days, limit=limit)

    # Parse JSON payloads
    items = [json.loads(e.payload) for e in events]

    return RawDataResponse(
        endpoint=endpoint,
        count=len(items),
        items=items,
    )


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_data(
    max_days: int = Query(default=None, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run retention cleanup to delete old cached data.

    Deletes records based on:
    - fetched_at: when we cached the data
    - day: the actual data date (for daily summaries)
    """
    result = repo.cleanup_old_events(db, max_days=max_days, user_id=user.id)
    return CleanupResponse(**result)


@router.get("/status")
async def get_connection_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Oura connection status and data summary."""
    token = repo.get_user_token(db, user.id)

    if not token:
        return {
            "connected": False,
            "message": "Oura not connected",
        }

    # Get counts by endpoint
    counts = repo.count_raw_events_by_endpoint(db, user.id)

    return {
        "connected": True,
        "user_id": user.id,
        "token_expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "scopes": token.scopes,
        "cached_data_counts": counts,
        "sync_in_progress": is_sync_in_progress(user.id),
    }


# =============================================================================
# Sync Routes
# =============================================================================


@router.post("/sync/backfill", response_model=SyncResponse)
async def sync_backfill(
    days: int = Query(default=None, ge=1, le=365, description="Days to backfill (default: 60)"),
    background_tasks: BackgroundTasks = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger a full backfill sync (heavy).

    Fetches all configured endpoints for the specified date range.
    Runs in background and returns immediately.
    """
    token = repo.get_user_token(db, user.id)

    if not token:
        raise HTTPException(status_code=401, detail="Oura not connected")

    if is_sync_in_progress(user.id):
        return SyncResponse(
            success=False,
            mode="backfill",
            message="Sync already in progress",
            sync_in_progress=True,
        )

    backfill_days = days or settings.oura_cache_max_days

    if background_tasks:
        background_tasks.add_task(_run_background_backfill, user.id, backfill_days)
        return SyncResponse(
            success=True,
            mode="backfill",
            message=f"Backfill started for {backfill_days} days",
            sync_in_progress=True,
        )
    else:
        # Synchronous fallback
        sync_service = SyncService(db)
        result = await sync_service.run_backfill(user.id, days=backfill_days)
        return SyncResponse(
            success=result.success,
            mode="backfill",
            message=f"Backfill complete: {sum(result.counts.values())} items" if result.success else f"Errors: {result.errors}",
        )


@router.post("/sync/refresh", response_model=SyncResponse)
async def sync_refresh(
    days: int = Query(default=None, ge=1, le=30, description="Days to refresh (default: 7)"),
    background_tasks: BackgroundTasks = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger a light refresh sync.

    Fetches recent data to capture updates.
    Runs in background and returns immediately.
    """
    token = repo.get_user_token(db, user.id)

    if not token:
        raise HTTPException(status_code=401, detail="Oura not connected")

    if is_sync_in_progress(user.id):
        return SyncResponse(
            success=False,
            mode="refresh",
            message="Sync already in progress",
            sync_in_progress=True,
        )

    refresh_days = days or settings.oura_refresh_days

    if background_tasks:
        background_tasks.add_task(_run_background_refresh, user.id, refresh_days)
        return SyncResponse(
            success=True,
            mode="refresh",
            message=f"Refresh started for {refresh_days} days",
            sync_in_progress=True,
        )
    else:
        # Synchronous fallback
        sync_service = SyncService(db)
        result = await sync_service.run_refresh(user.id, days=refresh_days)
        return SyncResponse(
            success=result.success,
            mode="refresh",
            message=f"Refresh complete: {sum(result.counts.values())} items" if result.success else f"Errors: {result.errors}",
        )


@router.post("/sync/cleanup", response_model=CleanupResponse)
async def sync_cleanup(
    max_days: int = Query(default=None, ge=1, le=365, description="Max age in days (default: 60)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run retention cleanup to delete old cached data.

    Enforces the 60-day retention cap as required by Oura API Agreement.
    """
    sync_service = SyncService(db)
    result = sync_service.run_cleanup(user_id=user.id, max_days=max_days)
    return CleanupResponse(**result)


@router.get("/cache/summary", response_model=CacheSummaryResponse)
async def get_cache_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get cache summary with counts and date ranges per endpoint."""
    summary = repo.get_cache_summary(db, user.id)
    return CacheSummaryResponse(**summary)
