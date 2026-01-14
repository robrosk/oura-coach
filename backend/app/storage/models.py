"""SQLAlchemy ORM models for SQLite storage."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """User model with Google OAuth support for multi-user authentication."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)  # Required for auth
    google_id = Column(String(255), unique=True, nullable=True)  # Google 'sub' claim
    name = Column(String(255), nullable=True)  # Display name from Google
    picture = Column(Text, nullable=True)  # Profile picture URL from Google
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    oauth_token = relationship("OuraOAuthToken", back_populates="user", uselist=False, cascade="all, delete-orphan")
    raw_events = relationship("OuraRawEvent", back_populates="user", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="user", cascade="all, delete-orphan")


class OuraOAuthToken(Base):
    """OAuth tokens for Oura API access."""

    __tablename__ = "oura_oauth_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="oauth_token")


class OuraRawEvent(Base):
    """Raw JSON payloads from Oura API endpoints."""

    __tablename__ = "oura_raw_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(100), nullable=False)  # e.g., "daily_sleep", "workout"
    record_id = Column(String(100), nullable=True)  # Oura's document ID if present
    day = Column(String(10), nullable=True)  # DATE for daily summaries (YYYY-MM-DD)
    start_datetime = Column(String(30), nullable=True)  # ISO timestamp for time-series
    payload = Column(Text, nullable=False)  # Raw JSON
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="raw_events")

    __table_args__ = (
        # Prevent duplicate records per user/endpoint/record_id
        UniqueConstraint("user_id", "endpoint", "record_id", name="uq_user_endpoint_record"),
        # Indexes for common queries
        Index("idx_raw_events_user_endpoint", "user_id", "endpoint"),
        Index("idx_raw_events_fetched_at", "fetched_at"),
        Index("idx_raw_events_day", "day"),
    )


class Experiment(Base):
    """User-defined wellness experiments."""

    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    hypothesis = Column(Text, nullable=False)
    protocol = Column(Text, nullable=False)
    duration_days = Column(Integer, nullable=False)
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    success_criteria = Column(Text, nullable=False)
    metrics = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="experiments")

    __table_args__ = (
        Index("idx_experiments_user", "user_id"),
        Index("idx_experiments_status", "status"),
    )
