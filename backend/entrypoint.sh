#!/bin/bash
# Clear database on startup for clean local dev
rm -f /app/*.db /app/local.db

# Start uvicorn with hot-reload
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
