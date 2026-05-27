"""
================================================================================
API服务器 - 基于Python标准库的轻量HTTP API
================================================================================

提供REST API接口，无需Flask/FastAPI依赖

启动: python api_server.py [--port 8000] [--host 0.0.0.0]
"""

import json
import os
import sys
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.evolution_loop import SelfEvolvingAI, create_evolution_ai


# 全局AI实例
ai: SelfEvolvingAI = None


class APIHandler(BaseHTTPRequestHandler):
    """API请求处理器"""

    def do_OPTIONS(self):
        """预检请求"""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """GET请求"""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        routes = {
            "/": self._handle_index,
            "/api/status": self._handle_status,
            "/api/modules": self._handle_modules,
            "/api/memory": self._handle_memory,
            "/api/knowledge": self._handle_knowledge,
            "/api/report": self._handle_report,
            "/api/health": self._handle_health,
            "/api/providers": self._handle_providers,
        }

        handler = routes.get(path)
        if handler:
            handler(query)
        else:
            self._json_response(404, {"error": "Not Found"})

    def do_POST(self):
        """POST请求"""
        path = urlparse(self.path).path
        body = self._read_body()

        routes = {
            "/api/chat": self._handle_chat,
            "/api/chat/stream": self._handle_chat_stream,
            "/api/learn": self._handle_learn,
            "/api/evolve": self._handle_evolve,
            "/api/goal": self._handle_goal,
            "/api/code": self._handle_code,
        }

        handler = routes.get(path)
        if handler:
            handler(body)
        else:
            self._json_response(404, {"error": "Not Found"})

    def _read_body(self) -> dict:
        """读取请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            raw = self.rfile.read(content_length)
            try:
                return json.loads(raw.decode('utf-8'))
            except json.JSONDecodeError:
                return {}
        return {}

    def _json_response(self, status: int, data: dict):
        """JSON响应"""
        self.send_response(status)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_cors_headers(self):
        """CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    # ==================== 路由处理 ====================

    def _handle_index(self, query=None):
        self._json_response(200, {
            "name": "SelfEvolvingAI API",
            "version": "4.0",
            "modules": 65,
            "endpoints": [
                "GET  /api/status",
                "GET  /api/modules",
                "GET  /api/memory",
                "GET  /api/knowledge",
                "GET  /api/report",
                "GET  /api/health",
                "GET  /api/providers",
                "POST /api/chat",
                "POST /api/chat/stream",
                "POST /api/learn",
                "POST /api/evolve",
                "POST /api/goal",
                "POST /api/code",
            ]
        })

    def _handle_status(self, query=None):
        self._json_response(200, ai.get_status())

    def _handle_modules(self, query=None):
        self._json_response(200, ai.get_all_module_stats())

    def _handle_memory(self, query=None):
        self._json_response(200, ai.memory.summarize())

    def _handle_knowledge(self, query=None):
        self._json_response(200, ai.knowledge_graph.get_graph_stats())

    def _handle_report(self, query=None):
        self._json_response(200, {"report": ai.generate_evolution_report()})

    def _handle_health(self, query=None):
        self._json_response(200, {
            "status": "healthy",
            "uptime": time.time(),
            "modules": ai.state.modules_loaded,
        })

    def _handle_providers(self, query=None):
        self._json_response(200, ai.llm.get_stats())

    def _handle_chat(self, body):
        user_input = body.get("message", "")
        provider = body.get("provider", "")
        stream = body.get("stream", False)

        if not user_input:
            self._json_response(400, {"error": "message is required"})
            return

        if stream:
            self._handle_chat_stream(body)
            return

        result = ai.process(user_input)
        self._json_response(200, {
            "response": result['answer'],
            "confidence": result['confidence'],
            "domain": result['domain'],
            "modules_used": result.get('modules_used', []),
            "model": result.get('model', ''),
            "provider": result.get('provider', ''),
            "latency": result.get('processing_time', 0),
        })

    def _handle_chat_stream(self, body):
        user_input = body.get("message", "")
        provider = body.get("provider", "")

        if not user_input:
            self._json_response(400, {"error": "message is required"})
            return

        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        # 先执行模块处理
        context_parts = []
        ctx = ai.context_awareness.perceive_context({"input": user_input})
        relevant = ai.memory.recall(user_input, top_k=2)
        if relevant:
            context_parts.append(f"记忆: {'; '.join(m.content for _, m in relevant)}")

        kg = ai.knowledge_graph.ask(user_input)
        if kg.get('context'):
            context_parts.append(f"知识: {str(kg['context'])[:200]}")

        full_context = "\n".join(context_parts)

        # 流式输出
        for chunk in ai.llm.chat_stream(user_input, context=full_context, provider=provider):
            data = json.dumps({"content": chunk}, ensure_ascii=False)
            self.wfile.write(f"data: {data}\n\n".encode('utf-8'))
            self.wfile.flush()

        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

        # 记录交互
        ai.memory.remember(
            content=f"用户问: {user_input[:100]}",
            memory_type="short_term",
            tags=['interaction'],
        )

    def _handle_learn(self, body):
        content = body.get("content", "")
        if not content:
            self._json_response(400, {"error": "content is required"})
            return

        result = ai.learn_from_knowledge(content, source='api')
        self._json_response(200, {"result": result})

    def _handle_evolve(self, body):
        result = ai.evolve("api")
        self._json_response(200, {
            "generation": ai.state.generation,
            "improvements": len(result['improvements']),
            "duration": result.get('duration', 0),
        })

    def _handle_goal(self, body):
        title = body.get("title", "")
        description = body.get("description", title)
        if not title:
            self._json_response(400, {"error": "title is required"})
            return

        result = ai.set_goal(title, description)
        self._json_response(200, result)

    def _handle_code(self, body):
        description = body.get("description", "")
        language = body.get("language", "python")
        if not description:
            self._json_response(400, {"error": "description is required"})
            return

        result = ai.generate_code(description, language)
        self._json_response(200, {"result": str(result)[:500]})

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """启动服务器"""
    global ai

    print("=" * 60)
    print("🧬 SelfEvolvingAI API Server")
    print("=" * 60)

    # 初始化AI
    print("正在初始化AI系统...")
    ai = create_evolution_ai(".")
    print(f"✅ 已加载 {ai.state.modules_loaded} 个模块")
    print(f"✅ LLM提供商: {ai.llm.get_available_providers()}")
    print(f"✅ 默认模型: {ai.llm.default_provider}")

    # 启动服务器
    server = HTTPServer((host, port), APIHandler)
    print(f"\n🚀 服务器启动: http://{host}:{port}")
    print(f"📖 API文档: http://localhost:{port}/")
    print(f"💬 聊天接口: POST http://localhost:{port}/api/chat")
    print(f"📡 流式接口: POST http://localhost:{port}/api/chat/stream")
    print(f"\n按 Ctrl+C 停止\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器停止")
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SelfEvolvingAI API Server')
    parser.add_argument('--host', default='0.0.0.0', help='绑定地址')
    parser.add_argument('--port', type=int, default=8000, help='端口')
    args = parser.parse_args()

    run_server(args.host, args.port)
