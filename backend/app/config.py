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
    AWS_EVENT_BUS_NAME: str = os.getenv("AWS_EVENT_BUS_NAME", "default")

    # GitHub Actions processing handoff
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPOSITORY: str = os.getenv("GITHUB_REPOSITORY", "")
    GITHUB_WORKFLOW_FILE: str = os.getenv("GITHUB_WORKFLOW_FILE", "process-video.yml")
    PUBLIC_API_URL: str = os.getenv("PUBLIC_API_URL", "")
    PROCESSING_CALLBACK_TOKEN: str = os.getenv("PROCESSING_CALLBACK_TOKEN", "")

    # Local storage fallback (always used as a staging area before S3 upload,
    # and as the only storage if AWS credentials are not set)
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")

    # Resolution ladder: original plus all downgrade renditions requested by the client.
    RESOLUTIONS: list = [
        {"name": "144p", "height": 144, "bitrate": "200k"},
        {"name": "240p", "height": 240, "bitrate": "350k"},
        {"name": "360p", "height": 360, "bitrate": "600k"},
        {"name": "480p", "height": 480, "bitrate": "800k"},
        {"name": "720p", "height": 720, "bitrate": "2500k"},
        {"name": "1080p", "height": 1080, "bitrate": "5000k"},
    ]

    class Config:
        env_file = ".env"


settings = Settings()
