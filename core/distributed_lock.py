"""分布式锁 - 分布式锁、乐观锁、死锁检测"""

import json
import os
import time
import hashlib
import threading
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any


class LockType(Enum):
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    READ_WRITE = "read_write"


@dataclass
class Lock:
    lock_id: str
    resource: str
    owner: str
    lock_type: str = "exclusive"
    acquired_at: float = 0.0
    expires_at: float = 0.0
    ttl: float = 30.0
    is_reentrant: bool = True
    reentrant_count: int = 0


@dataclass
class OptimisticLock:
    resource: str
    version: int = 0
    updated_at: float = 0.0
    updated_by: str = ""


class DistributedLockEngine:
    """分布式锁引擎"""

    def __init__(self, storage_dir: str = "data/locks"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.locks: Dict[str, Lock] = {}
        self.optimistic_locks: Dict[str, OptimisticLock] = {}
        self.wait_queue: Dict[str, List[str]] = {}
        self.stats = {"acquired": 0, "released": 0, "expired": 0, "contended": 0}

        self._lock = threading.Lock()

    def acquire(self, resource: str, owner: str, ttl: float = 30.0,
                lock_type: str = "exclusive", timeout: float = 0) -> Optional[str]:
        """获取锁"""
        with self._lock:
            now = time.time()

            # 检查现有锁
            existing = self.locks.get(resource)
            if existing:
                # 检查是否过期
                if existing.expires_at > 0 and now > existing.expires_at:
                    self._release_lock(resource)
                    self.stats["expired"] += 1
                elif existing.owner == owner and existing.is_reentrant:
                    # 可重入
                    existing.reentrant_count += 1
                    existing.expires_at = now + ttl
                    return existing.lock_id
                elif existing.lock_type == "shared" and lock_type == "shared":
                    # 共享锁
                    pass
                else:
                    # 锁冲突
                    self.stats["contended"] += 1
                    if resource not in self.wait_queue:
                        self.wait_queue[resource] = []
                    if owner not in self.wait_queue[resource]:
                        self.wait_queue[resource].append(owner)
                    return None

            # 创建锁
            lock_id = hashlib.md5(f"{resource}_{owner}_{now}".encode()).hexdigest()[:12]
            lock = Lock(
                lock_id=lock_id,
                resource=resource,
                owner=owner,
                lock_type=lock_type,
                acquired_at=now,
                expires_at=now + ttl,
                ttl=ttl,
            )
            self.locks[resource] = lock
            self.stats["acquired"] += 1
            return lock_id

    def release(self, resource: str, owner: str) -> bool:
        """释放锁"""
        with self._lock:
            existing = self.locks.get(resource)
            if not existing or existing.owner != owner:
                return False

            if existing.is_reentrant and existing.reentrant_count > 0:
                existing.reentrant_count -= 1
                return True

            self._release_lock(resource)
            self.stats["released"] += 1
            return True

    def _release_lock(self, resource: str):
        """内部释放锁"""
        self.locks.pop(resource, None)

        # 唤醒等待队列
        if resource in self.wait_queue and self.wait_queue[resource]:
            self.wait_queue[resource].pop(0)

    def extend(self, resource: str, owner: str, additional_ttl: float = 30.0) -> bool:
        """延长锁"""
        existing = self.locks.get(resource)
        if existing and existing.owner == owner:
            existing.expires_at = time.time() + additional_ttl
            existing.ttl = additional_ttl
            return True
        return False

    def force_release(self, resource: str) -> bool:
        """强制释放"""
        if resource in self.locks:
            self._release_lock(resource)
            return True
        return False

    def is_locked(self, resource: str) -> bool:
        """检查是否锁定"""
        existing = self.locks.get(resource)
        if not existing:
            return False
        if existing.expires_at > 0 and time.time() > existing.expires_at:
            self._release_lock(resource)
            return False
        return True

    def get_lock_info(self, resource: str) -> Optional[Dict[str, Any]]:
        """获取锁信息"""
        existing = self.locks.get(resource)
        if existing:
            return asdict(existing)
        return None

    # 乐观锁
    def optimistic_acquire(self, resource: str, owner: str) -> int:
        """获取乐观锁版本号"""
        if resource not in self.optimistic_locks:
            self.optimistic_locks[resource] = OptimisticLock(resource=resource)
        return self.optimistic_locks[resource].version

    def optimistic_commit(self, resource: str, owner: str,
                          expected_version: int) -> bool:
        """乐观锁提交"""
        if resource not in self.optimistic_locks:
            return False

        lock = self.optimistic_locks[resource]
        if lock.version != expected_version:
            return False  # 版本冲突

        lock.version += 1
        lock.updated_at = time.time()
        lock.updated_by = owner
        return True

    def cleanup_expired(self) -> int:
        """清理过期锁"""
        now = time.time()
        expired = []
        for resource, lock in self.locks.items():
            if lock.expires_at > 0 and now > lock.expires_at:
                expired.append(resource)

        for resource in expired:
            self._release_lock(resource)
            self.stats["expired"] += 1

        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_locks": len(self.locks),
            "optimistic_resources": len(self.optimistic_locks),
            "stats": self.stats,
        }

    def generate_report(self) -> Dict[str, Any]:
        return {
            "active_locks": len(self.locks),
            "stats": self.stats,
        }


if __name__ == "__main__":
    print("=== 分布式锁测试 ===")
    engine = DistributedLockEngine()

    # 获取锁
    lock_id = engine.acquire("resource_1", "worker_1", ttl=60)
    print(f"获取锁: {lock_id}")

    # 检查
    print(f"是否锁定: {engine.is_locked('resource_1')}")
    print(f"锁信息: {engine.get_lock_info('resource_1')}")

    # 冲突
    lock2 = engine.acquire("resource_1", "worker_2")
    print(f"冲突获取: {lock2}")

    # 可重入
    lock3 = engine.acquire("resource_1", "worker_1")
    print(f"可重入: {lock3}")

    # 释放
    engine.release("resource_1", "worker_1")
    engine.release("resource_1", "worker_1")
    print(f"释放后是否锁定: {engine.is_locked('resource_1')}")

    # 乐观锁
    v = engine.optimistic_acquire("counter", "user_1")
    print(f"\n乐观锁版本: {v}")
    print(f"提交: {engine.optimistic_commit('counter', 'user_1', v)}")
    print(f"版本冲突: {engine.optimistic_commit('counter', 'user_2', v)}")

    report = engine.generate_report()
    print(f"\n锁报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
