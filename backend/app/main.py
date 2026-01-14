"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_agent import router as agent_router
from .api.routes_auth import router as auth_router
from .api.routes_experiments import router as experiments_router
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


def _validate_config():
    """Validate and log configuration status on startup."""
    logger.info("=" * 50)
    logger.info("CONFIGURATION STATUS")
    logger.info("=" * 50)

    # Google OAuth
    google_configured = bool(settings.google_client_id and settings.google_client_secret)
    if google_configured:
        logger.info(f"✓ Google OAuth: CONFIGURED")
        logger.info(f"  - Client ID: {settings.google_client_id[:20]}...")
        logger.info(f"  - Redirect URI: {settings.google_redirect_uri}")
    else:
        logger.warning("✗ Google OAuth: NOT CONFIGURED")
        if not settings.google_client_id:
            logger.warning("  - GOOGLE_CLIENT_ID is empty or not set")
        if not settings.google_client_secret:
            logger.warning("  - GOOGLE_CLIENT_SECRET is empty or not set")

    # Oura OAuth
    oura_configured = bool(settings.oura_client_id and settings.oura_client_secret)
    if oura_configured:
        logger.info(f"✓ Oura OAuth: CONFIGURED")
        logger.info(f"  - Client ID: {settings.oura_client_id[:20]}...")
    else:
        logger.warning("✗ Oura OAuth: NOT CONFIGURED")

    # JWT
    jwt_default = settings.jwt_secret == "change-me-in-production-use-secure-random-string"
    if jwt_default:
        logger.warning("⚠ JWT Secret: USING DEFAULT (change in production!)")
    else:
        logger.info("✓ JWT Secret: CONFIGURED")

    # Database
    logger.info(f"✓ Database URL: {settings.database_url}")

    # Env file location
    from pathlib import Path
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        logger.info(f"✓ Env file found: {env_path}")
    else:
        logger.warning(f"✗ Env file NOT found at: {env_path}")

    logger.info("=" * 50)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global scheduler

    # Startup
    logger.info("Starting Oura Agent backend...")
    _validate_config()
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
app.include_router(agent_router)
app.include_router(experiments_router)


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


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration status (no secrets exposed)."""
    from pathlib import Path

    env_path = Path(__file__).parent.parent / ".env"

    return {
        "google_oauth": {
            "configured": bool(settings.google_client_id and settings.google_client_secret),
            "client_id_set": bool(settings.google_client_id),
            "client_id_preview": settings.google_client_id[:20] + "..." if settings.google_client_id else None,
            "client_secret_set": bool(settings.google_client_secret),
            "redirect_uri": settings.google_redirect_uri,
        },
        "oura_oauth": {
            "configured": bool(settings.oura_client_id and settings.oura_client_secret),
            "client_id_set": bool(settings.oura_client_id),
            "client_secret_set": bool(settings.oura_client_secret),
        },
        "jwt": {
            "using_default_secret": settings.jwt_secret == "change-me-in-production-use-secure-random-string",
            "algorithm": settings.jwt_algorithm,
            "expire_hours": settings.jwt_expire_hours,
        },
        "database": {
            "url": settings.database_url,
        },
        "env_file": {
            "expected_path": str(Path(__file__).parent.parent.parent / ".env"),
            "exists": (Path(__file__).parent.parent.parent / ".env").exists(),
        },
    }
