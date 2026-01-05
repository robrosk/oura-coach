-- Migration: 002_oura_raw_cache_sqlite.sql
-- Description: SQLite schema for Oura raw data cache (temporary storage)
-- Created: 2026-01-04
-- Note: This is documentation only - SQLAlchemy creates tables automatically.
--       This file documents the schema for reference and manual debugging.

-- =============================================================================
-- USERS TABLE (minimal, MVP single-user)
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,  -- UUID as text
    email TEXT UNIQUE,    -- nullable for anonymous users
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- OAUTH TOKENS TABLE
-- =============================================================================
-- Stores Oura OAuth tokens per user.
-- Security note: Tokens stored as plaintext for MVP.
-- TODO: Add encryption wrapper for production.

CREATE TABLE IF NOT EXISTS oura_oauth_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TEXT,      -- ISO timestamp when access token expires
    scopes TEXT,          -- space-separated scopes
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id)       -- One token per user
);

-- =============================================================================
-- RAW EVENTS TABLE
-- =============================================================================
-- Stores raw JSON payloads from Oura API endpoints.
-- This is temporary cache storage with 60-day retention.

CREATE TABLE IF NOT EXISTS oura_raw_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Endpoint identification
    endpoint TEXT NOT NULL,           -- e.g., "daily_sleep", "workout"
    record_id TEXT,                   -- Oura's document ID (from "id" field in response)

    -- Time fields (one of these will be populated depending on endpoint type)
    day TEXT,                         -- DATE for daily summaries (YYYY-MM-DD)
    start_datetime TEXT,              -- ISO timestamp for time-series items

    -- Data storage
    payload TEXT NOT NULL,            -- Raw JSON response object

    -- Cache metadata
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Prevent duplicate records per user/endpoint/record_id
    UNIQUE(user_id, endpoint, record_id)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Fast lookup by user + endpoint (common query pattern)
CREATE INDEX IF NOT EXISTS idx_raw_events_user_endpoint
    ON oura_raw_events(user_id, endpoint);

-- For retention cleanup by cache age
CREATE INDEX IF NOT EXISTS idx_raw_events_fetched_at
    ON oura_raw_events(fetched_at);

-- For retention cleanup by data age
CREATE INDEX IF NOT EXISTS idx_raw_events_day
    ON oura_raw_events(day);

-- =============================================================================
-- RETENTION POLICY (executed via application code)
-- =============================================================================
-- The following queries are run by the cleanup function:
--
-- Delete by cache age (when we fetched the data):
-- DELETE FROM oura_raw_events WHERE fetched_at < datetime('now', '-60 days');
--
-- Delete by data age (the actual data date):
-- DELETE FROM oura_raw_events WHERE day IS NOT NULL AND day < date('now', '-60 days');
--
-- This ensures:
-- 1. Cached data doesn't persist longer than 60 days (per data agreement)
-- 2. Old daily summaries are cleaned up even if recently re-fetched
