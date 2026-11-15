"""Download ONNX model at startup for cloud deployments.

This script checks if the model exists and downloads it from HuggingFace
if needed. Run this before starting uvicorn in production environments.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def ensure_model_exists():
    """Download model from HuggingFace if not present locally."""
    model_path = Path("models/artifacts/agridoc_cv.onnx")

    # Check if model already exists
    if model_path.exists():
        size_kb = model_path.stat().st_size / 1024
        print(f"[OK] Model already exists: {model_path} ({size_kb:.1f} KB)")
        return True

    # Model doesn't exist - try to download from HuggingFace
    hf_url = "https://huggingface.co/roshanjpr80/agridoc-model/blob/main/agridoc_cv.onnx"

    print(f"[INFO] Downloading model from: {hf_url}")
    print("   This may take 30-60 seconds...")

    try:
        import requests
        response = requests.get(hf_url, timeout=120, stream=True)
        response.raise_for_status()

        # Ensure directory exists
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = downloaded * 100 // total_size
            sys.stderr.write(f"\r   Progress: {percent}% ({downloaded / 1024 / 1024:.2f} MB)")
            sys.stderr.flush()

        print()
        print(f"[OK] Model downloaded successfully: {model_path} ({downloaded / 1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        return False


if __name__ == "__main__":
    success = ensure_model_exists()
    sys.exit(0 if success else 1)
