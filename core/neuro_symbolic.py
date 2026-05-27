"""
================================================================================
神经符号集成系统 (Neuro-Symbolic Integration System)
================================================================================

核心能力：
  1. 神经网络处理 - 处理模式识别、特征提取
  2. 符号推理 - 处理逻辑推理、规则应用
  3. 知识融合 - 融合神经和符号知识
  4. 可解释性 - 提供决策的可解释性
  5. 混合推理 - 结合两种推理方式

设计原则：
  - 互补性：神经和符号各有所长
  - 可解释性：决策过程可追溯
  - 鲁棒性：结合两种方法的优势
"""

import json
import os
import time
import hashlib
import re
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class ReasoningType(Enum):
    NEURAL = "neural"            # 神经推理
    SYMBOLIC = "symbolic"        # 符号推理
    HYBRID = "hybrid"            # 混合推理

@dataclass
class NeuralFeature:
    """神经网络特征"""
    feature_id: str
    values: list                 # 特征值
    confidence: float
    source: str

@dataclass
class SymbolicRule:
    """符号规则"""
    rule_id: str
    condition: str               # 条件
    action: str                  # 动作
    confidence: float
    domain: str

@dataclass
class HybridDecision:
    """混合决策"""
    decision_id: str
    neural_contribution: float   # 神经网络贡献
    symbolic_contribution: float # 符号推理贡献
    final_decision: str
    confidence: float
    explanation: str


# ============================================================================
# 神经网络处理器
# ============================================================================

class NeuralProcessor:
    """神经网络处理器"""

    def __init__(self):
        self.feature_extractors = {}
        self.pattern_memory = {}

    def extract_features(self, input_data: Any,
                          feature_type: str = "text") -> NeuralFeature:
        """提取特征"""
        if feature_type == "text":
            return self._extract_text_features(input_data)
        elif feature_type == "numeric":
            return self._extract_numeric_features(input_data)
        else:
            return self._extract_generic_features(input_data)

    def _extract_text_features(self, text: str) -> NeuralFeature:
        """提取文本特征"""
        # 简化实现：基于统计的特征
        features = {
            'length': len(text),
            'word_count': len(text.split()),
            'has_question': '?' in text or '？' in text,
            'has_code': bool(re.search(r'def |class |import', text)),
            'complexity': min(1.0, len(text) / 200),
        }

        values = list(features.values())
        confidence = 0.7

        return NeuralFeature(
            feature_id=hashlib.md5(text[:50].encode()).hexdigest()[:12],
            values=values,
            confidence=confidence,
            source="text_processor",
        )

    def _extract_numeric_features(self, numbers: list) -> NeuralFeature:
        """提取数值特征"""
        if not numbers:
            return NeuralFeature(
                feature_id="empty",
                values=[],
                confidence=0,
                source="numeric_processor",
            )

        features = [
            sum(numbers) / len(numbers),  # 平均值
            max(numbers) - min(numbers),  # 范围
            len(numbers),                 # 数量
        ]

        return NeuralFeature(
            feature_id=hashlib.md5(str(numbers[:5]).encode()).hexdigest()[:12],
            values=features,
            confidence=0.8,
            source="numeric_processor",
        )

    def _extract_generic_features(self, data: Any) -> NeuralFeature:
        """提取通用特征"""
        return NeuralFeature(
            feature_id="generic",
            values=[0.5],
            confidence=0.5,
            source="generic_processor",
        )

    def recognize_pattern(self, features: NeuralFeature) -> dict:
        """识别模式"""
        # 简化实现：基于规则的模式匹配
        patterns = []

        if features.source == "text_processor":
            values = features.values
            if len(values) >= 5:
                if values[3]:  # has_code
                    patterns.append({'pattern': 'code_related', 'confidence': 0.8})
                if values[2]:  # has_question
                    patterns.append({'pattern': 'question', 'confidence': 0.7})

        return {
            'patterns': patterns,
            'count': len(patterns),
        }


# ============================================================================
# 符号推理器
# ============================================================================

class SymbolicReasoner:
    """符号推理器"""

    def __init__(self):
        self.rules: dict[str, SymbolicRule] = {}
        self.facts: dict[str, Any] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """初始化默认规则"""
        defaults = [
            SymbolicRule(
                rule_id="rule_001",
                condition="input is question",
                action="provide answer",
                confidence=0.9,
                domain="general",
            ),
            SymbolicRule(
                rule_id="rule_002",
                condition="input is code and has error",
                action="suggest fix",
                confidence=0.85,
                domain="programming",
            ),
            SymbolicRule(
                rule_id="rule_003",
                condition="confidence < 0.5",
                action="ask for clarification",
                confidence=0.8,
                domain="general",
            ),
        ]

        for rule in defaults:
            self.rules[rule.rule_id] = rule

    def add_rule(self, condition: str, action: str,
                  confidence: float, domain: str) -> SymbolicRule:
        """添加规则"""
        rule_id = hashlib.md5(f"{condition}:{action}".encode()).hexdigest()[:12]
        rule = SymbolicRule(
            rule_id=rule_id,
            condition=condition,
            action=action,
            confidence=confidence,
            domain=domain,
        )
        self.rules[rule_id] = rule
        return rule

    def add_fact(self, fact_id: str, value: Any):
        """添加事实"""
        self.facts[fact_id] = value

    def reason(self, context: dict) -> dict:
        """执行推理"""
        applicable_rules = []

        for rule in self.rules.values():
            if self._check_condition(rule.condition, context):
                applicable_rules.append(rule)

        if not applicable_rules:
            return {
                'applicable_rules': [],
                'recommended_action': None,
                'confidence': 0,
            }

        # 选择置信度最高的规则
        best_rule = max(applicable_rules, key=lambda r: r.confidence)

        return {
            'applicable_rules': [asdict(r) for r in applicable_rules],
            'recommended_action': best_rule.action,
            'confidence': best_rule.confidence,
            'explanation': f"根据规则 '{best_rule.condition}'，建议 '{best_rule.action}'",
        }

    def _check_condition(self, condition: str,
                          context: dict) -> bool:
        """检查条件是否满足"""
        condition_lower = condition.lower()

        # 简化的条件检查
        if "is question" in condition_lower:
            return context.get('is_question', False)
        elif "has error" in condition_lower:
            return context.get('has_error', False)
        elif "confidence < 0.5" in condition_lower:
            return context.get('confidence', 1.0) < 0.5
        elif "is code" in condition_lower:
            return context.get('is_code', False)

        return False


# ============================================================================
# 知识融合器
# ============================================================================

class KnowledgeFusion:
    """知识融合器"""

    def fuse(self, neural_result: dict,
              symbolic_result: dict) -> HybridDecision:
        """融合神经和符号结果"""
        # 计算贡献度
        neural_confidence = neural_result.get('confidence', 0.5)
        symbolic_confidence = symbolic_result.get('confidence', 0.5)

        total = neural_confidence + symbolic_confidence
        if total == 0:
            neural_weight = 0.5
            symbolic_weight = 0.5
        else:
            neural_weight = neural_confidence / total
            symbolic_weight = symbolic_confidence / total

        # 融合决策
        if symbolic_result.get('recommended_action'):
            final_decision = symbolic_result['recommended_action']
            explanation = symbolic_result.get('explanation', '')
        else:
            final_decision = "基于模式识别处理"
            explanation = "未找到匹配的规则，使用默认处理"

        # 综合置信度
        confidence = neural_weight * neural_confidence + symbolic_weight * symbolic_confidence

        decision_id = hashlib.md5(f"{final_decision}{time.time()}".encode()).hexdigest()[:12]

        return HybridDecision(
            decision_id=decision_id,
            neural_contribution=neural_weight,
            symbolic_contribution=symbolic_weight,
            final_decision=final_decision,
            confidence=confidence,
            explanation=explanation,
        )


# ============================================================================
# 神经符号集成引擎
# ============================================================================

class NeuroSymbolicEngine:
    """
    神经符号集成引擎 - 整合所有组件

    核心功能：
    1. 神经网络特征提取
    2. 符号推理决策
    3. 混合推理
    4. 可解释性输出
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "neuro_symbolic"
        os.makedirs(storage_dir, exist_ok=True)

        self.neural_processor = NeuralProcessor()
        self.symbolic_reasoner = SymbolicReasoner()
        self.fusion = KnowledgeFusion()

        self.decision_history: list[HybridDecision] = []

    def process(self, input_data: Any,
                 context: dict = None) -> dict:
        """处理输入"""
        context = context or {}

        # 1. 神经网络处理
        features = self.neural_processor.extract_features(input_data)
        patterns = self.neural_processor.recognize_pattern(features)

        # 更新上下文
        if patterns['patterns']:
            for pattern in patterns['patterns']:
                if pattern['pattern'] == 'question':
                    context['is_question'] = True
                elif pattern['pattern'] == 'code_related':
                    context['is_code'] = True

        context['confidence'] = features.confidence

        # 2. 符号推理
        symbolic_result = self.symbolic_reasoner.reason(context)

        # 3. 融合
        neural_result = {
            'confidence': features.confidence,
            'patterns': patterns['patterns'],
        }

        decision = self.fusion.fuse(neural_result, symbolic_result)

        # 记录决策
        self.decision_history.append(decision)

        return {
            'features': asdict(features),
            'patterns': patterns,
            'symbolic_reasoning': symbolic_result,
            'decision': asdict(decision),
        }

    def add_rule(self, condition: str, action: str,
                  confidence: float, domain: str) -> SymbolicRule:
        """添加规则"""
        return self.symbolic_reasoner.add_rule(condition, action, confidence, domain)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_decisions': len(self.decision_history),
            'rules_count': len(self.symbolic_reasoner.rules),
            'avg_neural_contribution': (
                sum(d.neural_contribution for d in self.decision_history) /
                max(1, len(self.decision_history))
            ),
            'avg_symbolic_contribution': (
                sum(d.symbolic_contribution for d in self.decision_history) /
                max(1, len(self.decision_history))
            ),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🧠 神经符号集成报告")
        report.append("=" * 50)
        report.append(f"\n决策总数: {stats['total_decisions']}")
        report.append(f"规则数量: {stats['rules_count']}")
        report.append(f"神经网络贡献: {stats['avg_neural_contribution']:.2%}")
        report.append(f"符号推理贡献: {stats['avg_symbolic_contribution']:.2%}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = NeuroSymbolicEngine("test_neuro_symbolic")

    # 测试输入
    test_inputs = [
        "请帮我写一个Python函数",
        "这段代码有bug，怎么修复？",
        "什么是机器学习？",
    ]

    print("=== 神经符号处理 ===")
    for text in test_inputs:
        result = engine.process(text)
        print(f"\n输入: {text}")
        print(f"  神经网络: {len(result['patterns']['patterns'])}个模式")
        print(f"  符号推理: {result['symbolic_reasoning']['recommended_action']}")
        print(f"  最终决策: {result['decision']['final_decision']}")
        print(f"  置信度: {result['decision']['confidence']:.2f}")

    # 报告
    print("\n" + engine.generate_report())