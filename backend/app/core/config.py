"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


def _find_env_file() -> str:
    """Find .env file - works both locally and in Docker."""
    # Docker: /app/.env (mounted)
    docker_path = Path("/app/.env")
    if docker_path.exists():
        return str(docker_path)

    # Local dev: project root .env (4 levels up from this file)
    local_path = Path(__file__).parent.parent.parent.parent / ".env"
    return str(local_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Oura OAuth
    oura_client_id: str = ""
    oura_client_secret: str = ""
    oura_redirect_uri: str = "http://localhost:8000/oura/callback"
    oura_scopes: str = "daily personal"

    # Oura API URLs
    oura_auth_url: str = "https://cloud.ouraring.com/oauth/authorize"
    oura_token_url: str = "https://api.ouraring.com/oauth/token"
    oura_api_base_url: str = "https://api.ouraring.com"

    # Storage
    database_url: str = "sqlite:///./local.db"
    oura_cache_max_days: int = 60

    # Sync settings
    oura_refresh_days: int = 7  # Days to fetch during refresh (light sync)
    enable_scheduler: bool = False  # Enable periodic background refresh
    scheduler_interval_hours: int = 12  # Hours between scheduled refreshes

    # Logging
    log_level: str = "INFO"

    # Web redirect after OAuth
    web_app_url: str = "http://localhost:5173"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # JWT Authentication
    jwt_secret: str = "change-me-in-production-use-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # OpenAI
    openai_api_key: str = ""

    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
