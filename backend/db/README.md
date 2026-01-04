# Database Migrations

This folder contains SQL migrations for the Oura Coach backend.

## Current Approach

For now, migrations are simple numbered SQL files applied manually. Later we'll adopt [Alembic](https://alembic.sqlalchemy.org/) for Python-integrated migrations with proper up/down support.

## Local Postgres Setup

### Option 1: Docker (recommended)

```bash
docker run -d \
  --name oura-postgres \
  -e POSTGRES_USER=oura \
  -e POSTGRES_PASSWORD=oura \
  -e POSTGRES_DB=oura_coach \
  -p 5432:5432 \
  postgres:16
```

### Option 2: Native Install (macOS)

```bash
brew install postgresql@16
brew services start postgresql@16
createdb oura_coach
```

## Applying Migrations

Connect to your database and run the migration:

```bash
# Using psql with Docker
psql -h localhost -U oura -d oura_coach -f backend/db/migrations/001_init.sql

# Or if using native Postgres
psql -d oura_coach -f backend/db/migrations/001_init.sql
```

You'll be prompted for the password (`oura` if using Docker example above).

### Verify

```bash
psql -h localhost -U oura -d oura_coach -c "\dt"
```

Should show:
```
            List of relations
 Schema |       Name        | Type  | Owner
--------+-------------------+-------+-------
 public | terms_acceptances | table | oura
 public | users             | table | oura
```

## Rollback

Currently no automated rollback. To manually rollback `001_init.sql`:

```sql
drop table if exists terms_acceptances cascade;
drop table if exists users cascade;
drop function if exists update_updated_at_column cascade;
drop extension if exists pgcrypto;
```

## Migration Naming Convention

```
NNN_description.sql
```

- `NNN`: Zero-padded sequence number (001, 002, ...)
- `description`: Brief snake_case description

Examples:
- `001_init.sql`
- `002_add_oura_tokens.sql`
- `003_add_user_preferences.sql`

## Future: Alembic

When we add the Python backend, we'll switch to Alembic which provides:
- Automatic up/down migration generation
- Migration history tracking in the database
- Integration with SQLAlchemy models

For now, keep migrations simple and idempotent where possible (`create table if not exists`, `create index if not exists`).
