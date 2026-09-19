"""
Garden Bot - FastAPI application.
Serves sensor readings, video stream, and frontend.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .database import init_db
from .routers import agent, readings, stream, fan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Frontend dist directory
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    logger.info("Starting Garden Bot API")
    init_db()
    logger.info(f"Database initialized at {settings.database_path}")
    yield
    logger.info("Shutting down Garden Bot API")


app = FastAPI(
    title="Garden Bot",
    description="Raspberry Pi sensor monitoring and automation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(readings.router)
app.include_router(stream.router)
app.include_router(fan.router)
app.include_router(agent.router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "database": str(settings.database_path)}


@app.get("/")
async def root():
    """Serve frontend index."""
    if FRONTEND_DIST.exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {"message": "Garden Bot API"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend assets."""
    file_path = FRONTEND_DIST / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    # Fallback to index for SPA routing
    if FRONTEND_DIST.exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {"message": "Not found"}
