"""AgriDoc AI API services.

This package contains FastAPI applications and inference endpoints
for agricultural AI prediction and advice services.
"""

from .app import app
from .inference import predict

__all__ = ["app", "predict_onnx"]