import argparse
import os
import shutil
from pathlib import Path

import boto3
import requests

from app.config import settings
from app.services import ffmpeg_service, storage_service


def api_headers() -> dict:
    return {"Authorization": f"Bearer {settings.PROCESSING_CALLBACK_TOKEN}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True, type=int)
    args = parser.parse_args()

    api_url = settings.PUBLIC_API_URL.rstrip("/")
    if not api_url:
        raise RuntimeError("PUBLIC_API_URL is required")

    job_response = requests.get(
        f"{api_url}/uploads/jobs/{args.video_id}",
        headers=api_headers(),
        timeout=30,
    )
    job_response.raise_for_status()
    job = job_response.json()

    work_dir = Path(settings.LOCAL_STORAGE_PATH) / "jobs" / str(args.video_id)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    source_path = work_dir / (job.get("original_filename") or "source.mp4")
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)

    try:
        s3.download_file(settings.AWS_S3_BUCKET, job["source_s3_key"], str(source_path))

        duration = ffmpeg_service.probe_duration(str(source_path))
        thumbnail_path = work_dir / "thumbnail.jpg"
        ffmpeg_service.generate_thumbnail(str(source_path), str(thumbnail_path))
        thumbnail_key = f"{job['output_prefix'].strip('/')}/thumbnail.jpg"
        s3.upload_file(
            str(thumbnail_path),
            settings.AWS_S3_BUCKET,
            thumbnail_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

        hls_dir = work_dir / "hls"
        result = ffmpeg_service.transcode_to_hls(str(source_path), str(hls_dir))
        if not result["success"]:
            raise RuntimeError(result["error"] or "ffmpeg processing failed")

        hls_prefix = f"{job['output_prefix'].strip('/')}/hls"
        storage_service.upload_directory_to_storage(str(hls_dir), hls_prefix)

        complete_payload = {
            "thumbnail_url": storage_service.get_s3_public_url(thumbnail_key),
            "master_playlist_url": storage_service.get_s3_public_url(f"{hls_prefix}/master.m3u8"),
            "duration_seconds": duration,
            "renditions": result["renditions"],
        }
    except Exception as exc:
        complete_payload = {"error": str(exc), "renditions": []}

    complete_response = requests.post(
        f"{api_url}/uploads/jobs/{args.video_id}/complete",
        headers=api_headers(),
        json=complete_payload,
        timeout=30,
    )
    complete_response.raise_for_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
