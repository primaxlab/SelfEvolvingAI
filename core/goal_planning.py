"""
================================================================================
目标规划系统 (Goal Planning System)
================================================================================

核心能力：
  1. 目标分解 - 将复杂目标拆解为可执行的子任务
  2. 任务排序 - 确定任务执行顺序和依赖关系
  3. 资源评估 - 评估完成任务需要的资源
  4. 进度追踪 - 监控任务执行进度
  5. 计划调整 - 根据执行情况动态调整计划

设计原则：
  - SMART目标：具体、可衡量、可达成、相关、有时限
  - 最小化依赖：减少任务间的耦合
  - 弹性规划：预留缓冲时间应对意外
"""

import json
import os
import time
import hashlib
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque


# ============================================================================
# 数据结构
# ============================================================================

class GoalStatus(Enum):
    PENDING = "pending"          # 待开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 已失败
    BLOCKED = "blocked"         # 被阻塞
    CANCELLED = "cancelled"     # 已取消

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ResourceType(Enum):
    TIME = "time"
    COMPUTE = "compute"
    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    HUMAN = "human"

@dataclass
class Resource:
    """资源"""
    resource_type: ResourceType
    amount: float
    unit: str = ""

@dataclass
class Task:
    """任务"""
    id: str
    title: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None       # 父任务ID
    subtask_ids: list = field(default_factory=list)  # 子任务ID列表
    dependencies: list = field(default_factory=list)  # 依赖的任务ID
    required_resources: list = field(default_factory=list)  # 所需资源
    estimated_duration: float = 0.0       # 预估时长(秒)
    actual_duration: float = 0.0          # 实际时长(秒)
    progress: float = 0.0                 # 进度 0-1
    result: Any = None                    # 执行结果
    error: str = ""                       # 错误信息
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    deadline: Optional[float] = None      # 截止时间
    metadata: dict = field(default_factory=dict)

@dataclass
class Goal:
    """目标"""
    id: str
    title: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: TaskPriority = TaskPriority.HIGH
    root_task_ids: list = field(default_factory=list)  # 根任务ID列表
    success_criteria: list = field(default_factory=list)  # 成功标准
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    metadata: dict = field(default_factory=dict)

@dataclass
class ExecutionPlan:
    """执行计划"""
    id: str
    goal_id: str
    task_order: list              # 任务执行顺序
    critical_path: list           # 关键路径
    estimated_duration: float     # 预估总时长
    risk_factors: list = field(default_factory=list)  # 风险因素
    created_at: float = field(default_factory=time.time)


# ============================================================================
# 目标分解器
# ============================================================================

class GoalDecomposer:
    """目标分解器"""

    def __init__(self):
        # 分解策略
        self.strategies = {
            'sequential': self._decompose_sequential,
            'parallel': self._decompose_parallel,
            'hierarchical': self._decompose_hierarchical,
        }

    def decompose(self, goal: Goal, strategy: str = 'hierarchical') -> list:
        """分解目标为任务"""
        decomposer = self.strategies.get(strategy, self._decompose_hierarchical)
        return decomposer(goal)

    def _decompose_sequential(self, goal: Goal) -> list:
        """顺序分解：任务按顺序执行"""
        tasks = []

        # 通用分解模板
        phases = [
            ("分析需求", "理解和分析目标需求", TaskPriority.HIGH),
            ("设计方案", "制定实现方案", TaskPriority.HIGH),
            ("实现核心", "实现核心功能", TaskPriority.CRITICAL),
            ("测试验证", "测试和验证结果", TaskPriority.HIGH),
            ("优化完善", "优化和完善", TaskPriority.MEDIUM),
        ]

        prev_task_id = None
        for i, (title, desc, priority) in enumerate(phases):
            task = Task(
                id=f"task_{goal.id}_{i}",
                title=title,
                description=desc,
                priority=priority,
                parent_id=goal.id,
                dependencies=[prev_task_id] if prev_task_id else [],
                estimated_duration=3600,  # 默认1小时
            )
            tasks.append(task)
            prev_task_id = task.id

        return tasks

    def _decompose_parallel(self, goal: Goal) -> list:
        """并行分解：任务可并行执行"""
        tasks = []

        subtasks = [
            ("子任务A", "独立子任务A", TaskPriority.MEDIUM),
            ("子任务B", "独立子任务B", TaskPriority.MEDIUM),
            ("子任务C", "独立子任务C", TaskPriority.MEDIUM),
            ("整合结果", "整合所有子任务结果", TaskPriority.HIGH),
        ]

        for i, (title, desc, priority) in enumerate(subtasks):
            task = Task(
                id=f"task_{goal.id}_{i}",
                title=title,
                description=desc,
                priority=priority,
                parent_id=goal.id,
                dependencies=[] if i < len(subtasks) - 1 else
                             [f"task_{goal.id}_{j}" for j in range(len(subtasks) - 1)],
                estimated_duration=1800,
            )
            tasks.append(task)

        return tasks

    def _decompose_hierarchical(self, goal: Goal) -> list:
        """层次分解：逐层细化"""
        tasks = []

        # 第一层：主要阶段
        main_phases = [
            ("规划阶段", "制定整体计划", TaskPriority.HIGH, [
                ("需求分析", "分析具体需求", TaskPriority.HIGH),
                ("资源评估", "评估所需资源", TaskPriority.MEDIUM),
                ("风险识别", "识别潜在风险", TaskPriority.MEDIUM),
            ]),
            ("执行阶段", "执行核心任务", TaskPriority.CRITICAL, [
                ("环境准备", "准备执行环境", TaskPriority.HIGH),
                ("核心实现", "实现主要功能", TaskPriority.CRITICAL),
                ("集成测试", "测试集成功能", TaskPriority.HIGH),
            ]),
            ("收尾阶段", "完成和总结", TaskPriority.MEDIUM, [
                ("结果验证", "验证最终结果", TaskPriority.HIGH),
                ("文档整理", "整理相关文档", TaskPriority.LOW),
                ("经验总结", "总结经验教训", TaskPriority.MEDIUM),
            ]),
        ]

        for phase_idx, (phase_title, phase_desc, phase_priority, subtasks) in enumerate(main_phases):
            phase_id = f"task_{goal.id}_{phase_idx}"

            # 创建阶段任务
            phase_task = Task(
                id=phase_id,
                title=phase_title,
                description=phase_desc,
                priority=phase_priority,
                parent_id=goal.id,
                subtask_ids=[f"task_{goal.id}_{phase_idx}_{i}" for i in range(len(subtasks))],
                dependencies=[f"task_{goal.id}_{phase_idx - 1}"] if phase_idx > 0 else [],
            )
            tasks.append(phase_task)

            # 创建子任务
            for sub_idx, (sub_title, sub_desc, sub_priority) in enumerate(subtasks):
                sub_id = f"task_{goal.id}_{phase_idx}_{sub_idx}"
                sub_task = Task(
                    id=sub_id,
                    title=sub_title,
                    description=sub_desc,
                    priority=sub_priority,
                    parent_id=phase_id,
                    dependencies=[f"task_{goal.id}_{phase_idx}_{sub_idx - 1}"] if sub_idx > 0 else [],
                    estimated_duration=1800,
                )
                tasks.append(sub_task)

        return tasks


# ============================================================================
# 任务调度器
# ============================================================================

class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def add_tasks(self, tasks: list):
        """添加任务"""
        for task in tasks:
            self.tasks[task.id] = task

    def get_executable_tasks(self) -> list:
        """获取可执行的任务（依赖已满足）"""
        executable = []

        for task in self.tasks.values():
            if task.status != GoalStatus.PENDING:
                continue

            # 检查依赖
            deps_satisfied = all(
                self.tasks.get(dep_id) and
                self.tasks[dep_id].status == GoalStatus.COMPLETED
                for dep_id in task.dependencies
            )

            if deps_satisfied:
                executable.append(task)

        # 按优先级排序
        executable.sort(key=lambda t: t.priority.value, reverse=True)
        return executable

    def update_task_status(self, task_id: str, status: GoalStatus,
                           result: Any = None, error: str = ""):
        """更新任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return

        task.status = status

        if status == GoalStatus.IN_PROGRESS:
            task.started_at = time.time()
        elif status == GoalStatus.COMPLETED:
            task.completed_at = time.time()
            task.result = result
            if task.started_at:
                task.actual_duration = task.completed_at - task.started_at
        elif status == GoalStatus.FAILED:
            task.error = error

    def get_task_progress(self, task_id: str) -> float:
        """获取任务进度（包括子任务）"""
        task = self.tasks.get(task_id)
        if not task:
            return 0.0

        if not task.subtask_ids:
            return task.progress

        # 计算子任务平均进度
        subtask_progress = []
        for sub_id in task.subtask_ids:
            subtask_progress.append(self.get_task_progress(sub_id))

        return sum(subtask_progress) / len(subtask_progress) if subtask_progress else 0.0

    def get_critical_path(self) -> list:
        """计算关键路径"""
        # 拓扑排序 + 最长路径
        visited = set()
        path = []

        def dfs(task_id):
            if task_id in visited:
                return
            visited.add(task_id)

            task = self.tasks.get(task_id)
            if not task:
                return

            for dep_id in task.dependencies:
                dfs(dep_id)

            path.append(task_id)

        for task_id in self.tasks:
            dfs(task_id)

        return path

    def get_blocked_tasks(self) -> list:
        """获取被阻塞的任务"""
        blocked = []
        for task in self.tasks.values():
            if task.status == GoalStatus.PENDING:
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if dep_task and dep_task.status == GoalStatus.FAILED:
                        blocked.append(task)
                        break
        return blocked


# ============================================================================
# 计划执行器
# ============================================================================

class PlanExecutor:
    """计划执行器"""

    def __init__(self, scheduler: TaskScheduler):
        self.scheduler = scheduler
        self.execution_log: list[dict] = []
        self.handlers: dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.handlers[task_type] = handler

    def execute_next(self) -> Optional[dict]:
        """执行下一个任务"""
        executable = self.scheduler.get_executable_tasks()
        if not executable:
            return None

        task = executable[0]

        # 更新状态
        self.scheduler.update_task_status(task.id, GoalStatus.IN_PROGRESS)

        # 查找处理器
        handler = self.handlers.get(task.title)
        if handler:
            try:
                result = handler(task)
                self.scheduler.update_task_status(
                    task.id, GoalStatus.COMPLETED, result=result
                )
                log_entry = {
                    'task_id': task.id,
                    'task_title': task.title,
                    'status': 'completed',
                    'result': result,
                    'timestamp': time.time(),
                }
            except Exception as e:
                self.scheduler.update_task_status(
                    task.id, GoalStatus.FAILED, error=str(e)
                )
                log_entry = {
                    'task_id': task.id,
                    'task_title': task.title,
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': time.time(),
                }
        else:
            # 无处理器，标记为完成（人工处理）
            self.scheduler.update_task_status(
                task.id, GoalStatus.COMPLETED,
                result="需要人工处理"
            )
            log_entry = {
                'task_id': task.id,
                'task_title': task.title,
                'status': 'completed',
                'result': '需要人工处理',
                'timestamp': time.time(),
            }

        self.execution_log.append(log_entry)
        return log_entry

    def execute_all(self, max_iterations: int = 100) -> list:
        """执行所有任务"""
        results = []
        iteration = 0

        while iteration < max_iterations:
            result = self.execute_next()
            if result is None:
                break
            results.append(result)
            iteration += 1

        return results

    def get_execution_summary(self) -> dict:
        """获取执行摘要"""
        total = len(self.scheduler.tasks)
        completed = sum(1 for t in self.scheduler.tasks.values()
                       if t.status == GoalStatus.COMPLETED)
        failed = sum(1 for t in self.scheduler.tasks.values()
                    if t.status == GoalStatus.FAILED)
        in_progress = sum(1 for t in self.scheduler.tasks.values()
                         if t.status == GoalStatus.IN_PROGRESS)

        return {
            'total_tasks': total,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'progress': completed / total if total > 0 else 0,
            'execution_log': self.execution_log,
        }


# ============================================================================
# 目标规划引擎
# ============================================================================

class GoalPlanningEngine:
    """
    目标规划引擎 - 整合所有组件

    核心功能：
    1. 接收高层目标
    2. 分解为可执行任务
    3. 生成执行计划
    4. 追踪执行进度
    5. 动态调整计划
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "goal_planning"
        os.makedirs(storage_dir, exist_ok=True)

        self.decomposer = GoalDecomposer()
        self.scheduler = TaskScheduler()
        self.executor = PlanExecutor(self.scheduler)
        self.goals: dict[str, Goal] = {}
        self.plans: dict[str, ExecutionPlan] = {}

        self.storage_path = os.path.join(storage_dir, "plans.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 加载目标
                for g_data in data.get('goals', []):
                    g_data['status'] = GoalStatus(g_data['status'])
                    g_data['priority'] = TaskPriority(g_data['priority'])
                    goal = Goal(**g_data)
                    self.goals[goal.id] = goal

    def _save(self):
        """保存数据"""
        data = {
            'goals': [],
        }
        for goal in self.goals.values():
            g_dict = asdict(goal)
            g_dict['status'] = goal.status.value
            g_dict['priority'] = goal.priority.value
            data['goals'].append(g_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_goal(self, title: str, description: str,
                    priority: TaskPriority = TaskPriority.HIGH,
                    deadline: float = None) -> Goal:
        """创建新目标"""
        goal_id = hashlib.md5(f"{title}{time.time()}".encode()).hexdigest()[:12]

        goal = Goal(
            id=goal_id,
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
        )

        self.goals[goal_id] = goal
        self._save()
        return goal

    def plan_goal(self, goal_id: str,
                  strategy: str = 'hierarchical') -> ExecutionPlan:
        """为目标制定计划"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"目标 {goal_id} 不存在")

        # 分解目标
        tasks = self.decomposer.decompose(goal, strategy)

        # 添加到调度器
        self.scheduler.add_tasks(tasks)

        # 设置根任务
        goal.root_task_ids = [t.id for t in tasks if t.parent_id == goal.id]

        # 计算关键路径
        critical_path = self.scheduler.get_critical_path()

        # 估算总时长
        total_duration = sum(t.estimated_duration for t in tasks)

        # 识别风险
        risk_factors = self._identify_risks(tasks)

        # 创建执行计划
        plan = ExecutionPlan(
            id=f"plan_{goal_id}",
            goal_id=goal_id,
            task_order=[t.id for t in tasks],
            critical_path=critical_path,
            estimated_duration=total_duration,
            risk_factors=risk_factors,
        )

        self.plans[goal_id] = plan
        self._save()
        return plan

    def _identify_risks(self, tasks: list) -> list:
        """识别风险因素"""
        risks = []

        # 检查依赖链长度
        max_dep_depth = 0
        for task in tasks:
            depth = len(task.dependencies)
            max_dep_depth = max(max_dep_depth, depth)

        if max_dep_depth > 5:
            risks.append({
                'type': 'dependency_chain',
                'description': f'依赖链过长 ({max_dep_depth}层)',
                'severity': 'medium',
            })

        # 检查关键任务
        critical_tasks = [t for t in tasks if t.priority == TaskPriority.CRITICAL]
        if len(critical_tasks) > 3:
            risks.append({
                'type': 'too_many_critical',
                'description': f'关键任务过多 ({len(critical_tasks)}个)',
                'severity': 'high',
            })

        return risks

    def execute_goal(self, goal_id: str) -> dict:
        """执行目标"""
        goal = self.goals.get(goal_id)
        if not goal:
            return {'error': f'目标 {goal_id} 不存在'}

        goal.status = GoalStatus.IN_PROGRESS
        self._save()

        # 执行所有任务
        results = self.executor.execute_all()

        # 更新目标状态
        summary = self.executor.get_execution_summary()
        if summary['failed'] > 0:
            goal.status = GoalStatus.FAILED
        elif summary['completed'] == summary['total_tasks']:
            goal.status = GoalStatus.COMPLETED
        else:
            goal.status = GoalStatus.IN_PROGRESS

        self._save()
        return summary

    def get_goal_progress(self, goal_id: str) -> dict:
        """获取目标进度"""
        goal = self.goals.get(goal_id)
        if not goal:
            return {'error': f'目标 {goal_id} 不存在'}

        plan = self.plans.get(goal_id)
        if not plan:
            return {'error': f'目标 {goal_id} 尚未制定计划'}

        # 计算整体进度
        total_tasks = len(plan.task_order)
        completed_tasks = sum(
            1 for task_id in plan.task_order
            if self.scheduler.tasks.get(task_id) and
               self.scheduler.tasks[task_id].status == GoalStatus.COMPLETED
        )

        return {
            'goal_id': goal_id,
            'goal_title': goal.title,
            'status': goal.status.value,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'progress': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'critical_path': plan.critical_path,
            'risks': plan.risk_factors,
        }

    def adjust_plan(self, goal_id: str, adjustments: dict) -> ExecutionPlan:
        """调整计划"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"目标 {goal_id} 不存在")

        # 重新分解
        new_strategy = adjustments.get('strategy', 'hierarchical')
        new_tasks = self.decomposer.decompose(goal, new_strategy)

        # 更新调度器
        self.scheduler.add_tasks(new_tasks)

        # 重新生成计划
        return self.plan_goal(goal_id, new_strategy)

    def get_status_report(self) -> str:
        """生成状态报告"""
        report = []
        report.append("=" * 50)
        report.append("🎯 目标规划状态报告")
        report.append("=" * 50)

        for goal in self.goals.values():
            report.append(f"\n目标: {goal.title}")
            report.append(f"  状态: {goal.status.value}")
            report.append(f"  优先级: {goal.priority.value}")

            progress = self.get_goal_progress(goal.id)
            if 'error' not in progress:
                report.append(f"  进度: {progress['progress']:.0%}")
                report.append(f"  任务: {progress['completed_tasks']}/{progress['total_tasks']}")

                if progress['risks']:
                    report.append(f"  风险: {len(progress['risks'])}个")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = GoalPlanningEngine("test_goal_planning")

    # 创建目标
    goal = engine.create_goal(
        title="构建自我进化AI系统",
        description="开发一个能够自我学习、自我改进的AI系统",
        priority=TaskPriority.CRITICAL,
    )

    print(f"创建目标: {goal.title} (ID: {goal.id})")

    # 制定计划
    plan = engine.plan_goal(goal.id)
    print(f"\n执行计划:")
    print(f"  任务数量: {len(plan.task_order)}")
    print(f"  预估时长: {plan.estimated_duration/3600:.1f}小时")
    print(f"  关键路径: {len(plan.critical_path)}个任务")
    print(f"  风险因素: {len(plan.risk_factors)}个")

    # 执行
    print("\n=== 执行目标 ===")
    result = engine.execute_goal(goal.id)
    print(f"执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 状态报告
    print("\n" + engine.get_status_report())