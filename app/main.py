import importlib
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base

# Set up logging for backend startup diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("torc-backend")

#try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as err:
    logger.warning(f"Could not auto-create database tables on boot: {err}")

#app = FastAPI(
    title="TORC AI - Steerable Video Clipping Engine",
    description="Backend API for transcribing, detecting viral highlights, and rendering video clips.",
    version="1.0.0"
)

# Allow requests from frontend web app domains and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#def register_routers():
    """Import and attach API routers explicitly to avoid circular import loops."""
    # Mount Auth Router
    try:
        from app.routers.auth import router as auth_router
        app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
        logger.info("Successfully mounted /api/auth router.")
    except Exception as e:
        logger.error(f"Failed to load auth router: {e}")

    # Mount Projects Router
    try:
        from app.routers.projects import router as projects_router
        app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
        logger.info("Successfully mounted /api/projects router.")
    except Exception as e:
        logger.error(f"Failed to load projects router: {e}")

    # Mount Custom Presets Router
    try:
        from app.routers.presets import router as presets_router
        app.include_router(presets_router, prefix="/api/presets", tags=["presets"])
        logger.info("Successfully mounted /api/presets router.")
    except Exception as e:
        logger.warning(f"Presets router optional mount skipped or failed: {e}")

register_routers()

#@app.get("/", tags=["health"])
def root_status():
    """Basic root health check response."""
    return {
        "status": "online",
        "service": "TORC AI Engine API",
        "docs": "/docs"
    }

@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for Render/hosting monitoring."""
    return {"status": "ok"}
