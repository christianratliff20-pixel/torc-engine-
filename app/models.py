import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    plan = Column(String, default="free")  # 'free', 'starter', 'pro', 'studio'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="user")
    presets = relationship("CustomPreset", back_populates="user")


class CustomPreset(Base):
    __tablename__ = "custom_presets"

    id = Column(String, primary_key=True, default=lambda: f"cp-{uuid.uuid4().hex[:8]}")
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="presets")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    source_type = Column(String, default="file")
    status = Column(String, default="transcribing")  # 'fetching', 'transcribing', 'detecting', 'ready', 'failed'
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    file_path = Column(String, nullable=True)
    instructions = Column(Text, nullable=True)
    preset = Column(String, default="auto")
    clip_count = Column(String, default="12")
    redos_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="projects")
    highlights = relationship("Highlight", back_populates="project", cascade="all, delete-orphan")


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    batch_id = Column(Integer, default=1)
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    score = Column(Float, nullable=True)
    label = Column(String, nullable=False)
    is_manual = Column(Boolean, default=False)
    is_smart_clip = Column(Boolean, default=True)
    sub_cuts_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="highlights")


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=lambda: f"clip-{uuid.uuid4().hex[:8]}")
    highlight_id = Column(String, ForeignKey("highlights.id"), nullable=True)
    status = Column(String, default="pending")  # 'pending', 'rendering', 'rendered', 'failed'
    error_message = Column(Text, nullable=True)
    output_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
