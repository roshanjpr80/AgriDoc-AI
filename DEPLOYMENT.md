# AgriDoc AI — Production Deployment Guide

**Deploy AgriDoc AI for real-world public users at $0/month.** This guide covers Render.com (recommended), Oracle Cloud Always Free, and Docker deployments with exact configurations verified against the codebase.

---

## Live Production Deployment

| Service | URL | Status |
|---------|-----|--------|
| **Backend API** | https://agridoc-ai-backend.onrender.com | ✅ Live |
| **API Docs (Swagger)** | https://agridoc-ai-backend.onrender.com/docs | ✅ Live |
| **Frontend PWA** | https://agridoc-ai-frontend.onrender.com | ✅ Live |
| **GitHub Repository** | https://github.com/roshanjpr80/AgriDoc-AI | ✅ Source |

**Test the live API:**
```bash
# Health check (no auth required)
curl https://agridoc-ai-backend.onrender.com/health

# Full prediction (requires API key)
curl -H "X-API-Key: YOUR_KEY" \
  -F "file=@leaf.jpg" \
  https://agridoc-ai-backend.onrender.com/predict
```

---

## Quick Decision Matrix

---

## Quick Decision Matrix

| Need | Recommended Platform |
|------|---------------------|
| Simplest free tier, auto-deploy from GitHub | **Render.com** |
| Full VM control, no time limits | **Oracle Cloud Always Free** |
| Container orchestration, team workflows | **Docker + any cloud** |
| Local development | **uvicorn + Vite** (see below) |

---

## Option 1: Render.com (Recommended — Free Tier)

**Why Render**: Native GitHub integration, auto-deploy on push, free TLS, 512MB RAM, custom domains, zero-config static sites.

### Architecture on Render

```
┌─────────────────────────────────────────────────────────────┐
│                      RENDER.COM                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │  Backend Web Service│    │  Frontend Static Site       │ │
│  │  (FastAPI + ONNX)   │    │  (React 19 PWA, Vite 8)     │ │
│  │  Port: $PORT        │    │  Build: npm run build       │ │
│  │  Auto HTTPS         │    │  Auto HTTPS + CDN           │ │
│  └──────────┬──────────┘    └──────────────┬──────────────┘ │
│             │                              │                │
│             │  Internal network            │                │
│             ▼                              ▼                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Environment Variables                   │   │
│  │  AGRIDOC_API_KEYS, AGRIDOC_DB_KEYS,                 │   │
│  │  CORS_ALLOWED_ORIGINS, AGRIDOC_RATE_LIMIT           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Prepare Repository

Ensure your GitHub repo has this structure at root:

```
your-repo/
├── render.yaml              ← Render Blueprint (optional)
├── requirements.txt         ← Python deps (pinned)
├── src/api/app.py           ← Production entrypoint
├── models/artifacts/
│   ├── agridoc_cv.onnx      ← 610KB model (git-tracked)
│   ├── meta.json
│   └── metadata.json
├── frontend/
│   ├── package.json
│   ├── vite.config.ts       ← Port 3000, proxy /api/* → :9998
│   └── public/              ← PWA icons, manifest
├── backend/config.py        ← Central config (reads AGRIDOC_* env)
├── configs/                 ← YAML configs (data, advice, sync, train)
├── agridoc_db/              ← DB layer (Fernet REQUIRED)
└── .env.example             ← Template (no real secrets)
```

### Step 2: Generate Production Secrets

```bash
# Run locally to generate secure keys
python -c "
import secrets
from cryptography.fernet import Fernet
api_key = 'agridoc-' + secrets.token_urlsafe(32)
db_key = Fernet.generate_key().decode()
print(f'AGRIDOC_API_KEYS={api_key}')
print(f'AGRIDOC_DB_KEYS={db_key}')
"
```

**Save these — you'll need them for both services.**

### Step 3: Deploy Backend (Web Service)

**Via Render Dashboard** (recommended for first time):

1. **New → Web Service** → Connect GitHub repo
2. **Configure**:
   ```
   Name: agridoc-api
   Region: Oregon (US West) or Frankfurt (EU)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
   ```
3. **Environment Variables** (Settings → Environment):
   | Key | Value | Notes |
   |-----|-------|-------|
   | `AGRIDOC_API_KEYS` | `agridoc-xxx...` | From Step 2 |
   | `AGRIDOC_DB_KEYS` | `xxx...` | From Step 2 |
   | `CORS_ALLOWED_ORIGINS` | `https://your-frontend.onrender.com` | Update after frontend deploy |
   | `AGRIDOC_RATE_LIMIT` | `300` | 300 req/min/IP (Render free tier) |
   | `AGRIDOC_LOG_LEVEL` | `INFO` | |
   | `PYTHON_VERSION` | `3.11.9` | Pin version |
4. **Create Web Service** — auto-deploys on push

**Via Blueprint** (`render.yaml` at repo root):
```yaml
services:
  - type: web
    name: agridoc-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: AGRIDOC_API_KEYS
        sync: false
      - key: AGRIDOC_DB_KEYS
        sync: false
      - key: CORS_ALLOWED_ORIGINS
        value: https://agridoc-frontend.onrender.com
      - key: AGRIDOC_RATE_LIMIT
        value: "300"
      - key: PYTHON_VERSION
        value: "3.11.9"
  - type: web
    name: agridoc-frontend
    runtime: static
    plan: free
    buildCommand: cd frontend && npm ci && npm run build
    staticPublishPath: frontend/dist
    envVars:
      - key: VITE_API_BASE
        value: https://agridoc-api.onrender.com
```

### Step 4: Deploy Frontend (Static Site)

1. **New → Static Site** → Same GitHub repo
2. **Configure**:
   ```
   Name: agridoc-frontend
   Branch: main
   Build Command: cd frontend && npm ci && npm run build
   Publish Directory: frontend/dist
   ```
3. **Environment Variables**:
   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE` | `https://agridoc-api.onrender.com` |
4. **Create** — auto-deploys on push

### Step 5: Wire CORS

After both deploy, get frontend URL (e.g., `https://agridoc-frontend.onrender.com`), then:

1. Backend service → Settings → Environment
2. Update `CORS_ALLOWED_ORIGINS` = `https://agridoc-frontend.onrender.com`
3. **Save Changes** → triggers backend redeploy

### Step 6: Custom Domain (Optional)

1. Both services → Settings → Custom Domains
2. Add `api.yourdomain.com` → backend, `yourdomain.com` → frontend
3. Render provisions TLS automatically (Let's Encrypt)
4. Update `CORS_ALLOWED_ORIGINS` to your custom domain

---

## Option 2: Oracle Cloud Always Free (Full VM Control)

**Why Oracle**: 2 AMD VMs (1/8 OCPU, 1GB RAM) + 4 ARM VMs (24GB RAM total), 200GB storage, 10TB bandwidth/month, **never expires**.

### Prerequisites

- Oracle Cloud account (credit card for verification only)
- SSH key pair
- Domain name (optional, can use VM public IP)

### Step 1: Create ARM Instance (Recommended — More Resources)

```
Console → Compute → Instances → Create Instance

Name: agridoc-arm
Image: Ubuntu 22.04 Minimal
Shape: VM.Standard.A1.Flex
OCPUs: 4          (max free tier)
Memory: 24 GB     (max free tier)
Boot Volume: 50 GB
SSH Key: Paste your public key
```

**For AMD fallback** (if ARM unavailable):
```
Shape: VM.Standard.E2.1.Micro
OCPUs: 1/8
Memory: 1 GB
```

### Step 2: SSH & Initial Setup

```bash
# Mac/Linux/WSL
chmod 400 ~/.ssh/oracle_key.pem
ssh -i ~/.ssh/oracle_key.pem ubuntu@YOUR_VM_PUBLIC_IP

# Windows PowerShell
ssh -i "C:\path\oracle_key.pem" ubuntu@YOUR_VM_PUBLIC_IP
```

```bash
# On VM: Update & install basics
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx docker.io docker-compose
```

### Step 3: Install Docker & Compose (Easiest Production Deploy)

```bash
# Docker already installed above, verify
docker --version
docker compose version

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 4: Create docker-compose.yml

```bash
mkdir -p /home/ubuntu/agridoc && cd /home/ubuntu/agridoc
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: agridoc-backend
    restart: unless-stopped
    ports:
      - "9998:9998"
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9998/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    container_name: agridoc-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    container_name: agridoc-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - backend
      - frontend

  certbot:
    image: certbot/certbot
    container_name: agridoc-certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait \$\$!; done'"
EOF
```

### Step 5: Create Dockerfiles

**Dockerfile.backend** (repo root):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for ONNX Runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY src/ ./src/
COPY backend/ ./backend/
COPY configs/ ./configs/
COPY agridoc_db/ ./agridoc_db/
COPY models/ ./models/
COPY data/knowledge/ ./data/knowledge/

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 9998
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "9998"]
```

**Dockerfile.frontend** (frontend/):
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

**frontend/nginx.conf**:
```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:9998/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**nginx.conf** (repo root, for main nginx):
```nginx
events { worker_connections 1024; }

http {
    upstream backend { server backend:9998; }
    upstream frontend { server frontend:3000; }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers (match FastAPI middleware)
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header Referrer-Policy strict-origin-when-cross-origin;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 60s;
        }

        # Health checks (no auth)
        location /health { proxy_pass http://backend/health; }
        location /ready { proxy_pass http://backend/ready; }
    }
}
```

### Step 6: Create .env (Production Secrets)

```bash
cat > .env << 'EOF'
# REQUIRED: Generate fresh keys!
AGRIDOC_API_KEYS=agridoc-your-secure-api-key-here
AGRIDOC_DB_KEYS=your-fernet-key-here

# CORS: Exact frontend domain (no wildcards!)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database (SQLite for simplicity, PostgreSQL for scale)
AGRIDOC_DATABASE_URL=sqlite:///./data/agridoc.db

# Rate limit (higher for production behind nginx)
AGRIDOC_RATE_LIMIT=300

# Logging
AGRIDOC_LOG_LEVEL=INFO

# Queue TTL (offline sync)
AGRIDOC_QUEUE_TTL_HOURS=72
EOF

chmod 600 .env
```

### Step 7: Get SSL Certificate

```bash
# Create directories
mkdir -p certbot/conf certbot/www

# Get initial certificate (replace domain)
docker run --rm -it \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com \
  --email your@email.com --agree-tos --no-eff-email
```

### Step 8: Deploy

```bash
# Clone your repo
git clone https://github.com/yourusername/agridoc-ai.git .
# Copy model files if not in repo
cp /path/to/agridoc_cv.onnx models/artifacts/
cp /path/to/meta.json models/artifacts/
cp /path/to/metadata.json models/artifacts/

# Start stack
docker compose up -d

# Verify
docker compose ps
curl http://localhost/health
curl http://localhost/api/health
```

---

## Option 3: Local Development (Verified Commands)

### Backend (Terminal 1)
```bash
cd D:/agridoc
# Windows
.\agridoc-venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 9998

# Linux/Mac
source agridoc-venv/bin/activate
uvicorn src.api.app:app --host 0.0.0.0 --port 9998
```

### Frontend (Terminal 2)
```bash
cd D:/agridoc/frontend
npm run dev
# Opens http://localhost:3000 (proxies /api/* to :9998)
```

### Test Locally
```bash
# Health (no auth)
curl http://localhost:9998/health

# Predict (requires auth)
API_KEY=$(grep AGRIDOC_API_KEYS .env | cut -d= -f2)
curl -H "X-API-Key: $API_KEY" -F "file=@test.jpg" http://localhost:9998/predict

# Frontend proxy
curl http://localhost:3000/api/health
```

---

## Environment Variables — Complete Reference

All variables read by `backend/config.py` with `AGRIDOC_` prefix:

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `AGRIDOC_API_KEYS` | **YES** | — | Comma-separated API keys (rotation supported) |
| `AGRIDOC_DB_KEYS` | **YES** | — | Comma-separated Fernet keys (MultiFernet, rotation) |
| `CORS_ALLOWED_ORIGINS` | **YES** | — | Exact frontend URLs, comma-separated |
| `AGRIDOC_DATABASE_URL` | No | `sqlite:///./data/agridoc.db` | SQLite or PostgreSQL URL |
| `AGRIDOC_RATE_LIMIT` | No | `60` | Requests/minute per IP |
| `AGRIDOC_QUEUE_TTL_HOURS` | No | `72` | Offline sync retention |
| `AGRIDOC_LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `AGRIDOC_MODEL_PATH` | No | `models/artifacts/agridoc_cv.onnx` | ONNX model path |
| `AGRIDOC_MAX_IMAGE_BYTES` | No | `10485760` | Max upload (10 MiB) |

**Generate keys**:
```bash
# API Key
python -c "import secrets; print('agridoc-' + secrets.token_urlsafe(32))"

# Fernet Key (run twice for rotation)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Model Files (Required in `models/artifacts/`)

| File | Size | Purpose | Source |
|------|------|---------|--------|
| `agridoc_cv.onnx` | 610KB | EfficientNet-B0, 38 classes, opset 18 | Trained / HF `roshanjpr80/agridoc-model` |
| `meta.json` | 2KB | SHA-256 hashes, version | `scripts/download_model.py` |
| `metadata.json` | 2KB | Accuracy, config, parity | Auto-generated on export |

**Auto-download**: If missing, `src/api/inference.py:_ensure_model_available()` downloads from HuggingFace on first request.

---

## Health Checks & Monitoring

### Endpoints (No Auth Required)

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Liveness probe | `{"status":"ok","model":{"model":"agridoc_cv.onnx","size_mb":0.6,"classes":38,"runtime":"onnxruntime","confidence_floor":0.7}}` |
| `GET /ready` | Readiness probe | `{"status":"ready","model":{...}}` |
| `GET /docs` | Swagger UI | HTML |
| `GET /redoc` | ReDoc | HTML |

### Render Health Checks
```yaml
# render.yaml backend service
healthCheckPath: /health
```

### Docker Health Check
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9998/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Nginx Upstream Checks
```nginx
upstream backend {
    server backend:9998 max_fails=3 fail_timeout=30s;
    # Health check via proxy_pass to /health
}
```

---

## Security Checklist (Pre-Production)

- [ ] **Fresh API keys** generated (not from `.env.example`)
- [ ] **Fresh Fernet keys** generated (run key gen twice for rotation)
- [ ] **CORS_ALLOWED_ORIGINS** = exact frontend domains (no `*`, no localhost)
- [ ] **HTTPS everywhere** (HSTS header requires it — Render/Oracle provide auto)
- [ ] **Rate limiting** configured (300/min for production)
- [ ] **Security headers** verified (CSP, HSTS, X-Frame-Options, etc.)
- [ ] **DB encryption** enabled (AGRIDOC_DB_KEYS required — app crashes without)
- [ ] **Model SHA-256** verified against `meta.json`
- [ ] **`.env` file permissions** `chmod 600` (Unix) / restricted ACL (Windows)
- [ ] **Non-root Docker user** (Dockerfile.backend uses `appuser:1000`)
- [ ] **Firewall** only allows 80/443 (and 22 for SSH)

---

## Cost Breakdown (Real $0/Month)

| Resource | Render Free | Oracle Always Free | Your Cost |
|----------|-------------|-------------------|-----------|
| Backend CPU/RAM | 512MB RAM | 24GB RAM (ARM) / 1GB (AMD) | $0 |
| Frontend Hosting | Static Site (CDN) | Nginx on VM | $0 |
| Bandwidth | 100GB/mo | 10TB/mo | $0 |
| Storage | Ephemeral | 200GB block | $0 |
| TLS/SSL | Auto Let's Encrypt | Auto Let's Encrypt | $0 |
| Custom Domain | Optional ($12/yr) | Optional ($12/yr) | $0-12/yr |
| **Total** | | | **$0/month** |

---

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
docker compose logs backend
# or Render: Service → Logs

# Common issues:
# 1. Port already in use
netstat -tulpn | grep :9998
# 2. Missing model
ls -la models/artifacts/agridoc_cv.onnx
# 3. Missing env vars
docker compose exec backend env | grep AGRIDOC
# 4. Python version mismatch
python --version  # Must be 3.11+
```

### CORS Errors
```bash
# Verify CORS_ALLOWED_ORIGINS matches frontend EXACTLY
# Check backend logs for: "CORS_ALLOWED_ORIGINS from env: ..."
# Must include protocol: https://yourdomain.com (not yourdomain.com)
```

### Model Not Loading
```bash
# Verify ONNX Runtime
python -c "import onnxruntime; print(onnxruntime.__version__)"
# Verify model file
file models/artifacts/agridoc_cv.onnx
# Check auto-download (first request may be slow)
curl -H "X-API-Key: $KEY" http://localhost:9998/health
```

### Rate Limiting Behind Proxy
```python
# src/api/app.py:166-181 uses X-Forwarded-For
# Ensure nginx/proxy passes real IP:
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

### Database Errors
```bash
# SQLite: check file permissions
ls -la data/agridoc.db
# PostgreSQL: verify connection string
AGRIDOC_DATABASE_URL=postgresql://user:pass@host:5432/db
# Fernet: must have AGRIDOC_DB_KEYS or app raises ValueError
```

---

## Post-Deployment Verification

```bash
# 1. Health checks
curl https://yourdomain.com/health
curl https://yourdomain.com/ready

# 2. Auth required endpoints (401 without key)
curl https://yourdomain.com/classes
# Should return 401

# 3. Auth works
curl -H "X-API-Key: $YOUR_KEY" https://yourdomain.com/classes
# Should return 38 class names

# 4. Prediction
curl -H "X-API-Key: $YOUR_KEY" \
  -F "file=@test_leaf.jpg" \
  https://yourdomain.com/predict

# 5. Frontend loads
open https://yourdomain.com

# 6. PWA installable
# Chrome DevTools → Application → Manifest → "Installable"

# 7. Offline works
# DevTools → Network → Offline → Take photo → Comes back online → Auto-sync
```

---

## Scaling Beyond Free Tier

| Bottleneck | Solution |
|------------|----------|
| CPU (ONNX inference) | Add GPU instance, use ONNX Runtime CUDA provider |
| Concurrent requests | Horizontal scaling (Redis rate limit, shared DB) |
| Database | PostgreSQL on managed service (Neon, Supabase free tiers) |
| Queue processing | Background worker for `/sync` reconciliation |
| Model updates | Blue-green deploy, A/B testing with feature flags |

---

## Support & Resources

- **Health**: `https://yourdomain.com/health`
- **API Docs**: `https://yourdomain.com/docs`
- **Logs**: Render Dashboard → Logs / `docker compose logs -f`
- **GitHub Issues**: Your repo issues
- **Model Updates**: Retrain → Export ONNX → Replace `models/artifacts/` → Redeploy

---

**Deployed correctly, AgriDoc AI serves real farmers offline-first, in their language, with privacy — at zero cost.**