"""缓存管理 - LRU/LFU缓存、分布式缓存、缓存失效策略"""

import json
import os
import time
import hashlib
import threading
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import OrderedDict


class EvictionPolicy(Enum):
    """淘汰策略"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    RANDOM = "random"


class CacheLevel(Enum):
    """缓存级别"""
    L1 = "l1"  # 内存缓存
    L2 = "l2"  # 磁盘缓存
    L3 = "l3"  # 分布式缓存


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    ttl: float = 0  # 0=永不过期
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    cache_level: str = "l1"


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size: int = 0
    entry_count: int = 0


class LRUCache:
    """LRU缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self.cache:
                self.stats.misses += 1
                return None

            entry = self.cache[key]

            # 检查TTL
            if entry.ttl > 0 and (time.time() - entry.created_at) > entry.ttl:
                del self.cache[key]
                self.stats.misses += 1
                return None

            # 移到末尾(最近使用)
            self.cache.move_to_end(key)
            entry.accessed_at = time.time()
            entry.access_count += 1
            self.stats.hits += 1
            return entry.value

    def put(self, key: str, value: Any, ttl: float = 0,
            tags: List[str] = None) -> bool:
        """设置缓存"""
        with self._lock:
            now = time.time()

            if key in self.cache:
                self.cache.move_to_end(key)
                entry = self.cache[key]
                entry.value = value
                entry.accessed_at = now
                entry.ttl = ttl or self.default_ttl
                if tags:
                    entry.tags = tags
                return True

            # 淘汰旧条目
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
                self.stats.evictions += 1

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                access_count=0,
                ttl=ttl or self.default_ttl,
                tags=tags or [],
            )
            self.cache[key] = entry
            self.stats.entry_count = len(self.cache)
            return True

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.entry_count = len(self.cache)
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.stats = CacheStats()

    def get_by_tag(self, tag: str) -> List[Any]:
        """按标签获取"""
        results = []
        for entry in self.cache.values():
            if tag in entry.tags:
                results.append(entry.value)
        return results

    def invalidate_by_tag(self, tag: str) -> int:
        """按标签失效"""
        with self._lock:
            keys_to_delete = [k for k, v in self.cache.items() if tag in v.tags]
            for key in keys_to_delete:
                del self.cache[key]
            self.stats.entry_count = len(self.cache)
            return len(keys_to_delete)


class LFUCache:
    """LFU缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.freq: Dict[str, int] = {}
        self.stats = CacheStats()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self.cache:
                self.stats.misses += 1
                return None

            entry = self.cache[key]
            if entry.ttl > 0 and (time.time() - entry.created_at) > entry.ttl:
                self._remove(key)
                self.stats.misses += 1
                return None

            entry.accessed_at = time.time()
            entry.access_count += 1
            self.freq[key] = self.freq.get(key, 0) + 1
            self.stats.hits += 1
            return entry.value

    def put(self, key: str, value: Any, ttl: float = 0,
            tags: List[str] = None) -> bool:
        with self._lock:
            now = time.time()

            if key in self.cache:
                self.cache[key].value = value
                self.cache[key].accessed_at = now
                return True

            while len(self.cache) >= self.max_size:
                self._evict_lfu()

            self.cache[key] = CacheEntry(
                key=key, value=value, created_at=now,
                accessed_at=now, ttl=ttl or self.default_ttl,
                tags=tags or [],
            )
            self.freq[key] = 0
            self.stats.entry_count = len(self.cache)
            return True

    def _evict_lfu(self):
        if not self.freq:
            return
        min_key = min(self.freq, key=self.freq.get)
        self._remove(min_key)
        self.stats.evictions += 1

    def _remove(self, key: str):
        self.cache.pop(key, None)
        self.freq.pop(key, None)
        self.stats.entry_count = len(self.cache)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self.cache:
                self._remove(key)
                return True
            return False

    def clear(self):
        with self._lock:
            self.cache.clear()
            self.freq.clear()
            self.stats = CacheStats()


class CacheManager:
    """缓存管理引擎"""

    def __init__(self, storage_dir: str = "data/cache", max_size: int = 10000):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.caches: Dict[str, Any] = {}
        self.default_policy = EvictionPolicy.LRU.value
        self.max_size = max_size
        self.global_stats = {"total_hits": 0, "total_misses": 0, "total_evictions": 0}

        # 创建默认缓存
        self.create_cache("default", EvictionPolicy.LRU.value, max_size)
        self.create_cache("lfu", EvictionPolicy.LFU.value, max_size // 2)

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "cache_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.global_stats = data.get("global_stats", self.global_stats)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "cache_data.json")
        data = {"global_stats": self.global_stats}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_cache(self, name: str, policy: str = "lru",
                     max_size: int = 1000, default_ttl: float = 0) -> bool:
        """创建缓存池"""
        if policy == EvictionPolicy.LRU.value:
            self.caches[name] = LRUCache(max_size, default_ttl)
        elif policy == EvictionPolicy.LFU.value:
            self.caches[name] = LFUCache(max_size, default_ttl)
        else:
            self.caches[name] = LRUCache(max_size, default_ttl)
        return True

    def get(self, key: str, cache_name: str = "default") -> Optional[Any]:
        """获取"""
        cache = self.caches.get(cache_name)
        if not cache:
            return None
        result = cache.get(key)
        if result is not None:
            self.global_stats["total_hits"] += 1
        else:
            self.global_stats["total_misses"] += 1
        return result

    def put(self, key: str, value: Any, cache_name: str = "default",
            ttl: float = 0, tags: List[str] = None) -> bool:
        """设置"""
        cache = self.caches.get(cache_name)
        if not cache:
            return False
        return cache.put(key, value, ttl, tags)

    def delete(self, key: str, cache_name: str = "default") -> bool:
        """删除"""
        cache = self.caches.get(cache_name)
        if not cache:
            return False
        return cache.delete(key)

    def invalidate_by_tag(self, tag: str, cache_name: str = "default") -> int:
        """按标签失效"""
        cache = self.caches.get(cache_name)
        if not cache:
            return 0
        if hasattr(cache, 'invalidate_by_tag'):
            return cache.invalidate_by_tag(tag)
        return 0

    def clear(self, cache_name: str = "default"):
        """清空"""
        cache = self.caches.get(cache_name)
        if cache:
            cache.clear()

    def clear_all(self):
        """清空所有缓存"""
        for cache in self.caches.values():
            cache.clear()

    def get_or_set(self, key: str, factory: Callable, cache_name: str = "default",
                   ttl: float = 0, tags: List[str] = None) -> Any:
        """获取或设置(缓存穿透保护)"""
        value = self.get(key, cache_name)
        if value is not None:
            return value
        value = factory()
        self.put(key, value, cache_name, ttl, tags)
        return value

    def get_stats(self, cache_name: str = "default") -> Dict[str, Any]:
        """获取统计"""
        cache = self.caches.get(cache_name)
        if not cache:
            return {}

        stats = cache.stats
        hit_rate = stats.hits / max(stats.hits + stats.misses, 1)

        return {
            "cache_name": cache_name,
            "hits": stats.hits,
            "misses": stats.misses,
            "hit_rate": round(hit_rate, 4),
            "evictions": stats.evictions,
            "entry_count": stats.entry_count,
        }

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        cache_stats = {}
        for name in self.caches:
            cache_stats[name] = self.get_stats(name)

        total_hits = sum(s.get("hits", 0) for s in cache_stats.values())
        total_misses = sum(s.get("misses", 0) for s in cache_stats.values())

        return {
            "total_caches": len(self.caches),
            "total_hits": total_hits,
            "total_misses": total_misses,
            "overall_hit_rate": round(total_hits / max(total_hits + total_misses, 1), 4),
            "cache_details": cache_stats,
            "global_stats": self.global_stats,
        }


if __name__ == "__main__":
    print("=== 缓存管理测试 ===")
    mgr = CacheManager()

    # LRU测试
    mgr.put("key1", "value1", tags=["user"])
    mgr.put("key2", "value2", tags=["user"])
    mgr.put("key3", "value3", tags=["data"])
    print(f"key1: {mgr.get('key1')}")
    print(f"key2: {mgr.get('key2')}")

    # 标签失效
    mgr.invalidate_by_tag("user")
    print(f"失效后key1: {mgr.get('key1')}")

    # get_or_set
    val = mgr.get_or_set("computed", lambda: 42 * 42)
    print(f"计算缓存: {val}")

    # 报告
    report = mgr.generate_report()
    print(f"\n缓存报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
