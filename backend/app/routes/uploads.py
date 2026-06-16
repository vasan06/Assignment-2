import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas import (
    VideoOut,
    VideoUploadResponse,
    ProcessingStatusOut,
)
from app.auth_utils import get_current_admin
from app.config import settings
from app.services import storage_service, ffmpeg_service
from app.services import github_service, eventbridge_service

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Resolutions to request (names only)
ALL_RESOLUTIONS = [r["name"] for r in settings.RESOLUTIONS]


def _run_local_transcode(video_id: int, source_path: str, work_dir: str, video_uuid: str):
    """
    Background task: runs FFmpeg locally, then uploads HLS to S3.
    Used when GitHub Actions is not configured.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        video.processing_started_at = datetime.now(timezone.utc)
        db.commit()

        # Thumbnail
        thumb_path = os.path.join(work_dir, "thumbnail.jpg")
        ffmpeg_service.generate_thumbnail(source_path, thumb_path)
        if os.path.exists(thumb_path):
            thumb_key = f"videos/{video_uuid}/thumbnail.jpg"
            storage_service.upload_file_to_storage(thumb_path, s3_key=thumb_key)
            video.thumbnail_url = storage_service.get_public_url(thumb_path, s3_key=thumb_key)
            db.commit()

        # HLS transcoding
        hls_dir = os.path.join(work_dir, "hls")
        result = ffmpeg_service.transcode_to_hls(source_path, hls_dir)

        if result["success"]:
            s3_prefix = f"videos/{video_uuid}/hls"
            storage_service.upload_directory_to_storage(hls_dir, s3_prefix=s3_prefix)
            master_url = storage_service.get_master_playlist_url(video_uuid)
            video.master_playlist_url = master_url
            video.status = VideoStatus.ready
            video.available_resolutions = ",".join(result["renditions"])
            video.processing_completed_at = datetime.now(timezone.utc)
        else:
            video.status = VideoStatus.failed

        db.commit()
    except Exception:
        import traceback
        traceback.print_exc()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.failed
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("", response_model=VideoUploadResponse, status_code=201)
async def upload_video(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Upload a video file.

    Flow:
    1. Save original video to S3 (or local staging).
    2. Create DB record with status=processing.
    3. If GitHub Actions is configured: trigger the transcode workflow → returns immediately.
       Otherwise: run FFmpeg locally in a background task.
    4. Video is only marked `ready` (and shown to clients) after ALL resolutions complete.
    """
    video = Video(
        title=title,
        description=description,
        status=VideoStatus.processing,
        original_filename=file.filename,
        uploader_id=current_user.id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        # Save original upload
        saved = storage_service.save_upload(file.file, file.filename, subdir="uploads")
        source_path = saved["local_path"]
        work_dir = saved["dir"]
        video_uuid = saved["video_uuid"]

        video.video_uuid = video_uuid
        video.original_s3_key = saved.get("s3_key") or f"uploads/{video_uuid}/source"

        # Probe duration immediately (fast operation)
        duration = ffmpeg_service.probe_duration(source_path)
        video.duration_seconds = duration
        db.commit()
        db.refresh(video)

        # Decide processing path
        use_github = bool(settings.GITHUB_TOKEN and settings.GITHUB_REPO and saved.get("s3_key"))

        if use_github:
            # Trigger GitHub Actions workflow
            video.processing_started_at = datetime.now(timezone.utc)
            db.commit()
            triggered = github_service.trigger_transcode_workflow(
                video_id=video.id,
                video_uuid=video_uuid,
                s3_key=saved["s3_key"],
                bucket=settings.AWS_S3_BUCKET,
                resolutions=ALL_RESOLUTIONS,
            )
            if triggered:
                message = (
                    "Video uploaded to S3. Transcoding triggered via GitHub Actions. "
                    "It will be available once all resolutions are ready."
                )
            else:
                # Fall back to local
                background_tasks.add_task(
                    _run_local_transcode, video.id, source_path, work_dir, video_uuid
                )
                message = "Video uploaded. Transcoding started locally (GitHub Actions unavailable)."
        else:
            # Local ffmpeg in background
            background_tasks.add_task(
                _run_local_transcode, video.id, source_path, work_dir, video_uuid
            )
            num_res = len(ALL_RESOLUTIONS)
            est_secs = eventbridge_service.estimate_processing_seconds(duration, num_res)
            mins = est_secs // 60
            message = (
                f"Video uploaded. Transcoding to {num_res} resolutions started locally. "
                f"Estimated time: ~{mins} minute(s). "
                "The video will appear in the feed once all resolutions are ready."
            )

        db.refresh(video)

    except Exception:
        import traceback
        traceback.print_exc()
        video.status = VideoStatus.failed
        db.commit()
        db.refresh(video)
        message = "Upload failed during processing setup."

    return VideoUploadResponse(video=video, message=message)


@router.post("/processing-complete")
def processing_complete(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Webhook called by GitHub Actions when transcoding finishes.
    Marks video as ready and records available resolutions.

    Expected payload:
      { video_id, video_uuid, status, resolutions }
    """
    video_id = payload.get("video_id")
    video_uuid = payload.get("video_uuid")
    status = payload.get("status", "failed")
    resolutions = payload.get("resolutions", "")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if status == "ready":
        video.status = VideoStatus.ready
        video.available_resolutions = resolutions
        video.master_playlist_url = storage_service.get_master_playlist_url(video_uuid)
        video.thumbnail_url = (
            f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com"
            f"/videos/{video_uuid}/thumbnail.jpg"
        )
        video.processing_completed_at = datetime.now(timezone.utc)
    else:
        video.status = VideoStatus.failed

    db.commit()
    return {"ok": True}


@router.get("/status/{video_id}", response_model=ProcessingStatusOut)
def upload_status(video_id: int, db: Session = Depends(get_db)):
    """
    Polling endpoint for EventBridge-style processing status.
    Returns status + estimated remaining time.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    num_res = len(ALL_RESOLUTIONS)
    remaining = eventbridge_service.estimate_remaining_seconds(
        video.processing_started_at, video.duration_seconds, num_res
    )
    message = eventbridge_service.format_processing_message(
        video.status, video.processing_started_at, video.duration_seconds, num_res
    )

    return ProcessingStatusOut(
        video_id=video.id,
        status=video.status,
        processing_started_at=video.processing_started_at,
        processing_completed_at=video.processing_completed_at,
        available_resolutions=video.available_resolutions,
        estimated_remaining_seconds=remaining,
        message=message,
    )


@router.delete("/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return None
