"""限流器 - 令牌桶、滑动窗口、分布式限流"""

import json
import os
import time
import hashlib
import threading
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any


class LimiterType(Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimiter:
    limiter_id: str
    name: str
    limiter_type: str = "token_bucket"
    max_rate: float = 100  # 请求/秒
    burst_size: int = 200
    window_seconds: int = 60
    is_active: bool = True
    created_at: float = 0.0


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    retry_after: float = 0.0
    limiter_name: str = ""


class RateLimiterEngine:
    """限流器引擎"""

    def __init__(self, storage_dir: str = "data/ratelimit"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.limiters: Dict[str, RateLimiter] = {}
        # 令牌桶状态
        self.token_buckets: Dict[str, Dict[str, float]] = {}
        # 滑动窗口状态
        self.sliding_windows: Dict[str, List[float]] = {}
        # 固定窗口状态
        self.fixed_windows: Dict[str, Dict[str, Any]] = {}
        # 统计
        self.stats = {"total_requests": 0, "allowed": 0, "rejected": 0}

        self._lock = threading.Lock()
        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "ratelimit_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("limiters", {}).items():
                    self.limiters[k] = RateLimiter(**v)
                self.stats = data.get("stats", self.stats)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "ratelimit_data.json")
        data = {
            "limiters": {k: asdict(v) for k, v in self.limiters.items()},
            "stats": self.stats,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_limiter(self, name: str, max_rate: float = 100,
                       burst_size: int = 200, window_seconds: int = 60,
                       limiter_type: str = "token_bucket") -> str:
        """创建限流器"""
        limiter_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        limiter = RateLimiter(
            limiter_id=limiter_id, name=name,
            limiter_type=limiter_type,
            max_rate=max_rate, burst_size=burst_size,
            window_seconds=window_seconds,
            created_at=time.time(),
        )
        self.limiters[limiter_id] = limiter
        self._save()
        return limiter_id

    def check(self, limiter_id: str, key: str = "global",
              tokens: int = 1) -> RateLimitResult:
        """检查限流"""
        if limiter_id not in self.limiters:
            return RateLimitResult(allowed=True, remaining=999, limit=999)

        limiter = self.limiters[limiter_id]
        self.stats["total_requests"] += 1

        with self._lock:
            if limiter.limiter_type == LimiterType.TOKEN_BUCKET.value:
                result = self._check_token_bucket(limiter, key, tokens)
            elif limiter.limiter_type == LimiterType.SLIDING_WINDOW.value:
                result = self._check_sliding_window(limiter, key)
            elif limiter.limiter_type == LimiterType.FIXED_WINDOW.value:
                result = self._check_fixed_window(limiter, key)
            else:
                result = self._check_token_bucket(limiter, key, tokens)

        if result.allowed:
            self.stats["allowed"] += 1
        else:
            self.stats["rejected"] += 1

        return result

    def _check_token_bucket(self, limiter: RateLimiter, key: str,
                            tokens: int) -> RateLimitResult:
        """令牌桶"""
        bucket_key = f"{limiter.limiter_id}:{key}"
        now = time.time()

        if bucket_key not in self.token_buckets:
            self.token_buckets[bucket_key] = {
                "tokens": limiter.burst_size,
                "last_update": now,
            }

        bucket = self.token_buckets[bucket_key]
        elapsed = now - bucket["last_update"]
        bucket["tokens"] = min(
            limiter.burst_size,
            bucket["tokens"] + elapsed * limiter.max_rate
        )
        bucket["last_update"] = now

        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket["tokens"]),
                limit=limiter.burst_size,
                limiter_name=limiter.name,
            )
        else:
            retry_after = (tokens - bucket["tokens"]) / limiter.max_rate
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limiter.burst_size,
                retry_after=retry_after,
                limiter_name=limiter.name,
            )

    def _check_sliding_window(self, limiter: RateLimiter, key: str) -> RateLimitResult:
        """滑动窗口"""
        window_key = f"{limiter.limiter_id}:{key}"
        now = time.time()
        window_start = now - limiter.window_seconds

        if window_key not in self.sliding_windows:
            self.sliding_windows[window_key] = []

        # 清理过期
        self.sliding_windows[window_key] = [
            t for t in self.sliding_windows[window_key] if t > window_start
        ]

        current = len(self.sliding_windows[window_key])
        max_requests = int(limiter.max_rate * limiter.window_seconds)

        if current < max_requests:
            self.sliding_windows[window_key].append(now)
            return RateLimitResult(
                allowed=True,
                remaining=max_requests - current - 1,
                limit=max_requests,
                limiter_name=limiter.name,
            )
        else:
            oldest = self.sliding_windows[window_key][0]
            retry_after = oldest + limiter.window_seconds - now
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=max_requests,
                retry_after=retry_after,
                limiter_name=limiter.name,
            )

    def _check_fixed_window(self, limiter: RateLimiter, key: str) -> RateLimitResult:
        """固定窗口"""
        window_key = f"{limiter.limiter_id}:{key}"
        now = time.time()
        window_id = int(now / limiter.window_seconds)
        max_requests = int(limiter.max_rate * limiter.window_seconds)

        if window_key not in self.fixed_windows:
            self.fixed_windows[window_key] = {"window_id": window_id, "count": 0}

        window = self.fixed_windows[window_key]
        if window["window_id"] != window_id:
            window["window_id"] = window_id
            window["count"] = 0

        if window["count"] < max_requests:
            window["count"] += 1
            return RateLimitResult(
                allowed=True,
                remaining=max_requests - window["count"],
                limit=max_requests,
                limiter_name=limiter.name,
            )
        else:
            retry_after = (window_id + 1) * limiter.window_seconds - now
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=max_requests,
                retry_after=retry_after,
                limiter_name=limiter.name,
            )

    def reset(self, limiter_id: str, key: str = "global"):
        """重置限流状态"""
        bucket_key = f"{limiter_id}:{key}"
        self.token_buckets.pop(bucket_key, None)
        self.sliding_windows.pop(bucket_key, None)
        self.fixed_windows.pop(bucket_key, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "limiters_count": len(self.limiters),
            "total_requests": self.stats["total_requests"],
            "allowed": self.stats["allowed"],
            "rejected": self.stats["rejected"],
            "rejection_rate": round(self.stats["rejected"] / max(self.stats["total_requests"], 1), 4),
        }

    def generate_report(self) -> Dict[str, Any]:
        return {
            "total_limiters": len(self.limiters),
            "stats": self.stats,
        }


if __name__ == "__main__":
    print("=== 限流器测试 ===")
    engine = RateLimiterEngine()

    # 令牌桶
    tb = engine.create_limiter("API限流", max_rate=10, burst_size=20)
    print(f"令牌桶: {tb}")

    # 滑动窗口
    sw = engine.create_limiter("用户限流", max_rate=5, window_seconds=10,
                                limiter_type="sliding_window")
    print(f"滑动窗口: {sw}")

    # 测试令牌桶
    print("\n令牌桶测试:")
    for i in range(25):
        result = engine.check(tb, "client_1")
        if not result.allowed:
            print(f"  请求 {i+1}: 拒绝 (剩余: {result.remaining})")
            break
        if i % 5 == 0:
            print(f"  请求 {i+1}: 允许 (剩余: {result.remaining})")

    # 测试滑动窗口
    print("\n滑动窗口测试:")
    for i in range(8):
        result = engine.check(sw, "user_1")
        print(f"  请求 {i+1}: {'允许' if result.allowed else '拒绝'} (剩余: {result.remaining})")

    report = engine.generate_report()
    print(f"\n限流报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
