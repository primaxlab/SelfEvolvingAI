"""
================================================================================
主动探索系统 (Active Exploration System)
================================================================================

核心能力：
  1. 知识空白发现 - 主动识别自己不知道的领域
  2. 探索策略生成 - 制定学习计划
  3. 资源定位 - 找到学习资源
  4. 自主学习 - 主动获取新知识
  5. 知识验证 - 验证学到的知识是否正确

设计原则：
  - 好奇心驱动：对未知领域保持探索欲望
  - 目标导向：探索是为了填补知识空白
  - 效率优先：优先探索高价值领域
"""

import json
import os
import time
import hashlib
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class ExplorationStatus(Enum):
    PENDING = "pending"          # 待探索
    IN_PROGRESS = "in_progress"  # 探索中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    DEFERRED = "deferred"       # 已推迟

class ExplorationPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class KnowledgeGap:
    """知识空白"""
    id: str
    domain: str
    topic: str
    description: str
    priority: ExplorationPriority = ExplorationPriority.MEDIUM
    estimated_effort: float = 1.0  # 预估学习时长(小时)
    potential_value: float = 0.5   # 潜在价值 0-1
    status: ExplorationStatus = ExplorationStatus.PENDING
    discovered_at: float = field(default_factory=time.time)
    last_attempted: float = 0.0
    attempt_count: int = 0
    resources: list = field(default_factory=list)  # 学习资源
    progress: float = 0.0  # 学习进度 0-1

@dataclass
class ExplorationPlan:
    """探索计划"""
    id: str
    gap_id: str
    steps: list  # 探索步骤
    resources: list  # 学习资源
    estimated_duration: float  # 预估时长
    status: ExplorationStatus = ExplorationStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0

@dataclass
class ExplorationResult:
    """探索结果"""
    id: str
    gap_id: str
    plan_id: str
    knowledge_gained: list  # 获得的知识
    confidence: float  # 置信度
    remaining_gaps: list  # 剩余空白
    success: bool = True
    error: str = ""
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 知识空白发现器
# ============================================================================

class GapDiscoverer:
    """知识空白发现器"""

    def __init__(self):
        # 空白检测策略
        self.detection_strategies = [
            self._detect_from_failures,
            self._detect_from_uncertainty,
            self._detect_from_questions,
            self._detect_from_domains,
        ]

    def discover(self, context: dict) -> list:
        """发现知识空白"""
        gaps = []

        for strategy in self.detection_strategies:
            try:
                found = strategy(context)
                gaps.extend(found)
            except Exception:
                continue

        # 去重
        unique_gaps = self._deduplicate(gaps)

        # 按优先级排序
        unique_gaps.sort(key=lambda g: g.priority.value, reverse=True)

        return unique_gaps

    def _detect_from_failures(self, context: dict) -> list:
        """从失败中检测空白"""
        gaps = []
        failures = context.get('failures', [])

        for failure in failures:
            domain = failure.get('domain', 'unknown')
            error = failure.get('error', '')

            gap = KnowledgeGap(
                id=hashlib.md5(f"fail:{domain}:{error}".encode()).hexdigest()[:12],
                domain=domain,
                topic=failure.get('task', ''),
                description=f"失败原因: {error}",
                priority=ExplorationPriority.HIGH,
                potential_value=0.7,
            )
            gaps.append(gap)

        return gaps

    def _detect_from_uncertainty(self, context: dict) -> list:
        """从不确定性中检测空白"""
        gaps = []
        low_confidence = context.get('low_confidence_interactions', [])

        for interaction in low_confidence:
            if interaction.get('confidence', 1.0) < 0.4:
                domain = interaction.get('domain', 'unknown')

                gap = KnowledgeGap(
                    id=hashlib.md5(f"unc:{domain}:{interaction.get('task', '')}".encode()).hexdigest()[:12],
                    domain=domain,
                    topic=interaction.get('task', ''),
                    description=f"置信度过低: {interaction.get('confidence', 0):.2f}",
                    priority=ExplorationPriority.MEDIUM,
                    potential_value=0.5,
                )
                gaps.append(gap)

        return gaps

    def _detect_from_questions(self, context: dict) -> list:
        """从未能回答的问题中检测空白"""
        gaps = []
        unanswered = context.get('unanswered_questions', [])

        for question in unanswered:
            gap = KnowledgeGap(
                id=hashlib.md5(f"q:{question}".encode()).hexdigest()[:12],
                domain='general',
                topic=question[:100],
                description=f"无法回答的问题: {question[:200]}",
                priority=ExplorationPriority.MEDIUM,
                potential_value=0.6,
            )
            gaps.append(gap)

        return gaps

    def _detect_from_domains(self, context: dict) -> list:
        """从领域覆盖中检测空白"""
        gaps = []
        known_domains = context.get('known_domains', [])
        target_domains = context.get('target_domains', [])

        for domain in target_domains:
            if domain not in known_domains:
                gap = KnowledgeGap(
                    id=hashlib.md5(f"dom:{domain}".encode()).hexdigest()[:12],
                    domain=domain,
                    topic=f"{domain}领域知识",
                    description=f"尚未学习{domain}领域",
                    priority=ExplorationPriority.LOW,
                    potential_value=0.4,
                )
                gaps.append(gap)

        return gaps

    def _deduplicate(self, gaps: list) -> list:
        """去重"""
        seen = set()
        unique = []

        for gap in gaps:
            key = f"{gap.domain}:{gap.topic}"
            if key not in seen:
                seen.add(key)
                unique.append(gap)

        return unique


# ============================================================================
# 探索策略生成器
# ============================================================================

class StrategyGenerator:
    """探索策略生成器"""

    def __init__(self):
        self.strategy_templates = {
            'research': {
                'name': '研究学习',
                'steps': [
                    '收集相关资料',
                    '阅读和理解核心概念',
                    '总结关键知识点',
                    '验证理解是否正确',
                ],
            },
            'practice': {
                'name': '实践学习',
                'steps': [
                    '找到实践项目',
                    '动手实现',
                    '遇到问题并解决',
                    '总结经验教训',
                ],
            },
            'experiment': {
                'name': '实验验证',
                'steps': [
                    '提出假设',
                    '设计实验',
                    '执行实验',
                    '分析结果',
                ],
            },
            'collaborate': {
                'name': '协作学习',
                'steps': [
                    '找到专家或同伴',
                    '讨论和交流',
                    '获取反馈',
                    '整合新知识',
                ],
            },
        }

    def generate(self, gap: KnowledgeGap) -> ExplorationPlan:
        """为知识空白生成探索计划"""
        # 选择策略
        strategy = self._select_strategy(gap)

        # 生成步骤
        steps = self._generate_steps(gap, strategy)

        # 生成资源
        resources = self._generate_resources(gap)

        # 估算时长
        duration = self._estimate_duration(gap, strategy)

        plan = ExplorationPlan(
            id=f"plan_{gap.id}",
            gap_id=gap.id,
            steps=steps,
            resources=resources,
            estimated_duration=duration,
        )

        return plan

    def _select_strategy(self, gap: KnowledgeGap) -> dict:
        """选择探索策略"""
        # 根据领域和优先级选择
        if gap.priority == ExplorationPriority.CRITICAL:
            return self.strategy_templates['practice']
        elif gap.domain in ['programming', 'technology']:
            return self.strategy_templates['practice']
        elif gap.domain in ['science', 'math']:
            return self.strategy_templates['research']
        else:
            return self.strategy_templates['research']

    def _generate_steps(self, gap: KnowledgeGap, strategy: dict) -> list:
        """生成探索步骤"""
        steps = []

        for i, step in enumerate(strategy['steps']):
            steps.append({
                'order': i + 1,
                'action': step,
                'description': f"针对{gap.topic}: {step}",
                'estimated_duration': gap.estimated_effort / len(strategy['steps']),
            })

        return steps

    def _generate_resources(self, gap: KnowledgeGap) -> list:
        """生成学习资源"""
        resources = []

        # 通用资源
        resources.append({
            'type': 'search',
            'query': f"{gap.domain} {gap.topic} 教程",
            'description': '搜索相关教程',
        })

        resources.append({
            'type': 'documentation',
            'query': f"{gap.topic} 官方文档",
            'description': '查找官方文档',
        })

        if gap.domain == 'programming':
            resources.append({
                'type': 'code',
                'query': f"{gap.topic} 示例代码",
                'description': '查找示例代码',
            })

        return resources

    def _estimate_duration(self, gap: KnowledgeGap, strategy: dict) -> float:
        """估算学习时长"""
        base_duration = gap.estimated_effort

        # 根据策略调整
        if strategy['name'] == '实践学习':
            base_duration *= 1.5  # 实践需要更多时间
        elif strategy['name'] == '协作学习':
            base_duration *= 0.8  # 协作可以更快

        return base_duration


# ============================================================================
# 自主学习器
# ============================================================================

class SelfLearner:
    """自主学习器"""

    def __init__(self):
        self.learning_history: list[dict] = []

    def learn(self, plan: ExplorationPlan, context: dict = None) -> ExplorationResult:
        """执行学习计划"""
        context = context or {}
        knowledge_gained = []
        remaining_gaps = []

        # 模拟学习过程
        for step in plan.steps:
            # 执行步骤
            step_result = self._execute_step(step, context)

            if step_result['success']:
                knowledge_gained.extend(step_result.get('knowledge', []))
            else:
                remaining_gaps.append({
                    'step': step,
                    'error': step_result.get('error', ''),
                })

        # 计算置信度
        confidence = len(knowledge_gained) / max(1, len(plan.steps))

        # 创建结果
        result = ExplorationResult(
            id=f"result_{plan.id}",
            gap_id=plan.gap_id,
            plan_id=plan.id,
            knowledge_gained=knowledge_gained,
            confidence=confidence,
            remaining_gaps=remaining_gaps,
            success=len(remaining_gaps) == 0,
        )

        # 记录学习历史
        self.learning_history.append({
            'plan_id': plan.id,
            'result': asdict(result),
            'timestamp': time.time(),
        })

        return result

    def _execute_step(self, step: dict, context: dict) -> dict:
        """执行学习步骤"""
        # 这里是框架，实际使用时接入搜索/阅读等工具
        action = step.get('action', '')

        # 模拟成功
        return {
            'success': True,
            'knowledge': [
                {
                    'topic': step.get('description', ''),
                    'content': f"学习了: {action}",
                    'confidence': 0.7,
                }
            ],
        }

    def get_learning_stats(self) -> dict:
        """获取学习统计"""
        total = len(self.learning_history)
        successful = sum(1 for h in self.learning_history if h['result']['success'])

        return {
            'total_explorations': total,
            'successful': successful,
            'success_rate': successful / max(1, total),
            'knowledge_items': sum(
                len(h['result']['knowledge_gained'])
                for h in self.learning_history
            ),
        }


# ============================================================================
# 主动探索引擎
# ============================================================================

class ActiveExplorationEngine:
    """
    主动探索引擎 - 整合所有组件

    核心功能：
    1. 发现知识空白
    2. 生成探索计划
    3. 执行自主学习
    4. 更新知识库
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "exploration"
        os.makedirs(storage_dir, exist_ok=True)

        self.gap_discoverer = GapDiscoverer()
        self.strategy_generator = StrategyGenerator()
        self.self_learner = SelfLearner()

        self.knowledge_gaps: dict[str, KnowledgeGap] = {}
        self.exploration_plans: dict[str, ExplorationPlan] = {}
        self.exploration_results: list[ExplorationResult] = []

        self.storage_path = os.path.join(storage_dir, "exploration.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for g_data in data.get('gaps', []):
                    g_data['priority'] = ExplorationPriority(g_data['priority'])
                    g_data['status'] = ExplorationStatus(g_data['status'])
                    gap = KnowledgeGap(**g_data)
                    self.knowledge_gaps[gap.id] = gap

    def _save(self):
        """保存数据"""
        data = {
            'gaps': [],
        }

        for gap in self.knowledge_gaps.values():
            g_dict = asdict(gap)
            g_dict['priority'] = gap.priority.value
            g_dict['status'] = gap.status.value
            data['gaps'].append(g_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def discover_gaps(self, context: dict) -> list:
        """发现知识空白"""
        gaps = self.gap_discoverer.discover(context)

        # 添加到知识空白库
        for gap in gaps:
            self.knowledge_gaps[gap.id] = gap

        self._save()
        return gaps

    def create_plan(self, gap_id: str) -> Optional[ExplorationPlan]:
        """为知识空白创建探索计划"""
        gap = self.knowledge_gaps.get(gap_id)
        if not gap:
            return None

        plan = self.strategy_generator.generate(gap)
        self.exploration_plans[plan.id] = plan

        # 更新空白状态
        gap.status = ExplorationStatus.IN_PROGRESS
        gap.last_attempted = time.time()
        gap.attempt_count += 1

        self._save()
        return plan

    def execute_plan(self, plan_id: str, context: dict = None) -> ExplorationResult:
        """执行探索计划"""
        plan = self.exploration_plans.get(plan_id)
        if not plan:
            return ExplorationResult(
                id=f"result_{plan_id}",
                gap_id="",
                plan_id=plan_id,
                knowledge_gained=[],
                confidence=0.0,
                remaining_gaps=[],
                success=False,
                error="计划不存在",
            )

        # 执行学习
        result = self.self_learner.learn(plan, context)
        self.exploration_results.append(result)

        # 更新空白状态
        gap = self.knowledge_gaps.get(plan.gap_id)
        if gap:
            if result.success:
                gap.status = ExplorationStatus.COMPLETED
                gap.progress = 1.0
            else:
                gap.status = ExplorationStatus.PENDING
                gap.progress = result.confidence

        self._save()
        return result

    def explore(self, context: dict) -> dict:
        """执行一次完整的探索循环"""
        # 1. 发现空白
        gaps = self.discover_gaps(context)

        if not gaps:
            return {
                'status': 'no_gaps',
                'message': '未发现知识空白',
            }

        # 2. 选择最高优先级的空白
        top_gap = gaps[0]

        # 3. 创建计划
        plan = self.create_plan(top_gap.id)
        if not plan:
            return {
                'status': 'plan_failed',
                'message': '无法创建探索计划',
            }

        # 4. 执行计划
        result = self.execute_plan(plan.id, context)

        return {
            'status': 'completed' if result.success else 'partial',
            'gap': asdict(top_gap),
            'plan': asdict(plan),
            'result': asdict(result),
        }

    def get_pending_gaps(self) -> list:
        """获取待探索的空白"""
        return [
            asdict(gap) for gap in self.knowledge_gaps.values()
            if gap.status == ExplorationStatus.PENDING
        ]

    def get_exploration_stats(self) -> dict:
        """获取探索统计"""
        total_gaps = len(self.knowledge_gaps)
        completed = sum(
            1 for g in self.knowledge_gaps.values()
            if g.status == ExplorationStatus.COMPLETED
        )

        return {
            'total_gaps': total_gaps,
            'completed': completed,
            'pending': total_gaps - completed,
            'learner_stats': self.self_learner.get_learning_stats(),
        }

    def generate_report(self) -> str:
        """生成探索报告"""
        stats = self.get_exploration_stats()

        report = []
        report.append("=" * 50)
        report.append("🔍 主动探索报告")
        report.append("=" * 50)
        report.append(f"\n知识空白总数: {stats['total_gaps']}")
        report.append(f"已完成探索: {stats['completed']}")
        report.append(f"待探索: {stats['pending']}")
        report.append(f"\n学习统计:")
        report.append(f"  总探索次数: {stats['learner_stats']['total_explorations']}")
        report.append(f"  成功率: {stats['learner_stats']['success_rate']:.0%}")
        report.append(f"  获得知识项: {stats['learner_stats']['knowledge_items']}")

        # 最近的空白
        pending = self.get_pending_gaps()
        if pending:
            report.append(f"\n待探索空白 (前5个):")
            for gap in pending[:5]:
                report.append(f"  - [{gap['priority']}] {gap['domain']}: {gap['topic'][:50]}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = ActiveExplorationEngine("test_exploration")

    # 模拟上下文
    context = {
        'failures': [
            {'domain': 'database', 'task': '连接数据库', 'error': 'timeout'},
            {'domain': 'deployment', 'task': '部署服务', 'error': 'permission denied'},
        ],
        'low_confidence_interactions': [
            {'domain': 'machine_learning', 'task': '神经网络优化', 'confidence': 0.3},
        ],
        'unanswered_questions': [
            '量子计算的基本原理是什么？',
        ],
        'known_domains': ['python', 'web'],
        'target_domains': ['python', 'web', 'machine_learning', 'devops'],
    }

    # 执行探索
    print("=== 执行探索 ===")
    result = engine.explore(context)
    print(f"状态: {result['status']}")
    if result.get('gap'):
        print(f"探索空白: {result['gap']['domain']} - {result['gap']['topic']}")

    # 报告
    print("\n" + engine.generate_report())