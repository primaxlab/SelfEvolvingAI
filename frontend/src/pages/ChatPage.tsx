import { useState, useRef, useEffect } from 'react';
import { chat, chatStream, type ChatResponse } from '../api';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  confidence?: number;
  domain?: string;
  modules?: string[];
  timestamp: number;
}

const PROVIDER_NAMES: Record<string, string> = {
  local: '本地模式',
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  claude: 'Claude',
  ollama: 'Ollama',
  custom: '自定义',
};

const PROVIDER_ICONS: Record<string, string> = {
  local: '🏠',
  openai: '🟢',
  deepseek: '🔵',
  claude: '🟠',
  ollama: '🦙',
  custom: '⚙️',
};

function getConfigFromStorage(): { provider: string; config?: Record<string, any> } {
  try {
    const saved = localStorage.getItem('selfevolving_providers');
    if (saved) {
      const providers = JSON.parse(saved);
      for (const [id, cfg] of Object.entries(providers)) {
        const p = cfg as any;
        if (p.enabled && p.apiKey) {
          return {
            provider: id,
            config: { base_url: p.baseUrl, api_key: p.apiKey, model: p.model },
          };
        }
      }
      for (const [id, cfg] of Object.entries(providers)) {
        const p = cfg as any;
        if (p.enabled) {
          return {
            provider: id,
            config: { base_url: p.baseUrl, model: p.model },
          };
        }
      }
    }
  } catch {}
  return { provider: 'local' };
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamMode, setStreamMode] = useState(true);
  const [activeProvider, setActiveProvider] = useState(getConfigFromStorage());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 每次页面可见时重新读取配置
  useEffect(() => {
    const refresh = () => setActiveProvider(getConfigFromStorage());
    window.addEventListener('focus', refresh);
    // 也监听 storage 事件（跨标签页同步）
    window.addEventListener('storage', refresh);
    // 每秒检查一次（同标签页内模型页面修改后）
    const interval = setInterval(refresh, 1000);
    return () => {
      window.removeEventListener('focus', refresh);
      window.removeEventListener('storage', refresh);
      clearInterval(interval);
    };
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    // 每次发送时重新读取最新配置
    const prov = getConfigFromStorage();

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    if (streamMode) {
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: '',
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, aiMsg]);

      await chatStream(
        text,
        (chunk) => {
          setMessages(prev => prev.map(m =>
            m.id === aiMsg.id ? { ...m, content: m.content + chunk } : m
          ));
        },
        (result) => {
          setMessages(prev => prev.map(m =>
            m.id === aiMsg.id ? {
              ...m,
              confidence: result.confidence,
              domain: result.domain,
            } : m
          ));
          setLoading(false);
        },
        (error) => {
          setMessages(prev => prev.map(m =>
            m.id === aiMsg.id ? { ...m, content: `错误: ${error.message}` } : m
          ));
          setLoading(false);
        },
        prov.provider,
        prov.config,
      );
    } else {
      try {
        const result: ChatResponse = await chat(text, prov.provider, prov.config);
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: result.answer,
          confidence: result.confidence,
          domain: result.domain,
          modules: result.modules_used,
          timestamp: result.timestamp,
        }]);
      } catch (e: any) {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: `错误: ${e.message}`,
          timestamp: Date.now(),
        }]);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const confidenceColor = (c?: number) => {
    if (!c) return 'var(--text-muted)';
    if (c > 0.7) return 'var(--success)';
    if (c > 0.4) return 'var(--warning)';
    return 'var(--error)';
  };

  const isLocal = activeProvider.provider === 'local';

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700 }}>💬 对话</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* 当前模型显示（只读，配置在模型页面） */}
          <span style={{
            fontSize: 12,
            color: isLocal ? 'var(--text-muted)' : 'var(--accent-light)',
            padding: '4px 12px',
            background: 'var(--bg-card)',
            borderRadius: '12px',
            border: '1px solid var(--border)',
          }}>
            {PROVIDER_ICONS[activeProvider.provider] || '🤖'} {PROVIDER_NAMES[activeProvider.provider] || activeProvider.provider}
            {activeProvider.config?.model ? ` · ${activeProvider.config.model}` : ''}
          </span>
          {!isLocal && (
            <a href="#/settings" style={{ fontSize: 11, color: 'var(--text-muted)', textDecoration: 'none' }}>
              更换模型
            </a>
          )}
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={streamMode} onChange={e => setStreamMode(e.target.checked)} />
            流式
          </label>
        </div>
      </div>

      {/* 消息列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 4px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🧬</div>
            <div style={{ fontSize: 18 }}>开始和自我进化AI对话</div>
            <div style={{ fontSize: 13, marginTop: 8 }}>
              当前模型: <span style={{ color: isLocal ? 'var(--text-muted)' : 'var(--accent-light)' }}>
                {PROVIDER_ICONS[activeProvider.provider]} {PROVIDER_NAMES[activeProvider.provider]}
                {activeProvider.config?.model ? ` (${activeProvider.config.model})` : ''}
              </span>
            </div>
            {isLocal && (
              <div style={{ fontSize: 12, marginTop: 8, color: 'var(--warning)' }}>
                前往 <a href="#/settings" style={{ color: 'var(--accent-light)' }}>模型页面</a> 配置大模型以获得更好体验
              </div>
            )}
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '75%', padding: '12px 16px', borderRadius: '16px',
              background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-card)',
              border: msg.role === 'ai' ? '1px solid var(--border)' : 'none',
              borderBottomRightRadius: msg.role === 'user' ? 4 : 16,
              borderBottomLeftRadius: msg.role === 'ai' ? 4 : 16,
            }}>
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.6 }}>{msg.content}</div>
              {msg.role === 'ai' && msg.confidence !== undefined && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)', display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>置信度: <span style={{ color: confidenceColor(msg.confidence) }}>{(msg.confidence * 100).toFixed(0)}%</span></span>
                  {msg.domain && <span>领域: {msg.domain}</span>}
                  {msg.modules && <span>模块: {msg.modules.length}个</span>}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && !streamMode && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{ padding: '12px 16px', borderRadius: '16px', borderBottomLeftRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
              <span style={{ animation: 'pulse 1.5s infinite' }}>思考中...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8, padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isLocal ? '本地模式 - 输入消息...' : `与 ${PROVIDER_NAMES[activeProvider.provider]} 对话...`}
          style={{ flex: 1, background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: 14, resize: 'none', outline: 'none', minHeight: 24, maxHeight: 120, lineHeight: 1.5 }}
          rows={1}
        />
        <button className="btn btn-primary" onClick={sendMessage} disabled={!input.trim() || loading}>
          发送
        </button>
      </div>
    </div>
  );
}
