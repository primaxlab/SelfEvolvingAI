"""
================================================================================
元认知系统 (Metacognition System)
================================================================================

核心能力：
  1. 能力边界自评估 - 知道自己能做什么、不能做什么
  2. 置信度计算 - 对每个回答给出可信度评分
  3. 知识空白检测 - 识别自己不知道的领域
  4. 不确定性量化 - 量化回答的不确定性
  5. 求助决策 - 决定何时需要求助外部资源

设计原则：
  - 诚实优先：宁可说"不知道"也不瞎编
  - 可量化：所有评估都有数值支撑
  - 动态更新：随着学习不断修正自我认知
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

class ConfidenceLevel(Enum):
    VERY_LOW = 0.1      # 完全不确定
    LOW = 0.3           # 不太确定
    MEDIUM = 0.5        # 一般
    HIGH = 0.7          # 比较确定
    VERY_HIGH = 0.9     # 非常确定

class KnowledgeDomain(Enum):
    PROGRAMMING = "programming"
    MATH = "math"
    SCIENCE = "science"
    LANGUAGE = "language"
    HISTORY = "history"
    ART = "art"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    MEDICINE = "medicine"
    LAW = "law"
    OTHER = "other"

@dataclass
class CapabilityAssessment:
    """能力评估"""
    domain: str
    proficiency: float        # 熟练度 0-1
    confidence: float         # 置信度 0-1
    last_assessed: float = field(default_factory=time.time)
    evidence_count: int = 0   # 评估依据数量
    success_rate: float = 0.0 # 历史成功率

@dataclass
class KnowledgeGap:
    """知识空白"""
    domain: str
    topic: str
    severity: float           # 严重程度 0-1
    detected_at: float = field(default_factory=time.time)
    context: str = ""         # 检测上下文
    filled: bool = False      # 是否已填补

@dataclass
class UncertaintyEstimate:
    """不确定性估计"""
    answer: str
    confidence: float
    uncertainty_sources: list = field(default_factory=list)
    alternative_answers: list = field(default_factory=list)
    needs_verification: bool = False


# ============================================================================
# 能力边界管理器
# ============================================================================

class CapabilityManager:
    """能力边界管理器"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "capabilities.json"
        self.capabilities: dict[str, CapabilityAssessment] = {}
        self._load()

    def _load(self):
        """加载能力数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for domain, cap_data in data.items():
                    self.capabilities[domain] = CapabilityAssessment(**cap_data)

    def _save(self):
        """保存能力数据"""
        data = {k: asdict(v) for k, v in self.capabilities.items()}
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def assess(self, domain: str) -> CapabilityAssessment:
        """获取某领域能力评估"""
        if domain not in self.capabilities:
            self.capabilities[domain] = CapabilityAssessment(
                domain=domain,
                proficiency=0.5,  # 默认中等
                confidence=0.3,   # 默认低置信度
            )
        return self.capabilities[domain]

    def update_from_feedback(self, domain: str, success: bool,
                              difficulty: float = 0.5):
        """根据反馈更新能力评估"""
        cap = self.assess(domain)
        cap.evidence_count += 1

        # 更新成功率
        total = cap.evidence_count
        cap.success_rate = (
            (cap.success_rate * (total - 1) + (1.0 if success else 0.0)) / total
        )

        # 更新熟练度（成功提升，失败降低）
        if success:
            cap.proficiency = min(1.0, cap.proficiency + 0.05 * difficulty)
        else:
            cap.proficiency = max(0.0, cap.proficiency - 0.03 * difficulty)

        # 更新置信度（证据越多越确定）
        cap.confidence = min(0.95, 0.3 + 0.02 * cap.evidence_count)
        cap.last_assessed = time.time()

        self._save()

    def get_weak_domains(self, threshold: float = 0.4) -> list:
        """获取薄弱领域"""
        weak = []
        for domain, cap in self.capabilities.items():
            if cap.proficiency < threshold:
                weak.append({
                    'domain': domain,
                    'proficiency': cap.proficiency,
                    'confidence': cap.confidence,
                })
        return sorted(weak, key=lambda x: x['proficiency'])

    def get_strong_domains(self, threshold: float = 0.7) -> list:
        """获取擅长领域"""
        strong = []
        for domain, cap in self.capabilities.items():
            if cap.proficiency >= threshold:
                strong.append({
                    'domain': domain,
                    'proficiency': cap.proficiency,
                    'confidence': cap.confidence,
                })
        return sorted(strong, key=lambda x: x['proficiency'], reverse=True)


# ============================================================================
# 知识空白检测器
# ============================================================================

class KnowledgeGapDetector:
    """知识空白检测器"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "knowledge_gaps.json"
        self.gaps: list[KnowledgeGap] = []
        self._load()

    def _load(self):
        """加载知识空白数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.gaps = [KnowledgeGap(**g) for g in data]

    def _save(self):
        """保存知识空白数据"""
        data = [asdict(g) for g in self.gaps]
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def detect_from_uncertainty(self, question: str, answer: str,
                                 confidence: float) -> Optional[KnowledgeGap]:
        """从不确定性中检测知识空白"""
        if confidence < 0.4:
            # 低置信度表示可能存在知识空白
            domain = self._classify_domain(question)
            gap = KnowledgeGap(
                domain=domain,
                topic=question[:100],
                severity=1.0 - confidence,
                context=f"回答置信度低: {confidence:.2f}",
            )
            self.gaps.append(gap)
            self._save()
            return gap
        return None

    def detect_from_failure(self, question: str, error: str) -> KnowledgeGap:
        """从失败中检测知识空白"""
        domain = self._classify_domain(question)
        gap = KnowledgeGap(
            domain=domain,
            topic=question[:100],
            severity=0.8,
            context=f"执行失败: {error}",
        )
        self.gaps.append(gap)
        self._save()
        return gap

    def detect_from_contradiction(self, topic: str,
                                   contradiction: str) -> KnowledgeGap:
        """从矛盾中检测知识空白"""
        domain = self._classify_domain(topic)
        gap = KnowledgeGap(
            domain=domain,
            topic=topic[:100],
            severity=0.6,
            context=f"发现矛盾: {contradiction}",
        )
        self.gaps.append(gap)
        self._save()
        return gap

    def _classify_domain(self, text: str) -> str:
        """分类领域"""
        text_lower = text.lower()

        domain_keywords = {
            'programming': ['python', 'java', '代码', '函数', 'api', 'bug', '算法'],
            'math': ['数学', '公式', '计算', '统计', '概率', '方程'],
            'science': ['物理', '化学', '生物', '实验', '科学'],
            'language': ['翻译', '语法', '语言', '英语', '中文'],
            'technology': ['技术', '系统', '架构', '数据库', '网络'],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return domain

        return 'other'

    def mark_filled(self, gap_index: int):
        """标记知识空白已填补"""
        if 0 <= gap_index < len(self.gaps):
            self.gaps[gap_index].filled = True
            self._save()

    def get_unfilled_gaps(self, min_severity: float = 0.3) -> list:
        """获取未填补的知识空白"""
        return [
            asdict(g) for g in self.gaps
            if not g.filled and g.severity >= min_severity
        ]

    def get_gap_summary(self) -> dict:
        """获取知识空白摘要"""
        unfilled = [g for g in self.gaps if not g.filled]
        by_domain = {}
        for g in unfilled:
            if g.domain not in by_domain:
                by_domain[g.domain] = 0
            by_domain[g.domain] += 1

        return {
            'total_gaps': len(self.gaps),
            'unfilled_gaps': len(unfilled),
            'by_domain': by_domain,
            'high_severity': sum(1 for g in unfilled if g.severity >= 0.7),
        }


# ============================================================================
# 置信度计算器
# ============================================================================

class ConfidenceCalculator:
    """置信度计算器"""

    def __init__(self):
        self.factors = {
            'domain_expertise': 0.3,    # 领域专业度
            'information_completeness': 0.25,  # 信息完整度
            'consistency': 0.2,         # 一致性
            'recency': 0.15,            # 时效性
            'source_quality': 0.1,      # 来源质量
        }

    def calculate(self, domain_proficiency: float, info_completeness: float,
                  consistency: float = 0.8, recency: float = 0.7,
                  source_quality: float = 0.6) -> float:
        """计算综合置信度"""
        scores = {
            'domain_expertise': domain_proficiency,
            'information_completeness': info_completeness,
            'consistency': consistency,
            'recency': recency,
            'source_quality': source_quality,
        }

        confidence = sum(
            scores[factor] * weight
            for factor, weight in self.factors.items()
        )

        return max(0.0, min(1.0, confidence))

    def explain_confidence(self, confidence: float) -> str:
        """解释置信度"""
        if confidence >= 0.9:
            return "非常确定 - 基于充分的知识和信息"
        elif confidence >= 0.7:
            return "比较确定 - 有较好的依据，但可能有细节遗漏"
        elif confidence >= 0.5:
            return "一般确定 - 有一定依据，建议进一步验证"
        elif confidence >= 0.3:
            return "不太确定 - 信息有限，可能存在错误"
        else:
            return "很不确定 - 知识不足，强烈建议查证"

    def get_uncertainty_sources(self, domain_proficiency: float,
                                 info_completeness: float) -> list:
        """识别不确定性来源"""
        sources = []

        if domain_proficiency < 0.5:
            sources.append("该领域专业知识不足")
        if info_completeness < 0.5:
            sources.append("提供的信息不够完整")

        return sources


# ============================================================================
# 元认知引擎
# ============================================================================

class MetacognitionEngine:
    """
    元认知引擎 - 整合所有元认知组件

    核心职责：
    1. 回答前评估自己的能力
    2. 给出置信度评分
    3. 识别知识空白
    4. 决定是否需要求助
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "metacognition"
        os.makedirs(storage_dir, exist_ok=True)

        self.capability_mgr = CapabilityManager(
            os.path.join(storage_dir, "capabilities.json")
        )
        self.gap_detector = KnowledgeGapDetector(
            os.path.join(storage_dir, "knowledge_gaps.json")
        )
        self.confidence_calc = ConfidenceCalculator()

        # 交互历史
        self.interaction_history: list[dict] = []

    def pre_answer_assessment(self, question: str) -> dict:
        """回答前的能力评估"""
        # 1. 识别领域
        domain = self.gap_detector._classify_domain(question)

        # 2. 获取领域能力
        capability = self.capability_mgr.assess(domain)

        # 3. 评估信息完整度（简化版）
        info_completeness = self._assess_info_completeness(question)

        # 4. 计算置信度
        confidence = self.confidence_calc.calculate(
            domain_proficiency=capability.proficiency,
            info_completeness=info_completeness,
        )

        # 5. 识别不确定性来源
        uncertainty_sources = self.confidence_calc.get_uncertainty_sources(
            capability.proficiency, info_completeness
        )

        # 6. 决定是���需要求助
        needs_help = confidence < 0.4

        return {
            'domain': domain,
            'capability': asdict(capability),
            'confidence': confidence,
            'confidence_explanation': self.confidence_calc.explain_confidence(confidence),
            'uncertainty_sources': uncertainty_sources,
            'needs_help': needs_help,
            'recommendation': self._get_recommendation(confidence, domain),
        }

    def _assess_info_completeness(self, question: str) -> float:
        """评估问题信息完整度"""
        # 简单启发式：问题越长、越具体，信息越完整
        length_score = min(1.0, len(question) / 200)

        # 检查是否有具体细节
        detail_indicators = ['具体', '详细', '例如', '比如', '当', '如果']
        detail_count = sum(1 for ind in detail_indicators if ind in question)
        detail_score = min(1.0, detail_count * 0.2)

        return (length_score + detail_score) / 2

    def _get_recommendation(self, confidence: float, domain: str) -> str:
        """获取建议"""
        if confidence >= 0.8:
            return "可以直接回答"
        elif confidence >= 0.6:
            return "可以回答，但建议注明不确定性"
        elif confidence >= 0.4:
            return "谨慎回答，需要更多上下文或查证"
        else:
            return "建议求助外部资源或明确告知用户不确定"

    def post_answer_update(self, question: str, answer: str,
                            confidence: float, feedback: str = None,
                            success: bool = True):
        """回答后的能力更新"""
        domain = self.gap_detector._classify_domain(question)

        # 更新能力评估
        self.capability_mgr.update_from_feedback(domain, success)

        # 检测知识空白
        if confidence < 0.4:
            self.gap_detector.detect_from_uncertainty(question, answer, confidence)

        # 记录交互
        self.interaction_history.append({
            'question': question[:200],
            'confidence': confidence,
            'domain': domain,
            'success': success,
            'feedback': feedback,
            'timestamp': time.time(),
        })

    def should_ask_clarification(self, question: str,
                                   initial_confidence: float) -> dict:
        """判断是否需要请求澄清"""
        if initial_confidence >= 0.7:
            return {'needed': False}

        # 检查问题是否模糊
        ambiguous_indicators = ['这个', '那个', '它', '他们', '一些', '某些']
        ambiguity_count = sum(1 for ind in ambiguous_indicators if ind in question)

        if ambiguity_count > 2 or initial_confidence < 0.4:
            return {
                'needed': True,
                'reason': '问题不够明确或信息不足',
                'suggestions': [
                    '能否提供更多细节？',
                    '具体是哪个方面？',
                    '能否举个例子？',
                ],
            }

        return {'needed': False}

    def generate_uncertainty_disclaimer(self, confidence: float) -> str:
        """生成不确定性声明"""
        if confidence >= 0.9:
            return ""
        elif confidence >= 0.7:
            return "（这个回答我比较确定，但建议你也验证一下）"
        elif confidence >= 0.5:
            return "（⚠️ 这个回答我不太确定，建议查证）"
        elif confidence >= 0.3:
            return "（⚠️ 这个领域我不太熟悉，回答可能不准确）"
        else:
            return "（❌ 这个问题超出了我的知识范围，建议寻求专业帮助）"

    def get_self_awareness_report(self) -> str:
        """生成自我认知报告"""
        report = []
        report.append("=" * 50)
        report.append("🧠 元认知自我报告")
        report.append("=" * 50)

        # 擅长领域
        strong = self.capability_mgr.get_strong_domains(0.6)
        if strong:
            report.append("\n✅ 擅长领域:")
            for s in strong:
                report.append(f"  - {s['domain']}: {s['proficiency']:.0%}")

        # 薄弱领域
        weak = self.capability_mgr.get_weak_domains(0.5)
        if weak:
            report.append("\n⚠️ 薄弱领域:")
            for w in weak:
                report.append(f"  - {w['domain']}: {w['proficiency']:.0%}")

        # 知识空白
        gap_summary = self.gap_detector.get_gap_summary()
        if gap_summary['unfilled_gaps'] > 0:
            report.append(f"\n🔍 知识空白: {gap_summary['unfilled_gaps']}个")
            for domain, count in gap_summary['by_domain'].items():
                report.append(f"  - {domain}: {count}个")

        # 交互统计
        if self.interaction_history:
            total = len(self.interaction_history)
            success = sum(1 for h in self.interaction_history if h.get('success'))
            avg_confidence = sum(h['confidence'] for h in self.interaction_history) / total
            report.append(f"\n📊 交互统计:")
            report.append(f"  - 总交互: {total}")
            report.append(f"  - 成功率: {success/total:.0%}")
            report.append(f"  - 平均置信度: {avg_confidence:.0%}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = MetacognitionEngine("test_metacognition")

    # 测试回答前评估
    print("=== 回答前评估 ===")
    questions = [
        "如何用Python实现快速排序？",
        "量子纠缠的原理是什么？",
        "帮我写一个机器学习模型",
        "今天天气怎么样？",
    ]

    for q in questions:
        assessment = engine.pre_answer_assessment(q)
        print(f"\n问题: {q}")
        print(f"  领域: {assessment['domain']}")
        print(f"  置信度: {assessment['confidence']:.2f}")
        print(f"  解释: {assessment['confidence_explanation']}")
        print(f"  建议: {assessment['recommendation']}")

        # 模拟回答后更新
        engine.post_answer_update(q, "模拟回答", assessment['confidence'])

    # 自我认知报告
    print("\n" + engine.get_self_awareness_report())