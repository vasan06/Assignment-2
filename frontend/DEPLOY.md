# Frontend Deployment (Vercel)

## Local Development
```bash
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL
npm run dev
```

## Deploy to Vercel

### Option A — Vercel CLI
```bash
npm i -g vercel
vercel login
vercel --prod
# Set environment variable when prompted:
#   NEXT_PUBLIC_API_URL = https://your-lambda-url.amazonaws.com
```

### Option B — Vercel Dashboard
1. Import GitHub repo at vercel.com/new
2. Set root directory to `frontend/`
3. Add environment variable:
   - Key: NEXT_PUBLIC_API_URL
   - Value: your backend Lambda/API URL
4. Click Deploy

## Build Settings (auto-detected for Next.js)
- Framework: Next.js
- Build command: `npm run build`
- Output: `.next`
