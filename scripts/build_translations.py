"""Build data/knowledge/translations.json from advisory_rules.json.

Produces a translation map {lang: {english_string: translated_string}} for the
knowledge-base strings. English is the source of truth. Other languages are
built from a small curated set of translations for the common strings (symptoms,
treatment bullets, prevention tips) that appear across many diseases.

In a real deployment you would run each unique English string through a
translator (Google Translate, Bhashini, etc.) once and commit the result. This
script creates the skeleton with placeholder translations for the demo — the
engine falls back to English automatically if a string is missing.
"""
from __future__ import annotations

import json
from pathlib import Path

# Make repo root importable so `configs` resolves when running
# `python scripts/build_translations.py` directly.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from configs import load_config

cfg = load_config("advice")
kb_path = Path(cfg["knowledge_json"])
out_path = Path(cfg["translations_json"])

if not kb_path.exists():
    raise RuntimeError(f"Knowledge base missing: {kb_path}")

KB = json.loads(kb_path.read_text(encoding="utf-8"))

LANGUAGES = ["hi", "kn", "ta", "te", "mr", "bn", "gu", "ml", "pa"]

strings = set()
strings.add("Guidance, not a replacement for an agriculture officer.")
strings.add("Verify doses and pre-harvest intervals locally before use.")
strings.add("Symptoms:")
strings.add("Low-cost / organic first:")
strings.add("Chemical (if needed):")
strings.add("Prevention:")
strings.add("Source:")
strings.add("reviewed")
strings.add("No verified advice found for that query. Please rephrase or contact an agriculture officer.")
for entry in KB.values():
    for k in ("symptoms", "organic", "chemical", "prevention"):
        for s in entry.get(k, []):
            strings.add(s)
strings = sorted(strings)

out: dict[str, dict[str, str]] = {}
for lang in LANGUAGES:
    out[lang] = {s: s for s in strings}

# Hindi common phrases
out["hi"].update({
    "Guidance, not a replacement for an agriculture officer.": "यह केवल मार्गदर्शन है, कृषि अधिकारी का विकल्प नहीं।",
    "Verify doses and pre-harvest intervals locally before use.": "उपयोग से पहले खुराक और उपज के अंतराल की स्थानीय जाँच करें।",
    "Symptoms:": "लक्षण:",
    "Low-cost / organic first:": "सस्ता / जैविक विकल्प:",
    "Chemical (if needed):": "रसायनिक उपचार (यदि आवश्यक हो):",
    "Prevention:": "रोकथाम:",
    "Source:": "स्रोत:",
    "reviewed": "समीक्षित",
    "No verified advice found for that query. Please rephrase or contact an agriculture officer.": "इस प्रश्न के लिए कोई पुष्टि सलाह नहीं मिली। कृपया पुनः प्रश्न करें या कृषि अधिकारी से संपर्क करें।",
})

# Kannada common phrases
out["kn"].update({
    "Guidance, not a replacement for an agriculture officer.": "ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ಕೃಷಿ ಅಧಿಕಾರಿಯ ಪ್ರತಿನಿಧಿತ್ವ ಅಲ್ಲ.",
    "Verify doses and pre-harvest intervals locally before use.": "ಬಳಕೆಗೂ ಮುಂಚೆ ಡೋಸುಗಳು ಮತ್ತು ಉತ್ಪಾದನೆ ಅಂತರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
    "Symptoms:": "ಲಕ್ಷಣಗಳು:",
    "Low-cost / organic first:": "ಕಡಿಮೆ ವೆಚ್ಚ / ಜೈವಿಕ ಮೊದಲು:",
    "Chemical (if needed):": "ರಸಾಯನಿಕ (ಆವಶ್ಯಕವಾದರೆ):",
    "Prevention:": "ಪ್ರತಿಬಂಧ:",
    "Source:": "ಮೂಲ:",
    "reviewed": "ಸಮೀಕ್ಷಿತ",
    "No verified advice found for that query. Please rephrase or contact an agriculture officer.": "ಆ ಪ್ರಶ್ನೆಗೆ ನಿಶ್ಚಿತ ಸಲಹೆ ಸಿಕ್ಕಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಕೇಳಿ ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
})

# Tamil common phrases
out["ta"].update({
    "Guidance, not a replacement for an agriculture officer.": "மேலாளர் அறிவுரை, விவசாய அலுவலரின் மாற்று அல்ல.",
    "Verify doses and pre-harvest intervals locally before use.": "பயன்படுத்துமுன் அளவுகள் மற்றும் நடவு இடைவெளிகளைச் சரிபார்க்கவும்.",
    "Symptoms:": "அறிகுறிகள்:",
    "Low-cost / organic first:": "குறைந்த செலவு / கரிமம் முதலில்:",
    "Chemical (if needed):": "ரசாயனம் (தேவைப்பட்டால்):",
    "Prevention:": "தடுப்பு:",
    "Source:": "மூலம்:",
    "reviewed": "மறுஆய்வு",
    "No verified advice found for that query. Please rephrase or contact an agriculture officer.": "அந்த வினாவிற்கான உறுதிப்படுத்தப்பட்ட ஆலோசனை கிடைக்கவில்லை. மீண்டும் கேளுங்கள் அல்லது விவசாய அலுவலரைத் தொடர்பு கொள்ளுங்கள்.",
})

# Telugu common phrases
out["te"].update({
    "Guidance, not a replacement for an agriculture officer.": "మార్గదర్శకత్వం మాత్రమే, వ్యవసాయ అధికారికి ప్రత్యామ్నాయం కాదు.",
    "Verify doses and pre-harvest intervals locally before use.": "ఉపయోగించే ముందు డోసులు మరియు ఉత్పాదన అంతరాలను సరిచూసుకోండి.",
    "Symptoms:": "లక్షణాలు:",
    "Low-cost / organic first:": "తక్కువ ఖర్చు / ఆర్గానిక్ మొదటిది:",
    "Chemical (if needed):": "రసాయనం (అవసరమైతే):",
    "Prevention:": "ముందు జాగ్రత్త:",
    "Source:": "మూలం:",
    "reviewed": "సమీక్షించబడింది",
    "No verified advice found for that query. Please rephrase or contact an agriculture officer.": "ఆ ప్రశ్నకు నిర్ధారిత సలహా దొరకలేదు. దయచేసి మళ్ళీ అడగండి లేదా వ్యవసాయ అధికారినీ సంప్రదించండి.",
})

# Marathi common phrases
out["mr"].update({
    "Guidance, not a replacement for an agriculture officer.": "मार्गदर्शन फक्त, शेती अधिकारांचे प्रतिनिधित्व नाही.",
    "Verify doses and pre-harvest intervals locally before use.": "वापरपूर्वी डोस आणि उत्पादन अंतर तपासा.",
    "Symptoms:": "लक्षणे:",
    "Low-cost / organic first:": "कमी खर्च / जैविक प्रथम:",
    "Chemical (if needed):": "रसायने (गरज असल्यास):",
    "Prevention:": "प्रतिबंध:",
    "Source:": "स्रोत:",
    "reviewed": "समीक्षित",
    "No verified advice found for that query. Please rephrase or contact an agriculture officer.": "त्या प्रश्नासाठी पुष्टीकृत सल्ला मिळाला नाही. कृपया पुन्हा विचारा किंवा शेती अधिकाऱ्याशी संपर्क साधा.",
})

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {len(out)} languages -> {out_path}")
for lang, mapping in out.items():
    print(f"  {lang}: {len(mapping)} strings")