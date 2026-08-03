from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import projects, auth, presets

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TORC AI Clipping Engine API",
    version="1.0.0",
    description="Production API for TORC AI Video Clipping Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(presets.router, prefix="/api/presets")

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "TORC AI Backend Engine",
        "version": "1.0.0"
    }
