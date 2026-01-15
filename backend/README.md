# Oura Agent Backend

FastAPI backend for Oura data ingestion and caching.

## Features

- OAuth 2.0 Authorization Code flow for Oura API
- Backfill all Oura v2 endpoints with pagination
- SQLite storage for raw JSON payloads
- 60-day retention policy (configurable)
- CLI script for manual backfill

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Oura OAuth application credentials

### 2. Setup

```bash
# From project root
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the **project root** (not in backend/):

```bash
# Copy example
cp .env.example ../.env

# Edit with your Oura credentials
vim ../.env
```

Required environment variables:
- `OURA_CLIENT_ID` - From Oura developer portal
- `OURA_CLIENT_SECRET` - From Oura developer portal

### 4. Run the Server

```bash
# From backend directory
uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## OAuth Flow

1. **Start OAuth**: Visit http://localhost:8000/oura/connect/start
2. **Authorize**: Redirects to Oura, log in and authorize
3. **Callback**: Oura redirects back to `/oura/callback`
4. **Done**: Tokens stored in SQLite, redirects to web app

## API Endpoints

### OAuth
- `GET /oura/connect/start` - Start OAuth flow
- `GET /oura/callback` - OAuth callback handler (auto-triggers backfill)
- `POST /oura/disconnect` - Delete stored tokens

### Data Sync
- `POST /oura/sync/backfill?days=60` - Full backfill (heavy), runs in background
- `POST /oura/sync/refresh?days=7` - Light refresh, runs in background
- `POST /oura/sync/cleanup` - Run retention cleanup (60-day cap, scoped to current user)
- `GET /oura/cache/summary` - Cache summary with counts and date ranges

### Data Access
- `GET /oura/backfill?days=60` - Legacy: Fetch and cache Oura data (synchronous)
- `GET /oura/raw?endpoint=daily_sleep&days=14` - Get cached data
- `POST /oura/cleanup` - Run retention cleanup (scoped to current user)
- `GET /oura/status` - Connection status and data summary

## CLI Backfill Script

```bash
# From project root directory
python -m backend.scripts.oura_backfill --days 60

# Specific endpoints only
python -m backend.scripts.oura_backfill --days 30 --endpoints daily_sleep daily_readiness

# Run cleanup before backfill
python -m backend.scripts.oura_backfill --days 60 --cleanup

# Output as JSON
python -m backend.scripts.oura_backfill --days 60 --json
```

## Verify Data

```bash
# Check SQLite database
sqlite3 local.db

# List tables
.tables

# Count records by endpoint
SELECT endpoint, COUNT(*) FROM oura_raw_events GROUP BY endpoint;

# View sample record
SELECT * FROM oura_raw_events LIMIT 1;
```

## Supported Oura Endpoints

| Endpoint | Description |
|----------|-------------|
| personal_info | User profile (no date range) |
| daily_sleep | Daily sleep scores |
| daily_readiness | Daily readiness scores |
| daily_activity | Daily activity scores |
| daily_spo2 | Blood oxygen levels |
| daily_stress | Stress levels |
| sleep | Detailed sleep periods |
| workout | Workouts |
| session | Meditation/focus sessions |

## Data Storage

- **Location**: `backend/local.db` (SQLite)
- **Retention**: 60 days (configurable via `OURA_CACHE_MAX_DAYS`)
- **Schema**: See `db/migrations/002_oura_raw_cache_sqlite.sql`

Raw JSON payloads are stored as-is in the `oura_raw_events` table. This allows for rapid iteration during development - we can parse/transform the data later.

## Data Sync

### Sync Modes

1. **Backfill** (heavy) - Fetches last 60 days of data. Triggered:
   - Automatically after OAuth connect
   - Manually via `POST /oura/sync/backfill`

2. **Refresh** (light) - Fetches last 7 days of data. Triggered:
   - Manually via `POST /oura/sync/refresh`
   - Automatically by scheduler (if enabled)

3. **Cleanup** - Deletes data older than 60 days (Oura API Agreement requirement):
   - Runs automatically after every sync
   - Can be triggered manually via `POST /oura/sync/cleanup`

### Background Scheduler (Optional)

Enable periodic refresh with environment variables:

```bash
ENABLE_SCHEDULER=true
SCHEDULER_INTERVAL_HOURS=12
```

When enabled, the scheduler runs a refresh every N hours to keep data fresh.

### Manual Sync via cURL

```bash
# Trigger backfill (60 days)
curl -X POST http://localhost:8000/oura/sync/backfill \
  -H "Authorization: Bearer <token>"

# Trigger refresh (7 days)
curl -X POST http://localhost:8000/oura/sync/refresh \
  -H "Authorization: Bearer <token>"

# Custom days
curl -X POST "http://localhost:8000/oura/sync/backfill?days=30" \
  -H "Authorization: Bearer <token>"

# Check cache summary
curl http://localhost:8000/oura/cache/summary \
  -H "Authorization: Bearer <token>"

# Run cleanup
curl -X POST http://localhost:8000/oura/sync/cleanup \
  -H "Authorization: Bearer <token>"
```

## Debug Config Endpoint

`/debug/config` is disabled by default. Enable it only for local debugging:

```bash
DEBUG_CONFIG_ENABLED=true
```

## Docker Development Note

To wipe the SQLite database on container start (dev only):

```bash
CLEAR_DB_ON_STARTUP=true
```

### Concurrency Protection

Only one sync operation can run at a time per user. If a sync is already in progress, subsequent requests return immediately with `sync_in_progress: true`.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── core/
│   │   ├── config.py        # Pydantic settings
│   │   └── logging.py       # Logging setup
│   ├── oura/
│   │   ├── oauth.py         # OAuth flow
│   │   ├── client.py        # API client
│   │   └── endpoints.py     # Endpoint definitions
│   ├── storage/
│   │   ├── db.py            # SQLite connection
│   │   ├── models.py        # SQLAlchemy models
│   │   └── repo.py          # Data access layer
│   └── api/
│       └── routes_oura.py   # API routes
├── scripts/
│   └── oura_backfill.py     # CLI backfill script
├── db/
│   └── migrations/          # Schema documentation
├── requirements.txt
└── README.md
```
