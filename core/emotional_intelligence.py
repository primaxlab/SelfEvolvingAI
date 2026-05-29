"""
================================================================================
情感智能系统 (Emotional Intelligence System)
================================================================================

核心能力：
  1. 情绪识别 - 识别用户的情绪状态
  2. 情绪理解 - 理解情绪背后的原因
  3. 情绪响应 - 根据情绪调整交互方式
  4. 情绪记忆 - 记住用户的情绪模式
  5. 情绪预测 - 预测用户可能的情绪变化

设计原则：
  - 共情优先：先理解情绪，再解决问题
  - 适应性：根据情绪状态调整交互风格
  - 尊重隐私：不滥用情绪信息
"""

import json
import os
import time
import re
import hashlib
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class EmotionType(Enum):
    NEUTRAL = "neutral"        # 中性
    HAPPY = "happy"           # 开心
    SAD = "sad"               # 悲伤
    ANGRY = "angry"           # 愤怒
    FRUSTRATED = "frustrated" # 沮丧
    ANXIOUS = "anxious"       # 焦虑
    CONFUSED = "confused"     # 困惑
    EXCITED = "excited"       # 兴奋
    SATISFIED = "satisfied"   # 满意
    DISAPPOINTED = "disappointed"  # 失望

class EmotionIntensity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4

class ResponseStyle(Enum):
    FORMAL = "formal"          # 正式
    FRIENDLY = "friendly"      # 友好
    EMPATHETIC = "empathetic"  # 共情
    ENCOURAGING = "encouraging" # 鼓励
    CALM = "calm"             # 冷静
    CONCISE = "concise"       # 简洁

@dataclass
class EmotionState:
    """情绪状态"""
    emotion: EmotionType
    intensity: EmotionIntensity
    confidence: float  # 识别置信度
    triggers: list = field(default_factory=list)  # 触发因素
    timestamp: float = field(default_factory=time.time)

@dataclass
class EmotionPattern:
    """情绪模式"""
    user_id: str
    frequent_emotions: dict = field(default_factory=dict)  # 常见情绪
    triggers: dict = field(default_factory=dict)           # 常见触发因素
    preferred_response_style: ResponseStyle = ResponseStyle.FRIENDLY
    interaction_count: int = 0
    last_interaction: float = 0.0

@dataclass
class EmotionResponse:
    """情绪响应"""
    emotion_detected: EmotionType
    response_style: ResponseStyle
    empathy_statement: str  # 共情语句
    adjustment: str         # 交互调整建议
    tone: str              # 语气建议


# ============================================================================
# 情绪识别器
# ============================================================================

class EmotionRecognizer:
    """情绪识别器"""

    def __init__(self):
        # 情绪关键词库
        self.emotion_keywords = {
            EmotionType.HAPPY: [
                '开心', '高兴', '太好了', '棒', '赞', '感谢', '谢谢',
                'happy', 'great', 'awesome', 'thanks', 'wonderful',
                'excellent', 'perfect', 'love', 'amazing',
            ],
            EmotionType.SAD: [
                '难过', '伤心', '失望', '可惜', '遗憾',
                'sad', 'disappointed', 'unfortunately', 'pity',
            ],
            EmotionType.ANGRY: [
                '生气', '愤怒', '烦', '讨厌', '垃圾',
                'angry', 'hate', 'stupid', 'terrible', 'awful',
                'useless', 'worst',
            ],
            EmotionType.FRUSTRATED: [
                '沮丧', '无奈', '搞不定', '不会', '太难了',
                'frustrated', 'stuck', 'confused', 'don\'t understand',
                'can\'t figure out', 'no idea',
            ],
            EmotionType.ANXIOUS: [
                '担心', '焦虑', '着急', '急', '快',
                'worried', 'anxious', 'urgent', 'hurry', 'asap',
                'deadline', '紧急',
            ],
            EmotionType.CONFUSED: [
                '困惑', '不懂', '什么意思', '为什么', '怎么',
                'confused', 'what', 'why', 'how', 'don\'t get it',
                'unclear', 'unclear',
            ],
            EmotionType.EXCITED: [
                '兴奋', '期待', '想', '希望',
                'excited', 'looking forward', 'can\'t wait', 'hope',
            ],
            EmotionType.SATISFIED: [
                '满意', '不错', '可以', '好的',
                'satisfied', 'good', 'okay', 'fine', 'nice',
            ],
            EmotionType.DISAPPOINTED: [
                '失望', '不满意', '不好', '差',
                'disappointed', 'not good', 'poor', 'bad',
            ],
        }

    def recognize(self, text: str) -> EmotionState:
        """识别文本中的情绪"""
        text_lower = text.lower()
        emotion_scores = {}

        # 计算每种情绪的匹配分数
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            triggers = []

            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    triggers.append(keyword)

            if score > 0:
                emotion_scores[emotion] = {
                    'score': score,
                    'triggers': triggers,
                }

        # 找到最匹配的情绪
        if emotion_scores:
            best_emotion = max(emotion_scores.keys(),
                             key=lambda e: emotion_scores[e]['score'])
            best_score = emotion_scores[best_emotion]['score']
            triggers = emotion_scores[best_emotion]['triggers']

            # 计算强度
            if best_score >= 3:
                intensity = EmotionIntensity.HIGH
            elif best_score >= 2:
                intensity = EmotionIntensity.MEDIUM
            else:
                intensity = EmotionIntensity.LOW

            # 计算置信度
            confidence = min(0.95, 0.5 + best_score * 0.15)

            return EmotionState(
                emotion=best_emotion,
                intensity=intensity,
                confidence=confidence,
                triggers=triggers,
            )

        # 默认中性
        return EmotionState(
            emotion=EmotionType.NEUTRAL,
            intensity=EmotionIntensity.LOW,
            confidence=0.5,
        )

    def recognize_from_context(self, text: str, context: dict) -> EmotionState:
        """结合上下文识别情绪"""
        # 基本文本识别
        state = self.recognize(text)

        # 结合上下文调整
        if context.get('previous_emotion'):
            prev_emotion = context['previous_emotion']
            # 情绪连续性：如果之前是负面情绪，现在可能是延续
            if prev_emotion in [EmotionType.ANGRY, EmotionType.FRUSTRATED]:
                if state.emotion == EmotionType.NEUTRAL:
                    state.emotion = prev_emotion
                    state.confidence *= 0.8  # 降低置信度

        return state


# ============================================================================
# 情绪理解器
# ============================================================================

class EmotionInterpreter:
    """情绪理解器"""

    def __init__(self):
        # 情绪-原因映射
        self.emotion_causes = {
            EmotionType.FRUSTRATED: [
                '遇到困难',
                '不理解内容',
                '多次尝试失败',
                '期望过高',
            ],
            EmotionType.ANGRY: [
                '感到被冒犯',
                '结果不满意',
                '感到被忽视',
                '不公平对待',
            ],
            EmotionType.ANXIOUS: [
                '时间压力',
                '不确定性',
                '重要任务',
                '害怕失败',
            ],
            EmotionType.CONFUSED: [
                '信息不清晰',
                '概念复杂',
                '缺乏背景知识',
                '表述模糊',
            ],
            EmotionType.DISAPPOINTED: [
                '期望未满足',
                '结果不如预期',
                '服务质量差',
                '承诺未兑现',
            ],
        }

    def interpret(self, emotion_state: EmotionState,
                  context: dict = None) -> dict:
        """解释情绪"""
        context = context or {}

        # 获取可能的原因
        possible_causes = self.emotion_causes.get(
            emotion_state.emotion, ['未知原因']
        )

        # 根据触发因素进一步分析
        specific_causes = []
        for trigger in emotion_state.triggers:
            if trigger in ['不会', '不懂', 'confused']:
                specific_causes.append('理解困难')
            elif trigger in ['失败', '错误', 'error']:
                specific_causes.append('执行失败')
            elif trigger in ['急', '快', 'urgent']:
                specific_causes.append('时间压力')

        return {
            'emotion': emotion_state.emotion.value,
            'intensity': emotion_state.intensity.value,
            'possible_causes': possible_causes,
            'specific_causes': specific_causes,
            'needs_support': emotion_state.emotion in [
                EmotionType.FRUSTRATED,
                EmotionType.ANGRY,
                EmotionType.ANXIOUS,
                EmotionType.DISAPPOINTED,
            ],
        }


# ============================================================================
# 情绪响应生成器
# ============================================================================

class EmotionResponder:
    """情绪响应生成器"""

    def __init__(self):
        # 共情语句模板
        self.empathy_templates = {
            EmotionType.FRUSTRATED: [
                "我理解这可能让你感到沮丧。",
                "遇到困难确实令人烦恼。",
                "让我们一步步来解决这个问题。",
            ],
            EmotionType.ANGRY: [
                "我理解你的感受。",
                "抱歉让你有了不好的体验。",
                "让我们一起来改善这个情况。",
            ],
            EmotionType.ANXIOUS: [
                "别担心，我们有足够的时间。",
                "让我们先理清思路。",
                "一步一步来，不着急。",
            ],
            EmotionType.CONFUSED: [
                "让我换个方式解释。",
                "这个问题确实有点复杂。",
                "我来详细说明一下。",
            ],
            EmotionType.DISAPPOINTED: [
                "我理解你的失望。",
                "让我看看还能做些什么。",
                "我们可以尝试其他方法。",
            ],
            EmotionType.HAPPY: [
                "很高兴能帮到你！",
                "这真是太好了！",
                "继续保持！",
            ],
            EmotionType.SATISFIED: [
                "很高兴你满意。",
                "如果有其他需要，随时告诉我。",
            ],
        }

        # 响应风格映射
        self.response_styles = {
            EmotionType.FRUSTRATED: ResponseStyle.ENCOURAGING,
            EmotionType.ANGRY: ResponseStyle.EMPATHETIC,
            EmotionType.ANXIOUS: ResponseStyle.CALM,
            EmotionType.CONFUSED: ResponseStyle.FRIENDLY,
            EmotionType.DISAPPOINTED: ResponseStyle.EMPATHETIC,
            EmotionType.HAPPY: ResponseStyle.FRIENDLY,
            EmotionType.SATISFIED: ResponseStyle.FRIENDLY,
            EmotionType.NEUTRAL: ResponseStyle.FORMAL,
        }

    def generate_response(self, emotion_state: EmotionState,
                          interpretation: dict) -> EmotionResponse:
        """生成情绪响应"""
        # 选择响应风格
        response_style = self.response_styles.get(
            emotion_state.emotion, ResponseStyle.FRIENDLY
        )

        # 选择共情语句
        empathy_templates = self.empathy_templates.get(
            emotion_state.emotion, ["我理解。"]
        )
        empathy_statement = empathy_templates[0]  # 选择第一个

        # 生成调整建议
        adjustment = self._generate_adjustment(emotion_state, interpretation)

        # 生成语气建议
        tone = self._generate_tone(emotion_state)

        return EmotionResponse(
            emotion_detected=emotion_state.emotion,
            response_style=response_style,
            empathy_statement=empathy_statement,
            adjustment=adjustment,
            tone=tone,
        )

    def _generate_adjustment(self, state: EmotionState,
                              interpretation: dict) -> str:
        """生成交互调整建议"""
        if state.emotion == EmotionType.FRUSTRATED:
            return "简化解释，提供更多示例，分步骤指导"
        elif state.emotion == EmotionType.ANGRY:
            return "表达理解，避免辩解，提供解决方案"
        elif state.emotion == EmotionType.ANXIOUS:
            return "提供明确的时间线，分解任务，给予肯定"
        elif state.emotion == EmotionType.CONFUSED:
            return "使用更简单的语言，提供图示，检查理解"
        elif state.emotion == EmotionType.DISAPPOINTED:
            return "承认不足，提供替代方案，表达改进意愿"
        else:
            return "保持当前交互方式"

    def _generate_tone(self, state: EmotionState) -> str:
        """生成语气建议"""
        if state.intensity == EmotionIntensity.HIGH:
            if state.emotion in [EmotionType.ANGRY, EmotionType.FRUSTRATED]:
                return "温和、耐心、理解"
            elif state.emotion == EmotionType.ANXIOUS:
                return "冷静、稳定、可靠"
        elif state.emotion == EmotionType.HAPPY:
            return "热情、友好、积极"
        elif state.emotion == EmotionType.CONFUSED:
            return "清晰、耐心、鼓励"

        return "专业、友好、适中"


# ============================================================================
# 情绪记忆器
# ============================================================================

class EmotionMemory:
    """情绪记忆器"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "emotion_memory.json"
        self.user_patterns: dict[str, EmotionPattern] = {}
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for user_id, pattern_data in data.items():
                    self.user_patterns[user_id] = EmotionPattern(**pattern_data)

    def _save(self):
        """保存数据"""
        data = {}
        for user_id, pattern in self.user_patterns.items():
            d = asdict(pattern)
            # 处理枚举类型
            for k, v in d.items():
                if hasattr(v, 'value'):
                    d[k] = v.value
            data[user_id] = d

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_interaction(self, user_id: str, emotion_state: EmotionState):
        """记录用户情绪交互"""
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = EmotionPattern(user_id=user_id)

        pattern = self.user_patterns[user_id]
        pattern.interaction_count += 1
        pattern.last_interaction = time.time()

        # 更新常见情绪
        emotion_key = emotion_state.emotion.value
        if emotion_key not in pattern.frequent_emotions:
            pattern.frequent_emotions[emotion_key] = 0
        pattern.frequent_emotions[emotion_key] += 1

        # 更新触发因素
        for trigger in emotion_state.triggers:
            if trigger not in pattern.triggers:
                pattern.triggers[trigger] = 0
            pattern.triggers[trigger] += 1

        # 更新偏好响应风格
        if emotion_state.emotion in [EmotionType.ANGRY, EmotionType.FRUSTRATED]:
            pattern.preferred_response_style = ResponseStyle.EMPATHETIC
        elif emotion_state.emotion == EmotionType.ANXIOUS:
            pattern.preferred_response_style = ResponseStyle.CALM

        self._save()

    def get_user_pattern(self, user_id: str) -> Optional[EmotionPattern]:
        """获取用户情绪模式"""
        return self.user_patterns.get(user_id)

    def get_dominant_emotion(self, user_id: str) -> Optional[EmotionType]:
        """获取用户主导情绪"""
        pattern = self.user_patterns.get(user_id)
        if not pattern or not pattern.frequent_emotions:
            return None

        dominant = max(pattern.frequent_emotions.keys(),
                      key=lambda e: pattern.frequent_emotions[e])
        return EmotionType(dominant)


# ============================================================================
# 情感智能引擎
# ============================================================================

class EmotionalIntelligenceEngine:
    """
    情感智能引擎 - 整合所有组件

    核心功能：
    1. 识别用户情绪
    2. 理解情绪原因
    3. 生成合适的响应
    4. 记忆情绪模式
    5. 预测情绪变化
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "emotional_intelligence"
        os.makedirs(storage_dir, exist_ok=True)

        self.recognizer = EmotionRecognizer()
        self.interpreter = EmotionInterpreter()
        self.responder = EmotionResponder()
        self.memory = EmotionMemory(
            os.path.join(storage_dir, "emotion_memory.json")
        )

    def process(self, text: str, user_id: str = "default",
                context: dict = None) -> dict:
        """处理用户输入的情感"""
        # 1. 识别情绪
        emotion_state = self.recognizer.recognize_from_context(text, context or {})

        # 2. 理解情绪
        interpretation = self.interpreter.interpret(emotion_state, context)

        # 3. 生成响应
        response = self.responder.generate_response(emotion_state, interpretation)

        # 4. 记录情绪
        self.memory.record_interaction(user_id, emotion_state)

        return {
            'emotion': emotion_state.emotion.value,
            'intensity': emotion_state.intensity.value,
            'confidence': emotion_state.confidence,
            'interpretation': interpretation,
            'response': asdict(response),
            'user_pattern': asdict(self.memory.get_user_pattern(user_id))
                          if self.memory.get_user_pattern(user_id) else None,
        }

    def get_empathetic_prefix(self, text: str, user_id: str = "default") -> str:
        """获取共情前缀"""
        result = self.process(text, user_id)
        response = result['response']

        if result['emotion'] != 'neutral':
            return response['empathy_statement']
        return ""

    def should_adjust_style(self, user_id: str) -> Optional[ResponseStyle]:
        """判断是否需要调整交互风格"""
        pattern = self.memory.get_user_pattern(user_id)
        if not pattern:
            return None

        # 如果用户经常有负面情绪，建议调整风格
        negative_emotions = ['angry', 'frustrated', 'disappointed', 'anxious']
        negative_count = sum(
            pattern.frequent_emotions.get(e, 0) for e in negative_emotions
        )

        if negative_count > pattern.interaction_count * 0.3:  # 超过30%是负面
            return ResponseStyle.EMPATHETIC

        return None

    def generate_report(self, user_id: str = "default") -> str:
        """生成情感分析报告"""
        pattern = self.memory.get_user_pattern(user_id)

        report = []
        report.append("=" * 50)
        report.append("💝 情感智能报告")
        report.append("=" * 50)

        if pattern:
            report.append(f"\n用户ID: {user_id}")
            report.append(f"交互次数: {pattern.interaction_count}")

            if pattern.frequent_emotions:
                report.append("\n常见情绪:")
                sorted_emotions = sorted(
                    pattern.frequent_emotions.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for emotion, count in sorted_emotions[:5]:
                    percentage = count / pattern.interaction_count * 100
                    report.append(f"  - {emotion}: {count}次 ({percentage:.0f}%)")

            if pattern.triggers:
                report.append("\n常见触发因素:")
                sorted_triggers = sorted(
                    pattern.triggers.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                for trigger, count in sorted_triggers[:5]:
                    report.append(f"  - {trigger}: {count}次")

            style = pattern.preferred_response_style
            style_val = style.value if hasattr(style, 'value') else str(style)
            report.append(f"\n偏好响应风格: {style_val}")
        else:
            report.append("\n暂无用户情感数据")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = EmotionalIntelligenceEngine("test_emotional_intelligence")

    # 测试文本
    test_texts = [
        "这个代码太难了，我搞不定！",
        "太棒了，终于成功了！",
        "你能快点吗？我赶时间。",
        "这是什么意思？我不太懂。",
        "谢谢你的帮助！",
    ]

    print("=== 情感分析 ===")
    for text in test_texts:
        result = engine.process(text, user_id="test_user")
        print(f"\n输入: {text}")
        print(f"情绪: {result['emotion']} (强度: {result['intensity']}, 置信度: {result['confidence']:.2f})")
        print(f"共情: {result['response']['empathy_statement']}")
        print(f"调整: {result['response']['adjustment']}")

    # 报告
    print("\n" + engine.generate_report("test_user"))
