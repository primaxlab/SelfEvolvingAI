"""API网关系统 - 路由管理、限流、认证、请求转发"""

import json
import os
import time
import hashlib
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import threading


class HttpMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class RateLimitStrategy(Enum):
    """限流策略"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    IP_HASH = "ip_hash"


@dataclass
class Route:
    """路由规则"""
    route_id: str
    path: str
    method: str = "GET"
    target_service: str = ""
    target_url: str = ""
    strip_prefix: bool = False
    rate_limit: int = 0  # 请求/秒
    auth_required: bool = False
    auth_type: str = "none"
    timeout: int = 30
    retry_count: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    is_active: bool = True
    created_at: float = 0.0


@dataclass
class RateLimitRule:
    """限流规则"""
    rule_id: str
    name: str
    strategy: str = "fixed_window"
    max_requests: int = 100
    window_seconds: int = 60
    target: str = "global"  # "global", "ip", "user", "route"
    target_value: str = ""
    is_active: bool = True


@dataclass
class ApiKey:
    """API密钥"""
    key_id: str
    key_hash: str
    name: str = ""
    owner: str = ""
    permissions: List[str] = field(default_factory=list)
    rate_limit: int = 0
    is_active: bool = True
    created_at: float = 0.0
    expires_at: float = 0.0
    last_used: float = 0.0
    usage_count: int = 0


@dataclass
class RequestLog:
    """请求日志"""
    log_id: str
    timestamp: float
    method: str
    path: str
    status_code: int = 0
    response_time: float = 0.0
    client_ip: str = ""
    user_agent: str = ""
    api_key_id: str = ""
    route_id: str = ""
    error: str = ""


@dataclass
class UpstreamService:
    """上游服务"""
    service_id: str
    name: str
    url: str
    weight: int = 1
    is_healthy: bool = True
    current_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_health_check: float = 0.0


class APIGatewayEngine:
    """API网关引擎"""

    def __init__(self, storage_dir: str = "data/gateway"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.routes: Dict[str, Route] = {}
        self.rate_limit_rules: Dict[str, RateLimitRule] = {}
        self.api_keys: Dict[str, ApiKey] = {}
        self.request_logs: List[RequestLog] = []
        self.upstream_services: Dict[str, UpstreamService] = {}

        # 限流计数器
        self.rate_counters: Dict[str, List[float]] = defaultdict(list)
        self.token_buckets: Dict[str, Dict[str, float]] = {}

        # 统计
        self.total_requests: int = 0
        self.total_errors: int = 0

        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "gateway_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("routes", {}).items():
                    self.routes[k] = Route(**v)
                for k, v in data.get("rate_limit_rules", {}).items():
                    self.rate_limit_rules[k] = RateLimitRule(**v)
                for k, v in data.get("api_keys", {}).items():
                    self.api_keys[k] = ApiKey(**v)
                self.request_logs = [RequestLog(**l) for l in data.get("request_logs", [])]
                for k, v in data.get("upstream_services", {}).items():
                    self.upstream_services[k] = UpstreamService(**v)
                self.total_requests = data.get("total_requests", 0)
                self.total_errors = data.get("total_errors", 0)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "gateway_data.json")
        data = {
            "routes": {k: asdict(v) for k, v in self.routes.items()},
            "rate_limit_rules": {k: asdict(v) for k, v in self.rate_limit_rules.items()},
            "api_keys": {k: asdict(v) for k, v in self.api_keys.items()},
            "request_logs": [asdict(l) for l in self.request_logs[-10000:]],
            "upstream_services": {k: asdict(v) for k, v in self.upstream_services.items()},
            "total_requests": self.total_requests,
            "total_errors": self.total_errors
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_route(self, path: str, target_service: str, method: str = "GET",
                  strip_prefix: bool = False, rate_limit: int = 0,
                  auth_required: bool = False, timeout: int = 30) -> str:
        """添加路由"""
        route_id = hashlib.md5(f"{method}:{path}_{time.time()}".encode()).hexdigest()[:12]
        route = Route(
            route_id=route_id,
            path=path,
            method=method,
            target_service=target_service,
            strip_prefix=strip_prefix,
            rate_limit=rate_limit,
            auth_required=auth_required,
            timeout=timeout,
            is_active=True,
            created_at=time.time()
        )
        self.routes[route_id] = route
        self._save()
        return route_id

    def match_route(self, path: str, method: str = "GET") -> Optional[Route]:
        """匹配路由"""
        for route in self.routes.values():
            if not route.is_active:
                continue

            if route.method != method and route.method != "*":
                continue

            if self._path_match(route.path, path):
                return route

        return None

    def _path_match(self, pattern: str, path: str) -> bool:
        """路径匹配"""
        # 简单的通配符匹配
        if pattern == path:
            return True

        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])

        if "*" in pattern:
            regex = pattern.replace("*", "[^/]*")
            return bool(re.match(f"^{regex}$", path))

        return False

    def create_api_key(self, name: str, owner: str = "",
                       permissions: List[str] = None,
                       rate_limit: int = 0,
                       expires_in: int = 0) -> Tuple[str, str]:
        """创建API密钥"""
        key_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        raw_key = hashlib.sha256(f"{key_id}_{time.time()}".encode()).hexdigest()
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            owner=owner,
            permissions=permissions or ["*"],
            rate_limit=rate_limit,
            is_active=True,
            created_at=time.time(),
            expires_at=time.time() + expires_in if expires_in > 0 else 0
        )

        self.api_keys[key_id] = api_key
        self._save()
        return key_id, raw_key

    def validate_api_key(self, raw_key: str) -> Optional[ApiKey]:
        """验证API密钥"""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        for api_key in self.api_keys.values():
            if api_key.key_hash == key_hash and api_key.is_active:
                if api_key.expires_at > 0 and api_key.expires_at < time.time():
                    return None
                api_key.last_used = time.time()
                api_key.usage_count += 1
                return api_key

        return None

    def add_rate_limit_rule(self, name: str, max_requests: int,
                            window_seconds: int = 60,
                            strategy: str = "fixed_window",
                            target: str = "global") -> str:
        """添加限流规则"""
        rule_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        rule = RateLimitRule(
            rule_id=rule_id,
            name=name,
            strategy=strategy,
            max_requests=max_requests,
            window_seconds=window_seconds,
            target=target,
            is_active=True
        )
        self.rate_limit_rules[rule_id] = rule
        self._save()
        return rule_id

    def check_rate_limit(self, key: str, rule_id: str = "") -> Dict[str, Any]:
        """检查限流"""
        rules = []
        if rule_id:
            if rule_id in self.rate_limit_rules:
                rules.append(self.rate_limit_rules[rule_id])
        else:
            rules = [r for r in self.rate_limit_rules.values() if r.is_active]

        for rule in rules:
            counter_key = f"{rule.rule_id}:{key}"

            if rule.strategy == RateLimitStrategy.FIXED_WINDOW.value:
                now = time.time()
                window_start = now - rule.window_seconds

                with self._lock:
                    self.rate_counters[counter_key] = [
                        t for t in self.rate_counters[counter_key] if t > window_start
                    ]

                    if len(self.rate_counters[counter_key]) >= rule.max_requests:
                        return {
                            "allowed": False,
                            "rule": rule.name,
                            "limit": rule.max_requests,
                            "remaining": 0,
                            "reset": window_start + rule.window_seconds
                        }

                    self.rate_counters[counter_key].append(now)

                    return {
                        "allowed": True,
                        "rule": rule.name,
                        "limit": rule.max_requests,
                        "remaining": rule.max_requests - len(self.rate_counters[counter_key]),
                        "reset": window_start + rule.window_seconds
                    }

            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET.value:
                with self._lock:
                    if counter_key not in self.token_buckets:
                        self.token_buckets[counter_key] = {
                            "tokens": rule.max_requests,
                            "last_update": time.time()
                        }

                    bucket = self.token_buckets[counter_key]
                    now = time.time()
                    elapsed = now - bucket["last_update"]
                    bucket["tokens"] = min(
                        rule.max_requests,
                        bucket["tokens"] + elapsed * (rule.max_requests / rule.window_seconds)
                    )
                    bucket["last_update"] = now

                    if bucket["tokens"] >= 1:
                        bucket["tokens"] -= 1
                        return {
                            "allowed": True,
                            "rule": rule.name,
                            "remaining": int(bucket["tokens"])
                        }
                    else:
                        return {
                            "allowed": False,
                            "rule": rule.name,
                            "remaining": 0
                        }

        return {"allowed": True}

    def register_upstream(self, name: str, url: str, weight: int = 1) -> str:
        """注册上游服务"""
        service_id = hashlib.md5(f"{name}_{url}".encode()).hexdigest()[:12]
        service = UpstreamService(
            service_id=service_id,
            name=name,
            url=url,
            weight=weight,
            is_healthy=True
        )
        self.upstream_services[service_id] = service
        self._save()
        return service_id

    def select_upstream(self, service_name: str,
                        strategy: str = "round_robin") -> Optional[UpstreamService]:
        """选择上游服务"""
        services = [
            s for s in self.upstream_services.values()
            if s.name == service_name and s.is_healthy
        ]

        if not services:
            return None

        if strategy == LoadBalanceStrategy.ROUND_ROBIN.value:
            # 简单轮询
            return min(services, key=lambda s: s.total_requests)

        elif strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN.value:
            # 加权轮询
            import random
            weights = [s.weight for s in services]
            return random.choices(services, weights=weights, k=1)[0]

        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS.value:
            return min(services, key=lambda s: s.current_connections)

        elif strategy == LoadBalanceStrategy.RANDOM.value:
            import random
            return random.choice(services)

        return services[0]

    def log_request(self, method: str, path: str, status_code: int,
                    response_time: float, client_ip: str = "",
                    api_key_id: str = "", route_id: str = "",
                    error: str = "") -> str:
        """记录请求"""
        log_id = hashlib.md5(f"{method}_{path}_{time.time()}".encode()).hexdigest()[:12]
        log = RequestLog(
            log_id=log_id,
            timestamp=time.time(),
            method=method,
            path=path,
            status_code=status_code,
            response_time=response_time,
            client_ip=client_ip,
            api_key_id=api_key_id,
            route_id=route_id,
            error=error
        )

        self.request_logs.append(log)
        self.total_requests += 1

        if status_code >= 400:
            self.total_errors += 1

        self._save()
        return log_id

    def get_request_stats(self, hours: int = 24) -> Dict[str, Any]:
        """获取请求统计"""
        cutoff = time.time() - hours * 3600
        recent = [l for l in self.request_logs if l.timestamp > cutoff]

        if not recent:
            return {"total": 0}

        status_counts = defaultdict(int)
        method_counts = defaultdict(int)
        path_counts = defaultdict(int)
        response_times = []

        for log in recent:
            status_counts[log.status_code // 100] += 1
            method_counts[log.method] += 1
            path_counts[log.path] += 1
            response_times.append(log.response_time)

        return {
            "total_requests": len(recent),
            "total_errors": sum(1 for l in recent if l.status_code >= 400),
            "error_rate": sum(1 for l in recent if l.status_code >= 400) / len(recent),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "status_distribution": dict(status_counts),
            "method_distribution": dict(method_counts),
            "top_paths": dict(sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }

    def get_route_stats(self) -> List[Dict[str, Any]]:
        """获取路由统计"""
        route_stats = []

        for route in self.routes.values():
            route_logs = [l for l in self.request_logs if l.route_id == route.route_id]
            if route_logs:
                response_times = [l.response_time for l in route_logs]
                errors = sum(1 for l in route_logs if l.status_code >= 400)
                route_stats.append({
                    "route_id": route.route_id,
                    "path": route.path,
                    "method": route.method,
                    "total_requests": len(route_logs),
                    "error_count": errors,
                    "error_rate": errors / len(route_logs),
                    "avg_response_time": sum(response_times) / len(response_times)
                })

        return sorted(route_stats, key=lambda x: x["total_requests"], reverse=True)

    def health_check_upstream(self, service_id: str) -> bool:
        """健康检查上游服务"""
        if service_id not in self.upstream_services:
            return False

        service = self.upstream_services[service_id]
        # 简化实现 - 实际应发送HTTP请求
        service.last_health_check = time.time()
        return service.is_healthy

    def generate_report(self) -> Dict[str, Any]:
        """生成网关报告"""
        request_stats = self.get_request_stats(24)

        return {
            "total_routes": len(self.routes),
            "active_routes": sum(1 for r in self.routes.values() if r.is_active),
            "total_api_keys": len(self.api_keys),
            "active_api_keys": sum(1 for k in self.api_keys.values() if k.is_active),
            "total_upstream_services": len(self.upstream_services),
            "healthy_upstream": sum(1 for s in self.upstream_services.values() if s.is_healthy),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "request_stats_24h": request_stats,
            "rate_limit_rules": len(self.rate_limit_rules)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "routes_count": len(self.routes),
            "api_keys_count": len(self.api_keys),
            "request_logs_count": len(self.request_logs),
            "upstream_services_count": len(self.upstream_services),
            "rate_limit_rules_count": len(self.rate_limit_rules),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors
        }


if __name__ == "__main__":
    engine = APIGatewayEngine()
    print("=== API网关系统测试 ===")

    # 添加路由
    r1 = engine.add_route("/api/v1/users", "user_service", "GET")
    r2 = engine.add_route("/api/v1/users", "user_service", "POST")
    r3 = engine.add_route("/api/v1/orders/*", "order_service", "*")
    r4 = engine.add_route("/api/v1/products", "product_service", "GET", rate_limit=100)
    print(f"添加路由: {r1}, {r2}, {r3}, {r4}")

    # 路由匹配
    route = engine.match_route("/api/v1/users", "GET")
    print(f"匹配路由: {route.route_id if route else 'None'}")

    route = engine.match_route("/api/v1/orders/123", "DELETE")
    print(f"匹配路由: {route.route_id if route else 'None'}")

    # 创建API密钥
    key_id, raw_key = engine.create_api_key("测试密钥", "测试用户", ["read", "write"], 1000)
    print(f"API密钥: {key_id}")

    # 验证密钥
    valid_key = engine.validate_api_key(raw_key)
    print(f"密钥验证: {'有效' if valid_key else '无效'}")

    # 限流规则
    rule_id = engine.add_rate_limit_rule("全局限流", 100, 60, "fixed_window", "global")
    print(f"限流规则: {rule_id}")

    # 检查限流
    for i in range(5):
        result = engine.check_rate_limit("client_1", rule_id)
        print(f"限流检查 {i+1}: {result['allowed']}")

    # 上游服务
    s1 = engine.register_upstream("user_service", "http://localhost:8001", 3)
    s2 = engine.register_upstream("user_service", "http://localhost:8002", 1)
    print(f"上游服务: {s1}, {s2}")

    # 负载均衡
    selected = engine.select_upstream("user_service", "weighted_round_robin")
    print(f"选择上游: {selected.url if selected else 'None'}")

    # 记录请求
    for i in range(10):
        engine.log_request("GET", "/api/v1/users", 200, 50 + i * 10, "192.168.1.1", route_id=r1)
    engine.log_request("POST", "/api/v1/users", 500, 150, "192.168.1.2", route_id=r2, error="内部错误")

    # 请求统计
    stats = engine.get_request_stats()
    print(f"请求统计: {stats}")

    # 报告
    report = engine.generate_report()
    print(f"\n网关报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    print("\n测试完成!")
