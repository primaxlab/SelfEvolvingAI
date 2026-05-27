"""
================================================================================
自监督学习系统 (Self-Supervised Learning System)
================================================================================

核心能力：
  1. 自动标注 - 从未标注数据自动生成标签
  2. 对比学习 - 通过对比学习特征表示
  3. 预测学习 - 预测数据的缺失部分
  4. 一致性学习 - 学习数据的一致性约束
  5. 表示学习 - 学习数据的有效表示

设计原则：
  - 无需人工标注：自动从数据中学习
  - 通用表示：学习可迁移的表示
  - 数据效率：最大化利用未标注数据
"""

import json
import os
import time
import hashlib
import random
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class LearningTask(Enum):
    MASKED_PREDICTION = "masked_prediction"  # 遮挡预测
    CONTRASTIVE = "contrastive"              # 对比学习
    ROTATION = "rotation"                    # 旋转预测
    JIGSAW = "jigsaw"                        # 拼图预测
    TEMPORAL = "temporal"                    # 时序预测

@dataclass
class UnlabeledData:
    """未标注数据"""
    id: str
    content: Any
    modality: str                # 数据模态
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class PseudoLabel:
    """伪标签"""
    data_id: str
    label: Any
    confidence: float
    task: LearningTask
    created_at: float = field(default_factory=time.time)

@dataclass
class LearnedRepresentation:
    """学习到的表示"""
    data_id: str
    representation: list         # 向量表示
    quality_score: float
    task: LearningTask


# ============================================================================
# 自动标注器
# ============================================================================

class AutoAnnotator:
    """自动标注器"""

    def __init__(self):
        self.annotation_rules = {}
        self.confidence_threshold = 0.6

    def annotate_text(self, text: str) -> PseudoLabel:
        """自动标注文本"""
        # 基于规则的标注
        label = self._apply_rules(text)
        confidence = self._calculate_confidence(text, label)

        return PseudoLabel(
            data_id=hashlib.md5(text[:50].encode()).hexdigest()[:12],
            label=label,
            confidence=confidence,
            task=LearningTask.MASKED_PREDICTION,
        )

    def _apply_rules(self, text: str) -> str:
        """应用标注规则"""
        text_lower = text.lower()

        # 主题分类
        if any(kw in text_lower for kw in ['python', 'java', '代码', '函数']):
            return 'programming'
        elif any(kw in text_lower for kw in ['机器学习', '深度学习', 'ai']):
            return 'ai_ml'
        elif any(kw in text_lower for kw in ['数据', '分析', '统计']):
            return 'data_analysis'
        elif any(kw in text_lower for kw in ['网页', '前端', '后端']):
            return 'web_development'
        else:
            return 'general'

    def _calculate_confidence(self, text: str, label: str) -> float:
        """计算标注置信度"""
        # 基于文本长度和关键词匹配度
        base_confidence = 0.5

        # 长度加成
        if len(text) > 50:
            base_confidence += 0.1

        # 关键词匹配
        text_lower = text.lower()
        label_keywords = {
            'programming': ['python', 'java', '代码', '函数', '变量'],
            'ai_ml': ['机器学习', '深度学习', '神经网络', '模型'],
            'data_analysis': ['数据', '分析', '统计', '可视化'],
            'web_development': ['网页', '前端', '后端', 'api'],
        }

        keywords = label_keywords.get(label, [])
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            base_confidence += min(0.3, matches * 0.1)

        return min(0.95, base_confidence)

    def batch_annotate(self, texts: list) -> list:
        """批量标注"""
        return [self.annotate_text(text) for text in texts]


# ============================================================================
# 对比学习器
# ============================================================================

class ContrastiveLearner:
    """对比学习器"""

    def __init__(self):
        self.positive_pairs = []
        self.negative_pairs = []

    def create_pairs(self, data: list) -> dict:
        """创建正负样本对"""
        positive = []
        negative = []

        for i in range(len(data)):
            for j in range(i + 1, len(data)):
                # 计算相似度
                similarity = self._calculate_similarity(data[i], data[j])

                if similarity > 0.7:
                    positive.append((data[i].id, data[j].id, similarity))
                elif similarity < 0.3:
                    negative.append((data[i].id, data[j].id, similarity))

        self.positive_pairs.extend(positive)
        self.negative_pairs.extend(negative)

        return {
            'positive_pairs': len(positive),
            'negative_pairs': len(negative),
        }

    def _calculate_similarity(self, data_a: UnlabeledData,
                                data_b: UnlabeledData) -> float:
        """计算数据相似度"""
        if isinstance(data_a.content, str) and isinstance(data_b.content, str):
            words_a = set(data_a.content.lower().split())
            words_b = set(data_b.content.lower().split())

            if not words_a or not words_b:
                return 0.0

            intersection = len(words_a & words_b)
            union = len(words_a | words_b)

            return intersection / union if union > 0 else 0.0

        return 0.5

    def learn_representation(self, data: UnlabeledData) -> LearnedRepresentation:
        """学习表示"""
        # 简化实现：基于内容的简单表示
        if isinstance(data.content, str):
            # 字符级别的简单哈希表示
            representation = [ord(c) / 255.0 for c in data.content[:10]]
            # 填充到固定长度
            representation.extend([0.0] * (10 - len(representation)))
        else:
            representation = [0.5] * 10

        quality_score = 0.7  # 简化的质量分数

        return LearnedRepresentation(
            data_id=data.id,
            representation=representation,
            quality_score=quality_score,
            task=LearningTask.CONTRASTIVE,
        )


# ============================================================================
# 预测学习器
# ============================================================================

class PredictiveLearner:
    """预测学习器"""

    def __init__(self):
        self.prediction_tasks = []

    def create_masked_task(self, text: str) -> dict:
        """创建遮挡预测任务"""
        words = text.split()
        if len(words) < 3:
            return {'error': '文本太短'}

        # 随机遮挡一个词
        mask_index = random.randint(0, len(words) - 1)
        masked_word = words[mask_index]
        words[mask_index] = '[MASK]'

        return {
            'masked_text': ' '.join(words),
            'masked_word': masked_word,
            'mask_index': mask_index,
            'context': ' '.join(words[max(0, mask_index-2):mask_index+3]),
        }

    def create_temporal_task(self, sequence: list) -> dict:
        """创建时序预测任务"""
        if len(sequence) < 2:
            return {'error': '序列太短'}

        # 预测下一个值
        return {
            'input_sequence': sequence[:-1],
            'target': sequence[-1],
            'sequence_length': len(sequence),
        }

    def evaluate_prediction(self, predicted: Any,
                              actual: Any) -> dict:
        """评估预测"""
        if isinstance(predicted, str) and isinstance(actual, str):
            correct = predicted.lower() == actual.lower()
        else:
            correct = predicted == actual

        return {
            'correct': correct,
            'predicted': predicted,
            'actual': actual,
        }


# ============================================================================
# 自监督学习引擎
# ============================================================================

class SelfSupervisedLearningEngine:
    """
    自监督学习引擎 - 整合所有组件

    核心功能：
    1. 自动标注未标注数据
    2. 对比学习表示
    3. 预测学习任务
    4. 评估学习效果
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "self_supervised"
        os.makedirs(storage_dir, exist_ok=True)

        self.auto_annotator = AutoAnnotator()
        self.contrastive_learner = ContrastiveLearner()
        self.predictive_learner = PredictiveLearner()

        self.labeled_data: list[PseudoLabel] = []
        self.representations: dict[str, LearnedRepresentation] = {}
        self.learning_history: list[dict] = []

        self.storage_path = os.path.join(storage_dir, "ssl.json")
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

    def process_unlabeled_data(self, texts: list) -> dict:
        """处理未标注数据"""
        # 1. 自动标注
        labels = self.auto_annotator.batch_annotate(texts)
        self.labeled_data.extend(labels)

        # 2. 创建学习任务
        tasks = []
        for text in texts[:5]:  # 限制任务数量
            task = self.predictive_learner.create_masked_task(text)
            if 'error' not in task:
                tasks.append(task)

        # 记录学习历史
        self.learning_history.append({
            'data_count': len(texts),
            'labels_generated': len(labels),
            'tasks_created': len(tasks),
            'timestamp': time.time(),
        })
        self._save()

        return {
            'data_processed': len(texts),
            'labels': [{'label': l.label, 'confidence': l.confidence} for l in labels[:5]],
            'tasks': len(tasks),
        }

    def learn_representations(self, data: list) -> dict:
        """学习表示"""
        # 创建对比学习样本对
        pairs_result = self.contrastive_learner.create_pairs(data)

        # 学习表示
        representations = []
        for item in data:
            rep = self.contrastive_learner.learn_representation(item)
            self.representations[item.id] = rep
            representations.append(asdict(rep))

        return {
            'pairs': pairs_result,
            'representations_learned': len(representations),
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'labeled_data': len(self.labeled_data),
            'representations': len(self.representations),
            'learning_sessions': len(self.learning_history),
            'positive_pairs': len(self.contrastive_learner.positive_pairs),
            'negative_pairs': len(self.contrastive_learner.negative_pairs),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("📚 自监督学习报告")
        report.append("=" * 50)
        report.append(f"\n已标注数据: {stats['labeled_data']}")
        report.append(f"学习表示: {stats['representations']}")
        report.append(f"学习会话: {stats['learning_sessions']}")
        report.append(f"正样本对: {stats['positive_pairs']}")
        report.append(f"负样本对: {stats['negative_pairs']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = SelfSupervisedLearningEngine("test_self_supervised")

    # 未标注数据
    texts = [
        "Python是一种解释型编程语言",
        "机器学习使用算法从数据中学习",
        "深度学习是机器学习的子领域",
        "Web开发包括前端和后端",
        "数据���析需要统计学知识",
    ]

    # 处理数据
    print("=== 自监督学习 ===")
    result = engine.process_unlabeled_data(texts)
    print(f"处理数据: {result['data_processed']}")
    print(f"生成标签: {len(result['labels'])}")
    for label in result['labels']:
        print(f"  - {label['label']} (置信度: {label['confidence']:.2f})")

    # 学习表示
    print("\n=== 学习表示 ===")
    unlabeled_data = [
        UnlabeledData(id=f"d{i}", content=text, modality="text")
        for i, text in enumerate(texts)
    ]
    rep_result = engine.learn_representations(unlabeled_data)
    print(f"学习表示: {rep_result['representations_learned']}")
    print(f"正样本对: {rep_result['pairs']['positive_pairs']}")

    # 报告
    print("\n" + engine.generate_report())