"""
================================================================================
分布式协作系统 (Distributed Collaboration System)
================================================================================

核心能力：
  1. 实例发现 - 发现其他AI实例
  2. 任务分发 - 将任务分发给合适的实例
  3. 结果聚合 - 聚合多个实例的结果
  4. 负载均衡 - 平衡各实例的负载
  5. 一致性维护 - 维护分布式状态一致性

设计原则：
  - 去中心化：无单点故障
  - 可扩展：支持动态添加实例
  - 容错性：部分实例故障不影响整体
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

class InstanceStatus(Enum):
    ONLINE = "online"            # 在线
    OFFLINE = "offline"          # 离线
    BUSY = "busy"                # 忙碌
    MAINTENANCE = "maintenance"  # 维护中

class TaskStatus(Enum):
    PENDING = "pending"          # 待处理
    ASSIGNED = "assigned"        # 已分配
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败

@dataclass
class Instance:
    """AI实例"""
    id: str
    name: str
    status: InstanceStatus
    capabilities: list           # 能力列表
    load: float = 0.0           # 当前负载 0-1
    max_load: float = 1.0       # 最大负载
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

@dataclass
class DistributedTask:
    """分布式任务"""
    id: str
    description: str
    requirements: list           # 能力要求
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str = ""
    result: Any = None
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    priority: int = 0

@dataclass
class AggregatedResult:
    """聚合结果"""
    task_id: str
    results: list                # 各实例结果
    aggregated: Any              # 聚合后结果
    confidence: float
    instances_used: list


# ============================================================================
# 实例管理器
# ============================================================================

class InstanceManager:
    """实例管理器"""

    def __init__(self):
        self.instances: dict[str, Instance] = {}
        self.heartbeat_timeout = 60  # 心跳超时时间(秒)

    def register_instance(self, instance: Instance):
        """注册实例"""
        self.instances[instance.id] = instance

    def unregister_instance(self, instance_id: str):
        """注销实例"""
        if instance_id in self.instances:
            del self.instances[instance_id]

    def update_heartbeat(self, instance_id: str):
        """更新心跳"""
        if instance_id in self.instances:
            self.instances[instance_id].last_heartbeat = time.time()

    def get_available_instances(self) -> list:
        """获取可用实例"""
        now = time.time()
        available = []

        for instance in self.instances.values():
            # 检查心跳
            if now - instance.last_heartbeat > self.heartbeat_timeout:
                instance.status = InstanceStatus.OFFLINE
                continue

            # 检查状态和负载
            if (instance.status == InstanceStatus.ONLINE and
                instance.load < instance.max_load):
                available.append(instance)

        return available

    def find_capable_instances(self, requirements: list) -> list:
        """查找有能力的实例"""
        available = self.get_available_instances()
        capable = []

        for instance in available:
            # 检查能力匹配
            if all(req in instance.capabilities for req in requirements):
                capable.append(instance)

        return capable

    def update_load(self, instance_id: str, load: float):
        """更新负载"""
        if instance_id in self.instances:
            self.instances[instance_id].load = load

    def get_instance_stats(self) -> dict:
        """获取实例统计"""
        total = len(self.instances)
        online = sum(1 for i in self.instances.values()
                    if i.status == InstanceStatus.ONLINE)

        return {
            'total_instances': total,
            'online_instances': online,
            'avg_load': sum(i.load for i in self.instances.values()) / max(1, total),
        }


# ============================================================================
# 任务分发器
# ============================================================================

class TaskDistributor:
    """任务分发器"""

    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager
        self.task_queue: list[DistributedTask] = []
        self.completed_tasks: list[DistributedTask] = []

    def submit_task(self, task: DistributedTask):
        """提交任务"""
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)

    def distribute_next(self) -> Optional[dict]:
        """分发下一个任务"""
        if not self.task_queue:
            return None

        task = self.task_queue[0]

        # 查找有能力的实例
        capable_instances = self.instance_manager.find_capable_instances(
            task.requirements
        )

        if not capable_instances:
            return {'error': '没有可用的实例'}

        # 选择负载最低的实例
        selected = min(capable_instances, key=lambda i: i.load)

        # 分配任务
        task.status = TaskStatus.ASSIGNED
        task.assigned_to = selected.id

        # 更新实例负载
        selected.load += 0.1  # 简化负载计算

        # 移动到已完成队列
        self.task_queue.pop(0)
        self.completed_tasks.append(task)

        return {
            'task_id': task.id,
            'assigned_to': selected.id,
            'instance_name': selected.name,
        }

    def complete_task(self, task_id: str, result: Any) -> bool:
        """完成任务"""
        for task in self.completed_tasks:
            if task.id == task_id:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = time.time()
                return True
        return False

    def get_queue_stats(self) -> dict:
        """获取队列统计"""
        return {
            'pending': len(self.task_queue),
            'completed': len(self.completed_tasks),
            'total': len(self.task_queue) + len(self.completed_tasks),
        }


# ============================================================================
# 结果聚合器
# ============================================================================

class ResultAggregator:
    """结果聚合器"""

    def aggregate(self, results: list,
                   strategy: str = "majority") -> AggregatedResult:
        """聚合结果"""
        if not results:
            return AggregatedResult(
                task_id="",
                results=[],
                aggregated=None,
                confidence=0,
                instances_used=[],
            )

        if strategy == "majority":
            return self._majority_vote(results)
        elif strategy == "average":
            return self._average(results)
        elif strategy == "best":
            return self._select_best(results)
        else:
            return self._majority_vote(results)

    def _majority_vote(self, results: list) -> AggregatedResult:
        """多数投票"""
        # 统计结果出现次数
        result_counts = {}
        for r in results:
            key = str(r.get('result', ''))
            result_counts[key] = result_counts.get(key, 0) + 1

        # 找出最多的结果
        if result_counts:
            majority = max(result_counts, key=result_counts.get)
            confidence = result_counts[majority] / len(results)
        else:
            majority = None
            confidence = 0

        return AggregatedResult(
            task_id=results[0].get('task_id', ''),
            results=results,
            aggregated=majority,
            confidence=confidence,
            instances_used=[r.get('instance_id', '') for r in results],
        )

    def _average(self, results: list) -> AggregatedResult:
        """平均值"""
        numeric_results = []
        for r in results:
            try:
                numeric_results.append(float(r.get('result', 0)))
            except (ValueError, TypeError):
                continue

        if numeric_results:
            avg = sum(numeric_results) / len(numeric_results)
            confidence = 0.8
        else:
            avg = None
            confidence = 0

        return AggregatedResult(
            task_id=results[0].get('task_id', ''),
            results=results,
            aggregated=avg,
            confidence=confidence,
            instances_used=[r.get('instance_id', '') for r in results],
        )

    def _select_best(self, results: list) -> AggregatedResult:
        """选择最佳"""
        # 选择置信度最高的
        best = max(results, key=lambda r: r.get('confidence', 0))

        return AggregatedResult(
            task_id=best.get('task_id', ''),
            results=results,
            aggregated=best.get('result'),
            confidence=best.get('confidence', 0),
            instances_used=[best.get('instance_id', '')],
        )


# ============================================================================
# 负载均衡器
# ============================================================================

class LoadBalancer:
    """负载均衡器"""

    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager

    def select_instance(self, requirements: list = None,
                         strategy: str = "least_loaded") -> Optional[Instance]:
        """选择实例"""
        if requirements:
            candidates = self.instance_manager.find_capable_instances(requirements)
        else:
            candidates = self.instance_manager.get_available_instances()

        if not candidates:
            return None

        if strategy == "least_loaded":
            return min(candidates, key=lambda i: i.load)
        elif strategy == "random":
            return random.choice(candidates)
        elif strategy == "round_robin":
            # 简化实现
            return candidates[0]
        else:
            return min(candidates, key=lambda i: i.load)

    def rebalance(self) -> list:
        """重新平衡负载"""
        instances = self.instance_manager.get_available_instances()
        if len(instances) < 2:
            return []

        # 计算平均负载
        avg_load = sum(i.load for i in instances) / len(instances)

        # 找出过载和空闲的实例
        overloaded = [i for i in instances if i.load > avg_load * 1.5]
        underloaded = [i for i in instances if i.load < avg_load * 0.5]

        return [
            {'action': 'redistribute', 'from': o.id, 'to': u.id}
            for o, u in zip(overloaded, underloaded)
        ]


# ============================================================================
# 分布式协作引擎
# ============================================================================

class DistributedCollaborationEngine:
    """
    分布式协作引擎 - 整合所有组件

    核心功能：
    1. 管理多个AI实例
    2. 分发和调度任务
    3. 聚合结果
    4. 负载均衡
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "distributed"
        os.makedirs(storage_dir, exist_ok=True)

        self.instance_manager = InstanceManager()
        self.task_distributor = TaskDistributor(self.instance_manager)
        self.result_aggregator = ResultAggregator()
        self.load_balancer = LoadBalancer(self.instance_manager)

        self.collaboration_history: list[dict] = []

    def register_instance(self, instance_id: str, name: str,
                           capabilities: list) -> Instance:
        """注册实例"""
        instance = Instance(
            id=instance_id,
            name=name,
            status=InstanceStatus.ONLINE,
            capabilities=capabilities,
        )
        self.instance_manager.register_instance(instance)
        return instance

    def submit_task(self, description: str, requirements: list,
                     priority: int = 0) -> DistributedTask:
        """提交任务"""
        task_id = hashlib.md5(f"{description}{time.time()}".encode()).hexdigest()[:12]
        task = DistributedTask(
            id=task_id,
            description=description,
            requirements=requirements,
            priority=priority,
        )
        self.task_distributor.submit_task(task)
        return task

    def process_tasks(self) -> list:
        """处理任务队列"""
        results = []

        while self.task_distributor.task_queue:
            result = self.task_distributor.distribute_next()
            if result:
                results.append(result)
            else:
                break

        return results

    def aggregate_results(self, task_id: str,
                           results: list,
                           strategy: str = "majority") -> dict:
        """聚合结果"""
        aggregated = self.result_aggregator.aggregate(results, strategy)

        # 记录协作历史
        self.collaboration_history.append({
            'task_id': task_id,
            'instances': aggregated.instances_used,
            'confidence': aggregated.confidence,
            'timestamp': time.time(),
        })

        return asdict(aggregated)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'instances': self.instance_manager.get_instance_stats(),
            'tasks': self.task_distributor.get_queue_stats(),
            'collaborations': len(self.collaboration_history),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🌐 分布式协作报告")
        report.append("=" * 50)
        report.append(f"\n总实例数: {stats['instances']['total_instances']}")
        report.append(f"在线实例: {stats['instances']['online_instances']}")
        report.append(f"平均负载: {stats['instances']['avg_load']:.2f}")
        report.append(f"待处理任务: {stats['tasks']['pending']}")
        report.append(f"已完成任务: {stats['tasks']['completed']}")
        report.append(f"协作次数: {stats['collaborations']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = DistributedCollaborationEngine("test_distributed")

    # 注册实例
    print("=== 注册实例 ===")
    instances = [
        ("instance_1", "AI Worker 1", ["text_processing", "analysis"]),
        ("instance_2", "AI Worker 2", ["code_generation", "analysis"]),
        ("instance_3", "AI Worker 3", ["text_processing", "code_generation"]),
    ]

    for instance_id, name, capabilities in instances:
        engine.register_instance(instance_id, name, capabilities)
        print(f"注册: {name}")

    # 提交任务
    print("\n=== 提交任务 ===")
    tasks = [
        ("分析代码质量", ["analysis"], 1),
        ("生成报告", ["text_processing"], 0),
        ("优化算法", ["code_generation", "analysis"], 2),
    ]

    for desc, reqs, priority in tasks:
        task = engine.submit_task(desc, reqs, priority)
        print(f"提交: {desc} (ID: {task.id})")

    # 处理任务
    print("\n=== 处理任务 ===")
    results = engine.process_tasks()
    for r in results:
        print(f"分配: 任务 {r.get('task_id')} -> {r.get('instance_name')}")

    # 报告
    print("\n" + engine.generate_report())