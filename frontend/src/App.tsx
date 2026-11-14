import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useTheme } from './contexts/ThemeContext';
import { useLanguage } from './contexts/LanguageContext';
import { useAuth } from './contexts/AuthContext';
import { useOffline } from './contexts/OfflineContext';
import { toast } from 'react-hot-toast';
import Layout from './components/Layout';
import CameraView from './views/CameraView';
import ResultView from './views/ResultView';
import DashboardView from './views/DashboardView';
import LibraryView from './views/LibraryView';
import HistoryView from './views/HistoryView';
import ChatView from './views/ChatView';
import SettingsView from './views/SettingsView';
import { Camera, MessageSquare, LayoutDashboard, BookOpen, History, Settings } from 'lucide-react';

function ProtectedRoutes() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/settings" replace />;
  }

  return (
    <Routes>
      <Route path="/camera" element={<CameraView />} />
      <Route path="/result" element={<ResultView />} />
      <Route path="/dashboard" element={<DashboardView />} />
      <Route path="/library" element={<LibraryView />} />
      <Route path="/history" element={<HistoryView />} />
      <Route path="/chat" element={<ChatView />} />
      <Route path="/settings" element={<SettingsView />} />
      <Route path="/" element={<Navigate to="/camera" replace />} />
      <Route path="*" element={<Navigate to="/camera" replace />} />
    </Routes>
  );
}

function UnauthenticatedView({ navItems, showAuthError, onDismissAuthError, t }: {
  navItems: { path: string; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }[];
  showAuthError: boolean;
  onDismissAuthError: () => void;
  t: (key: string) => string;
}) {
  return (
    <div className="app-shell">
      <Layout navItems={navItems} showAuthError={showAuthError} onDismissAuthError={onDismissAuthError} />
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        minHeight: '60vh', padding: '40px 20px', textAlign: 'center'
      }}>
        <div style={{
          width: 80, height: 80, borderRadius: '20px',
          background: 'linear-gradient(135deg, var(--green-500), var(--green-700))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: '24px', fontSize: '36px'
        }}>
          🌾
        </div>
        <h1 style={{ fontSize: 'var(--text-4xl)', marginBottom: '12px', color: 'var(--text-primary)' }}>
          AgriDoc AI
        </h1>
        <p style={{ fontSize: 'var(--text-xl)', color: 'var(--text-muted)', marginBottom: '32px', maxWidth: '400px' }}>
          {t('settings.mission')}
        </p>
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-lg)', padding: '24px', maxWidth: '400px', width: '100%',
          textAlign: 'left', boxShadow: 'var(--shadow-lg)'
        }}>
          <h3 style={{ marginBottom: '16px', color: 'var(--text-primary)' }}>Setup Required</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Please configure your API key in Settings to connect to the AgriDoc AI backend.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={() => window.location.href = '/settings'}
              className="btn btn-primary"
            >
              Go to Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const { theme } = useTheme();
  const { t } = useLanguage();
  const { isAuthenticated, apiKey, apiBase } = useAuth();
  const { isOnline, queuedCount, syncQueue } = useOffline();

  const [showAuthError, setShowAuthError] = useState(false);

  // Check connection on mount and periodically
  useEffect(() => {
    const abortController = new AbortController();
    const checkAuth = async () => {
      if (!apiKey) {
        setShowAuthError(true);
        toast.error(t('common.error') + ': API key not configured', { id: 'auth-error' });
        return;
      }
      try {
        const res = await fetch(`${apiBase}/health`, {
          headers: { 'X-API-Key': apiKey },
          signal: abortController.signal,
          cache: 'no-store'
        });
        if (!res.ok && res.status === 401) {
          setShowAuthError(true);
          toast.error(t('common.error') + ': Invalid API key', { id: 'auth-error' });
        }
      } catch {
        // Network error - will be handled by offline context
      }
    };
    checkAuth();
    return () => abortController.abort();
  }, [apiKey, apiBase, t]);

  // Auto-sync when coming online
  useEffect(() => {
    if (isOnline && queuedCount > 0) {
      const sync = async () => {
        try {
          await syncQueue();
          toast.success(`${t('common.success')}: ${t('error.exportSuccess')?.replace('{{count}}', queuedCount.toString()) || `${queuedCount} items synced`}`, { id: 'sync-success' });
        } catch {
          toast.error(t('error.predictionFailed'), { id: 'sync-error' });
        }
      };
      sync();
    }
  }, [isOnline, queuedCount, syncQueue, t]);

  // Show offline indicator
  useEffect(() => {
    if (!isOnline) {
      toast(t('error.offline'), { icon: '⚠️', id: 'offline-notice', duration: 10000 });
    } else {
      toast.dismiss('offline-notice');
    }
  }, [isOnline, t]);

  const navItems = [
    { path: '/camera', label: t('nav.diagnose'), icon: Camera, exact: true },
    { path: '/chat', label: t('nav.chat'), icon: MessageSquare },
    { path: '/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard },
    { path: '/library', label: t('nav.library'), icon: BookOpen },
    { path: '/history', label: t('nav.history'), icon: History },
    { path: '/settings', label: t('nav.settings'), icon: Settings },
  ];

  return (
    <div className="app-shell" data-theme={theme}>
      <Layout navItems={navItems} showAuthError={showAuthError} onDismissAuthError={() => setShowAuthError(false)}>
        {isAuthenticated ? <ProtectedRoutes /> : <UnauthenticatedView navItems={navItems} showAuthError={showAuthError} onDismissAuthError={() => setShowAuthError(false)} t={t} />}
      </Layout>
    </div>
  );
}

export default App;