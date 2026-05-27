"""
================================================================================
迁移学习系统 (Transfer Learning System)
================================================================================

核心能力：
  1. 知识表示 - 将知识抽象为可迁移的形式
  2. 相似性计算 - 计算领域间的相似度
  3. 知识迁移 - 将一个领域的知识应用到另一个领域
  4. 适配调整 - 调整迁移的知识以适应新领域
  5. 迁移效果评估 - 评估迁移的效果

设计原则：
  - 抽象优先：先抽象再迁移
  - 验证迁移：迁移后必须验证有效性
  - 渐进迁移：小步迁移，逐步验证
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

class KnowledgeType(Enum):
    PATTERN = "pattern"         # 模式/规律
    STRATEGY = "strategy"       # 策略/方法
    CONCEPT = "concept"         # 概念/原理
    PROCEDURE = "procedure"     # 程序/步骤
    HEURISTIC = "heuristic"     # 启发式规则

class TransferStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class KnowledgeUnit:
    """知识单元"""
    id: str
    name: str
    knowledge_type: KnowledgeType
    content: str
    source_domain: str
    abstraction_level: float  # 抽象程度 0-1
    confidence: float
    examples: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

@dataclass
class DomainProfile:
    """领域画像"""
    name: str
    description: str
    keywords: list = field(default_factory=list)
    concepts: list = field(default_factory=list)
    knowledge_count: int = 0
    similarity_cache: dict = field(default_factory=dict)

@dataclass
class TransferTask:
    """迁移任务"""
    id: str
    source_domain: str
    target_domain: str
    knowledge_ids: list
    status: TransferStatus = TransferStatus.PENDING
    progress: float = 0.0
    result: Any = None
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

@dataclass
class TransferResult:
    """迁移结果"""
    task_id: str
    success: bool
    transferred_knowledge: list
    adapted_knowledge: list
    confidence: float
    issues: list = field(default_factory=list)


# ============================================================================
# 领域相似性计算器
# ============================================================================

class DomainSimilarityCalculator:
    """领域相似性计算器"""

    def __init__(self):
        self.similarity_cache: dict[str, float] = {}

    def calculate(self, domain_a: DomainProfile,
                  domain_b: DomainProfile) -> float:
        """计算两个领域的相似度"""
        cache_key = f"{domain_a.name}:{domain_b.name}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]

        # 关键词重叠度
        keywords_a = set(k.lower() for k in domain_a.keywords)
        keywords_b = set(k.lower() for k in domain_b.keywords)

        if keywords_a and keywords_b:
            intersection = len(keywords_a & keywords_b)
            union = len(keywords_a | keywords_b)
            keyword_similarity = intersection / union if union > 0 else 0
        else:
            keyword_similarity = 0

        # 概念重���度
        concepts_a = set(c.lower() for c in domain_a.concepts)
        concepts_b = set(c.lower() for c in domain_b.concepts)

        if concepts_a and concepts_b:
            intersection = len(concepts_a & concepts_b)
            union = len(concepts_a | concepts_b)
            concept_similarity = intersection / union if union > 0 else 0
        else:
            concept_similarity = 0

        # 综合相似度
        similarity = keyword_similarity * 0.4 + concept_similarity * 0.6

        self.similarity_cache[cache_key] = similarity
        return similarity

    def find_similar_domains(self, target: DomainProfile,
                              all_domains: list,
                              threshold: float = 0.3) -> list:
        """找到与目标领域相似的领域"""
        similar = []

        for domain in all_domains:
            if domain.name == target.name:
                continue

            similarity = self.calculate(target, domain)
            if similarity >= threshold:
                similar.append({
                    'domain': domain.name,
                    'similarity': similarity,
                })

        # 按相似度排序
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar


# ============================================================================
# 知识抽象器
# ============================================================================

class KnowledgeAbstractor:
    """知识抽象器"""

    def abstract(self, knowledge: KnowledgeUnit,
                  target_abstraction: float = 0.8) -> KnowledgeUnit:
        """将知识抽象到更高层次"""
        current_abstraction = knowledge.abstraction_level

        if current_abstraction >= target_abstraction:
            return knowledge

        # 提取核心模式
        abstracted_content = self._extract_core_pattern(
            knowledge.content, target_abstraction
        )

        # 创建抽象后的知识单元
        abstracted = KnowledgeUnit(
            id=f"abs_{knowledge.id}",
            name=f"[抽象] {knowledge.name}",
            knowledge_type=knowledge.knowledge_type,
            content=abstracted_content,
            source_domain=knowledge.source_domain,
            abstraction_level=target_abstraction,
            confidence=knowledge.confidence * 0.9,  # 抽象会降低一些置信度
            examples=knowledge.examples[:2],  # 只保留少数例子
        )

        return abstracted

    def _extract_core_pattern(self, content: str,
                                target_abstraction: float) -> str:
        """提取核心模式"""
        # 简化实现：提取关键句子
        sentences = content.split('。')
        if len(sentences) <= 2:
            return content

        # 根据目标抽象程度选择句子数量
        num_sentences = max(1, int(len(sentences) * (1 - target_abstraction)))
        selected = sentences[:num_sentences]

        return '。'.join(selected) + '。' if selected else content


# ============================================================================
# 知识适配器
# ============================================================================

class KnowledgeAdapter:
    """知识适配器"""

    def adapt(self, knowledge: KnowledgeUnit,
              target_domain: DomainProfile) -> KnowledgeUnit:
        """将知识适配到目标领域"""
        # 替换领域特定术语
        adapted_content = self._adapt_terminology(
            knowledge.content, knowledge.source_domain, target_domain.name
        )

        # 调整示例
        adapted_examples = self._adapt_examples(
            knowledge.examples, target_domain
        )

        # 创建适配后的知识单元
        adapted = KnowledgeUnit(
            id=f"adapt_{knowledge.id}",
            name=f"[{target_domain.name}] {knowledge.name}",
            knowledge_type=knowledge.knowledge_type,
            content=adapted_content,
            source_domain=target_domain.name,
            abstraction_level=knowledge.abstraction_level,
            confidence=knowledge.confidence * 0.8,  # 适配会降低置信度
            examples=adapted_examples,
        )

        return adapted

    def _adapt_terminology(self, content: str,
                            source_domain: str,
                            target_domain: str) -> str:
        """适配术语"""
        # 简单替换
        adapted = content
        adapted = adapted.replace(source_domain, target_domain)
        return adapted

    def _adapt_examples(self, examples: list,
                         target_domain: DomainProfile) -> list:
        """适配示例"""
        # 简化实现：保留原示例
        return examples


# ============================================================================
# 迁移效果评估器
# ============================================================================

class TransferEvaluator:
    """迁移效果评估器"""

    def evaluate(self, original: KnowledgeUnit,
                 transferred: KnowledgeUnit,
                 target_domain: DomainProfile) -> dict:
        """评估迁移效果"""
        # 内容保留度
        content_preservation = self._calculate_preservation(
            original.content, transferred.content
        )

        # 领域适配度
        domain_fit = self._calculate_domain_fit(
            transferred.content, target_domain
        )

        # 置信度变化
        confidence_change = transferred.confidence - original.confidence

        # 综合评分
        overall_score = (
            content_preservation * 0.4 +
            domain_fit * 0.4 +
            (1 + confidence_change) * 0.2
        )

        return {
            'content_preservation': content_preservation,
            'domain_fit': domain_fit,
            'confidence_change': confidence_change,
            'overall_score': overall_score,
            'success': overall_score > 0.5,
        }

    def _calculate_preservation(self, original: str,
                                  transferred: str) -> float:
        """计算内容保留度"""
        # 简单实现：词汇重叠度
        original_words = set(original.split())
        transferred_words = set(transferred.split())

        if not original_words:
            return 0

        overlap = len(original_words & transferred_words)
        return overlap / len(original_words)

    def _calculate_domain_fit(self, content: str,
                                domain: DomainProfile) -> float:
        """计算领域适配度"""
        content_lower = content.lower()
        keyword_matches = sum(
            1 for kw in domain.keywords
            if kw.lower() in content_lower
        )

        if not domain.keywords:
            return 0.5

        return min(1.0, keyword_matches / len(domain.keywords))


# ============================================================================
# 迁移学习引擎
# ============================================================================

class TransferLearningEngine:
    """
    迁移学习引擎 - 整合所有组件

    核心功能：
    1. 管理领域知识
    2. 计算领域相似性
    3. 执行知识迁移
    4. 评估迁移效果
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "transfer_learning"
        os.makedirs(storage_dir, exist_ok=True)

        self.similarity_calc = DomainSimilarityCalculator()
        self.abstractor = KnowledgeAbstractor()
        self.adapter = KnowledgeAdapter()
        self.evaluator = TransferEvaluator()

        self.domains: dict[str, DomainProfile] = {}
        self.knowledge_units: dict[str, KnowledgeUnit] = {}
        self.transfer_tasks: dict[str, TransferTask] = {}
        self.transfer_results: list[TransferResult] = []

        self.storage_path = os.path.join(storage_dir, "transfer.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for d_data in data.get('domains', []):
                    domain = DomainProfile(**d_data)
                    self.domains[domain.name] = domain

                for k_data in data.get('knowledge', []):
                    k_data['knowledge_type'] = KnowledgeType(k_data['knowledge_type'])
                    unit = KnowledgeUnit(**k_data)
                    self.knowledge_units[unit.id] = unit

    def _save(self):
        """保存数据"""
        data = {
            'domains': [asdict(d) for d in self.domains.values()],
            'knowledge': [],
        }

        for unit in self.knowledge_units.values():
            k_dict = asdict(unit)
            k_dict['knowledge_type'] = unit.knowledge_type.value
            data['knowledge'].append(k_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register_domain(self, name: str, description: str,
                        keywords: list = None,
                        concepts: list = None) -> DomainProfile:
        """注册领域"""
        domain = DomainProfile(
            name=name,
            description=description,
            keywords=keywords or [],
            concepts=concepts or [],
        )
        self.domains[name] = domain
        self._save()
        return domain

    def add_knowledge(self, name: str, content: str,
                      domain: str,
                      knowledge_type: KnowledgeType = KnowledgeType.CONCEPT,
                      confidence: float = 0.8) -> KnowledgeUnit:
        """添加知识"""
        unit_id = hashlib.md5(f"{domain}:{name}".encode()).hexdigest()[:12]
        unit = KnowledgeUnit(
            id=unit_id,
            name=name,
            knowledge_type=knowledge_type,
            content=content,
            source_domain=domain,
            abstraction_level=0.5,
            confidence=confidence,
        )
        self.knowledge_units[unit_id] = unit

        # 更新领域知识计数
        if domain in self.domains:
            self.domains[domain].knowledge_count += 1

        self._save()
        return unit

    def find_transfer_candidates(self, target_domain: str,
                                  min_similarity: float = 0.3) -> list:
        """找到可迁移到目标领域的知识"""
        target = self.domains.get(target_domain)
        if not target:
            return []

        candidates = []

        for unit in self.knowledge_units.values():
            if unit.source_domain == target_domain:
                continue  # 跳过同一领域

            source = self.domains.get(unit.source_domain)
            if not source:
                continue

            similarity = self.similarity_calc.calculate(source, target)
            if similarity >= min_similarity:
                candidates.append({
                    'knowledge': unit,
                    'source_domain': unit.source_domain,
                    'similarity': similarity,
                    'transfer_score': similarity * unit.confidence,
                })

        # 按迁移分数排序
        candidates.sort(key=lambda x: x['transfer_score'], reverse=True)
        return candidates

    def transfer(self, knowledge_id: str,
                 target_domain: str,
                 abstract_first: bool = True) -> TransferResult:
        """执行知识迁移"""
        unit = self.knowledge_units.get(knowledge_id)
        if not unit:
            return TransferResult(
                task_id="",
                success=False,
                transferred_knowledge=[],
                adapted_knowledge=[],
                confidence=0.0,
                issues=["知识不存在"],
            )

        target = self.domains.get(target_domain)
        if not target:
            return TransferResult(
                task_id="",
                success=False,
                transferred_knowledge=[],
                adapted_knowledge=[],
                confidence=0.0,
                issues=["目标领域不存在"],
            )

        issues = []
        transferred = unit

        # 1. 抽象化（可选）
        if abstract_first:
            transferred = self.abstractor.abstract(unit, target_abstraction=0.7)

        # 2. 适配到目标领域
        adapted = self.adapter.adapt(transferred, target)

        # 3. 评估迁移效果
        evaluation = self.evaluator.evaluate(unit, adapted, target)

        # 4. 保存迁移后的知识
        self.knowledge_units[adapted.id] = adapted

        # 5. 记录结果
        result = TransferResult(
            task_id=f"transfer_{int(time.time())}",
            success=evaluation['success'],
            transferred_knowledge=[unit.id],
            adapted_knowledge=[adapted.id],
            confidence=evaluation['overall_score'],
            issues=issues,
        )

        self.transfer_results.append(result)
        self._save()

        return result

    def get_domain_similarity(self, domain_a: str,
                               domain_b: str) -> float:
        """获取两个领域的相似度"""
        a = self.domains.get(domain_a)
        b = self.domains.get(domain_b)

        if not a or not b:
            return 0.0

        return self.similarity_calc.calculate(a, b)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'domains': len(self.domains),
            'knowledge_units': len(self.knowledge_units),
            'transfers_completed': sum(
                1 for r in self.transfer_results if r.success
            ),
            'transfers_failed': sum(
                1 for r in self.transfer_results if not r.success
            ),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🔄 迁移学习报告")
        report.append("=" * 50)
        report.append(f"\n领域数量: {stats['domains']}")
        report.append(f"知识单元: {stats['knowledge_units']}")
        report.append(f"迁移成功: {stats['transfers_completed']}")
        report.append(f"迁移失败: {stats['transfers_failed']}")

        if self.domains:
            report.append("\n领域列表:")
            for domain in self.domains.values():
                report.append(f"  - {domain.name}: {domain.knowledge_count}条知识")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = TransferLearningEngine("test_transfer_learning")

    # 注册领域
    engine.register_domain("python", "Python编程语言",
                          keywords=["python", "编程", "代码", "函数"],
                          concepts=["面向对象", "函数式", "模块"])

    engine.register_domain("javascript", "JavaScript编程语言",
                          keywords=["javascript", "编程", "代码", "函数"],
                          concepts=["面向对象", "函数式", "异步"])

    # 添加知识
    engine.add_knowledge(
        "列表推导式",
        "Python列表推导式是一种简洁的创建列表的方式，语法为 [x for x in range(10)]",
        domain="python",
        knowledge_type=KnowledgeType.PROCEDURE,
    )

    # 查找迁移候选
    print("=== 迁移候选 ===")
    candidates = engine.find_transfer_candidates("javascript")
    for c in candidates[:3]:
        print(f"  - {c['knowledge'].name} (相似度: {c['similarity']:.2f})")

    # 执行迁移
    if candidates:
        print("\n=== 执行迁移 ===")
        result = engine.transfer(candidates[0]['knowledge'].id, "javascript")
        print(f"成功: {result.success}")
        print(f"置信度: {result.confidence:.2f}")

    # 报告
    print("\n" + engine.generate_report())