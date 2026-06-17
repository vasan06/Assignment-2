"""
Upload routes.

Flow:
  POST /uploads
    → save file to S3
    → create Video record (status=processing)
    → trigger GitHub Actions workflow_dispatch
    → return 201 immediately (frontend polls from here)

  POST /uploads/processing-complete          (called by GitHub Actions)
    → validate X-Internal-Token
    → mark video ready / failed
    → frontend poll picks it up on next tick

  GET  /uploads/status/{video_id}            (polled by frontend every 10s)
    → return current status + estimated remaining seconds
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, UploadFile, Form
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas import ProcessingStatusOut, VideoUploadResponse
from app.auth_utils import get_current_admin
from app.services import storage_service, ffmpeg_service, github_service, eventbridge_service

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALL_RESOLUTIONS = [r["name"] for r in settings.RESOLUTIONS]


# ── Local FFmpeg fallback (dev only) ──────────────────────────────────────────

def _run_local_transcode(video_id: int, source_path: str, work_dir: str, video_uuid: str):
    """Background task: runs FFmpeg locally. Only used when GitHub Actions is not configured."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        video.processing_started_at = datetime.now(timezone.utc)
        db.commit()

        thumb_path = os.path.join(work_dir, "thumbnail.jpg")
        ffmpeg_service.generate_thumbnail(source_path, thumb_path)
        if os.path.exists(thumb_path):
            thumb_key = f"videos/{video_uuid}/thumbnail.jpg"
            storage_service.upload_file_to_storage(thumb_path, s3_key=thumb_key)
            video.thumbnail_url = storage_service.get_public_url(thumb_path, s3_key=thumb_key)
            db.commit()

        hls_dir = os.path.join(work_dir, "hls")
        result = ffmpeg_service.transcode_to_hls(source_path, hls_dir)

        if result["success"]:
            s3_prefix = f"videos/{video_uuid}/hls"
            storage_service.upload_directory_to_storage(hls_dir, s3_prefix=s3_prefix)
            video.master_playlist_url = storage_service.get_master_playlist_url(video_uuid)
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
            v = db.query(Video).filter(Video.id == video_id).first()
            if v:
                v.status = VideoStatus.failed
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── POST /uploads ─────────────────────────────────────────────────────────────

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
    Upload a video.
    1. Save raw file to S3.
    2. Create DB record (status=processing).
    3. Trigger GitHub Actions workflow → returns 201 immediately.
    4. Frontend polls /uploads/status/:id until ready.
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
        saved = storage_service.save_upload(file.file, file.filename, subdir="uploads")
        source_path = saved["local_path"]
        work_dir = saved["dir"]
        video_uuid = saved["video_uuid"]

        video.video_uuid = video_uuid
        video.original_s3_key = saved.get("s3_key") or f"uploads/{video_uuid}/source"

        duration = ffmpeg_service.probe_duration(source_path)
        video.duration_seconds = duration
        db.commit()
        db.refresh(video)

        use_github = bool(
            settings.GITHUB_TOKEN
            and settings.GITHUB_REPO
            and saved.get("s3_key")
        )

        if use_github:
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
                message = "Video uploaded. Transcoding started — check back in a few minutes."
            else:
                # GitHub dispatch failed → fall back to local
                background_tasks.add_task(
                    _run_local_transcode, video.id, source_path, work_dir, video_uuid
                )
                message = "Video uploaded. Running transcode locally (GitHub Actions unavailable)."
        else:
            background_tasks.add_task(
                _run_local_transcode, video.id, source_path, work_dir, video_uuid
            )
            message = "Video uploaded. Transcoding started locally."

        db.refresh(video)

    except Exception:
        import traceback
        traceback.print_exc()
        video.status = VideoStatus.failed
        db.commit()
        db.refresh(video)
        message = "Upload failed during processing setup."

    return VideoUploadResponse(video=video, message=message)


# ── POST /uploads/processing-complete  (GitHub Actions callback) ──────────────

@router.post("/processing-complete")
def processing_complete(
    payload: dict,
    db: Session = Depends(get_db),
    x_internal_token: str = Header(None, alias="X-Internal-Token"),
):
    """
    Called by GitHub Actions on transcode completion (success or failure).

    Payload: { video_id, video_uuid, status, resolutions }
    Auth:    X-Internal-Token must match PROCESSING_CALLBACK_TOKEN env var.
    """
    if not settings.PROCESSING_CALLBACK_TOKEN or x_internal_token != settings.PROCESSING_CALLBACK_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

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


# ── GET /uploads/status/{video_id}  (polled by frontend) ─────────────────────

@router.get("/status/{video_id}", response_model=ProcessingStatusOut)
def upload_status(video_id: int, db: Session = Depends(get_db)):
    """
    Frontend polls this every 10 s after upload.
    Returns status + estimated seconds remaining.
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


# ── DELETE /uploads/{video_id} ────────────────────────────────────────────────

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
