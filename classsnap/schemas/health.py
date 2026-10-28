"""
Health check schema models.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Current running environment")
    database_status: str = Field(..., description="Database connection health ('connected' or 'disconnected')")
    timestamp: datetime = Field(..., description="Current UTC timestamp")
