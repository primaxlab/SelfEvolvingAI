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

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamMode, setStreamMode] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

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
      // 流式模式
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
            m.id === aiMsg.id ? { ...m, content: `❌ 错误: ${error.message}` } : m
          ));
          setLoading(false);
        }
      );
    } else {
      // 普通模式
      try {
        const result: ChatResponse = await chat(text);
        const aiMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: result.answer,
          confidence: result.confidence,
          domain: result.domain,
          modules: result.modules_used,
          timestamp: result.timestamp,
        };
        setMessages(prev => [...prev, aiMsg]);
      } catch (e: any) {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: `❌ 错误: ${e.message}`,
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

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700 }}>💬 对话</h2>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
          <input
            type="checkbox"
            checked={streamMode}
            onChange={e => setStreamMode(e.target.checked)}
          />
          流式输出
        </label>
      </div>

      {/* 消息列表 */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '0 4px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}>
        {messages.length === 0 && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-muted)',
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🧬</div>
            <div style={{ fontSize: 18 }}>开始和自我进化AI对话</div>
            <div style={{ fontSize: 13, marginTop: 8 }}>输入任何问题，AI会思考并回答</div>
          </div>
        )}

        {messages.map(msg => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              maxWidth: '75%',
              padding: '12px 16px',
              borderRadius: '16px',
              background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-card)',
              border: msg.role === 'ai' ? '1px solid var(--border)' : 'none',
              borderBottomRightRadius: msg.role === 'user' ? 4 : 16,
              borderBottomLeftRadius: msg.role === 'ai' ? 4 : 16,
            }}>
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.6 }}>
                {msg.content}
              </div>
              {msg.role === 'ai' && msg.confidence !== undefined && (
                <div style={{
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: '1px solid var(--border)',
                  display: 'flex',
                  gap: 12,
                  fontSize: 11,
                  color: 'var(--text-muted)',
                }}>
                  <span>
                    置信度: <span style={{ color: confidenceColor(msg.confidence) }}>
                      {(msg.confidence * 100).toFixed(0)}%
                    </span>
                  </span>
                  {msg.domain && <span>领域: {msg.domain}</span>}
                  {msg.modules && <span>模块: {msg.modules.length}个</span>}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && !streamMode && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '12px 16px',
              borderRadius: '16px',
              borderBottomLeftRadius: 4,
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
            }}>
              <span style={{ animation: 'pulse 1.5s infinite' }}>思考中...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div style={{
        marginTop: 16,
        display: 'flex',
        gap: 8,
        padding: '12px',
        background: 'var(--bg-card)',
        borderRadius: 'var(--radius)',
        border: '1px solid var(--border)',
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: 'var(--text-primary)',
            fontSize: 14,
            resize: 'none',
            outline: 'none',
            minHeight: 24,
            maxHeight: 120,
            lineHeight: 1.5,
          }}
          rows={1}
        />
        <button
          className="btn btn-primary"
          onClick={sendMessage}
          disabled={!input.trim() || loading}
        >
          发送
        </button>
      </div>
    </div>
  );
}
