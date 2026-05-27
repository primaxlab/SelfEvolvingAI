"""调度器 - Cron定时任务、任务调度、延迟执行"""

import json
import os
import time
import hashlib
import threading
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class ScheduleType(Enum):
    """调度类型"""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DELAY = "delay"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    name: str
    schedule_type: str = "interval"
    status: str = "pending"
    interval_seconds: float = 0
    cron_expression: str = ""
    delay_seconds: float = 0
    run_at: float = 0
    last_run: float = 0
    next_run: float = 0
    run_count: int = 0
    max_runs: int = 0  # 0=无限
    max_failures: int = 3
    failure_count: int = 0
    callback_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: float = 0.0
    result: str = ""
    error: str = ""


@dataclass
class TaskExecution:
    """任务执行记录"""
    execution_id: str
    task_id: str
    started_at: float = 0.0
    completed_at: float = 0.0
    duration: float = 0.0
    status: str = "running"
    result: Any = None
    error: str = ""


class CronParser:
    """简单Cron表达式解析器"""

    @staticmethod
    def parse(expression: str) -> Dict[str, Any]:
        """解析cron表达式 (分 时 日 月 周)"""
        parts = expression.strip().split()
        if len(parts) != 5:
            return {"error": "无效的cron表达式"}

        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "weekday": parts[4],
        }

    @staticmethod
    def next_run_time(expression: str, after: float = 0) -> float:
        """计算下次运行时间(简化版)"""
        if after == 0:
            after = time.time()

        parts = expression.strip().split()
        if len(parts) != 5:
            return 0

        # 简化实现：只处理固定间隔
        try:
            minute = int(parts[0]) if parts[0] != '*' else -1
            hour = int(parts[1]) if parts[1] != '*' else -1

            if minute >= 0 and hour >= 0:
                # 每天指定时间
                import datetime
                now = datetime.datetime.fromtimestamp(after)
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target <= now:
                    target += datetime.timedelta(days=1)
                return target.timestamp()
        except (ValueError, TypeError):
            pass

        return after + 3600  # 默认1小时后


class SchedulerEngine:
    """调度器引擎"""

    def __init__(self, storage_dir: str = "data/scheduler"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.tasks: Dict[str, ScheduledTask] = {}
        self.executions: List[TaskExecution] = []
        self.callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "scheduler_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("tasks", {}).items():
                    self.tasks[k] = ScheduledTask(**v)
                self.executions = [TaskExecution(**e) for e in data.get("executions", [])]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "scheduler_data.json")
        data = {
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "executions": [asdict(e) for e in self.executions[-2000:]],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def schedule_once(self, name: str, run_at: float, callback_name: str = "",
                      args: Dict[str, Any] = None, tags: List[str] = None) -> str:
        """一次性调度"""
        task_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        task = ScheduledTask(
            task_id=task_id, name=name,
            schedule_type=ScheduleType.ONCE.value,
            status=TaskStatus.SCHEDULED.value,
            run_at=run_at, next_run=run_at,
            callback_name=callback_name,
            args=args or {}, tags=tags or [],
            created_at=time.time(),
        )
        self.tasks[task_id] = task
        self._save()
        return task_id

    def schedule_interval(self, name: str, interval_seconds: float,
                          callback_name: str = "", max_runs: int = 0,
                          args: Dict[str, Any] = None, tags: List[str] = None) -> str:
        """间隔调度"""
        task_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()
        task = ScheduledTask(
            task_id=task_id, name=name,
            schedule_type=ScheduleType.INTERVAL.value,
            status=TaskStatus.SCHEDULED.value,
            interval_seconds=interval_seconds,
            next_run=now + interval_seconds,
            callback_name=callback_name,
            max_runs=max_runs,
            args=args or {}, tags=tags or [],
            created_at=now,
        )
        self.tasks[task_id] = task
        self._save()
        return task_id

    def schedule_cron(self, name: str, cron_expression: str,
                      callback_name: str = "", args: Dict[str, Any] = None,
                      tags: List[str] = None) -> str:
        """Cron调度"""
        task_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        next_run = CronParser.next_run_time(cron_expression)
        task = ScheduledTask(
            task_id=task_id, name=name,
            schedule_type=ScheduleType.CRON.value,
            status=TaskStatus.SCHEDULED.value,
            cron_expression=cron_expression,
            next_run=next_run,
            callback_name=callback_name,
            args=args or {}, tags=tags or [],
            created_at=time.time(),
        )
        self.tasks[task_id] = task
        self._save()
        return task_id

    def schedule_delay(self, name: str, delay_seconds: float,
                       callback_name: str = "", args: Dict[str, Any] = None) -> str:
        """延迟调度"""
        task_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()
        task = ScheduledTask(
            task_id=task_id, name=name,
            schedule_type=ScheduleType.DELAY.value,
            status=TaskStatus.SCHEDULED.value,
            delay_seconds=delay_seconds,
            next_run=now + delay_seconds,
            callback_name=callback_name,
            args=args or {},
            created_at=now,
        )
        self.tasks[task_id] = task
        self._save()
        return task_id

    def register_callback(self, name: str, callback: Callable):
        """注册回调"""
        self.callbacks[name] = callback

    def tick(self) -> List[Dict[str, Any]]:
        """调度器心跳 - 检查并执行到期任务"""
        now = time.time()
        executed = []

        with self._lock:
            for task in self.tasks.values():
                if not task.is_active:
                    continue
                if task.status not in [TaskStatus.SCHEDULED.value, TaskStatus.PENDING.value]:
                    continue
                if task.next_run > now:
                    continue

                # 执行任务
                result = self._execute_task(task)
                executed.append(result)

                # 更新下次运行时间
                if task.schedule_type == ScheduleType.INTERVAL.value:
                    task.next_run = now + task.interval_seconds
                    if task.max_runs > 0 and task.run_count >= task.max_runs:
                        task.status = TaskStatus.COMPLETED.value
                        task.is_active = False
                elif task.schedule_type == ScheduleType.CRON.value:
                    task.next_run = CronParser.next_run_time(task.cron_expression, now)
                elif task.schedule_type in [ScheduleType.ONCE.value, ScheduleType.DELAY.value]:
                    task.status = TaskStatus.COMPLETED.value
                    task.is_active = False

        if executed:
            self._save()

        return executed

    def _execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """执行任务"""
        execution_id = hashlib.md5(f"{task.task_id}_{time.time()}".encode()).hexdigest()[:12]
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task.task_id,
            started_at=time.time(),
            status="running",
        )

        task.status = TaskStatus.RUNNING.value
        task.last_run = time.time()
        task.run_count += 1

        # 尝试执行回调
        callback = self.callbacks.get(task.callback_name)
        if callback:
            try:
                result = callback(**task.args)
                execution.status = "completed"
                execution.result = str(result)[:500]
                task.result = str(result)[:200]
                task.failure_count = 0
            except Exception as e:
                execution.status = "failed"
                execution.error = str(e)
                task.error = str(e)[:200]
                task.failure_count += 1
                if task.failure_count >= task.max_failures:
                    task.status = TaskStatus.FAILED.value
                    task.is_active = False
        else:
            execution.status = "completed"
            execution.result = "no_callback"

        execution.completed_at = time.time()
        execution.duration = execution.completed_at - execution.started_at
        task.status = TaskStatus.SCHEDULED.value

        self.executions.append(execution)
        return asdict(execution)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED.value
            self.tasks[task_id].is_active = False
            self._save()
            return True
        return False

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.PAUSED.value
            self.tasks[task_id].is_active = False
            self._save()
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PAUSED.value:
                task.status = TaskStatus.SCHEDULED.value
                task.is_active = True
                task.next_run = time.time() + (task.interval_seconds or 60)
                self._save()
                return True
        return False

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """获取待执行任务"""
        now = time.time()
        pending = [
            asdict(t) for t in self.tasks.values()
            if t.is_active and t.next_run <= now + 60
        ]
        return sorted(pending, key=lambda x: x["next_run"])

    def get_task_history(self, task_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        executions = self.executions
        if task_id:
            executions = [e for e in executions if e.task_id == task_id]
        return [asdict(e) for e in sorted(executions, key=lambda x: x.started_at, reverse=True)[:limit]]

    def get_tasks_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """按标签获取任务"""
        return [asdict(t) for t in self.tasks.values() if tag in t.tags]

    def cleanup_completed(self) -> int:
        """清理已完成任务"""
        completed = [
            tid for tid, t in self.tasks.items()
            if t.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]
        ]
        for tid in completed:
            del self.tasks[tid]
        self._save()
        return len(completed)

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        status_counts = defaultdict(int)
        type_counts = defaultdict(int)
        for t in self.tasks.values():
            status_counts[t.status] += 1
            type_counts[t.schedule_type] += 1

        return {
            "total_tasks": len(self.tasks),
            "active_tasks": sum(1 for t in self.tasks.values() if t.is_active),
            "total_executions": len(self.executions),
            "status_distribution": dict(status_counts),
            "type_distribution": dict(type_counts),
            "registered_callbacks": len(self.callbacks),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tasks_count": len(self.tasks),
            "active_count": sum(1 for t in self.tasks.values() if t.is_active),
            "executions_count": len(self.executions),
            "callbacks_count": len(self.callbacks),
        }


if __name__ == "__main__":
    print("=== 调度器测试 ===")
    engine = SchedulerEngine()

    # 注册回调
    engine.register_callback("print_hello", lambda msg="Hello": print(f"  回调: {msg}"))

    # 间隔调度
    t1 = engine.schedule_interval("每5秒问候", 5, "print_hello", max_runs=3, args={"msg": "你好"})
    print(f"间隔任务: {t1}")

    # 延迟调度
    t2 = engine.schedule_delay("延迟任务", 10, "print_hello", args={"msg": "延迟执行"})
    print(f"延迟任务: {t2}")

    # Cron调度
    t3 = engine.schedule_cron("每日报告", "0 9 * * *", "print_hello")
    print(f"Cron任务: {t3}")

    # 模拟心跳
    print("\n模拟调度器心跳:")
    for i in range(3):
        executed = engine.tick()
        if executed:
            for e in executed:
                print(f"  执行: {e['task_id']} -> {e['status']}")
        time.sleep(0.1)

    # 报告
    report = engine.generate_report()
    print(f"\n调度报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
