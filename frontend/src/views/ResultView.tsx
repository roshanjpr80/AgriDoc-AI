import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Camera, BookOpen, MessageSquare, Share2, Download, Printer, AlertCircle } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useAPI } from '../services/api';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'react-hot-toast';
import { format } from 'date-fns';

interface Prediction {
  class: string;
  confidence: number;
}

interface ResultData {
  diagnosis: string;
  confidence: number;
  predictions: Prediction[];
  uncertain: boolean;
  confidence_floor: number;
  gradcam_url?: string;
  advice?: string;
  advice_source?: string;
  disclaimer?: string;
}

export default function ResultView() {
  const { t } = useLanguage();
  const { getAdvice, submitFeedback } = useAPI();
  const {  } = useOffline();
  const navigate = useNavigate();
  const location = useLocation();

  const [result, setResult] = useState<ResultData | null>(null);
  const [advice, setAdvice] = useState<string>('');
  const [adviceSource, setAdviceSource] = useState<string>('');
  const [disclaimer, setDisclaimer] = useState<string>('');
  const [loadingAdvice, setLoadingAdvice] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sharing, setSharing] = useState(false);

  // Get result from navigation state
  useEffect(() => {
    const state = location.state as { result?: ResultData; file?: string } | undefined;
    if (state?.result) {
      setResult(state.result);
      fetchAdvice(state.result.diagnosis);
    } else {
      // No result, go back to camera
      navigate('/camera', { replace: true });
    }
  }, [location, navigate]);

  const fetchAdvice = useCallback(async (classLabel: string) => {
    setLoadingAdvice(true);
    try {
      const lang = localStorage.getItem('agridoc_lang') || 'en';
      const data = await getAdvice(classLabel, lang);
      setAdvice(data.advice || '');
      setAdviceSource(data.source ? `${t('result.adviceSource')}: ${data.source}` : '');
      setDisclaimer(data.disclaimer || t('result.disclaimer'));
    } catch {
      setAdvice(t('error.adviceUnavailable'));
      setAdviceSource('');
      setDisclaimer(t('result.disclaimer'));
    } finally {
      setLoadingAdvice(false);
    }
  }, [getAdvice, t]);

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

  const handleSave = async () => {
    if (!result) return;
    setSaving(true);
    try {
      // Save to localStorage history
      const history = JSON.parse(localStorage.getItem('agridoc_history') || '[]');
      const top = result.predictions[0];
      history.unshift({
        id: Date.now(),
        date: new Date().toISOString(),
        class: top.class,
        confidence: top.confidence,
        uncertain: result.uncertain,
        advice,
      });
      localStorage.setItem('agridoc_history', JSON.stringify(history.slice(0, 50)));
      toast.success(t('common.success') + ': ' + t('result.save'), { id: 'save-result' });
    } catch {
      toast.error(t('common.error'), { id: 'save-error' });
    } finally {
      setSaving(false);
    }
  };

  const handleShare = async () => {
    if (!result) return;
    setSharing(true);
    try {
      const top = result.predictions[0];
      const text = `AgriDoc AI Diagnosis\nDisease: ${top.class}\nConfidence: ${Math.round(top.confidence * 100)}%\nDate: ${format(new Date(), 'PPpp')}`;
      if (navigator.share) {
        await navigator.share({ title: 'AgriDoc AI Diagnosis', text });
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        toast.success('Copied to clipboard', { id: 'share-success' });
      }
    } catch {
      toast.error('Could not share', { id: 'share-error' });
    } finally {
      setSharing(false);
    }
  };

  const handleReportMiss = () => {
    if (!result) return;
    const reason = prompt(t('result.reportMiss') + '\n\n' + '(e.g. image quality, wrong class, different disease):');
    if (!reason) return;
    submitFeedback(result.diagnosis, false, reason)
      .then(() => toast.success(t('error.feedbackSuccess'), { id: 'feedback-success' }))
      .catch(() => toast.error(t('error.feedbackFailed'), { id: 'feedback-error' }));
  };

  const handlePrint = () => {
    if (!result) return;
    const top = result.predictions[0];
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toast.error(t('error.popupBlocked'), { id: 'print-error' });
      return;
    }
    const doc = printWindow.document;
    doc.open();
    doc.write('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>AgriDoc AI - Diagnosis Report</title></head><body></body></html>');
    doc.close();

    const style = doc.createElement('style');
    style.textContent = `
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: system-ui, sans-serif; padding: 40px; max-width: 620px; margin: 0 auto; color: #1a2e1a; }
      h1 { color: #1b7a31; margin-bottom: 16px; font-size: 22px; }
      .table { width: 100%; border-collapse: collapse; margin: 16px 0; }
      td, th { padding: 10px 12px; border-bottom: 1px solid #ddd; text-align: left; font-size: 14px; }
      .note { color: #555; font-size: 12px; margin-top: 24px; padding: 12px; background: #f9f9f9; border-left: 3px solid #f59e0b; line-height: 1.5; }
      @media print { body { padding: 0; } }
    `;
    doc.head.appendChild(style);

    const body = doc.body;
    const h1 = doc.createElement('h1');
    h1.textContent = '🌾 AgriDoc AI — Diagnosis Report';
    body.appendChild(h1);

    const dateP = doc.createElement('p');
    dateP.style.cssText = 'color:#666;font-size:13px;margin-bottom:16px';
    dateP.textContent = `Date: ${format(new Date(), 'PPpp')}`;
    body.appendChild(dateP);

    const table = doc.createElement('table');
    table.className = 'table';
    const tbody = doc.createElement('tbody');
    const rows = [
      ['Disease', top.class.replace(/___/g, ' ')],
      ['Confidence', `${Math.round(top.confidence * 100)}%`],
      ['Status', result.uncertain ? 'Uncertain — re-take recommended' : 'Confident diagnosis'],
    ];
    rows.forEach(([th, td]) => {
      const tr = doc.createElement('tr');
      const thEl = doc.createElement('th');
      thEl.style.width = '120px';
      thEl.textContent = th;
      const tdEl = doc.createElement('td');
      tdEl.innerHTML = `<strong>${td}</strong>`;
      tr.appendChild(thEl);
      tr.appendChild(tdEl);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    body.appendChild(table);

    if (advice) {
      const adviceDiv = doc.createElement('div');
      adviceDiv.style.marginTop = '24px';
      const h3 = doc.createElement('h3');
      h3.textContent = 'Treatment Advice';
      adviceDiv.appendChild(h3);
      const p = doc.createElement('p');
      p.textContent = advice;
      adviceDiv.appendChild(p);
      body.appendChild(adviceDiv);
    }

    const noteP = doc.createElement('p');
    noteP.className = 'note';
    noteP.innerHTML = '⚠️ This is AI-generated guidance, not a substitute for professional agricultural advice. Consult a local agriculture officer before applying any treatment.';
    body.appendChild(noteP);

    printWindow.print();
  };

  const handleNewDiagnosis = () => {
    navigate('/camera', { replace: true });
  };

  const handleChatAbout = () => {
    if (!result) return;
    const top = result.predictions[0];
    navigate('/chat', { state: { initialQuery: `Tell me about ${top.class.replace(/___/g, ' ').toLowerCase()} treatment` } });
  };

  const handleViewInLibrary = () => {
    if (!result) return;
    navigate('/library', { state: { filter: result.diagnosis } });
  };

  if (!result) {
    return (
      <section className="view-panel active" id="view-result">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
          <div className="loader-area">
            <div className="spinner-ring"></div>
            <div className="loader-text">Loading result…</div>
          </div>
        </div>
      </section>
    );
  }

  const top = result.predictions[0];
  const pct = Math.round(top.confidence * 100);
  const confClass = pct >= 80 ? 'conf-high' : pct >= 60 ? 'conf-medium' : 'conf-low';
  const statusText = result.uncertain ? t('result.uncertain') : t('result.confident');
  const statusColor = result.uncertain ? 'var(--amber-500)' : 'var(--green-600)';

  return (
    <section className="view-panel active" id="view-result" aria-labelledby="result-title">
      <div className="view-header row-between">
        <div>
          <h1 id="result-title">{t('result.title')}</h1>
          <p id="result-date">{format(new Date(), 'PPpp')}</p>
        </div>
        <button className="btn btn-secondary" id="btn-new-diag" onClick={handleNewDiagnosis}>
          <Camera size={16} aria-hidden="true" /> {t('result.newDiagnosis')}
        </button>
      </div>

      <div className="result-layout">
        <div className="result-main card" id="result-main">
          <div className="result-hero" id="result-hero">
            <div className="result-icon" id="result-icon" aria-hidden="true">
              {typeEmoji(extractType(top.class))}
            </div>
            <div className="result-meta-result">
              <h2 className="result-disease-name" id="result-disease">
                {top.class.replace(/___/g, ' ')}
              </h2>
              <p className="result-crop-hint" id="result-crop">
                {extractCrop(top.class)} · {extractType(top.class)}
              </p>
            </div>
            <div className={`conf-badge ${confClass}`} id="conf-badge" aria-label={`${pct}% confidence`}>
              {pct}%
            </div>
          </div>

          <div className="conf-bar-wrap">
            <div className="conf-bar-label">
              <span>{t('result.confidence')}</span>
              <span id="conf-pct-label">{pct}%</span>
            </div>
            <div className="conf-bar-track">
              <div
                className="conf-bar-fill"
                id="conf-bar-fill"
                style={{
                  width: `${pct}%`,
                  background: pct >= 80 ? 'var(--green-500)' : pct >= 60 ? 'var(--amber-500)' : 'var(--red-500)'
                }}
              ></div>
            </div>
            <div className="conf-status" id="conf-status" style={{ color: statusColor }}>
              {result.uncertain ? '⚠️' : '✅'} {statusText}
            </div>
          </div>

          <h3 className="section-title">{t('result.topPredictions')}</h3>
          <div className="pred-list" id="pred-list" role="list">
            {result.predictions.map((p, i) => (
              <div key={p.class} className="pred-row" role="listitem">
                <span className="pred-class">
                  {i === 0 ? '🏆 ' : ''}{p.class.replace(/___/g, ' ')}
                </span>
                <div className="pred-bar-bg">
                  <div className="pred-bar-fg" style={{ width: `${Math.round(p.confidence * 100)}%` }}></div>
                </div>
                <span className="pred-pct">{Math.round(p.confidence * 100)}%</span>
              </div>
            ))}
          </div>

          <div className="advice-block card" id="advice-block">
            <h3 className="section-title">🌿 {t('result.treatmentAdvice')}</h3>
            {loadingAdvice ? (
              <div className="loader-area" style={{ padding: '20px' }}>
                <div className="spinner-ring" style={{ width: '24px', height: '24px', margin: '0 auto 12px' }}></div>
                <div className="loader-text" style={{ fontSize: 'var(--text-sm)' }}>Loading advice…</div>
              </div>
            ) : (
              <>
                <p className="advice-text" id="advice-text">{advice || 'No advice available.'}</p>
                {adviceSource && <div className="advice-source" id="advice-source">{adviceSource}</div>}
                <div className="disclaimer-text" id="disclaimer-text">
                  ⚠️ {disclaimer}
                </div>
              </>
            )}
          </div>

          <div className="result-actions">
            <button className="btn btn-outline" id="btn-save-result" onClick={handleSave} disabled={saving}>
              <Download size={16} aria-hidden="true" /> {saving ? t('common.saving') : t('result.save')}
            </button>
            <button className="btn btn-link" id="btn-share-result" onClick={handleShare} disabled={sharing}>
              <Share2 size={16} aria-hidden="true" /> {sharing ? t('common.sharing') : t('result.share')}
            </button>
            <button className="btn btn-text-danger" id="btn-report-miss" onClick={handleReportMiss}>
              <AlertCircle size={16} aria-hidden="true" /> {t('result.reportMiss')}
            </button>
          </div>
        </div>

        <div className="result-sidebar">
          <div className="card info-card">
            <h3>{t('result.quickActions')}</h3>
            <button className="action-btn" id="btn-chat-about-result" onClick={handleChatAbout}>
              <MessageSquare size={18} aria-hidden="true" /> {t('result.askAbout')}
            </button>
            <button className="action-btn" id="btn-library-this-disease" onClick={handleViewInLibrary}>
              <BookOpen size={18} aria-hidden="true" /> {t('result.viewLibrary')}
            </button>
            <button className="action-btn" id="btn-print-report" onClick={handlePrint}>
              <Printer size={18} aria-hidden="true" /> {t('result.print')}
            </button>
          </div>
          <div className="card info-card" id="related-cards">
            <h3>{t('result.relatedDiseases')}</h3>
            <div id="related-list">
              {result.predictions.slice(1).map(p => (
                <div
                  key={p.class}
                  className="related-item"
                  onClick={() => navigate('/library', { state: { filter: p.class } })}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate('/library', { state: { filter: p.class } }); }}
                >
                  <span>{p.class.replace(/___/g, ' ')}</span>
                  <span>{Math.round(p.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}