"""
================================================================================
反思循环系统 (Reflection Loop System)
================================================================================

核心能力：
  1. 经验提取 - 从成功/失败中提取经验
  2. 模式识别 - 识别重复出现的问题模式
  3. 策略优化 - 基于经验优化应对策略
  4. 知识更新 - 将反思结果更新到知识库
  5. 行为调整 - 根据反思调整未来行为

设计原则：
  - 数据驱动：基于事实而非猜测
  - 持续改进：每次交互都是一次学习机会
  - 可量化：改进效果必须可衡量
"""

import json
import os
import time
import hashlib
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import Counter


# ============================================================================
# 数据结构
# ============================================================================

class ExperienceType(Enum):
    SUCCESS = "success"        # 成功经验
    FAILURE = "failure"        # 失败教训
    INSIGHT = "insight"        # 洞察发现
    MISTAKE = "mistake"        # 错误总结
    DISCOVERY = "discovery"    # 新发现

class ReflectionDepth(Enum):
    SURFACE = 1    # 表面反思：发生了什么
    TACTICAL = 2   # 战术反思：为什么发生
    STRATEGIC = 3  # 战略反思：如何改进
    SYSTEMIC = 4   # 系统反思：根本原因

@dataclass
class Experience:
    """经验记录"""
    id: str
    experience_type: ExperienceType
    context: str                  # 发生背景
    description: str              # 描述
    outcome: str                  # 结果
    factors: list = field(default_factory=list)  # 影响因素
    lessons: list = field(default_factory=list)  # 学到的教训
    confidence: float = 1.0       # 置信度
    impact_score: float = 0.5     # 影响程度 0-1
    created_at: float = field(default_factory=time.time)
    tags: list = field(default_factory=list)
    related_experiences: list = field(default_factory=list)

@dataclass
class Pattern:
    """识别出的模式"""
    id: str
    name: str
    description: str
    occurrences: int = 0          # 出现次数
    examples: list = field(default_factory=list)  # 示例经验ID
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    severity: float = 0.5         # 严重程度
    is_positive: bool = True      # 是否是正面模式

@dataclass
class Strategy:
    """应对策略"""
    id: str
    name: str
    description: str
    trigger_pattern_ids: list     # 触发此策略的模式ID
    actions: list                 # 具体行动
    success_rate: float = 0.0     # 历史成功率
    usage_count: int = 0          # 使用次数
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0

@dataclass
class ReflectionResult:
    """反思结果"""
    experience_id: str
    depth: ReflectionDepth
    insights: list                # 洞察
    action_items: list            # 行动项
    strategy_updates: list        # 策略更新
    knowledge_updates: list       # 知识更新
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 经验提取器
# ============================================================================

class ExperienceExtractor:
    """经验提取器"""

    def __init__(self):
        # 成功指标
        self.success_indicators = [
            '成功', '完成', '解决', '通过', '达到', '实现',
            'success', 'complete', 'solve', 'pass', 'achieve',
        ]
        # 失败指标
        self.failure_indicators = [
            '失败', '错误', '问题', 'bug', '异常', '超时',
            'fail', 'error', 'issue', 'bug', 'exception', 'timeout',
        ]

    def extract_from_interaction(self, interaction: dict) -> Experience:
        """从交互中提取经验"""
        # 判断类型
        experience_type = self._classify_experience(interaction)

        # 提取因素
        factors = self._extract_factors(interaction)

        # 提取教训
        lessons = self._extract_lessons(interaction, experience_type)

        # 计算影响分数
        impact_score = self._calculate_impact(interaction)

        # 创建经验记录
        exp_id = hashlib.md5(
            f"{interaction.get('task', '')}{time.time()}".encode()
        ).hexdigest()[:12]

        return Experience(
            id=exp_id,
            experience_type=experience_type,
            context=interaction.get('context', ''),
            description=interaction.get('task', ''),
            outcome=interaction.get('result', ''),
            factors=factors,
            lessons=lessons,
            confidence=interaction.get('confidence', 0.8),
            impact_score=impact_score,
            tags=interaction.get('tags', []),
        )

    def _classify_experience(self, interaction: dict) -> ExperienceType:
        """分类经验类型"""
        result = interaction.get('result', '').lower()
        error = interaction.get('error', '').lower()

        # 检查失败指标
        for indicator in self.failure_indicators:
            if indicator in result or indicator in error:
                return ExperienceType.FAILURE

        # 检查成功指标
        for indicator in self.success_indicators:
            if indicator in result:
                return ExperienceType.SUCCESS

        # 根据置信度判断
        if interaction.get('confidence', 0.5) < 0.4:
            return ExperienceType.MISTAKE

        return ExperienceType.INSIGHT

    def _extract_factors(self, interaction: dict) -> list:
        """提取影响因素"""
        factors = []

        # 任务复杂度
        task = interaction.get('task', '')
        if len(task) > 200:
            factors.append("任务复杂度高")

        # 领域知识
        domain = interaction.get('domain', '')
        if domain:
            factors.append(f"领域: {domain}")

        # 工具使用
        tools = interaction.get('tools_used', [])
        if tools:
            factors.append(f"使用工具: {', '.join(tools)}")

        # 时间压力
        if interaction.get('time_pressure'):
            factors.append("存在时间压力")

        return factors

    def _extract_lessons(self, interaction: dict,
                          experience_type: ExperienceType) -> list:
        """提取教训"""
        lessons = []

        if experience_type == ExperienceType.FAILURE:
            error = interaction.get('error', '')
            if 'timeout' in error.lower():
                lessons.append("需要优化执行效率或增加超时时间")
            elif 'permission' in error.lower():
                lessons.append("需要检查权限配置")
            elif 'not found' in error.lower():
                lessons.append("需要验证资源是否存在")

        elif experience_type == ExperienceType.SUCCESS:
            # 成功经验也值得总结
            if interaction.get('confidence', 0) > 0.9:
                lessons.append("高置信度决策通常可靠")

        return lessons

    def _calculate_impact(self, interaction: dict) -> float:
        """计算影响分数"""
        impact = 0.5

        # 任务重要性
        if interaction.get('priority') == 'critical':
            impact += 0.3
        elif interaction.get('priority') == 'high':
            impact += 0.2

        # 是否有后续影响
        if interaction.get('has_side_effects'):
            impact += 0.1

        return min(1.0, impact)


# ============================================================================
# 模式识别器
# ============================================================================

class PatternRecognizer:
    """模式识别器"""

    def __init__(self):
        self.experiences: list[Experience] = []
        self.patterns: dict[str, Pattern] = {}

    def add_experience(self, experience: Experience):
        """添加经验并识别模式"""
        self.experiences.append(experience)
        self._detect_patterns(experience)

    def _detect_patterns(self, experience: Experience):
        """检测模式"""
        # 基于因素的模式
        for factor in experience.factors:
            pattern_id = hashlib.md5(f"factor:{factor}".encode()).hexdigest()[:12]

            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.occurrences += 1
                pattern.last_seen = time.time()
                if experience.id not in pattern.examples:
                    pattern.examples.append(experience.id)
            else:
                self.patterns[pattern_id] = Pattern(
                    id=pattern_id,
                    name=f"因素模式: {factor}",
                    description=f"与 {factor} 相关的经验",
                    occurrences=1,
                    examples=[experience.id],
                    is_positive=experience.experience_type == ExperienceType.SUCCESS,
                )

        # 基于教训的模式
        for lesson in experience.lessons:
            pattern_id = hashlib.md5(f"lesson:{lesson}".encode()).hexdigest()[:12]

            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.occurrences += 1
                pattern.last_seen = time.time()
            else:
                self.patterns[pattern_id] = Pattern(
                    id=pattern_id,
                    name=f"教训模式: {lesson[:30]}",
                    description=lesson,
                    occurrences=1,
                    examples=[experience.id],
                    is_positive=False,
                )

        # 基于标签的模式
        for tag in experience.tags:
            pattern_id = hashlib.md5(f"tag:{tag}".encode()).hexdigest()[:12]

            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern.occurrences += 1
                pattern.last_seen = time.time()
            else:
                self.patterns[pattern_id] = Pattern(
                    id=pattern_id,
                    name=f"标签模式: {tag}",
                    description=f"与标签 {tag} 相关的经验",
                    occurrences=1,
                    examples=[experience.id],
                    is_positive=True,
                )

    def get_frequent_patterns(self, min_occurrences: int = 3) -> list:
        """获取频繁模式"""
        return [
            p for p in self.patterns.values()
            if p.occurrences >= min_occurrences
        ]

    def get_negative_patterns(self) -> list:
        """获取负面模式"""
        return [p for p in self.patterns.values() if not p.is_positive]

    def get_pattern_summary(self) -> dict:
        """获取模式摘要"""
        total = len(self.patterns)
        positive = sum(1 for p in self.patterns.values() if p.is_positive)
        negative = total - positive
        frequent = len(self.get_frequent_patterns())

        return {
            'total_patterns': total,
            'positive_patterns': positive,
            'negative_patterns': negative,
            'frequent_patterns': frequent,
        }


# ============================================================================
# 策略优化器
# ============================================================================

class StrategyOptimizer:
    """策略优化器"""

    def __init__(self):
        self.strategies: dict[str, Strategy] = {}

    def create_strategy(self, pattern: Pattern,
                         actions: list) -> Strategy:
        """为模式创建策略"""
        strategy_id = hashlib.md5(
            f"strategy:{pattern.id}".encode()
        ).hexdigest()[:12]

        strategy = Strategy(
            id=strategy_id,
            name=f"应对 {pattern.name}",
            description=f"针对 {pattern.description} 的应对策略",
            trigger_pattern_ids=[pattern.id],
            actions=actions,
        )

        self.strategies[strategy_id] = strategy
        return strategy

    def update_strategy(self, strategy_id: str, success: bool):
        """根据使用结果更新策略"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return

        strategy.usage_count += 1
        strategy.last_used = time.time()

        # 更新成功率
        total = strategy.usage_count
        strategy.success_rate = (
            (strategy.success_rate * (total - 1) + (1.0 if success else 0.0)) / total
        )

    def get_best_strategy(self, pattern_id: str) -> Optional[Strategy]:
        """获取最佳策略"""
        candidates = [
            s for s in self.strategies.values()
            if pattern_id in s.trigger_pattern_ids
        ]

        if not candidates:
            return None

        # 按成功率排序
        candidates.sort(key=lambda s: s.success_rate, reverse=True)
        return candidates[0]

    def get_strategy_recommendations(self, pattern: Pattern) -> list:
        """获取策略推荐"""
        # 检查现有策略
        existing = [
            s for s in self.strategies.values()
            if pattern.id in s.trigger_pattern_ids
        ]

        if existing:
            return [{
                'strategy': s.name,
                'success_rate': s.success_rate,
                'actions': s.actions,
            } for s in sorted(existing, key=lambda x: x.success_rate, reverse=True)]

        # 生成新策略建议
        recommendations = []

        if not pattern.is_positive:
            recommendations.append({
                'strategy': '预防策略',
                'description': f'避免触发 {pattern.name}',
                'actions': [
                    '识别触发条件',
                    '提前采取预防措施',
                    '建立检查清单',
                ],
            })
            recommendations.append({
                'strategy': '缓解策略',
                'description': f'减轻 {pattern.name} 的影响',
                'actions': [
                    '建立快速响应机制',
                    '准备备用方案',
                    '设置监控告警',
                ],
            })

        return recommendations


# ============================================================================
# 反思引擎
# ============================================================================

class ReflectionEngine:
    """
    反思引擎 - 整合所有组件

    核心功能：
    1. 从交互中提取经验
    2. 识别重复模式
    3. 生成和优化策略
    4. 更新知识库
    5. 调整未来行为
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "reflection"
        os.makedirs(storage_dir, exist_ok=True)

        self.extractor = ExperienceExtractor()
        self.pattern_recognizer = PatternRecognizer()
        self.strategy_optimizer = StrategyOptimizer()

        self.experiences: list[Experience] = []
        self.reflections: list[ReflectionResult] = []

        self.storage_path = os.path.join(storage_dir, "reflections.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for e_data in data.get('experiences', []):
                    e_data['experience_type'] = ExperienceType(e_data['experience_type'])
                    exp = Experience(**e_data)
                    self.experiences.append(exp)
                    self.pattern_recognizer.add_experience(exp)

    def _save(self):
        """保存数据"""
        data = {
            'experiences': [],
        }
        for exp in self.experiences:
            e_dict = asdict(exp)
            e_dict['experience_type'] = exp.experience_type.value
            data['experiences'].append(e_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def reflect_on_interaction(self, interaction: dict) -> ReflectionResult:
        """对交互进行反思"""
        # 1. 提取经验
        experience = self.extractor.extract_from_interaction(interaction)
        self.experiences.append(experience)

        # 2. 识别模式
        self.pattern_recognizer.add_experience(experience)

        # 3. 深度反思
        depth = self._determine_reflection_depth(experience)
        insights = self._generate_insights(experience, depth)
        action_items = self._generate_action_items(experience, insights)
        strategy_updates = self._update_strategies(experience)
        knowledge_updates = self._extract_knowledge_updates(experience)

        # 4. 创建反思结果
        result = ReflectionResult(
            experience_id=experience.id,
            depth=depth,
            insights=insights,
            action_items=action_items,
            strategy_updates=strategy_updates,
            knowledge_updates=knowledge_updates,
        )

        self.reflections.append(result)
        self._save()

        return result

    def _determine_reflection_depth(self, experience: Experience) -> ReflectionDepth:
        """确定反思深度"""
        if experience.impact_score >= 0.8:
            return ReflectionDepth.SYSTEMIC
        elif experience.impact_score >= 0.6:
            return ReflectionDepth.STRATEGIC
        elif experience.experience_type in (ExperienceType.FAILURE, ExperienceType.MISTAKE):
            return ReflectionDepth.TACTICAL
        else:
            return ReflectionDepth.SURFACE

    def _generate_insights(self, experience: Experience,
                            depth: ReflectionDepth) -> list:
        """生成洞察"""
        insights = []

        # 表面洞察
        insights.append(f"发生了: {experience.description}")
        insights.append(f"结果: {experience.outcome}")

        # 战术洞察
        if depth.value >= ReflectionDepth.TACTICAL.value:
            if experience.experience_type == ExperienceType.FAILURE:
                insights.append(f"失败原因: {', '.join(experience.factors)}")
            elif experience.experience_type == ExperienceType.SUCCESS:
                insights.append(f"成功因素: {', '.join(experience.factors)}")

        # 战略洞察
        if depth.value >= ReflectionDepth.STRATEGIC.value:
            patterns = self.pattern_recognizer.get_frequent_patterns()
            related_patterns = [
                p for p in patterns
                if any(f in p.name for f in experience.factors)
            ]
            if related_patterns:
                insights.append(f"识别到重复模式: {len(related_patterns)}个")

        # 系统洞察
        if depth.value >= ReflectionDepth.SYSTEMIC.value:
            negative_patterns = self.pattern_recognizer.get_negative_patterns()
            if negative_patterns:
                insights.append(f"存在 {len(negative_patterns)} 个需要改进的模式")

        return insights

    def _generate_action_items(self, experience: Experience,
                                insights: list) -> list:
        """生成行动项"""
        action_items = []

        if experience.experience_type == ExperienceType.FAILURE:
            action_items.append({
                'action': '分析失败根因',
                'priority': 'high',
                'deadline': 'immediate',
            })
            action_items.append({
                'action': '制定预防措施',
                'priority': 'high',
                'deadline': 'short_term',
            })

        elif experience.experience_type == ExperienceType.MISTAKE:
            action_items.append({
                'action': '记录错误模式',
                'priority': 'medium',
                'deadline': 'immediate',
            })

        # 基于教训生成
        for lesson in experience.lessons:
            action_items.append({
                'action': f'应用教训: {lesson}',
                'priority': 'medium',
                'deadline': 'ongoing',
            })

        return action_items

    def _update_strategies(self, experience: Experience) -> list:
        """更新策略"""
        updates = []

        # 查找相关模式
        for pattern in self.pattern_recognizer.patterns.values():
            if any(f in pattern.name for f in experience.factors):
                # 检查是否有策略
                strategy = self.strategy_optimizer.get_best_strategy(pattern.id)

                if strategy:
                    # 更新现有策略
                    success = experience.experience_type == ExperienceType.SUCCESS
                    self.strategy_optimizer.update_strategy(strategy.id, success)
                    updates.append({
                        'strategy_id': strategy.id,
                        'action': 'updated',
                        'new_success_rate': strategy.success_rate,
                    })
                else:
                    # 创建新策略
                    if not pattern.is_positive:
                        new_strategy = self.strategy_optimizer.create_strategy(
                            pattern,
                            actions=['识别触发条件', '采取预防措施']
                        )
                        updates.append({
                            'strategy_id': new_strategy.id,
                            'action': 'created',
                        })

        return updates

    def _extract_knowledge_updates(self, experience: Experience) -> list:
        """提取知识更新"""
        updates = []

        for lesson in experience.lessons:
            updates.append({
                'type': 'lesson',
                'content': lesson,
                'confidence': experience.confidence,
                'source': experience.id,
            })

        return updates

    def get_recommendations(self, context: str) -> list:
        """根据上下文获取推荐"""
        recommendations = []

        # 基于模式推荐
        negative_patterns = self.pattern_recognizer.get_negative_patterns()
        for pattern in negative_patterns[:3]:
            strategy = self.strategy_optimizer.get_best_strategy(pattern.id)
            if strategy:
                recommendations.append({
                    'type': 'strategy',
                    'pattern': pattern.name,
                    'strategy': strategy.name,
                    'actions': strategy.actions,
                    'success_rate': strategy.success_rate,
                })
            else:
                # 生成建议
                recs = self.strategy_optimizer.get_strategy_recommendations(pattern)
                recommendations.extend(recs)

        return recommendations

    def get_learning_summary(self) -> dict:
        """获取学习摘要"""
        total_exp = len(self.experiences)
        success_exp = sum(1 for e in self.experiences
                         if e.experience_type == ExperienceType.SUCCESS)
        failure_exp = sum(1 for e in self.experiences
                         if e.experience_type == ExperienceType.FAILURE)

        pattern_summary = self.pattern_recognizer.get_pattern_summary()

        return {
            'total_experiences': total_exp,
            'success_count': success_exp,
            'failure_count': failure_exp,
            'success_rate': success_exp / total_exp if total_exp > 0 else 0,
            'patterns': pattern_summary,
            'strategies_count': len(self.strategy_optimizer.strategies),
            'reflections_count': len(self.reflections),
        }

    def generate_report(self) -> str:
        """生成反思报告"""
        summary = self.get_learning_summary()

        report = []
        report.append("=" * 50)
        report.append("🔄 反思循环学习报告")
        report.append("=" * 50)
        report.append(f"\n经验总数: {summary['total_experiences']}")
        report.append(f"  成功: {summary['success_count']}")
        report.append(f"  失败: {summary['failure_count']}")
        report.append(f"  成功率: {summary['success_rate']:.0%}")

        report.append(f"\n模式识别:")
        report.append(f"  总模式数: {summary['patterns']['total_patterns']}")
        report.append(f"  正面模式: {summary['patterns']['positive_patterns']}")
        report.append(f"  负面模式: {summary['patterns']['negative_patterns']}")
        report.append(f"  频繁模式: {summary['patterns']['frequent_patterns']}")

        report.append(f"\n策略优化:")
        report.append(f"  策略总数: {summary['strategies_count']}")

        # 最近教训
        recent_lessons = []
        for exp in self.experiences[-5:]:
            recent_lessons.extend(exp.lessons)
        if recent_lessons:
            report.append("\n最近教训:")
            for lesson in set(recent_lessons[-5:]):
                report.append(f"  - {lesson}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = ReflectionEngine("test_reflection")

    # 模拟交互
    interactions = [
        {
            'task': '读取配置文件',
            'result': '成功读取配置',
            'confidence': 0.95,
            'domain': 'file_io',
            'tags': ['config', 'file'],
        },
        {
            'task': '连接数据库',
            'result': '连接失败',
            'error': 'timeout after 30s',
            'confidence': 0.3,
            'domain': 'database',
            'tags': ['database', 'connection'],
        },
        {
            'task': '部署服务',
            'result': '部署失败',
            'error': 'permission denied',
            'confidence': 0.4,
            'domain': 'deployment',
            'tags': ['deploy', 'permission'],
        },
        {
            'task': '优化查询',
            'result': '成功优化，性能提升50%',
            'confidence': 0.9,
            'domain': 'database',
            'tags': ['database', 'optimization'],
        },
    ]

    # 反思
    print("=== 反思过程 ===")
    for interaction in interactions:
        result = engine.reflect_on_interaction(interaction)
        print(f"\n任务: {interaction['task']}")
        print(f"  深度: {result.depth.name}")
        print(f"  洞察: {result.insights}")
        print(f"  行动项: {len(result.action_items)}个")

    # 推荐
    print("\n=== 推荐 ===")
    recommendations = engine.get_recommendations("database")
    for rec in recommendations[:3]:
        print(f"  - {rec.get('strategy', rec.get('type'))}: {rec.get('description', '')}")

    # 报告
    print("\n" + engine.generate_report())