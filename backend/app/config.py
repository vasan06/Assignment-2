import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ── AWS ───────────────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")

    # ── GitHub Actions (triggers FFmpeg transcoding) ──────────────────────────
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")          # e.g. "owner/repo"
    GITHUB_WORKFLOW_ID: str = os.getenv("GITHUB_WORKFLOW_ID", "process-video.yml")

    # ── Callback security ─────────────────────────────────────────────────────
    # GitHub Actions sends this in X-Internal-Token when calling /uploads/processing-complete
    # Must equal the PROCESSING_CALLBACK_TOKEN GitHub repository secret
    PROCESSING_CALLBACK_TOKEN: str = os.getenv("PROCESSING_CALLBACK_TOKEN", "change-me-in-production")

    # ── Local fallback (dev only — not used on Lambda) ────────────────────────
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")

    RESOLUTIONS: list = [
        {"name": "1080p", "height": 1080, "bitrate": "5000k"},
        {"name": "720p",  "height": 720,  "bitrate": "2500k"},
        {"name": "480p",  "height": 480,  "bitrate": "800k"},
        {"name": "360p",  "height": 360,  "bitrate": "500k"},
        {"name": "240p",  "height": 240,  "bitrate": "300k"},
        {"name": "144p",  "height": 144,  "bitrate": "150k"},
    ]

    class Config:
        env_file = ".env"


settings = Settings()
