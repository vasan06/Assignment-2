"""
Storage service: saves uploaded files locally as a staging area (for ffmpeg),
then uploads original + processed HLS output + thumbnail to AWS S3.
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
    Returns dict with video_uuid, local_path (source file), dir (working dir),
    and s3_key (S3 object key if uploaded).
    """
    video_uuid = uuid.uuid4().hex
    ext = Path(original_filename).suffix or ".mp4"

    target_dir = LOCAL_STORAGE / subdir / video_uuid
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"source{ext}"

    with open(target_path, "wb") as f:
        shutil.copyfileobj(file_obj, f)

    s3_key = None
    if _use_s3():
        s3_key = f"uploads/{video_uuid}/source{ext}"
        upload_file_to_storage(str(target_path), s3_key=s3_key)

    return {
        "video_uuid": video_uuid,
        "local_path": str(target_path),
        "dir": str(target_dir),
        "s3_key": s3_key,
    }


def get_public_url(local_path: str, s3_key: str = None) -> str:
    """
    Returns a URL the frontend can use to access a file.
    - If S3 is configured, returns the S3 public URL.
    - Otherwise, returns a local /static/... URL.
    """
    if _use_s3():
        key = s3_key or os.path.relpath(local_path, LOCAL_STORAGE).replace(os.sep, "/")
        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    rel = os.path.relpath(local_path, LOCAL_STORAGE).replace(os.sep, "/")
    return f"/static/{rel}"


def get_s3_key_for_hls(video_uuid: str, resolution: str, filename: str) -> str:
    """Build a consistent S3 key for HLS files."""
    return f"videos/{video_uuid}/hls/{resolution}/{filename}"


def get_master_playlist_url(video_uuid: str) -> str:
    """Returns the public URL for a video's master HLS playlist."""
    if _use_s3():
        key = f"videos/{video_uuid}/hls/master.m3u8"
        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
    # local fallback
    local_path = LOCAL_STORAGE / "uploads" / video_uuid / "hls" / "master.m3u8"
    return f"/static/uploads/{video_uuid}/hls/master.m3u8"


def upload_directory_to_storage(local_dir: str, s3_prefix: str = None) -> None:
    """
    Uploads every file under local_dir to S3.
    s3_prefix overrides the default relative-path calculation.
    """
    if not _use_s3():
        return

    client = _get_s3_client()
    local_dir_path = Path(local_dir)

    for root, _, files in os.walk(local_dir_path):
        for fname in files:
            file_path = Path(root) / fname
            if s3_prefix:
                relative = os.path.relpath(file_path, local_dir_path).replace(os.sep, "/")
                key = f"{s3_prefix}/{relative}"
            else:
                key = os.path.relpath(file_path, LOCAL_STORAGE).replace(os.sep, "/")

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


def upload_file_to_storage(local_path: str, s3_key: str = None) -> str:
    """
    Uploads a single file to S3.
    Returns the S3 key used.
    """
    if not _use_s3():
        return ""

    client = _get_s3_client()
    key = s3_key or os.path.relpath(local_path, LOCAL_STORAGE).replace(os.sep, "/")

    content_type, _ = mimetypes.guess_type(local_path)
    if content_type is None:
        content_type = "application/octet-stream"

    client.upload_file(
        local_path,
        settings.AWS_S3_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return key
