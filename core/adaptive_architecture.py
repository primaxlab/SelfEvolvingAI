"""
================================================================================
自适应架构系统 (Adaptive Architecture System)
================================================================================

核心能力：
  1. 架构监控 - 监控系统架构状态
  2. 瓶颈识别 - 识别系统瓶颈
  3. 动态调整 - 动态调整架构
  4. 资源优化 - 优化资源分配
  5. 弹性伸缩 - 根据负载自动伸缩

设计原则：
  - 自适应：根据负载自动调整
  - 高效性：最大化资源利用
  - 可观测：架构状态可监控
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

class ComponentType(Enum):
    PROCESSOR = "processor"      # 处理器
    STORAGE = "storage"          # 存储
    NETWORK = "network"          # 网络
    CACHE = "cache"              # 缓存
    QUEUE = "queue"              # 队列

class ScalingAction(Enum):
    SCALE_UP = "scale_up"        # 扩容
    SCALE_DOWN = "scale_down"    # 缩容
    REBALANCE = "rebalance"      # 重新平衡
    OPTIMIZE = "optimize"        # 优化

@dataclass
class Component:
    """架构组件"""
    id: str
    name: str
    component_type: ComponentType
    capacity: float              # 容量
    current_load: float = 0.0   # 当前负载
    instances: int = 1           # 实例数
    health: float = 1.0         # 健康度 0-1
    metadata: dict = field(default_factory=dict)

@dataclass
class ArchitectureState:
    """架构状态"""
    components: dict             # 组件状态
    overall_health: float        # 整体健康度
    bottlenecks: list            # 瓶颈列表
    recommendations: list        # 优化建议
    timestamp: float = field(default_factory=time.time)

@dataclass
class ScalingDecision:
    """伸缩决策"""
    component_id: str
    action: ScalingAction
    current_instances: int
    target_instances: int
    reason: str
    confidence: float


# ============================================================================
# 架构监控器
# ============================================================================

class ArchitectureMonitor:
    """架构监控器"""

    def __init__(self):
        self.components: dict[str, Component] = {}
        self.metrics_history: dict[str, list] = {}

    def register_component(self, component: Component):
        """注册组件"""
        self.components[component.id] = component
        self.metrics_history[component.id] = []

    def update_metrics(self, component_id: str, metrics: dict):
        """更新指标"""
        if component_id not in self.components:
            return

        component = self.components[component_id]
        component.current_load = metrics.get('load', component.current_load)
        component.health = metrics.get('health', component.health)

        # 记录历史
        self.metrics_history[component_id].append({
            'load': component.current_load,
            'health': component.health,
            'timestamp': time.time(),
        })

        # 保持最近100条
        if len(self.metrics_history[component_id]) > 100:
            self.metrics_history[component_id] = self.metrics_history[component_id][-100:]

    def get_state(self) -> ArchitectureState:
        """获取架构状态"""
        bottlenecks = self._identify_bottlenecks()
        recommendations = self._generate_recommendations(bottlenecks)

        # 计算整体健康度
        if self.components:
            overall_health = sum(c.health for c in self.components.values()) / len(self.components)
        else:
            overall_health = 1.0

        return ArchitectureState(
            components={cid: asdict(c) for cid, c in self.components.items()},
            overall_health=overall_health,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

    def _identify_bottlenecks(self) -> list:
        """识别瓶颈"""
        bottlenecks = []

        for component in self.components.values():
            # 负载过高
            if component.current_load > component.capacity * 0.9:
                bottlenecks.append({
                    'component': component.id,
                    'type': 'high_load',
                    'severity': component.current_load / component.capacity,
                    'description': f"{component.name} 负载过高 ({component.current_load:.1%})",
                })

            # 健康度低
            if component.health < 0.7:
                bottlenecks.append({
                    'component': component.id,
                    'type': 'low_health',
                    'severity': 1.0 - component.health,
                    'description': f"{component.name} 健康度低 ({component.health:.1%})",
                })

        return bottlenecks

    def _generate_recommendations(self, bottlenecks: list) -> list:
        """生成优化建议"""
        recommendations = []

        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'high_load':
                recommendations.append({
                    'component': bottleneck['component'],
                    'action': 'scale_up',
                    'reason': bottleneck['description'],
                    'priority': 'high',
                })
            elif bottleneck['type'] == 'low_health':
                recommendations.append({
                    'component': bottleneck['component'],
                    'action': 'health_check',
                    'reason': bottleneck['description'],
                    'priority': 'medium',
                })

        return recommendations


# ============================================================================
# 瓶颈分析器
# ============================================================================

class BottleneckAnalyzer:
    """瓶颈分析器"""

    def analyze(self, state: ArchitectureState) -> dict:
        """分析瓶颈"""
        bottlenecks = state.bottlenecks

        if not bottlenecks:
            return {
                'has_bottleneck': False,
                'bottlenecks': [],
                'severity': 'none',
            }

        # 计算严重程度
        max_severity = max(b['severity'] for b in bottlenecks)

        if max_severity > 0.9:
            severity = 'critical'
        elif max_severity > 0.7:
            severity = 'high'
        elif max_severity > 0.5:
            severity = 'medium'
        else:
            severity = 'low'

        return {
            'has_bottleneck': True,
            'bottlenecks': bottlenecks,
            'severity': severity,
            'count': len(bottlenecks),
        }


# ============================================================================
# 动态调整器
# ============================================================================

class DynamicAdjuster:
    """动态调整器"""

    def __init__(self):
        self.adjustment_history: list[dict] = []

    def generate_scaling_decisions(self, state: ArchitectureState,
                                     analysis: dict) -> list:
        """生成伸缩决策"""
        decisions = []

        if not analysis['has_bottleneck']:
            return decisions

        for bottleneck in analysis['bottlenecks']:
            component_id = bottleneck['component']
            component = state.components.get(component_id)

            if not component:
                continue

            if bottleneck['type'] == 'high_load':
                # 扩容决策
                current_instances = component.get('instances', 1)
                target = min(current_instances * 2, 10)  # 最多10个实例

                decisions.append(ScalingDecision(
                    component_id=component_id,
                    action=ScalingAction.SCALE_UP,
                    current_instances=current_instances,
                    target_instances=target,
                    reason=bottleneck['description'],
                    confidence=0.8,
                ))

            elif bottleneck['type'] == 'low_health':
                # 重新平衡决策
                decisions.append(ScalingDecision(
                    component_id=component_id,
                    action=ScalingAction.REBALANCE,
                    current_instances=component.get('instances', 1),
                    target_instances=component.get('instances', 1),
                    reason=bottleneck['description'],
                    confidence=0.7,
                ))

        return decisions

    def apply_decision(self, decision: ScalingDecision,
                        components: dict) -> bool:
        """应用决策"""
        if decision.component_id not in components:
            return False

        component = components[decision.component_id]

        if decision.action == ScalingAction.SCALE_UP:
            component['instances'] = decision.target_instances
        elif decision.action == ScalingAction.SCALE_DOWN:
            component['instances'] = max(1, decision.target_instances)
        elif decision.action == ScalingAction.REBALANCE:
            # 重新平衡逻辑
            pass

        # 记录调整
        self.adjustment_history.append({
            'component': decision.component_id,
            'action': decision.action.value,
            'from': decision.current_instances,
            'to': decision.target_instances,
            'timestamp': time.time(),
        })

        return True


# ============================================================================
# 自适应架构引擎
# ============================================================================

class AdaptiveArchitectureEngine:
    """
    自适应架构引擎 - 整合所有组件

    核心功能：
    1. 监控架构状态
    2. 识别瓶颈
    3. 生成调整决策
    4. 自动优化架构
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "adaptive_architecture"
        os.makedirs(storage_dir, exist_ok=True)

        self.monitor = ArchitectureMonitor()
        self.analyzer = BottleneckAnalyzer()
        self.adjuster = DynamicAdjuster()

        self.optimization_history: list[dict] = []

    def register_component(self, component_id: str, name: str,
                            component_type: ComponentType,
                            capacity: float) -> Component:
        """注册组件"""
        component = Component(
            id=component_id,
            name=name,
            component_type=component_type,
            capacity=capacity,
        )
        self.monitor.register_component(component)
        return component

    def update_component(self, component_id: str, metrics: dict):
        """更新组件指标"""
        self.monitor.update_metrics(component_id, metrics)

    def analyze_and_optimize(self) -> dict:
        """分析并优化"""
        # 1. 获取架构状态
        state = self.monitor.get_state()

        # 2. 分析瓶颈
        analysis = self.analyzer.analyze(state)

        # 3. 生成决策
        decisions = self.adjuster.generate_scaling_decisions(state, analysis)

        # 4. 应用决策
        applied = []
        for decision in decisions:
            success = self.adjuster.apply_decision(
                decision, state.components
            )
            if success:
                applied.append(asdict(decision))

        # 记录优化历史
        self.optimization_history.append({
            'bottlenecks': len(analysis['bottlenecks']),
            'decisions': len(decisions),
            'applied': len(applied),
            'timestamp': time.time(),
        })

        return {
            'state': asdict(state),
            'analysis': analysis,
            'decisions': [asdict(d) for d in decisions],
            'applied': applied,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'components': len(self.monitor.components),
            'optimizations': len(self.optimization_history),
            'adjustments': len(self.adjuster.adjustment_history),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()
        state = self.monitor.get_state()

        report = []
        report.append("=" * 50)
        report.append("🏗️ 自适应架构报告")
        report.append("=" * 50)
        report.append(f"\n组件数量: {stats['components']}")
        report.append(f"整体健康: {state.overall_health:.1%}")
        report.append(f"瓶颈数量: {len(state.bottlenecks)}")
        report.append(f"优化次数: {stats['optimizations']}")
        report.append(f"调整次数: {stats['adjustments']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = AdaptiveArchitectureEngine("test_adaptive_architecture")

    # 注册组件
    print("=== 注册组件 ===")
    components = [
        ("api_gateway", "API网关", ComponentType.NETWORK, 1000),
        ("processor", "处理器", ComponentType.PROCESSOR, 500),
        ("database", "数据库", ComponentType.STORAGE, 200),
        ("cache", "缓存", ComponentType.CACHE, 800),
    ]

    for comp_id, name, comp_type, capacity in components:
        engine.register_component(comp_id, name, comp_type, capacity)
        print(f"注册: {name}")

    # 模拟负载
    print("\n=== 模拟负载 ===")
    engine.update_component("api_gateway", {'load': 950, 'health': 0.9})
    engine.update_component("processor", {'load': 480, 'health': 0.6})
    engine.update_component("database", {'load': 180, 'health': 0.95})
    engine.update_component("cache", {'load': 400, 'health': 0.99})

    # 分析优化
    print("\n=== 分析优化 ===")
    result = engine.analyze_and_optimize()
    print(f"瓶颈: {result['analysis']['severity']}")
    print(f"决策: {len(result['decisions'])}")
    print(f"应用: {len(result['applied'])}")

    # 报告
    print("\n" + engine.generate_report())