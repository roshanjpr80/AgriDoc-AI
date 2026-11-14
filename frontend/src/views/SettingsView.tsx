import { useState, useEffect } from 'react';
import { Save, Shield, Trash2, Download, AlertCircle, CheckCircle, Info, ExternalLink, RefreshCw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../contexts/OfflineContext';
import { LANGUAGES } from '../contexts/LanguageContext';
import { toast } from 'react-hot-toast';

export default function SettingsView() {
  const { t, language, setLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const { apiKey, apiBase, setApiKey, setApiBase, isAuthenticated, clearAuth } = useAuth();
  const { isOnline, queuedCount, syncQueue, clearQueue } = useOffline();

  const [settings, setSettings] = useState({
    apiKey,
    apiBase,
    darkMode: theme === 'dark',
    language,
    autoSave: localStorage.getItem('agridoc_autoSave') !== 'false',
    offlineMode: localStorage.getItem('agridoc_offlineMode') === 'true',
    showTips: localStorage.getItem('agridoc_showTips') !== 'false',
  });

  const [saving, setSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Sync settings with context
  useEffect(() => {
    setSettings(s => ({ ...s, apiKey, apiBase, darkMode: theme === 'dark', language }));
  }, [apiKey, apiBase, theme, language]);

  const handleSave = async () => {
    setSaving(true);
    try {
      setApiKey(settings.apiKey);
      setApiBase(settings.apiBase);
      setLanguage(settings.language);
      if (settings.darkMode !== (theme === 'dark')) toggleTheme();
      localStorage.setItem('agridoc_autoSave', settings.autoSave.toString());
      localStorage.setItem('agridoc_offlineMode', settings.offlineMode.toString());
      localStorage.setItem('agridoc_showTips', settings.showTips.toString());
      toast.success(t('common.success') + ': ' + t('settings.subtitle'), { id: 'settings-saved' });
    } catch {
      toast.error(t('common.error'), { id: 'settings-error' });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: string | boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleExportData = () => {
    try {
      const data = {
        history: JSON.parse(localStorage.getItem('agridoc_history') || '[]'),
        settings: {
          apiBase: settings.apiBase,
          language: settings.language,
          darkMode: settings.darkMode,
          autoSave: settings.autoSave,
          offlineMode: settings.offlineMode,
          showTips: settings.showTips,
        },
        queue: JSON.parse(localStorage.getItem('agridoc_queue') || '[]'),
        exportedAt: new Date().toISOString(),
      };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agridoc-backup-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Data exported successfully', { id: 'export-success' });
    } catch {
      toast.error('Export failed', { id: 'export-error' });
    }
  };

  const handleClearAllData = () => {
    if (confirm(t('settings.deleteAll') + '? This will delete all history, settings, and offline queue. This cannot be undone.')) {
      localStorage.clear();
      clearAuth();
      clearQueue();
      toast.success(t('error.dataCleared'), { id: 'clear-success' });
      setTimeout(() => window.location.reload(), 1000);
    }
  };

  const handleSyncQueue = async () => {
    if (!isOnline) {
      toast.error('Cannot sync while offline', { id: 'sync-offline' });
      return;
    }
    try {
      await syncQueue();
      toast.success(`Synced ${queuedCount} items`, { id: 'sync-success' });
    } catch {
      toast.error('Sync failed', { id: 'sync-error' });
    }
  };

  return (
    <section className="view-panel active" id="view-settings" aria-labelledby="settings-title">
      <div className="view-header">
        <h1 id="settings-title">{t('settings.title')}</h1>
        <p>{t('settings.subtitle')}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* Appearance */}
        <section className="card settings-section">
          <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
            <span style={{ fontSize: '24px' }}>🎨</span>
            {t('settings.appearance')}
          </h2>
          <div className="setting-row">
            <div className="setting-info">
              <strong>{t('settings.darkMode')}</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Toggle dark/light theme
              </p>
            </div>
            <button
              className={`toggle-switch ${settings.darkMode ? 'on' : ''}`}
              onClick={() => handleChange('darkMode', !settings.darkMode)}
              role="switch"
              aria-checked={settings.darkMode}
              aria-label={t('settings.darkMode')}
            >
              <span className="toggle-thumb"></span>
            </button>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>{t('settings.language')}</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Select your preferred language
              </p>
            </div>
            <select
              className="setting-input"
              value={settings.language}
              onChange={(e) => handleChange('language', e.target.value as any)}
              style={{ maxWidth: '200px' }}
            >
              {LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.nativeName}
                </option>
              ))}
            </select>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>{t('settings.showTips') || 'Show Tips'}</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Show photography tips on camera view
              </p>
            </div>
            <button
              className={`toggle-switch ${settings.showTips ? 'on' : ''}`}
              onClick={() => handleChange('showTips', !settings.showTips)}
              role="switch"
              aria-checked={settings.showTips}
              aria-label={t('settings.showTips') || 'Show Tips'}
            >
              <span className="toggle-thumb"></span>
            </button>
          </div>
        </section>

        {/* Connection */}
        <section className="card settings-section">
          <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
            <Shield size={24} />
            {t('settings.connection')}
          </h2>
          <div className="setting-row">
            <div className="setting-info" style={{ flex: 1 }}>
              <strong>{t('settings.apiEndpoint')}</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Backend API base URL
              </p>
            </div>
          </div>
          <input
            type="url"
            className="setting-input"
            style={{ width: '100%', marginBottom: '16px' }}
            value={settings.apiBase}
            onChange={(e) => handleChange('apiBase', e.target.value)}
            placeholder="http://localhost:9998"
          />
          <div className="setting-row">
            <div className="setting-info" style={{ flex: 1 }}>
              <strong>API Key</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Your authentication key (agridoc-...)
              </p>
            </div>
          </div>
          <input
            type="password"
            className="setting-input"
            style={{ width: '100%' }}
            value={settings.apiKey}
            onChange={(e) => handleChange('apiKey', e.target.value)}
            placeholder="agridoc-..."
            disabled={!isAuthenticated}
          />
          {isAuthenticated && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--green-600)', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle size={12} /> Connected successfully
            </p>
          )}
        </section>

        {/* Offline & Data */}
        <section className="card settings-section">
          <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
            <span style={{ fontSize: '24px' }}>💾</span>
            {t('settings.dataPrivacy')}
          </h2>
          <div className="setting-row">
            <div className="setting-info">
              <strong>{t('settings.offlineMode')}</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Queue predictions locally when offline
              </p>
            </div>
            <button
              className={`toggle-switch ${settings.offlineMode ? 'on' : ''}`}
              onClick={() => handleChange('offlineMode', !settings.offlineMode)}
              role="switch"
              aria-checked={settings.offlineMode}
              aria-label={t('settings.offlineMode')}
            >
              <span className="toggle-thumb"></span>
            </button>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>{t('settings.autoSave')}</strong>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginTop: '4px' }}>
                Automatically save diagnoses to history
              </p>
            </div>
            <button
              className={`toggle-switch ${settings.autoSave ? 'on' : ''}`}
              onClick={() => handleChange('autoSave', !settings.autoSave)}
              role="switch"
              aria-checked={settings.autoSave}
              aria-label={t('settings.autoSave')}
            >
              <span className="toggle-thumb"></span>
            </button>
          </div>

          <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 'var(--leading-relaxed)' }}>
              {t('settings.privacyDesc')}
            </p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" onClick={handleExportData}>
                <Download size={16} /> Export Data
              </button>
              <button className="btn btn-text-danger" onClick={() => setShowDeleteConfirm(true)}>
                <Trash2 size={16} /> {t('settings.deleteAll')}
              </button>
            </div>
          </div>
        </section>

        {/* Queue Status */}
        <section className="card settings-section">
          <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
            <span style={{ fontSize: '24px' }}>📦</span>
            {t('settings.offlineMode')} Queue
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', padding: '16px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius)' }}>
            <div>
              <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>
                {queuedCount}
              </div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                {queuedCount === 1 ? 'item queued' : 'items queued for sync'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn btn-primary"
                onClick={handleSyncQueue}
                disabled={!isOnline || queuedCount === 0}
              >
                <RefreshCw size={16} /> Sync Now
              </button>
              {queuedCount > 0 && (
                <button className="btn btn-text-danger" onClick={() => {
                  if (confirm('Clear the entire offline queue?')) clearQueue();
                }}>
                  <Trash2 size={16} /> Clear Queue
                </button>
              )}
            </div>
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', lineHeight: 'var(--leading-relaxed)' }}>
            <p><strong>Status:</strong> {isOnline ? 'Online — ready to sync' : 'Offline — will sync when connected'}</p>
            <p style={{ marginTop: '8px' }}><strong>TTL:</strong> 72 hours (configured in sync.yaml)</p>
          </div>
        </section>

        {/* About */}
        <section className="card settings-section" style={{ gridColumn: '1 / -1' }}>
          <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
            <Info size={24} />
            {t('settings.about')}
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
            <div>
              <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '12px', color: 'var(--text-primary)' }}>
                {t('settings.version')}
              </h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>{t('settings.tech')}</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>{t('settings.mission')}</p>
              <div style={{ display: 'flex', gap: '8px' }}>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <ExternalLink size={16} /> GitHub
                </a>
                <a
                  href="https://github.com/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-outline"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <AlertCircle size={16} /> Report Issue
                </a>
              </div>
            </div>
            <div>
              <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '12px', color: 'var(--text-primary)' }}>
                System Info
              </h3>
              <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 16px', fontSize: 'var(--text-sm)' }}>
                <dt style={{ color: 'var(--text-muted)' }}>Model</dt>
                <dd style={{ color: 'var(--text-primary)' }}>EfficientNet-B0 (38 classes)</dd>
                <dt style={{ color: 'var(--text-muted)' }}>Runtime</dt>
                <dd style={{ color: 'var(--text-primary)' }}>ONNX Runtime (CPU)</dd>
                <dt style={{ color: 'var(--text-muted)' }}>Languages</dt>
                <dd style={{ color: 'var(--text-primary)' }}>10 Indian languages</dd>
                <dt style={{ color: 'var(--text-muted)' }}>Offline Queue</dt>
                <dd style={{ color: 'var(--text-primary)' }}>IndexedDB + JSONL (72h TTL)</dd>
                <dt style={{ color: 'var(--text-muted)' }}>Encryption</dt>
                <dd style={{ color: 'var(--text-primary)' }}>Fernet MultiKey (AGRIDOC_DB_KEYS)</dd>
                <dt style={{ color: 'var(--text-muted)' }}>API Auth</dt>
                <dd style={{ color: 'var(--text-primary)' }}>API Key (X-API-Key header)</dd>
              </dl>
            </div>
          </div>
        </section>
      </div>

      {/* Save Button - Fixed at bottom on mobile */}
      <div style={{ position: 'sticky', bottom: '0', padding: '16px 0 0', background: 'var(--bg-primary)', borderTop: '1px solid var(--border-light)', marginTop: '24px' }}>
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
          style={{ width: '100%', maxWidth: '320px', margin: '0 auto', display: 'block' }}
        >
          <Save size={16} /> {saving ? t('common.saving') : t('common.save')}
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="overlay" onClick={() => setShowDeleteConfirm(false)} style={{ zIndex: 200 }}>
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-xl)',
              padding: '32px',
              maxWidth: '480px',
              width: '90%',
              boxShadow: 'var(--shadow-xl)',
              zIndex: 201,
            }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-confirm-title"
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: 48, height: 48, borderRadius: 'var(--radius)',
                background: '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <AlertCircle size={24} color="#dc2626" />
              </div>
              <h2 id="delete-confirm-title" style={{ fontSize: 'var(--text-xl)', color: 'var(--text-primary)' }}>
                {t('settings.deleteAll')}
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 'var(--leading-relaxed)' }}>
              This will permanently delete all your diagnosis history, settings, and offline queue. This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowDeleteConfirm(false)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="btn btn-danger"
                onClick={handleClearAllData}
              >
                <Trash2 size={16} /> {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .settings-section {
          minHeight: fit-content;
        }
        .setting-row {
          display: flex;
          alignItems: center;
          justifyContent: space-between;
          padding: '16px 0';
          borderBottom: '1px solid var(--border-light)';
          gap: 16px;
        }
        .setting-row:last-child {
          borderBottom: none;
        }
        .setting-info {
          flex: 1;
          minWidth: 0;
        }
        .setting-input {
          padding: '10px 12px';
          border: '1px solid var(--border)';
          borderRadius: 'var(--radius)';
          background: 'var(--bg-input)';
          color: 'var(--text-primary)';
          fontSize: 'var(--text-base)';
          outline: none;
          transition: 'border-color var(--transition), box-shadow var(--transition)';
          width: 100%;
          boxSizing: border-box;
        }
        .setting-input:focus {
          borderColor: var(--green-500);
          boxShadow: 0 0 0 3px var(--green-100);
        }
        .toggle-switch {
          position: relative;
          width: 52px;
          height: 28px;
          borderRadius: 14px;
          background: var(--border);
          border: none;
          cursor: pointer;
          transition: background var(--transition);
          flexShrink: 0;
        }
        .toggle-switch.on {
          background: var(--green-600);
        }
        .toggle-switch:focus {
          outline: none;
          boxShadow: 0 0 0 3px var(--green-100);
        }
        .toggle-thumb {
          position: absolute;
          top: 3px;
          left: 3px;
          width: 22px;
          height: 22px;
          borderRadius: 11px;
          background: white;
          boxShadow: 0 2px 4px rgba(0,0,0,0.2);
          transition: transform var(--transition);
        }
        .toggle-switch.on .toggle-thumb {
          transform: translateX(24px);
        }
        @media (max-width: 768px) {
          .setting-row {
            flexDirection: column;
            alignItems: flex-start;
            gap: 8px;
          }
        }
      `}</style>
    </section>
  );
}