import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base


class VideoStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.pending, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    master_playlist_url = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    original_s3_key = Column(String, nullable=True)   # S3 key of the raw upload
    video_uuid = Column(String, nullable=True, index=True)  # UUID used for S3 prefix
    uploader_id = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    # Comma-separated list of ready resolutions e.g. "original,1080p,720p,480p"
    available_resolutions = Column(String, nullable=True)
    # EventBridge / processing tracking
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
