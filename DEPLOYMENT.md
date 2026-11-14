# AgriDoc AI — Free Deployment Guide

**Deploy AgriDoc AI publicly with $0/month cost. Forever free.**

---

## Zero-Cost Hosting Options

| Provider | Backend | Frontend | Notes |
|----------|---------|----------|-------|
| **Oracle Cloud Always Free** | ✅ VM + Docker | ✅ Netlify | **Recommended** — truly free forever |
| Render.com | ✅ Free tier | ✅ Free | 512MB RAM limit |
| Railway.app | ⚠️ $5 credit | ✅ Free | Credit expires |
| Vercel | ✅ Serverless | ✅ Static | Serverless functions |
| Netlify | ✅ Functions | ✅ Static | Functions on Edge |

---

## Option 1: Vercel (Recommended for Static Frontend)

**Zero-config deployment with global CDN, automatic HTTPS, and serverless functions.**

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Generate Production Secrets

```bash
# Generate API key and Fernet key
python -c "import secrets; from cryptography.fernet import Fernet; print(f'API_KEY=agridoc-{secrets.token_urlsafe(32)}'); print(f'DB_KEY={Fernet.generate_key().decode()}')"
```

Example output:
```
API_KEY=agridoc-YourSecureKeyHere12345
DB_KEY=HV7QA-zwSehXoQqbxjfHwIRSnSjIE410YourKeyHere12345
```

### Step 3: Deploy Frontend (Static Site)

```bash
cd D:/agridoc/frontend
npm install
npm run build
cd ..
vercel
```

During Vercel setup:

1. **Project name**: `agridoc-frontend`
2. **Framework**: Select `React` (auto-detected) or `Other`
3. **Output Directory**: `frontend/dist`
4. **Link to existing project**: No (creates new)

### Step 4: Set Environment Variables on Vercel

**Dashboard → Your Project → Settings → Environment Variables**

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_BACKEND_URL` | `https://your-api.vercel.app/api` | Production |
| `AGRIDOC_API_KEYS` | `agridoc-YourKeyHere` | Production |
| `AGRIDOC_DB_KEYS` | `YourFernetKey` | Production |
| `CORS_ALLOWED_ORIGINS` | `https://your-vercel-frontend.vercel.app` | Production |

### Step 5: Deploy Backend (API Routes)

**Option A: Single Vercel Project (Frontend + Backend)**

Create `api/index.py` in project root:
```python
import sys
sys.path.insert(0, '/var/task/src')
from api.app import app
```

**Option B: Separate Backend Project**

```bash
cd D:/agridoc
vercel
```

During setup:
1. **Project name**: `agridoc-api`
2. **Root Directory**: `./src/api`
3. **Build Command**: (leave empty - no build needed)
4. **Output Directory**: (leave empty)

### Step 6: Test Your Deployment

```bash
# Test frontend (should show AgriDoc UI)
curl -I https://your-vercel-frontend.vercel.app

# Test backend health
curl https://your-api.vercel.app/api/health
```

---

## Option 2: Zero-Docker Manual Deployment (No Docker)

**Get a free VM that never expires:**
- 2 VM instances × 1GB RAM
- 200GB storage
- 10TB bandwidth/month
- Runs forever (not just 12 months)

### Step 1: Create Oracle Account
1. Go to https://www.oracle.com/cloud/free/
2. Create account (requires credit card for identity verification)
3. Verify email and complete setup

### Step 2: Create VM Instance
```
Console → Compute → Instances → Create Instance

Name: agridoc-backend
Image: Ubuntu 22.04 LTS
Shape: VM.Standard.A1.Flex
OCPUs: 1
Memory: 1GB
```

**Configure SSH**: Download `.pem` key file

### Step 3: SSH Into Your VM
```bash
# On your computer (Mac/Linux/WSL)
chmod 400 oracle_key.pem
ssh -i oracle_key.pem ubuntu@YOUR_VM_PUBLIC_IP
```

**On Windows** (PowerShell):
```powershell
ssh -i "oracle_key.pem" ubuntu@YOUR_VM_PUBLIC_IP
```

### Step 4: Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.14
sudo apt install -y python3 python3-pip python3-venv git

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Docker (easier deployment)
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
```

### Step 5: Deploy Backend
```bash
# Create project directory
mkdir -p /home/ubuntu/agridoc
cd /home/ubuntu/agridoc

# Clone your repository (replace with your actual repo)
git clone https://github.com/yourusername/agridoc-ai.git .

# Generate production secrets
python3 -c "import secrets; from cryptography.fernet import Fernet; print(f'AGRIDOC_API_KEYS=agridoc-{secrets.token_urlsafe(32)}'); print(f'AGRIDOC_DB_KEYS={Fernet.generate_key().decode()}')" > .env

# Add to .env
echo "CORS_ALLOWED_ORIGINS=https://yourdomain.netlify.app" >> .env

# Download model (if not in repo)
mkdir -p models/artifacts
# Place agridoc_cv.onnx in this folder

# Create systemd service
sudo tee /etc/systemd/system/agridoc.service << 'EOF'
[Unit]
Description=AgriDoc AI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/agridoc
Environment="PATH=/home/ubuntu/agridoc/agridoc-venv/bin"
ExecStart=/home/ubuntu/agridoc/agridoc-venv/bin/python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create venv and install
python3 -m venv agridoc-venv
source agridoc-venv/bin/activate
pip install -r requirements.txt

# Start service
sudo systemctl daemon-reload
sudo systemctl start agridoc
sudo systemctl enable agridoc
```

### Step 6: Test Backend
```bash
# Check if running
curl http://localhost:8000/health

# Should return: {"status":"ok","model":{...}}
```

### Step 7: Set Up Domain + HTTPS
```bash
# Install Nginx
sudo apt install -y nginx

# Install Certbot (Let's Encrypt SSL)
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 3 * * * /usr/bin/certbot renew --quiet
```

### Step 8: Configure Nginx Reverse Proxy
```bash
sudo tee /etc/nginx/sites-available/agridoc << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/agridoc /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

### Step 9: Deploy Frontend to Vercel (Static Site)

```bash
# Install Vercel CLI
npm install -g vercel

# Build frontend
cd ../frontend
npm install
npm run build
cd ..

# Deploy
vercel
```

During Vercel setup, select:
- Template: **Other** or **React** (auto-detected)
- Root Directory: Leave empty (uses repo root)
- Output Directory: `frontend/dist`
- Build Command: `cd frontend && npm install && npm run build`

**Set environment variables in Vercel Dashboard:**
| Name | Value |
|------|-------|
| `VITE_BACKEND_URL` | `https://your-api.vercel.app/api` |
| `AGRIDOC_API_KEYS` | `agridoc-your-production-key` |
| `AGRIDOC_DB_KEYS` | `YourFernetKey` |
| `CORS_ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` |

---

---

## Option 2: Zero-Docker Manual Deployment (No Docker)

### Step 1: Prepare on Your Computer
```bash
cd D:/agridoc

# Generate production secrets
python -c "import secrets; from cryptography.fernet import Fernet; print(f'AGRIDOC_API_KEYS=agridoc-{secrets.token_urlsafe(32)}'); print(f'AGRIDOC_DB_KEYS={Fernet.generate_key().decode()}')"

# Create .env.production
echo "AGRIDOC_API_KEYS=your-key-here" > .env.production
echo "AGRIDOC_DB_KEYS=your-fernet-key-here" >> .env.production
echo "CORS_ALLOWED_ORIGINS=https://your-netlify-site.netlify.app" >> .env.production
echo "AGRIDOC_DATABASE_URL=sqlite:///./data/agridoc.db" >> .env.production
echo "AGRIDOC_RATE_LIMIT_PER_MIN=300" >> .env.production
echo "AGRIDOC_LOG_LEVEL=INFO" >> .env.production
```

### Step 2: Create Deployment Package
```bash
# Create zip for upload
zip -r agridoc-deploy.zip \
  src/ \
  backend/ \
  configs/ \
  agridoc_db/ \
  models/artifacts/agridoc_cv.onnx \
  data/knowledge/ \
  .env.production
```

### Step 3: Deploy to Free Cloud VM
```bash
# SSH into server
scp -i key.pem agridoc-deploy.zip ubuntu@YOUR_IP:/home/ubuntu/
ssh -i key.pem ubuntu@YOUR_IP

# Extract and set up
unzip agridoc-deploy.zip
python3 -m venv agridoc-venv
source agridoc-venv/bin/activate
pip install -r requirements.txt

# Update .env
mv .env.production .env

# Start with systemd (see Step 5 above)
```

---

## Environment Variables — Required for Production

Create `.env` file (never commit):

```env
# REQUIRED: API key for authentication
AGRIDOC_API_KEYS=agridoc-YourProductionKeyHere12345

# REQUIRED: Database encryption (Fernet)
AGRIDOC_DB_KEYS=HV7QA-zwSehXoQqbxjfHwIRSnSjIE410YourKeyHere12345

# CORS allowed origins (frontend URLs only!)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Database URL (SQLite for small apps, PostgreSQL for production)
AGRIDOC_DATABASE_URL=sqlite:///./data/agridoc.db

# Queue TTL (offline sync retention)
AGRIDOC_QUEUE_TTL_HOURS=72

# Rate limiting
AGRIDOC_RATE_LIMIT_PER_MIN=300

# Logging
AGRIDOC_LOG_LEVEL=INFO
```

---

## Model Files Required

**Place these in `models/artifacts/`:**

1. `agridoc_cv.onnx` — ONNX model (610KB)
2. `meta.json` — Model metadata with SHA-256 hashes
3. `classes.json` — 38 disease class names

---

## Quick Start — Local Development

**Terminal 1 - Backend (port 9998):**
```bash
cd D:/agridoc
.\agridoc-venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 9998
```

**Terminal 2 - Frontend (port 3000):**
```bash
cd D:/agridoc/frontend
npm run dev
```

---

## Monitoring & Health Checks

```bash
# Health check endpoint
curl https://yourdomain.com/health

# Readiness check
curl https://yourdomain.com/ready

# API documentation
curl https://yourdomain.com/docs
```

Expected responses:
```json
// GET /health
{"status":"ok","model":{"model":"agridoc_cv.onnx","size_mb":0.6,"classes":38,"runtime":"onnxruntime","confidence_floor":0.7}}

// GET /ready
{"status":"ready","model":{"model":"agridoc_cv.onnx","size_mb":0.6,"classes":38,"runtime":"onnxruntime","confidence_floor":0.7}}
```

---

## Testing After Deployment

```bash
# Run test suite locally
python -m pytest tests/ -v

# Test health endpoint
curl http://localhost:9998/health

# Test prediction
curl -X POST http://localhost:9998/predict \
  -H "X-API-Key: $(grep AGRIDOC_API_KEYS .env | cut -d= -f2)" \
  -F "file=@test_image.jpg"
```

---

## Troubleshooting

### Backend Won't Start
```bash
# Check if port is in use
netstat -ano | grep :9998

# Kill process
taskkill /PID <pid> /F

# Restart
uvicorn src.api.app:app --port 9998
```

### CORS Errors
```bash
# Check CORS_ALLOWED_ORIGINS in .env
# Must EXACTLY match frontend URL
grep CORS .env
```

### Model Not Loading
```bash
# Verify model exists
ls -la models/artifacts/agridoc_cv.onnx

# Verify venv has dependencies
.\agridoc-venv\Scripts\python.exe -c "import onnxruntime; print('OK')"
```

---

## Security Checklist

Before deploying publicly:

- [ ] Generate strong API keys (don't use defaults)
- [ ] Set CORS to specific domains only (never `*`)
- [ ] Enable database encryption (Fernet keys required)
- [ ] Use HTTPS everywhere (HSTS is set)
- [ ] Enable security headers (CSP, HSTS, X-Frame-Options) - **Already in code**
- [ ] Set rate limiting (default: 300/min per IP)
- [ ] Monitor logs for suspicious activity
- [ ] Keep .env file secure (chmod 600 on Unix)

---

## Cost Breakdown (Real Costs)

| Resource | Oracle Free Tier | Your Cost |
|----------|------------------|-----------|
| VM (1GB RAM) | ✅ Included | **$0** |
| Storage (200GB) | ✅ Included | **$0** |
| Bandwidth (10TB) | ✅ Included | **$0** |
| SSL Certificate | ✅ Let's Encrypt | **$0** |
| Domain | Optional (can use .netlify.app, .vercel.app) | $0-12/year |

**Total: $0/month** (excluding optional domain)

---

## Support

- Check logs: Terminal output from uvicorn
- Health endpoint: https://yourdomain.com/health
- API docs: https://yourdomain.com/docs
- GitHub Issues: github.com/yourusername/agridoc-ai/issues

---

**"Technology should serve the last mile farmer, not just the city consumer."**