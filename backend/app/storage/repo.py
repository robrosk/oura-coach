"""Repository pattern for database operations."""

import json
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from .models import Experiment, OuraOAuthToken, OuraRawEvent, User

settings = get_settings()


# =============================================================================
# User Repository
# =============================================================================


def get_or_create_default_user(db: Session) -> User:
    """Get or create the default MVP user.

    For MVP, we use a single user. Later this will be replaced
    with proper multi-user support.
    """
    user = db.execute(select(User)).scalar_one_or_none()
    if user is None:
        user = User(email="default@oura-agent.local")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created default user: {user.id}")
    return user


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID."""
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    """Get user by Google ID (sub claim)."""
    return db.execute(select(User).where(User.google_id == google_id)).scalar_one_or_none()


def create_user(
    db: Session,
    email: str,
    google_id: Optional[str] = None,
    name: Optional[str] = None,
    picture: Optional[str] = None,
) -> User:
    """Create a new user.

    Args:
        db: Database session.
        email: User's email address (required, unique).
        google_id: Google's unique user ID (sub claim).
        name: Display name from Google profile.
        picture: Profile picture URL from Google.

    Returns:
        The created User object.
    """
    user = User(
        email=email,
        google_id=google_id,
        name=name,
        picture=picture,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created user {user.id} with email {email}")
    return user


def update_user(
    db: Session,
    user_id: str,
    **kwargs,
) -> Optional[User]:
    """Update user fields.

    Args:
        db: Database session.
        user_id: The user's ID.
        **kwargs: Fields to update (name, picture, google_id).

    Returns:
        The updated User object, or None if not found.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    allowed_fields = {"name", "picture", "google_id"}
    for field, value in kwargs.items():
        if field in allowed_fields:
            setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    logger.info(f"Updated user {user_id}: {list(kwargs.keys())}")
    return user


def get_or_create_user_by_google(
    db: Session,
    email: str,
    google_id: str,
    name: Optional[str] = None,
    picture: Optional[str] = None,
) -> tuple[User, bool]:
    """Get existing user or create new one from Google OAuth.

    First tries to find by google_id, then by email.
    Updates profile info if user exists.

    Args:
        db: Database session.
        email: User's email from Google.
        google_id: Google's unique user ID.
        name: Display name from Google.
        picture: Profile picture URL.

    Returns:
        Tuple of (User, created) where created is True if new user.
    """
    # First try to find by google_id
    user = get_user_by_google_id(db, google_id)
    if user:
        # Update profile info if changed
        update_user(db, user.id, name=name, picture=picture)
        return user, False

    # Try to find by email (user might exist without google_id)
    user = get_user_by_email(db, email)
    if user:
        # Link Google account to existing user
        update_user(db, user.id, google_id=google_id, name=name, picture=picture)
        return user, False

    # Create new user
    user = create_user(db, email=email, google_id=google_id, name=name, picture=picture)
    return user, True


# =============================================================================
# OAuth Token Repository
# =============================================================================


def get_user_token(db: Session, user_id: str) -> Optional[OuraOAuthToken]:
    """Get OAuth token for a user."""
    return db.execute(
        select(OuraOAuthToken).where(OuraOAuthToken.user_id == user_id)
    ).scalar_one_or_none()


def upsert_user_token(
    db: Session,
    user_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: Optional[datetime] = None,
    scopes: Optional[str] = None,
) -> OuraOAuthToken:
    """Create or update OAuth token for a user."""
    existing = get_user_token(db, user_id)

    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.expires_at = expires_at
        existing.scopes = scopes
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated OAuth token for user {user_id}")
        return existing
    else:
        token = OuraOAuthToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scopes,
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        logger.info(f"Created OAuth token for user {user_id}")
        return token


def delete_user_token(db: Session, user_id: str) -> bool:
    """Delete OAuth token for a user."""
    result = db.execute(
        delete(OuraOAuthToken).where(OuraOAuthToken.user_id == user_id)
    )
    db.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info(f"Deleted OAuth token for user {user_id}")
    return deleted


def delete_user_raw_events(db: Session, user_id: str) -> int:
    """Delete all cached raw events for a user.

    Used when disconnecting to clear all cached Oura data.

    Returns:
        Number of deleted records.
    """
    result = db.execute(
        delete(OuraRawEvent).where(OuraRawEvent.user_id == user_id)
    )
    db.commit()
    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} raw events for user {user_id}")
    return deleted_count


# =============================================================================
# Raw Events Repository
# =============================================================================


def upsert_raw_event(
    db: Session,
    user_id: str,
    endpoint: str,
    payload: dict,
    record_id: Optional[str] = None,
    day: Optional[str] = None,
    start_datetime: Optional[str] = None,
) -> OuraRawEvent:
    """Insert or update a raw event record.

    Uses SQLite's INSERT OR REPLACE via unique constraint on
    (user_id, endpoint, record_id).
    """
    # Check if record exists
    existing = None
    if record_id:
        existing = db.execute(
            select(OuraRawEvent).where(
                OuraRawEvent.user_id == user_id,
                OuraRawEvent.endpoint == endpoint,
                OuraRawEvent.record_id == record_id,
            )
        ).scalar_one_or_none()

    payload_json = json.dumps(payload)

    if existing:
        existing.payload = payload_json
        existing.day = day
        existing.start_datetime = start_datetime
        existing.fetched_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        event = OuraRawEvent(
            user_id=user_id,
            endpoint=endpoint,
            record_id=record_id,
            day=day,
            start_datetime=start_datetime,
            payload=payload_json,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event


def get_raw_events(
    db: Session,
    user_id: str,
    endpoint: str,
    days: Optional[int] = None,
    limit: int = 1000,
) -> list[OuraRawEvent]:
    """Get raw events for a user/endpoint.

    Args:
        db: Database session.
        user_id: User ID.
        endpoint: Endpoint name (e.g., "daily_sleep").
        days: Only return events from the last N days (by day field).
        limit: Maximum number of records to return.
    """
    query = select(OuraRawEvent).where(
        OuraRawEvent.user_id == user_id,
        OuraRawEvent.endpoint == endpoint,
    )

    if days is not None:
        cutoff_day = (date.today() - timedelta(days=days)).isoformat()
        query = query.where(OuraRawEvent.day >= cutoff_day)

    query = query.order_by(OuraRawEvent.day.desc()).limit(limit)

    return list(db.execute(query).scalars().all())


def get_raw_events_by_range(
    db: Session,
    user_id: str,
    endpoint: str,
    start_day: str,
    end_day: str,
    limit: int = 1000,
) -> list[OuraRawEvent]:
    """Get raw events for a user/endpoint within a date range (by day field)."""
    query = (
        select(OuraRawEvent)
        .where(
            OuraRawEvent.user_id == user_id,
            OuraRawEvent.endpoint == endpoint,
            OuraRawEvent.day.isnot(None),
            OuraRawEvent.day >= start_day,
            OuraRawEvent.day <= end_day,
        )
        .order_by(OuraRawEvent.day.desc())
        .limit(limit)
    )

    return list(db.execute(query).scalars().all())


def count_raw_events_by_endpoint(db: Session, user_id: str) -> dict[str, int]:
    """Count raw events grouped by endpoint for a user."""
    from sqlalchemy import func

    results = db.execute(
        select(OuraRawEvent.endpoint, func.count(OuraRawEvent.id))
        .where(OuraRawEvent.user_id == user_id)
        .group_by(OuraRawEvent.endpoint)
    ).all()

    return {endpoint: count for endpoint, count in results}


def cleanup_old_events(db: Session, max_days: Optional[int] = None) -> dict[str, int]:
    """Delete events older than max_days.

    Cleans up based on both:
    1. fetched_at - when we cached the data
    2. day - the actual data date (for daily summaries)

    Args:
        max_days: Maximum age in days. Defaults to config value.

    Returns:
        Dict with counts of deleted records by cleanup type.
    """
    if max_days is None:
        max_days = settings.oura_cache_max_days

    cutoff_datetime = (datetime.utcnow() - timedelta(days=max_days)).isoformat()
    cutoff_day = (date.today() - timedelta(days=max_days)).isoformat()

    # Delete by fetched_at (cache age)
    result_fetched = db.execute(
        delete(OuraRawEvent).where(OuraRawEvent.fetched_at < cutoff_datetime)
    )
    deleted_by_fetched = result_fetched.rowcount

    # Delete by day (data age) - only for records with day field
    result_day = db.execute(
        delete(OuraRawEvent).where(
            OuraRawEvent.day.isnot(None),
            OuraRawEvent.day < cutoff_day,
        )
    )
    deleted_by_day = result_day.rowcount

    db.commit()

    logger.info(
        f"Cleanup complete: {deleted_by_fetched} by fetched_at, {deleted_by_day} by day"
    )

    return {
        "deleted_by_fetched_at": deleted_by_fetched,
        "deleted_by_day": deleted_by_day,
        "total_deleted": deleted_by_fetched + deleted_by_day,
    }


def get_cache_summary(db: Session, user_id: str) -> dict:
    """Get cache summary with counts and date ranges per endpoint.

    Returns:
        Dict with endpoint summaries including count, min_day, max_day.
    """
    from sqlalchemy import func

    results = db.execute(
        select(
            OuraRawEvent.endpoint,
            func.count(OuraRawEvent.id).label("count"),
            func.min(OuraRawEvent.day).label("min_day"),
            func.max(OuraRawEvent.day).label("max_day"),
            func.min(OuraRawEvent.fetched_at).label("oldest_fetch"),
            func.max(OuraRawEvent.fetched_at).label("newest_fetch"),
        )
        .where(OuraRawEvent.user_id == user_id)
        .group_by(OuraRawEvent.endpoint)
    ).all()

    endpoints = {}
    total_count = 0

    for row in results:
        endpoints[row.endpoint] = {
            "count": row.count,
            "min_day": row.min_day,
            "max_day": row.max_day,
            "oldest_fetch": row.oldest_fetch.isoformat() if row.oldest_fetch else None,
            "newest_fetch": row.newest_fetch.isoformat() if row.newest_fetch else None,
        }
        total_count += row.count

    return {
        "total_count": total_count,
        "endpoints": endpoints,
    }


# =============================================================================
# Experiments Repository
# =============================================================================


def create_experiment(
    db: Session,
    user_id: str,
    title: str,
    objective: str,
    hypothesis: str,
    protocol: str,
    duration_days: int,
    start_date: str,
    end_date: str,
    success_criteria: str,
    metrics: str | None = None,
) -> Experiment:
    """Create a new experiment for a user."""
    experiment = Experiment(
        user_id=user_id,
        title=title,
        objective=objective,
        hypothesis=hypothesis,
        protocol=protocol,
        duration_days=duration_days,
        start_date=start_date,
        end_date=end_date,
        success_criteria=success_criteria,
        metrics=metrics,
        status="active",
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def list_experiments(db: Session, user_id: str) -> list[Experiment]:
    """List experiments for a user (newest first)."""
    query = (
        select(Experiment)
        .where(Experiment.user_id == user_id)
        .order_by(Experiment.created_at.desc())
    )
    return list(db.execute(query).scalars().all())


def get_experiment(db: Session, user_id: str, experiment_id: str) -> Experiment | None:
    """Fetch a single experiment by id for a user."""
    return db.execute(
        select(Experiment).where(
            Experiment.user_id == user_id,
            Experiment.id == experiment_id,
        )
    ).scalar_one_or_none()


def update_experiment_status(
    db: Session,
    user_id: str,
    experiment_id: str,
    status: str,
    outcome: str | None = None,
) -> Experiment | None:
    """Update experiment status and optional outcome."""
    experiment = get_experiment(db, user_id, experiment_id)
    if not experiment:
        return None

    experiment.status = status
    if outcome:
        experiment.outcome = outcome
    experiment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(experiment)
    return experiment
