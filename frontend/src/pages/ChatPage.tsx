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

const PROVIDERS = [
  { id: 'local', name: '本地模式', icon: '🏠', needsKey: false },
  { id: 'deepseek', name: 'DeepSeek', icon: '🔵', needsKey: true, defaultUrl: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat' },
  { id: 'openai', name: 'OpenAI', icon: '🟢', needsKey: true, defaultUrl: 'https://api.openai.com/v1', defaultModel: 'gpt-4o' },
  { id: 'claude', name: 'Claude', icon: '🟠', needsKey: true, defaultUrl: 'https://api.anthropic.com/v1', defaultModel: 'claude-sonnet-4-20250514' },
  { id: 'ollama', name: 'Ollama', icon: '🦙', needsKey: false, defaultUrl: 'http://localhost:11434', defaultModel: 'llama3.2' },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamMode, setStreamMode] = useState(true);
  const [providerId, setProviderId] = useState('local');
  const [apiKey, setApiKey] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getProviderConfig = () => {
    const p = PROVIDERS.find(x => x.id === providerId);
    if (!p || p.id === 'local') return { provider: 'local' };
    return {
      provider: p.id,
      config: {
        base_url: p.defaultUrl,
        api_key: apiKey,
        model: p.defaultModel,
      },
    };
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const prov = getProviderConfig();

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

  const currentProvider = PROVIDERS.find(x => x.id === providerId);
  const confidenceColor = (c?: number) => {
    if (!c) return 'var(--text-muted)';
    if (c > 0.7) return 'var(--success)';
    if (c > 0.4) return 'var(--warning)';
    return 'var(--error)';
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)' }}>
      {/* 顶部栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700 }}>对话</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* 模型选择下拉框 */}
          <select
            value={providerId}
            onChange={e => {
              setProviderId(e.target.value);
            }}
            style={{
              padding: '6px 12px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              color: providerId === 'local' ? 'var(--text-muted)' : 'var(--accent-light)',
              fontSize: 13,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {PROVIDERS.map(p => (
              <option key={p.id} value={p.id}>{p.icon} {p.name}</option>
            ))}
          </select>

          {/* API Key 输入（仅在需要时显示） */}
          {currentProvider?.needsKey && (
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="API Key"
              style={{
                width: 160,
                padding: '6px 10px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: 12,
                outline: 'none',
              }}
            />
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
              当前: <span style={{ color: providerId === 'local' ? 'var(--text-muted)' : 'var(--accent-light)' }}>
                {currentProvider?.icon} {currentProvider?.name}
                {currentProvider?.defaultModel ? ` (${currentProvider.defaultModel})` : ''}
              </span>
            </div>
            {providerId === 'local' && (
              <div style={{ fontSize: 12, marginTop: 4, color: 'var(--warning)' }}>
                在右上角选择模型并输入API Key以获得更好体验
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
          placeholder="输入消息... (Enter 发送)"
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
