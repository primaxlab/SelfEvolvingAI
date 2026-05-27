"""
================================================================================
多模态感知系统 (Multimodal Perception System)
================================================================================

核心能力：
  1. 文本理解 - 理解自然语言文本
  2. 图像识别 - 识别图像内容（框架）
  3. 音频处理 - 处理音频信息（框架）
  4. 跨模态关联 - 关联不同模态的信息
  5. 多模态融合 - 融合多模态信息进行理解

设计原则：
  - 统一表示：将不同模态信息转换为统一表示
  - 互补融合：利用不同模态的互补信息
  - 容错处理：单一模态失败时仍能工作
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

class ModalityType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED = "structured"  # 结构化数据

@dataclass
class ModalityInput:
    """模态输入"""
    modality: ModalityType
    content: Any
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class ModalityFeature:
    """模态特征"""
    modality: ModalityType
    features: dict
    confidence: float
    extraction_method: str

@dataclass
class MultimodalRepresentation:
    """多模态表示"""
    id: str
    modalities: list  # 包含的模态类型
    features: dict    # 各模态特征
    fused_feature: dict  # 融合后的特征
    confidence: float
    created_at: float = field(default_factory=time.time)


# ============================================================================
# 文本处理器
# ============================================================================

class TextProcessor:
    """文本处理器"""

    def __init__(self):
        # 关键词词典
        self.keyword_categories = {
            'programming': ['python', 'java', '代码', '函数', '变量', '算法'],
            'data': ['数据', '分析', '统计', '图表', '可视化'],
            'ai': ['机器学习', '深度学习', '神经网络', '模型', '训练'],
            'web': ['网页', '前端', '后端', 'API', '服务器'],
        }

    def extract_features(self, text: str) -> ModalityFeature:
        """提取文本特征"""
        text_lower = text.lower()

        # 基本统计
        features = {
            'length': len(text),
            'word_count': len(text.split()),
            'sentence_count': len(re.split(r'[。！？.!?]', text)),
            'has_code': bool(re.search(r'def |class |import |function', text)),
            'has_question': '?' in text or '？' in text,
        }

        # 主题分类
        topic_scores = {}
        for topic, keywords in self.keyword_categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                topic_scores[topic] = score

        features['topics'] = topic_scores
        features['main_topic'] = max(topic_scores, key=topic_scores.get) if topic_scores else 'general'

        # 情感倾向（简单）
        positive_words = ['好', '棒', '优秀', '成功', '喜欢', '感谢']
        negative_words = ['差', '坏', '失败', '问题', '错误', '困难']

        positive_count = sum(1 for w in positive_words if w in text)
        negative_count = sum(1 for w in negative_words if w in text)

        if positive_count > negative_count:
            features['sentiment'] = 'positive'
        elif negative_count > positive_count:
            features['sentiment'] = 'negative'
        else:
            features['sentiment'] = 'neutral'

        return ModalityFeature(
            modality=ModalityType.TEXT,
            features=features,
            confidence=0.8,
            extraction_method='rule_based',
        )

    def summarize(self, text: str, max_length: int = 100) -> str:
        """生成摘要"""
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return text[:max_length]

        # 取前几句
        summary = ''
        for sentence in sentences:
            if len(summary) + len(sentence) <= max_length:
                summary += sentence + '。'
            else:
                break

        return summary if summary else sentences[0][:max_length]


# ============================================================================
# 图像处理器（框架）
# ============================================================================

class ImageProcessor:
    """图像处理器（框架）"""

    def __init__(self):
        # 实际应用时接入计算机视觉模型
        pass

    def extract_features(self, image_path: str = None,
                          image_data: bytes = None) -> ModalityFeature:
        """提取图像特征"""
        # 框架实现
        features = {
            'width': 0,
            'height': 0,
            'format': 'unknown',
            'objects': [],
            'scene': 'unknown',
            'colors': [],
        }

        return ModalityFeature(
            modality=ModalityType.IMAGE,
            features=features,
            confidence=0.0,
            extraction_method='placeholder',
        )

    def describe(self, image_path: str = None) -> str:
        """描述图像内容"""
        # 框架实现
        return "图像描述功能需要接入计算机视觉模型"


# ============================================================================
# 音频处理器（框架）
# ============================================================================

class AudioProcessor:
    """音频处理器（框架）"""

    def __init__(self):
        # 实际应用时接入语音识别模型
        pass

    def extract_features(self, audio_path: str = None,
                          audio_data: bytes = None) -> ModalityFeature:
        """提取音频特征"""
        features = {
            'duration': 0,
            'sample_rate': 0,
            'channels': 0,
            'transcript': '',
            'language': 'unknown',
            'emotion': 'neutral',
        }

        return ModalityFeature(
            modality=ModalityType.AUDIO,
            features=features,
            confidence=0.0,
            extraction_method='placeholder',
        )

    def transcribe(self, audio_path: str = None) -> str:
        """转录音频"""
        return "音频转录功能需要接入语音识别模型"


# ============================================================================
# 跨模态关联器
# ============================================================================

class CrossModalAssociator:
    """跨模态关联器"""

    def __init__(self):
        # 关联规则
        self.association_rules = []

    def associate(self, features_a: ModalityFeature,
                   features_b: ModalityFeature) -> dict:
        """关联两个模态的特征"""
        associations = []

        # 文本-图像关联
        if (features_a.modality == ModalityType.TEXT and
            features_b.modality == ModalityType.IMAGE):
            associations.extend(
                self._associate_text_image(features_a, features_b)
            )

        # 文本-音频关联
        if (features_a.modality == ModalityType.TEXT and
            features_b.modality == ModalityType.AUDIO):
            associations.extend(
                self._associate_text_audio(features_a, features_b)
            )

        return {
            'associations': associations,
            'confidence': sum(a.get('confidence', 0) for a in associations) / max(1, len(associations)),
        }

    def _associate_text_image(self, text_features: ModalityFeature,
                                image_features: ModalityFeature) -> list:
        """关联文本和图像"""
        associations = []

        # 检查文本是否描述了图像中的对象
        text_content = text_features.features
        image_content = image_features.features

        if text_content.get('has_code') and 'diagram' in str(image_content.get('scene', '')):
            associations.append({
                'type': 'text_describes_image',
                'description': '文本可能是图像的说明',
                'confidence': 0.6,
            })

        return associations

    def _associate_text_audio(self, text_features: ModalityFeature,
                                audio_features: ModalityFeature) -> list:
        """关联文本和音频"""
        associations = []

        # 检查文本是否是音频的转录
        text_content = text_features.features
        audio_content = audio_features.features

        if audio_content.get('transcript'):
            # 简单匹配
            text_words = set(text_content.get('text', '').lower().split())
            audio_words = set(audio_content['transcript'].lower().split())

            if text_words & audio_words:
                associations.append({
                    'type': 'text_matches_audio',
                    'description': '文本与音频内容匹配',
                    'confidence': 0.7,
                })

        return associations


# ============================================================================
# 多模态融合器
# ============================================================================

class MultimodalFusion:
    """多模态融合器"""

    def fuse(self, features_list: list) -> MultimodalRepresentation:
        """融合多个模态的特征"""
        if not features_list:
            return MultimodalRepresentation(
                id="empty",
                modalities=[],
                features={},
                fused_feature={},
                confidence=0.0,
            )

        # 收集各模态特征
        all_features = {}
        modalities = []

        for features in features_list:
            modality = features.modality.value
            modalities.append(modality)
            all_features[modality] = features.features

        # 融合策略：加权平均
        fused = self._weighted_fusion(features_list)

        # 生成ID
        rep_id = hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:12]

        # 计算综合置信度
        avg_confidence = sum(f.confidence for f in features_list) / len(features_list)

        return MultimodalRepresentation(
            id=rep_id,
            modalities=modalities,
            features=all_features,
            fused_feature=fused,
            confidence=avg_confidence,
        )

    def _weighted_fusion(self, features_list: list) -> dict:
        """加权融合"""
        fused = {}

        # 合并所有特征
        for features in features_list:
            for key, value in features.features.items():
                if key not in fused:
                    fused[key] = []
                fused[key].append({
                    'value': value,
                    'modality': features.modality.value,
                    'confidence': features.confidence,
                })

        # 对每个特征取加权平均或众数
        result = {}
        for key, values in fused.items():
            if isinstance(values[0]['value'], (int, float)):
                # 数值型：加权平均
                total_weight = sum(v['confidence'] for v in values)
                if total_weight > 0:
                    result[key] = sum(
                        v['value'] * v['confidence'] for v in values
                    ) / total_weight
            else:
                # 非数值型：取置信度最高的
                best = max(values, key=lambda v: v['confidence'])
                result[key] = best['value']

        return result


# ============================================================================
# 多模态感知引擎
# ============================================================================

class MultimodalPerceptionEngine:
    """
    多模态感知引擎 - 整合所有组件

    核心功能：
    1. 处理不同模态的输入
    2. 提取各模态特征
    3. 关联跨模态信息
    4. 融合多模态理解
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "multimodal"
        os.makedirs(storage_dir, exist_ok=True)

        self.text_processor = TextProcessor()
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.associator = CrossModalAssociator()
        self.fusion = MultimodalFusion()

        self.representations: dict[str, MultimodalRepresentation] = {}

    def process_text(self, text: str) -> ModalityFeature:
        """处理文本"""
        return self.text_processor.extract_features(text)

    def process_image(self, image_path: str = None) -> ModalityFeature:
        """处理图像"""
        return self.image_processor.extract_features(image_path)

    def process_audio(self, audio_path: str = None) -> ModalityFeature:
        """处理音频"""
        return self.audio_processor.extract_features(audio_path)

    def process_multimodal(self, inputs: list) -> dict:
        """处理多模态输入"""
        features_list = []

        for inp in inputs:
            if inp.modality == ModalityType.TEXT:
                features = self.text_processor.extract_features(inp.content)
            elif inp.modality == ModalityType.IMAGE:
                features = self.image_processor.extract_features(inp.content)
            elif inp.modality == ModalityType.AUDIO:
                features = self.audio_processor.extract_features(inp.content)
            else:
                continue

            features_list.append(features)

        if not features_list:
            return {'error': '没有有效的模态输入'}

        # 融合
        representation = self.fusion.fuse(features_list)

        # 存储
        self.representations[representation.id] = representation

        return {
            'id': representation.id,
            'modalities': representation.modalities,
            'features': representation.fused_feature,
            'confidence': representation.confidence,
        }

    def get_text_understanding(self, text: str) -> dict:
        """获取文本理解"""
        features = self.text_processor.extract_features(text)
        summary = self.text_processor.summarize(text)

        return {
            'features': features.features,
            'summary': summary,
            'confidence': features.confidence,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'representations': len(self.representations),
            'modalities_processed': list(set(
                m for rep in self.representations.values()
                for m in rep.modalities
            )),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("👁️ 多模态感知报告")
        report.append("=" * 50)
        report.append(f"\n表示数量: {stats['representations']}")
        report.append(f"处理模态: {', '.join(stats['modalities_processed']) if stats['modalities_processed'] else '无'}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = MultimodalPerceptionEngine("test_multimodal")

    # 文本处理
    print("=== 文本处理 ===")
    text = "Python是一种解释型、面向对象、动态类型的高级编程语言。它广泛应用于Web开发、数据分析和人工智能领域。"
    result = engine.get_text_understanding(text)
    print(f"主题: {result['features']['main_topic']}")
    print(f"摘要: {result['summary']}")
    print(f"情感: {result['features']['sentiment']}")

    # 多模态处理
    print("\n=== 多模态处理 ===")
    inputs = [
        ModalityInput(modality=ModalityType.TEXT, content="这是一段代码"),
        ModalityInput(modality=ModalityType.IMAGE, content="diagram.png"),
    ]
    result = engine.process_multimodal(inputs)
    print(f"模态: {result.get('modalities', [])}")
    print(f"置信度: {result.get('confidence', 0):.2f}")

    # 报告
    print("\n" + engine.generate_report())