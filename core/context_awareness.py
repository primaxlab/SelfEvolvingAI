"""
================================================================================
情境感知系统 (Context Awareness System)
================================================================================

核心能力：
  1. 时间感知 - 感知时间、日期、时段
  2. 空间感知 - 感知位置、环境
  3. 用户状态感知 - 感知用户当前状态
  4. 任务上下文 - 理解当前任务背景
  5. 历史上下文 - 考虑历史交互

设计原则：
  - 全面感知：多维度感知环境
  - 动态更新：实时更新情境信息
  - 智能适配：根据情境调整行为
"""

import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class TimeOfDay(Enum):
    EARLY_MORNING = "early_morning"  # 凌晨 0-5
    MORNING = "morning"              # 上午 6-11
    NOON = "noon"                    # 中午 12-13
    AFTERNOON = "afternoon"          # 下午 14-17
    EVENING = "evening"              # 晚上 18-21
    NIGHT = "night"                  # 深夜 22-23

class UserState(Enum):
    FOCUSED = "focused"              # 专注
    RELAXED = "relaxed"              # 放松
    BUSY = "busy"                    # 忙碌
    TIRED = "tired"                  # 疲惫
    EXCITED = "excited"              # 兴奋
    FRUSTRATED = "frustrated"        # 沮丧

class TaskContext(Enum):
    LEARNING = "learning"            # 学习
    WORKING = "working"              # 工作
    EXPLORING = "exploring"          # 探索
    PROBLEM_SOLVING = "problem_solving"  # 解决问题
    CASUAL = "casual"                # 随意聊天

@dataclass
class TimeContext:
    """时间上下文"""
    timestamp: float
    time_of_day: TimeOfDay
    is_weekday: bool
    hour: int
    minute: int

@dataclass
class UserContext:
    """用户上下文"""
    user_id: str
    state: UserState
    recent_topics: list
    expertise_level: float
    preferences: dict

@dataclass
class TaskInfo:
    """任务信息"""
    task_type: TaskContext
    complexity: float
    urgency: float
    domain: str

@dataclass
class Situation:
    """完整情境"""
    time_context: TimeContext
    user_context: Optional[UserContext]
    task_info: Optional[TaskInfo]
    environment: dict


# ============================================================================
# 时间感知器
# ============================================================================

class TimePerceiver:
    """时间感知器"""

    def perceive(self) -> TimeContext:
        """感知当前时间"""
        now = datetime.now()

        # 确定时段
        hour = now.hour
        if 0 <= hour < 6:
            time_of_day = TimeOfDay.EARLY_MORNING
        elif 6 <= hour < 12:
            time_of_day = TimeOfDay.MORNING
        elif 12 <= hour < 14:
            time_of_day = TimeOfDay.NOON
        elif 14 <= hour < 18:
            time_of_day = TimeOfDay.AFTERNOON
        elif 18 <= hour < 22:
            time_of_day = TimeOfDay.EVENING
        else:
            time_of_day = TimeOfDay.NIGHT

        return TimeContext(
            timestamp=time.time(),
            time_of_day=time_of_day,
            is_weekday=now.weekday() < 5,
            hour=hour,
            minute=now.minute,
        )

    def get_time_description(self, context: TimeContext) -> str:
        """获取时间描述"""
        descriptions = {
            TimeOfDay.EARLY_MORNING: "凌晨",
            TimeOfDay.MORNING: "上午",
            TimeOfDay.NOON: "中午",
            TimeOfDay.AFTERNOON: "下午",
            TimeOfDay.EVENING: "晚上",
            TimeOfDay.NIGHT: "深夜",
        }

        desc = descriptions.get(context.time_of_day, "")
        if context.is_weekday:
            desc += " 工作日"
        else:
            desc += " 周末"

        return desc


# ============================================================================
# 用户状态感知器
# ============================================================================

class UserStatePerceiver:
    """用户状态感知器"""

    def __init__(self):
        self.user_history: dict[str, list] = {}

    def perceive(self, user_id: str,
                  interaction_data: dict = None) -> UserContext:
        """感知用户状态"""
        # 分析交互数据推断状态
        state = self._infer_state(interaction_data or {})

        # 获取最近话题
        recent_topics = self._get_recent_topics(user_id)

        # 获取专业水平
        expertise = self._estimate_expertise(user_id)

        return UserContext(
            user_id=user_id,
            state=state,
            recent_topics=recent_topics,
            expertise_level=expertise,
            preferences={},
        )

    def _infer_state(self, data: dict) -> UserState:
        """推断用户状态"""
        # 基于输入速度
        typing_speed = data.get('typing_speed', 0)
        if typing_speed > 100:  # 快速输入
            return UserState.FOCUSED
        elif typing_speed < 30:  # 慢速输入
            return UserState.TIRED

        # 基于交互频率
        interaction_frequency = data.get('interaction_frequency', 0)
        if interaction_frequency > 10:  # 高频交互
            return UserState.BUSY

        return UserState.RELAXED

    def _get_recent_topics(self, user_id: str) -> list:
        """获取最近话题"""
        history = self.user_history.get(user_id, [])
        return history[-5:] if history else []

    def _estimate_expertise(self, user_id: str) -> float:
        """估计专业水平"""
        # 简化实现
        return 0.5

    def update_history(self, user_id: str, topic: str):
        """更新用户历史"""
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id].append(topic)
        # 只保留最近20个
        self.user_history[user_id] = self.user_history[user_id][-20:]


# ============================================================================
# 任务上下文分析器
# ============================================================================

class TaskContextAnalyzer:
    """任务上下文分析器"""

    def analyze(self, task_description: str,
                context: dict = None) -> TaskInfo:
        """分析任务上下文"""
        # 推断任务类型
        task_type = self._infer_task_type(task_description)

        # 估计复杂度
        complexity = self._estimate_complexity(task_description)

        # 估计紧急度
        urgency = self._estimate_urgency(task_description, context or {})

        # 推断领域
        domain = self._infer_domain(task_description)

        return TaskInfo(
            task_type=task_type,
            complexity=complexity,
            urgency=urgency,
            domain=domain,
        )

    def _infer_task_type(self, description: str) -> TaskContext:
        """推断任务类型"""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ['学习', '教程', '了解', 'learn']):
            return TaskContext.LEARNING
        elif any(kw in desc_lower for kw in ['工作', '项目', '任务', 'work']):
            return TaskContext.WORKING
        elif any(kw in desc_lower for kw in ['探索', '研究', '调查', 'explore']):
            return TaskContext.EXPLORING
        elif any(kw in desc_lower for kw in ['问题', '错误', '修复', '解决']):
            return TaskContext.PROBLEM_SOLVING
        else:
            return TaskContext.CASUAL

    def _estimate_complexity(self, description: str) -> float:
        """估计复杂度"""
        # 基于长度
        complexity = min(1.0, len(description) / 200)

        # 关键词调整
        complex_keywords = ['复杂', '系统', '架构', '优化', '多个']
        for keyword in complex_keywords:
            if keyword in description:
                complexity = min(1.0, complexity + 0.1)

        return complexity

    def _estimate_urgency(self, description: str,
                           context: dict) -> float:
        """估计紧急度"""
        urgency = 0.5

        # 紧急关键词
        urgent_keywords = ['紧急', '立即', '马上', '快', 'urgent']
        for keyword in urgent_keywords:
            if keyword in description.lower():
                urgency = min(1.0, urgency + 0.2)

        # 上下文调整
        if context.get('deadline'):
            urgency = min(1.0, urgency + 0.2)

        return urgency

    def _infer_domain(self, description: str) -> str:
        """推断领域"""
        desc_lower = description.lower()

        domain_keywords = {
            'programming': ['python', 'java', '代码', '编程', '程序'],
            'data': ['数据', '分析', '统计', '可视化'],
            'ai': ['机器学习', '深度学习', 'ai', '模型'],
            'web': ['网页', '前端', '后端', 'api'],
            'general': [],
        }

        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return domain

        return 'general'


# ============================================================================
# 情境感知引擎
# ============================================================================

class ContextAwarenessEngine:
    """
    情境感知引擎 - 整合所有组件

    核心功能：
    1. 感知时间、用户状态、任务上下文
    2. 构建完整情境
    3. 根据情境调整行为
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "context"
        os.makedirs(storage_dir, exist_ok=True)

        self.time_perceiver = TimePerceiver()
        self.user_perceiver = UserStatePerceiver()
        self.task_analyzer = TaskContextAnalyzer()

        self.current_situation: Optional[Situation] = None

    def perceive_situation(self, user_id: str = None,
                            task_description: str = None,
                            interaction_data: dict = None) -> Situation:
        """感知完整情境"""
        # 时间感知
        time_ctx = self.time_perceiver.perceive()

        # 用户感知
        user_ctx = None
        if user_id:
            user_ctx = self.user_perceiver.perceive(user_id, interaction_data)

        # 任务感知
        task_info = None
        if task_description:
            task_info = self.task_analyzer.analyze(task_description)

        # 构建情境
        situation = Situation(
            time_context=time_ctx,
            user_context=user_ctx,
            task_info=task_info,
            environment={},
        )

        self.current_situation = situation
        return situation

    def get_adaptation_recommendations(self,
                                         situation: Situation) -> dict:
        """根据情境获取适配建议"""
        recommendations = {
            'tone': 'neutral',
            'verbosity': 'normal',
            'pace': 'normal',
            'suggestions': [],
        }

        # 基于时间调整
        if situation.time_context.time_of_day == TimeOfDay.NIGHT:
            recommendations['tone'] = 'calm'
            recommendations['suggestions'].append('现在是深夜，建议简洁回复')
        elif situation.time_context.time_of_day == TimeOfDay.MORNING:
            recommendations['tone'] = 'energetic'

        # 基于用户状态调整
        if situation.user_context:
            if situation.user_context.state == UserState.TIRED:
                recommendations['verbosity'] = 'concise'
                recommendations['suggestions'].append('用户可能疲惫，建议简洁')
            elif situation.user_context.state == UserState.FOCUSED:
                recommendations['pace'] = 'fast'

        # 基于任务调整
        if situation.task_info:
            if situation.task_info.urgency > 0.8:
                recommendations['pace'] = 'fast'
                recommendations['suggestions'].append('任务紧急，快速响应')
            if situation.task_info.complexity > 0.7:
                recommendations['verbosity'] = 'detailed'

        return recommendations

    def get_situation_summary(self) -> str:
        """获取情境摘要"""
        if not self.current_situation:
            return "未感知到情境"

        s = self.current_situation
        parts = []

        # 时间
        time_desc = self.time_perceiver.get_time_description(s.time_context)
        parts.append(f"时间: {time_desc}")

        # 用户
        if s.user_context:
            parts.append(f"用户状态: {s.user_context.state.value}")

        # 任务
        if s.task_info:
            parts.append(f"任务: {s.task_info.task_type.value} (复杂度: {s.task_info.complexity:.2f})")

        return " | ".join(parts)

    def generate_report(self) -> str:
        """生成报告"""
        report = []
        report.append("=" * 50)
        report.append("🌍 情境感知报告")
        report.append("=" * 50)

        if self.current_situation:
            report.append(f"\n{self.get_situation_summary()}")
        else:
            report.append("\n暂无情境信息")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = ContextAwarenessEngine("test_context")

    # 感知情境
    print("=== 情境感知 ===")
    situation = engine.perceive_situation(
        user_id="test_user",
        task_description="紧急：修复系统bug",
        interaction_data={'typing_speed': 80}
    )

    print(engine.get_situation_summary())

    # 获取适配建议
    recommendations = engine.get_adaptation_recommendations(situation)
    print(f"\n适配建议:")
    print(f"  语气: {recommendations['tone']}")
    print(f"  详细度: {recommendations['verbosity']}")
    print(f"  节奏: {recommendations['pace']}")
    for suggestion in recommendations['suggestions']:
        print(f"  - {suggestion}")

    # 报告
    print("\n" + engine.generate_report())