from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers.auth import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.presets import router as presets_router

# Auto-create missing database tables on boot
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TORC AI Clipping Engine API",
    version="1.0.0",
    description="Production API for TORC AI Video Clipping Engine"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules directly to avoid circular import issues
app.include_router(auth_router, prefix="/api/auth")
app.include_router(projects_router, prefix="/api/projects")
app.include_router(presets_router, prefix="/api/presets")

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "TORC AI Backend Engine",
        "version": "1.0.0"
    }
