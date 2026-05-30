import { useState, useRef, useEffect, useCallback } from 'react';
import { chat, chatStream, type ChatResponse } from '../api';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  confidence?: number;
  domain?: string;
  modules?: string[];
  moduleContext?: string;
  moduleTags?: string[];
  emotion?: string;
  timestamp: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = 'selfevolving_conversations';

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
          return { provider: id, config: { base_url: p.baseUrl, api_key: p.apiKey, model: p.model } };
        }
      }
      for (const [id, cfg] of Object.entries(providers)) {
        const p = cfg as any;
        if (p.enabled) {
          return { provider: id, config: { base_url: p.baseUrl, model: p.model } };
        }
      }
    }
  } catch {}
  return { provider: 'local' };
}

function loadConversations(): Conversation[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {}
  return [];
}

function saveConversations(convs: Conversation[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
  } catch {}
}

function getTitle(messages: Message[]): string {
  const firstUser = messages.find(m => m.role === 'user');
  if (firstUser) {
    const text = firstUser.content.slice(0, 30);
    return text.length < firstUser.content.length ? text + '...' : text;
  }
  return '新对话';
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeConvId, setActiveConvId] = useState<string>(() => {
    const convs = loadConversations();
    return convs.length > 0 ? convs[0].id : '';
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamMode, setStreamMode] = useState(true);
  const [activeProvider, setActiveProvider] = useState(getConfigFromStorage());
  const [showSidebar, setShowSidebar] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find(c => c.id === activeConvId);
  const messages = activeConv?.messages || [];

  // 自动保存
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 刷新模型配置
  useEffect(() => {
    const refresh = () => setActiveProvider(getConfigFromStorage());
    window.addEventListener('focus', refresh);
    const interval = setInterval(refresh, 1000);
    return () => { window.removeEventListener('focus', refresh); clearInterval(interval); };
  }, []);

  const newConversation = useCallback(() => {
    const conv: Conversation = {
      id: Date.now().toString(),
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(conv.id);
  }, []);

  const deleteConversation = useCallback((id: string) => {
    setConversations(prev => {
      const next = prev.filter(c => c.id !== id);
      if (activeConvId === id) {
        setActiveConvId(next.length > 0 ? next[0].id : '');
      }
      return next;
    });
  }, [activeConvId]);

  const updateMessages = useCallback((convId: string, updater: (prev: Message[]) => Message[]) => {
    setConversations(prev => prev.map(c => {
      if (c.id !== convId) return c;
      const newMsgs = updater(c.messages);
      return { ...c, messages: newMsgs, title: getTitle(newMsgs), updatedAt: Date.now() };
    }));
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    let convId = activeConvId;
    if (!convId) {
      const conv: Conversation = {
        id: Date.now().toString(),
        title: getTitle([{ id: 'tmp', role: 'user', content: text, timestamp: Date.now() }]),
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      setConversations(prev => [conv, ...prev]);
      convId = conv.id;
      setActiveConvId(conv.id);
    }

    const prov = getConfigFromStorage();

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    };
    updateMessages(convId, prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    if (streamMode) {
      const aiMsgId = (Date.now() + 1).toString();
      updateMessages(convId, prev => [...prev, { id: aiMsgId, role: 'ai', content: '', timestamp: Date.now() }]);

      await chatStream(
        text,
        (chunk) => {
          updateMessages(convId, prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, content: m.content + chunk } : m
          ));
        },
        (result) => {
          updateMessages(convId, prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, confidence: result.confidence, domain: result.domain } : m
          ));
          setLoading(false);
        },
        (error) => {
          updateMessages(convId, prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, content: `错误: ${error.message}` } : m
          ));
          setLoading(false);
        },
        prov.provider,
        prov.config,
      );
    } else {
      try {
        const result: ChatResponse = await chat(text, prov.provider, prov.config);
        // 构建模块标签
        const moduleTags: string[] = [];
        if (result.emotion && result.emotion !== 'neutral') moduleTags.push(`情感: ${result.emotion}`);
        if (result.domain) moduleTags.push(`领域: ${result.domain}`);
        if (result.confidence > 0) moduleTags.push(`置信度: ${(result.confidence * 100).toFixed(0)}%`);
        if (result.modules_used?.length > 0) moduleTags.push(`${result.modules_used.length}个模块`);
        updateMessages(convId, prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: result.answer,
          confidence: result.confidence,
          domain: result.domain,
          modules: result.modules_used,
          moduleContext: result.module_context,
          moduleTags,
          emotion: result.emotion,
          timestamp: result.timestamp,
        }]);
      } catch (e: any) {
        updateMessages(convId, prev => [...prev, {
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
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const confidenceColor = (c?: number) => {
    if (!c) return 'var(--text-muted)';
    if (c > 0.7) return 'var(--success)';
    if (c > 0.4) return 'var(--warning)';
    return 'var(--error)';
  };

  const isLocal = activeProvider.provider === 'local';

  return (
    <div className="fade-in" style={{ display: 'flex', height: 'calc(100vh - 48px)' }}>
      {/* 左侧会话列表 */}
      {showSidebar && (
        <div style={{
          width: 220, flexShrink: 0, background: 'var(--bg-secondary)',
          borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column',
          borderRadius: 'var(--radius)', overflow: 'hidden', marginRight: 12,
        }}>
          <div style={{ padding: '12px', borderBottom: '1px solid var(--border)' }}>
            <button className="btn btn-primary" onClick={newConversation} style={{ width: '100%', justifyContent: 'center' }}>
              + 新对话
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
            {conversations.length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                暂无对话
              </div>
            )}
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                style={{
                  padding: '8px 10px', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
                  background: conv.id === activeConvId ? 'var(--accent-glow)' : 'transparent',
                  marginBottom: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, fontWeight: conv.id === activeConvId ? 600 : 400,
                    color: conv.id === activeConvId ? 'var(--accent-light)' : 'var(--text-secondary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {conv.title}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {conv.messages.length} 条消息
                  </div>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); deleteConversation(conv.id); }}
                  style={{
                    background: 'none', border: 'none', color: 'var(--text-muted)',
                    cursor: 'pointer', fontSize: 14, padding: '2px 4px', opacity: 0.5,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 右侧聊天区 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* 顶部栏 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowSidebar(!showSidebar)}
              style={{ padding: '4px 8px', fontSize: 16 }}
            >
              {showSidebar ? '◀' : '▶'}
            </button>
            <h2 style={{ fontSize: 20, fontWeight: 700 }}>💬 对话</h2>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{
              fontSize: 12, color: isLocal ? 'var(--text-muted)' : 'var(--accent-light)',
              padding: '4px 12px', background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border)',
            }}>
              {PROVIDER_ICONS[activeProvider.provider]} {PROVIDER_NAMES[activeProvider.provider]}
              {activeProvider.config?.model ? ` · ${activeProvider.config.model}` : ''}
            </span>
            {!isLocal && <a href="#/settings" style={{ fontSize: 11, color: 'var(--text-muted)', textDecoration: 'none' }}>更换</a>}
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
                当前: <span style={{ color: isLocal ? 'var(--text-muted)' : 'var(--accent-light)' }}>
                  {PROVIDER_ICONS[activeProvider.provider]} {PROVIDER_NAMES[activeProvider.provider]}
                  {activeProvider.config?.model ? ` (${activeProvider.config.model})` : ''}
                </span>
              </div>
              {isLocal && (
                <div style={{ fontSize: 12, marginTop: 8 }}>
                  前往 <a href="#/settings" style={{ color: 'var(--accent-light)' }}>模型页面</a> 配置大模型
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
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                    {/* 模块标签 */}
                    {msg.moduleTags && msg.moduleTags.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
                        {msg.moduleTags.map((tag, i) => (
                          <span key={i} style={{
                            fontSize: 10, padding: '2px 8px', borderRadius: 10,
                            background: 'var(--accent-glow)', color: 'var(--accent-light)',
                            border: '1px solid var(--border)',
                          }}>{tag}</span>
                        ))}
                      </div>
                    )}
                    {/* 模块上下文详情 */}
                    {msg.moduleContext && (
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', background: 'var(--bg-secondary)', padding: '6px 10px', borderRadius: 8, marginBottom: 6, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                        {msg.moduleContext}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                      <span>置信度: <span style={{ color: confidenceColor(msg.confidence) }}>{(msg.confidence * 100).toFixed(0)}%</span></span>
                      {msg.domain && <span>领域: {msg.domain}</span>}
                      {msg.emotion && msg.emotion !== 'neutral' && <span>情绪: {msg.emotion}</span>}
                      {msg.modules && <span>模块: {msg.modules.length}个</span>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && !streamMode && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{ padding: '12px 16px', borderRadius: '16px', borderBottomLeftRadius: 4, background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                思考中...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <div style={{ marginTop: 12, display: 'flex', gap: 8, padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
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
    </div>
  );
}
