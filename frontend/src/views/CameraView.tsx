import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Image, Loader2, AlertCircle, Zap, Shield, Sun, Smartphone } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useAPI } from '../services/api';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'react-hot-toast';

export default function CameraView() {
  const { t } = useLanguage();
  const { predict } = useAPI();
  const {  } = useOffline();
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropzoneRef = useRef<HTMLDivElement>(null);
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };
  }, [previewUrl]);

  const handleFile = useCallback((selectedFile: File) => {
    if (!selectedFile.type.startsWith('image/')) {
      setError(t('error.selectImage'));
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File too large. Maximum 10 MB.');
      return;
    }
    setFile(selectedFile);
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    setError(null);
  }, [t]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFile(droppedFile);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  }, [handleFile]);

  const handleRetake = useCallback(() => {
    setFile(null);
    setPreviewUrl(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const runPredict = useCallback(async () => {
    if (!file) {
      setError(t('error.selectImage'));
      return;
    }

    setLoading(true);
    setError(null);
    setProgress(0);

    // Simulate progress animation
    let pct = 0;
    progressIntervalRef.current = setInterval(() => {
      pct = Math.min(pct + 8, 92);
      setProgress(pct);
    }, 200);

    try {
      const result = await predict(file, { top_k: 3, include_cam: true });
      clearInterval(progressIntervalRef.current!);
      setProgress(100);

      // Navigate to result view with state
      navigate('/result', { state: { result, file: file.name } });
    } catch (err) {
      clearInterval(progressIntervalRef.current!);
      setProgress(0);
      const message = err instanceof Error ? err.message : t('error.predictionFailed');
      setError(message);
      toast.error(message, { id: 'predict-error' });
    } finally {
      setLoading(false);
    }
  }, [file, predict, navigate, t]);

  return (
    <section className="view-panel active" id="view-camera" aria-labelledby="camera-title">
      <div className="view-header">
        <h1 id="camera-title">🌿 {t('camera.title')}</h1>
        <p>{t('camera.subtitle')}</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-msg" role="alert" aria-live="polite">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Zone / Preview */}
      {!previewUrl ? (
        <div
          ref={dropzoneRef}
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(); }}}
          aria-label={t('camera.dropzone')}
        >
          <input
            ref={fileInputRef}
            type="file"
            id="file-input"
            accept="image/*"
            capture="environment"
            hidden
            onChange={handleInputChange}
          />
          <div className="upload-inner">
            <div className="upload-icon" aria-hidden="true">
              <Camera size={48} />
            </div>
            <div className="upload-title">{t('camera.dropzone')}</div>
            <div className="upload-hint">{t('camera.hint')}</div>
            <button
              className="btn btn-lg"
              id="btn-open-camera"
              type="button"
              onClick={(e) => { e.stopPropagation(); handleClick(); }}
            >
              <Camera size={18} aria-hidden="true" /> {t('camera.openCamera')}
            </button>
          </div>
        </div>
      ) : (
        <div className="preview-card" aria-live="polite">
          <img
            id="preview-img"
            src={previewUrl}
            alt="Leaf preview for diagnosis"
            onLoad={() => {}}
          />
          <div className="preview-controls">
            <button
              className="btn btn-secondary"
              id="btn-retake"
              onClick={handleRetake}
              disabled={loading}
            >
              <Image size={16} aria-hidden="true" /> {t('camera.retake')}
            </button>
            <button
              className="btn btn-primary"
              id="btn-diagnose"
              onClick={runPredict}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" aria-hidden="true" />
                  {t('camera.loading')}
                </>
              ) : (
                <>
                  <Zap size={18} aria-hidden="true" />
                  {t('camera.diagnose')}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Loading Area */}
      {loading && (
        <div className="loader-area" aria-live="polite" aria-label={t('camera.loading')}>
          <div className="spinner-ring" aria-hidden="true"></div>
          <div className="loader-text" id="loader-text">{t('camera.loading')}</div>
          <div className="progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Diagnosis progress">
            <div className="progress-fill" id="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
        </div>
      )}

      {/* Quick Tips */}
      <div className="quick-tips" role="list" aria-label="Photography tips for best results">
        <article className="tip-card" role="listitem">
          <span className="tip-emoji" aria-hidden="true">☀️</span>
          <div className="tip-body">
            <strong>{t('camera.tip.lighting').split(' — ')[0]}</strong>
            <br />
            {t('camera.tip.lighting').split(' — ')[1]}
          </div>
        </article>
        <article className="tip-card" role="listitem">
          <span className="tip-emoji" aria-hidden="true">🎯</span>
          <div className="tip-body">
            <strong>{t('camera.tip.focus').split(' — ')[0]}</strong>
            <br />
            {t('camera.tip.focus').split(' — ')[1]}
          </div>
        </article>
        <article className="tip-card" role="listitem">
          <span className="tip-emoji" aria-hidden="true">📱</span>
          <div className="tip-body">
            <strong>{t('camera.tip.offline').split(' — ')[0]}</strong>
            <br />
            {t('camera.tip.offline').split(' — ')[1]}
          </div>
        </article>
        <article className="tip-card" role="listitem">
          <span className="tip-emoji" aria-hidden="true">🔒</span>
          <div className="tip-body">
            <strong>{t('camera.tip.privacy').split(' — ')[0]}</strong>
            <br />
            {t('camera.tip.privacy').split(' — ')[1]}
          </div>
        </article>
      </div>

      {/* Feature Highlights */}
      <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--border-light)' }}>
        <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: '16px', color: 'var(--text-primary)' }}>
          Why AgriDoc AI?
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <FeatureCard icon={<Zap size={24} />} title="Instant AI Diagnosis" desc="EfficientNet-B0 ONNX model runs in milliseconds on CPU" />
          <FeatureCard icon={<Smartphone size={24} />} title="Works Offline" desc="Queue predictions locally, sync when connection returns" />
          <FeatureCard icon={<Shield size={24} />} title="Privacy First" desc="Photos never leave your device; encrypted local storage" />
          <FeatureCard icon={<Sun size={24} />} title="10 Languages" desc="Supports Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Malayalam, Kannada, Punjabi" />
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
      padding: '20px', background: 'var(--bg-card)', border: '1px solid var(--border-light)',
      borderRadius: 'var(--radius-lg)', transition: 'all var(--transition)'
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: 'var(--radius)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', marginBottom: '12px',
        background: 'var(--green-50)', color: 'var(--green-600)'
      }}>
        {icon}
      </div>
      <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
        {title}
      </h4>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
        {desc}
      </p>
    </div>
  );
}