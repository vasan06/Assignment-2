"""
Storage service: saves uploaded files locally as a staging area (for ffmpeg
to read/write), then uploads the processed HLS output + thumbnail to AWS S3.

If AWS credentials are not configured, falls back to serving files from local
disk via the /static mount (useful for local development without AWS).
"""
import mimetypes
import os
import shutil
import uuid
from pathlib import Path

from app.config import settings

LOCAL_STORAGE = Path(settings.LOCAL_STORAGE_PATH)
LOCAL_STORAGE.mkdir(parents=True, exist_ok=True)

_s3_client = None


def _use_s3() -> bool:
    return bool(
        settings.AWS_ACCESS_KEY_ID
        and settings.AWS_SECRET_ACCESS_KEY
        and settings.AWS_S3_BUCKET
    )


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3

        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
    return _s3_client


def save_upload(file_obj, original_filename: str, subdir: str = "uploads") -> dict:
    """
    Saves an uploaded file to local disk (staging area for ffmpeg).
    Returns dict with video_uuid, local_path (source file), and dir (working dir).
    """
    video_uuid = uuid.uuid4().hex
    ext = Path(original_filename).suffix or ".mp4"

    target_dir = LOCAL_STORAGE / subdir / video_uuid
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"source{ext}"

    with open(target_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)

    return {"video_uuid": video_uuid, "local_path": str(target_path), "dir": str(target_dir)}


def get_public_url(local_path: str) -> str:
    """
    Returns a URL the frontend can use to access a file.
    - If S3 is configured, returns the S3 public URL for the corresponding key.
    - Otherwise, returns a local /static/... URL.
    """
    rel = os.path.relpath(local_path, LOCAL_STORAGE)
    rel = rel.replace(os.sep, "/")

    if _use_s3():
        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{rel}"

    return f"/static/{rel}"


def get_s3_public_url(key: str) -> str:
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def upload_stream_to_s3(file_obj, key: str, content_type: str | None = None) -> None:
    if not _use_s3():
        raise RuntimeError("AWS S3 settings are required for Lambda upload flow")

    client = _get_s3_client()
    extra_args = {"ContentType": content_type or "application/octet-stream"}
    client.upload_fileobj(file_obj, settings.AWS_S3_BUCKET, key, ExtraArgs=extra_args)


def create_presigned_put_url(key: str, content_type: str | None = None, expires_in: int = 3600) -> str:
    if not _use_s3():
        raise RuntimeError("AWS S3 settings are required for presigned uploads")

    return _get_s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key,
            "ContentType": content_type or "application/octet-stream",
        },
        ExpiresIn=expires_in,
    )


def upload_directory_to_storage(local_dir: str, remote_prefix: str) -> None:
    """
    Uploads every file under local_dir to S3, preserving the directory
    structure relative to LOCAL_STORAGE (so get_public_url() keys match).

    If S3 is not configured, this is a no-op (files are served from local
    disk via /static instead).
    """
    if not _use_s3():
        return

    client = _get_s3_client()
    local_dir_path = Path(local_dir)

    for root, _, files in os.walk(local_dir_path):
        for fname in files:
            file_path = Path(root) / fname
            relative_key = os.path.relpath(file_path, local_dir_path).replace(os.sep, "/")
            key = f"{remote_prefix.strip('/')}/{relative_key}" if remote_prefix else relative_key

            content_type, _ = mimetypes.guess_type(fname)
            if fname.endswith(".m3u8"):
                content_type = "application/vnd.apple.mpegurl"
            elif fname.endswith(".ts"):
                content_type = "video/mp2t"
            elif content_type is None:
                content_type = "application/octet-stream"

            client.upload_file(
                str(file_path),
                settings.AWS_S3_BUCKET,
                key,
                ExtraArgs={"ContentType": content_type},
            )


def upload_file_to_storage(local_path: str) -> None:
    """Uploads a single file (e.g. thumbnail) to S3, preserving its relative path."""
    if not _use_s3():
        return

    client = _get_s3_client()
    key = os.path.relpath(local_path, LOCAL_STORAGE).replace(os.sep, "/")

    content_type, _ = mimetypes.guess_type(local_path)
    if content_type is None:
        content_type = "application/octet-stream"

    client.upload_file(
        local_path,
        settings.AWS_S3_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
