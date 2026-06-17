# Video Streaming Platform

Next.js frontend · FastAPI on AWS Lambda · S3 · GitHub Actions (FFmpeg)

---

## How it works

```
1. Admin uploads a video from the frontend.

2. Lambda receives the file, saves it to S3, creates a DB record
   (status = processing), then fires a GitHub Actions workflow_dispatch.
   It responds 201 immediately — the frontend does NOT wait.

3. GitHub Actions runner:
   - Downloads the raw video from S3
   - Runs FFmpeg to generate HLS at multiple resolutions
   - Uploads HLS segments + master.m3u8 + thumbnail back to S3
   - POSTs to /uploads/processing-complete on the Lambda

4. Lambda marks the video ready in the DB.

5. Frontend has been polling /uploads/status/:id every 10 s.
   It sees status = ready, shows the Watch button.
   The HLS player loads master.m3u8 directly from S3.
```

Nothing is hidden from you — every step is visible in GitHub Actions logs
and in the DB status field.

---

## Folder structure

```
Assignment-2/
├── .github/
│   └── workflows/
│       └── process-video.yml   ← FFmpeg transcoding job
├── backend/
│   ├── app/
│   │   ├── models/             ← SQLAlchemy models
│   │   ├── routes/             ← FastAPI routers
│   │   │   └── uploads.py      ← upload + status + callback endpoints
│   │   ├── services/
│   │   │   ├── github_service.py     ← fires workflow_dispatch
│   │   │   ├── storage_service.py    ← S3 helpers
│   │   │   └── eventbridge_service.py ← status/time estimates
│   │   ├── config.py           ← all env vars in one place
│   │   └── main.py             ← FastAPI app
│   ├── handler.py              ← Mangum Lambda entry point
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/                ← Next.js pages
    │   ├── components/
    │   │   └── UploadForm.tsx  ← upload UI with live status polling
    │   ├── services/           ← API client functions
    │   └── types/              ← TypeScript interfaces
    └── .env.local.example
```

---

## Local development (no AWS needed)

When AWS credentials are absent the backend stores files locally and runs
FFmpeg in-process. Good for testing auth, video listing, and the player.

### 1 · Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# No edits needed for local dev — SQLite + local storage defaults are fine

uvicorn app.main:app --reload --port 8000
```

Swagger UI → http://localhost:8000/docs

### 2 · Frontend

```bash
cd frontend
npm install

# Create env file
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local

npm run dev
```

App → http://localhost:3000

---

## Production setup

### Step 1 — S3 bucket

Replace `YOUR_BUCKET` and `YOUR_REGION` throughout.

```bash
# Create bucket
aws s3 mb s3://YOUR_BUCKET --region YOUR_REGION

# CORS (required — browser fetches HLS segments directly from S3)
aws s3api put-bucket-cors --bucket YOUR_BUCKET --cors-configuration '{
  "CORSRules": [{
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }]
}'

# Allow public read on videos/ prefix
aws s3api put-public-access-block --bucket YOUR_BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3api put-bucket-policy --bucket YOUR_BUCKET --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::YOUR_BUCKET/videos/*"
  }]
}'
```

### Step 2 — IAM user (for both Lambda and GitHub Actions)

```bash
aws iam create-user --user-name video-platform

aws iam put-user-policy --user-name video-platform \
  --policy-name S3Full \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:PutObject","s3:GetObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET",
        "arn:aws:s3:::YOUR_BUCKET/*"
      ]
    }]
  }'

# Save AccessKeyId and SecretAccessKey — you only see the secret once
aws iam create-access-key --user-name video-platform
```

### Step 3 — Lambda function (zip deploy, no Docker)

```bash
cd backend

# Install into a local package directory
pip install -r requirements.txt -t ./package \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11

# Add application code
cp -r app handler.py ./package/

# Zip it up
cd package && zip -r ../lambda.zip . && cd ..

# Create the function (first time only)
aws lambda create-function \
  --function-name video-platform-api \
  --runtime python3.11 \
  --handler handler.handler \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_LAMBDA_ROLE \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --region YOUR_REGION

# Update code on subsequent deploys
aws lambda update-function-code \
  --function-name video-platform-api \
  --zip-file fileb://lambda.zip \
  --region YOUR_REGION
```

> **Lambda IAM role** needs: `AWSLambdaBasicExecutionRole` (for CloudWatch logs).
> S3 access is handled by the IAM user credentials you pass as env vars.

### Step 4 — Lambda environment variables

Set these in the AWS console:
**Lambda → video-platform-api → Configuration → Environment variables**

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` (or leave SQLite for demos) |
| `SECRET_KEY` | random 64-char string — `python -c "import secrets; print(secrets.token_hex(32))"` |
| `AWS_ACCESS_KEY_ID` | from Step 2 |
| `AWS_SECRET_ACCESS_KEY` | from Step 2 |
| `AWS_REGION` | `ap-south-1` |
| `AWS_S3_BUCKET` | `YOUR_BUCKET` |
| `GITHUB_TOKEN` | GitHub PAT — see Step 5 |
| `GITHUB_REPO` | `vasan06/Assignment-2` |
| `GITHUB_WORKFLOW_ID` | `process-video.yml` |
| `PROCESSING_CALLBACK_TOKEN` | random 64-char string — **same value** as the GitHub secret below |

### Step 5 — Lambda Function URL (public HTTPS endpoint)

```bash
aws lambda create-function-url-config \
  --function-name video-platform-api \
  --auth-type NONE \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["*"],"AllowHeaders":["*"]}' \
  --region YOUR_REGION
```

The output contains `FunctionUrl` — copy it. This is your `PUBLIC_API_URL`.

Example: `https://abcdef1234.lambda-url.ap-south-1.on.aws`

### Step 6 — GitHub repository secrets

Go to: **repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|-------------|-------|
| `PUBLIC_API_URL` | Lambda Function URL from Step 5 — **no trailing slash** |
| `PROCESSING_CALLBACK_TOKEN` | Same random string you set on Lambda in Step 4 |
| `AWS_ACCESS_KEY_ID` | from Step 2 |
| `AWS_SECRET_ACCESS_KEY` | from Step 2 |

> `PUBLIC_API_URL` being empty is the cause of the `curl: (3) URL rejected` error.
> The workflow now checks for it and fails early with a clear message.

### Step 7 — GitHub PAT (for Lambda to trigger workflows)

1. Go to https://github.com/settings/tokens → **Generate new token (classic)**
2. Scopes needed: **repo** + **workflow**
3. Copy the token → set as `GITHUB_TOKEN` in Lambda env vars (Step 4)

### Step 8 — Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

When prompted (or in the Vercel dashboard → Settings → Environment Variables):

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | Lambda Function URL from Step 5 |

---

## Re-deploying Lambda after code changes

```bash
cd backend

rm -rf package lambda.zip

pip install -r requirements.txt -t ./package \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11

cp -r app handler.py ./package/
cd package && zip -r ../lambda.zip . && cd ..

aws lambda update-function-code \
  --function-name video-platform-api \
  --zip-file fileb://lambda.zip \
  --region YOUR_REGION
```

---

## Environment variable reference

### Backend

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes | `sqlite:///./app.db` | SQLAlchemy URL |
| `SECRET_KEY` | Yes | *(insecure)* | JWT signing key |
| `AWS_ACCESS_KEY_ID` | S3 only | — | |
| `AWS_SECRET_ACCESS_KEY` | S3 only | — | |
| `AWS_REGION` | S3 only | `ap-south-1` | |
| `AWS_S3_BUCKET` | S3 only | — | |
| `GITHUB_TOKEN` | GH Actions only | — | PAT with repo+workflow |
| `GITHUB_REPO` | GH Actions only | — | `owner/repo` |
| `GITHUB_WORKFLOW_ID` | GH Actions only | `process-video.yml` | |
| `PROCESSING_CALLBACK_TOKEN` | Yes | *(insecure)* | Must match GitHub secret |

### Frontend

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | Lambda Function URL |

---

## Troubleshooting

**`curl: (3) URL rejected: Malformed input to a URL function`**
→ `PUBLIC_API_URL` GitHub secret is empty. Add it in repo Settings → Secrets.

**GitHub Actions returns 403 on the callback**
→ `PROCESSING_CALLBACK_TOKEN` secret doesn't match `PROCESSING_CALLBACK_TOKEN` on Lambda. They must be identical.

**Video stuck on `processing` forever**
→ Check the Actions tab in your repo for the `Process Video` run. Look at which step failed. Common causes: FFmpeg OOM (video too large for free runner), S3 permission denied, or the callback URL unreachable.

**Lambda returns 500**
→ Check CloudWatch logs. Most common cause: a missing required env var.

**HLS video won't play**
→ S3 CORS is missing or the bucket policy doesn't allow public GET on `videos/*`. Re-run the S3 setup commands in Step 1.

**`ImportError` on Lambda cold start**
→ You packaged deps for the wrong platform. Re-run `pip install` with `--platform manylinux2014_x86_64 --only-binary=:all:`.
