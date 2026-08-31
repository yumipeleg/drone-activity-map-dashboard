"""Application configuration, loaded from environment variables / .env file.

Kept as a single Settings object so every module imports the same
already-parsed configuration instead of re-reading environment variables.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[1] is backend/
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str

    # Origins allowed to call the API. The Angular dev server runs on
    # localhost:4200 by default.
    cors_allowed_origins: list[str] = ["http://localhost:4200"]

    # Runtime pipeline input directory (repo-root input/ locally; overridden
    # to /app/input in Docker Compose). Files are read directly at run time.
    pipeline_input_dir: str = str(_PROJECT_ROOT / "input")

    # Logical filename used when POST /api/pipeline/run omits input_file.
    pipeline_default_input_file: str = "sample_drones.json"

    # Celery message broker — Redis only; no result backend is configured.
    celery_broker_url: str = "redis://localhost:6379/0"


settings = Settings()
