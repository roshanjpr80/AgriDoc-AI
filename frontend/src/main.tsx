import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { OfflineProvider } from './contexts/OfflineContext';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <LanguageProvider>
          <AuthProvider>
            <OfflineProvider>
              <App />
              <Toaster
                position="bottom-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: 'var(--surface)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: '12px',
                    padding: '16px',
                    boxShadow: 'var(--shadow-lg)',
                  },
                  success: {
                    iconTheme: {
                      primary: '#1a5e1f',
                      secondary: '#fff',
                    },
                  },
                  error: {
                    iconTheme: {
                      primary: '#dc2626',
                      secondary: '#fff',
                    },
                  },
                }}
              />
            </OfflineProvider>
          </AuthProvider>
        </LanguageProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);