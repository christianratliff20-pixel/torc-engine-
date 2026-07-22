import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth as auth_utils

router = APIRouter()


@router.get("", response_model=list[schemas.PlatformConnectionOut])
def list_connections(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.PlatformConnection)
        .filter(models.PlatformConnection.user_id == current_user.id)
        .all()
    )


@router.get("/{platform}/connect")
def connect(
    platform: str,
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    if platform not in models.Platform.__members__:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    raise HTTPException(
        501,
        f"{platform} OAuth not configured yet — register a developer app "
        f"with {platform} and add credentials to .env before this endpoint works.",
    )


@router.delete("/{connection_id}")
def disconnect(
    connection_id: uuid.UUID,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    conn = (
        db.query(models.PlatformConnection)
        .filter(
            models.PlatformConnection.id == connection_id,
            models.PlatformConnection.user_id == current_user.id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(404, "Connection not found")

    db.delete(conn)
    db.commit()
    return {"ok": True}
