import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # AWS S3 storage settings
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")

    # Local storage fallback
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")

    # GitHub Actions webhook (optional - for triggering FFmpeg via GitHub Actions)
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")  # e.g. "owner/repo"
    GITHUB_WORKFLOW_ID: str = os.getenv("GITHUB_WORKFLOW_ID", "ffmpeg-transcode.yml")
    
    # Added to fix the Pydantic extra_forbidden validation error
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "change-this-internal-key")

    # Full resolution ladder: original, 1080p, 720p, 480p, 360p, 240p, 144p
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