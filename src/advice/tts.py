"""Text-to-speech for low-literacy farmers.

Many smallholders prefer to listen rather than read a diagnosis. This module
renders the advice text to audio using a local TTS engine (espeak-ng on
Linux, pyttsx3 fallback) so it works offline. Output is a base64 WAV that the
mobile app can play directly.

No cloud dependency: espeak-ng is a tiny C binary (2 MB) that runs on any
Android/Linux device.
"""
from __future__ import annotations

import base64
import io
import logging
import shutil
import subprocess
from typing import Optional

log = logging.getLogger("agridoc.tts")

# espeak-ng voice presets per language. Each maps to an espeak voice name.
VOICES = {
    "en": "en+m3",
    "hi": "hi+m3",
    "bn": "bn+m3",
    "ta": "ta+m3",
    "te": "te+m3",
    "mr": "mr+m3",
    "gu": "gu+m3",
    "ml": "ml+m3",
    "kn": "kn+m3",
    "pa": "pa+m3",
}

# Speed: words per minute. Slower is better for low-literacy listeners.
SPEED = {
    "en": 150,
    "hi": 140,
    "bn": 140,
    "ta": 140,
    "te": 140,
    "mr": 140,
    "gu": 140,
    "ml": 140,
    "kn": 140,
    "pa": 140,
}


def _espeak_path() -> Optional[str]:
    return shutil.which("espeak-ng") or shutil.which("espeak")


def speak_espeak(text: str, lang: str = "en") -> Optional[bytes]:
    """Synthesize speech with espeak-ng. Returns WAV bytes or None."""
    path = _espeak_path()
    if not path:
        return None
    voice = VOICES.get(lang, "en+m3")
    speed = SPEED.get(lang, 150)
    cmd = [path, "-v", voice, "-s", str(speed), "-w", "-", text]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, check=True, timeout=30
        )
        return proc.stdout or None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        log.warning("espeak failed: %s", exc)
        return None


def speak_pyttsx3(text: str, lang: str = "en") -> Optional[bytes]:
    """Fallback TTS using pyttsx3 (offline, system-dependent)."""
    try:
        import pyttsx3
    except ImportError:
        return None
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", SPEED.get(lang, 150))
        voices = engine.getProperty("voices")
        # Try to pick a voice matching the language.
        for v in voices:
            if lang in (v.name or "").lower() or lang in (v.id or "").lower():
                engine.setProperty("voice", v.id)
                break
        buf = io.BytesIO()
        engine.save_to_file(text, buf)  # type: ignore[arg-type]
        engine.runAndWait()
        data = buf.getvalue()
        return data or None
    except Exception as exc:  # noqa: BLE001
        log.warning("pyttsx3 failed: %s", exc)
        return None


def speak(text: str, lang: str = "en") -> Optional[str]:
    """Render *text* to audio and return base64 data URL, or None if unavailable.

    Order: espeak-ng (best offline quality) -> pyttsx3 -> None.
    """
    for fn in (speak_espeak, speak_pyttsx3):
        wav = fn(text, lang)
        if wav:
            b64 = base64.b64encode(wav).decode("ascii")
            return f"data:audio/wav;base64,{b64}"
    return None


def available_voices() -> dict:
    """Return the set of languages with a usable TTS voice."""
    out = {}
    for lang in VOICES:
        out[lang] = bool(_espeak_path() or _pyttsx3_available())
    return out


def _pyttsx3_available() -> bool:
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        return False


def synthesize_speech(text: str, lang: str = "en") -> Optional[str]:
    """Wrapper for backward compatibility."""
    return speak(text, lang)