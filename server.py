"""
================================================================================
SelfEvolvingAI - FastAPI 后端
================================================================================

RESTful API + WebSocket 实时通信

启动: python server.py [--port 8000] [--host 0.0.0.0]
"""

import os
import sys
import json
import time
import asyncio
import argparse
from typing import Optional, List
from contextlib import asynccontextmanager

# Windows UTF-8 支持
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.evolution_loop import SelfEvolvingAI

# ==================== 全局状态 ====================
ai: Optional[SelfEvolvingAI] = None
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global ai
    storage_dir = os.path.join(os.path.dirname(__file__), ".evolution", "data")
    ai = SelfEvolvingAI(storage_dir)
    print(f"✅ SelfEvolvingAI 已启动 | {ai.state.modules_loaded} 个模块加载")
    yield
    print("🛑 SelfEvolvingAI 已关闭")


app = FastAPI(
    title="SelfEvolvingAI",
    description="70模块自我进化AI系统 API",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 数据模型 ====================

class ChatRequest(BaseModel):
    message: str
    provider: str = "local"
    provider_config: Optional[dict] = None
    stream: bool = False


class LearnRequest(BaseModel):
    content: str
    source: str = "user"


class GoalRequest(BaseModel):
    goal: str
    priority: str = "medium"


class EvolveRequest(BaseModel):
    trigger: str = "manual"


# ==================== API 路由 ====================

@app.get("/")
async def root():
    return {
        "name": "SelfEvolvingAI",
        "version": "4.0.0",
        "modules": ai.state.modules_loaded,
        "uptime": time.time() - start_time,
    }


@app.get("/api/status")
async def get_status():
    """系统状态"""
    return {
        "status": "running",
        "version": "4.0.0",
        "modules_loaded": ai.state.modules_loaded,
        "generation": ai.state.generation,
        "total_interactions": ai.state.total_interactions,
        "total_evolutions": ai.state.total_evolutions,
        "uptime": time.time() - start_time,
        "start_time": start_time,
    }


@app.get("/api/modules")
async def get_modules():
    """所有模块状态"""
    return ai.get_all_module_stats()


@app.get("/api/modules/{module_id}")
async def get_module(module_id: str):
    """单个模块状态"""
    stats = ai.get_all_module_stats()
    if module_id in stats:
        return stats[module_id]
    raise HTTPException(status_code=404, detail=f"模块 {module_id} 不存在")


@app.get("/api/memory")
async def get_memory():
    """记忆系统"""
    return ai.memory.summarize()


@app.get("/api/knowledge")
async def get_knowledge():
    """知识图谱"""
    return ai.knowledge_graph.get_graph_stats()


@app.get("/api/report")
async def get_report():
    """进化报告"""
    return {"report": ai.generate_evolution_report()}


@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "uptime": time.time() - start_time,
        "modules": ai.state.modules_loaded,
    }


@app.get("/api/providers")
async def get_providers():
    """LLM 提供商"""
    return ai.llm.get_stats()


def execute_tool(tool_name: str, args: dict, ai_instance) -> str:
    """统一工具执行器"""
    try:
        # === 系统操作 ===
        if tool_name == "execute_command":
            result = ai_instance.process_mgr.execute(args.get("command", ""), timeout=30)
            if result["success"]:
                return f"命令执行成功:\n{result['stdout'][:2000]}"
            return f"命令执行失败:\n{result.get('stderr', result.get('error', ''))[:500]}"

        elif tool_name == "process_list":
            result = ai_instance.process_mgr.execute("tasklist /FO CSV", timeout=10)
            return result.get("stdout", "获取进程列表失败")[:2000]

        elif tool_name == "process_kill":
            pid = args.get("pid", 0)
            result = ai_instance.process_mgr.execute(f"taskkill /PID {pid} /F", timeout=10)
            return result.get("stdout", f"终止进程 {pid}")[:500]

        # === 文件操作 ===
        elif tool_name == "read_file":
            path = args.get("path", "")
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(50000)
            return f"文件内容 ({len(content)} 字符):\n{content}"

        elif tool_name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"已写入: {path} ({len(content)} 字符)"

        elif tool_name == "edit_file":
            path = args.get("path", "")
            old_text = args.get("old_text", "")
            new_text = args.get("new_text", "")
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if old_text not in content:
                return f"未找到要替换的文本"
            content = content.replace(old_text, new_text, 1)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"已编辑: {path}"

        elif tool_name == "list_directory":
            path = args.get("path", ".")
            items = os.listdir(path)
            result = []
            for item in items[:50]:
                full = os.path.join(path, item)
                is_dir = os.path.isdir(full)
                size = os.path.getsize(full) if not is_dir else 0
                result.append(f"{'📁' if is_dir else '📄'} {item} {'(' + str(size) + ' bytes)' if not is_dir else ''}")
            return "\n".join(result)

        elif tool_name == "create_directory":
            path = args.get("path", "")
            os.makedirs(path, exist_ok=True)
            return f"已创建目录: {path}"

        elif tool_name == "delete_file":
            path = args.get("path", "")
            os.remove(path)
            return f"已删除: {path}"

        elif tool_name == "move_file":
            src = args.get("src", "")
            dst = args.get("dst", "")
            os.rename(src, dst)
            return f"已移动: {src} -> {dst}"

        # === 网络 & 浏览器 ===
        elif tool_name == "search_web":
            result = ai_instance.browser.search_web(args.get("query", ""))
            if result.get("success"):
                return f"搜索结果:\n{result.get('text_preview', '')[:2000]}"
            return f"搜索失败: {result.get('error', '')}"

        elif tool_name == "open_url":
            result = ai_instance.browser.open_url(args.get("url", ""))
            if result.get("success"):
                return f"页面: {result.get('title', '')}\n内容: {result.get('text_preview', '')[:2000]}"
            return f"打开失败: {result.get('error', '')}"

        elif tool_name == "browser_navigate":
            result = ai_instance.browser.open_url(args.get("url", ""))
            return f"导航到: {args.get('url', '')} - {'成功' if result.get('success') else '失败'}"

        elif tool_name == "browser_click":
            selector = args.get("selector", "")
            return f"浏览器点击: {selector} (模拟)"

        elif tool_name == "browser_type":
            selector = args.get("selector", "")
            text = args.get("text", "")
            return f"浏览器输入: '{text}' 到 {selector} (模拟)"

        elif tool_name == "browser_screenshot":
            path = ai_instance.desktop.screenshot()
            return f"浏览器截图已保存: {path}" if path else "截图失败"

        # === 桌面操作 ===
        elif tool_name == "screenshot":
            path = ai_instance.desktop.screenshot()
            return f"截图已保存: {path}" if path else "截图失败"

        elif tool_name == "click":
            x, y = args.get("x", 0), args.get("y", 0)
            success = ai_instance.desktop.click(x, y)
            return f"点击 ({x}, {y}): {'成功' if success else '失败'}"

        elif tool_name == "type_text":
            text = args.get("text", "")
            success = ai_instance.desktop.type_text(text)
            return f"输入: '{text[:50]}': {'成功' if success else '失败'}"

        elif tool_name == "mouse_move":
            x, y = args.get("x", 0), args.get("y", 0)
            import pyautogui
            pyautogui.moveTo(x, y)
            return f"鼠标移动到 ({x}, {y})"

        elif tool_name == "keyboard_press":
            key = args.get("key", "")
            import pyautogui
            pyautogui.press(key)
            return f"按下按键: {key}"

        elif tool_name == "clipboard_get":
            import pyperclip
            text = pyperclip.paste()
            return f"剪贴板内容: {text[:500]}"

        elif tool_name == "clipboard_set":
            import pyperclip
            pyperclip.copy(args.get("text", ""))
            return f"已设置剪贴板: {args.get('text', '')[:50]}"

        # === 系统信息 ===
        elif tool_name == "get_system_info":
            import platform
            import psutil
            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
                "memory_available": f"{psutil.virtual_memory().available / (1024**3):.1f} GB",
                "disk_usage": f"{psutil.disk_usage('/').percent}%"
            }
            return json.dumps(info, ensure_ascii=False, indent=2)

        elif tool_name == "get_network_info":
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return f"主机名: {hostname}\nIP: {ip}"

        elif tool_name == "get_current_time":
            from datetime import datetime
            now = datetime.now()
            return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"

        # === 媒体处理 ===
        elif tool_name == "analyze_image":
            path = args.get("path", "")
            prompt = args.get("prompt", "描述这张图片")
            return f"图片分析: {path} - {prompt} (需要视觉模型支持)"

        elif tool_name == "text_to_speech":
            text = args.get("text", "")
            return f"TTS: '{text[:50]}' (需要TTS引擎支持)"

        # === 网络请求 ===
        elif tool_name == "http_request":
            import urllib.request
            url = args.get("url", "")
            method = args.get("method", "GET")
            data = args.get("data")
            headers = args.get("headers", {})
            req = urllib.request.Request(url, data=data.encode() if data else None,
                                        headers=headers, method=method)
            resp = urllib.request.urlopen(req, timeout=30)
            return resp.read().decode('utf-8', errors='replace')[:5000]

        # === 定时任务 ===
        elif tool_name == "schedule_task":
            name = args.get("name", "")
            command = args.get("command", "")
            cron_expr = args.get("cron", "")
            # 保存到文件
            schedules = {}
            sched_file = os.path.join(".evolution", "data", "schedules.json")
            if os.path.exists(sched_file):
                with open(sched_file, 'r') as f:
                    schedules = json.load(f)
            schedules[name] = {"command": command, "cron": cron_expr, "created": time.time()}
            os.makedirs(os.path.dirname(sched_file), exist_ok=True)
            with open(sched_file, 'w') as f:
                json.dump(schedules, f, ensure_ascii=False, indent=2)
            return f"已创建定时任务: {name} ({cron_expr})"

        elif tool_name == "schedule_list":
            sched_file = os.path.join(".evolution", "data", "schedules.json")
            if os.path.exists(sched_file):
                with open(sched_file, 'r') as f:
                    schedules = json.load(f)
                result = []
                for name, info in schedules.items():
                    result.append(f"- {name}: {info['command']} ({info['cron']})")
                return "定时任务:\n" + "\n".join(result) if result else "暂无定时任务"
            return "暂无定时任务"

        elif tool_name == "schedule_delete":
            name = args.get("name", "")
            sched_file = os.path.join(".evolution", "data", "schedules.json")
            if os.path.exists(sched_file):
                with open(sched_file, 'r') as f:
                    schedules = json.load(f)
                if name in schedules:
                    del schedules[name]
                    with open(sched_file, 'w') as f:
                        json.dump(schedules, f, ensure_ascii=False, indent=2)
                    return f"已删除定时任务: {name}"
            return f"未找到任务: {name}"

        # === 代码执行 ===
        elif tool_name == "run_python":
            code = args.get("code", "")
            result = ai_instance.process_mgr.execute(f"python -c \"{code}\"", timeout=30)
            if result["success"]:
                return f"Python执行结果:\n{result['stdout'][:2000]}"
            return f"Python执行失败:\n{result.get('stderr', '')[:500]}"

        # === 记忆 & 知识 ===
        elif tool_name == "recall_memory":
            query = args.get("query", "")
            memories = ai_instance.memory.recall(query, top_k=5)
            if memories:
                result = []
                for score, mem in memories:
                    result.append(f"[{score:.2f}] {mem.content[:100]}")
                return "记忆检索结果:\n" + "\n".join(result)
            return "未找到相关记忆"

        elif tool_name == "save_memory":
            content = args.get("content", "")
            tags = args.get("tags", [])
            from core.memory import MemoryType
            ai_instance.memory.remember(content=content, memory_type=MemoryType.LONG_TERM, tags=tags)
            return f"已保存到记忆: {content[:50]}"

        elif tool_name == "query_knowledge":
            query = args.get("query", "")
            result = ai_instance.knowledge_graph.ask(query)
            return f"知识图谱查询: {json.dumps(result, ensure_ascii=False)[:1000]}"

        else:
            return f"未知工具: {tool_name}"

    except Exception as e:
        return f"工具执行失败 ({tool_name}): {str(e)}"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """聊天 - 模块+LLM协作模式"""
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        # Step 1: 70个模块先处理
        result = ai.process(req.message)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"模块处理失败: {str(e)}")

    try:
        modules_used = result.get("modules_used", [])

        # Step 2: 收集模块上下文（协作式）
        context_parts = []

        # 2a. 情感分析
        emotion = result.get("emotion", {})
        emotion_label = "neutral"
        if isinstance(emotion, dict):
            emotion_label = emotion.get("emotion", emotion.get("dominant_emotion", "neutral"))
            emo_conf = emotion.get("confidence", 0)
            if emotion_label != "neutral":
                context_parts.append(f"[情感分析] 用户情绪: {emotion_label} (置信度{emo_conf:.0%})，请用相应语气回应")

        # 2b. 元认知
        confidence = result.get("confidence", 0)
        domain = result.get("domain", "other")
        conf_exp = result.get("confidence_explanation", "")
        context_parts.append(f"[元认知] 领域={domain}, 置信度={confidence:.0%}{', ' + conf_exp if conf_exp else ''}")

        # 2c. 记忆
        memory_used = result.get("memory_used", 0)
        if memory_used > 0:
            context_parts.append(f"[记忆系统] 检索到 {memory_used} 条相关记忆")

        # 2d. 知识图谱
        if "knowledge_graph" in modules_used:
            try:
                kg = ai.knowledge_graph.ask(req.message)
                kg_ctx = kg.get("context", [])
                if kg_ctx:
                    context_parts.append(f"[知识图谱] 相关知识: {', '.join(str(k) for k in kg_ctx[:5])}")
            except: pass

        # 2e. 因果推理
        if "causal_reasoning" in modules_used:
            try:
                causal = ai.causal_reasoning.find_root_causes(req.message)
                if causal and isinstance(causal, list) and len(causal) > 0:
                    context_parts.append(f"[因果推理] {', '.join(str(c) for c in causal[:3])}")
            except: pass

        # 2f. 反思洞察
        insights = result.get("reflection_insights", [])
        if insights:
            context_parts.append(f"[反思] {insights[0]}")

        # 2g. 决策模式
        if "decision_patterns" in modules_used:
            try:
                similar = ai.decision_patterns.find_similar_cases(req.message)
                if similar and len(similar) > 0:
                    context_parts.append(f"[决策模式] 找到{len(similar)}个相似案例")
            except: pass

        # 2h. 需要规划
        needs_plan = result.get("needs_planning", False)
        if needs_plan:
            context_parts.append("[目标规划] 用户需要步骤化建议")

        module_context = "\n".join(context_parts) if context_parts else ""

        # Step 3: 调用 LLM（带模块上下文 + 工具）
        llm_answer = None
        tools_used = []
        if req.provider != "local" and req.provider_config:
            try:
                import urllib.request as _urlreq
                cfg = req.provider_config
                base_url = cfg.get("base_url", "").rstrip("/")
                api_key = cfg.get("api_key", "")
                model = cfg.get("model", "deepseek-chat")

                # 根据情感调整系统提示
                emotion_hint = ""
                if emotion_label == "happy":
                    emotion_hint = "用户心情不错，可以用轻松愉快的语气回答。"
                elif emotion_label == "sad":
                    emotion_hint = "用户情绪低落，请用温暖关怀的语气回答。"
                elif emotion_label == "angry":
                    emotion_hint = "用户有些不满，请耐心解释，语气平和。"
                elif emotion_label == "anxious":
                    emotion_hint = "用户感到焦虑，请给出清晰明确的回答，减轻不安。"

                # 工具定义（传给 LLM function calling）
                tool_definitions = [
                    # === 系统操作 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "execute_command",
                            "description": "执行系统命令（如: dir, python script.py, git status, tasklist）",
                            "parameters": {"type": "object", "properties": {
                                "command": {"type": "string", "description": "要执行的命令"}
                            }, "required": ["command"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "process_list",
                            "description": "列出正在运行的进程",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "process_kill",
                            "description": "终止指定进程",
                            "parameters": {"type": "object", "properties": {
                                "pid": {"type": "integer", "description": "进程ID"}
                            }, "required": ["pid"]}
                        }
                    },
                    # === 文件操作 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "description": "读取文件内容",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "文件路径"}
                            }, "required": ["path"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "description": "写入文件内容",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "文件路径"},
                                "content": {"type": "string", "description": "文件内容"}
                            }, "required": ["path", "content"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "edit_file",
                            "description": "编辑文件（查找替换）",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "文件路径"},
                                "old_text": {"type": "string", "description": "要替换的原文"},
                                "new_text": {"type": "string", "description": "新内容"}
                            }, "required": ["path", "old_text", "new_text"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "list_directory",
                            "description": "列出目录内容",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "目录路径，默认当前目录"}
                            }}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "create_directory",
                            "description": "创建目录",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "目录路径"}
                            }, "required": ["path"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "delete_file",
                            "description": "删除文件",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "文件路径"}
                            }, "required": ["path"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "move_file",
                            "description": "移动或重命名文件",
                            "parameters": {"type": "object", "properties": {
                                "src": {"type": "string", "description": "源路径"},
                                "dst": {"type": "string", "description": "目标路径"}
                            }, "required": ["src", "dst"]}
                        }
                    },
                    # === 网络 & 浏览器 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "search_web",
                            "description": "搜索网页获取信息",
                            "parameters": {"type": "object", "properties": {
                                "query": {"type": "string", "description": "搜索关键词"}
                            }, "required": ["query"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "open_url",
                            "description": "打开网页并获取内容",
                            "parameters": {"type": "object", "properties": {
                                "url": {"type": "string", "description": "网址"}
                            }, "required": ["url"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "browser_navigate",
                            "description": "浏览器导航到指定URL",
                            "parameters": {"type": "object", "properties": {
                                "url": {"type": "string", "description": "网址"}
                            }, "required": ["url"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "browser_click",
                            "description": "浏览器点击元素",
                            "parameters": {"type": "object", "properties": {
                                "selector": {"type": "string", "description": "CSS选择器或文本"}
                            }, "required": ["selector"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "browser_type",
                            "description": "浏览器输入文字",
                            "parameters": {"type": "object", "properties": {
                                "selector": {"type": "string", "description": "CSS选择器"},
                                "text": {"type": "string", "description": "要输入的文字"}
                            }, "required": ["selector", "text"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "browser_screenshot",
                            "description": "浏览器截屏",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    # === 桌面操作 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "screenshot",
                            "description": "截取屏幕截图",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "click",
                            "description": "点击屏幕指定位置",
                            "parameters": {"type": "object", "properties": {
                                "x": {"type": "integer", "description": "X坐标"},
                                "y": {"type": "integer", "description": "Y坐标"}
                            }, "required": ["x", "y"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "type_text",
                            "description": "在当前位置输入文字",
                            "parameters": {"type": "object", "properties": {
                                "text": {"type": "string", "description": "要输入的文字"}
                            }, "required": ["text"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "mouse_move",
                            "description": "移动鼠标到指定位置",
                            "parameters": {"type": "object", "properties": {
                                "x": {"type": "integer", "description": "X坐标"},
                                "y": {"type": "integer", "description": "Y坐标"}
                            }, "required": ["x", "y"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "keyboard_press",
                            "description": "按下键盘按键",
                            "parameters": {"type": "object", "properties": {
                                "key": {"type": "string", "description": "按键名称（如: enter, tab, escape, ctrl+c）"}
                            }, "required": ["key"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "clipboard_get",
                            "description": "获取剪贴板内容",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "clipboard_set",
                            "description": "设置剪贴板内容",
                            "parameters": {"type": "object", "properties": {
                                "text": {"type": "string", "description": "要设置的文字"}
                            }, "required": ["text"]}
                        }
                    },
                    # === 系统信息 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "get_system_info",
                            "description": "获取系统信息（OS、CPU、内存、磁盘）",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_network_info",
                            "description": "获取网络信息（IP、接口）",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_current_time",
                            "description": "获取当前日期和时间",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    # === 媒体处理 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "analyze_image",
                            "description": "分析图片内容",
                            "parameters": {"type": "object", "properties": {
                                "path": {"type": "string", "description": "图片路径或URL"},
                                "prompt": {"type": "string", "description": "分析提示"}
                            }, "required": ["path"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "text_to_speech",
                            "description": "文字转语音",
                            "parameters": {"type": "object", "properties": {
                                "text": {"type": "string", "description": "要转换的文字"},
                                "voice": {"type": "string", "description": "语音类型"}
                            }, "required": ["text"]}
                        }
                    },
                    # === 网络请求 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "http_request",
                            "description": "发送HTTP请求",
                            "parameters": {"type": "object", "properties": {
                                "url": {"type": "string", "description": "URL"},
                                "method": {"type": "string", "description": "方法（GET/POST/PUT/DELETE）"},
                                "data": {"type": "string", "description": "请求体（JSON字符串）"},
                                "headers": {"type": "object", "description": "请求头"}
                            }, "required": ["url"]}
                        }
                    },
                    # === 定时任务 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "schedule_task",
                            "description": "创建定时任务",
                            "parameters": {"type": "object", "properties": {
                                "name": {"type": "string", "description": "任务名称"},
                                "command": {"type": "string", "description": "要执行的命令"},
                                "cron": {"type": "string", "description": "Cron表达式（如: 0 9 * * * 每天9点）"}
                            }, "required": ["name", "command", "cron"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "schedule_list",
                            "description": "列出所有定时任务",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "schedule_delete",
                            "description": "删除定时任务",
                            "parameters": {"type": "object", "properties": {
                                "name": {"type": "string", "description": "任务名称"}
                            }, "required": ["name"]}
                        }
                    },
                    # === 代码执行 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "run_python",
                            "description": "执行Python代码并返回结果",
                            "parameters": {"type": "object", "properties": {
                                "code": {"type": "string", "description": "Python代码"}
                            }, "required": ["code"]}
                        }
                    },
                    # === 记忆 & 知识 ===
                    {
                        "type": "function",
                        "function": {
                            "name": "recall_memory",
                            "description": "从记忆中检索相关信息",
                            "parameters": {"type": "object", "properties": {
                                "query": {"type": "string", "description": "查询内容"}
                            }, "required": ["query"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "save_memory",
                            "description": "保存信息到记忆",
                            "parameters": {"type": "object", "properties": {
                                "content": {"type": "string", "description": "要记住的内容"},
                                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签"}
                            }, "required": ["content"]}
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "query_knowledge",
                            "description": "从知识图谱查询",
                            "parameters": {"type": "object", "properties": {
                                "query": {"type": "string", "description": "查询内容"}
                            }, "required": ["query"]}
                        }
                    },
                ]

                system_prompt = (
                    "你是SelfEvolvingAI，一个具备自我进化能力的AI助手，集成了70个智能模块和多种工具。"
                    "你由杨元强（primaxlab）开发。请以SelfEvolvingAI的身份回复，不要说自己是DeepSeek或其他模型。\n\n"
                    f"系统内部模块分析结果:\n{module_context}\n\n"
                    f"{emotion_hint}\n"
                    "【工具使用规则】\n"
                    "当用户请求涉及以下操作时，你必须调用相应工具：\n"
                    "1. 执行命令（dir, ls, python等） → 调用 execute_command\n"
                    "2. 读取文件 → 调用 read_file\n"
                    "3. 写入/创建文件 → 调用 write_file\n"
                    "4. 搜索网页 → 调用 search_web\n"
                    "5. 打开网页 → 调用 open_url\n"
                    "6. 截屏 → 调用 screenshot\n"
                    "7. 点击屏幕 → 调用 click\n"
                    "8. 输入文字 → 调用 type_text\n"
                    "9. 查看系统信息 → 调用 get_system_info\n"
                    "10. 创建定时任务 → 调用 schedule_task\n\n"
                    "【重要】不要只告诉用户怎么做，要直接调用工具执行！"
                )

                # 工具定义格式（OpenAI function calling 格式）
                formatted_tools = []
                for t in tool_definitions:
                    formatted_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"]
                        }
                    })

                payload = json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": req.message}
                    ],
                    "tools": formatted_tools,
                    "tool_choice": "auto",  # 让模型自动决定是否调用工具
                    "max_tokens": 1024,
                    "temperature": 0.7,
                }).encode()

                llm_req = _urlreq.Request(
                    f"{base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST",
                )
                llm_resp = _urlreq.urlopen(llm_req, timeout=30)
                llm_data = json.loads(llm_resp.read())
                message = llm_data["choices"][0]["message"]

                # 检查是否有工具调用
                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        func = tool_call["function"]
                        tool_name = func["name"]
                        try:
                            tool_args = json.loads(func["arguments"])
                        except:
                            tool_args = {}

                        # 执行工具
                        tool_result = execute_tool(tool_name, tool_args, ai)
                        tools_used.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": tool_result[:500],
                        })

                    # 把工具结果反馈给 LLM 获取最终回答
                    tool_results_msg = "工具执行结果:\n"
                    for tu in tools_used:
                        tool_results_msg += f"- {tu['tool']}: {tu['result']}\n"

                    payload2 = json.dumps({
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": req.message},
                            {"role": "assistant", "content": None, "tool_calls": message["tool_calls"]},
                            {"role": "tool", "tool_call_id": message["tool_calls"][0]["id"], "content": tool_results_msg},
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.7,
                    }).encode()
                    llm_req2 = _urlreq.Request(
                        f"{base_url}/chat/completions",
                        data=payload2,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}",
                        },
                        method="POST",
                    )
                    llm_resp2 = _urlreq.urlopen(llm_req2, timeout=30)
                    llm_data2 = json.loads(llm_resp2.read())
                    llm_answer = llm_data2["choices"][0]["message"]["content"]
                else:
                    llm_answer = message["content"]

            except Exception as e:
                print(f"LLM调用失败: {e}")
                llm_answer = None

        # Step 4: 最终回答
        answer = result.get("answer", result.get("response", ""))
        if llm_answer:
            answer = llm_answer

        return {
            "answer": answer,
            "confidence": confidence,
            "domain": domain,
            "emotion": emotion_label,
            "modules_used": modules_used,
            "module_context": module_context,
            "needs_planning": needs_plan,
            "tools_used": tools_used,
            "provider": req.provider,
            "model": req.provider_config.get("model", "") if req.provider_config else "",
            "timestamp": time.time(),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式聊天 - 模块+LLM协作"""
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    async def generate():
        try:
            result = ai.process(req.message)
        except Exception:
            result = {"answer": "处理出错", "confidence": 0, "domain": "other", "modules_used": [], "emotion": {}}

        modules_used = result.get("modules_used", [])
        confidence = result.get("confidence", 0)
        domain = result.get("domain", "other")
        emotion = result.get("emotion", {})
        emotion_label = emotion.get("emotion", emotion.get("dominant_emotion", "neutral")) if isinstance(emotion, dict) else "neutral"

        context_parts = []
        if emotion_label != "neutral":
            context_parts.append(f"[情感分析] 用户情绪: {emotion_label}")
        context_parts.append(f"[元认知] 领域={domain}, 置信度={confidence:.0%}")
        memory_used = result.get("memory_used", 0)
        if memory_used > 0:
            context_parts.append(f"[记忆系统] {memory_used} 条相关记忆")
        insights = result.get("reflection_insights", [])
        if insights:
            context_parts.append(f"[反思] {insights[0][:50]}")
        module_context = "\n".join(context_parts)

        llm_answer = None
        if req.provider != "local" and req.provider_config:
            try:
                import urllib.request as _urlreq
                cfg = req.provider_config
                base_url = cfg.get("base_url", "").rstrip("/")
                api_key = cfg.get("api_key", "")
                model = cfg.get("model", "deepseek-chat")
                system_prompt = (
                    "你是SelfEvolvingAI，集成了70个智能模块。"
                    f"模块分析:\n{module_context}\n\n"
                    "请基于以上分析回答。"
                )
                payload = json.dumps({
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": req.message}],
                    "max_tokens": 1024, "temperature": 0.7,
                }).encode()
                llm_req = _urlreq.Request(f"{base_url}/chat/completions", data=payload,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
                llm_resp = _urlreq.urlopen(llm_req, timeout=30)
                llm_data = json.loads(llm_resp.read())
                llm_answer = llm_data["choices"][0]["message"]["content"]
            except Exception:
                llm_answer = None

        answer = result.get("answer", result.get("response", ""))
        if llm_answer:
            answer = llm_answer

        for i in range(0, len(answer), 3):
            chunk = answer[i:i+3]
            yield f"data: {json.dumps({'chunk': chunk, 'done': False}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.02)
        yield f"data: {json.dumps({'chunk': '', 'done': True, 'confidence': confidence, 'domain': domain, 'emotion': emotion_label, 'modules_used': modules_used, 'module_context': module_context, 'provider': req.provider, 'model': req.provider_config.get('model', '') if req.provider_config else ''}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/stats/summary")
async def get_stats_summary():
    """系统概览统计"""
    stats = ai.get_all_module_stats()
    memory = ai.memory.summarize()
    kg = ai.knowledge_graph.get_graph_stats()
    return {
        "modules": len(stats),
        "memory": memory,
        "knowledge": kg,
        "generation": ai.state.generation,
        "interactions": ai.state.total_interactions,
    }


@app.post("/api/learn")
async def learn(req: LearnRequest):
    """学习知识"""
    if not req.content:
        raise HTTPException(status_code=400, detail="content is required")

    result = ai.learn_from_knowledge(req.content, source=req.source)
    return {"success": True, "result": result}


@app.post("/api/evolve")
async def evolve(req: EvolveRequest):
    """触发进化"""
    result = ai.evolve(req.trigger)
    return {
        "success": True,
        "generation": ai.state.generation,
        "improvements": len(result.get("improvements", [])),
        "duration": result.get("duration", 0),
        "details": result.get("improvements", []),
    }


@app.post("/api/goal")
async def set_goal(req: GoalRequest):
    """设定目标"""
    result = ai.goal_planning.add_goal(
        description=req.goal,
        priority=req.priority,
    )
    return {"success": True, "goal": result}


@app.get("/api/goals")
async def get_goals():
    """获取目标列表"""
    return ai.goal_planning.get_all_goals()


# ==================== WebSocket ====================

class ConnectionManager:
    """WebSocket 连接管理"""
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        for conn in self.active:
            try:
                await conn.send_json(message)
            except:
                pass

manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket 实时通信"""
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "chat":
                result = ai.process(data.get("message", ""))
                await ws.send_json({
                    "type": "chat_response",
                    "answer": result.get("answer", result.get("response", "")),
                    "confidence": result.get("confidence", 0),
                    "domain": result.get("domain", "other"),
                    "modules_used": result.get("modules_used", []),
                })

            elif msg_type == "evolve":
                result = ai.evolve("manual")
                await ws.send_json({
                    "type": "evolve_result",
                    "generation": ai.state.generation,
                    "improvements": len(result.get("improvements", [])),
                })

            elif msg_type == "status":
                await ws.send_json({
                    "type": "status",
                    "modules_loaded": ai.state.modules_loaded,
                    "generation": ai.state.generation,
                    "interactions": ai.state.total_interactions,
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)


# ==================== 静态文件服务 ====================

# 前端构建产物
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 路由 - 所有非 API 路径返回 index.html"""
        file_path = os.path.join(frontend_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"🚀 SelfEvolvingAI API 启动于 http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
