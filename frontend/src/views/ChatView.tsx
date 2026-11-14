import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Loader2, Sparkles, RefreshCw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useAPI } from '../services/api';
import { toast } from 'react-hot-toast';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  streaming?: boolean;
}

interface SuggestedQuestion {
  text: string;
  category: string;
}

const SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
  { text: 'How to prevent late blight in tomatoes?', category: 'Prevention' },
  { text: 'What causes yellow leaves on citrus trees?', category: 'Symptoms' },
  { text: 'Best organic treatment for powdery mildew?', category: 'Treatment' },
  { text: 'When to apply copper fungicide?', category: 'Application' },
  { text: 'How to identify bacterial spot vs fungal spot?', category: 'Identification' },
  { text: 'Crop rotation for soil-borne diseases?', category: 'Management' },
];

export default function ChatView() {
  const { t } = useLanguage();
  const { askRAG } = useAPI();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `👋 ${t('chat.subtitle')}\n\nI can help you with:\n• Disease identification & treatment\n• Prevention strategies\n• Organic & chemical controls\n• Crop-specific advice\n• Seasonal timing\n\nTry one of the suggested questions or ask your own!`,
          timestamp: new Date(),
        },
      ]);
    }
  }, [t]);

  // Handle initial query from navigation state
  useEffect(() => {
    const state = history.state as { initialQuery?: string } | undefined;
    if (state?.initialQuery && messages.length <= 1) {
      handleSend(state.initialQuery);
    }
  }, [messages.length]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || loading) return;

    setInput('');
    setShowSuggestions(false);
    setLoading(true);

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);

    try {
      const lang = localStorage.getItem('agridoc_lang') || 'en';
      const data = await askRAG(messageText, lang);

      // Simulate streaming
      const fullResponse = data.answer || t('error.adviceUnavailable');
      const words = fullResponse.split(' ');
      let currentText = '';

      for (let i = 0; i < words.length; i++) {
        currentText += words[i] + (i < words.length - 1 ? ' ' : '');
        setMessages(prev => prev.map(m =>
          m.id === assistantMessage.id ? { ...m, content: currentText } : m
        ));
        await new Promise(resolve => setTimeout(resolve, 30));
      }

      setMessages(prev => prev.map(m =>
        m.id === assistantMessage.id ? { ...m, content: fullResponse, streaming: false } : m
      ));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t('error.predictionFailed');
      setMessages(prev => prev.map(m =>
        m.id === assistantMessage.id ? { ...m, content: `⚠️ ${errorMsg}`, streaming: false } : m
      ));
      toast.error(errorMsg, { id: 'chat-error' });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (q: string) => {
    handleSend(q);
  };

  const handleClearChat = () => {
    if (confirm(t('common.confirm') + '?')) {
      setMessages([]);
      setShowSuggestions(true);
    }
  };

  return (
    <section className="view-panel active" id="view-chat" aria-labelledby="chat-title">
      <div className="view-header row-between">
        <div>
          <h1 id="chat-title">{t('chat.title')}</h1>
          <p>{t('chat.subtitle')}</p>
        </div>
        <button
          className="btn btn-text-secondary"
          onClick={handleClearChat}
          disabled={messages.length <= 1}
          aria-label="Clear chat"
        >
          <RefreshCw size={16} /> {t('common.clear')}
        </button>
      </div>

      {/* Messages Area */}
      <div className="chat-messages" role="log" aria-live="polite" aria-label="Chat messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-message ${msg.role} ${msg.streaming ? 'streaming' : ''}`}
            role={msg.role === 'assistant' ? 'status' : undefined}
            aria-busy={msg.streaming}
          >
            <div className="message-avatar" aria-hidden="true">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="message-content">
              <div className="message-bubble">
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  wordWrap: 'break-word',
                  fontFamily: 'inherit',
                  fontSize: 'var(--text-base)',
                  lineHeight: 'var(--leading-relaxed)',
                  margin: 0,
                  color: 'var(--text-primary)'
                }}>
                  {msg.content}
                </pre>
                {msg.streaming && <span className="cursor" aria-hidden="true">▌</span>}
              </div>
              <div className="message-time">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      {showSuggestions && messages.length <= 1 && (
        <div className="chat-suggestions" role="list" aria-label="Suggested questions">
          <div className="suggestions-header">
            <Sparkles size={16} aria-hidden="true" />
            <span>{t('chat.tryAsking')}</span>
          </div>
          <div className="suggestions-grid" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                className="suggestion-chip"
                onClick={() => handleSuggestionClick(q.text)}
                role="listitem"
              >
                {q.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="chat-input-area">
        <div className="input-wrap">
          <textarea
            ref={inputRef}
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('chat.placeholder')}
            disabled={loading}
            rows={1}
            style={{
              minHeight: '48px',
              maxHeight: '120px',
              resize: 'none',
              padding: '12px 16px',
              paddingRight: '56px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--bg-input)',
              color: 'var(--text-primary)',
              fontSize: 'var(--text-base)',
              lineHeight: 'var(--leading-normal)',
              width: '100%',
              outline: 'none',
              transition: 'border-color var(--transition), box-shadow var(--transition)',
              boxSizing: 'border-box',
            }}
            aria-label={t('chat.placeholder')}
          />
          <button
            className="send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() && !loading || loading}
            aria-label={t('chat.send')}
            style={{
              position: 'absolute',
              right: '8px',
              bottom: '8px',
              padding: '8px',
              borderRadius: 'var(--radius)',
              background: 'var(--green-600)',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all var(--transition)',
              opacity: input.trim() || loading ? 1 : 0.5,
            }}
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
        <p className="chat-disclaimer" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textAlign: 'center', marginTop: '8px' }}>
          ⚠️ {t('result.disclaimer')}
        </p>
      </div>

      <style>{`
        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          minHeight: 300px;
        }
        .chat-message {
          display: flex;
          gap: 12px;
          animation: fadeIn var(--transition);
        }
        .chat-message.user {
          flex-direction: row-reverse;
        }
        .message-avatar {
          width: 36px;
          height: 36px;
          borderRadius: 'var(--radius-full)';
          background: var(--bg-tertiary);
          display: flex;
          alignItems: center;
          justifyContent: center;
          fontSize: 16px;
          flexShrink: 0;
        }
        .message-content {
          flex: 1;
          maxWidth: 85%;
          display: flex;
          flexDirection: column;
          gap: 4px;
        }
        .chat-message.user .message-content {
          alignItems: flex-end;
        }
        .message-bubble {
          padding: 12px 16px;
          borderRadius: 'var(--radius-lg)';
          background: var(--bg-tertiary);
          position: relative;
        }
        .chat-message.user .message-bubble {
          background: var(--green-600);
          color: white;
        }
        .message-time {
          fontSize: 'var(--text-xs)';
          color: 'var(--text-muted)';
          padding: 0 4px;
        }
        .chat-message.user .message-time {
          textAlign: right;
        }
        .cursor {
          display: inline-block;
          animation: blink 1s infinite;
          color: var(--green-600);
        }
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
        .chat-suggestions {
          padding: 0 20px 16px;
          borderTop: '1px solid var(--border-light)';
          background: var(--bg-primary);
        }
        .suggestions-header {
          display: flex;
          alignItems: center;
          gap: 8px;
          fontSize: 'var(--text-sm)';
          fontWeight: 600;
          color: 'var(--text-secondary)';
          marginBottom: '12px';
        }
        .suggestion-chip {
          padding: '8px 14px';
          borderRadius: 'var(--radius-full)';
          background: var(--bg-tertiary);
          border: '1px solid var(--border-light)';
          color: var(--text-primary);
          fontSize: 'var(--text-sm)';
          cursor: pointer;
          transition: 'all var(--transition)';
          whiteSpace: nowrap;
        }
        .suggestion-chip:hover {
          background: var(--green-50);
          borderColor: var(--green-300);
          color: var(--green-700);
        }
        .chat-input-area {
          padding: '20px';
          borderTop: '1px solid var(--border-light)';
          background: var(--bg-primary);
        }
        .input-wrap {
          position: relative;
        }
        .send-btn:disabled {
          cursor: not-allowed;
        }
        .send-btn:hover:not(:disabled) {
          background: var(--green-700);
          transform: scale(1.05);
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </section>
  );
}