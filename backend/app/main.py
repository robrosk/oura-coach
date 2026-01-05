"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_auth import router as auth_router
from .api.routes_oura import router as oura_router
from .core.config import get_settings
from .core.logging import logger
from .storage.db import init_db, SessionLocal
from .storage import repo

settings = get_settings()

# Optional scheduler (only imported if enabled)
scheduler: Optional["AsyncIOScheduler"] = None


async def _scheduled_refresh():
    """Scheduled refresh task for all connected users."""
    from .oura.sync import SyncService

    logger.info("Running scheduled refresh...")
    db = SessionLocal()
    try:
        # Get all users with tokens (for MVP, just the default user)
        user = repo.get_or_create_default_user(db)
        token = repo.get_user_token(db, user.id)

        if token:
            sync_service = SyncService(db)
            result = await sync_service.run_refresh(user.id)
            if result.success:
                logger.info(f"Scheduled refresh complete: {result.counts}")
            else:
                logger.error(f"Scheduled refresh failed: {result.errors}")
        else:
            logger.debug("No connected users, skipping scheduled refresh")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global scheduler

    # Startup
    logger.info("Starting Oura Agent backend...")
    init_db()
    logger.info("Database initialized")

    # Initialize scheduler if enabled
    if settings.enable_scheduler:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                _scheduled_refresh,
                IntervalTrigger(hours=settings.scheduler_interval_hours),
                id="oura_refresh",
                name="Oura Data Refresh",
                replace_existing=True,
            )
            scheduler.start()
            logger.info(
                f"Scheduler started: refresh every {settings.scheduler_interval_hours} hours"
            )
        except ImportError:
            logger.warning(
                "APScheduler not installed. Install with: pip install apscheduler"
            )

    yield

    # Shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    logger.info("Shutting down Oura Agent backend...")


app = FastAPI(
    title="Oura Agent API",
    description="Backend API for Oura data ingestion and analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.web_app_url,
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(oura_router)


@app.get("/")
async def root():
    """Root endpoint - basic health check."""
    return {
        "service": "oura-agent-backend",
        "status": "healthy",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
