import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type SupportedLanguage =
  | 'en' | 'hi' | 'bn' | 'ta' | 'te'
  | 'mr' | 'gu' | 'ml' | 'kn' | 'pa';

interface LanguageOption {
  code: SupportedLanguage;
  name: string;
  nativeName: string;
  flag: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇬🇧' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिंदी', flag: '🇮🇳' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', flag: '🇧🇩' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', flag: '🇮🇳' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', flag: '🇮🇳' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', flag: '🇮🇳' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', flag: '🇮🇳' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം', flag: '🇮🇳' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', flag: '🇮🇳' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ', flag: '🇮🇳' },
];

interface LanguageContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string, params?: Record<string, string>) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// Translation dictionary - in production, this would be loaded from JSON files
const translations: Record<SupportedLanguage, Record<string, string>> = {
  en: {
    // Navigation
    'nav.diagnose': 'Diagnose Leaf',
    'nav.chat': 'Expert Chat',
    'nav.dashboard': 'Dashboard',
    'nav.library': 'Disease Library',
    'nav.history': 'My History',
    'nav.settings': 'Settings',
    'nav.clearData': 'Clear All Data',

    // Camera View
    'camera.title': 'Leaf Diagnosis',
    'camera.subtitle': 'Upload or capture a leaf photo for instant AI disease detection',
    'camera.dropzone': 'Drop an image here or tap to capture',
    'camera.hint': 'Supports JPG, PNG, WEBP • Max 10 MB',
    'camera.openCamera': 'Open Camera',
    'camera.retake': 'Retake',
    'camera.diagnose': 'Diagnose Now',
    'camera.loading': 'Analyzing leaf with AI model…',
    'camera.tip.lighting': 'Good lighting — Natural daylight gives best results',
    'camera.tip.focus': 'Focus on symptoms — Capture spots, lesions, discoloration clearly',
    'camera.tip.offline': 'Works offline — Results queue locally when no connection',
    'camera.tip.privacy': 'Your privacy — Photos stored only on your device',

    // Result View
    'result.title': 'Diagnosis Result',
    'result.newDiagnosis': 'New Diagnosis',
    'result.confidence': 'Confidence',
    'result.uncertain': 'Uncertain — recommend re-take',
    'result.confident': 'Confident diagnosis',
    'result.topPredictions': 'Top Predictions',
    'result.treatmentAdvice': 'Treatment Advice',
    'result.disclaimer': 'Guidance, not a replacement for an agriculture officer.',
    'result.save': 'Save to History',
    'result.share': 'Share Report',
    'result.reportMiss': 'Wrong Diagnosis',
    'result.askAbout': 'Ask about this disease',
    'result.viewLibrary': 'View in Library',
    'result.print': 'Print Report',
    'result.quickActions': 'Quick Actions',
    'result.relatedDiseases': 'Related Diseases',

    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.subtitle': 'System overview and statistics',
    'dashboard.modelRuntime': 'Model Runtime',
    'dashboard.diseaseClasses': 'Disease Classes',
    'dashboard.confidenceFloor': 'Confidence Floor',
    'dashboard.myDiagnoses': 'My Diagnoses',
    'dashboard.supportedCrops': 'Supported Crops',
    'dashboard.allClasses': 'All Disease Classes',

    // Library
    'library.title': 'Disease Library',
    'library.subtitle': 'Browse all supported diseases and their treatments',
    'library.search': 'Search diseases…',
    'library.filterCrop': 'All Crops',
    'library.filterType': 'All Types',
    'library.type.fungal': 'Fungal',
    'library.type.bacterial': 'Bacterial',
    'library.type.viral': 'Viral',
    'library.type.healthy': 'Healthy',
    'library.type.other': 'Other',
    'library.diagnose': 'Diagnose',
    'library.treatment': 'Treatment',
    'library.empty': 'No diseases match your filters.',

    // History
    'history.title': 'My History',
    'history.subtitle': 'Previous diagnoses saved locally',
    'history.export': 'Export JSON',
    'history.empty': 'No diagnoses yet. Start by taking a leaf photo!',
    'history.details': 'Details',
    'history.delete': 'Delete',

    // Chat
    'chat.title': 'Expert Chat',
    'chat.subtitle': 'Ask crop health questions — answers from verified knowledge base',
    'chat.placeholder': 'Type your question…',
    'chat.send': 'Send',
    'chat.tryAsking': 'Try asking:',

    // Settings
    'settings.title': 'Settings',
    'settings.subtitle': 'Customize your experience',
    'settings.appearance': 'Appearance',
    'settings.darkMode': 'Dark Mode',
    'settings.language': 'Language',
    'settings.connection': 'Connection',
    'settings.apiEndpoint': 'API Endpoint',
    'settings.offlineMode': 'Offline Mode',
    'settings.autoSave': 'Auto-save Results',
    'settings.dataPrivacy': 'Data & Privacy',
    'settings.privacyDesc': 'Your diagnoses are stored locally on this device. No photos are uploaded to any server.',
    'settings.deleteAll': 'Delete All Local Data',
    'settings.about': 'About',
    'settings.version': 'AgriDoc AI v2.0',
    'settings.tech': 'EfficientNet-B0 · ONNX Runtime · CPU Inference',
    'settings.mission': 'Built for farmers with limited connectivity',

    // Common
    'common.online': 'Online',
    'common.offline': 'Offline',
    'common.checking': 'Checking…',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.delete': 'Delete',
    'common.confirm': 'Confirm',
    'common.close': 'Close',
    'common.loading': 'Loading…',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.warning': 'Warning',
    'common.info': 'Information',

    // Errors
    'error.selectImage': 'Please select or capture a leaf photo first.',
    'error.predictionFailed': 'Prediction failed. Check backend connection.',
    'error.adviceUnavailable': 'Advice unavailable. Please consult an agriculture officer.',
    'error.feedbackFailed': 'Could not submit feedback',
    'error.feedbackSuccess': 'Feedback submitted — thank you!',
    'error.offline': 'Running offline — upload images when connected',
    'error.noHistory': 'No history to export',
    'error.exportSuccess': 'Exported {{count}} records',
    'error.dataCleared': 'All data cleared',
    'error.popupBlocked': 'Pop-up blocked — allow pop-ups to print',
  },
  hi: {
    'nav.diagnose': 'पत्ती का निदान',
    'nav.chat': 'विशेषज्ञ चैट',
    'nav.dashboard': 'डैशबोर्ड',
    'nav.library': 'रोग पुस्तकालय',
    'nav.history': 'मेरा इतिहास',
    'nav.settings': 'सेटिंग्स',
    'nav.clearData': 'सभी डेटा साफ़ करें',

    'camera.title': 'पत्ती निदान',
    'camera.subtitle': 'तत्काल AI रोग पहचान के लिए पत्ती की फोटो अपलोड या खींचें',
    'camera.dropzone': 'यहाँ छवि डालें या खींचने के लिए टैप करें',
    'camera.hint': 'JPG, PNG, WEBP समर्थित • अधिकतम 10 MB',
    'camera.openCamera': 'कैमरा खोलें',
    'camera.retake': 'फिर से लें',
    'camera.diagnose': 'अभी निदान करें',
    'camera.loading': 'AI मॉडल से पत्ती का विश्लेषण…',
    'camera.tip.lighting': 'अच्छी रोशनी — प्राकृतिक दिन का प्रकाश सर्वोत्तम परिणाम देता है',
    'camera.tip.focus': 'लक्षणों पर ध्यान दें — धब्बे, घाव, मलिनकिरण स्पष्ट रूप से खींचें',
    'camera.tip.offline': 'ऑफ़लाइन काम करता है — कनेक्शन न होने पर परिणाम स्थानीय रूप से कतारबद्ध होते हैं',
    'camera.tip.privacy': 'आपकी गोपनीयता — फोटो केवल आपके डिवाइस पर संग्रहीत',

    'result.title': 'निदान परिणाम',
    'result.newDiagnosis': 'नया निदान',
    'result.confidence': 'आत्मविश्वास',
    'result.uncertain': 'अनिश्चित — दोबारा लेने की सलाह',
    'result.confident': 'आत्मविश्वासपूर्ण निदान',
    'result.topPredictions': 'शीर्ष भविष्यवाणियाँ',
    'result.treatmentAdvice': 'उपचार सलाह',
    'result.disclaimer': 'मार्गदर्शन, कृषि अधिकारी का विकल्प नहीं।',
    'result.save': 'इतिहास में सहेजें',
    'result.share': 'रिपोर्ट साझा करें',
    'result.reportMiss': 'गलत निदान',
    'result.askAbout': 'इस रोग के बारे में पूछें',
    'result.viewLibrary': 'पुस्तकालय में देखें',
    'result.print': 'रिपोर्ट प्रिंट करें',
    'result.quickActions': 'त्वरित कार्य',
    'result.relatedDiseases': 'संबंधित रोग',

    'dashboard.title': 'डैशबोर्ड',
    'dashboard.subtitle': 'सिस्टम अवलोकन और आंकड़े',
    'dashboard.modelRuntime': 'मॉडल रनटाइम',
    'dashboard.diseaseClasses': 'रोग वर्ग',
    'dashboard.confidenceFloor': 'आत्मविश्वास न्यूनतम',
    'dashboard.myDiagnoses': 'मेरे निदान',
    'dashboard.supportedCrops': 'समर्थित फसलें',
    'dashboard.allClasses': 'सभी रोग वर्ग',

    'library.title': 'रोग पुस्तकालय',
    'library.subtitle': 'सभी समर्थित रोगों और उनके उपचारों को ब्राउज़ करें',
    'library.search': 'रोग खोजें…',
    'library.filterCrop': 'सभी फसलें',
    'library.filterType': 'सभी प्रकार',
    'library.type.fungal': 'फफूंदी',
    'library.type.bacterial': 'जीवाणु',
    'library.type.viral': 'वायरल',
    'library.type.healthy': 'स्वस्थ',
    'library.type.other': 'अन्य',
    'library.diagnose': 'निदान',
    'library.treatment': 'उपचार',
    'library.empty': 'आपके फिल्टर से कोई रोग मेल नहीं खाता।',

    'history.title': 'मेरा इतिहास',
    'history.subtitle': 'स्थानीय रूप से सहेजे गए पिछले निदान',
    'history.export': 'JSON निर्यात करें',
    'history.empty': 'अभी तक कोई निदान नहीं। पत्ती की फोटो लेकर शुरू करें!',
    'history.details': 'विवरण',
    'history.delete': 'हटाएं',

    'chat.title': 'विशेषज्ञ चैट',
    'chat.subtitle': 'फसल स्वास्थ्य प्रश्न पूछें — सत्यापित ज्ञान आधार से उत्तर',
    'chat.placeholder': 'अपना प्रश्न लिखें…',
    'chat.send': 'भेजें',
    'chat.tryAsking': 'पूछने का प्रयास करें:',

    'settings.title': 'सेटिंग्स',
    'settings.subtitle': 'अपना अनुभव अनुकूलित करें',
    'settings.appearance': 'दिखावट',
    'settings.darkMode': 'डार्क मोड',
    'settings.language': 'भाषा',
    'settings.connection': 'कनेक्शन',
    'settings.apiEndpoint': 'API एंडपॉइंट',
    'settings.offlineMode': 'ऑफ़लाइन मोड',
    'settings.autoSave': 'स्वचालित सहेजना',
    'settings.dataPrivacy': 'डेटा और गोपनीयता',
    'settings.privacyDesc': 'आपके निदान इस डिवाइस पर स्थानीय रूप से संग्रहीत हैं। कोई फोटो किसी सर्वर पर अपलोड नहीं की जाती।',
    'settings.deleteAll': 'सभी स्थानीय डेटा हटाएं',
    'settings.about': 'के बारे में',
    'settings.version': 'AgriDoc AI v2.0',
    'settings.tech': 'EfficientNet-B0 · ONNX रनटाइम · CPU इन्फरेंस',
    'settings.mission': 'सीमित कनेक्टिविटी वाले किसानों के लिए बनाया गया',

    'common.online': 'ऑनलाइन',
    'common.offline': 'ऑफ़लाइन',
    'common.checking': 'जांच हो रही है…',
    'common.save': 'सहेजें',
    'common.cancel': 'रद्द करें',
    'common.delete': 'हटाएं',
    'common.confirm': 'पुष्टि करें',
    'common.close': 'बंद करें',
    'common.loading': 'लोड हो रहा है…',
    'common.error': 'त्रुटि',
    'common.success': 'सफलता',
    'common.warning': 'चेतावनी',
    'common.info': 'जानकारी',

    'error.selectImage': 'कृपया पहले पत्ती की फोटो चुनें या खींचें।',
    'error.predictionFailed': 'भविष्यवाणी विफल। बैकएंड कनेक्शन जांचें।',
    'error.adviceUnavailable': 'सलाह उपलब्ध नहीं। कृपया कृषि अधिकारी से सलाह लें।',
    'error.feedbackFailed': 'प्रतिक्रिया सबमिट नहीं हो सकी',
    'error.feedbackSuccess': 'प्रतिक्रिया सबमिट की गई — धन्यवाद!',
    'error.offline': 'ऑफ़लाइन चल रहा है — कनेक्ट होने पर छवियाँ अपलोड करें',
    'error.noHistory': 'निर्यात करने के लिए कोई इतिहास नहीं',
    'error.exportSuccess': '{{count}} रिकॉर्ड निर्यात किए गए',
    'error.dataCleared': 'सभी डेटा साफ़ किया गया',
    'error.popupBlocked': 'पॉप-अप अवरुद्ध — प्रिंट करने के लिए पॉप-अप की अनुमति दें',
  },
  // Other languages would follow similar structure - abbreviated for brevity
  bn: {},
  ta: {},
  te: {},
  mr: {},
  gu: {},
  ml: {},
  kn: {},
  pa: {},
};

// Fill missing languages with English fallback
const baseTranslations = translations.en;
(LANGUAGES.filter(l => l.code !== 'en').map(l => l.code) as SupportedLanguage[]).forEach(lang => {
  translations[lang] = { ...baseTranslations, ...translations[lang] };
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('agridoc_lang') as SupportedLanguage) || 'en';
    }
    return 'en';
  });

  useEffect(() => {
    localStorage.setItem('agridoc_lang', language);
  }, [language]);

  const setLanguage = useCallback((lang: SupportedLanguage) => {
    setLanguageState(lang);
  }, []);

  const t = useCallback((key: string, params?: Record<string, string>) => {
    let text = translations[language]?.[key] || translations.en[key] || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(new RegExp(`{{${k}}}`, 'g'), v);
      });
    }
    return text;
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
}