import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, Database, Target, Activity, Leaf, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useAPI } from '../services/api';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

interface ModelInfo {
  runtime: string;
  classes: number;
  confidence_floor: number;
  input_size: number;
  model_version: string;
}

export default function DashboardView() {
  const { t } = useLanguage();
  const { getModelInfo, getClasses, getHealth } = useAPI();
  const { isOnline, queuedCount, syncQueue } = useOffline();
  const navigate = useNavigate();

  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [classes, setClasses] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historyCount, setHistoryCount] = useState(0);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [info, classesData] = await Promise.all([
        getModelInfo(),
        getClasses(),
      ]);
      setModelInfo(info);
      setClasses(classesData);
      setHistoryCount(JSON.parse(localStorage.getItem('agridoc_history') || '[]').length);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard';
      setError(message);
      toast.error(message, { id: 'dashboard-error' });
    } finally {
      setLoading(false);
    }
  }, [getModelInfo, getClasses, getHealth]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const extractCrop = (label: string) => label.split('___')[0] || label;
  const extractType = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('healthy')) return 'healthy';
    if (l.includes('blight') || l.includes('rust') || l.includes('scab') || l.includes('mold') || l.includes('rot') || l.includes('powdery')) return 'fungal';
    if (l.includes('bacterial') || l.includes('spot')) return 'bacterial';
    if (l.includes('virus') || l.includes('mosaic')) return 'viral';
    return 'other';
  };

  const crops = [...new Set(classes.map(extractCrop))].sort();

  if (loading) {
    return (
      <section className="view-panel active" id="view-dashboard">
        <div className="view-header">
          <h1>{t('dashboard.title')}</h1>
          <p>{t('dashboard.subtitle')}</p>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
          <div className="loader-area">
            <div className="spinner-ring"></div>
            <div className="loader-text">Loading dashboard…</div>
          </div>
        </div>
      </section>
    );
  }

  if (error && !modelInfo) {
    return (
      <section className="view-panel active" id="view-dashboard">
        <div className="view-header">
          <h1>{t('dashboard.title')}</h1>
          <p>{t('dashboard.subtitle')}</p>
        </div>
        <div className="card" style={{ maxWidth: '480px', margin: '0 auto', textAlign: 'center', padding: '40px' }}>
          <AlertCircle size={48} color="var(--red-500)" style={{ marginBottom: '16px' }} />
          <h3 style={{ marginBottom: '12px' }}>Unable to Load Dashboard</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>{error}</p>
          <button className="btn btn-primary" onClick={loadDashboard}>
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="view-panel active" id="view-dashboard">
      <div className="view-header row-between">
        <div>
          <h1>{t('dashboard.title')}</h1>
          <p>{t('dashboard.subtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn btn-secondary"
            onClick={loadDashboard}
            disabled={loading}
            aria-label="Refresh dashboard"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
          {queuedCount > 0 && (
            <button
              className="btn btn-primary"
              onClick={async () => {
                try {
                  await syncQueue();
                  toast.success(`${t('common.success')}: Synced ${queuedCount} items`);
                  loadDashboard();
                } catch {
                  toast.error(t('error.predictionFailed'));
                }
              }}
            >
              <Activity size={16} /> Sync Queue ({queuedCount})
            </button>
          )}
        </div>
      </div>

      {/* Stats Row */}
      <div className="stats-row" id="stats-row">
        <StatTile
          icon={<Leaf size={28} />}
          value={modelInfo?.runtime || 'ONNX'}
          label={t('dashboard.modelRuntime')}
          color="var(--green-600)"
        />
        <StatTile
          icon={<Database size={28} />}
          value={modelInfo?.classes || classes.length || '—'}
          label={t('dashboard.diseaseClasses')}
          color="var(--blue-500)"
        />
        <StatTile
          icon={<Target size={28} />}
          value={`${Math.round((modelInfo?.confidence_floor || 0.7) * 100)}%`}
          label={t('dashboard.confidenceFloor')}
          color="var(--amber-500)"
        />
        <StatTile
          icon={<TrendingUp size={28} />}
          value={historyCount}
          label={t('dashboard.myDiagnoses')}
          color="var(--purple-500)"
        />
      </div>

      {/* Connection Status Card */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: 48, height: 48, borderRadius: 'var(--radius)',
              background: isOnline ? 'var(--green-50)' : '#fef2f2',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              {isOnline ? <CheckCircle size={24} color="var(--green-600)" /> : <AlertCircle size={24} color="#dc2626" />}
            </div>
            <div>
              <h3 style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}>
                {isOnline ? t('common.online') : t('common.offline')}
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                {isOnline
                  ? 'Backend connected — ready for predictions'
                  : 'Running offline — predictions will queue locally'}
              </p>
            </div>
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            API: {localStorage.getItem('agridoc_api_base') || 'http://localhost:9998'}
          </div>
        </div>
      </div>

      {/* Supported Crops */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 className="section-title" style={{ padding: '20px 24px 0', margin: 0 }}>{t('dashboard.supportedCrops')}</h3>
        <div className="crop-grid" style={{ padding: '16px 24px 24px' }}>
          {crops.map(crop => (
            <button
              key={crop}
              className="crop-item"
              onClick={() => navigate('/library', { state: { filterCrop: crop } })}
              style={{ cursor: 'pointer' }}
            >
              {crop}
            </button>
          ))}
        </div>
      </div>

      {/* All Disease Classes Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 24px 0', margin: 0 }}>
          <h3 className="section-title" style={{ margin: 0 }}>{t('dashboard.allClasses')}</h3>
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            {classes.length} classes
          </span>
        </div>
        <div className="class-table-wrap" style={{ padding: '0 24px 24px' }}>
          <table className="class-table" role="table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Class Name</th>
                <th scope="col">Crop</th>
                <th scope="col">Type</th>
              </tr>
            </thead>
            <tbody id="class-tbody">
              {classes.map((c, i) => {
                const crop = extractCrop(c);
                const type = extractType(c);
                return (
                  <tr key={c}>
                    <td>{i + 1}</td>
                    <td>
                      <strong>{c.replace(/___/g, ' ')}</strong>
                    </td>
                    <td>{crop}</td>
                    <td>
                      <span className={`type-tag type-${type}`}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function StatTile({ icon, value, label, color }: {
  icon: React.ReactNode;
  value: string | number;
  label: string;
  color: string;
}) {
  return (
    <div className="stat-tile">
      <div style={{
        width: 48, height: 48, borderRadius: 'var(--radius)',
        background: `${color}15`, color,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 12px'
      }}>
        {icon}
      </div>
      <div className="stat-num" style={{ color }}>{value}</div>
      <div className="stat-lbl">{label}</div>
    </div>
  );
}