"""AgriDoc AI FastAPI application.

Endpoints:
  GET  /health          — liveness + model info
  GET  /ready           — readiness (model loaded?)
  GET  /classes         — supported crop/disease classes
  POST /predict         — leaf image -> top-k diagnosis + Grad-CAM overlay
  POST /advice          — class label + language -> grounded treatment advice
  POST /rag             — free-text question -> grounded KB answer
  POST /feedback        — "was this correct?" -> expert review queue
  DELETE /data          — delete my data (privacy)

Auth: X-API-Key header. Rate limit: 60 req/min per IP.
"""
from __future__ import annotations

import base64
import gzip
import io
import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image

from backend import config
from .inference import predict, model_info
import logging

# Use standard library logger
logger = logging.getLogger("agridoc.api")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
from src.advice.engine import build_advice, answer_free_text
from src.advice import knowledge as kb_module

# Sanitize class labels and text inputs
_LABEL_RE = re.compile(r'^[A-Za-z0-9_\-]+$', re.ASCII)
_TEXT_MAX_LEN = 200
_COMMENT_MAX_LEN = 500

# Initialize global model loader and advice data
_model_loader = None
_advice_data = None

def _get_advice_data():
    """Get advice data."""
    global _advice_data
    if _advice_data is None:
        _advice_data = {
            "backbone": "efficientnet_b0",
            "image_size": 224,
            "confidence_floor": 0.70,
            "top_k": 3,
            "supported_languages": ["en", "hi", "bn", "ta", "te", "mr", "gu", "ml", "kn", "pa"],
            "supported_crops": [
                "Apple", "Blueberry", "Cherry", "Corn", "Grape", "Orange",
                "Peach", "Pepper", "Potato", "Raspberry", "Soybean", "Squash",
                "Strawberry", "Tomato",
            ],
            "rules": [
                {
                    "class": "Leaf_Blight",
                    "languages": {
                        "en": "Mix 1 tbsp neem oil with 1 liter water, spray weekly for 3 weeks.",
                        "hi": "1 चम्मच नीम का तेल 1 लीटर पानी के साथ मिलाएं, हफ्तावार 3 हफ्तों तक छिड़काव करें।",
                    },
                    "care_level": "medium",
                },
                {
                    "class": "Healthy",
                    "languages": {
                        "en": "Plant is healthy. Continue regular care and monitoring.",
                        "hi": "पौधा स्वस्थ है। नियमित देखभाल और निगरानी जारी रखें।",
                    },
                    "care_level": "low",
                },
                {
                    "class": "Rice_Blade_Blight",
                    "languages": {
                        "en": "Apply fungicide every 7 days. Remove infected plant parts.",
                        "hi": "हर 7 दिनों में फफूंदनाशक का छिड़काव करें। संक्रमित पौधे के हिस्सों को हटा दें।",
                    },
                    "care_level": "high",
                },
            ],
            "max_query_length": 200,
            "min_query_length": 3,
            "default_language": "en",
            "fallback_language": "en",
            "fallback_advice": "Please consult with an agricultural expert for specific guidance.",
        }
    return _advice_data

def _get_all_classes():
    """Get all supported classes from knowledge base or fallback."""
    try:
        # Try knowledge base first (preferred source)
        return sorted(kb_module.all_classes())
    except Exception:
        pass

    # Fallback: use classes.json
    try:
        classes_path = PKG_ROOT / "data" / "splits" / "classes.json"
        if classes_path.exists():
            return json.loads(classes_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    # Last resort: stub data (should never reach in production)
    return [
        "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",
        "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___healthy",
    ]

app = FastAPI(title="AgriDoc AI", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

# CORS config — restrict in production via CORS_ALLOWED_ORIGINS env var
# MUST be added FIRST so CORS headers are applied to ALL responses including auth errors
_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
import logging
logger.info(f"CORS_ALLOWED_ORIGINS from env: {os.environ.get('CORS_ALLOWED_ORIGINS')}")
logger.info(f"ALLOWED_ORIGINS list: {_ALLOWED_ORIGINS}")
if _ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
else:
    logger.warning("No CORS_ALLOWED_ORIGINS configured - CORS middleware not added!")

# Auth + rate limiting
_RATE: dict[str, list[float]] = defaultdict(list)

def _check_api_key(request: Request) -> None:
    key = request.headers.get(config.API_KEY_HEADER)
    # DEBUG
    import logging
    debug_logger = logging.getLogger("debug_auth")
    debug_logger.warning(f"API_KEY_HEADER={config.API_KEY_HEADER}, got key={key}, allowed={config.ALLOWED_API_KEYS}")
    if not key or key not in config.ALLOWED_API_KEYS:
        raise HTTPException(status_code=401, detail="unauthorised")

def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _RATE[ip]
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= config.RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="too many requests")
    window.append(now)
# Security headers
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline';",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Cache-Control": "no-store",
}
@app.middleware("http")
async def _security_mw(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    t0 = time.perf_counter()
    # Skip auth for liveness/readiness probes and OpenAPI docs.
    # /docs and /redoc are dev-only — they are not served in production
    # deployments (docs_url=None) and are safe to leave unauthenticated
    # because they expose no data, only the API schema.
    if (
        request.url.path in ("/health", "/ready", "/docs", "/redoc", "/openapi.json")
        or request.method == "OPTIONS"
    ):
        return await call_next(request)
    # Log every request
    logger.info(
        f"{request.method} {request.url.path} {request.client.host if request.client else '-'}",
        extra={"request_id": request_id, "http_method": request.method, "path": request.url.path, "client_host": request.client.host if request.client else "-"},
    )
    try:
        _check_api_key(request)
        _rate_limit(request)
    except HTTPException as exc:
        logger.warning(
            "auth/rate-limit fail",
            extra={"request_id": request_id, "http_method": request.method, "path": request.url.path, "error": exc.detail},
        )
        response = JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
        response.headers["x-request-id"] = request_id
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        # Add CORS headers to error responses
        origin = request.headers.get("origin")
        if origin in _ALLOWED_ORIGINS:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        return response
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        f"request-response: {request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.0f}ms)",
        extra={"request_id": request_id, "http_method": request.method, "path": request.url.path, "status_code": response.status_code, "elapsed_ms": elapsed_ms},
    )
    # Add request ID to response headers
    response.headers["x-request-id"] = request_id
    for header, value in _SECURITY_HEADERS.items():
        response.headers[header] = value
    # Add CORS headers for allowed origins
    origin = request.headers.get("origin")
    if origin in _ALLOWED_ORIGINS:
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"
    # Store headers before gzip compression
    response_headers = dict(response.headers)
    # Gzip compression for JSON responses
    accept_encoding = request.headers.get("accept-encoding", "")
    if "gzip" in accept_encoding and "application/json" in response.headers.get("content-type", ""):
        body = b"".join([chunk async for chunk in response.body_iterator])
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(body)
        response = Response(content=buf.getvalue(), status_code=response.status_code)
        response.headers["content-encoding"] = "gzip"
        response.headers["content-type"] = "application/json"
        # Restore CORS, security, and id headers after gzip
        # Exclude Content-Length since compressed size differs from original
        for header, value in response_headers.items():
            if header.lower() != "content-length":
                response.headers[header] = value
    return response
@app.get("/health")
async def health():
    return {"status": "ok", "model": model_info()}
@app.get("/ready")
async def readiness():
    """Health check that also verifies model is loaded."""
    try:
        info = model_info()
        return {"status": "ready", "model": info}
    except Exception as exc:
        logger.error("readiness check failed: %s", str(exc))
        return JSONResponse(status_code=503, content={"status": "not ready", "error": str(exc)})
@app.get("/model-info")
async def model_info_endpoint():
    """Get the ONNX model metadata."""
    from .inference import model_info
    return model_info()
@app.get("/classes")
async def classes():
    """Get all supported classes for crop disease prediction."""
    return {"classes": _get_all_classes()}
@app.post("/predict")
async def predict_endpoint(
    request: Request,
    file: UploadFile = File(...),
    top_k: int = 3,
    include_cam: bool = False,
):
    """Upload a leaf photo -> top-k diagnosis + optional Grad-CAM overlay."""
    if file.content_type not in config.ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, f"unsupported media type: {file.content_type}")
    raw = await file.read()
    if len(raw) > config.MAX_IMAGE_BYTES:
        raise HTTPException(413, "image too large (max 10 MiB)")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(400, "not a valid image")
    result = predict(raw, top_k=top_k)
    out = {
        "diagnosis": result["predictions"][0]["class"],
        "confidence": result["confidence"],
        "predictions": result["predictions"],
        "uncertain": result["uncertain"],
        "confidence_floor": result["confidence_floor"],
    }
    if include_cam:
        from src.vision.gradcam import overlay_png  # type: ignore
        out["gradcam_url"] = "data:image/png;base64," + overlay_png(img, result["predictions"][0]["class"])
    return out
@app.post("/advice")
async def advice_endpoint(class_label: str = Form(...), lang: str = Form("en")):
    if not class_label or not _LABEL_RE.match(class_label):
        raise HTTPException(400, "invalid class_label")
    if lang not in ("en", "hi", "bn", "ta", "te", "mr", "gu", "ml", "kn", "pa"):
        raise HTTPException(400, "unsupported language")
    try:
        return build_advice(class_label, lang=lang)
    except KeyError:
        raise HTTPException(404, "no advisory entry for that disease")
@app.post("/rag")
async def rag_endpoint(query: str = Form(...), lang: str = Form("en")):
    if not query.strip() or len(query) > _TEXT_MAX_LEN:
        raise HTTPException(400, "query is required (max 200 chars)")
    if lang not in ("en", "hi", "bn", "ta", "te", "mr", "gu", "ml", "kn", "pa"):
        raise HTTPException(400, "unsupported language")
    return answer_free_text(query, lang=lang)
@app.post("/agripulse")
async def agripulse_endpoint(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("en"),
    district: str = Form(""),
    offline: bool = Form(False),
):
    """Run the full AgriPulse workflow: diagnose -> advise -> market -> weather -> plan.

    Returns the final state with a single actionable plan and reasons.
    """
    raw = await file.read()
    if len(raw) > config.MAX_IMAGE_BYTES:
        raise HTTPException(413, "image too large (max 10 MiB)")
    from src.agents.graph import run_agripulse
    state = run_agripulse(
        image_bytes=raw,
        language=language,
        district=district,
        offline=offline,
    )
    return {
        "plan": state.get("plan", "call_expert"),
        "reasons": state.get("reasons", []),
        "predicted_class": state.get("predicted_class", ""),
        "confidence": state.get("confidence", 0.0),
        "advice": state.get("advice_text", ""),
        "sell_recommendation": state.get("sell_recommendation", "unknown"),
        "weather_risk": state.get("weather_risk", "unknown"),
        "decisions": state.get("decisions", []),
    }
@app.post("/feedback")
async def feedback_endpoint(class_label: str = Form(...), correct: bool = Form(...),
                            comment: str = Form("")):
    from src.feedback.review_queue import submit
    return submit(class_label=class_label, correct=correct, comment=comment)
@app.post("/sync")
async def sync_endpoint(request: Request):
    """Accept offline-queued predictions and reconcile duplicates.

    Body: {"device_id": str, "items": [ {id, ts, image_b64, mime_type,
    predicted_class, confidence, uncertain, farmer_correct, farmer_comment}, ... ]}

    Returns: {"synced": [...ids], "merged": [...ids], "rejected": [...ids],
              "server_predictions": {id: {...}}}
    """
    body = await request.json()
    device_id = body.get("device_id", "unknown")
    items = body.get("items", [])
    from src.api.inference import predict
    from src.feedback.review_queue import submit as feedback_submit

    synced: List[str] = []
    merged: List[str] = []
    rejected: List[str] = []
    server_predictions: Dict[str, dict] = {}

    for item in items:
        # Re-run the prediction server-side to reconcile duplicates.
        try:
            result = predict(item["image_b64"] if isinstance(item["image_b64"], bytes) else _b64d(item["image_b64"]))
        except Exception:
            rejected.append(item["id"])
            continue
        top = result["predictions"][0]
        if top["class"] == item["predicted_class"]:
            synced.append(item["id"])
        else:
            merged.append(item["id"])
        server_predictions[item["id"]] = {
            "predicted_class": top["class"],
            "confidence": top["confidence"],
            "uncertain": result["uncertain"],
        }
        # Merge farmer verdict into the expert review queue.
        if item.get("farmer_correct") is not None:
            feedback_submit(
                class_label=top["class"],
                correct=bool(item["farmer_correct"]),
                comment=item.get("farmer_comment", "") + " [offline]",
            )
    return {
        "synced": synced,
        "merged": merged,
        "rejected": rejected,
        "server_predictions": server_predictions,
    }
def _b64d(s: str) -> bytes:
    import base64
    return base64.b64decode(s)
@app.delete("/data")
async def delete_data():
    from src.feedback.review_queue import purge_user
    return purge_user()
@app.exception_handler(HTTPException)
async def _err_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})