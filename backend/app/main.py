from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import Base, engine
from app.config import settings
from app.routes import auth, videos, uploads, analytics

# Create tables (use Alembic migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Streaming Platform API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve locally-stored video files (HLS playlists, segments, thumbnails)
# Only used when AWS S3 is not configured (local dev fallback)
storage_path = settings.LOCAL_STORAGE_PATH
os.makedirs(storage_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=storage_path), name="static")

app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(uploads.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "video-streaming-api", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
