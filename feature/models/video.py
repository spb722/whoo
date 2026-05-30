import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey,
    Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base


class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    FAILED = "failed"


class RoomVideo(Base):
    __tablename__ = "room_videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.UPLOADED)
    duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    display_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_room_video_user', 'room_id', 'user_id', unique=True),
    )


class CompilationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RoomCompilation(Base):
    __tablename__ = "room_compilations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(String(100), nullable=False, default="default")
    config = Column(String(2000), nullable=True)
    status = Column(SQLEnum(CompilationStatus), default=CompilationStatus.PENDING)
    storage_key = Column(String(500), nullable=True)
    video_count = Column(Integer, default=0)
    error_message = Column(String(1000), nullable=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('room_id', name='uq_compilation_room'),
    )
