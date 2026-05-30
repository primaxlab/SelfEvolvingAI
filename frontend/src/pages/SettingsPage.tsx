import { useState, useEffect } from 'react';

interface ProviderConfig {
  id: string;
  name: string;
  icon: string;
  baseUrl: string;
  apiKey: string;
  model: string;
  enabled: boolean;
}

const DEFAULT_PROVIDERS: ProviderConfig[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    icon: '🟢',
    baseUrl: 'https://api.openai.com/v1',
    apiKey: '',
    model: 'gpt-4o',
    enabled: false,
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    icon: '🔵',
    baseUrl: 'https://api.deepseek.com/v1',
    apiKey: '',
    model: 'deepseek-chat',
    enabled: false,
  },
  {
    id: 'claude',
    name: 'Claude (Anthropic)',
    icon: '🟠',
    baseUrl: 'https://api.anthropic.com/v1',
    apiKey: '',
    model: 'claude-sonnet-4-20250514',
    enabled: false,
  },
  {
    id: 'ollama',
    name: 'Ollama (本地)',
    icon: '🦙',
    baseUrl: 'http://localhost:11434',
    apiKey: '',
    model: 'llama3.2',
    enabled: false,
  },
  {
    id: 'custom',
    name: '自定义 (OpenAI兼容)',
    icon: '⚙️',
    baseUrl: '',
    apiKey: '',
    model: '',
    enabled: false,
  },
];

export default function SettingsPage() {
  const [providers, setProviders] = useState<ProviderConfig[]>(DEFAULT_PROVIDERS);
  const [activeTab, setActiveTab] = useState('providers');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState<{ id: string; ok: boolean; msg: string } | null>(null);

  // 从 localStorage 加载配置
  useEffect(() => {
    const saved = localStorage.getItem('selfevolving_providers');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setProviders(prev => prev.map(p => ({
          ...p,
          ...parsed[p.id],
        })));
      } catch {}
    }
  }, []);

  const updateProvider = (id: string, field: keyof ProviderConfig, value: any) => {
    setProviders(prev => prev.map(p =>
      p.id === id ? { ...p, [field]: value } : p
    ));
  };

  const handleSave = () => {
    setSaving(true);
    const config: Record<string, any> = {};
    providers.forEach(p => {
      config[p.id] = {
        baseUrl: p.baseUrl,
        apiKey: p.apiKey,
        model: p.model,
        enabled: p.enabled,
      };
    });
    localStorage.setItem('selfevolving_providers', JSON.stringify(config));
    setTimeout(() => {
      setSaving(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }, 500);
  };

  const handleTest = async (provider: ProviderConfig) => {
    setTestResult({ id: provider.id, ok: false, msg: '测试中...' });
    try {
      // 简单测试：检查 URL 是否可达
      const response = await fetch(provider.baseUrl + '/models', {
        headers: provider.apiKey ? { 'Authorization': `Bearer ${provider.apiKey}` } : {},
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        setTestResult({ id: provider.id, ok: true, msg: '连接成功！' });
      } else {
        setTestResult({ id: provider.id, ok: false, msg: `HTTP ${response.status}` });
      }
    } catch (e: any) {
      setTestResult({ id: provider.id, ok: false, msg: e.message || '连接失败' });
    }
  };

  return (
    <div className="fade-in">
      <h2 style={{ marginBottom: 24, fontSize: 24, fontWeight: 700 }}>⚙️ 设置</h2>

      {/* 标签页 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { id: 'providers', label: '🤖 大模型配置' },
          { id: 'general', label: '🔧 通用设置' },
        ].map(tab => (
          <button
            key={tab.id}
            className={`btn ${activeTab === tab.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 大模型配置 */}
      {activeTab === 'providers' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {providers.map(provider => (
            <div key={provider.id} className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 24 }}>{provider.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 16 }}>{provider.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{provider.id}</div>
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>启用</span>
                  <input
                    type="checkbox"
                    checked={provider.enabled}
                    onChange={e => updateProvider(provider.id, 'enabled', e.target.checked)}
                    style={{ width: 18, height: 18, cursor: 'pointer' }}
                  />
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {/* Base URL */}
                <div>
                  <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                    API 地址
                  </label>
                  <input
                    type="text"
                    value={provider.baseUrl}
                    onChange={e => updateProvider(provider.id, 'baseUrl', e.target.value)}
                    placeholder="https://api.example.com/v1"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'var(--bg-primary)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: 13,
                      outline: 'none',
                    }}
                  />
                </div>

                {/* Model */}
                <div>
                  <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                    模型名称
                  </label>
                  <input
                    type="text"
                    value={provider.model}
                    onChange={e => updateProvider(provider.id, 'model', e.target.value)}
                    placeholder="gpt-4o"
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      background: 'var(--bg-primary)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: 13,
                      outline: 'none',
                    }}
                  />
                </div>

                {/* API Key */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                    API Key
                  </label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="password"
                      value={provider.apiKey}
                      onChange={e => updateProvider(provider.id, 'apiKey', e.target.value)}
                      placeholder="sk-..."
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-primary)',
                        fontSize: 13,
                        outline: 'none',
                      }}
                    />
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleTest(provider)}
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      🔗 测试连接
                    </button>
                  </div>
                  {testResult && testResult.id === provider.id && (
                    <div style={{
                      marginTop: 6,
                      fontSize: 12,
                      color: testResult.ok ? 'var(--success)' : 'var(--error)',
                    }}>
                      {testResult.ok ? '✅' : '❌'} {testResult.msg}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* 保存按钮 */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
            {saved && (
              <span style={{ color: 'var(--success)', fontSize: 14, alignSelf: 'center' }}>
                ✅ 已保存
              </span>
            )}
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving}
              style={{ padding: '10px 24px' }}
            >
              {saving ? '保存中...' : '💾 保存配置'}
            </button>
          </div>

          {/* 使用说明 */}
          <div className="card" style={{ marginTop: 8 }}>
            <div className="card-header">
              <div className="card-title">💡 使用说明</div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              <p><strong>推荐配置：</strong></p>
              <p>• <strong>DeepSeek</strong> — 国内访问快，性价比高，推荐新手使用</p>
              <p>• <strong>Ollama</strong> — 完全本地运行，无需API Key，需要先安装 Ollama</p>
              <p>• <strong>OpenAI</strong> — 最强模型，需要海外网络</p>
              <p>• <strong>Claude</strong> — 长文本理解强，需要海外网络</p>
              <p style={{ marginTop: 8 }}><strong>自定义：</strong>支持任何 OpenAI 兼容的 API（如 vLLM、LocalAI、Text Generation WebUI 等）</p>
            </div>
          </div>
        </div>
      )}

      {/* 通用设置 */}
      {activeTab === 'general' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <div className="card-title">🔧 系统设置</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  API 服务器地址
                </label>
                <input
                  type="text"
                  defaultValue="http://localhost:8000"
                  placeholder="http://localhost:8000"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  进化触发间隔（秒）
                </label>
                <input
                  type="number"
                  defaultValue={300}
                  min={60}
                  style={{
                    width: 200,
                    padding: '8px 12px',
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div className="card-title">📊 关于</div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              <p><strong>SelfEvolvingAI</strong> v4.0.0</p>
              <p>70模块自我进化AI系统</p>
              <p>GitHub: <a href="https://github.com/primaxlab/SelfEvolvingAI" target="_blank" rel="noopener" style={{ color: 'var(--accent-light)' }}>primaxlab/SelfEvolvingAI</a></p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
