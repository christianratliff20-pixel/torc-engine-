from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import projects, clips, auth, platforms, billing

app = FastAPI(title="Clipping Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(clips.router, prefix="/api/clips", tags=["clips"])
app.include_router(platforms.router, prefix="/api/platforms", tags=["platforms"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
