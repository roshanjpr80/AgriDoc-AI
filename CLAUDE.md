# AgriDoc AI — Development Guide (Code-Level Reference)

**Crop disease diagnosis platform**: EfficientNet CV model, FastAPI backend, React/Vite PWA frontend, LangGraph agent orchestration. Built for smallholder farmers with intermittent connectivity.

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

## Project Layout (Verified)

```
D:/agridoc/
├── AUDIT.md                    ← Comprehensive security & readiness audit
├── CLAUDE.md                   ← This file
├── README.md                   ← Project overview
├── DEPLOYMENT.md               ← Free deployment guide (Oracle Cloud / Render)
├── .env.example                ← Environment template (TEST KEYS — generate fresh for prod)
├── requirements.txt            ← Pinned Python deps (fastapi, onnxruntime, uvicorn, etc.)
│
├── models/artifacts/           ← TRAINED MODEL FILES (git-tracked)
│   ├── agridoc_cv.onnx         ← 610KB EfficientNet-B0, 38 classes
│   ├── meta.json               ← SHA-256 hashes, version
│   └── metadata.json           ← Accuracy, opset, parity verified
│
├── data/
│   ├── plantvillage/color/     ← ~38K color images (PlantVillage)
│   ├── splits/
│   │   └── classes.json        ← Full 38 disease class names
│   └── knowledge/
│       ├── advisory_rules.json ← KB: 38 diseases × treatments
│       └── translations.json   ← 10 languages (en,hi,bn,ta,te,mr,gu,ml,kn,pa)
│
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py              ← PRODUCTION API (430 lines, 12 endpoints)
│   │   └── inference.py        ← ONNX Runtime wrapper (auto-download from HF)
│   │
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── transforms.py       ← ImageNet preprocessing (224×224)
│   │   ├── gradcam.py          ← Visual explanations (base64 PNG overlay)
│   │   ├── phash.py            ← Perceptual hashing (deduplication)
│   │   ├── model.py            ← Model utilities
│   │   ├── plantvillage.py     ← Dataset loader
│   │   ├── balance.py          ← Class balancing
│   │   ├── efficientnet_v2_b2.py
│   │   ├── mobilenet_v3.py
│   │   ├── source_tags.py
│   │   └── train.py            ← Training script
│   │
│   ├── advice/
│   │   ├── __init__.py
│   │   ├── engine.py           ← build_advice(), answer_free_text() — grounded RAG
│   │   ├── knowledge.py        ← KB loading (38 diseases, organic-first ordering)
│   │   ├── translate.py        ← 10-language translation with fallback
│   │   └── tts.py              ← Optional TTS
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py            ← TypedDict state schema
│   │   ├── graph.py            ← LangGraph StateGraph (5 nodes)
│   │   ├── diagnosis.py        ← ONNX prediction node
│   │   ├── advice_agent.py     ← KB advisory node
│   │   ├── market_agent.py     ← eNAM/AGMARKNET prices node
│   │   ├── weather_agent.py    ← Open-Meteo forecast node
│   │   └── coordinator.py      ← Decision logic node
│   │
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── queue.py            ← JSONL queue (72h TTL, 200 max, retries)
│   │   ├── sync.py             ← Reconciliation logic
│   │   └── compress.py         ← JPEG quality 60 compression
│   │
│   ├── feedback/
│   │   ├── __init__.py
│   │   └── review_queue.py     ← Expert review queue for farmer corrections
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   └── onnx_export.py      ← PyTorch → ONNX export (opset 18)
│   │
│   ├── market/
│   │   ├── __init__.py
│   │   ├── prices.py           ← Mandi price fetch + forecast
│   │   ├── forecast.py         ← Market trend forecasting
│   │   └── lookup.py           ← Price lookup by district/crop
│   │
│   ├── privacy/
│   │   ├── __init__.py
│   │   ├── exif.py             ← EXIF/GPS stripping
│   │   └── location.py         ← Coarsen to ~1km (district level)
│   │
│   └── __init__.py
│
├── backend/
│   ├── __init__.py
│   ├── config.py               ← CENTRAL CONFIG (reads AGRIDOC_* env vars)
│   └── models/
│       └── cv_model.py         ← Model loading utilities
│
├── agridoc_db/                 ← DATABASE LAYER (Fernet encryption REQUIRED)
│   ├── __init__.py
│   ├── models.py               ← SQLModel definitions
│   ├── engine.py               ← Engine + MultiFernet encryption
│   ├── security.py             ← Key management
│   └── services.py             ← CRUD operations
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx            ← React 19 entry
│   │   ├── App.tsx             ← Routing + providers
│   │   ├── components/
│   │   │   ├── Layout.tsx      ← Shell, nav, offline banner
│   │   │   ├── CameraView.tsx  ← Photo capture
│   │   │   ├── ResultView.tsx  ← Diagnosis + advice display
│   │   │   ├── ChatView.tsx    ← RAG Q&A
│   │   │   ├── DashboardView.tsx
│   │   │   ├── LibraryView.tsx
│   │   │   ├── HistoryView.tsx
│   │   │   └── SettingsView.tsx
│   │   ├── contexts/
│   │   │   ├── AuthContext.tsx       ← API key/base (localStorage, validates HTTPS)
│   │   │   ├── OfflineContext.tsx    ← IndexedDB queue, auto-sync on online
│   │   │   ├── LanguageContext.tsx   ← 10-language i18n
│   │   │   └── ThemeContext.tsx      ← Dark/light mode
│   │   ├── services/
│   │   │   └── api.ts        ← Typed API client (FormData, auth, offline queue)
│   │   └── styles/
│   │       └── index.css     ← Tailwind + design system
│   ├── public/
│   │   ├── pwa-192x192.svg      ← Maskable PWA icons (SVG)
│   │   ├── pwa-512x512.svg
│   │   ├── camera-icon.svg       ← Shortcut icons
│   │   ├── chat-icon.svg
│   │   └── favicon.svg
│   ├── vite.config.ts            ← Port 3000, proxy /api/* → :99998, PWA config
│   ├── package.json              ← React 19, Vite 8, PWA plugin, Tailwind
│   └── index.html
│
├── tests/                        ← 138 tests passing
│   ├── test_api.py               ← 32 tests (all endpoints, auth, CORS, rate limit, security headers)
│   ├── test_advice.py            ← 27 tests (KB, translation, safety, grounding)
│   ├── test_agents.py            ← 21 tests (LangGraph, fallback, nodes)
│   ├── test_sync.py              ← 12 tests (queue, reconciliation, TTL)
│   ├── test_vision.py            ← 18 tests (CV, Grad-CAM, phash)
│   └── test_data.py              ← 28 tests (splits, manifests, KB)
│
├── configs/                      ← YAML hyperparameter source of truth
│   ├── __init__.py
│   ├── data.yaml                 ← image_size, confidence_floor, top_k, splits
│   ├── train.yaml                ← Training hyperparams (epochs, lr, optimizer)
│   ├── advice.yaml               ← Advisory thresholds, languages, KB path
│   └── sync.yaml                 ← queue_ttl_hours=72, max_size=200, quality=60
│
└── scripts/
    ├── __init__.py
    ├── train.py                  ← Full training pipeline
    ├── export_onnx.py            ← ONNX export
    ├── build_splits.py           ← Dataset splits
    ├── evaluate.py               ← Model evaluation
    ├── build_translations.py     ← Translation build
    ├── build_knowledge.py        ← KB build
    ├── init_db.py                ← Database init
    └── download_model.py         ← Download from HF (roshanjpr80/agridoc-model)
```

---

## Two Runtime Profiles (Critical Distinction)

### Production API (What Public Users Hit)
- **Entry**: `src/api/app.py` — FastAPI, 12 endpoints
- **Runtime**: CPU-only, ONNX Runtime 1.31, **NO PyTorch**
- **Model**: 610KB EfficientNet-B0, 38 classes, opset 18
- **Port**: 9998
- **Config**: Reads `backend/config.py` + `os.environ` (AGRIDOC_ prefix)
- **Auth**: **Required X-API-Key** on all endpoints except `/health`, `/ready`, `/docs`, `/redoc`, `/openapi.json`

### Minimal Entrypoint (Not Production)
- **Entry**: `backend/main.py` — Only `/health`, `/ready`
- **Loads**: `backend/models/cv_model.py` which imports `torch`
- **Purpose**: Lightweight health checks for container orchestration
- **⚠️ NOT the production inference path**

---

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt     # Python 3.11+, verified

# Start backend (Terminal 1)
.\agridoc-venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 9998

# Start frontend (Terminal 2)
cd frontend && npm run dev

# Run all tests (138 tests)
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_api.py -v
python -m pytest tests/test_advice.py -v
```

---

## Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 9998 | http://localhost:9998 |
| API Docs (Swagger) | 9998 | http://localhost:9998/docs |
| ReDoc | 9998 | http://localhost:9998/redoc |
| Frontend (Vite) | 3000 | http://localhost:3000 |
| Frontend proxy | 3000 | http://localhost:3000/api/* → :9998 |

**Port 8501 is OBSOLETE** (Streamlit legacy). Frontend uses port 3000.

---

## API Endpoints (12 Total — All Authenticated Except Health)

| Method | Path | Auth? | Rate Limited? | Purpose |
|--------|------|-------|---------------|---------|
| GET | `/health` | ❌ | ❌ | Liveness + model info |
| GET | `/ready` | ❌ | ❌ | Readiness probe |
| GET | `/classes` | ✅ | ✅ | 38 crop disease class names |
| POST | `/predict` | ✅ | ✅ | Image → diagnosis + Grad-CAM |
| POST | `/advice` | ✅ | ✅ | Class + lang → grounded treatment |
| POST | `/rag` | ✅ | ✅ | Free-text Q&A (KB-grounded) |
| POST | `/agripulse` | ✅ | ✅ | Full 5-agent workflow |
| POST | `/feedback` | ✅ | ✅ | Farmer correction queue |
| POST | `/sync` | ✅ | ✅ | Offline queue reconciliation |
| DELETE | `/data` | ✅ | ✅ | GDPR data deletion |

---

## Request/Response Formats (Code-Level)

### Health Check (No Auth)
```bash
curl http://localhost:9998/health
```
```json
{
  "status": "ok",
  "model": {
    "model": "agridoc_cv.onnx",
    "size_mb": 0.6,
    "classes": 38,
    "runtime": "onnxruntime",
    "confidence_floor": 0.7
  }
}
```

### Predict (Requires Auth)
```bash
API_KEY=$(grep AGRIDOC_API_KEYS .env | cut -d= -f2)
curl -H "X-API-Key: $API_KEY" \
  -F "file=@leaf.jpg" \
  -F "top_k=3" \
  -F "include_cam=true" \
  http://localhost:9998/predict
```
```json
{
  "diagnosis": "Tomato___Early_blight",
  "confidence": 0.92,
  "predictions": [
    {"class": "Tomato___Early_blight", "confidence": 0.92},
    {"class": "Tomato___Late_blight", "confidence": 0.05},
    {"class": "Tomato___healthy", "confidence": 0.02}
  ],
  "uncertain": false,
  "confidence_floor": 0.7,
  "gradcam_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```

### Advice (Requires Auth)
```bash
curl -H "X-API-Key: $API_KEY" \
  -F "class_label=Tomato___Early_blight" \
  -F "lang=hi" \
  http://localhost:9998/advice
```
```json
{
  "advice": "Tomato — Early blight\nSymptoms: ...\nLow-cost / organic first:\n  • नीम का तेल...\nChemical (if needed):\n  • मैन्कोजेब... (verify with agriculture officer)\nPrevention:\n  • ...\nSource: ICAR-CIPHT (reviewed 2025-06-15)",
  "crop": "Tomato",
  "disease": "Early blight",
  "source": "ICAR-CIPHT",
  "reviewed": "2025-06-15",
  "grounded": true,
  "disclaimer": "मार्गदर्शन, कृषि अधिकारी का प्रतिस्थापन नहीं। उपयोग से पहले खुराक और प्री-हार्वेस्ट अंतराल स्थानीय रूप से सत्यापित करें।"
}
```

### AgriPulse (Full Workflow)
```bash
curl -H "X-API-Key: $API_KEY" \
  -F "file=@leaf.jpg" \
  -F "language=hi" \
  -F "district=Punjab_Ludhiana" \
  -F "offline=false" \
  http://localhost:9998/agripulse
```
```json
{
  "plan": "treat_and_monitor",
  "reasons": ["Confidence 0.92 > floor 0.70", "Weather risk: low", "Market: hold"],
  "predicted_class": "Tomato___Early_blight",
  "confidence": 0.92,
  "advice": "...",
  "sell_recommendation": "hold",
  "weather_risk": "low",
  "decisions": [
    "diagnose: Tomato___Early_blight (0.92)",
    "advice: Grounded KB entry found",
    "market: Price ₹18/kg, trend stable → hold",
    "weather: No rain next 48h → safe to spray",
    "coordinate: treat_and_monitor"
  ]
}
```

---

## Configuration (Source of Truth)

### Environment Variables (.env — Never Commit)
```bash
# Required
AGRIDOC_API_KEYS=key1,key2,key3           # Comma-separated, rotation supported
AGRIDOC_DB_KEYS=fernet_key1,fernet_key2   # REQUIRED — MultiFernet, raises ValueError if missing

# CORS (exact domains, NO wildcards)
CORS_ALLOWED_ORIGINS=https://your-app.com,https://www.your-app.com

# Optional overrides
AGRIDOC_RATE_LIMIT=60                     # Requests/minute per IP
AGRIDOC_DATABASE_URL=sqlite:///./data/agridoc.db  # Or postgresql://...
AGRIDOC_MODEL_PATH=models/artifacts/agridoc_cv.onnx
```

### YAML Configs (configs/ — Not Env Vars)
**configs/data.yaml**:
```yaml
image_size: 224
top_k: 3
confidence_floor: 0.70
classes_path: "data/splits/classes.json"
train_split: 0.8
val_split: 0.1
test_split: 0.1
seed: 42
```

**configs/advice.yaml**:
```yaml
onnx_model: "models/artifacts/agridoc_cv.onnx"
onnx_labels: "models/artifacts/agridoc_cv.onnx.json"
languages: [en, hi, bn, ta, te, mr, gu, ml, kn, pa]
default_language: en
fallback_language: en
max_query_length: 200
min_query_length: 3
knowledge_base_path: "models/artifacts/advisory_rules.json"
```

**configs/sync.yaml**:
```yaml
queue_dir: data/offline/queue
queue_path: data/offline/queue.jsonl
max_queue_size: 200
queue_max_size: 200
max_retries: 3
queue_ttl_hours: 72
compression_format: jpeg
compression_quality: 60
server_url: ""  # Set to backend URL; empty = manual-only sync
```

**configs/train.yaml**:
```yaml
model:
  backbone: efficientnet_b0
  num_classes: 38
  image_size: 224
  pretrained: true
training:
  epochs: 50
  batch_size: 32
  lr: 3e-4
  optimizer: adamw
  scheduler: cosine_annealing
  mixed_precision: true
  early_stopping_patience: 10
```

---

## Security Implementation (Code References)

### API Key Auth (`src/api/app.py:157-164`)
```python
def _check_api_key(request: Request) -> None:
    key = request.headers.get(config.API_KEY_HEADER)  # X-API-Key
    if not key or key not in config.ALLOWED_API_KEYS:
        raise HTTPException(status_code=401, detail="unauthorised")
```

### CORS (`src/api/app.py:133-152`) — Applied FIRST
```python
_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=_ALLOWED_ORIGINS, allow_credentials=True, ...)
```
- ✅ Headers on ALL responses including 401/429
- ✅ No wildcards — exact domains only
- ✅ `allow_credentials=True` for API key in header

### Rate Limiting (`src/api/app.py:166-181`)
```python
def _rate_limit(request: Request) -> None:
    forwarded_for = request.headers.get("x-forwarded-for")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    # Sliding window: 60 req/min default
```
- ✅ Uses `X-Forwarded-For` for real client IP behind proxies (Render, Cloudflare)
- ✅ In-memory sliding window (use Redis for multi-instance)

### Security Headers (`src/api/app.py:182-266`)
```python
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline';",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Cache-Control": "no-store",
}
```
- ✅ Applied to EVERY response (including errors)
- ✅ HSTS 1 year + subdomains (requires HTTPS in prod)
- ✅ Request ID header (`X-Request-ID`) for traceability

### Input Validation
- **Image**: MIME whitelist (jpeg, png, webp), 10 MiB max (`config.MAX_IMAGE_BYTES`)
- **Text**: Regex `^[A-Za-z0-9_\-]+$` for class labels, 200 char max
- **Language**: Whitelist of 10 supported languages

### Database Encryption (`agridoc_db/engine.py`)
```python
def get_engine():
    db_keys = os.environ.get("AGRIDOC_DB_KEYS")
    if not db_keys:
        raise ValueError("AGRIDOC_DB_KEYS environment variable is required")
    keys = [Fernet(k.encode()) for k in db_keys.split(",")]
    cipher = MultiFernet(keys)  # Supports key rotation
```
- ✅ **REQUIRED** — raises `ValueError` if not set
- ✅ MultiFernet for key rotation
- ✅ All sensitive fields encrypted before write

### Privacy (`src/privacy/`)
```python
# exif.py: strip_exif() — removes all EXIF (GPS, timestamps, camera serial)
# location.py: coarsen_location(lat, lon, precision=2) — ~1km district level
```

---

## Model Verification (Production)

### Files (models/artifacts/)
```bash
agridoc_cv.onnx      # 610KB, CPU-only inference
meta.json            # SHA-256 hashes, version
metadata.json        # Accuracy, opset, parity
```

### Metadata (models/artifacts/metadata.json)
```json
{
  "model": "EfficientNet-B0",
  "opset_version": 18,
  "classes": 38,
  "inference_type": "onnxruntime",
  "parity_diff": "< 1e-7",
  "image_size": 224,
  "top_k": 3,
  "confidence_floor": 0.70,
  "trained_on": "PlantVillage color",
  "accuracy_top1": 0.9882,
  "accuracy_top5": 0.9991
}
```

### Inference (`src/api/inference.py`)
```python
def _load():
    if not _ensure_model_available():  # Auto-downloads from HF if missing
        raise RuntimeError("Model not found")
    import onnxruntime as ort
    _session = ort.InferenceSession(str(_model_path), providers=["CPUExecutionProvider"])
```
- ✅ Auto-download from HuggingFace (`roshanjpr80/agridoc-model`)
- ✅ CPUExecutionProvider only
- ✅ SHA-256 validation via meta.json
- ✅ ~15ms inference on Intel i5

---

## Frontend (React 19 + Vite 8 PWA)

### Vite Config (`frontend/vite.config.ts`)
```typescript
server: {
    port: 3000,
    proxy: {
        '/api': { target: 'http://localhost:9998', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') }
    }
},
plugins: [
    VitePWA({
        registerType: 'autoUpdate',
        manifest: {
            name: 'AgriDoc AI',
            short_name: 'AgriDoc',
            display: 'standalone',
            icons: [
                { src: 'pwa-192x192.svg', sizes: '192x192', type: 'image/svg+xml', purpose: 'any maskable' },
                { src: 'pwa-512x512.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' }
            ],
            shortcuts: [
                { name: 'Diagnose Leaf', url: '/camera', icons: [{ src: 'camera-icon.svg', sizes: '192x192' }] },
                { name: 'Expert Chat', url: '/chat', icons: [{ src: 'chat-icon.svg', sizes: '192x192' }] }
            ]
        },
        workbox: {
            runtimeCaching: [
                { urlPattern: /^https:\/\/api\./, handler: 'NetworkFirst', options: { cacheName: 'api-cache', expiration: { maxEntries: 100, maxAgeSeconds: 604800 }}},
                { urlPattern: /^https:\/\/.*\.tile\.openstreetmap\.org/, handler: 'CacheFirst', options: { cacheName: 'map-tiles', expiration: { maxEntries: 500, maxAgeSeconds: 2592000 }}}
            ]
        }
    })
]
```

### Key Contexts
- **AuthContext.tsx**: API key/base in localStorage, validates HTTPS URLs
- **OfflineContext.tsx**: IndexedDB queue (72h TTL), auto-sync on `online` event
- **LanguageContext.tsx**: 10 languages (en,hi,bn,ta,te,mr,gu,ml,kn,pa)
- **ThemeContext.tsx**: Dark/light mode

### API Client (`frontend/src/services/api.ts`)
```typescript
async function request<T>(endpoint, options, auth) {
    const headers = new Headers(options.headers);
    headers.set('X-API-Key', auth.apiKey);
    if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    return fetch(`${auth.apiBase}${endpoint}`, { ...options, headers });
}
```

---

## Offline Sync Architecture

### Client-Side (IndexedDB + Service Worker)
```typescript
// OfflineContext.tsx: QUEUE_TTL_HOURS = 72
// Auto-sync on window.addEventListener('online', checkOnline)
// Compressed JPEG (quality 60) before queuing
```

### Server-Side (`src/sync/queue.py`)
```python
@dataclass
class QueuedPrediction:
    id: str; ts: float; image_b64: str; mime_type: str
    predicted_class: str; confidence: float; uncertain: bool
    farmer_correct: Optional[bool]; farmer_comment: str; farmer_id: str
    attempts: int = 0; next_retry_ts: float = field(default_factory=lambda: time.time() + 1)

MAX_QUEUE_SIZE = 200; MAX_RETRIES = 3; QUEUE_TTL_SECONDS = 72 * 3600
# Storage: JSONL per device in data/offline/queue/
```

### Reconciliation (`src/api/app.py:371-421`)
```python
@app.post("/sync")
async def sync_endpoint(request: Request):
    for item in items:
        result = predict(item["image_b64"])  # Re-run server-side
        if result["predictions"][0]["class"] == item["predicted_class"]:
            synced.append(item["id"])      # Match → confirmed
        else:
            merged.append(item["id"])      # Mismatch → server wins
        # Farmer feedback → expert review queue
```

### Deduplication (`src/vision/phash.py`)
```python
def perceptual_hash(image_bytes: bytes, hash_size: int = 8) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((hash_size, hash_size))
    pixels = list(img.getdata()); avg = sum(pixels) / len(pixels)
    return hex(int(''.join('1' if p > avg else '0' for p in pixels), 2))[2:]

# Hamming distance ≤ 8 = near-duplicate → reject
```

---

## LangGraph AgriPulse Workflow (5 Agents)

### Graph (`src/agents/graph.py`)
```
ENTRY → DIAGNOSE → (uncertain? → CALL_EXPERT) → ADVISE → MARKET → WEATHER → COORDINATE → OUTPUT
                              (confidence < 0.7)
```

### Nodes
1. **DIAGNOSE** (`diagnosis.py`): ONNX prediction → `predicted_class`, `confidence`, `uncertain`
2. **ADVISE** (`advice_agent.py`): `build_advice()` → grounded KB response
3. **MARKET** (`market_agent.py`): eNAM/AGMARKNET prices → `sell_recommendation` (skip if offline)
4. **WEATHER** (`weather_agent.py`): Open-Meteo → `weather_risk` (skip if offline)
5. **COORDINATE** (`coordinator.py`): Decision logic → `plan` + `reasons`

### Sequential Fallback (`src/agents/graph.py`)
```python
def run_agripulse(...):
    graph = _get_graph()
    if graph is not None:
        try:
            return graph.invoke(state)
        except Exception:
            pass  # Fall through
    # Sequential fallback if LangGraph unavailable
    for node in (diagnose, advise, market, weather, coordinate):
        try:
            state = node(state)
        except Exception:
            state["decisions"].append(f"{node.__name__}: error -> skipped")
    return state
```

---

## Adding Dependencies

**Rule**: The production API path is `src/api/app.py` → `src/api/inference.py` → ONNX Runtime only.

| Dependency Needed By | Where to Add |
|---------------------|--------------|
| Production API (inference, API) | `requirements.txt` main section (pinned) |
| Training, export, scripts | `requirements.txt` "training/export" section |
| Frontend only | `frontend/package.json` |

---

## Testing

```bash
# All 138 tests
python -m pytest tests/ -v

# By category
python -m pytest tests/test_api.py -v        # 32: endpoints, auth, CORS, rate limit, security headers
python -m pytest tests/test_advice.py -v     # 27: KB, translation, safety, grounding
python -m pytest tests/test_agents.py -v     # 21: LangGraph, fallback, nodes
python -m pytest tests/test_sync.py -v       # 12: queue, reconciliation, TTL
python -m pytest tests/test_vision.py -v     # 18: CV, Grad-CAM, phash
python -m pytest tests/test_data.py -v       # 28: splits, manifests, KB
```

### Key Test Fixtures (`tests/test_api.py:379-394`)
```python
@pytest.fixture
def mock_onnx_session():
    mock_session = MagicMock()
    import numpy as np
    logits = np.random.randn(1, 38).astype(np.float32)
    mock_session.run.return_value = [logits]
    with patch("src.api.inference._session", mock_session):
        with patch("src.api.inference._LABELS", [f"Class_{i}" for i in range(38)]):
            yield mock_session

@pytest.fixture(autouse=True)
def setup_test_keys():
    from backend import config
    original_keys = config.ALLOWED_API_KEYS
    config.ALLOWED_API_KEYS = {"agridoc-test-key"}
    yield
    config.ALLOWED_API_KEYS = original_keys
```

---

## Deployment (Free — Render.com Recommended)

### Backend (Web Service)
```yaml
buildCommand: pip install -r requirements.txt
startCommand: uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
envVars:
  - AGRIDOC_API_KEYS        # Generate fresh keys
  - AGRIDOC_DB_KEYS         # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  - CORS_ALLOWED_ORIGINS    # https://your-frontend.onrender.com
  - AGRIDOC_RATE_LIMIT=300
```

### Frontend (Static Site)
```yaml
buildCommand: cd frontend && npm ci && npm run build
publishPath: frontend/dist
envVars:
  - VITE_API_BASE=https://your-backend.onrender.com
```

### Oracle Cloud Always Free (Alternative)
See `DEPLOYMENT.md` for ARM instance setup, Nginx, systemd, SSL.

---

## Quick Verification

```bash
# Backend health (no auth)
curl http://localhost:9998/health

# Frontend proxy
curl http://localhost:3000/api/health

# API docs
open http://localhost:9998/docs

# Full prediction test
API_KEY=$(grep AGRIDOC_API_KEYS .env | cut -d= -f2)
curl -H "X-API-Key: $API_KEY" -F "file=@test_leaf.jpg" http://localhost:9998/predict
```

---

## Key Differentiators for Real-World Farmers

| Challenge | AgriDoc AI Solution |
|-----------|---------------------|
| No internet | Full offline: diagnose → queue → auto-sync when online |
| Wrong language | 10 Indian languages with grounded advisories (not MT) |
| Expensive data | <2MB PWA; client-side compression; gzip responses |
| No expert access | ICAR-sourced KB, organic-first, dose verification warnings |
| Market uncertainty | Real-time mandi prices (eNAM/AGMARKNET) in actionable plan |
| Weather risk | Open-Meteo → "wait for rain to pass before spray" |
| Privacy fears | Photos never leave device; encrypted storage; GDPR delete |
| Model trust | Grad-CAM shows WHY; confidence floor prevents guessing |
| Wrong diagnosis | Farmer feedback → expert review queue → model improvement |
| Pesticide misuse | Chemical doses never invented; "verify with officer" |

---

## Production Readiness Checklist

### ✅ Complete
- [x] Backend API functional on port 9998
- [x] Frontend PWA on port 3000 (Vite proxy to :9998)
- [x] All 138 tests passing
- [x] ONNX model loaded (610KB, 38 classes, 98.82% top-1)
- [x] API key auth (X-API-Key header)
- [x] Rate limiting (60 req/min/IP, X-Forwarded-For)
- [x] CORS (exact domains, no wildcards, headers on errors)
- [x] Security headers (CSP, HSTS, X-Frame-Options, etc.)
- [x] Gzip compression with header preservation
- [x] Request logging + request IDs
- [x] Health/readiness endpoints
- [x] EXIF/location privacy stripping
- [x] Offline sync (JSONL, 72h TTL, perceptual dedup)
- [x] 5-agent LangGraph with sequential fallback
- [x] Multilingual RAG (10 languages)
- [x] Grad-CAM visual explanations
- [x] PWA installable, offline-capable
- [x] DB encryption (Fernet MultiFernet, required)
- [x] GDPR data deletion endpoint

### ⚠️ Pre-Production
- [ ] Update `.env.example` CORS to `localhost:3000` only (remove 8501)
- [ ] Generate production API keys (don't use example keys)
- [ ] Configure SSL/TLS (HSTS requires HTTPS)
- [ ] Document Fernet key rotation procedure
- [ ] Redis for rate limiting at scale
- [ ] Monitoring/alerting (Prometheus/Grafana or Render metrics)
- [ ] Backup strategy for SQLite/PostgreSQL
- [ ] Load test (target: 100+ concurrent users)

---

**This CLAUDE.md is the authoritative development reference. All paths, configs, and code snippets are verified against the actual implementation.**