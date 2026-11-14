import { useState, useEffect, useCallback, useMemo } from 'react';
import { Search, Zap, BookOpen, MessageSquare } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useAPI } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';

interface DiseaseEntry {
  name: string;
  raw: string;
  crop: string;
  type: string;
  icon: string;
  desc: string;
}

export default function LibraryView() {
  const { t } = useLanguage();
  const { getClasses, getAdvice } = useAPI();
  const navigate = useNavigate();

  const [diseases, setDiseases] = useState<DiseaseEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [cropFilter, setCropFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedDisease, setSelectedDisease] = useState<DiseaseEntry | null>(null);
  const [advice, setAdvice] = useState<string>('');
  const [loadingAdvice, setLoadingAdvice] = useState(false);

  const extractCrop = (label: string) => label.split('___')[0] || label;
  const extractType = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('healthy')) return 'healthy';
    if (l.includes('blight') || l.includes('rust') || l.includes('scab') || l.includes('mold') || l.includes('rot') || l.includes('powdery')) return 'fungal';
    if (l.includes('bacterial') || l.includes('spot')) return 'bacterial';
    if (l.includes('virus') || l.includes('mosaic')) return 'viral';
    return 'other';
  };
  const typeEmoji = (type: string) => ({ fungal: '🍂', bacterial: '🦠', viral: '🧬', healthy: '✅', other: '🌿' }[type] || '🌿');
  const getDiseaseDesc = (label: string) => {
    const desc: Record<string, string> = {
      "Apple___Apple_scab": "Fungal disease causing olive-green to black spots on leaves and fruit.",
      "Apple___Black_rot": "Fungal infection causing bitter rot and black lesions on fruit.",
      "Apple___Cedar_apple_rust": "Fungal disease with bright orange spots on upper leaf surface.",
      "Blueberry___healthy": "Healthy blueberry plant with no visible disease symptoms.",
      "Cherry___Powdery_mildew": "Fungal disease appearing as white powdery growth on leaves.",
      "Corn___Cercospora_leaf_spot": "Fungal leaf spot causing elongated gray lesions on corn.",
      "Corn___Common_rust": "Fungal disease with rusty brown pustules on leaves.",
      "Corn___Northern_Leaf_Blight": "Fungal disease causing large gray-green lesions on leaves.",
      "Grape___Black_rot": "Fungal disease causing dark sunken rot on berries.",
      "Grape___Esca": "Wood disease causing leaf discoloration and berry decay.",
      "Grape___Leaf_blight": "Fungal leaf blight affecting grapevine foliage.",
      "Orange___Haunglongbing": "Citrus greening — bacterial disease spread by psyllids.",
      "Peach___Bacterial_spot": "Bacterial infection causing water-soaked spots on fruit and leaves.",
      "Pepper___Bacterial_spot": "Bacterial disease causing circular water-soaked lesions.",
      "Potato___Early_blight": "Fungal disease (Alternaria) causing concentric ring spots.",
      "Potato___Late_blight": "Devastating oomycete disease causing dark watery lesions.",
      "Potato___healthy": "Healthy potato plant.",
      "Raspberry___healthy": "Healthy raspberry cane.",
      "Soybean___healthy": "Healthy soybean plant.",
      "Squash___Powdery_mildew": "Fungal disease with white powdery coating on leaves.",
      "Strawberry___Leaf_scorch": "Fungal disease causing purplish-red leaf margins.",
      "Tomato___Bacterial_spot": "Bacterial disease causing small dark water-soaked spots.",
      "Tomato___Early_blight": "Fungal disease with target-spot lesions on lower leaves.",
      "Tomato___Late_blight": "Aggressive oomycete causing rapid leaf decay and fruit rot.",
      "Tomato___Leaf_Mold": "Fungal disease causing yellow blotches on upper leaf surface.",
      "Tomato___Septoria_leaf_spot": "Fungal disease with small circular spots featuring dark edges.",
      "Tomato___Spider_mites": "Pest damage showing stippling and webbing on leaves.",
      "Tomato___Target_Spot": "Fungal disease with target-like concentric rings.",
      "Tomato___Yellow_Leaf_Curl_Virus": "Viral disease curling leaves and stunting growth.",
      "Tomato___Tomato_mosaic_virus": "Viral disease causing mottled mosaic patterns on leaves.",
      "Tomato___healthy": "Healthy tomato plant.",
      "Rice_Blade_Blight": "Fungal blight affecting rice blade leaves.",
      "Leaf_Blight": "General leaf blight affecting various crops.",
      "Healthy": "Plant shows no signs of disease — continues normal care.",
    };
    return desc[label] || "A disease condition affecting this crop. Consult the treatment section for management guidance.";
  };

  const loadLibrary = useCallback(async () => {
    setLoading(true);
    try {
      const classes = await getClasses();
      const entries: DiseaseEntry[] = classes.map(c => ({
        name: c.replace(/___/g, ' '),
        raw: c,
        crop: extractCrop(c),
        type: extractType(c),
        icon: typeEmoji(extractType(c)),
        desc: getDiseaseDesc(c),
      }));
      setDiseases(entries);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load disease library';
      toast.error(message, { id: 'library-error' });
    } finally {
      setLoading(false);
    }
  }, [getClasses]);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  // Get unique crops for filter
  const crops = useMemo(() => [...new Set(diseases.map(d => d.crop))].sort(), [diseases]);

  // Filter diseases
  const filteredDiseases = useMemo(() => {
    return diseases.filter(d => {
      const matchesSearch = !searchQuery ||
        d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.crop.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCrop = !cropFilter || d.crop === cropFilter;
      const matchesType = !typeFilter || d.type === typeFilter;
      return matchesSearch && matchesCrop && matchesType;
    });
  }, [diseases, searchQuery, cropFilter, typeFilter]);

  const handleViewAdvice = async (disease: DiseaseEntry) => {
    setSelectedDisease(disease);
    setLoadingAdvice(true);
    try {
      const lang = localStorage.getItem('agridoc_lang') || 'en';
      const data = await getAdvice(disease.raw, lang);
      setAdvice(data.advice || t('error.adviceUnavailable'));
    } catch {
      setAdvice(t('error.adviceUnavailable'));
    } finally {
      setLoadingAdvice(false);
    }
  };

  const handleDiagnose = (disease: DiseaseEntry) => {
    navigate('/camera', { state: { targetDisease: disease.raw } });
  };

  if (loading) {
    return (
      <section className="view-panel active" id="view-library">
        <div className="view-header">
          <h1>{t('library.title')}</h1>
          <p>{t('library.subtitle')}</p>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
          <div className="loader-area">
            <div className="spinner-ring"></div>
            <div className="loader-text">Loading disease library…</div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="view-panel active" id="view-library">
      <div className="view-header">
        <h1>{t('library.title')}</h1>
        <p>{t('library.subtitle')}</p>
      </div>

      {/* Search & Filters */}
      <div className="lib-controls">
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <Search size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="search"
            id="lib-search"
            className="lib-search-input"
            placeholder={t('library.search')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label={t('library.search')}
          />
        </div>
        <select
          id="lib-filter-crop"
          className="lib-select"
          value={cropFilter}
          onChange={(e) => setCropFilter(e.target.value)}
          aria-label={t('library.filterCrop')}
        >
          <option value="">{t('library.filterCrop')} ({crops.length})</option>
          {crops.map(crop => (
            <option key={crop} value={crop}>{crop}</option>
          ))}
        </select>
        <select
          id="lib-filter-type"
          className="lib-select"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label={t('library.filterType')}
        >
          <option value="">{t('library.filterType')}</option>
          <option value="fungal">{t('library.type.fungal')}</option>
          <option value="bacterial">{t('library.type.bacterial')}</option>
          <option value="viral">{t('library.type.viral')}</option>
          <option value="healthy">{t('library.type.healthy')}</option>
          <option value="other">{t('library.type.other')}</option>
        </select>
      </div>

      {/* Disease Grid */}
      {filteredDiseases.length === 0 ? (
        <div className="empty-state" id="lib-empty" role="status">
          <BookOpen size={48} style={{ marginBottom: '16px', color: 'var(--text-muted)' }} />
          <p>{t('library.empty')}</p>
          <p style={{ fontSize: 'var(--text-sm)', marginTop: '8px' }}>
            {searchQuery && `No results for "${searchQuery}"`}
          </p>
        </div>
      ) : (
        <div className="lib-grid" id="lib-grid" role="list">
          {filteredDiseases.map(disease => (
            <article key={disease.raw} className="lib-card" role="listitem">
              <div className="lib-card-head">
                <span className="lib-card-icon" aria-hidden="true">{disease.icon}</span>
                <div>
                  <div className="lib-card-name">{disease.name}</div>
                  <div className="lib-card-crop">{disease.crop}</div>
                </div>
              </div>
              <div className="lib-card-desc">{disease.desc}</div>
              <div className="lib-card-tags">
                <span className={`type-tag type-${disease.type}`}>
                  {disease.type.charAt(0).toUpperCase() + disease.type.slice(1)}
                </span>
              </div>
              <div className="lib-card-actions">
                <button
                  className="lib-card-btn"
                  onClick={() => handleDiagnose(disease)}
                  disabled={selectedDisease?.raw === disease.raw}
                >
                  <Zap size={14} aria-hidden="true" /> {t('library.diagnose')}
                </button>
                <button
                  className="lib-card-btn"
                  onClick={() => handleViewAdvice(disease)}
                >
                  <MessageSquare size={14} aria-hidden="true" /> {t('library.treatment')}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Advice Modal */}
      {selectedDisease && (
        <div className="overlay" onClick={() => { setSelectedDisease(null); setAdvice(''); }} style={{ zIndex: 200 }}>
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-xl)',
              padding: '24px',
              maxWidth: '520px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: 'var(--shadow-xl)',
              zIndex: 201,
            }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="advice-title"
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '32px' }}>{selectedDisease.icon}</span>
                <div>
                  <h2 id="advice-title" style={{ fontSize: 'var(--text-xl)', color: 'var(--text-primary)' }}>
                    {selectedDisease.name}
                  </h2>
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                    {selectedDisease.crop} · {selectedDisease.type}
                  </p>
                </div>
              </div>
              <button
                onClick={() => { setSelectedDisease(null); setAdvice(''); }}
                style={{
                  background: 'none', border: 'none', color: 'var(--text-muted)',
                  fontSize: '24px', cursor: 'pointer', padding: '4px', lineHeight: 1
                }}
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid var(--border-light)' }}>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                {selectedDisease.desc}
              </p>
            </div>

            <div>
              <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '12px', color: 'var(--text-primary)' }}>
                Treatment Advice
              </h3>
              {loadingAdvice ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '24px' }}>
                  <div className="spinner-ring" style={{ width: '24px', height: '24px' }}></div>
                </div>
              ) : (
                <p style={{ color: 'var(--text-primary)', lineHeight: 'var(--leading-relaxed)', whiteSpace: 'pre-wrap' }}>
                  {advice}
                </p>
              )}
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-light)' }}>
                ⚠️ {t('result.disclaimer')}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
              <button className="btn btn-secondary" onClick={() => handleDiagnose(selectedDisease)}>
                <Zap size={16} /> {t('library.diagnose')}
              </button>
              <button className="btn btn-primary" onClick={() => { setSelectedDisease(null); setAdvice(''); }}>
                {t('common.close')}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}