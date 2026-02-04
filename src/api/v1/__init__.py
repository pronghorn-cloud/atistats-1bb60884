"""API v1 package."""

from fastapi import APIRouter

from src.api.v1 import public_bodies, ati_requests, ingestion

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    public_bodies.router,
    prefix="/public-bodies",
    tags=["Public Bodies"]
)
api_router.include_router(
    ati_requests.router,
    prefix="/ati-requests",
    tags=["ATI Requests"]
)
api_router.include_router(
    ingestion.router,
    prefix="/ingestion",
    tags=["Data Ingestion"]
)
