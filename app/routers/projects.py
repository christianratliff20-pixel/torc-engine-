import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth as auth_utils

router = APIRouter()


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Project)
        .filter(models.Project.owner_id == current_user.id)
        .order_by(models.Project.created_at.desc())
        .all()
    )


def _get_owned_project(project_id: uuid.UUID, current_user: models.User, db: Session) -> models.Project:
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.owner_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: uuid.UUID,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_project(project_id, current_user, db)


@router.get("/{project_id}/status", response_model=schemas.ProjectOut)
def get_project_status(
    project_id: uuid.UUID,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_project(project_id, current_user, db)


@router.get("/{project_id}/highlights", response_model=list[schemas.HighlightOut])
def get_highlights(
    project_id: uuid.UUID,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(project_id, current_user, db)
    return (
        db.query(models.Highlight)
        .filter(models.Highlight.project_id == project_id)
        .order_by(models.Highlight.start_seconds)
        .all()
    )


@router.post("/upload", response_model=schemas.ProjectOut)
def upload_project(
    file: UploadFile = File(...),
    user_instruction: str = Form(None),
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    project = models.Project(
        owner_id=current_user.id,
        name=file.filename,
        source_type=models.SourceType.upload,
        file_path=f"/data/uploads/{current_user.id}/{file.filename}",
        status=models.ProjectStatus.draft,
        user_instruction=user_instruction,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.post("/ingest", response_model=schemas.ProjectOut)
def ingest_project(
    payload: schemas.ProjectCreateFromLink,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if payload.platform not in models.SourceType.__members__:
        raise HTTPException(400, f"Unsupported platform: {payload.platform}")

    project = models.Project(
        owner_id=current_user.id,
        name=payload.url,
        source_type=models.SourceType[payload.platform],
        source_url=payload.url,
        status=models.ProjectStatus.fetching,
        user_instruction=payload.user_instruction,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return project
