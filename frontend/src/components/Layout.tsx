import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { X, Menu, Sun, Moon, Globe, AlertCircle, Settings } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../contexts/OfflineContext';
import { LANGUAGES } from '../contexts/LanguageContext';
import { toast } from 'react-hot-toast';

interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  exact?: boolean;
}

interface LayoutProps {
  navItems: NavItem[];
  showAuthError?: boolean;
  onDismissAuthError?: () => void;
  children?: React.ReactNode;
}

export default function Layout({ navItems, showAuthError, onDismissAuthError, children }: LayoutProps) {
  const { theme, toggleTheme } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const { apiKey, apiBase, setApiKey, setApiBase, isAuthenticated } = useAuth();
  const { isOnline, queuedCount } = useOffline();
  const location = useLocation();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);
  const [settingsApiKey, setSettingsApiKey] = useState(apiKey);
  const [settingsApiBase, setSettingsApiBase] = useState(apiBase);

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Focus search input when opened
  useEffect(() => {
    if (searchOpen && searchRef.current) {
      searchRef.current.focus();
    }
  }, [searchOpen]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigate to library with search query
      window.location.href = `/library?q=${encodeURIComponent(searchQuery.trim())}`;
      setSearchOpen(false);
      setSearchQuery('');
    }
  };

  const handleSaveSettings = () => {
    setApiKey(settingsApiKey);
    setApiBase(settingsApiBase);
    toast.success(t('common.success') + ': Settings saved');
    onDismissAuthError?.();
  };

  return (
    <>
      {/* Header */}
      <header className="topbar" role="banner">
        <div className="brand-area">
          <button
            className="hamburger"
            id="menu-btn"
            aria-label={t('common.menu') || 'Menu'}
            onClick={() => setSidebarOpen(true)}
            aria-expanded={sidebarOpen}
            aria-controls="sidebar"
          >
            <Menu size={24} />
          </button>
          <div className="logo-wrap" aria-hidden="true">
            <span className="logo-icon">🌾</span>
          </div>
          <div className="brand-text">
            <span className="brand-name">AgriDoc AI</span>
            <span className="brand-sub">{t('settings.mission')}</span>
          </div>
        </div>

        <div className="topbar-center">
          <form className="search-wrap" id="global-search-wrap" onSubmit={handleSearchSubmit}>
            <span className="s-icon" aria-hidden="true">
              <Globe size={18} style={{ transform: 'translateY(-50%)', position: 'absolute', left: '14px', top: '50%' }} />
            </span>
            <input
              ref={searchRef}
              id="global-search"
              type="search"
              placeholder={t('library.search')}
              autoComplete="off"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchOpen(true)}
              onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
              aria-label={t('library.search')}
            />
          </form>
        </div>

        <div className="topbar-right">
          {/* Connection Status */}
          <div className="status-chip" id="conn-chip" title={isOnline ? t('common.online') : t('common.offline')}>
            <span
              className={`dot ${isOnline ? 'dot-online' : 'dot-offline'}`}
              id="conn-dot"
              aria-hidden="true"
            ></span>
            <span id="conn-label" className="sr-only">
              {isOnline ? t('common.online') : t('common.offline')}
            </span>
            <span aria-hidden="true">
              {isOnline ? t('common.online') : t('common.offline')}
            </span>
            {queuedCount > 0 && (
              <span
                style={{
                  background: 'var(--amber-500)',
                  color: 'white',
                  fontSize: 'var(--text-xs)',
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-full)',
                  marginLeft: '4px'
                }}
                aria-label={`${queuedCount} items queued for sync`}
              >
                {queuedCount}
              </span>
            )}
          </div>

          {/* Language Selector */}
          <select
            className="lang-pick"
            id="lang-header"
            value={language}
            onChange={(e) => setLanguage(e.target.value as any)}
            aria-label="Select language"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.flag} {lang.nativeName}
              </option>
            ))}
          </select>

          {/* Theme Toggle */}
          <button
            className="icon-btn"
            id="theme-btn"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>
      </header>

      {/* Sidebar */}
      <nav
        className={`sidebar ${sidebarOpen ? 'open' : ''}`}
        id="sidebar"
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="sidebar-header">
          <span className="logo-icon" aria-hidden="true">🌾</span>
          <span className="sidebar-title">AgriDoc AI</span>
          <button
            className="close-btn"
            id="sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
          >
            <X size={24} />
          </button>
        </div>

        <div className="nav-section-label">Main</div>
        {navItems.slice(0, 3).map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
            onClick={() => setSidebarOpen(false)}
            aria-current={location.pathname === item.path ? 'page' : undefined}
          >
            <span className="nav-icon" aria-hidden="true">
              <item.icon size={20} />
            </span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}

        <div className="nav-divider" role="separator"></div>
        <div className="nav-section-label">Library</div>
        {navItems.slice(3, 5).map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
            onClick={() => setSidebarOpen(false)}
            aria-current={location.pathname === item.path ? 'page' : undefined}
          >
            <span className="nav-icon" aria-hidden="true">
              <item.icon size={20} />
            </span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}

        <div className="nav-divider" role="separator"></div>
        <div className="nav-section-label">Account</div>
        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          onClick={() => setSidebarOpen(false)}
        >
          <span className="nav-icon" aria-hidden="true"><Settings size={20} /></span>
          <span className="nav-label">{t('nav.settings')}</span>
        </NavLink>

        <div className="sidebar-footer">
          <p>Build v2.0 · ONNX EfficientNet-B0</p>
          <p className="footnote">Not a substitute for expert agricultural advice.</p>
        </div>
      </nav>

      {/* Overlay for mobile sidebar */}
      <div
        className={`overlay ${sidebarOpen ? '' : 'hidden'}`}
        id="overlay"
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      ></div>

      {/* Main Content */}
      <main className="main" id="main-content" role="main">
        {children}
      </main>

      {/* Auth Error Modal */}
      {showAuthError && !isAuthenticated && (
        <div
          className="overlay"
          style={{ zIndex: 200 }}
          onClick={() => {}}
        >
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
            aria-labelledby="auth-error-title"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: 48, height: 48, borderRadius: 'var(--radius)',
                background: '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <AlertCircle size={24} color="#dc2626" />
              </div>
              <h2 id="auth-error-title" style={{ fontSize: 'var(--text-xl)', color: 'var(--text-primary)' }}>
                API Key Required
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 'var(--leading-relaxed)' }}>
              Please configure your API key in Settings to connect to the AgriDoc AI backend.
              You can find your API key in the backend <code>.env</code> file as <code>AGRIDOC_API_KEYS</code>.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => window.location.href = '/settings'}
              >
                Go to Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Quick Panel - for API key setup */}
      {!isAuthenticated && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 150,
            animation: 'slideUp var(--transition)'
          }}
        >
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            boxShadow: 'var(--shadow-lg)',
            minWidth: '320px',
            maxWidth: '400px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}>Quick Setup</h3>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: '16px' }}>
              Enter your API key to connect to the backend
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input
                type="password"
                placeholder="API Key (agridoc-...)"
                value={settingsApiKey}
                onChange={(e) => setSettingsApiKey(e.target.value)}
                className="setting-input"
                style={{ width: '100%' }}
              />
              <input
                type="url"
                placeholder="API Base URL"
                value={settingsApiBase}
                onChange={(e) => setSettingsApiBase(e.target.value)}
                className="setting-input"
                style={{ width: '100%' }}
              />
              <button
                className="btn btn-primary"
                onClick={handleSaveSettings}
                style={{ width: '100%' }}
              >
                Save & Connect
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  );
}