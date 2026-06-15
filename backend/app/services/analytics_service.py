from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.video import Video
from app.models.watch_log import WatchLog


def get_video_play_stats(db: Session):
    """Total plays, unique viewers, avg watch duration per video."""
    rows = (
        db.query(
            Video.id.label("video_id"),
            Video.title.label("title"),
            func.count(WatchLog.id).label("total_plays"),
            func.count(func.distinct(WatchLog.user_id)).label("unique_viewers"),
            func.avg(WatchLog.watch_duration).label("avg_watch_duration"),
        )
        .outerjoin(WatchLog, WatchLog.video_id == Video.id)
        .group_by(Video.id, Video.title)
        .order_by(func.count(WatchLog.id).desc())
        .all()
    )
    return [
        {
            "video_id": r.video_id,
            "title": r.title,
            "total_plays": r.total_plays or 0,
            "unique_viewers": r.unique_viewers or 0,
            "avg_watch_duration": float(r.avg_watch_duration or 0),
        }
        for r in rows
    ]


def get_user_activity(db: Session):
    """Per-user activity summary: total watch time, videos watched, last active."""
    rows = (
        db.query(
            User.id.label("user_id"),
            User.email.label("email"),
            User.name.label("name"),
            User.last_active.label("last_active"),
            func.coalesce(func.sum(WatchLog.watch_duration), 0).label("total_watch_time"),
            func.count(func.distinct(WatchLog.video_id)).label("videos_watched"),
        )
        .outerjoin(WatchLog, WatchLog.user_id == User.id)
        .group_by(User.id, User.email, User.name, User.last_active)
        .order_by(func.coalesce(func.sum(WatchLog.watch_duration), 0).desc())
        .all()
    )
    return [
        {
            "user_id": r.user_id,
            "email": r.email,
            "name": r.name,
            "total_watch_time": int(r.total_watch_time or 0),
            "videos_watched": r.videos_watched or 0,
            "last_active": r.last_active,
        }
        for r in rows
    ]


def get_user_video_logs(db: Session, user_id: int):
    """For a given user: which videos watched, how many times, total duration, last watched."""
    rows = (
        db.query(
            Video.id.label("video_id"),
            Video.title.label("video_title"),
            func.count(WatchLog.id).label("play_count"),
            func.coalesce(func.sum(WatchLog.watch_duration), 0).label("total_watch_duration"),
            func.max(WatchLog.created_at).label("last_watched"),
        )
        .join(WatchLog, WatchLog.video_id == Video.id)
        .filter(WatchLog.user_id == user_id)
        .group_by(Video.id, Video.title)
        .order_by(func.count(WatchLog.id).desc())
        .all()
    )
    return [
        {
            "video_id": r.video_id,
            "video_title": r.video_title,
            "play_count": r.play_count,
            "total_watch_duration": int(r.total_watch_duration or 0),
            "last_watched": r.last_watched,
        }
        for r in rows
    ]


def get_most_repeated_videos(db: Session, limit: int = 10):
    """Leaderboard of videos with highest repeat-watch counts per user."""
    rows = (
        db.query(
            Video.id.label("video_id"),
            Video.title.label("title"),
            User.id.label("user_id"),
            User.email.label("user_email"),
            func.count(WatchLog.id).label("play_count"),
        )
        .join(WatchLog, WatchLog.video_id == Video.id)
        .join(User, User.id == WatchLog.user_id)
        .group_by(Video.id, Video.title, User.id, User.email)
        .having(func.count(WatchLog.id) > 1)
        .order_by(func.count(WatchLog.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "video_id": r.video_id,
            "title": r.title,
            "user_id": r.user_id,
            "user_email": r.user_email,
            "play_count": r.play_count,
        }
        for r in rows
    ]
