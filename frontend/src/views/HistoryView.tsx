import { useState, useEffect, useCallback } from 'react';
import { Download, Trash2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { toast } from 'react-hot-toast';

interface HistoryItem {
  id: number;
  date: string;
  class: string;
  confidence: number;
  uncertain: boolean;
  advice: string;
}

export default function HistoryView() {
  const { t } = useLanguage();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadHistory = useCallback(() => {
    try {
      const stored = localStorage.getItem('agridoc_history');
      if (stored) {
        setHistory(JSON.parse(stored));
      }
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleExport = async () => {
    if (history.length === 0) {
      toast.error(t('error.noHistory'), { id: 'export-error' });
      return;
    }
    try {
      const blob = new Blob([JSON.stringify(history, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agridoc-history-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(t('error.exportSuccess').replace('{{count}}', history.length.toString()), { id: 'export-success' });
    } catch {
      toast.error('Export failed', { id: 'export-failed' });
    }
  };

  const handleDelete = (id: number) => {
    if (confirm(t('common.confirm') + ': ' + t('common.delete') + '?')) {
      setHistory(prev => prev.filter(item => item.id !== id));
      localStorage.setItem('agridoc_history', JSON.stringify(history.filter(item => item.id !== id)));
      toast.success(t('common.success'), { id: 'delete-success' });
    }
  };

  const handleClearAll = () => {
    if (confirm(t('settings.deleteAll') + '? This cannot be undone.')) {
      setHistory([]);
      localStorage.removeItem('agridoc_history');
      toast.success(t('error.dataCleared'), { id: 'clear-success' });
    }
  };

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

  return (
    <section className="view-panel active" id="view-history" aria-labelledby="history-title">
      <div className="view-header row-between">
        <div>
          <h1 id="history-title">{t('history.title')}</h1>
          <p>{t('history.subtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {history.length > 0 && (
            <button className="btn btn-secondary" onClick={handleExport}>
              <Download size={16} /> {t('history.export')}
            </button>
          )}
          {history.length > 0 && (
            <button className="btn btn-text-danger" onClick={handleClearAll}>
              <Trash2 size={16} /> {t('nav.clearData')}
            </button>
          )}
        </div>
      </div>

      {history.length === 0 ? (
        <div className="empty-state" id="history-empty" role="status">
          <AlertCircle size={48} style={{ marginBottom: '16px', color: 'var(--text-muted)' }} />
          <p>{t('history.empty')}</p>
          <p style={{ fontSize: 'var(--text-sm)', marginTop: '8px', color: 'var(--text-muted)' }}>
            Diagnoses are saved locally on this device for your reference.
          </p>
        </div>
      ) : (
        <div className="card" style={{ overflow: 'hidden' }}>
          <div className="history-list" role="list">
            {history.map((item) => {
              const isExpanded = expandedId === item.id;
              const type = extractType(item.class);
              return (
                <article
                  key={item.id}
                  className={`history-item ${isExpanded ? 'expanded' : ''}`}
                  role="listitem"
                >
                  <div className="history-item-main" onClick={() => setExpandedId(isExpanded ? null : item.id)}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className="history-icon" aria-hidden="true">{typeEmoji(type)}</span>
                      <div>
                        <div className="history-disease">{item.class.replace(/___/g, ' ')}</div>
                        <div className="history-meta">
                          <span>{extractCrop(item.class)}</span>
                          <span>·</span>
                          <span style={{ textTransform: 'capitalize' }}>{type}</span>
                          <span>·</span>
                          <span>{new Date(item.date).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div className={`conf-badge ${item.confidence >= 80 ? 'conf-high' : item.confidence >= 60 ? 'conf-medium' : 'conf-low'}`}>
                        {Math.round(item.confidence * 100)}%
                      </div>
                      <button
                        className="expand-btn"
                        onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : item.id); }}
                        aria-expanded={isExpanded}
                        aria-label={isExpanded ? 'Collapse' : 'Expand'}
                      >
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="history-item-detail">
                      <div className="detail-section">
                        <h4>{t('history.details')}</h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                          <div><strong>Date:</strong> <span>{new Date(item.date).toLocaleString()}</span></div>
                          <div><strong>Crop:</strong> <span>{extractCrop(item.class)}</span></div>
                          <div><strong>Disease:</strong> <span>{item.class.replace(/___/g, ' ')}</span></div>
                          <div><strong>Type:</strong> <span style={{ textTransform: 'capitalize' }}>{type}</span></div>
                          <div><strong>Confidence:</strong> <span>{Math.round(item.confidence * 100)}%</span></div>
                          <div><strong>Status:</strong> <span>{item.uncertain ? 'Uncertain' : 'Confident'}</span></div>
                        </div>
                      </div>
                      {item.advice && (
                        <div className="detail-section">
                          <h4>Treatment Advice</h4>
                          <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-primary)', lineHeight: 'var(--leading-relaxed)' }}>
                            {item.advice}
                          </p>
                        </div>
                      )}
                      <div className="detail-actions">
                        <button
                          className="btn btn-text-danger"
                          onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }}
                        >
                          <Trash2 size={14} /> {t('history.delete')}
                        </button>
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}