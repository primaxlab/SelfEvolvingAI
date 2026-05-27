"""
================================================================================
元学习系统 (Meta-Learning System)
================================================================================

核心能力：
  1. 学习策略优化 - 学习如何更有效地学习
  2. 学习速度调节 - 根据任务难度调整学习速度
  3. 迁移能力评估 - 评估知识迁移的有效性
  4. 学习方法推荐 - 推荐最适合的学习方法
  5. 学习效果预测 - 预测学习方法的效果

设计原则：
  - 学会学习：不只是学知识，更要学方法
  - 自适应：根据反馈不断调整学习策略
  - 可迁移：学习方法要能迁移到新领域
"""

import json
import os
import time
import hashlib
import math
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class LearningStrategy(Enum):
    REPETITION = "repetition"           # 重复学习
    SPACED = "spaced"                   # 间隔重复
    INTERLEAVING = "interleaving"       # 交错学习
    ELABORATIVE = "elaborative"         # 精细加工
    RETRIEVAL = "retrieval"             # 检索练习
    TEACHING = "teaching"               # 教学相长
    ANALOGY = "analogy"                 # 类比学习
    CHUNKING = "chunking"               # 组块学习

class TaskDifficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4

@dataclass
class LearningSession:
    """学习会话"""
    id: str
    strategy: LearningStrategy
    domain: str
    difficulty: TaskDifficulty
    duration: float              # 学习时长(秒)
    items_learned: int           # 学习的知识点数量
    retention_rate: float        # 保留率 0-1
    efficiency: float            # 效率 0-1
    feedback_score: float        # 反馈分数 0-1
    timestamp: float = field(default_factory=time.time)

@dataclass
class LearningPattern:
    """学习模式"""
    id: str
    strategy: LearningStrategy
    domain: str
    difficulty: TaskDifficulty
    success_rate: float
    avg_efficiency: float
    usage_count: int = 0
    last_used: float = 0.0

@dataclass
class MetaKnowledge:
    """元知识"""
    id: str
    rule: str                    # 规则描述
    conditions: list             # 适用条件
    recommendation: str          # 推荐
    confidence: float
    examples: list = field(default_factory=list)


# ============================================================================
# 学习策略分析器
# ============================================================================

class StrategyAnalyzer:
    """学习策略分析器"""

    def __init__(self):
        self.session_history: list[LearningSession] = []
        self.patterns: dict[str, LearningPattern] = {}

    def analyze_session(self, session: LearningSession) -> dict:
        """分析学习会话"""
        self.session_history.append(session)

        # 更新模式
        pattern_key = f"{session.strategy.value}:{session.domain}:{session.difficulty.value}"
        if pattern_key in self.patterns:
            pattern = self.patterns[pattern_key]
            pattern.usage_count += 1
            pattern.avg_efficiency = (
                (pattern.avg_efficiency * (pattern.usage_count - 1) + session.efficiency) /
                pattern.usage_count
            )
            pattern.success_rate = (
                (pattern.success_rate * (pattern.usage_count - 1) + (1 if session.retention_rate > 0.6 else 0)) /
                pattern.usage_count
            )
        else:
            self.patterns[pattern_key] = LearningPattern(
                id=pattern_key,
                strategy=session.strategy,
                domain=session.domain,
                difficulty=session.difficulty,
                success_rate=1 if session.retention_rate > 0.6 else 0,
                avg_efficiency=session.efficiency,
                usage_count=1,
            )

        return {
            'session_id': session.id,
            'efficiency': session.efficiency,
            'retention': session.retention_rate,
            'pattern_updated': pattern_key,
        }

    def get_best_strategy(self, domain: str,
                           difficulty: TaskDifficulty) -> Optional[LearningStrategy]:
        """获取最佳学习策略"""
        candidates = [
            p for p in self.patterns.values()
            if p.domain == domain and p.difficulty == difficulty
        ]

        if not candidates:
            # 默认推荐
            if difficulty == TaskDifficulty.EASY:
                return LearningStrategy.REPETITION
            elif difficulty == TaskDifficulty.MEDIUM:
                return LearningStrategy.SPACED
            else:
                return LearningStrategy.INTERLEAVING

        # 按效率排序
        candidates.sort(key=lambda p: p.avg_efficiency, reverse=True)
        return candidates[0].strategy

    def get_strategy_stats(self) -> dict:
        """获取策略统计"""
        stats = {}
        for strategy in LearningStrategy:
            sessions = [s for s in self.session_history if s.strategy == strategy]
            if sessions:
                stats[strategy.value] = {
                    'count': len(sessions),
                    'avg_efficiency': sum(s.efficiency for s in sessions) / len(sessions),
                    'avg_retention': sum(s.retention_rate for s in sessions) / len(sessions),
                }
        return stats


# ============================================================================
# 学习速度调节器
# ============================================================================

class LearningRateAdapter:
    """学习速度调节器"""

    def __init__(self):
        self.base_rate = 0.1
        self.current_rate = 0.1
        self.performance_history: list[float] = []

    def adapt(self, performance: float) -> float:
        """根据表现调整学习速度"""
        self.performance_history.append(performance)

        # 计算趋势
        if len(self.performance_history) >= 3:
            recent = self.performance_history[-3:]
            trend = recent[-1] - recent[0]

            if trend > 0.1:
                # 表现提升，保持或略微增加
                self.current_rate = min(0.5, self.current_rate * 1.05)
            elif trend < -0.1:
                # 表现下降，降低学习速度
                self.current_rate = max(0.01, self.current_rate * 0.9)
            else:
                # 表现稳定，维持当前速度
                pass

        return self.current_rate

    def get_rate(self) -> float:
        """获取当前学习速度"""
        return self.current_rate

    def reset(self):
        """重置学习速度"""
        self.current_rate = self.base_rate
        self.performance_history = []


# ============================================================================
# 学习效果预测器
# ============================================================================

class LearningOutcomePredictor:
    """学习效果预测器"""

    def __init__(self):
        self.prediction_models: dict[str, dict] = {}

    def predict(self, strategy: LearningStrategy,
                domain: str,
                difficulty: TaskDifficulty,
                duration: float) -> dict:
        """预测学习效果"""
        # 基于历史数据的简单预测
        base_prediction = self._get_base_prediction(strategy, difficulty)

        # 考虑学习时长
        time_factor = min(1.0, duration / 3600)  # 1小时为基准

        predicted_retention = base_prediction['retention'] * time_factor
        predicted_efficiency = base_prediction['efficiency'] * time_factor

        return {
            'predicted_retention': min(1.0, predicted_retention),
            'predicted_efficiency': min(1.0, predicted_efficiency),
            'confidence': base_prediction['confidence'],
            'recommendation': self._get_recommendation(strategy, difficulty),
        }

    def _get_base_prediction(self, strategy: LearningStrategy,
                              difficulty: TaskDifficulty) -> dict:
        """获取基础预测"""
        # 不同策略的基础效果
        strategy_effects = {
            LearningStrategy.REPETITION: {'retention': 0.6, 'efficiency': 0.5},
            LearningStrategy.SPACED: {'retention': 0.8, 'efficiency': 0.7},
            LearningStrategy.INTERLEAVING: {'retention': 0.7, 'efficiency': 0.8},
            LearningStrategy.ELABORATIVE: {'retention': 0.75, 'efficiency': 0.6},
            LearningStrategy.RETRIEVAL: {'retention': 0.85, 'efficiency': 0.75},
            LearningStrategy.TEACHING: {'retention': 0.9, 'efficiency': 0.5},
            LearningStrategy.ANALOGY: {'retention': 0.7, 'efficiency': 0.65},
            LearningStrategy.CHUNKING: {'retention': 0.75, 'efficiency': 0.8},
        }

        # 难度调整
        difficulty_factor = {
            TaskDifficulty.EASY: 1.2,
            TaskDifficulty.MEDIUM: 1.0,
            TaskDifficulty.HARD: 0.8,
            TaskDifficulty.EXPERT: 0.6,
        }

        base = strategy_effects.get(strategy, {'retention': 0.5, 'efficiency': 0.5})
        factor = difficulty_factor.get(difficulty, 1.0)

        return {
            'retention': base['retention'] * factor,
            'efficiency': base['efficiency'] * factor,
            'confidence': 0.6,
        }

    def _get_recommendation(self, strategy: LearningStrategy,
                             difficulty: TaskDifficulty) -> str:
        """获取推荐"""
        if difficulty == TaskDifficulty.EXPERT:
            return "建议结合多种策略，增加学习时长"
        elif strategy == LearningStrategy.REPETITION and difficulty == TaskDifficulty.HARD:
            return "对于困难任务，建议使用间隔重复或交错学习"
        else:
            return "当前策略适合，建议保持"


# ============================================================================
# 元知识管理器
# ============================================================================

class MetaKnowledgeManager:
    """元知识管理器"""

    def __init__(self):
        self.meta_knowledge: dict[str, MetaKnowledge] = {}
        self._initialize_default_knowledge()

    def _initialize_default_knowledge(self):
        """初始化默认元知识"""
        defaults = [
            MetaKnowledge(
                id="mk_001",
                rule="对于简单任务，重复学习足够有效",
                conditions=["difficulty == EASY", "time_pressure == HIGH"],
                recommendation="使用重复学习策略",
                confidence=0.8,
            ),
            MetaKnowledge(
                id="mk_002",
                rule="间隔重复适合长期记忆",
                conditions=["goal == LONG_TERM", "material == FACTUAL"],
                recommendation="使用间隔重复策略",
                confidence=0.9,
            ),
            MetaKnowledge(
                id="mk_003",
                rule="交错学习提高辨别能力",
                conditions=["material == SIMILAR", "goal == DISCRIMINATION"],
                recommendation="使用交错学习策略",
                confidence=0.85,
            ),
            MetaKnowledge(
                id="mk_004",
                rule="教学相长，教是最好的学",
                conditions=["depth == DEEP", "time == AVAILABLE"],
                recommendation="尝试教授他人",
                confidence=0.9,
            ),
        ]

        for mk in defaults:
            self.meta_knowledge[mk.id] = mk

    def add_knowledge(self, rule: str, conditions: list,
                      recommendation: str, confidence: float) -> MetaKnowledge:
        """添加元知识"""
        mk_id = hashlib.md5(rule.encode()).hexdigest()[:12]
        mk = MetaKnowledge(
            id=mk_id,
            rule=rule,
            conditions=conditions,
            recommendation=recommendation,
            confidence=confidence,
        )
        self.meta_knowledge[mk_id] = mk
        return mk

    def get_recommendation(self, context: dict) -> list:
        """根据上下文获取推荐"""
        recommendations = []

        for mk in self.meta_knowledge.values():
            # 检查条件匹配
            if self._check_conditions(mk.conditions, context):
                recommendations.append({
                    'rule': mk.rule,
                    'recommendation': mk.recommendation,
                    'confidence': mk.confidence,
                })

        # 按置信度排序
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        return recommendations[:3]

    def _check_conditions(self, conditions: list, context: dict) -> bool:
        """检查条件是否��足"""
        # 简化实现：检查关键条件
        for condition in conditions:
            if '==' in condition:
                key, value = condition.split('==')
                key = key.strip()
                value = value.strip()
                if key in context and str(context[key]) != value:
                    return False
        return True


# ============================================================================
# 元学习引擎
# ============================================================================

class MetaLearningEngine:
    """
    元学习引擎 - 整合所有组件

    核心功能：
    1. 分析学习策略效果
    2. 自适应调整学习速度
    3. 预测学习效果
    4. 推荐最佳学习方法
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "meta_learning"
        os.makedirs(storage_dir, exist_ok=True)

        self.strategy_analyzer = StrategyAnalyzer()
        self.rate_adapter = LearningRateAdapter()
        self.outcome_predictor = LearningOutcomePredictor()
        self.meta_knowledge_mgr = MetaKnowledgeManager()

        self.learning_history: list[dict] = []

        self.storage_path = os.path.join(storage_dir, "meta_learning.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.learning_history = data.get('history', [])

    def _save(self):
        """保存数据"""
        data = {
            'history': self.learning_history[-100:],
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_learning(self, strategy: LearningStrategy,
                        domain: str,
                        difficulty: TaskDifficulty,
                        duration: float,
                        items_learned: int,
                        retention_rate: float,
                        feedback_score: float) -> dict:
        """记录学习会话"""
        # 计算效率
        efficiency = retention_rate * items_learned / max(1, duration / 60)

        session = LearningSession(
            id=f"session_{int(time.time())}",
            strategy=strategy,
            domain=domain,
            difficulty=difficulty,
            duration=duration,
            items_learned=items_learned,
            retention_rate=retention_rate,
            efficiency=efficiency,
            feedback_score=feedback_score,
        )

        # 分析会话
        analysis = self.strategy_analyzer.analyze_session(session)

        # 调整学习速度
        new_rate = self.rate_adapter.adapt(retention_rate)

        # 记录历史
        self.learning_history.append({
            'session': asdict(session),
            'analysis': analysis,
            'new_rate': new_rate,
        })
        self._save()

        return {
            'session_id': session.id,
            'efficiency': efficiency,
            'new_learning_rate': new_rate,
            'analysis': analysis,
        }

    def get_recommendation(self, domain: str,
                           difficulty: TaskDifficulty,
                           context: dict = None) -> dict:
        """获取学习推荐"""
        # 获取最佳策略
        best_strategy = self.strategy_analyzer.get_best_strategy(domain, difficulty)

        # 预测效果
        prediction = self.outcome_predictor.predict(
            strategy=best_strategy or LearningStrategy.SPACED,
            domain=domain,
            difficulty=difficulty,
            duration=3600,  # 假设1小时
        )

        # 获取元知识推荐
        meta_recommendations = self.meta_knowledge_mgr.get_recommendation(
            context or {'difficulty': difficulty.value, 'domain': domain}
        )

        return {
            'recommended_strategy': best_strategy.value if best_strategy else 'spaced',
            'predicted_outcome': prediction,
            'meta_recommendations': meta_recommendations,
            'current_learning_rate': self.rate_adapter.get_rate(),
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_sessions': len(self.learning_history),
            'strategy_stats': self.strategy_analyzer.get_strategy_stats(),
            'current_learning_rate': self.rate_adapter.get_rate(),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🧠 元学习报告")
        report.append("=" * 50)
        report.append(f"\n学习会话总数: {stats['total_sessions']}")
        report.append(f"当前学习率: {stats['current_learning_rate']:.3f}")

        if stats['strategy_stats']:
            report.append("\n策略效果:")
            for strategy, data in stats['strategy_stats'].items():
                report.append(f"  - {strategy}: 效率={data['avg_efficiency']:.2f}, 保留率={data['avg_retention']:.2f}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = MetaLearningEngine("test_meta_learning")

    # 记录学习会话
    print("=== 记录学习 ===")
    sessions = [
        (LearningStrategy.SPACED, "python", TaskDifficulty.MEDIUM, 3600, 10, 0.8, 0.9),
        (LearningStrategy.INTERLEAVING, "python", TaskDifficulty.HARD, 5400, 8, 0.7, 0.8),
        (LearningStrategy.RETRIEVAL, "machine_learning", TaskDifficulty.HARD, 7200, 6, 0.85, 0.95),
    ]

    for strategy, domain, difficulty, duration, items, retention, feedback in sessions:
        result = engine.record_learning(strategy, domain, difficulty, duration, items, retention, feedback)
        print(f"会话 {result['session_id']}: 效率={result['efficiency']:.2f}")

    # 获取推荐
    print("\n=== 学习推荐 ===")
    recommendation = engine.get_recommendation("python", TaskDifficulty.HARD)
    print(f"推荐策略: {recommendation['recommended_strategy']}")
    print(f"预测保留率: {recommendation['predicted_outcome']['predicted_retention']:.2f}")

    # 报告
    print("\n" + engine.generate_report())