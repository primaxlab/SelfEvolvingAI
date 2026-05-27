"""
================================================================================
任务编排系统 (Task Orchestration System)
================================================================================

核心能力：
  1. 任务分解 - 将复杂任务分解为子任务
  2. 依赖管理 - 管理任务间的依赖关系
  3. 并行调度 - 并行执行独立任务
  4. 状态追踪 - 追踪任务执行状态
  5. 错误处理 - 处理任务执行错误

设计原则：
  - DAG编排：有向无环图管理依赖
  - 并行优先：尽可能并行执行
  - 容错性：单个任务失败不影响整体
"""

import json
import os
import time
import hashlib
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict, deque


# ============================================================================
# 数据结构
# ============================================================================

class TaskStatus(Enum):
    PENDING = "pending"          # 待执行
    READY = "ready"              # 就绪
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    SKIPPED = "skipped"          # 跳过

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Task:
    """任务"""
    id: str
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list = field(default_factory=list)  # 依赖的任务ID
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    timeout: float = 300.0       # 超时时间(秒)
    retries: int = 0             # 重试次数
    max_retries: int = 3         # 最大重试次数

@dataclass
class Workflow:
    """工作流"""
    id: str
    name: str
    tasks: dict                  # 任务字典
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

@dataclass
class ExecutionPlan:
    """执行计划"""
    levels: list                 # 执行层级（每层可并行）
    estimated_duration: float
    parallelism: int             # 并行度


# ============================================================================
# 依赖解析器
# ============================================================================

class DependencyResolver:
    """依赖解析器"""

    def __init__(self):
        self.graph: dict[str, list] = defaultdict(list)

    def add_dependency(self, task_id: str, depends_on: str):
        """添加依赖"""
        self.graph[task_id].append(depends_on)

    def resolve(self, tasks: dict) -> list:
        """解析依赖，返回执行层级"""
        # 拓扑排序
        in_degree = {task_id: 0 for task_id in tasks}
        for task_id in tasks:
            for dep in tasks[task_id].dependencies:
                if dep in tasks:
                    in_degree[task_id] += 1

        # BFS分层
        levels = []
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])

        while queue:
            level = []
            for _ in range(len(queue)):
                task_id = queue.popleft()
                level.append(task_id)

                # 更新依赖此任务的入度
                for other_id in tasks:
                    if task_id in tasks[other_id].dependencies:
                        in_degree[other_id] -= 1
                        if in_degree[other_id] == 0:
                            queue.append(other_id)

            if level:
                levels.append(level)

        return levels

    def has_cycle(self, tasks: dict) -> bool:
        """检测是否有循环依赖"""
        visited = set()
        rec_stack = set()

        def dfs(task_id):
            visited.add(task_id)
            rec_stack.add(task_id)

            for dep in tasks[task_id].dependencies:
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False


# ============================================================================
# 任务调度器
# ============================================================================

class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.task_queue: list[Task] = []
        self.running_tasks: dict[str, Task] = {}
        self.completed_tasks: dict[str, Task] = {}

    def submit(self, task: Task):
        """提交任务"""
        self.task_queue.append(task)
        # 按优先级排序
        self.task_queue.sort(key=lambda t: t.priority.value, reverse=True)

    def get_ready_tasks(self) -> list:
        """获取就绪任务"""
        ready = []
        for task in self.task_queue:
            if task.status == TaskStatus.READY:
                ready.append(task)
        return ready

    def start_task(self, task_id: str) -> bool:
        """启动任务"""
        for task in self.task_queue:
            if task.id == task_id:
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                self.running_tasks[task_id] = task
                return True
        return False

    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """完成任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()

            self.completed_tasks[task_id] = task
            del self.running_tasks[task_id]

            # 从队列移除
            self.task_queue = [t for t in self.task_queue if t.id != task_id]
            return True
        return False

    def fail_task(self, task_id: str, error: str) -> bool:
        """任务失败"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.error = error

            # 检查是否可以重试
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.READY
                del self.running_tasks[task_id]
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                self.completed_tasks[task_id] = task
                del self.running_tasks[task_id]

            return True
        return False

    def get_stats(self) -> dict:
        """获取统计"""
        return {
            'pending': len(self.task_queue),
            'running': len(self.running_tasks),
            'completed': len(self.completed_tasks),
        }


# ============================================================================
# 工作流引擎
# ============================================================================

class WorkflowEngine:
    """工作流引擎"""

    def __init__(self):
        self.workflows: dict[str, Workflow] = {}
        self.resolver = DependencyResolver()
        self.scheduler = TaskScheduler()

    def create_workflow(self, name: str, tasks: list) -> Workflow:
        """创建工作流"""
        workflow_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

        task_dict = {}
        for task in tasks:
            task_dict[task.id] = task

        workflow = Workflow(
            id=workflow_id,
            name=name,
            tasks=task_dict,
        )

        self.workflows[workflow_id] = workflow
        return workflow

    def execute_workflow(self, workflow_id: str) -> dict:
        """执行工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'error': '工作流不存在'}

        # 检查循环依赖
        if self.resolver.has_cycle(workflow.tasks):
            return {'error': '存在循环依赖'}

        # 解析执行层级
        levels = self.resolver.resolve(workflow.tasks)

        # 创建执行计划
        plan = ExecutionPlan(
            levels=levels,
            estimated_duration=len(workflow.tasks) * 10,  # 简化估算
            parallelism=max(len(level) for level in levels) if levels else 1,
        )

        workflow.status = TaskStatus.RUNNING

        return {
            'workflow_id': workflow_id,
            'plan': asdict(plan),
            'total_tasks': len(workflow.tasks),
        }

    def get_execution_plan(self, workflow_id: str) -> Optional[ExecutionPlan]:
        """获取执行计划"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        levels = self.resolver.resolve(workflow.tasks)

        return ExecutionPlan(
            levels=levels,
            estimated_duration=len(workflow.tasks) * 10,
            parallelism=max(len(level) for level in levels) if levels else 1,
        )

    def get_workflow_status(self, workflow_id: str) -> dict:
        """获取工作流状态"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'error': '工作流不存在'}

        status_counts = {}
        for task in workflow.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            'workflow_id': workflow_id,
            'status': workflow.status.value,
            'tasks': status_counts,
            'total': len(workflow.tasks),
        }


# ============================================================================
# 任务编排引擎
# ============================================================================

class TaskOrchestrationEngine:
    """
    任务编排引擎 - 整合所有组件

    核心功能：
    1. 创建和管理工作流
    2. 解析任务依赖
    3. 调度和执行任务
    4. 追踪执行状态
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "orchestration"
        os.makedirs(storage_dir, exist_ok=True)

        self.workflow_engine = WorkflowEngine()
        self.task_handlers: dict[str, Callable] = {}

        self.execution_history: list[dict] = []

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler

    def create_task(self, name: str, description: str,
                     dependencies: list = None,
                     priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        """创建任务"""
        task_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

        return Task(
            id=task_id,
            name=name,
            description=description,
            dependencies=dependencies or [],
            priority=priority,
        )

    def create_and_execute_workflow(self, name: str,
                                      tasks: list) -> dict:
        """创建并执行工作流"""
        workflow = self.workflow_engine.create_workflow(name, tasks)
        result = self.workflow_engine.execute_workflow(workflow.id)

        # 记录历史
        self.execution_history.append({
            'workflow_id': workflow.id,
            'name': name,
            'tasks': len(tasks),
            'timestamp': time.time(),
        })

        return result

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'workflows': len(self.workflow_engine.workflows),
            'handlers': len(self.task_handlers),
            'executions': len(self.execution_history),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("📋 任务编排报告")
        report.append("=" * 50)
        report.append(f"\n工作流数量: {stats['workflows']}")
        report.append(f"处理器数量: {stats['handlers']}")
        report.append(f"执行次数: {stats['executions']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = TaskOrchestrationEngine("test_orchestration")

    # 创建任务
    print("=== 创建任务 ===")
    tasks = [
        engine.create_task("数据收集", "收集原始数据", priority=TaskPriority.HIGH),
        engine.create_task("数据清洗", "清洗数据", dependencies=["数据收集"]),
        engine.create_task("特征工程", "提取特征", dependencies=["数据清洗"]),
        engine.create_task("模型训练", "训练模型", dependencies=["特征工程"]),
        engine.create_task("模型评估", "评估模型", dependencies=["模型训练"]),
    ]

    for task in tasks:
        print(f"  - {task.name} (依赖: {task.dependencies})")

    # 创建并执行工作流
    print("\n=== 执行工作流 ===")
    result = engine.create_and_execute_workflow("机器学习流水线", tasks)
    print(f"工作流ID: {result.get('workflow_id')}")
    print(f"总任务数: {result.get('total_tasks')}")
    if result.get('plan'):
        print(f"并行度: {result['plan']['parallelism']}")
        print(f"执行层级: {len(result['plan']['levels'])}")

    # 报告
    print("\n" + engine.generate_report())