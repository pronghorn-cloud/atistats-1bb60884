"""AI-Academy 3 ATI Stats - Main Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.api.v1 import api_router
from src.ui import ui_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    print(f"Starting {settings.APP_NAME}...")
    print(f"Dashboard available at: http://{settings.HOST}:{settings.PORT}/")
    print(f"API docs available at: http://{settings.HOST}:{settings.PORT}{settings.API_V1_PREFIX}/docs")
    yield
    # Shutdown
    print(f"Shutting down {settings.APP_NAME}...")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Track, analyze, and report on Access to Information (ATI) requests",
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Include UI router (serves the web interface)
    app.include_router(ui_router)

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "app": settings.APP_NAME}

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
