from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.models.watch_log import WatchLog, Favorite
from app.schemas import VideoOut, WatchLogCreate, WatchLogOut, FavoriteOut
from app.auth_utils import get_current_user

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=List[VideoOut])
def list_videos(search: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns only videos that are fully ready (all resolutions processed).
    Videos in processing/pending/failed state are NOT shown to clients.
    """
    query = db.query(Video).filter(Video.status == VideoStatus.ready)
    if search:
        query = query.filter(Video.title.ilike(f"%{search}%"))
    return query.order_by(Video.created_at.desc()).all()


@router.get("/favorites/me", response_model=List[VideoOut])
def my_favorites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Video)
        .join(Favorite, Favorite.video_id == Video.id)
        .filter(Favorite.user_id == current_user.id, Video.status == VideoStatus.ready)
        .all()
    )


@router.get("/history/me", response_model=List[VideoOut])
def my_watch_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Video)
        .join(WatchLog, WatchLog.video_id == Video.id)
        .filter(WatchLog.user_id == current_user.id, Video.status == VideoStatus.ready)
        .order_by(WatchLog.created_at.desc())
        .distinct()
        .all()
    )


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/watch-log", response_model=WatchLogOut, status_code=201)
def log_watch(
    payload: WatchLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    log = WatchLog(
        user_id=current_user.id,
        video_id=payload.video_id,
        watch_duration=payload.watch_duration,
    )
    db.add(log)
    current_user.last_active = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log


@router.post("/{video_id}/favorite", response_model=FavoriteOut, status_code=201)
def add_favorite(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.video_id == video_id)
        .first()
    )
    if existing:
        return existing

    fav = Favorite(user_id=current_user.id, video_id=video_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


@router.delete("/{video_id}/favorite", status_code=204)
def remove_favorite(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fav = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.video_id == video_id)
        .first()
    )
    if fav:
        db.delete(fav)
        db.commit()
    return None
