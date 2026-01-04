-- Migration: 001_init.sql
-- Description: Initial schema for users and terms acceptance tracking
-- Created: 2026-01-04

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

-- Enable pgcrypto for gen_random_uuid() function
-- This provides cryptographically strong random UUIDs
create extension if not exists pgcrypto;

-- =============================================================================
-- USERS TABLE
-- =============================================================================

-- Minimal users table. Will be extended later with Oura integration fields.
-- For now, we just need a stable user identity to track terms acceptances.
create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    email text unique,  -- nullable: user may connect before providing email
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Index for email lookups (unique constraint already creates one, but being explicit)
create index if not exists idx_users_email on users(email) where email is not null;

-- =============================================================================
-- TERMS ACCEPTANCES TABLE
-- =============================================================================

-- WHY WE STORE ACCEPTANCE HISTORY:
-- 1. Version tracking: When we update Terms or Privacy Policy, we need to know
--    which version each user accepted. If terms change materially, we may need
--    to prompt re-acceptance.
-- 2. Cross-device support: A user may accept on web, then use iOS app. We need
--    server-side record of acceptance, not just localStorage.
-- 3. Compliance & audit: For legal/regulatory purposes, we must be able to prove
--    when a user accepted which version of our terms.
-- 4. Non-repudiation: Storing metadata (source, user_agent, ip) provides evidence
--    of the acceptance context if ever disputed.

create table if not exists terms_acceptances (
    id uuid primary key default gen_random_uuid(),

    -- User who accepted (cascade delete if user is removed)
    user_id uuid not null references users(id) on delete cascade,

    -- Version identifiers (date-based, e.g., '2026-01-04')
    -- Stored separately because Terms and Privacy may be updated independently
    terms_version text not null,
    privacy_version text not null,

    -- ACCEPTED_AT: Required timestamp of when acceptance occurred.
    -- Critical for:
    -- - Audit trail: proves when user accepted
    -- - Version validity: shows acceptance was after terms effective date
    -- - Ordering: find most recent acceptance per user
    accepted_at timestamptz not null default now(),

    -- SOURCE: Where the acceptance originated
    -- 'web' = React website, 'ios' = iOS app (future)
    -- Useful for analytics and debugging platform-specific issues
    source text not null default 'web',

    -- OPTIONAL METADATA (nullable):
    -- user_agent: Browser/app version string for debugging
    -- ip: IP address for geo/fraud detection (store as inet for proper indexing)
    -- These are optional but valuable for compliance and fraud prevention
    user_agent text,
    ip inet,

    -- UNIQUE CONSTRAINT: Prevent duplicate acceptances of the same version combo.
    -- Why this combination?
    -- - A user should only have ONE acceptance record per (terms_version, privacy_version) pair
    -- - If they re-accept the same versions (e.g., clear localStorage and re-do flow),
    --   we don't create duplicates - the first acceptance stands
    -- - When EITHER version changes, they must accept again -> new record allowed
    constraint uq_user_terms_privacy_version unique (user_id, terms_version, privacy_version)
);

-- INDEX: Fast lookup of user's latest acceptance
-- Common query: "Has user X accepted current terms?" or "What's user's latest acceptance?"
-- This index supports: SELECT ... WHERE user_id = ? ORDER BY accepted_at DESC LIMIT 1
create index if not exists idx_terms_acceptances_user_latest
    on terms_acceptances(user_id, accepted_at desc);

-- INDEX: Find all acceptances of a specific terms version (for compliance reporting)
create index if not exists idx_terms_acceptances_terms_version
    on terms_acceptances(terms_version);

-- =============================================================================
-- HELPER FUNCTION: Update updated_at timestamp
-- =============================================================================

-- Trigger function to auto-update updated_at on row modification
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Apply trigger to users table
drop trigger if exists trigger_users_updated_at on users;
create trigger trigger_users_updated_at
    before update on users
    for each row
    execute function update_updated_at_column();
