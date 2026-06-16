"""
EventBridge / processing status estimation service.

AWS EventBridge is used to receive notifications about video processing events.
When GitHub Actions completes transcoding, it calls back our API endpoint.

This module also provides estimated processing time calculations.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Approximate transcode multiplier: real-time seconds of processing per second of video
# This is a rough estimate — 1080p typically takes ~3-5x the video duration
TRANSCODE_MULTIPLIER_PER_RESOLUTION = {
    "1080p": 3.0,
    "720p":  2.0,
    "480p":  1.5,
    "360p":  1.0,
    "240p":  0.7,
    "144p":  0.5,
}


def estimate_processing_seconds(
    duration_seconds: Optional[int],
    num_resolutions: int,
) -> int:
    """
    Estimates the total processing time in seconds for FFmpeg transcoding.

    Args:
        duration_seconds: Video duration in seconds
        num_resolutions: Number of resolution variants to produce

    Returns:
        Estimated processing time in seconds
    """
    if not duration_seconds:
        return 120  # Default estimate: 2 minutes

    # Sum of multipliers for all resolutions (first few are most expensive)
    resolutions = list(TRANSCODE_MULTIPLIER_PER_RESOLUTION.values())[:num_resolutions]
    total_multiplier = sum(resolutions)
    return int(duration_seconds * total_multiplier) + 30  # +30s overhead


def estimate_remaining_seconds(
    processing_started_at: Optional[datetime],
    duration_seconds: Optional[int],
    num_resolutions: int,
) -> Optional[int]:
    """
    Estimates remaining processing time.
    Returns None if processing hasn't started.
    Returns 0 if estimated time has elapsed.
    """
    if not processing_started_at:
        return None

    total_estimated = estimate_processing_seconds(duration_seconds, num_resolutions)
    # SQLite returns naive datetimes; make it UTC-aware before subtracting
    if processing_started_at.tzinfo is None:
        processing_started_at = processing_started_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - processing_started_at).total_seconds()
    remaining = int(total_estimated - elapsed)
    return max(0, remaining)


def format_processing_message(
    status: str,
    started_at: Optional[datetime],
    duration_seconds: Optional[int],
    num_resolutions: int,
) -> str:
    """
    Returns a human-readable processing status message.
    """
    if status == "ready":
        return "Video is ready to watch in all resolutions."
    if status == "failed":
        return "Video processing failed. Please re-upload."
    if status == "pending":
        return "Video is queued for processing."

    # status == "processing"
    remaining = estimate_remaining_seconds(started_at, duration_seconds, num_resolutions)
    if remaining is None:
        return "Video is being transcoded. Please wait."

    total_est = estimate_processing_seconds(duration_seconds, num_resolutions)

    if remaining == 0:
        return (
            f"Almost done — transcoding to {num_resolutions} resolutions "
            f"(estimated {total_est}s total). Finishing up..."
        )

    mins = remaining // 60
    secs = remaining % 60
    time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    return (
        f"Transcoding to {num_resolutions} resolutions "
        f"(~{time_str} remaining, estimated {total_est}s total)."
    )
