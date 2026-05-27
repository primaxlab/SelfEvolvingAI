"""数据同步 - 增量同步、冲突解决、变更追踪"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ConflictResolution(Enum):
    LAST_WRITE = "last_write"
    FIRST_WRITE = "first_write"
    MANUAL = "manual"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"


@dataclass
class ChangeRecord:
    change_id: str
    resource: str
    operation: str  # create/update/delete
    data: Any = None
    timestamp: float = 0.0
    source: str = ""
    version: int = 0
    synced: bool = False


@dataclass
class SyncTask:
    task_id: str
    source: str
    target: str
    status: str = "pending"
    conflict_resolution: str = "last_write"
    changes_total: int = 0
    changes_synced: int = 0
    conflicts: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""


@dataclass
class Conflict:
    conflict_id: str
    resource: str
    source_data: Any = None
    target_data: Any = None
    source_version: int = 0
    target_version: int = 0
    resolution: str = ""
    resolved: bool = False


class DataSyncEngine:
    """数据同步引擎"""

    def __init__(self, storage_dir: str = "data/sync"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.change_log: List[ChangeRecord] = []
        self.sync_tasks: List[SyncTask] = []
        self.conflicts: List[Conflict] = []
        self.versions: Dict[str, int] = defaultdict(int)
        self.data_store: Dict[str, Any] = {}

    def track_change(self, resource: str, operation: str,
                     data: Any = None, source: str = "local") -> str:
        """追踪变更"""
        self.versions[resource] += 1
        change_id = hashlib.md5(f"{resource}_{time.time()}".encode()).hexdigest()[:12]

        change = ChangeRecord(
            change_id=change_id,
            resource=resource,
            operation=operation,
            data=data,
            timestamp=time.time(),
            source=source,
            version=self.versions[resource],
        )
        self.change_log.append(change)

        # 更新数据存储
        if operation == "delete":
            self.data_store.pop(resource, None)
        else:
            self.data_store[resource] = {"data": data, "version": change.version}

        return change_id

    def get_changes_since(self, since_version: int = 0,
                          source: str = "") -> List[Dict[str, Any]]:
        """获取指定版本后的变更"""
        changes = self.change_log
        if source:
            changes = [c for c in changes if c.source == source]
        return [asdict(c) for c in changes if c.version > since_version]

    def sync(self, source: str, target: str,
             conflict_resolution: str = "last_write") -> Dict[str, Any]:
        """执行同步"""
        task_id = hashlib.md5(f"{source}_{target}_{time.time()}".encode()).hexdigest()[:12]
        task = SyncTask(
            task_id=task_id,
            source=source,
            target=target,
            status="syncing",
            conflict_resolution=conflict_resolution,
            started_at=time.time(),
        )

        # 获取源变更
        source_changes = self.get_changes_since(source=source)
        task.changes_total = len(source_changes)

        synced = 0
        conflicts = 0

        for change in source_changes:
            resource = change["resource"]

            # 检查冲突
            if resource in self.data_store:
                existing = self.data_store[resource]
                if existing["version"] > change["version"]:
                    # 版本冲突
                    conflict = Conflict(
                        conflict_id=hashlib.md5(f"{resource}_{time.time()}".encode()).hexdigest()[:12],
                        resource=resource,
                        source_data=change["data"],
                        target_data=existing["data"],
                        source_version=change["version"],
                        target_version=existing["version"],
                    )

                    if conflict_resolution == ConflictResolution.LAST_WRITE.value:
                        self.data_store[resource] = {"data": change["data"], "version": change["version"]}
                        conflict.resolution = "source_wins"
                        conflict.resolved = True
                        synced += 1
                    elif conflict_resolution == ConflictResolution.TARGET_WINS.value:
                        conflict.resolution = "target_wins"
                        conflict.resolved = True
                    else:
                        conflicts += 1

                    self.conflicts.append(conflict)
                    continue

            # 应用变更
            self.data_store[resource] = {"data": change["data"], "version": change["version"]}
            synced += 1

        task.changes_synced = synced
        task.conflicts = conflicts
        task.status = "completed"
        task.completed_at = time.time()

        self.sync_tasks.append(task)

        return {
            "task_id": task_id,
            "status": task.status,
            "changes_total": task.changes_total,
            "changes_synced": synced,
            "conflicts": conflicts,
            "duration": task.completed_at - task.started_at,
        }

    def resolve_conflict(self, conflict_id: str, resolution: str,
                         data: Any = None) -> bool:
        """手动解决冲突"""
        for conflict in self.conflicts:
            if conflict.conflict_id == conflict_id and not conflict.resolved:
                if resolution == "use_source":
                    self.data_store[conflict.resource] = {
                        "data": conflict.source_data,
                        "version": max(conflict.source_version, conflict.target_version) + 1,
                    }
                elif resolution == "use_target":
                    pass  # 保持目标数据
                elif resolution == "use_custom" and data is not None:
                    self.data_store[conflict.resource] = {
                        "data": data,
                        "version": max(conflict.source_version, conflict.target_version) + 1,
                    }
                conflict.resolved = True
                conflict.resolution = resolution
                return True
        return False

    def get_pending_conflicts(self) -> List[Dict[str, Any]]:
        """获取未解决的冲突"""
        return [asdict(c) for c in self.conflicts if not c.resolved]

    def get_version(self, resource: str) -> int:
        """获取资源版本"""
        return self.versions.get(resource, 0)

    def get_data(self, resource: str) -> Optional[Any]:
        """获取数据"""
        entry = self.data_store.get(resource)
        return entry["data"] if entry else None

    def get_sync_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取同步历史"""
        return [asdict(t) for t in sorted(self.sync_tasks, key=lambda x: x.started_at, reverse=True)[:limit]]

    def generate_report(self) -> Dict[str, Any]:
        return {
            "total_changes": len(self.change_log),
            "total_syncs": len(self.sync_tasks),
            "total_conflicts": len(self.conflicts),
            "unresolved_conflicts": sum(1 for c in self.conflicts if not c.resolved),
            "resources_tracked": len(self.data_store),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "changes_count": len(self.change_log),
            "sync_tasks_count": len(self.sync_tasks),
            "conflicts_count": len(self.conflicts),
            "resources_count": len(self.data_store),
        }


if __name__ == "__main__":
    print("=== 数据同步测试 ===")
    engine = DataSyncEngine()

    # 追踪变更
    engine.track_change("user:1", "create", {"name": "Alice", "age": 30}, "db1")
    engine.track_change("user:2", "create", {"name": "Bob", "age": 25}, "db1")
    engine.track_change("user:1", "update", {"name": "Alice", "age": 31}, "db1")
    print(f"变更追踪: {len(engine.change_log)} 条")

    # 版本
    print(f"user:1 版本: {engine.get_version('user:1')}")
    print(f"user:1 数据: {engine.get_data('user:1')}")

    # 同步
    result = engine.sync("db1", "db2", "last_write")
    print(f"\n同步结果: {result}")

    # 增量变更
    engine.track_change("user:3", "create", {"name": "Charlie"}, "db1")
    changes = engine.get_changes_since(3)
    print(f"增量变更: {len(changes)} 条")

    report = engine.generate_report()
    print(f"\n同步报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
