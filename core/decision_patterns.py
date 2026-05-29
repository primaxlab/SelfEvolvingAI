"""
================================================================================
决策模式学习系统 (Decision Pattern Learning System)
================================================================================

核心能力：
  1. 决策记录 - 记录决策过程和结果
  2. 模式识别 - 识别成功的决策模式
  3. 策略优化 - 优化决策策略
  4. 经验提取 - 从决策中提取经验
  5. 预测决策 - 预测决策的可能结果

设计原则：
  - 数据驱动：基于历史决策数据
  - 持续学习：不断从新决策中学习
  - 可解释性：决策过程可追溯
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

class DecisionOutcome(Enum):
    SUCCESS = "success"          # 成功
    PARTIAL = "partial"          # 部分成功
    FAILURE = "failure"          # 失败
    UNKNOWN = "unknown"          # 未知

@dataclass
class DecisionContext:
    """决策上下文"""
    situation: str               # 情境描述
    constraints: list            # 约束条件
    goals: list                  # 目标
    available_options: list      # 可选方案
    metadata: dict = field(default_factory=dict)

@dataclass
class Decision:
    """决策"""
    id: str
    context: DecisionContext
    chosen_option: str           # 选择的方案
    reasoning: str               # 推理过程
    outcome: DecisionOutcome = DecisionOutcome.UNKNOWN
    outcome_details: str = ""
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)
    execution_time: float = 0.0

@dataclass
class DecisionPattern:
    """决策模式"""
    id: str
    name: str
    description: str
    conditions: list             # 适用条件
    recommended_action: str      # 推荐动作
    success_rate: float
    usage_count: int = 0
    examples: list = field(default_factory=list)


# ============================================================================
# 决策记录器
# ============================================================================

class DecisionRecorder:
    """决策记录器"""

    def __init__(self):
        self.decisions: list[Decision] = []

    def record(self, context: DecisionContext,
               chosen_option: str, reasoning: str,
               confidence: float = 0.5) -> Decision:
        """记录决策"""
        decision_id = hashlib.md5(
            f"{context.situation}:{chosen_option}:{time.time()}".encode()
        ).hexdigest()[:12]

        decision = Decision(
            id=decision_id,
            context=context,
            chosen_option=chosen_option,
            reasoning=reasoning,
            confidence=confidence,
        )

        self.decisions.append(decision)
        return decision

    def update_outcome(self, decision_id: str,
                        outcome: DecisionOutcome,
                        details: str = "") -> bool:
        """更新决策结果"""
        for decision in self.decisions:
            if decision.id == decision_id:
                decision.outcome = outcome
                decision.outcome_details = details
                return True
        return False

    def get_decisions(self, limit: int = 100) -> list:
        """获取决策历史"""
        return self.decisions[-limit:]

    def get_successful_decisions(self) -> list:
        """获取成功决策"""
        return [d for d in self.decisions
                if d.outcome == DecisionOutcome.SUCCESS]


# ============================================================================
# 模式识别器
# ============================================================================

class PatternRecognizer:
    """模式识别器"""

    def __init__(self):
        self.patterns: dict[str, DecisionPattern] = {}

    def analyze(self, decisions: list) -> list:
        """分析决策模式"""
        if len(decisions) < 3:
            return []

        # 按情境分组
        situation_groups = {}
        for decision in decisions:
            key = self._categorize_situation(decision.context.situation)
            if key not in situation_groups:
                situation_groups[key] = []
            situation_groups[key].append(decision)

        # 识别模式
        patterns = []
        for situation, group in situation_groups.items():
            if len(group) >= 2:
                pattern = self._extract_pattern(situation, group)
                if pattern:
                    patterns.append(pattern)
                    self.patterns[pattern.id] = pattern

        return patterns

    def _categorize_situation(self, situation: str) -> str:
        """分类情境"""
        situation_lower = situation.lower()

        if any(kw in situation_lower for kw in ['错误', 'bug', '问题']):
            return 'problem_solving'
        elif any(kw in situation_lower for kw in ['选择', '决定', '比较']):
            return 'decision_making'
        elif any(kw in situation_lower for kw in ['学习', '理解', '研究']):
            return 'learning'
        elif any(kw in situation_lower for kw in ['创建', '构建', '开发']):
            return 'creation'
        else:
            return 'general'

    def _extract_pattern(self, situation: str,
                          decisions: list) -> Optional[DecisionPattern]:
        """提取模式"""
        # 统计成功决策
        successful = [d for d in decisions if d.outcome == DecisionOutcome.SUCCESS]

        if not successful:
            return None

        # 找出最常见的成功选项
        option_counts = {}
        for d in successful:
            option_counts[d.chosen_option] = option_counts.get(d.chosen_option, 0) + 1

        most_common = max(option_counts, key=option_counts.get)
        success_rate = len(successful) / len(decisions)

        pattern_id = hashlib.md5(f"{situation}:{most_common}".encode()).hexdigest()[:12]

        return DecisionPattern(
            id=pattern_id,
            name=f"{situation}模式",
            description=f"在{situation}情境下，选择{most_common}通常成功",
            conditions=[situation],
            recommended_action=most_common,
            success_rate=success_rate,
            usage_count=len(decisions),
            examples=[d.id for d in successful[:3]],
        )

    def find_matching_pattern(self, context: DecisionContext) -> Optional[DecisionPattern]:
        """查找匹配的模式"""
        situation_category = self._categorize_situation(context.situation)

        matching = [
            p for p in self.patterns.values()
            if situation_category in p.conditions
        ]

        if matching:
            # 返回成功率最高的
            return max(matching, key=lambda p: p.success_rate)

        return None


# ============================================================================
# 策略优化器
# ============================================================================

class StrategyOptimizer:
    """策略优化器"""

    def __init__(self):
        self.optimization_history: list[dict] = []

    def optimize(self, decisions: list,
                  patterns: list) -> dict:
        """优化策略"""
        # 分析成功因素
        success_factors = self._analyze_success_factors(decisions)

        # 分析失败原因
        failure_reasons = self._analyze_failure_reasons(decisions)

        # 生成优化建议
        recommendations = self._generate_recommendations(
            success_factors, failure_reasons, patterns
        )

        optimization = {
            'success_factors': success_factors,
            'failure_reasons': failure_reasons,
            'recommendations': recommendations,
            'timestamp': time.time(),
        }

        self.optimization_history.append(optimization)
        return optimization

    def _analyze_success_factors(self, decisions: list) -> list:
        """分析成功因素"""
        successful = [d for d in decisions if d.outcome == DecisionOutcome.SUCCESS]

        if not successful:
            return []

        # 分析共同特征
        factors = []

        # 高置信度决策通常更成功
        avg_confidence = sum(d.confidence for d in successful) / len(successful)
        if avg_confidence > 0.7:
            factors.append({
                'factor': 'high_confidence',
                'description': '高置信度决策更可能成功',
                'strength': avg_confidence,
            })

        return factors

    def _analyze_failure_reasons(self, decisions: list) -> list:
        """分析失败原因"""
        failed = [d for d in decisions if d.outcome == DecisionOutcome.FAILURE]

        if not failed:
            return []

        reasons = []

        # 低置信度决策更容易失败
        avg_confidence = sum(d.confidence for d in failed) / len(failed)
        if avg_confidence < 0.5:
            reasons.append({
                'reason': 'low_confidence',
                'description': '低置信度决策更容易失败',
                'frequency': len(failed),
            })

        return reasons

    def _generate_recommendations(self, success_factors: list,
                                    failure_reasons: list,
                                    patterns: list) -> list:
        """生成优化建议"""
        recommendations = []

        if failure_reasons:
            recommendations.append({
                'type': 'improve_confidence',
                'description': '提高决策置信度，减少低置信度决策',
                'priority': 'high',
            })

        if patterns:
            best_pattern = max(patterns, key=lambda p: p.success_rate)
            recommendations.append({
                'type': 'use_pattern',
                'description': f'使用已验证的模式: {best_pattern.name}',
                'priority': 'medium',
            })

        return recommendations


# ============================================================================
# 决策模式学习引擎
# ============================================================================

class DecisionPatternLearningEngine:
    """
    决策模式学习引擎 - 整合所有组件

    核心功能：
    1. 记录决策
    2. 识别模式
    3. 优化策略
    4. 预测结果
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "decision_patterns"
        os.makedirs(storage_dir, exist_ok=True)

        self.recorder = DecisionRecorder()
        self.pattern_recognizer = PatternRecognizer()
        self.strategy_optimizer = StrategyOptimizer()

        self.storage_path = os.path.join(storage_dir, "decisions.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 简化加载

    def _save(self):
        """保存数据"""
        data = {
            'decisions': len(self.recorder.decisions),
            'patterns': len(self.pattern_recognizer.patterns),
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def make_decision(self, context,
                       reasoning: str = "") -> dict:
        """做出决策"""
        # 兼容 dict 和 DecisionContext
        if isinstance(context, dict):
            context = DecisionContext(
                situation=context.get('input', context.get('situation', '')),
                constraints=context.get('constraints', []),
                goals=context.get('goals', []),
                available_options=context.get('available_options', context.get('modules', [])),
                metadata=context.get('metadata', {k: v for k, v in context.items() if k not in ('input', 'situation', 'constraints', 'goals', 'available_options', 'modules')}),
            )
        # 查找匹配的模式
        pattern = self.pattern_recognizer.find_matching_pattern(context)

        if pattern:
            # 使用模式推荐
            chosen_option = pattern.recommended_action
            confidence = pattern.success_rate
            reasoning = f"基于模式 '{pattern.name}': {reasoning}"
        else:
            # 使用默认逻辑
            if context.available_options:
                chosen_option = context.available_options[0]
            else:
                chosen_option = "default"
            confidence = 0.5

        # 记录决策
        decision = self.recorder.record(context, chosen_option, reasoning, confidence)

        return {
            'decision_id': decision.id,
            'chosen_option': chosen_option,
            'confidence': confidence,
            'based_on_pattern': pattern is not None,
            'pattern_name': pattern.name if pattern else None,
        }

    def record_outcome(self, decision_id: str,
                        outcome: DecisionOutcome,
                        details: str = "") -> bool:
        """记录决策结果"""
        success = self.recorder.update_outcome(decision_id, outcome, details)

        if success:
            # 重新分析模式
            decisions = self.recorder.get_decisions()
            self.pattern_recognizer.analyze(decisions)

        return success

    def get_recommendations(self, context: DecisionContext) -> dict:
        """获取决策建议"""
        pattern = self.pattern_recognizer.find_matching_pattern(context)

        return {
            'has_pattern': pattern is not None,
            'recommended_action': pattern.recommended_action if pattern else None,
            'pattern_name': pattern.name if pattern else None,
            'success_rate': pattern.success_rate if pattern else None,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        total = len(self.recorder.decisions)
        successful = len(self.recorder.get_successful_decisions())

        return {
            'total_decisions': total,
            'successful_decisions': successful,
            'success_rate': successful / max(1, total),
            'patterns_identified': len(self.pattern_recognizer.patterns),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🎯 决策模式学习报告")
        report.append("=" * 50)
        report.append(f"\n决策总数: {stats['total_decisions']}")
        report.append(f"成功决策: {stats['successful_decisions']}")
        report.append(f"成功率: {stats['success_rate']:.1%}")
        report.append(f"识别模式: {stats['patterns_identified']}")

        # 显示模式
        if self.pattern_recognizer.patterns:
            report.append("\n已识别模式:")
            for pattern in list(self.pattern_recognizer.patterns.values())[:5]:
                report.append(f"  - {pattern.name}: 成功率 {pattern.success_rate:.1%}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = DecisionPatternLearningEngine("test_decision_patterns")

    # 模拟决策
    print("=== 决策记录 ===")
    decisions = [
        ("代码有bug需要修复", ["查看日志", "调试代码", "询问他人"], "调试代码", 0.8, DecisionOutcome.SUCCESS),
        ("需要学习新技术", ["阅读文档", "看视频", "动手实践"], "动手实践", 0.7, DecisionOutcome.SUCCESS),
        ("代码有bug需要修复", ["查看日志", "调试代码", "询问他人"], "查看日志", 0.6, DecisionOutcome.PARTIAL),
    ]

    for situation, options, choice, confidence, outcome in decisions:
        context = DecisionContext(
            situation=situation,
            constraints=[],
            goals=["解决问题"],
            available_options=options,
        )
        result = engine.make_decision(context, f"选择{choice}")
        engine.record_outcome(result['decision_id'], outcome)
        print(f"决策: {situation} -> {result['chosen_option']} ({result['confidence']:.2f})")

    # 获取建议
    print("\n=== 决策建议 ===")
    new_context = DecisionContext(
        situation="代码有bug需要修复",
        constraints=[],
        goals=["快速修复"],
        available_options=["查看日志", "调试代码"],
    )
    recommendations = engine.get_recommendations(new_context)
    print(f"建议: {recommendations}")

    # 报告
    print("\n" + engine.generate_report())