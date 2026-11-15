# AgriDoc AI — Render Deployment Environment Variables

Copy these values to your Render dashboard for the **agridoc-ai-backend** service.

## Required Environment Variables

```bash
# Authentication
AGRIDOC_API_KEYS=agridoc-5mTNeyBhWqoFRKUQQJvIpgmo64jpGwushGKDTtBKmok
AGRIDOC_DB_KEYS=88PzJhtJUBsfq9lYn4nv9GpRpe-QF9AqKP3215qaixg=

# CORS — MUST include frontend URL
CORS_ALLOWED_ORIGINS=https://agridoc-ai-frontend.onrender.com,http://localhost:3000

# Database (SQLite is fine for free tier)
AGRIDOC_DATABASE_URL=sqlite:///./data/agridoc.db

# API configuration
AGRIDOC_RATE_LIMIT_PER_MIN=60
AGRIDOC_MAX_IMAGE_BYTES=10485760
AGRIDOC_ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp
AGRIDOC_LOG_LEVEL=INFO
```

## Update Steps

1. Go to https://dashboard.render.com
2. Click on **agridoc-ai-backend**
3. Click **"Environment"** tab
4. Add/update each variable above
5. Click **"Manual Deploy"** → select branch `main` → **"Deploy"**
