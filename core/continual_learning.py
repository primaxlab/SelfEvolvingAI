"""
================================================================================
持续学习系统 (Continual Learning System)
================================================================================

核心能力：
  1. 增量学习 - 从新数据中持续学习
  2. 遗忘防护 - 防止灾难性遗忘
  3. 知识巩固 - 将新知识整合到已有知识体系
  4. 重要性评估 - 评估知识的重要性
  5. 弹性权重巩固 - 保护重要知识不被覆盖

设计原则：
  - 稳定性-可塑性平衡：在学习新知识和保留旧知识间平衡
  - 选择性遗忘：不重要的知识可以遗忘
  - 渐进整合：新知识逐步整合到知识体系
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

class KnowledgeImportance(Enum):
    TRIVIAL = 0     # 琐碎
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4    # 关键

@dataclass
class KnowledgeItem:
    """知识项"""
    id: str
    content: str
    domain: str
    importance: KnowledgeImportance
    confidence: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    consolidation_score: float = 0.0  # 巩固分数
    interference_score: float = 0.0   # 干扰分数

@dataclass
class LearningSession:
    """学习会话"""
    id: str
    domain: str
    knowledge_items: list
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    items_learned: int = 0
    items_forgotten: int = 0

@dataclass
class ForgettingCurve:
    """遗忘曲线参数"""
    initial_strength: float = 1.0
    decay_rate: float = 0.1
    stability: float = 1.0  # 稳定性，越高遗忘越慢


# ============================================================================
# 遗忘防护器
# ============================================================================

class ForgettingProtector:
    """遗忘防护器"""

    def __init__(self):
        # 遗忘曲线参数
        self.forgetting_curves: dict[str, ForgettingCurve] = {}

    def calculate_retention(self, item: KnowledgeItem,
                             current_time: float = None) -> float:
        """计算知识保留率"""
        if current_time is None:
            current_time = time.time()

        # 获取遗忘曲线
        curve = self.forgetting_curves.get(item.id)
        if not curve:
            curve = ForgettingCurve()
            self.forgetting_curves[item.id] = curve

        # 计算时间差（天）
        time_diff = (current_time - item.last_accessed) / 86400

        # 艾宾浩斯遗忘曲线公式
        # R = e^(-t/S) 其中R是保留率，t是时间，S是稳定性
        retention = math.exp(-time_diff / (curve.stability * 10))

        # 考虑重要性调整
        importance_factor = 1.0 + item.importance.value * 0.1
        retention = min(1.0, retention * importance_factor)

        return retention

    def update_stability(self, item: KnowledgeItem,
                          successful_recall: bool):
        """更新稳定性"""
        curve = self.forgetting_curves.get(item.id)
        if not curve:
            curve = ForgettingCurve()
            self.forgetting_curves[item.id] = curve

        if successful_recall:
            # 成功回忆增加稳定性
            curve.stability = min(10.0, curve.stability * 1.2)
        else:
            # 失败降低稳定性
            curve.stability = max(0.1, curve.stability * 0.8)

    def needs_review(self, item: KnowledgeItem,
                      threshold: float = 0.5) -> bool:
        """判断是否需要复习"""
        retention = self.calculate_retention(item)
        return retention < threshold

    def get_review_priority(self, items: list) -> list:
        """获取复习优先级"""
        prioritized = []

        for item in items:
            retention = self.calculate_retention(item)
            priority = (1 - retention) * item.importance.value
            prioritized.append({
                'item': item,
                'retention': retention,
                'priority': priority,
            })

        # 按优先级排序
        prioritized.sort(key=lambda x: x['priority'], reverse=True)
        return prioritized


# ============================================================================
# 知识巩固器
# ============================================================================

class KnowledgeConsolidator:
    """知识巩固器"""

    def __init__(self):
        # 巩固策略
        self.strategies = {
            'spaced_repetition': self._spaced_repetition,
            'elaborative_rehearsal': self._elaborative_rehearsal,
            'interleaving': self._interleaving,
        }

    def consolidate(self, item: KnowledgeItem,
                     related_items: list = None,
                     strategy: str = 'spaced_repetition') -> KnowledgeItem:
        """巩固知识"""
        consolidator = self.strategies.get(strategy, self._spaced_repetition)
        return consolidator(item, related_items)

    def _spaced_repetition(self, item: KnowledgeItem,
                            related_items: list = None) -> KnowledgeItem:
        """间隔重复巩固"""
        # 增加巩固分数
        item.consolidation_score = min(1.0, item.consolidation_score + 0.1)

        # 降低干扰分数
        item.interference_score = max(0.0, item.interference_score - 0.05)

        return item

    def _elaborative_rehearsal(self, item: KnowledgeItem,
                                related_items: list = None) -> KnowledgeItem:
        """精细复述巩固"""
        # 增加巩固分数（更多）
        item.consolidation_score = min(1.0, item.consolidation_score + 0.15)

        # 如果有相关知识，降低干扰
        if related_items:
            item.interference_score = max(
                0.0,
                item.interference_score - 0.1 * len(related_items)
            )

        return item

    def _interleaving(self, item: KnowledgeItem,
                       related_items: list = None) -> KnowledgeItem:
        """交错练习巩固"""
        # 增加巩固分数
        item.consolidation_score = min(1.0, item.consolidation_score + 0.12)

        return item

    def calculate_consolidation_level(self, item: KnowledgeItem) -> str:
        """计算巩固程度"""
        if item.consolidation_score >= 0.8:
            return "高度巩固"
        elif item.consolidation_score >= 0.5:
            return "中度巩固"
        elif item.consolidation_score >= 0.2:
            return "初步巩固"
        else:
            return "未巩固"


# ============================================================================
# 干扰检测器
# ============================================================================

class InterferenceDetector:
    """干扰检测器"""

    def detect(self, new_item: KnowledgeItem,
               existing_items: list) -> list:
        """检测新知识与现有知识的干扰"""
        interferences = []

        for existing in existing_items:
            interference_score = self._calculate_interference(new_item, existing)

            if interference_score > 0.3:  # 阈值
                interferences.append({
                    'existing_item': existing,
                    'interference_score': interference_score,
                    'type': self._classify_interference(new_item, existing),
                })

        return interferences

    def _calculate_interference(self, item_a: KnowledgeItem,
                                  item_b: KnowledgeItem) -> float:
        """计算干扰分数"""
        # 基于内容相似度
        words_a = set(item_a.content.lower().split())
        words_b = set(item_b.content.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        similarity = intersection / union if union > 0 else 0

        # 同领域干扰更大
        domain_factor = 1.5 if item_a.domain == item_b.domain else 1.0

        return similarity * domain_factor

    def _classify_interference(self, item_a: KnowledgeItem,
                                 item_b: KnowledgeItem) -> str:
        """分类干扰类型"""
        if item_a.domain == item_b.domain:
            return "领域内干扰"
        else:
            return "领域间干扰"


# ============================================================================
# 持续学习引擎
# ============================================================================

class ContinualLearningEngine:
    """
    持续学习引擎 - 整合所有组件

    核心功能：
    1. 增量学习新知识
    2. 防止灾难性遗忘
    3. 巩固重要知识
    4. 检测和处理干扰
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "continual_learning"
        os.makedirs(storage_dir, exist_ok=True)

        self.forgetting_protector = ForgettingProtector()
        self.consolidator = KnowledgeConsolidator()
        self.interference_detector = InterferenceDetector()

        self.knowledge_base: dict[str, KnowledgeItem] = {}
        self.learning_sessions: list[LearningSession] = []

        self.storage_path = os.path.join(storage_dir, "knowledge.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for k_data in data.get('knowledge', []):
                    k_data['importance'] = KnowledgeImportance(k_data['importance'])
                    item = KnowledgeItem(**k_data)
                    self.knowledge_base[item.id] = item

    def _save(self):
        """保存数据"""
        data = {
            'knowledge': [],
        }

        for item in self.knowledge_base.values():
            k_dict = asdict(item)
            k_dict['importance'] = item.importance.value
            data['knowledge'].append(k_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def learn(self, content: str, domain: str,
              importance: KnowledgeImportance = KnowledgeImportance.MEDIUM) -> dict:
        """学习新知识"""
        # 创建知识项
        item_id = hashlib.md5(f"{domain}:{content[:50]}".encode()).hexdigest()[:12]
        item = KnowledgeItem(
            id=item_id,
            content=content,
            domain=domain,
            importance=importance,
            confidence=0.8,
        )

        # 检测干扰
        existing = list(self.knowledge_base.values())
        interferences = self.interference_detector.detect(item, existing)

        # 处理干扰
        if interferences:
            for interference in interferences:
                existing_item = interference['existing_item']
                existing_item.interference_score = interference['interference_score']

        # 巩固知识
        item = self.consolidator.consolidate(item)

        # 存储
        self.knowledge_base[item_id] = item
        self._save()

        return {
            'item_id': item_id,
            'content': content,
            'consolidation_level': self.consolidator.calculate_consolidation_level(item),
            'interferences_detected': len(interferences),
        }

    def recall(self, query: str, domain: str = None) -> list:
        """回忆知识"""
        results = []
        query_lower = query.lower()

        for item in self.knowledge_base.values():
            # 域过滤
            if domain and item.domain != domain:
                continue

            # 内容匹配
            if query_lower in item.content.lower():
                # 更新访问信息
                item.access_count += 1
                item.last_accessed = time.time()

                # 计算保留率
                retention = self.forgetting_protector.calculate_retention(item)

                results.append({
                    'item': item,
                    'retention': retention,
                    'relevance': 1.0,  # 简化
                })

        # 按相关性和保留率排序
        results.sort(key=lambda x: x['retention'], reverse=True)
        return results

    def review_needed(self) -> list:
        """获取需要复习的知识"""
        items = list(self.knowledge_base.values())
        prioritized = self.forgetting_protector.get_review_priority(items)

        return [
            {
                'item': p['item'],
                'retention': p['retention'],
                'priority': p['priority'],
            }
            for p in prioritized
            if p['retention'] < 0.6
        ]

    def consolidate_knowledge(self, item_id: str,
                               strategy: str = 'spaced_repetition') -> dict:
        """巩固知识"""
        item = self.knowledge_base.get(item_id)
        if not item:
            return {'error': '知识不存在'}

        # 获取相关知识
        related = [
            i for i in self.knowledge_base.values()
            if i.domain == item.domain and i.id != item.id
        ]

        # 巩固
        item = self.consolidator.consolidate(item, related, strategy)
        self.knowledge_base[item_id] = item
        self._save()

        return {
            'item_id': item_id,
            'consolidation_level': self.consolidator.calculate_consolidation_level(item),
            'consolidation_score': item.consolidation_score,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        total = len(self.knowledge_base)
        by_domain = {}
        by_importance = {}

        for item in self.knowledge_base.values():
            # 按领域统计
            if item.domain not in by_domain:
                by_domain[item.domain] = 0
            by_domain[item.domain] += 1

            # 按重要性统计
            imp = item.importance.value
            if imp not in by_importance:
                by_importance[imp] = 0
            by_importance[imp] += 1

        return {
            'total_knowledge': total,
            'by_domain': by_domain,
            'by_importance': by_importance,
            'needs_review': len(self.review_needed()),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("📚 持续学习报告")
        report.append("=" * 50)
        report.append(f"\n知识总数: {stats['total_knowledge']}")
        report.append(f"需要复习: {stats['needs_review']}")

        if stats['by_domain']:
            report.append("\n领域分布:")
            for domain, count in stats['by_domain'].items():
                report.append(f"  - {domain}: {count}")

        if stats['by_importance']:
            report.append("\n重要性分布:")
            for imp, count in sorted(stats['by_importance'].items(), reverse=True):
                report.append(f"  - 重要性{imp}: {count}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = ContinualLearningEngine("test_continual_learning")

    # 学习新知识
    print("=== 学习新知识 ===")
    knowledge_items = [
        ("Python列表推导式是创建列表的简洁方式", "python", KnowledgeImportance.HIGH),
        ("JavaScript使用let和const声明变量", "javascript", KnowledgeImportance.MEDIUM),
        ("机器学习是人工智能的子领域", "machine_learning", KnowledgeImportance.HIGH),
        ("深度学习使用神经网络", "machine_learning", KnowledgeImportance.MEDIUM),
    ]

    for content, domain, importance in knowledge_items:
        result = engine.learn(content, domain, importance)
        print(f"学习: {content[:30]}...")
        print(f"  巩固程度: {result['consolidation_level']}")
        print(f"  干扰检测: {result['interferences_detected']}")

    # 回忆
    print("\n=== 回忆测试 ===")
    results = engine.recall("Python")
    for r in results:
        print(f"  - {r['item'].content[:40]}... (保留率: {r['retention']:.2f})")

    # 需要复习的
    print("\n=== 需要复习 ===")
    review = engine.review_needed()
    for r in review[:3]:
        print(f"  - {r['item'].content[:40]}... (保留率: {r['retention']:.2f})")

    # 报告
    print("\n" + engine.generate_report())