"""AgriDoc AI advice module.

This package contains treatment advice generation and multilingual support.
"""

from .engine import build_advice
from .translate import translate_text, available_languages
from .knowledge import get_entry, all_classes, has_entry
from .tts import speak as synthesize_speech

__all__ = [
    "build_advice",
    "translate_text",
    "available_languages",
    "get_entry",
    "all_classes",
    "has_entry",
    "synthesize_speech",
]
