"""Oura data sync orchestration.

Provides backfill (heavy) and refresh (light) sync operations
with automatic retention cleanup.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from ..storage import repo
from .client import OuraAPIError, OuraClient
from .endpoints import BACKFILL_ENDPOINTS, get_endpoint_config
from . import oauth

settings = get_settings()

# In-memory lock to prevent concurrent syncs for the same user
_sync_locks: dict[str, asyncio.Lock] = {}


def _get_user_lock(user_id: str) -> asyncio.Lock:
    """Get or create a lock for a specific user."""
    if user_id not in _sync_locks:
        _sync_locks[user_id] = asyncio.Lock()
    return _sync_locks[user_id]


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    mode: str  # "backfill" or "refresh"
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    cleanup_stats: Optional[dict[str, int]] = None


class SyncService:
    """Service for orchestrating Oura data synchronization."""

    def __init__(self, db: Session):
        self.db = db

    async def _get_authenticated_client(self, user_id: str) -> Optional[OuraClient]:
        """Get an authenticated OuraClient, refreshing token if needed.

        Returns None if user has no valid token (disconnected).
        """
        token = repo.get_user_token(self.db, user_id)
        if not token:
            return None

        # Check if token needs refresh
        if oauth.is_token_expired(token.expires_at):
            logger.info(f"Access token expired for user {user_id}, refreshing...")
            try:
                new_token_data = await oauth.refresh_access_token(token.refresh_token)

                expires_at = None
                if "expires_in" in new_token_data:
                    expires_at = oauth.calculate_token_expiry(new_token_data["expires_in"])

                token = repo.upsert_user_token(
                    db=self.db,
                    user_id=user_id,
                    access_token=new_token_data["access_token"],
                    refresh_token=new_token_data["refresh_token"],
                    expires_at=expires_at,
                    scopes=new_token_data.get("scope"),
                )
            except oauth.OAuthError as e:
                logger.error(f"Token refresh failed for user {user_id}: {e}")
                # Token is invalid, delete it to mark user as disconnected
                repo.delete_user_token(self.db, user_id)
                return None

        return OuraClient(token.access_token)

    async def _sync_endpoints(
        self,
        client: OuraClient,
        user_id: str,
        start_date: date,
        end_date: date,
        endpoints: list[str],
    ) -> tuple[dict[str, int], list[str]]:
        """Sync specified endpoints for a date range.

        Returns tuple of (counts, errors).
        """
        counts: dict[str, int] = {}
        errors: list[str] = []

        for endpoint_name in endpoints:
            try:
                config = get_endpoint_config(endpoint_name)

                # Fetch data
                if config.date_param_type is None:
                    items = await client.get_collection(endpoint_name)
                else:
                    items = await client.get_collection(endpoint_name, start_date, end_date)

                # Store each item
                for item in items:
                    record_id = item.get("id")
                    day = item.get("day")
                    start_datetime = item.get("start_datetime")

                    repo.upsert_raw_event(
                        db=self.db,
                        user_id=user_id,
                        endpoint=endpoint_name,
                        payload=item,
                        record_id=record_id,
                        day=day,
                        start_datetime=start_datetime,
                    )

                counts[endpoint_name] = len(items)
                logger.info(f"Synced {len(items)} items from {endpoint_name}")

            except OuraAPIError as e:
                error_msg = f"{endpoint_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Sync error for {endpoint_name}: {e}")
                counts[endpoint_name] = 0

        return counts, errors

    async def run_backfill(
        self,
        user_id: str,
        days: int = None,
        endpoints: Optional[list[str]] = None,
    ) -> SyncResult:
        """Run a full backfill sync (heavy).

        Args:
            user_id: User ID to sync for.
            days: Number of days to backfill. Defaults to oura_cache_max_days.
            endpoints: Specific endpoints to sync. Defaults to BACKFILL_ENDPOINTS.

        Returns:
            SyncResult with counts and any errors.
        """
        if days is None:
            days = settings.oura_cache_max_days
        if endpoints is None:
            endpoints = BACKFILL_ENDPOINTS

        lock = _get_user_lock(user_id)
        if lock.locked():
            return SyncResult(
                success=False,
                mode="backfill",
                errors=["Sync already in progress for this user"],
            )

        async with lock:
            logger.info(f"Starting backfill for user {user_id}: {days} days")

            client = await self._get_authenticated_client(user_id)
            if not client:
                return SyncResult(
                    success=False,
                    mode="backfill",
                    errors=["User not connected to Oura or token invalid"],
                )

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            counts, errors = await self._sync_endpoints(
                client, user_id, start_date, end_date, endpoints
            )

            # Always run cleanup after sync
            cleanup_stats = repo.cleanup_old_events(self.db, user_id=user_id)

            total_items = sum(counts.values())
            logger.info(
                f"Backfill complete for user {user_id}: "
                f"{total_items} items synced, {len(errors)} errors"
            )

            return SyncResult(
                success=len(errors) == 0,
                mode="backfill",
                counts=counts,
                errors=errors,
                cleanup_stats=cleanup_stats,
            )

    async def run_refresh(
        self,
        user_id: str,
        days: int = None,
        endpoints: Optional[list[str]] = None,
    ) -> SyncResult:
        """Run a light refresh sync.

        Args:
            user_id: User ID to sync for.
            days: Number of days to refresh. Defaults to oura_refresh_days.
            endpoints: Specific endpoints to sync. Defaults to BACKFILL_ENDPOINTS.

        Returns:
            SyncResult with counts and any errors.
        """
        if days is None:
            days = settings.oura_refresh_days
        if endpoints is None:
            endpoints = BACKFILL_ENDPOINTS

        lock = _get_user_lock(user_id)
        if lock.locked():
            return SyncResult(
                success=False,
                mode="refresh",
                errors=["Sync already in progress for this user"],
            )

        async with lock:
            logger.info(f"Starting refresh for user {user_id}: {days} days")

            client = await self._get_authenticated_client(user_id)
            if not client:
                return SyncResult(
                    success=False,
                    mode="refresh",
                    errors=["User not connected to Oura or token invalid"],
                )

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            counts, errors = await self._sync_endpoints(
                client, user_id, start_date, end_date, endpoints
            )

            # Always run cleanup after sync
            cleanup_stats = repo.cleanup_old_events(self.db, user_id=user_id)

            total_items = sum(counts.values())
            logger.info(
                f"Refresh complete for user {user_id}: "
                f"{total_items} items synced, {len(errors)} errors"
            )

            return SyncResult(
                success=len(errors) == 0,
                mode="refresh",
                counts=counts,
                errors=errors,
                cleanup_stats=cleanup_stats,
            )

    def run_cleanup(
        self,
        user_id: Optional[str] = None,
        max_days: Optional[int] = None,
    ) -> dict[str, int]:
        """Run retention cleanup.

        Args:
            max_days: Maximum age in days. Defaults to oura_cache_max_days.

        Returns:
            Dict with deleted counts.
        """
        return repo.cleanup_old_events(self.db, max_days=max_days, user_id=user_id)


def is_sync_in_progress(user_id: str) -> bool:
    """Check if a sync is currently in progress for a user."""
    if user_id not in _sync_locks:
        return False
    return _sync_locks[user_id].locked()
