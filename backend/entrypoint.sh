#!/bin/bash
# Clear database on startup for clean local dev (opt-in)
if [ "${CLEAR_DB_ON_STARTUP}" = "true" ]; then
  rm -f /app/*.db /app/local.db
fi

# Start uvicorn with hot-reload
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
