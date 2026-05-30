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

                # 工具定义（传给 DeepSeek function calling）
                tool_definitions = [
                    {
                        "type": "function",
                        "function": {
                            "name": "execute_command",
                            "description": "执行系统命令（如: dir, python script.py, git status）",
                            "parameters": {"type": "object", "properties": {
                                "command": {"type": "string", "description": "要执行的命令"}
                            }, "required": ["command"]}
                        }
                    },
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
                ]

                system_prompt = (
                    "你是SelfEvolvingAI，一个具备自我进化能力的AI助手，集成了70个智能模块和多种工具。"
                    "你由杨元强（primaxlab）开发。请以SelfEvolvingAI的身份回复，不要说自己是DeepSeek或其他模型。\n\n"
                    f"系统内部模块分析结果:\n{module_context}\n\n"
                    f"{emotion_hint}\n"
                    "你可以使用工具来操作计算机、读写文件、搜索网页等。当用户请求需要工具操作时，调用相应工具。"
                )

                payload = json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": req.message}
                    ],
                    "tools": tool_definitions,
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
                        tool_result = ai._check_and_execute_tool(tool_name, tool_args)
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
