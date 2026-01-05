#!/usr/bin/env python3
"""CLI script for backfilling Oura data.

Usage:
    python -m backend.scripts.oura_backfill --days 60
    python -m backend.scripts.oura_backfill --days 30 --endpoints daily_sleep daily_readiness
"""

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.oura import oauth
from backend.app.oura.client import OuraAPIError, OuraClient
from backend.app.oura.endpoints import BACKFILL_ENDPOINTS, get_endpoint_config
from backend.app.storage import repo
from backend.app.storage.db import get_db_session, init_db

settings = get_settings()


async def run_backfill(
    days: int,
    endpoints: list[str] | None = None,
    cleanup_first: bool = False,
) -> dict[str, int]:
    """Run backfill for specified endpoints.

    Args:
        days: Number of days to backfill.
        endpoints: List of endpoint names. None = all default endpoints.
        cleanup_first: If True, run cleanup before backfill.

    Returns:
        Dict of endpoint -> item count.
    """
    init_db()

    with get_db_session() as db:
        # Get user and token
        user = repo.get_or_create_default_user(db)
        token = repo.get_user_token(db, user.id)

        if not token:
            logger.error("No Oura OAuth token found. Please connect via web UI first.")
            logger.error("Visit http://localhost:8000/oura/connect/start")
            sys.exit(1)

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
                logger.info("Token refreshed successfully")
            except oauth.OAuthError as e:
                logger.error(f"Token refresh failed: {e}")
                logger.error("Please reconnect via web UI")
                sys.exit(1)

        # Optional cleanup
        if cleanup_first:
            logger.info(f"Running cleanup (max {settings.oura_cache_max_days} days)...")
            result = repo.cleanup_old_events(db)
            logger.info(f"Cleanup: deleted {result['total_deleted']} records")

        # Create client
        client = OuraClient(token.access_token)

        # Determine endpoints to fetch
        target_endpoints = endpoints or BACKFILL_ENDPOINTS

        # Date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Backfilling {len(target_endpoints)} endpoints")
        logger.info(f"Date range: {start_date} to {end_date} ({days} days)")

        counts: dict[str, int] = {}
        errors: list[str] = []

        for endpoint_name in target_endpoints:
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
                        db=db,
                        user_id=user.id,
                        endpoint=endpoint_name,
                        payload=item,
                        record_id=record_id,
                        day=day,
                        start_datetime=start_datetime,
                    )

                counts[endpoint_name] = len(items)
                logger.info(f"  {endpoint_name}: {len(items)} items")

            except OuraAPIError as e:
                error_msg = f"{endpoint_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"  {endpoint_name}: ERROR - {e}")
                counts[endpoint_name] = 0

        # Summary
        total_items = sum(counts.values())
        logger.info(f"\nBackfill complete: {total_items} total items")

        if errors:
            logger.warning(f"Errors encountered: {len(errors)}")
            for error in errors:
                logger.warning(f"  - {error}")

        return counts


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Oura data from the API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.scripts.oura_backfill --days 60
  python -m backend.scripts.oura_backfill --days 30 --endpoints daily_sleep daily_readiness
  python -m backend.scripts.oura_backfill --days 60 --cleanup
        """,
    )

    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Number of days to backfill (default: 60)",
    )

    parser.add_argument(
        "--endpoints",
        nargs="+",
        default=None,
        help=f"Specific endpoints to backfill (default: all). Available: {', '.join(BACKFILL_ENDPOINTS)}",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Run cleanup before backfill",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Run backfill
    counts = asyncio.run(
        run_backfill(
            days=args.days,
            endpoints=args.endpoints,
            cleanup_first=args.cleanup,
        )
    )

    # Output results
    if args.json:
        print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
