from __future__ import annotations

import requests

from app.config import settings


def emit_processing_event(video_id: int, source_s3_key: str, output_prefix: str) -> None:
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return

    import boto3

    client = boto3.client(
        "events",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    client.put_events(
        Entries=[
            {
                "Source": "streamline.video",
                "DetailType": "VideoUploaded",
                "EventBusName": settings.AWS_EVENT_BUS_NAME,
                "Detail": (
                    "{"
                    f'"video_id": {video_id}, '
                    f'"source_s3_key": "{source_s3_key}", '
                    f'"output_prefix": "{output_prefix}"'
                    "}"
                ),
            }
        ]
    )


def dispatch_github_processing(video_id: int) -> None:
    if not settings.GITHUB_TOKEN or not settings.GITHUB_REPOSITORY:
        return

    url = (
        "https://api.github.com/repos/"
        f"{settings.GITHUB_REPOSITORY}/actions/workflows/"
        f"{settings.GITHUB_WORKFLOW_FILE}/dispatches"
    )
    response = requests.post(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": "main", "inputs": {"video_id": str(video_id)}},
        timeout=20,
    )
    response.raise_for_status()
