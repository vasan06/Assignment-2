"""
GitHub Actions service.
Triggers the ffmpeg-transcode workflow via the GitHub REST API.
This allows processing to run in GitHub Actions with FFmpeg,
pulling from S3 and pushing results back to S3.
"""
import json
import logging
from typing import List

import urllib.request
import urllib.error

from app.config import settings

logger = logging.getLogger(__name__)


def trigger_transcode_workflow(
    video_id: int,
    video_uuid: str,
    s3_key: str,
    bucket: str,
    resolutions: List[str],
) -> bool:
    """
    Dispatch a GitHub Actions workflow_dispatch event to trigger FFmpeg transcoding.
    Returns True if the dispatch was accepted (HTTP 204), False otherwise.

    The workflow receives these inputs:
      - video_id: DB id for callback
      - video_uuid: S3 prefix UUID
      - s3_key: source video S3 key
      - bucket: S3 bucket name
      - resolutions: comma-separated list e.g. "1080p,720p,480p,360p,240p,144p"
    """
    if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO:
        logger.warning(
            "GITHUB_TOKEN or GITHUB_REPO not set — skipping GitHub Actions trigger. "
            "FFmpeg will run locally instead."
        )
        return False

    url = (
        f"https://api.github.com/repos/{settings.GITHUB_REPO}"
        f"/actions/workflows/{settings.GITHUB_WORKFLOW_ID}/dispatches"
    )

    payload = json.dumps({
        "ref": "main",
        "inputs": {
            "video_id": str(video_id),
            "video_uuid": video_uuid,
            "s3_key": s3_key,
            "bucket": bucket,
            "resolutions": ",".join(resolutions),
            "aws_region": settings.AWS_REGION,
        },
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 204
    except urllib.error.HTTPError as e:
        logger.error("GitHub Actions dispatch failed: %s %s", e.code, e.reason)
        return False
    except Exception as e:
        logger.error("GitHub Actions dispatch error: %s", e)
        return False


def get_workflow_file_content() -> str:
    """Returns the recommended GitHub Actions workflow YAML content."""
    return '''name: FFmpeg Video Transcode

on:
  workflow_dispatch:
    inputs:
      video_id:
        description: "Video DB ID"
        required: true
      video_uuid:
        description: "Video UUID (S3 prefix)"
        required: true
      s3_key:
        description: "S3 key of the source video"
        required: true
      bucket:
        description: "S3 bucket name"
        required: true
      resolutions:
        description: "Comma-separated resolutions e.g. 1080p,720p,480p,360p,240p,144p"
        required: true
      aws_region:
        description: "AWS region"
        required: true
        default: "ap-south-1"

jobs:
  transcode:
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
      - name: Install FFmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ inputs.aws_region }}

      - name: Download source video from S3
        run: |
          mkdir -p /tmp/transcode/${{ inputs.video_uuid }}
          aws s3 cp s3://${{ inputs.bucket }}/${{ inputs.s3_key }} \\
            /tmp/transcode/${{ inputs.video_uuid }}/source.mp4

      - name: Probe video dimensions
        id: probe
        run: |
          HEIGHT=$(ffprobe -v error -select_streams v:0 \\
            -show_entries stream=height \\
            -of default=noprint_wrappers=1:nokey=1 \\
            /tmp/transcode/${{ inputs.video_uuid }}/source.mp4)
          echo "height=$HEIGHT" >> $GITHUB_OUTPUT

      - name: Generate thumbnail
        run: |
          ffmpeg -y -ss 00:00:01 \\
            -i /tmp/transcode/${{ inputs.video_uuid }}/source.mp4 \\
            -vframes 1 -vf scale=640:-1 \\
            /tmp/transcode/${{ inputs.video_uuid }}/thumbnail.jpg
          aws s3 cp /tmp/transcode/${{ inputs.video_uuid }}/thumbnail.jpg \\
            s3://${{ inputs.bucket }}/videos/${{ inputs.video_uuid }}/thumbnail.jpg \\
            --content-type image/jpeg

      - name: Transcode resolutions
        run: |
          SRC="/tmp/transcode/${{ inputs.video_uuid }}/source.mp4"
          UUID="${{ inputs.video_uuid }}"
          BUCKET="${{ inputs.bucket }}"
          IFS=',' read -ra RESOLUTIONS <<< "${{ inputs.resolutions }}"

          declare -A HEIGHTS=([1080p]=1080 [720p]=720 [480p]=480 [360p]=360 [240p]=240 [144p]=144)
          declare -A BITRATES=([1080p]=5000k [720p]=2500k [480p]=800k [360p]=500k [240p]=300k [144p]=150k)
          declare -A BANDWIDTHS=([1080p]=5500000 [720p]=2800000 [480p]=1000000 [360p]=600000 [240p]=350000 [144p]=200000)
          declare -A RES_STRS=([1080p]="1920x1080" [720p]="1280x720" [480p]="854x480" [360p]="640x360" [240p]="426x240" [144p]="256x144")

          MASTER_LINES="#EXTM3U\\n#EXT-X-VERSION:3"

          for RES in "${RESOLUTIONS[@]}"; do
            H=${HEIGHTS[$RES]}
            SRC_H=${{ steps.probe.outputs.height }}
            if [ "$H" -gt "$SRC_H" ]; then
              echo "Skipping $RES (source height $SRC_H < $H)"
              continue
            fi

            mkdir -p /tmp/transcode/$UUID/hls/$RES
            ffmpeg -y -i $SRC \\
              -vf "scale=-2:$H,format=yuv420p" \\
              -c:a aac -ar 48000 -ac 2 \\
              -c:v h264 -profile:v main -level 4.0 \\
              -crf 20 -sc_threshold 0 -g 48 -keyint_min 48 \\
              -b:v ${BITRATES[$RES]} \\
              -hls_time 6 -hls_playlist_type vod \\
              -hls_flags independent_segments \\
              -hls_segment_filename "/tmp/transcode/$UUID/hls/$RES/seg_%03d.ts" \\
              /tmp/transcode/$UUID/hls/$RES/index.m3u8

            aws s3 sync /tmp/transcode/$UUID/hls/$RES/ \\
              s3://$BUCKET/videos/$UUID/hls/$RES/ \\
              --content-type "video/mp2t" --exclude "*.m3u8"
            aws s3 cp /tmp/transcode/$UUID/hls/$RES/index.m3u8 \\
              s3://$BUCKET/videos/$UUID/hls/$RES/index.m3u8 \\
              --content-type "application/vnd.apple.mpegurl"

            BW=${BANDWIDTHS[$RES]}
            RS=${RES_STRS[$RES]}
            MASTER_LINES="$MASTER_LINES\\n#EXT-X-STREAM-INF:BANDWIDTH=$BW,RESOLUTION=$RS,NAME=\\"$RES\\""
            MASTER_LINES="$MASTER_LINES\\n$RES/index.m3u8"
          done

          echo -e "$MASTER_LINES" > /tmp/transcode/$UUID/hls/master.m3u8
          aws s3 cp /tmp/transcode/$UUID/hls/master.m3u8 \\
            s3://$BUCKET/videos/$UUID/hls/master.m3u8 \\
            --content-type "application/vnd.apple.mpegurl"

      - name: Notify backend of completion
        run: |
          curl -X POST "${{ secrets.API_BASE_URL }}/uploads/processing-complete" \\
            -H "Content-Type: application/json" \\
            -H "Authorization: Bearer ${{ secrets.INTERNAL_API_KEY }}" \\
            -d '{
              "video_id": ${{ inputs.video_id }},
              "video_uuid": "${{ inputs.video_uuid }}",
              "status": "ready",
              "resolutions": "${{ inputs.resolutions }}"
            }'
'''
