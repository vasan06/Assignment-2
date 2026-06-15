from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.database import Base, engine
from app.config import settings
from app.routes import auth, videos, uploads, analytics

# Create tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)


def ensure_video_columns():
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    columns = {
        row[1] for row in engine.connect().execute(text("PRAGMA table_info(videos)")).fetchall()
    }
    additions = {
        "source_s3_key": "VARCHAR",
        "output_prefix": "VARCHAR",
        "renditions_json": "TEXT",
        "processing_error": "TEXT",
        "processing_started_at": "DATETIME",
        "processing_completed_at": "DATETIME",
    }
    with engine.begin() as conn:
        for name, column_type in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE videos ADD COLUMN {name} {column_type}"))


ensure_video_columns()

app = FastAPI(title="Video Streaming Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local staging files in development.
Path(settings.LOCAL_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="static")

app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(uploads.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "video-streaming-api"}


@app.get("/health")
def health():
    return {"status": "healthy"}
