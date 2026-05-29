import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ChatPage from './pages/ChatPage';
import ModulesPage from './pages/ModulesPage';
import EvolvePage from './pages/EvolvePage';
import LearnPage from './pages/LearnPage';
import ReportPage from './pages/ReportPage';
import { getStatus, type SystemStatus } from './api';
import './index.css';

function Sidebar() {
  const location = useLocation();
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
    const interval = setInterval(() => {
      getStatus().then(setStatus).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { path: '/', icon: '📊', label: '仪表盘' },
    { path: '/chat', icon: '💬', label: '对话' },
    { path: '/modules', icon: '📦', label: '模块' },
    { path: '/evolve', icon: '🧬', label: '进化' },
    { path: '/learn', icon: '📚', label: '学习' },
    { path: '/report', icon: '📋', label: '报告' },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <h1>🧬 SelfEvolvingAI</h1>
        <div className="version">v4.0.0 · {status?.modules_loaded || 70} 模块</div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <span className="icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* 底部状态 */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border)',
        fontSize: 12,
        color: 'var(--text-muted)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
          <span className={`status-dot ${status?.status === 'running' ? 'online' : 'offline'}`} />
          <span>{status?.status === 'running' ? '运行中' : '未连接'}</span>
        </div>
        {status && (
          <div>
            代数: {status.generation} · 交互: {status.total_interactions}
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/modules" element={<ModulesPage />} />
            <Route path="/evolve" element={<EvolvePage />} />
            <Route path="/learn" element={<LearnPage />} />
            <Route path="/report" element={<ReportPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
