"""备份恢复系统 - 数据备份、增量备份、恢复管理、版本回滚"""

import json
import os
import time
import hashlib
import shutil
import zipfile
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict


class BackupType(Enum):
    """备份类型"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """备份状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class RestoreStatus(Enum):
    """恢复状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackupRecord:
    """备份记录"""
    backup_id: str
    backup_type: str
    source_path: str
    backup_path: str
    status: str = "pending"
    size_bytes: int = 0
    file_count: int = 0
    created_at: float = 0.0
    completed_at: float = 0.0
    duration: float = 0.0
    parent_backup_id: str = ""
    checksum: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: float = 0.0


@dataclass
class RestoreRecord:
    """恢复记录"""
    restore_id: str
    backup_id: str
    target_path: str
    status: str = "pending"
    created_at: float = 0.0
    completed_at: float = 0.0
    duration: float = 0.0
    files_restored: int = 0
    description: str = ""


@dataclass
class BackupPolicy:
    """备份策略"""
    policy_id: str
    name: str
    backup_type: str = "incremental"
    schedule_cron: str = ""
    retention_days: int = 30
    max_backups: int = 10
    source_paths: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: float = 0.0
    last_run: float = 0.0


@dataclass
class BackupSchedule:
    """备份调度"""
    schedule_id: str
    policy_id: str
    next_run: float = 0.0
    last_run: float = 0.0
    run_count: int = 0
    is_active: bool = True


class BackupRecoveryEngine:
    """备份恢复引擎"""

    def __init__(self, storage_dir: str = "data/backup", backup_dir: str = "backups"):
        self.storage_dir = storage_dir
        self.backup_dir = backup_dir
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        self.backup_records: Dict[str, BackupRecord] = {}
        self.restore_records: List[RestoreRecord] = []
        self.policies: Dict[str, BackupPolicy] = {}
        self.schedules: Dict[str, BackupSchedule] = {}
        self.file_hashes: Dict[str, str] = {}  # file_path -> hash

        self._load()

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "backup_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("backup_records", {}).items():
                    self.backup_records[k] = BackupRecord(**v)
                self.restore_records = [RestoreRecord(**r) for r in data.get("restore_records", [])]
                for k, v in data.get("policies", {}).items():
                    self.policies[k] = BackupPolicy(**v)
                for k, v in data.get("schedules", {}).items():
                    self.schedules[k] = BackupSchedule(**v)
                self.file_hashes = data.get("file_hashes", {})
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "backup_data.json")
        data = {
            "backup_records": {k: asdict(v) for k, v in self.backup_records.items()},
            "restore_records": [asdict(r) for r in self.restore_records[-1000:]],
            "policies": {k: asdict(v) for k, v in self.policies.items()},
            "schedules": {k: asdict(v) for k, v in self.schedules.items()},
            "file_hashes": self.file_hashes
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        if not os.path.exists(file_path):
            return ""

        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except (IOError, OSError):
            return ""
        return hash_md5.hexdigest()

    def _get_file_hash(self, file_path: str) -> str:
        """获取文件哈希(带缓存)"""
        if file_path not in self.file_hashes:
            self.file_hashes[file_path] = self._calculate_checksum(file_path)
        return self.file_hashes[file_path]

    def create_backup(self, source_path: str, backup_type: str = "incremental",
                      description: str = "", tags: List[str] = None,
                      parent_backup_id: str = "") -> str:
        """创建备份"""
        backup_id = hashlib.md5(f"{source_path}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()

        backup_path = os.path.join(self.backup_dir, f"{backup_id}.zip")

        record = BackupRecord(
            backup_id=backup_id,
            backup_type=backup_type,
            source_path=source_path,
            backup_path=backup_path,
            status=BackupStatus.IN_PROGRESS.value,
            created_at=now,
            description=description,
            tags=tags or [],
            parent_backup_id=parent_backup_id
        )

        self.backup_records[backup_id] = record

        try:
            if backup_type == BackupType.FULL.value:
                success = self._full_backup(source_path, backup_path)
            elif backup_type == BackupType.INCREMENTAL.value:
                success = self._incremental_backup(source_path, backup_path, parent_backup_id)
            else:
                success = self._full_backup(source_path, backup_path)

            if success:
                record.status = BackupStatus.COMPLETED.value
                record.completed_at = time.time()
                record.duration = record.completed_at - record.created_at
                record.size_bytes = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
                record.checksum = self._calculate_checksum(backup_path)
            else:
                record.status = BackupStatus.FAILED.value
        except Exception as e:
            record.status = BackupStatus.FAILED.value
            record.metadata["error"] = str(e)

        self._save()
        return backup_id

    def _full_backup(self, source_path: str, backup_path: str) -> bool:
        """全量备份"""
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.isfile(source_path):
                    zf.write(source_path, os.path.basename(source_path))
                    self.backup_records[hashlib.md5(f"{source_path}_{time.time()}".encode()).hexdigest()[:12]].file_count = 1
                elif os.path.isdir(source_path):
                    file_count = 0
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, source_path)
                            zf.write(file_path, arcname)
                            file_count += 1
                    # Update file count on the record
                    for record in self.backup_records.values():
                        if record.backup_path == backup_path:
                            record.file_count = file_count
                            break
            return True
        except Exception:
            return False

    def _incremental_backup(self, source_path: str, backup_path: str,
                           parent_backup_id: str) -> bool:
        """增量备份"""
        changed_files = []

        if os.path.isfile(source_path):
            current_hash = self._get_file_hash(source_path)
            if self.file_hashes.get(source_path) != current_hash:
                changed_files.append(source_path)
        elif os.path.isdir(source_path):
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    current_hash = self._get_file_hash(file_path)
                    if self.file_hashes.get(file_path) != current_hash:
                        changed_files.append(file_path)

        if not changed_files:
            return True

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in changed_files:
                    arcname = os.path.relpath(file_path, source_path) if os.path.isdir(source_path) else os.path.basename(file_path)
                    zf.write(file_path, arcname)
            return True
        except Exception:
            return False

    def restore_backup(self, backup_id: str, target_path: str,
                       overwrite: bool = False) -> str:
        """恢复备份"""
        if backup_id not in self.backup_records:
            return ""

        record = self.backup_records[backup_id]
        restore_id = hashlib.md5(f"{backup_id}_{time.time()}".encode()).hexdigest()[:12]

        restore = RestoreRecord(
            restore_id=restore_id,
            backup_id=backup_id,
            target_path=target_path,
            status=RestoreStatus.IN_PROGRESS.value,
            created_at=time.time()
        )

        try:
            if not os.path.exists(record.backup_path):
                restore.status = RestoreStatus.FAILED.value
                restore.description = "备份文件不存在"
            else:
                os.makedirs(target_path, exist_ok=True)

                with zipfile.ZipFile(record.backup_path, 'r') as zf:
                    if overwrite:
                        zf.extractall(target_path)
                    else:
                        for member in zf.namelist():
                            target_file = os.path.join(target_path, member)
                            if not os.path.exists(target_file):
                                zf.extract(member, target_path)

                    restore.files_restored = len(zf.namelist())

                restore.status = RestoreStatus.COMPLETED.value
                restore.completed_at = time.time()
                restore.duration = restore.completed_at - restore.created_at
        except Exception as e:
            restore.status = RestoreStatus.FAILED.value
            restore.description = str(e)

        self.restore_records.append(restore)
        self._save()
        return restore_id

    def create_policy(self, name: str, backup_type: str = "incremental",
                      retention_days: int = 30, max_backups: int = 10,
                      source_paths: List[str] = None,
                      exclude_patterns: List[str] = None) -> str:
        """创建备份策略"""
        policy_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        policy = BackupPolicy(
            policy_id=policy_id,
            name=name,
            backup_type=backup_type,
            retention_days=retention_days,
            max_backups=max_backups,
            source_paths=source_paths or [],
            exclude_patterns=exclude_patterns or [],
            is_active=True,
            created_at=time.time()
        )
        self.policies[policy_id] = policy
        self._save()
        return policy_id

    def run_policy(self, policy_id: str) -> List[str]:
        """执行备份策略"""
        if policy_id not in self.policies:
            return []

        policy = self.policies[policy_id]
        backup_ids = []

        for source_path in policy.source_paths:
            backup_id = self.create_backup(
                source_path=source_path,
                backup_type=policy.backup_type,
                description=f"策略 {policy.name} 自动备份",
                tags=["auto", policy.name]
            )
            backup_ids.append(backup_id)

        policy.last_run = time.time()
        self._save()
        return backup_ids

    def cleanup_expired(self) -> int:
        """清理过期备份"""
        now = time.time()
        expired = []

        for backup_id, record in self.backup_records.items():
            if record.expires_at > 0 and record.expires_at < now:
                expired.append(backup_id)

        # 检查策略保留期
        for policy in self.policies.values():
            policy_backups = [
                (bid, br) for bid, br in self.backup_records.items()
                if policy.name in br.tags
            ]
            policy_backups.sort(key=lambda x: x[1].created_at, reverse=True)

            if len(policy_backups) > policy.max_backups:
                for bid, _ in policy_backups[policy.max_backups:]:
                    if bid not in expired:
                        expired.append(bid)

            cutoff = now - policy.retention_days * 86400
            for bid, br in policy_backups:
                if br.created_at < cutoff and bid not in expired:
                    expired.append(bid)

        # 删除过期备份
        for backup_id in expired:
            record = self.backup_records[backup_id]
            if os.path.exists(record.backup_path):
                try:
                    os.remove(record.backup_path)
                except OSError:
                    pass
            record.status = BackupStatus.EXPIRED.value

        self._save()
        return len(expired)

    def get_backup_history(self, source_path: str = "",
                           backup_type: str = "",
                           status: str = "",
                           limit: int = 50) -> List[Dict[str, Any]]:
        """获取备份历史"""
        records = list(self.backup_records.values())

        if source_path:
            records = [r for r in records if r.source_path == source_path]
        if backup_type:
            records = [r for r in records if r.backup_type == backup_type]
        if status:
            records = [r for r in records if r.status == status]

        records.sort(key=lambda x: x.created_at, reverse=True)
        return [asdict(r) for r in records[:limit]]

    def get_restore_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取恢复历史"""
        records = sorted(self.restore_records, key=lambda x: x.created_at, reverse=True)
        return [asdict(r) for r in records[:limit]]

    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """验证备份完整性"""
        if backup_id not in self.backup_records:
            return {"valid": False, "error": "备份不存在"}

        record = self.backup_records[backup_id]

        if not os.path.exists(record.backup_path):
            return {"valid": False, "error": "备份文件不存在"}

        # 检查校验和
        current_checksum = self._calculate_checksum(record.backup_path)
        if record.checksum and current_checksum != record.checksum:
            return {"valid": False, "error": "校验和不匹配"}

        # 检查ZIP完整性
        try:
            with zipfile.ZipFile(record.backup_path, 'r') as zf:
                bad_files = zf.testzip()
                if bad_files:
                    return {"valid": False, "error": f"文件损坏: {bad_files}"}
        except zipfile.BadZipFile:
            return {"valid": False, "error": "无效的ZIP文件"}

        return {
            "valid": True,
            "backup_id": backup_id,
            "size_bytes": record.size_bytes,
            "file_count": record.file_count,
            "checksum": current_checksum
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        for bid, record in self.backup_records.items():
            backups.append({
                "backup_id": bid,
                "type": record.backup_type,
                "source": record.source_path,
                "status": record.status,
                "size": record.size_bytes,
                "files": record.file_count,
                "created": record.created_at,
                "description": record.description
            })
        return sorted(backups, key=lambda x: x["created"], reverse=True)

    def generate_report(self) -> Dict[str, Any]:
        """生成备份报告"""
        total_backups = len(self.backup_records)
        completed = sum(1 for r in self.backup_records.values() if r.status == BackupStatus.COMPLETED.value)
        failed = sum(1 for r in self.backup_records.values() if r.status == BackupStatus.FAILED.value)
        total_size = sum(r.size_bytes for r in self.backup_records.values())

        type_counts = defaultdict(int)
        for r in self.backup_records.values():
            type_counts[r.backup_type] += 1

        return {
            "total_backups": total_backups,
            "completed_backups": completed,
            "failed_backups": failed,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "backup_type_distribution": dict(type_counts),
            "total_restores": len(self.restore_records),
            "policies_count": len(self.policies),
            "active_policies": sum(1 for p in self.policies.values() if p.is_active)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "backups_count": len(self.backup_records),
            "restores_count": len(self.restore_records),
            "policies_count": len(self.policies),
            "schedules_count": len(self.schedules),
            "tracked_files": len(self.file_hashes)
        }


if __name__ == "__main__":
    engine = BackupRecoveryEngine()
    print("=== 备份恢复系统测试 ===")

    # 创建测试目录
    test_dir = "test_data"
    os.makedirs(test_dir, exist_ok=True)
    for i in range(5):
        with open(os.path.join(test_dir, f"file_{i}.txt"), "w") as f:
            f.write(f"测试数据 {i}\n" * 100)

    # 全量备份
    backup1 = engine.create_backup(test_dir, "full", "初始全量备份", ["test"])
    print(f"全量备份: {backup1}")

    # 修改文件
    with open(os.path.join(test_dir, "file_0.txt"), "w") as f:
        f.write("修改后的数据\n")

    # 增量备份
    backup2 = engine.create_backup(test_dir, "incremental", "增量备份", ["test"], backup1)
    print(f"增量备份: {backup2}")

    # 创建策略
    policy_id = engine.create_policy("每日备份", "incremental", retention_days=7, max_backups=5, source_paths=[test_dir])
    print(f"备份策略: {policy_id}")

    # 验证备份
    verify = engine.verify_backup(backup1)
    print(f"验证备份: {verify}")

    # 恢复备份
    restore_dir = "restored_data"
    restore_id = engine.restore_backup(backup1, restore_dir, overwrite=True)
    print(f"恢复操作: {restore_id}")

    # 备份列表
    backups = engine.list_backups()
    print(f"备份列表: {len(backups)} 个备份")

    # 报告
    report = engine.generate_report()
    print(f"\n备份报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    # 清理
    shutil.rmtree(test_dir, ignore_errors=True)
    shutil.rmtree(restore_dir, ignore_errors=True)

    print("\n测试完成!")
