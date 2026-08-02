from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

# Force the import from the specific module
import app.auth
from app.database import get_db
from app.tasks import process_video_pipeline, run_detection_pass_two

# Now reference it using the explicit module name
get_current_user = app.auth.get_current_user
router = APIRouter(prefix="/api/projects", tags=["projects"])

# Helper function to calculate limits based on Stripe plan
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
    return 3 # Default fallback

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    instructions: str = Form(None),
    preset: str = Form("auto"),
    clip_count: str = Form("auto"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    
    # Read the file and save it to the local /tmp disk so FFmpeg and Deepgram can find it
    video_path = f"/tmp/{project_id}.mp4"
    with open(video_path, "wb") as buffer:
        buffer.write(await file.read())
    
    new_project = Project(
        id=project_id,
        user_id=user.id,
        name=file.filename,
        source_type="file",
        status="transcribing",
        instructions=instructions,
        preset=preset,
        clip_count=clip_count,
        redos_used=0
    )
    db.add(new_project)
    db.commit()
    
    # Kick off the full pipeline (Transcribe -> Pass 1 -> Pass 2)
    process_video_pipeline.delay(project_id)
    return new_project

class ReDetectRequest(BaseModel):
    instructions: str
    preset: str
    clip_count: str

@router.post("/{project_id}/re-detect")
def re_detect_project(project_id: str, req: ReDetectRequest, db: Session = Depends(get_db), user = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # STRICT TIER LIMIT CHECK
    max_redos = get_max_redos_for_tier(user.plan)
    if project.redos_used >= max_redos:
        raise HTTPException(
            status_code=403, 
            detail=f"Redo limit reached. Your {user.plan.capitalize()} tier allows {max_redos} refetches per project."
        )

    # Update project with new steering instructions
    project.instructions = req.instructions
    project.preset = req.preset
    project.clip_count = req.clip_count
    project.redos_used += 1
    project.status = "detecting"
    
    # Wipe old highlights that haven't been queued for export
    db.query(Highlight).filter(Highlight.project_id == project_id).delete()
    db.commit()

    # Fire celery task for Pass 2 ONLY (skips transcription & Pass 1)
    run_detection_pass_two.delay(project.id)

    return project
