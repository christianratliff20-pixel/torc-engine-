import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Project, Highlight, User
from app.deps import get_current_user
from app.tasks import process_video_pipeline, run_detection_pass_two

router = APIRouter(tags=["projects"])

def get_max_redos_for_tier(plan_name: str) -> int:
    plan = plan_name.lower() if plan_name else "free"
    if plan == "free":
        return 3
    elif plan == "starter":
        return 6
    elif plan == "pro":
        return 9
    elif plan == "studio":
        return 12
    return 3

class ProjectOut(BaseModel):
    id: str
    name: str
    source_type: str
    status: str
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None
    instructions: Optional[str] = None
    preset: str
    clip_count: str
    redos_used: int

    class Config:
        from_attributes = True

class HighlightOut(BaseModel):
    id: str
    project_id: str
    batch_id: int
    start_seconds: float
    end_seconds: float
    score: Optional[float] = None
    label: str
    is_manual: bool
    is_smart_clip: bool
    sub_cuts_json: Optional[str] = None

    class Config:
        from_attributes = True

class ReDetectRequest(BaseModel):
    instructions: Optional[str] = ""
    preset: Optional[str] = "auto"
    clip_count: Optional[str] = "12"

@router.get("/", response_model=List[ProjectOut])
def list_user_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()

@router.get("/{project_id}", response_model=ProjectOut)
def get_project_details(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project

@router.get("/{project_id}/status", response_model=ProjectOut)
def get_project_status(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project

@router.get("/{project_id}/highlights", response_model=List[HighlightOut])
def get_project_highlights(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return db.query(Highlight).filter(Highlight.project_id == project_id).order_by(Highlight.start_seconds.asc()).all()

@router.post("/upload", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    instructions: Optional[str] = Form(None),
    preset: Optional[str] = Form("auto"),
    clip_count: Optional[str] = Form("12"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    video_path = f"/tmp/{project_id}.mp4"
    
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())

    new_project = Project(
        id=project_id,
        user_id=user.id,
        name=file.filename or "Uploaded Video",
        source_type="file",
        status="transcribing",
        file_path=video_path,
        instructions=instructions,
        preset=preset,
        clip_count=clip_count,
        redos_used=0
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    process_video_pipeline.delay(project_id)
    return new_project

@router.post("/{project_id}/re-detect", response_model=ProjectOut)
def re_detect_project(
    project_id: str,
    req: ReDetectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    max_redos = get_max_redos_for_tier(user.plan)
    if project.redos_used >= max_redos:
        raise HTTPException(
            status_code=403,
            detail=f"Redo limit reached. Your {user.plan.capitalize()} tier allows {max_redos} re-detections per project."
        )

    project.instructions = req.instructions
    project.preset = req.preset or "auto"
    project.clip_count = req.clip_count or "12"
    project.redos_used += 1
    project.status = "detecting"
    db.commit()
    db.refresh(project)

    run_detection_pass_two.delay(project.id)
    return project
