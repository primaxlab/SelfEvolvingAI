import { useState } from 'react';
import { learn } from '../api';

export default function LearnPage() {
  const [content, setContent] = useState('');
  const [source, setSource] = useState('user');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Array<{ content: string; result: any; time: number }>>([]);

  const handleLearn = async () => {
    const text = content.trim();
    if (!text || loading) return;

    setLoading(true);
    try {
      const result = await learn(text, source);
      setResults(prev => [{ content: text, result, time: Date.now() }, ...prev].slice(0, 20));
      setContent('');
    } catch (e: any) {
      console.error('Learn failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <h2 style={{ marginBottom: 24, fontSize: 24, fontWeight: 700 }}>📚 学习中心</h2>

      {/* 输入区 */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div className="card-title">输入知识</div>
          <select
            value={source}
            onChange={e => setSource(e.target.value)}
            style={{
              padding: '4px 8px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              fontSize: 13,
            }}
          >
            <option value="user">用户输入</option>
            <option value="web">网页</option>
            <option value="book">书籍</option>
            <option value="api">API</option>
          </select>
        </div>
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="输入任何知识内容，AI会学习并记住..."
          style={{
            width: '100%',
            minHeight: 120,
            padding: 12,
            background: 'var(--bg-primary)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-primary)',
            fontSize: 14,
            resize: 'vertical',
            outline: 'none',
            lineHeight: 1.6,
          }}
        />
        <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn btn-primary"
            onClick={handleLearn}
            disabled={!content.trim() || loading}
          >
            {loading ? '学习中...' : '📚 开始学习'}
          </button>
        </div>
      </div>

      {/* 学习结果 */}
      {results.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">学习记录</div>
            <span className="tag tag-accent">{results.length} 条</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {results.map((r, i) => (
              <div key={i} style={{
                padding: '12px 16px',
                background: 'var(--bg-primary)',
                borderRadius: 'var(--radius-sm)',
                borderLeft: '3px solid var(--success)',
              }}>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>
                  {r.content.length > 100 ? r.content.slice(0, 100) + '...' : r.content}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  来源: {source} · {new Date(r.time).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 使用提示 */}
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <div className="card-title">💡 使用提示</div>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p>• 输入任何知识内容，AI会自动提取关键信息并存储</p>
          <p>• 支持各种格式：文本、代码、公式、定义等</p>
          <p>• 学习的知识会在进化循环中被整合和优化</p>
          <p>• 高质量的知识会被提升为长期记忆</p>
        </div>
      </div>
    </div>
  );
}
