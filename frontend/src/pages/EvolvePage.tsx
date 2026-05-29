import { useState } from 'react';
import { evolve, type EvolveResult } from '../api';

export default function EvolvePage() {
  const [result, setResult] = useState<EvolveResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<EvolveResult[]>([]);

  const handleEvolve = async () => {
    setLoading(true);
    try {
      const data = await evolve('manual');
      setResult(data);
      setHistory(prev => [data, ...prev].slice(0, 10));
    } catch (e: any) {
      console.error('Evolve failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <h2 style={{ marginBottom: 24, fontSize: 24, fontWeight: 700 }}>🧬 进化中心</h2>

      {/* 触发进化 */}
      <div className="card" style={{ marginBottom: 24, textAlign: 'center', padding: 40 }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>
          {loading ? '⚡' : '🧬'}
        </div>
        <h3 style={{ fontSize: 20, marginBottom: 8 }}>
          {loading ? '进化中...' : '触发进化'}
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 24, fontSize: 14 }}>
          进化过程将执行：记忆巩固 → 代码自改进 → 反思总结 → 元认知更新 → 知识蒸馏 → 性能优化
        </p>
        <button
          className="btn btn-primary"
          onClick={handleEvolve}
          disabled={loading}
          style={{ fontSize: 16, padding: '12px 32px' }}
        >
          {loading ? '⏳ 进化中...' : '🧬 开始进化'}
        </button>
      </div>

      {/* 最新结果 */}
      {result && (
        <div className="card fade-in" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <div className="card-title">📊 进化结果</div>
            <span className="tag tag-success">成功</span>
          </div>

          <div className="grid-3" style={{ marginBottom: 16 }}>
            <div>
              <div className="stat-label">当前代数</div>
              <div className="stat-value">{result.generation}</div>
            </div>
            <div>
              <div className="stat-label">改进项</div>
              <div className="stat-value">{result.improvements}</div>
            </div>
            <div>
              <div className="stat-label">耗时</div>
              <div className="stat-value">{result.duration.toFixed(1)}s</div>
            </div>
          </div>

          {/* 改进详情 */}
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>改进详情</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {result.details.map((d, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 12px',
                  background: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 13,
                }}>
                  <span style={{ color: 'var(--success)' }}>✓</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{d.type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 历史记录 */}
      {history.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">📜 进化历史</div>
            <span className="tag tag-accent">{history.length} 条</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {history.map((h, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                background: i === 0 ? 'var(--accent-glow)' : 'var(--bg-primary)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 13,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontWeight: 600 }}>第 {h.generation} 代</span>
                  <span style={{ color: 'var(--text-muted)' }}>{h.improvements} 项改进</span>
                </div>
                <span style={{ color: 'var(--text-muted)' }}>{h.duration.toFixed(1)}s</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
