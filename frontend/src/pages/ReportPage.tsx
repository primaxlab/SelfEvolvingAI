import { useEffect, useState } from 'react';
import { getReport } from '../api';

export default function ReportPage() {
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getReport();
        setReport(data.report);
      } catch (e) {
        console.error('Failed to load report:', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div className="fade-in">加载中...</div>;

  return (
    <div className="fade-in">
      <h2 style={{ marginBottom: 24, fontSize: 24, fontWeight: 700 }}>📊 进化报告</h2>

      <div className="card">
        <pre style={{
          whiteSpace: 'pre-wrap',
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: 13,
          lineHeight: 1.7,
          color: 'var(--text-secondary)',
          maxHeight: 'calc(100vh - 200px)',
          overflow: 'auto',
        }}>
          {report}
        </pre>
      </div>
    </div>
  );
}
