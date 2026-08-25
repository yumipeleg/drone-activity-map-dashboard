"""Application configuration, loaded from environment variables / .env file.

Kept as a single Settings object so every module imports the same
already-parsed configuration instead of re-reading environment variables.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[1] is backend/
_BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str

    # Origins allowed to call the API. The Angular dev server runs on
    # localhost:4200 by default.
    cors_allowed_origins: list[str] = ["http://localhost:4200"]

    # Absolute by default so the pipeline finds the sample file regardless
    # of the working directory the process was started from.
    pipeline_input_file: str = str(_BACKEND_DIR / "data" / "sample_drones.json")

    # Celery message broker — Redis only; no result backend is configured.
    celery_broker_url: str = "redis://localhost:6379/0"


settings = Settings()
