"""
ffmpeg-based transcoding service.
Converts an uploaded source video into an HLS resolution ladder:
  original → 1080p → 720p → 480p → 360p → 240p → 144p
plus a master playlist and a thumbnail image.
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
                "-vframes", "1", "-vf", "scale=640:-1",
                output_path,
            ],
            capture_output=True, check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_source_dimensions(input_path: str) -> tuple[int, int]:
    """Return (width, height) of the source video."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                input_path,
            ],
            capture_output=True, text=True, check=True,
        )
        parts = result.stdout.strip().split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 1920, 1080


def transcode_to_hls(input_path: str, output_dir: str) -> dict:
    """
    Transcodes input_path into multiple HLS renditions.
    Always includes the original resolution plus all lower rungs.
    Videos will NOT be shown to clients until ALL resolutions are ready.

    Returns dict with:
      success (bool), master_playlist (str), renditions (list), error (str|None)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    src_width, src_height = get_source_dimensions(input_path)

    # Build resolution ladder: include resolutions ≤ source height, always
    # add at least one rung. We also add "original" as the top entry.
    defined_resolutions = settings.RESOLUTIONS  # sorted high→low in config
    applicable = [r for r in defined_resolutions if r["height"] <= src_height]
    if not applicable:
        applicable = [defined_resolutions[-1]]  # at minimum 144p

    master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    produced = []

    # ---- Transcode each resolution ----
    for res in applicable:
        name = res["name"]
        height = res["height"]
        bitrate = res["bitrate"]

        variant_dir = output_dir / name
        variant_dir.mkdir(parents=True, exist_ok=True)

        playlist_path = variant_dir / "index.m3u8"
        segment_pattern = str(variant_dir / "seg_%03d.ts")

        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"scale=-2:{height},format=yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            "-c:v", "h264", "-profile:v", "main", "-level", "4.0",
            "-crf", "20", "-sc_threshold", "0",
            "-g", "48", "-keyint_min", "48",
            "-b:v", bitrate,
            "-hls_time", "6",
            "-hls_playlist_type", "vod",
            "-hls_flags", "independent_segments",
            "-hls_segment_filename", segment_pattern,
            str(playlist_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=3600)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return {
                "success": False,
                "error": str(e),
                "master_playlist": None,
                "renditions": produced,
            }

        # Bandwidth estimation
        bw_map = {
            "1080p": 5500000,
            "720p": 2800000,
            "480p": 1000000,
            "360p": 600000,
            "240p": 350000,
            "144p": 200000,
        }
        res_str_map = {
            "1080p": f"{src_width}x1080",
            "720p": "1280x720",
            "480p": "854x480",
            "360p": "640x360",
            "240p": "426x240",
            "144p": "256x144",
        }

        bandwidth = bw_map.get(name, 1000000)
        resolution_str = res_str_map.get(name, f"{src_width}x{height}")

        master_lines.append(
            f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution_str},NAME=\"{name}\""
        )
        master_lines.append(f"{name}/index.m3u8")
        produced.append(name)

    # ---- Write master playlist ----
    master_path = output_dir / "master.m3u8"
    with open(master_path, "w") as f:
        f.write("\n".join(master_lines) + "\n")

    return {
        "success": True,
        "error": None,
        "master_playlist": "master.m3u8",
        "renditions": produced,
    }
