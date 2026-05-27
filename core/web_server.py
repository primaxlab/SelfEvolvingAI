"""Web服务器 - 轻量HTTP服务器、中间件、静态文件"""

import json
import os
import time
import hashlib
import mimetypes
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import threading


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


@dataclass
class Request:
    request_id: str
    method: str = "GET"
    path: str = "/"
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    client_ip: str = ""
    timestamp: float = 0.0


@dataclass
class Response:
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    content_type: str = "application/json"


@dataclass
class Route:
    path: str
    method: str = "GET"
    handler_name: str = ""
    middleware: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class Middleware:
    name: str
    priority: int = 0
    is_active: bool = True


class WebServerEngine:
    """Web服务器引擎"""

    def __init__(self, storage_dir: str = "data/webserver", static_dir: str = "static"):
        self.storage_dir = storage_dir
        self.static_dir = static_dir
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)

        self.routes: Dict[str, Route] = {}
        self.handlers: Dict[str, Callable] = {}
        self.middleware: Dict[str, Middleware] = {}
        self.middleware_handlers: Dict[str, Callable] = {}
        self.request_log: List[Dict[str, Any]] = []
        self.stats = {"total_requests": 0, "errors": 0}

        self._register_default_middleware()

    def _register_default_middleware(self):
        self.middleware["cors"] = Middleware(name="cors", priority=100)
        self.middleware_handlers["cors"] = self._cors_middleware

        self.middleware["logging"] = Middleware(name="logging", priority=90)
        self.middleware_handlers["logging"] = self._logging_middleware

    def _cors_middleware(self, request: Request, response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    def _logging_middleware(self, request: Request, response: Response) -> Response:
        self.request_log.append({
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "timestamp": time.time(),
        })
        return response

    def add_route(self, path: str, method: str = "GET",
                  handler: Callable = None, handler_name: str = "",
                  middleware: List[str] = None) -> str:
        """添加路由"""
        route_key = f"{method}:{path}"
        route = Route(
            path=path, method=method,
            handler_name=handler_name,
            middleware=middleware or [],
        )
        self.routes[route_key] = route
        if handler:
            self.handlers[route_key] = handler
        return route_key

    def register_handler(self, name: str, handler: Callable):
        """注册处理器"""
        self.handlers[name] = handler

    def register_middleware(self, name: str, handler: Callable, priority: int = 0):
        """注册中间件"""
        self.middleware[name] = Middleware(name=name, priority=priority)
        self.middleware_handlers[name] = handler

    def handle_request(self, method: str, path: str,
                       headers: Dict[str, str] = None,
                       query_params: Dict[str, str] = None,
                       body: Any = None,
                       client_ip: str = "") -> Response:
        """处理请求"""
        request_id = hashlib.md5(f"{method}_{path}_{time.time()}".encode()).hexdigest()[:12]
        request = Request(
            request_id=request_id,
            method=method,
            path=path,
            headers=headers or {},
            query_params=query_params or {},
            body=body,
            client_ip=client_ip,
            timestamp=time.time(),
        )

        self.stats["total_requests"] += 1
        response = Response()

        # OPTIONS预检
        if method == "OPTIONS":
            response.status_code = 204
            response = self._apply_middleware(request, response)
            return response

        # 匹配路由
        route_key = f"{method}:{path}"
        route = self.routes.get(route_key)

        if not route:
            # 尝试模糊匹配
            for key, r in self.routes.items():
                if r.method == method and self._path_match(r.path, path):
                    route = r
                    route_key = key
                    break

        if not route:
            # 尝试静态文件
            static_response = self._serve_static(path)
            if static_response:
                return static_response

            response.status_code = 404
            response.body = {"error": "Not Found"}
            self.stats["errors"] += 1
        else:
            handler = self.handlers.get(route_key)
            if handler:
                try:
                    result = handler(request)
                    if isinstance(result, Response):
                        response = result
                    elif isinstance(result, dict):
                        response.body = result
                    else:
                        response.body = {"result": str(result)}
                except Exception as e:
                    response.status_code = 500
                    response.body = {"error": str(e)}
                    self.stats["errors"] += 1
            else:
                response.status_code = 500
                response.body = {"error": "Handler not found"}

        # 应用中间件
        response = self._apply_middleware(request, response)
        return response

    def _path_match(self, pattern: str, path: str) -> bool:
        if pattern == path:
            return True
        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])
        return False

    def _apply_middleware(self, request: Request, response: Response) -> Response:
        active_middleware = sorted(
            [m for m in self.middleware.values() if m.is_active],
            key=lambda x: x.priority,
            reverse=True,
        )
        for mw in active_middleware:
            handler = self.middleware_handlers.get(mw.name)
            if handler:
                try:
                    response = handler(request, response)
                except Exception:
                    pass
        return response

    def _serve_static(self, path: str) -> Optional[Response]:
        """静态文件服务"""
        if path == "/":
            path = "/index.html"

        file_path = os.path.join(self.static_dir, path.lstrip("/"))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                return Response(
                    status_code=200,
                    body=content,
                    content_type=content_type or "application/octet-stream",
                )
            except Exception:
                pass
        return None

    def get_request_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取请求日志"""
        return self.request_log[-limit:]

    def get_route_list(self) -> List[Dict[str, Any]]:
        """获取路由列表"""
        return [
            {"path": r.path, "method": r.method, "handler": r.handler_name}
            for r in self.routes.values()
        ]

    def generate_report(self) -> Dict[str, Any]:
        method_counts = defaultdict(int)
        for log in self.request_log:
            method_counts[log.get("method", "")] += 1

        return {
            "total_routes": len(self.routes),
            "total_requests": self.stats["total_requests"],
            "total_errors": self.stats["errors"],
            "method_distribution": dict(method_counts),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "routes_count": len(self.routes),
            "handlers_count": len(self.handlers),
            "middleware_count": len(self.middleware),
            "total_requests": self.stats["total_requests"],
        }


if __name__ == "__main__":
    print("=== Web服务器测试 ===")
    engine = WebServerEngine()

    # 添加路由
    engine.add_route("/api/hello", "GET", handler=lambda req: {"message": "Hello!"})
    engine.add_route("/api/users", "GET", handler=lambda req: {"users": ["Alice", "Bob"]})
    engine.add_route("/api/users", "POST", handler=lambda req: {"created": True, "data": req.body})
    engine.add_route("/api/health", "GET", handler=lambda req: {"status": "ok"})

    # 处理请求
    r1 = engine.handle_request("GET", "/api/hello")
    print(f"GET /api/hello: {r1.status_code} {r1.body}")

    r2 = engine.handle_request("POST", "/api/users", body={"name": "Charlie"})
    print(f"POST /api/users: {r2.status_code} {r2.body}")

    r3 = engine.handle_request("GET", "/api/notfound")
    print(f"GET /api/notfound: {r3.status_code}")

    r4 = engine.handle_request("OPTIONS", "/api/hello")
    print(f"OPTIONS: {r4.headers}")

    report = engine.generate_report()
    print(f"\n服务器报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
