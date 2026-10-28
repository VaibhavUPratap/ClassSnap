"""
Health check endpoint.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from classsnap.config import get_settings
from classsnap.db.session import check_db_health, get_db
from classsnap.schemas.health import HealthCheckResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Returns current status of the ClassSnap application and database connectivity.",
)
def get_health(db: Session = Depends(get_db)) -> HealthCheckResponse:
    settings = get_settings()
    db_ok = check_db_health(db)

    return HealthCheckResponse(
        status="healthy" if db_ok else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database_status="connected" if db_ok else "disconnected",
        timestamp=datetime.now(timezone.utc),
    )
