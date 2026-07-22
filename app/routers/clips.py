import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth as auth_utils

router = APIRouter()


@router.get("/queue", response_model=list[schemas.ClipOut])
def get_queue(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Clip)
        .join(models.Highlight, models.Clip.highlight_id == models.Highlight.id)
        .join(models.Project, models.Highlight.project_id == models.Project.id)
        .filter(models.Project.owner_id == current_user.id)
        .order_by(models.Clip.created_at.desc())
        .all()
    )


@router.post("/{highlight_id}/queue", response_model=schemas.ClipOut)
def queue_clip(
    highlight_id: uuid.UUID,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    highlight = (
        db.query(models.Highlight)
        .join(models.Project, models.Highlight.project_id == models.Project.id)
        .filter(models.Highlight.id == highlight_id, models.Project.owner_id == current_user.id)
        .first()
    )
    if not highlight:
        raise HTTPException(404, "Highlight not found")

    clip = models.Clip(highlight_id=highlight.id, status=models.ClipStatus.queued)
    db.add(clip)
    db.commit()
    db.refresh(clip)

    return clip
