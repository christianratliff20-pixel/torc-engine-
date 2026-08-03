import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CustomPreset
from app.deps import get_current_user

router = APIRouter(tags=["presets"])

class PresetCreate(BaseModel):
    name: str
    prompt: str

class PresetOut(BaseModel):
    id: str
    name: str
    prompt: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[PresetOut])
def get_user_presets(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Fetch all saved custom style/prompt presets for the logged-in user."""
    return db.query(CustomPreset).filter(CustomPreset.user_id == user.id).all()

@router.post("/", response_model=PresetOut, status_code=status.HTTP_201_CREATED)
def create_custom_preset(
    req: PresetCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Save a new custom AI prompt directive preset to the database."""
    if not req.name.strip() or not req.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preset name and prompt directive cannot be empty."
        )

    new_preset = CustomPreset(
        id=f"cp-{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        name=req.name.strip(),
        prompt=req.prompt.strip()
    )
    db.add(new_preset)
    db.commit()
    db.refresh(new_preset)
    return new_preset

@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_preset(
    preset_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Delete a custom preset owned by the user."""
    preset = db.query(CustomPreset).filter(
        CustomPreset.id == preset_id,
        CustomPreset.user_id == user.id
    ).first()
    
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preset not found."
        )

    db.delete(preset)
    db.commit()
    return None
