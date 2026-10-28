"""
API v1 Central Router for ClassSnap.
"""

from fastapi import APIRouter
from classsnap.api.v1.endpoints import attendance, enrollment, health, processing, roster

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(attendance.router)
api_v1_router.include_router(roster.router)
api_v1_router.include_router(enrollment.router)
api_v1_router.include_router(processing.router)
