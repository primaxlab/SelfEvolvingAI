import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStatus, type SystemStatus } from '../api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getStatus();
        setStatus(data);
      } catch (e) {
        console.error('Failed to load status:', e);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="fade-in">加载中...</div>;
  if (!status) return <div className="fade-in">无法连接到后端</div>;

  const uptimeStr = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h > 0 ? `${h}小时${m}分钟` : `${m}分钟`;
  };

  return (
    <div className="fade-in">
      <h2 style={{ marginBottom: 24, fontSize: 24, fontWeight: 700 }}>
        🧬 仪表盘
      </h2>

      {/* 核心指标 */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="stat-label">系统状态</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
            <span className={`status-dot ${status.status === 'running' ? 'online' : 'offline'}`} />
            <span style={{ fontSize: 18, fontWeight: 600 }}>
              {status.status === 'running' ? '运行中' : '已停止'}
            </span>
          </div>
        </div>

        <div className="card">
          <div className="stat-label">模块数量</div>
          <div className="stat-value">{status.modules_loaded}</div>
        </div>

        <div className="card">
          <div className="stat-label">进化代数</div>
          <div className="stat-value">{status.generation}</div>
        </div>

        <div className="card">
          <div className="stat-label">总交互次数</div>
          <div className="stat-value">{status.total_interactions}</div>
        </div>
      </div>

      {/* 详细信息 */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">📊 系统信息</div>
          </div>
          <table style={{ width: '100%', fontSize: 14 }}>
            <tbody>
              <tr>
                <td style={{ color: 'var(--text-muted)', padding: '6px 0' }}>版本</td>
                <td style={{ textAlign: 'right' }}>{status.version}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-muted)', padding: '6px 0' }}>运行时间</td>
                <td style={{ textAlign: 'right' }}>{uptimeStr(status.uptime)}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-muted)', padding: '6px 0' }}>进化次数</td>
                <td style={{ textAlign: 'right' }}>{status.total_evolutions}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-muted)', padding: '6px 0' }}>交互频率</td>
                <td style={{ textAlign: 'right' }}>
                  {status.uptime > 0
                    ? `${(status.total_interactions / (status.uptime / 3600)).toFixed(1)} 次/小时`
                    : '—'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">🧬 进化循环</div>
          </div>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{
              fontSize: 48,
              fontWeight: 700,
              color: 'var(--accent-light)',
              lineHeight: 1,
            }}>
              {status.generation}
            </div>
            <div style={{ color: 'var(--text-muted)', marginTop: 8 }}>当前代数</div>
            <div style={{ marginTop: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
              感知 → 记忆 → 思考 → 行动 → 反思 → 进化
            </div>
          </div>
        </div>
      </div>

      {/* 快捷操作 */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">⚡ 快捷操作</div>
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={() => navigate('/chat')}>
            💬 开始对话
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/evolve')}>
            🧬 触发进化
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/modules')}>
            📦 查看模块
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/learn')}>
            📚 学习知识
          </button>
        </div>
      </div>
    </div>
  );
}
