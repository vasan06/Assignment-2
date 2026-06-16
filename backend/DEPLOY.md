# Backend Deployment (AWS Lambda via Mangum)

## Local Development
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn app.main:app --reload --port 8000
```

## AWS Lambda Deployment

### Option A — Container Image (recommended)
```bash
# Build & push to ECR
aws ecr create-repository --repository-name video-api
docker build -t video-api .
docker tag video-api:latest <account>.dkr.ecr.<region>.amazonaws.com/video-api:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker push <account>.dkr.ecr.<region>.amazonaws.com/video-api:latest

# Deploy Lambda
aws lambda create-function \
  --function-name video-streaming-api \
  --package-type Image \
  --code ImageUri=<account>.dkr.ecr.<region>.amazonaws.com/video-api:latest \
  --role arn:aws:iam::<account>:role/lambda-execution-role \
  --timeout 900 \
  --memory-size 1024
```

### Option B — Zip + Lambda Layer
```bash
pip install -r requirements.txt -t package/
cd package && zip -r ../lambda.zip . && cd ..
zip -g lambda.zip -r app/ handler.py
aws lambda update-function-code --function-name video-streaming-api --zip-file fileb://lambda.zip
```

## Required Lambda Environment Variables
Set these in Lambda console → Configuration → Environment variables:
- DATABASE_URL
- SECRET_KEY
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_REGION
- AWS_S3_BUCKET
- GITHUB_TOKEN
- GITHUB_REPO
- GITHUB_WORKFLOW_ID
- INTERNAL_API_KEY

## Required GitHub Secrets
Set these in your GitHub repo → Settings → Secrets → Actions:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- API_BASE_URL  (e.g. https://your-lambda-url.lambda-url.ap-south-1.on.aws)
- INTERNAL_API_KEY

## S3 Bucket Setup
Enable public read for /videos/ prefix or use presigned URLs.
Recommended CORS policy:
```json
[{
  "AllowedHeaders": ["*"],
  "AllowedMethods": ["GET", "HEAD"],
  "AllowedOrigins": ["https://your-vercel-app.vercel.app"],
  "ExposeHeaders": ["Content-Length"]
}]
```
