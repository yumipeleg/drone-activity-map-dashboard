"""Verifies the app can actually reach the configured PostgreSQL database.

This is separate from the /health endpoint on purpose: /health only reports
that the API process is alive, per the exercise's expected response shape.
"""

from sqlalchemy import text

from app.db.session import SessionLocal


def test_can_connect_to_database() -> None:
    with SessionLocal() as db:
        result = db.execute(text("SELECT 1")).scalar_one()

    assert result == 1
