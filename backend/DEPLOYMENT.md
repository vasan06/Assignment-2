# Deployment Notes

## Flow

1. Admin uploads from the Next.js frontend.
2. Frontend calls Lambda/FastAPI `/uploads/initiate`.
3. Lambda creates a video row and returns a presigned S3 URL.
4. Frontend uploads the source file directly to S3.
5. Frontend calls `/uploads/{id}/confirm`.
6. Lambda marks the video `processing`, emits an EventBridge event, and dispatches GitHub Actions.
7. GitHub Actions downloads the source from S3, runs ffmpeg, uploads HLS renditions and thumbnail to S3, then calls `/uploads/jobs/{id}/complete`.
8. Home only lists `ready` videos and refreshes every 30 seconds.

## Required S3 CORS

Configure the bucket to allow browser PUT uploads from your frontend host.

For production on Vercel:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedOrigins": ["https://your-vercel-domain.vercel.app"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

For local development with the frontend on `http://localhost:3000`:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedOrigins": ["http://localhost:3000"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

If your bucket CORS does not include the frontend origin, S3 preflight `OPTIONS` requests will fail with `403 Forbidden` and the browser upload will be blocked.

## Backend Lambda

Use `backend/lambda_handler.py` as the Lambda handler:

```text
lambda_handler.handler
```

Install `backend/requirements.txt` into the Lambda deployment package. For production-scale metadata, use Postgres for `DATABASE_URL`; SQLite is only for local development.

## GitHub Secrets

Add these repository secrets:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
AWS_S3_BUCKET
PUBLIC_API_URL
PROCESSING_CALLBACK_TOKEN
```

Also set backend env vars `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, and `PROCESSING_CALLBACK_TOKEN` so Lambda can dispatch `.github/workflows/process-video.yml`.

## Frontend Vercel

Set:

```text
NEXT_PUBLIC_API_URL=https://your-api-gateway-domain
```
