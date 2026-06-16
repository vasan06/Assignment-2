from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import VideoPlayStats, UserActivity, UserVideoLog
from app.auth_utils import get_current_admin
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/video-stats", response_model=List[VideoPlayStats])
def video_stats(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Total plays, unique viewers, avg watch duration per video."""
    return analytics_service.get_video_play_stats(db)


@router.get("/user-activity", response_model=List[UserActivity])
def user_activity(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Per-user summary: total watch time, distinct videos watched, last active."""
    return analytics_service.get_user_activity(db)


@router.get("/user/{user_id}/logs", response_model=List[UserVideoLog])
def user_video_logs(user_id: int, current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """For a specific user: which videos, how many times, total duration, last watched."""
    return analytics_service.get_user_video_logs(db, user_id)


@router.get("/repeated-videos")
def repeated_videos(current_user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Leaderboard: videos repeatedly watched, with which user and play counts."""
    return analytics_service.get_most_repeated_videos(db)
