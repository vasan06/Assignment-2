import enum
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text
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
    source_s3_key = Column(String, nullable=True)
    output_prefix = Column(String, nullable=True)
    renditions_json = Column(Text, nullable=True)
    processing_error = Column(Text, nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    original_filename = Column(String, nullable=True)
    uploader_id = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def renditions(self):
        return json.loads(self.renditions_json) if self.renditions_json else []

    @property
    def estimated_seconds(self):
        if not self.processing_started_at or self.processing_completed_at:
            return None
        elapsed = max(0, int((datetime.utcnow() - self.processing_started_at.replace(tzinfo=None)).total_seconds()))
        return max(30, 900 - elapsed)
