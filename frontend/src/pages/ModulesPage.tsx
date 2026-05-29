import { useEffect, useState } from 'react';
import { getModules, type ModuleStats } from '../api';

export default function ModulesPage() {
  const [modules, setModules] = useState<ModuleStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getModules();
        setModules(data);
      } catch (e) {
        console.error('Failed to load modules:', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div className="fade-in">加载中...</div>;
  if (!modules) return <div className="fade-in">无法加载模块数据</div>;

  const moduleEntries = Object.entries(modules).filter(([key]) =>
    key.toLowerCase().includes(search.toLowerCase())
  );

  // 模块分类
  const categories: Record<string, string[]> = {
    '核心模块': ['1_memory', '2_tool_extender', '3_self_improver', '4_metacognition', '5_knowledge_graph', '6_goal_planning', '7_reflection'],
    '智能层': ['8_active_exploration', '9_collaboration', '10_emotional_intelligence', '11_causal_reasoning', '12_transfer_learning', '13_continual_learning', '14_knowledge_distillation', '15_creative_thinking', '16_multimodal', '17_adversarial_robustness'],
    '学习层': ['18_meta_learning', '19_reinforcement_learning', '20_attention', '21_context_awareness', '22_self_healing', '23_knowledge_evolution', '24_predictive_learning', '25_distributed_collaboration', '26_adaptive_architecture', '27_neuro_symbolic', '28_self_supervised', '29_memory_palace', '30_decision_patterns', '31_adaptive_learning_rate', '32_federated_learning'],
    '工程层': ['33_prompt_engineering', '34_task_orchestration', '35_code_generation', '36_test_automation', '37_auto_documentation', '38_performance_optimization', '39_configuration_management', '40_log_analysis', '41_monitoring_alerting', '42_backup_recovery', '43_api_gateway', '44_message_queue'],
    '基础设施': ['45_cache_manager', '46_scheduler', '47_vector_store', '48_session_manager', '49_nlu_engine', '50_recommendation', '51_data_pipeline', '52_feature_engineering', '53_workflow_engine', '54_notification_center'],
    '扩展模块': ['55_encryption_service', '56_search_engine', '57_rate_limiter', '58_plugin_system', '59_stream_processor', '60_distributed_lock', '61_data_sync', '62_model_serving', '63_web_server', '64_i18n', '65_llm_integration', '66_desktop_automation', '67_process_manager', '68_browser_automation', '69_permission_control', '70_toolkit'],
  };

  const getModuleCategory = (key: string): string => {
    for (const [cat, keys] of Object.entries(categories)) {
      if (keys.includes(key)) return cat;
    }
    return '其他';
  };

  const getModuleName = (key: string): string => {
    const parts = key.split('_');
    return parts.slice(1).join('_').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700 }}>📦 模块管理</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="tag tag-accent">{moduleEntries.length} 个模块</span>
        </div>
      </div>

      {/* 搜索 */}
      <div style={{ marginBottom: 16 }}>
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="🔍 搜索模块..."
          style={{
            width: '100%',
            padding: '10px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-primary)',
            fontSize: 14,
            outline: 'none',
          }}
        />
      </div>

      {/* 分类统计 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {Object.entries(categories).map(([cat, keys]) => (
          <span key={cat} className="tag tag-accent" style={{ cursor: 'pointer' }}
            onClick={() => setSearch(keys[0].split('_').slice(1).join('_'))}>
            {cat}: {keys.length}
          </span>
        ))}
      </div>

      {/* 模块列表 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {moduleEntries.map(([key, stats]) => (
          <div
            key={key}
            className="card"
            style={{ cursor: 'pointer', padding: '12px 16px' }}
            onClick={() => setExpanded(expanded === key ? null : key)}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="status-dot online" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{getModuleName(key)}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {getModuleCategory(key)} · {key}
                  </div>
                </div>
              </div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                {expanded === key ? '▲' : '▼'}
              </span>
            </div>

            {expanded === key && (
              <div style={{
                marginTop: 12,
                paddingTop: 12,
                borderTop: '1px solid var(--border)',
                fontSize: 13,
              }}>
                <pre style={{
                  background: 'var(--bg-primary)',
                  padding: 12,
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'auto',
                  maxHeight: 300,
                  fontSize: 12,
                  lineHeight: 1.5,
                }}>
                  {JSON.stringify(stats, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
