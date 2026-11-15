import { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface AuthContextType {
  apiKey: string;
  apiBase: string;
  setApiKey: (key: string) => void;
  setApiBase: (base: string) => void;
  clearAuth: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Default API key from environment (for development)
const DEFAULT_API_KEY = (import.meta as any).env?.VITE_API_KEY || '';
const DEFAULT_API_BASE = (import.meta as any).env?.VITE_API_BASE || 'https://agridoc-ai-backend.onrender.com';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('agridoc_api_key') || DEFAULT_API_KEY;
    }
    return DEFAULT_API_KEY;
  });

  const [apiBase, setApiBaseState] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('agridoc_api_base');
      // Only use stored value if it's a valid https URL (production-safe)
      // Ignore relative paths (/api), localhost, or other dev settings
      if (stored && (stored.startsWith('https://') || stored.startsWith('http://'))) {
        return stored;
      }
      return DEFAULT_API_BASE;
    }
    return DEFAULT_API_BASE;
  });

  useEffect(() => {
    if (apiKey) localStorage.setItem('agridoc_api_key', apiKey);
  }, [apiKey]);

  useEffect(() => {
    if (apiBase) localStorage.setItem('agridoc_api_base', apiBase);
  }, [apiBase]);

  const setApiKey = useCallback((key: string) => {
    setApiKeyState(key);
  }, []);

  const setApiBase = useCallback((base: string) => {
    setApiBaseState(base.replace(/\/$/, '')); // Remove trailing slash
  }, []);

  const clearAuth = useCallback(() => {
    setApiKeyState('');
    setApiBaseState('');
    localStorage.removeItem('agridoc_api_key');
    localStorage.removeItem('agridoc_api_base');
  }, []);

  return (
    <AuthContext.Provider value={{
      apiKey,
      apiBase,
      setApiKey,
      setApiBase,
      clearAuth,
      isAuthenticated: !!apiKey
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}