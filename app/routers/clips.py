from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database import get_db
from app import models

# Lazy load the authentication dependency to avoid circular imports
def get_current_user_lazy():
from app.deps import get_current_user

# In your route definitions:
user = Depends(get_current_user)
    return get_current_user

router = APIRouter(prefix="/api/clips", tags=["clips"])

@router.get("/")
def get_clips(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_lazy())
):
    query = db.query(models.Clip).join(models.Project).filter(models.Project.user_id == current_user.id)
    if project_id:
        query = query.filter(models.Clip.project_id == project_id)
    return query.all()

@router.get("/{clip_id}")
def get_clip(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_lazy())
):
    clip = db.query(models.Clip).join(models.Project).filter(
        models.Clip.id == clip_id,
        models.Project.user_id == current_user.id
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return clip

@router.delete("/{clip_id}")
def delete_clip(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_lazy())
):
    clip = db.query(models.Clip).join(models.Project).filter(
        models.Clip.id == clip_id,
        models.Project.user_id == current_user.id
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    db.delete(clip)
    db.commit()
    return {"status": "success", "message": "Clip deleted successfully"}
