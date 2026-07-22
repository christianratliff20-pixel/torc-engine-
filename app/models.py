import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Enum, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    fetching = "fetching"
    transcribing = "transcribing"
    detecting = "detecting"
    ready = "ready"
    failed = "failed"


class SourceType(str, enum.Enum):
    upload = "upload"
    youtube = "youtube"
    twitch = "twitch"
    tiktok = "tiktok"
    instagram = "instagram"
    x = "x"
    rss = "rss"


class ClipStatus(str, enum.Enum):
    queued = "queued"
    rendering = "rendering"
    rendered = "rendered"
    failed = "failed"


class Platform(str, enum.Enum):
    youtube = "youtube"
    tiktok = "tiktok"
    instagram = "instagram"
    x = "x"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = Column(String, default="free", nullable=False)
    billing_cycle = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)

    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String, nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)

    password_reset_token = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)

    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    has_used_trial = Column(Boolean, default=False)

    period_started_at = Column(DateTime, default=datetime.utcnow)
    minutes_used_this_period = Column(Float, default=0.0)
    minutes_rollover_balance = Column(Float, default=0.0)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    platform_connections = relationship("PlatformConnection", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.draft, nullable=False)
    error_message = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    user_instruction = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    highlights = relationship("Highlight", back_populates="project", cascade="all, delete-orphan")


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    start_seconds = Column(Float, nullable=False)
    end_seconds = Column(Float, nullable=False)
    label = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    selected = Column(Integer, default=0)
    matches_instruction = Column(Boolean, nullable=True)
    instruction_reasoning = Column(String, nullable=True)

    project = relationship("Project", back_populates="highlights")
    clip = relationship("Clip", back_populates="highlight", uselist=False)


class Clip(Base):
    __tablename__ = "clips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    highlight_id = Column(UUID(as_uuid=True), ForeignKey("highlights.id"), nullable=False)
    status = Column(Enum(ClipStatus), default=ClipStatus.queued, nullable=False)
    error_message = Column(String, nullable=True)
    output_path = Column(String, nullable=True)
    target_platforms = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    highlight = relationship("Highlight", back_populates="clip")


class PlatformConnection(Base):
    __tablename__ = "platform_connections"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_user_platform"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    external_account_id = Column(String, nullable=True)
    external_username = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="platform_connections")
