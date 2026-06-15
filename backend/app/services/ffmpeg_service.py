"""
ffmpeg-based transcoding service.
Converts an uploaded source video into an HLS resolution ladder
(original, 144p, 240p, 360p, 480p, 720p, 1080p) plus a master playlist and a thumbnail image.
"""
import os
import subprocess
from pathlib import Path

from app.config import settings


def probe_duration(input_path: str) -> int:
    """Return duration of the video in whole seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            capture_output=True, text=True, check=True,
        )
        return int(float(result.stdout.strip()))
    except Exception:
        return 0


def generate_thumbnail(input_path: str, output_path: str, timestamp: str = "00:00:01") -> bool:
    """Extract a single frame as a JPEG thumbnail."""
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", timestamp, "-i", input_path,
                "-vframes", "1", "-vf", "scale=320:-1",
                output_path,
            ],
            capture_output=True, check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_source_height(input_path: str) -> int:
    """Return the source video's height in pixels."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=height",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip())
    except Exception:
        return 1080


def get_source_width(input_path: str) -> int:
    """Return the source video's width in pixels."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip())
    except Exception:
        return 1920


def transcode_to_hls(input_path: str, output_dir: str) -> dict:
    """
    Transcodes input_path into multiple HLS renditions (limited to resolutions
    that don't exceed the source resolution) and writes a master playlist.

    Returns dict with keys: success (bool), master_playlist (relative filename),
    renditions (list of resolution names produced), error (str or None).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_height = get_source_height(input_path)
    source_width = get_source_width(input_path)
    renditions = [{"name": "original", "height": source_height, "bitrate": "6000k", "original": True}]
    renditions.extend(
        [
            rendition
            for rendition in sorted(settings.RESOLUTIONS, key=lambda item: item["height"], reverse=True)
            if rendition["height"] < source_height
        ]
    )

    master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    produced = []

    for res in renditions:
        name = res["name"]
        height = res["height"]
        bitrate = res["bitrate"]
        variant_dir = output_dir / name
        variant_dir.mkdir(parents=True, exist_ok=True)

        playlist_path = variant_dir / "index.m3u8"
        segment_pattern = str(variant_dir / "seg_%03d.ts")

        video_filter = "format=yuv420p" if res.get("original") else f"scale=-2:{height},format=yuv420p"
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", video_filter,
            "-c:a", "aac", "-ar", "48000",
            "-c:v", "h264", "-profile:v", "main",
            "-crf", "20", "-sc_threshold", "0",
            "-g", "48", "-keyint_min", "48",
            "-b:v", bitrate,
            "-hls_time", "6", "-hls_playlist_type", "vod",
            "-hls_segment_filename", segment_pattern,
            str(playlist_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=1800)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return {"success": False, "error": str(e), "master_playlist": None, "renditions": produced}

        # Approximate bandwidth for ABR selection (bits per second)
        bw_map = {
            "144p": 250000,
            "240p": 450000,
            "360p": 750000,
            "480p": 1000000,
            "720p": 2800000,
            "1080p": 5500000,
            "original": 6500000,
        }
        bandwidth = bw_map.get(name, 1000000)
        resolution_str = {
            "144p": "256x144",
            "240p": "426x240",
            "360p": "640x360",
            "480p": "854x480",
            "720p": "1280x720",
            "1080p": "1920x1080",
            "original": f"{source_width}x{source_height}",
        }.get(name, "")

        master_lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution_str}'
        )
        master_lines.append(f"{name}/index.m3u8")
        produced.append(name)

    master_path = output_dir / "master.m3u8"
    with open(master_path, "w") as f:
        f.write("\n".join(master_lines) + "\n")

    return {"success": True, "error": None, "master_playlist": "master.m3u8", "renditions": produced}
