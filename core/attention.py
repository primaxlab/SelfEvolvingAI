"""
================================================================================
注意力机制系统 (Attention Mechanism System)
================================================================================

核心能力：
  1. 注意力分配 - 动态分配认知资源
  2. 重要性评估 - 评估信息的重要性
  3. 焦点管理 - 管理当前关注点
  4. 干扰过滤 - 过滤无关干扰
  5. 多任务切换 - 高效切换注意力

设计原则：
  - 选择性：只关注重要的信息
  - 适应性：根据任务动态调整
  - 效率性：最大化认知资源利用
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
from collections import OrderedDict


# ============================================================================
# 数据结构
# ============================================================================

class AttentionType(Enum):
    FOCUSED = "focused"           # 聚焦注意力
    DIVIDED = "divided"           # 分配注意力
    SUSTAINED = "sustained"       # 持续注意力
    SELECTIVE = "selective"       # 选择性注意力

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class AttentionFocus:
    """注意力焦点"""
    id: str
    target: str
    priority: Priority
    intensity: float             # 注意力强度 0-1
    duration: float              # 持续时间(秒)
    start_time: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

@dataclass
class InformationItem:
    """信息项"""
    id: str
    content: str
    relevance: float             # 相关性 0-1
    importance: float            # 重要性 0-1
    urgency: float               # 紧急性 0-1
    source: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class AttentionState:
    """注意力状态"""
    current_focus: Optional[AttentionFocus]
    active_foci: list            # 活跃焦点列表
    attention_capacity: float    # 注意力容量 0-1
    fatigue_level: float         # 疲劳程度 0-1
    switch_count: int            # 切换次数


# ============================================================================
# 重要性评估器
# ============================================================================

class ImportanceEvaluator:
    """重要性评估器"""

    def __init__(self):
        # 重要性规则
        self.importance_rules = {
            'keyword_boost': {
                'critical': ['紧急', '错误', '失败', '安全', '重要'],
                'high': ['注意', '问题', '需要', '必须'],
                'medium': ['建议', '可以', '考虑'],
                'low': ['顺便', '其他', '补充'],
            },
            'recency_boost': 0.1,      # 新信息加成
            'repetition_penalty': 0.05, # 重复信息惩罚
        }

    def evaluate(self, item: InformationItem,
                  context: dict = None) -> float:
        """评估信息重要性"""
        score = 0.0

        # 基础分数
        score += item.relevance * 0.3
        score += item.importance * 0.4
        score += item.urgency * 0.3

        # 关键词加成
        content_lower = item.content.lower()
        for level, keywords in self.importance_rules['keyword_boost'].items():
            for keyword in keywords:
                if keyword in content_lower:
                    if level == 'critical':
                        score += 0.3
                    elif level == 'high':
                        score += 0.2
                    elif level == 'medium':
                        score += 0.1
                    break

        # 时间衰减
        age_hours = (time.time() - item.timestamp) / 3600
        time_decay = math.exp(-age_hours / 24)  # 24小时衰减
        score *= time_decay

        return min(1.0, max(0.0, score))


# ============================================================================
# 焦点管理器
# ============================================================================

class FocusManager:
    """焦点管理器"""

    def __init__(self, max_foci: int = 5):
        self.max_foci = max_foci
        self.active_foci: OrderedDict[str, AttentionFocus] = OrderedDict()
        self.focus_history: list[dict] = []

    def add_focus(self, target: str, priority: Priority,
                   intensity: float = 0.5) -> AttentionFocus:
        """添加焦点"""
        # 检查是否已存在
        for focus in self.active_foci.values():
            if focus.target == target:
                # 更新
                focus.intensity = max(focus.intensity, intensity)
                focus.priority = max(focus.priority, priority, key=lambda p: p.value)
                return focus

        # 如果达到上限，移除最低优先级的焦点
        if len(self.active_foci) >= self.max_foci:
            self._remove_lowest_priority()

        # 创建新焦点
        focus_id = hashlib.md5(f"{target}{time.time()}".encode()).hexdigest()[:12]
        focus = AttentionFocus(
            id=focus_id,
            target=target,
            priority=priority,
            intensity=intensity,
            duration=0,
        )

        self.active_foci[focus_id] = focus
        return focus

    def remove_focus(self, focus_id: str):
        """移除焦点"""
        if focus_id in self.active_foci:
            focus = self.active_foci[focus_id]
            focus.duration = time.time() - focus.start_time

            # 记录历史
            self.focus_history.append({
                'target': focus.target,
                'priority': focus.priority.value,
                'duration': focus.duration,
                'timestamp': time.time(),
            })

            del self.active_foci[focus_id]

    def _remove_lowest_priority(self):
        """移除最低优先级的焦点"""
        if not self.active_foci:
            return

        lowest_id = min(
            self.active_foci.keys(),
            key=lambda fid: self.active_foci[fid].priority.value
        )
        self.remove_focus(lowest_id)

    def get_current_focus(self) -> Optional[AttentionFocus]:
        """获取当前焦点"""
        if not self.active_foci:
            return None

        # 返回最高优先级的焦点
        return max(
            self.active_foci.values(),
            key=lambda f: (f.priority.value, f.intensity)
        )

    def switch_focus(self, target: str, priority: Priority) -> dict:
        """切换焦点"""
        old_focus = self.get_current_focus()
        new_focus = self.add_focus(target, priority)

        return {
            'old_focus': old_focus.target if old_focus else None,
            'new_focus': new_focus.target,
            'switch_time': time.time(),
        }

    def get_focus_stats(self) -> dict:
        """获取焦点统计"""
        return {
            'active_foci': len(self.active_foci),
            'total_switches': len(self.focus_history),
            'avg_duration': (
                sum(f['duration'] for f in self.focus_history) /
                max(1, len(self.focus_history))
            ),
        }


# ============================================================================
# 干扰过滤器
# ============================================================================

class DistractionFilter:
    """干扰过滤器"""

    def __init__(self):
        self.noise_patterns = [
            '广告', '通知', '提醒', '更新',
            'advertisement', 'notification', 'alert',
        ]
        self.filtered_count = 0

    def filter(self, items: list,
               current_focus: str = None) -> list:
        """过滤干扰信息"""
        filtered = []

        for item in items:
            # 检查是否是噪声
            if self._is_noise(item):
                self.filtered_count += 1
                continue

            # 检查是否与当前焦点相关
            if current_focus and not self._is_relevant(item, current_focus):
                self.filtered_count += 1
                continue

            filtered.append(item)

        return filtered

    def _is_noise(self, item: InformationItem) -> bool:
        """判断是否是噪声"""
        content_lower = item.content.lower()
        for pattern in self.noise_patterns:
            if pattern in content_lower:
                return True
        return False

    def _is_relevant(self, item: InformationItem,
                      focus: str) -> bool:
        """判断是否与焦点相关"""
        # 简单关键词匹配
        focus_words = set(focus.lower().split())
        item_words = set(item.content.lower().split())

        overlap = len(focus_words & item_words)
        return overlap > 0

    def get_stats(self) -> dict:
        """获取过滤统计"""
        return {
            'filtered_count': self.filtered_count,
        }


# ============================================================================
# 注意力分配器
# ============================================================================

class AttentionAllocator:
    """注意力分配器"""

    def __init__(self, total_capacity: float = 1.0):
        self.total_capacity = total_capacity
        self.allocations: dict[str, float] = {}

    def allocate(self, focus_id: str,
                  priority: Priority,
                  demand: float) -> float:
        """分配注意力"""
        # 计算可用容量
        used = sum(self.allocations.values())
        available = self.total_capacity - used

        # 根据优先级和需求分配
        priority_factor = priority.value / 4.0
        allocated = min(demand * priority_factor, available)

        self.allocations[focus_id] = allocated
        return allocated

    def release(self, focus_id: str):
        """释放注意力"""
        if focus_id in self.allocations:
            del self.allocations[focus_id]

    def get_utilization(self) -> float:
        """获取利用率"""
        used = sum(self.allocations.values())
        return used / self.total_capacity if self.total_capacity > 0 else 0

    def get_allocation(self) -> dict:
        """获取分配情况"""
        return dict(self.allocations)


# ============================================================================
# 注意力引擎
# ============================================================================

class AttentionEngine:
    """
    注意力引擎 - 整合所有组件

    核心功能：
    1. 评估信息重要性
    2. 管理注意力焦点
    3. 过滤干扰
    4. 分配认知资源
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "attention"
        os.makedirs(storage_dir, exist_ok=True)

        self.importance_evaluator = ImportanceEvaluator()
        self.focus_manager = FocusManager()
        self.distraction_filter = DistractionFilter()
        self.attention_allocator = AttentionAllocator()

        self.state = AttentionState(
            current_focus=None,
            active_foci=[],
            attention_capacity=1.0,
            fatigue_level=0.0,
            switch_count=0,
        )

    def process_information(self, items: list,
                             current_task: str = None) -> dict:
        """处理信息流"""
        # 1. 过滤干扰
        filtered_items = self.distraction_filter.filter(items, current_task)

        # 2. 评估重要性
        evaluated_items = []
        for item in filtered_items:
            importance = self.importance_evaluator.evaluate(item)
            evaluated_items.append({
                'item': item,
                'importance': importance,
            })

        # 3. 按重要性排序
        evaluated_items.sort(key=lambda x: x['importance'], reverse=True)

        # 4. 更新焦点
        if evaluated_items:
            top_item = evaluated_items[0]
            if top_item['importance'] > 0.6:
                self.focus_manager.add_focus(
                    top_item['item'].content[:50],
                    Priority.HIGH if top_item['importance'] > 0.8 else Priority.MEDIUM,
                    top_item['importance'],
                )

        return {
            'total_items': len(items),
            'filtered_items': len(filtered_items),
            'top_items': [
                {
                    'content': e['item'].content[:100],
                    'importance': e['importance'],
                }
                for e in evaluated_items[:5]
            ],
            'current_focus': self.focus_manager.get_current_focus(),
        }

    def switch_attention(self, new_target: str,
                          priority: Priority) -> dict:
        """切换注意力"""
        result = self.focus_manager.switch_focus(new_target, priority)
        self.state.switch_count += 1

        # 更新疲劳度
        self.state.fatigue_level = min(1.0, self.state.fatigue_level + 0.05)

        return result

    def get_attention_state(self) -> dict:
        """获取注意力状态"""
        return {
            'current_focus': self.focus_manager.get_current_focus(),
            'active_foci': len(self.focus_manager.active_foci),
            'utilization': self.attention_allocator.get_utilization(),
            'fatigue_level': self.state.fatigue_level,
            'switch_count': self.state.switch_count,
        }

    def generate_report(self) -> str:
        """生成报告"""
        state = self.get_attention_state()
        focus_stats = self.focus_manager.get_focus_stats()

        report = []
        report.append("=" * 50)
        report.append("👁️ 注意力机制报告")
        report.append("=" * 50)
        report.append(f"\n当前焦点: {state['current_focus'].target if state['current_focus'] else '无'}")
        report.append(f"活跃焦点数: {state['active_foci']}")
        report.append(f"注意力利用率: {state['utilization']:.0%}")
        report.append(f"疲劳程度: {state['fatigue_level']:.0%}")
        report.append(f"切换次数: {state['switch_count']}")
        report.append(f"平均焦点时长: {focus_stats['avg_duration']:.1f}秒")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = AttentionEngine("test_attention")

    # 模拟信息处理
    print("=== 信息处理 ===")
    items = [
        InformationItem(id="1", content="紧急：系统出现错误", relevance=0.9, importance=0.9, urgency=0.9),
        InformationItem(id="2", content="通知：新消息", relevance=0.3, importance=0.2, urgency=0.1),
        InformationItem(id="3", content="重要：请立即处理这个任务", relevance=0.8, importance=0.8, urgency=0.8),
        InformationItem(id="4", content="广告：点击查看", relevance=0.1, importance=0.1, urgency=0.0),
    ]

    result = engine.process_information(items, current_task="处理系统问题")
    print(f"总信息: {result['total_items']}")
    print(f"过滤后: {result['filtered_items']}")
    print(f"Top信息:")
    for item in result['top_items']:
        print(f"  - [{item['importance']:.2f}] {item['content']}")

    # 注意力切换
    print("\n=== 注意力切换 ===")
    switch_result = engine.switch_attention("新任务", Priority.HIGH)
    print(f"从 {switch_result['old_focus']} 切换到 {switch_result['new_focus']}")

    # 报告
    print("\n" + engine.generate_report())