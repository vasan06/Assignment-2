from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Video ----------
class VideoOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    thumbnail_url: Optional[str] = None
    master_playlist_url: Optional[str] = None
    renditions: List[str] = []
    processing_error: Optional[str] = None
    estimated_seconds: Optional[int] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VideoUploadResponse(BaseModel):
    video: VideoOut
    message: str


class UploadInitIn(BaseModel):
    title: str
    description: Optional[str] = ""
    filename: str
    content_type: Optional[str] = "application/octet-stream"


class UploadInitOut(BaseModel):
    video: VideoOut
    upload_url: str
    message: str


class ProcessingJobOut(BaseModel):
    video_id: int
    source_s3_key: str
    output_prefix: str
    title: str
    original_filename: Optional[str] = None


class ProcessingCompleteIn(BaseModel):
    thumbnail_url: Optional[str] = None
    master_playlist_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    renditions: List[str] = []
    error: Optional[str] = None


# ---------- Watch logs ----------
class WatchLogCreate(BaseModel):
    video_id: int
    watch_duration: int = 0


class WatchLogOut(BaseModel):
    id: int
    user_id: int
    video_id: int
    watch_duration: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Favorites ----------
class FavoriteOut(BaseModel):
    id: int
    video_id: int

    class Config:
        from_attributes = True


# ---------- Analytics ----------
class VideoPlayStats(BaseModel):
    video_id: int
    title: str
    total_plays: int
    unique_viewers: int
    avg_watch_duration: float


class UserActivity(BaseModel):
    user_id: int
    email: str
    name: Optional[str] = None
    total_watch_time: int
    videos_watched: int
    last_active: Optional[datetime] = None


class UserVideoLog(BaseModel):
    video_id: int
    video_title: str
    play_count: int
    total_watch_duration: int
    last_watched: datetime
