# AgriDoc AI — Development Guide

Crop disease diagnosis platform: EfficientNet CV model, FastAPI backend,
React/Vite PWA frontend, LangGraph agent orchestration. Built for farmers
with intermittent connectivity.

## Project Layout

```
src/api/          production API (12 endpoints). CPU-only, ONNX, no PyTorch.
backend/          minimal entrypoint (/health, /ready) + settings/config.
src/advice/       advisory engine, knowledge base, multilingual RAG.
src/sync/         offline prediction queue (JSONL, retries, purge).
src/vision/       image preprocessing, perceptual hashing, Grad-CAM.
src/agents/       AgriPulse LangGraph workflow.
configs/          YAML hyperparameter source of truth (data, train, advice, sync).
scripts/          generate_secrets.sh, deploy scripts.
frontend/         React 19 + Vite 8 PWA (port 3000).
tests/            pytest suite (32 tests passing).
```

## Two Runtime Profiles

**Production API** (what public users hit):
- `src/api/app.py` — CPU-only, ONNX Runtime, no PyTorch. 610KB model, 38 classes.
- Port: 9998
- Reads `backend/config.py` and `os.environ` (AGRIDOC_ prefix)
- **Required auth**: X-API-Key header on all endpoints except /health, /ready, /docs

**Minimal entrypoint**:
- `backend/main.py` — only /health, /ready. Pulls `backend/models/cv_model.py` which imports torch. **Not the production path.**

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt     # Python 3.14, verified

# Start backend (Terminal 1)
.\agridoc-venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 9998

# Start frontend (Terminal 2)
cd frontend && npm run dev
```

## Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 9998 | http://localhost:9998 |
| API Docs | 9998 | http://localhost:9998/docs |
| Frontend | 3000 | http://localhost:3000 |
| Frontend proxy | 3000 | http://localhost:3000/api/health → :9998 |

**Port 8501 is obsolete** (Streamlit legacy). Frontend now uses port 3000.

## API Endpoints (12 total)

| Method | Path | Auth? | Purpose |
|--------|------|-------|---------|
| GET | /health | ❌ | Liveness + model info |
| GET | /ready | ❌ | Readiness probe |
| GET | /classes | ✅ | 38 crop disease classes |
| POST | /predict | ✅ | Image → diagnosis |
| POST | /advice | ✅ | Treatment advice |
| POST | /rag | ✅ | Free-text Q&A |
| POST | /agripulse | ✅ | Full workflow |
| POST | /sync | ✅ | Offline reconciliation |
| POST | /feedback | ✅ | Correction submission |
| DELETE | /data | ✅ | Delete my data |

## Adding Dependencies

Ask: does the production path need it? The production API is:
`src/api/app.py` → `src/api/inference.py` → ONNX Runtime only.

If **no** → add to "training/export" section of `requirements.txt`.

If **yes** → add to main section with pinned version.

## Configuration

- **Environment**: `.env` (never commit) ← `.env.example` (tracked, no secrets).
- **Model tuning** (confidence floor, top-k, image size): `configs/data.yaml` and `configs/advice.yaml`. Not env vars.
- **Sync queue TTL**: `configs/sync.yaml` → `queue_ttl_hours`. `src/sync/queue.py` reads it.

## Security (Critical)

- **API key required** on every endpoint except `/health`, `/ready`, `/docs`, `/redoc`, `/openapi.json`. Keys in `AGRIDOC_API_KEYS`.
- **`AGRIDOC_DB_KEYS` (Fernet) is REQUIRED** — the DB layer raises ValueError rather than storing plaintext. Never skip this.
- **`CORS_ALLOWED_ORIGINS` must never be `*`** — the API key travels in an HTTP header, not a cookie. List exact domains.
- **Rate limiting**: 60 requests/minute per IP by default. Override with `AGRIDOC_RATE_LIMIT_PER_MIN`.
- **Security headers**: CSP, HSTS (1 year), X-Frame-Options, X-Content-Type-Options, Cache-Control: no-store.
- **Fresh keys needed**: The API keys in `.env.example` are compromised — generate new ones for any real deployment.

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Test count: 32 tests
# Coverage: API endpoints, advice engine, LangGraph agents, sync queue
```

## Deployment (Free)

See `DEPLOYMENT.md` — deploy to Oracle Cloud Always Free ($0/month, no expiration).

## Quick Verification

```bash
# Backend health
curl -H "X-API-Key: $(grep AGRIDOC_API_KEYS .env | cut -d= -f2)" http://localhost:9998/health

# Frontend proxy works
curl http://localhost:3000/api/health

# API docs
open http://localhost:9998/docs
```