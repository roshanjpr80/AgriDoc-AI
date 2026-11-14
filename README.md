# AgriDoc AI — Offline Crop Disease Diagnosis for Smallholder Farmers

**AI-powered diagnosis without internet. Free. Works everywhere.**

---

## The Problem We Solve

Smallholder farmers lose **40-60% of crops** to undiagnosed plant diseases because:
- No nearby plant doctors (1 per 50,000 km² in developing regions)
- Expensive expert consultations
- Misdiagnosis leads to wrong treatments (worsening infections)
- Pesticide resistance from over-medicalization

**AgriDoc AI** provides instant, free diagnosis via phone camera, working offline, for farmers who can't afford or access traditional agronomy services.

---

## Quick Start — Get Running in 2 Minutes

```bash
# Terminal 1 - Start Backend (port 9998)
.\agridoc-venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 9998

# Terminal 2 - Start Frontend (port 3000)
cd frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

---

## What AgriDoc AI Does

| Feature | How It Helps Farmers |
|---------|---------------------|
| **Instant diagnosis** | Point camera at sick plant → get disease name in 2 seconds |
| **Offline-first** | Works without internet after first load |
| **Free treatment advice** | Step-by-step remedies in 10 Indian languages |
| **Expert consultation** | When unsure, connect to real plant doctors |
| **Privacy protected** | Photos never leave device; GPS/EXIF stripped |

---

## Technology Stack

### Backend (Port 9998)
- **Framework**: FastAPI 0.162 — async, auto-Docs, production-grade
- **Runtime**: ONNX Runtime 1.31 (CPU-only, 610KB model)
- **Security**: API key auth, rate limiting (60 req/min/IP), CSP/HSTS headers
- **Endpoints**: 12 total (`/health`, `/predict`, `/advice`, `/rag`, `/sync`, etc.)

### Frontend (Port 3000)
- **Framework**: React 19 + Vite 8 — modern SPA, fast HMR
- **PWA**: Works offline, installable, no app store needed
- **Inference**: ONNX Runtime Web + WebGL acceleration in browser
- **Languages**: JavaScript/TypeScript, Tailwind CSS

### Model
- **Architecture**: EfficientNet-B0 (224×224 input)
- **Classes**: 38 crop diseases (Apple, Corn, Tomato, etc.)
- **Accuracy**: 98.82% top-1 on PlantVillage test set
- **Size**: 610KB - tiny enough for phone storage

---

## API Endpoints

All endpoints require **`X-API-Key`** header (get from `.env`):

```bash
# Health check (no auth required)
curl http://localhost:9998/health

# Get all disease classes
curl http://localhost:9998/classes -H "X-API-Key: $(grep AGRIDOC_API_KEYS .env | cut -d= -f2)"

# Diagnose from image
curl -X POST http://localhost:9998/predict \
  -H "X-API-Key: ..." \
  -F "file=@leaf.jpg"

# Get treatment advice
curl -X POST http://localhost:9998/advice \
  -H "X-API-Key: ..." \
  -d "class_label=Tomato_Leaf_Mold&lang=en"

# Full AgriPulse workflow (diagnose → advise → market → weather)
curl -X POST http://localhost:9998/agripulse \
  -H "X-API-Key: ..." \
  -F "file=@leaf.jpg"
```

### All Endpoints Overview

| Method | Path | Auth? | Purpose |
|--------|------|-------|---------|
| GET | `/health` | ❌ | Liveness check (model info) |
| GET | `/ready` | ❌ | Readiness probe |
| GET | `/docs` | ❌ | Swagger API documentation |
| GET | `/classes` | ✅ | Disease class list |
| POST | `/predict` | ✅ | Image → diagnosis |
| POST | `/advice` | ✅ | Treatment advice |
| POST | `/rag` | ✅ | Free-text Q&A |
| POST | `/agripulse` | ✅ | Full workflow |
| POST | `/sync` | ✅ | Offline reconciliation |
| POST | `/feedback` | ✅ | Correction submission |
| DELETE | `/data` | ✅ | Delete my data |

---

## Deployment — Free Public Hosting

**Zero cost deployment guide**: `DEPLOYMENT.md`

### Option 1: Oracle Cloud Always Free (Recommended)
- 2 VM instances × 1GB RAM
- 200GB storage, 10TB bandwidth/month
- Runs forever free

### Option 2: Render.com
- Free tier for backend API
- Free custom domains

### Option 2: Vercel (Recommended for Static Frontend)
- Free Serverless Functions for backend API
- Free Static Site Hosting for frontend
- Global CDN, automatic HTTPS
- Drag-and-drop or CLI deployment

#### Quick Vercel Deployment:
```bash
# Install Vercel CLI
npm install -g vercel

# Generate production secrets first
python -c "import secrets; from cryptography.fernet import Fernet; print(f'API_KEY=agridoc-{secrets.token_urlsafe(32)}'); print(f'DB_KEY={Fernet.generate_key().decode()}')"

# Build frontend
cd frontend && npm install && npm run build

# Deploy frontend (from project root)
vercel

# Deploy backend (if needed as API routes)
# See DEPLOYMENT.md for full Vercel setup
```

### Quick Deploy Command:
```bash
# Generate production secrets first
python scripts/generate_secrets.sh

# Or use one-liner
python -c "import secrets; from cryptography.fernet import Fernet; print(f'API_KEY=agridoc-{secrets.token_urlsafe(32)}'); print(f'DB_KEY={Fernet.generate_key().decode()}')"
```

---

## Configuration

### Environment Variables (`.env`)

```env
# REQUIRED: API key for authentication
AGRIDOC_API_KEYS=agridoc-YourKeyHere

# REQUIRED: Database encryption (Fernet)
AGRIDOC_DB_KEYS=YourFernetKeyHere

# CORS allowed origins (frontend domains)
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Rate limit (requests per minute per IP)
AGRIDOC_RATE_LIMIT_PER_MIN=60

# Model settings (from configs/)
AGRIDOC_CONFIDENCE_FLOOR=0.70
AGRIDOC_TOP_K=3
AGRIDOC_MAX_IMAGE_BYTES=10485760
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Test count: 32 tests passing
# Coverage: API endpoints, advice engine, LangGraph agents, sync queue
```

---

## Security — Farmer-Protected

| Protection | Implementation |
|------------|----------------|
| **API Authentication** | Required on every endpoint except health checks |
| **Rate Limiting** | 60 requests/minute per IP |
| **Data Encryption** | Fernet encryption for stored data |
| **Privacy** | GPS/EXIF stripped from uploaded images |
| **CORS** | Allowlist only (never `*`) |
| **Headers** | CSP, HSTS, X-Frame-Options, X-Content-Type-Options |
| **Data Deletion** | `DELETE /data` removes all user data |

---

## The Full Story — How It Works

```
┌─────────────────┐
│  Farmer takes   │
│  photo of sick  │
│  leaf           │
└─────────────────┘
         ↓
┌─────────────────┐
│  Browser sends  │
│  image to /     │
│  predict       │
└─────────────────┘
         ↓
┌─────────────────┐
│  ONNX Runtime   │
│  EfficientNet   │
│  predicts       │
│  38 classes     │
└─────────────────┘
         ↓
┌─────────────────┐
│  Returns:       │
│  - Disease name │
│  - Confidence   │
│  - Grad-CAM     │
│    overlay      │
└─────────────────┘
         ↓
┌─────────────────┐
│  Farmer gets    │
│  instant        │
│  diagnosis      │
└─────────────────┘
         ↓
┌─────────────────┐
│  Advice engine  │
│  provides       │
│  treatment      │
│  (grounded KB)  │
└─────────────────┘
```

---

## Multilingual Support

| Language | Code |
|----------|------|
| English | en |
| Hindi | hi |
| Bengali | bn |
| Tamil | ta |
| Telugu | te |
| Marathi | mr |
| Gujarati | gu |
| Malayalam | ml |
| Kannada | kn |
| Punjabi | pa |

---

## Project Structure

```
D:/agridoc/
├── AUDIT.md              ← Security and readiness audit
├── DEPLOYMENT.md         ← Free deployment guide
├── README.md             ← This file
├── requirements.txt      ← Python dependencies
├── .env.example          ← Environment template
│
├── models/artifacts/
│   └── agridoc_cv.onnx   ← Trained ONNX model (610KB)
│
├── data/
│   ├── plantvillage/     ← Training images (~38K color)
│   ├── splits/
│   │   └── classes.json  ← 38 disease classes
│   └── knowledge/
│       ├── advisory_rules.json
│       └── translations.json
│
├── src/
│   ├── api/app.py        ← Production FastAPI (12 endpoints)
│   ├── inference.py      ← ONNX prediction wrapper
│   ├── agents/           ← LangGraph 5-agent workflow
│   ├── advice/           ← Grounded KB advice engine
│   ├── sync/             ← Offline queue (JSONL)
│   └── vision/           ← Image preprocessing, Grad-CAM
│
├── backend/              ← Minimal model utilities
├── configs/              ← YAML hyperparameter configs
├── frontend/             ← React 19 + Vite PWA
└── tests/                ← pytest suite (32 tests)
```

---

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

**Code standards**: Follow existing patterns. All imports are covered by dependencies in `requirements.txt`.

---

## License

MIT — Free for farmers everywhere.

---

## Contact

- GitHub Issues: [github.com/yourusername/agridoc-ai/issues](https://github.com/yourusername/agridoc-ai/issues)
- Documentation: `DEPLOYMENT.md` for free hosting guide

---

**"Technology should serve the last mile farmer, not just the city consumer."**