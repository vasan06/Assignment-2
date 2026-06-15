import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas import (
    ProcessingCompleteIn,
    ProcessingJobOut,
    UploadInitIn,
    UploadInitOut,
    VideoOut,
    VideoUploadResponse,
)
from app.auth_utils import get_current_admin
from app.services import storage_service, workflow_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


def require_processing_token(authorization: str = Header("")):
    expected = f"Bearer {settings.PROCESSING_CALLBACK_TOKEN}"
    if not settings.PROCESSING_CALLBACK_TOKEN or authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid processing token")


def start_processing(video: Video) -> None:
    workflow_service.emit_processing_event(video.id, video.source_s3_key, video.output_prefix)
    workflow_service.dispatch_github_processing(video.id)


@router.post("/initiate", response_model=UploadInitOut, status_code=201)
def initiate_upload(
    payload: UploadInitIn,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    video_uuid = uuid.uuid4().hex
    suffix = Path(payload.filename or "source.mp4").suffix or ".mp4"
    source_s3_key = f"uploads/{video_uuid}/source{suffix}"
    output_prefix = f"videos/{video_uuid}"

    video = Video(
        title=payload.title,
        description=payload.description,
        status=VideoStatus.pending,
        original_filename=payload.filename,
        uploader_id=current_user.id,
        source_s3_key=source_s3_key,
        output_prefix=output_prefix,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        upload_url = storage_service.create_presigned_put_url(source_s3_key, payload.content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to create presigned S3 upload URL: {exc}. "
                "Verify AWS credentials, bucket name, and S3 CORS configuration."
            ),
        )

    return UploadInitOut(
        video=video,
        upload_url=upload_url,
        message="Upload URL created. Send the file directly to S3, then confirm the upload.",
    )


@router.post("/{video_id}/confirm", response_model=VideoUploadResponse)
def confirm_upload(
    video_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    video.status = VideoStatus.processing
    video.processing_started_at = datetime.utcnow()
    video.processing_error = None
    db.commit()
    db.refresh(video)

    try:
        start_processing(video)
    except Exception as exc:
        video.status = VideoStatus.failed
        video.processing_error = str(exc)
        video.processing_completed_at = datetime.utcnow()
        db.commit()
        db.refresh(video)
        return VideoUploadResponse(video=video, message="Video uploaded but processing dispatch failed")

    return VideoUploadResponse(
        video=video,
        message="Video uploaded to S3. Processing has started and the video will appear when all renditions are ready.",
    )


@router.post("", response_model=VideoUploadResponse, status_code=201)
def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Upload the source to S3, then dispatch asynchronous ffmpeg processing."""
    video_uuid = uuid.uuid4().hex
    suffix = Path(file.filename or "source.mp4").suffix or ".mp4"
    source_s3_key = f"uploads/{video_uuid}/source{suffix}"
    output_prefix = f"videos/{video_uuid}"

    video = Video(
        title=title,
        description=description,
        status=VideoStatus.processing,
        original_filename=file.filename,
        uploader_id=current_user.id,
        source_s3_key=source_s3_key,
        output_prefix=output_prefix,
        processing_started_at=datetime.utcnow(),
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        storage_service.upload_stream_to_s3(file.file, source_s3_key, file.content_type)
        start_processing(video)
    except Exception as exc:
        video.status = VideoStatus.failed
        video.processing_error = str(exc)
        video.processing_completed_at = datetime.utcnow()
        db.commit()
        db.refresh(video)
        return VideoUploadResponse(video=video, message="Video upload failed")

    db.commit()
    db.refresh(video)

    return VideoUploadResponse(
        video=video,
        message="Video uploaded to S3. Processing has started and the video will appear when all renditions are ready.",
    )


@router.get("/status/{video_id}", response_model=VideoOut)
def upload_status(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get(
    "/jobs/{video_id}",
    response_model=ProcessingJobOut,
    dependencies=[Depends(require_processing_token)],
)
def processing_job(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or not video.source_s3_key or not video.output_prefix:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return ProcessingJobOut(
        video_id=video.id,
        source_s3_key=video.source_s3_key,
        output_prefix=video.output_prefix,
        title=video.title,
        original_filename=video.original_filename,
    )


@router.post(
    "/jobs/{video_id}/complete",
    response_model=VideoOut,
    dependencies=[Depends(require_processing_token)],
)
def complete_processing(
    video_id: int,
    payload: ProcessingCompleteIn,
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.processing_completed_at = datetime.utcnow()
    if payload.error:
        video.status = VideoStatus.failed
        video.processing_error = payload.error
    else:
        video.status = VideoStatus.ready
        video.thumbnail_url = payload.thumbnail_url
        video.master_playlist_url = payload.master_playlist_url
        video.duration_seconds = payload.duration_seconds
        video.renditions_json = json.dumps(payload.renditions)
        video.processing_error = None

    db.commit()
    db.refresh(video)
    return video


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
