"""
Regras Operativas Service - Main Application Entry Point.

This service applies reservoir operational rules to NEWAVE/DECOMP cases.
"""

import os
import pathlib
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.internal.settings import Settings
from app.routers import health, reservoir
from app.utils.log import Log

# Set install directory for legacy compatibility
BASEDIR = pathlib.Path().resolve()
os.environ["APP_INSTALLDIR"] = os.path.dirname(os.path.abspath(__file__))

# Load environment variables
load_dotenv(
    pathlib.Path(os.getenv("APP_INSTALLDIR")).joinpath(".env"),
    override=True,
)
Settings.read_environments()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    Log.configure_logging(BASEDIR)
    Log.log().info("Starting regras-operativas-service")
    yield
    # Shutdown
    Log.log().info("Shutting down regras-operativas-service")


def create_app(
    root_path: str | None = None,
    debug: bool = False,
) -> FastAPI:
    """
    Application factory for creating FastAPI instances.

    Args:
        root_path: FastAPI root path (for reverse proxies)
        debug: Enable debug mode with docs

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Regras Operativas Service",
        description="REST API for applying reservoir operational rules to NEWAVE/DECOMP cases",
        version="2.0.0",
        root_path=root_path or Settings.root_path,
        debug=debug,
        lifespan=lifespan,
        docs_url="/docs" if debug else "/docs",
        redoc_url="/redoc" if debug else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(reservoir.router)

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=Settings.host,
        port=Settings.port,
        log_level=Settings.log_level.lower(),
    )
