"""Route for `GET /api/stats` — fleet-wide summary statistics.

Thin by design, matching the other routers: querying/aggregation logic
lives in app/services/stats.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import StatsRead
from app.services import stats as stats_service

router = APIRouter(tags=["stats"])


@router.get("/api/stats", response_model=StatsRead)
def get_stats(db: Session = Depends(get_db)) -> StatsRead:
    """Whole-fleet summary, unaffected by the dashboard's drone filters.

    See app/services/stats.py for exactly which fields are computed from
    full telemetry history vs. each drone's latest row only.
    """
    return stats_service.get_stats(db)
