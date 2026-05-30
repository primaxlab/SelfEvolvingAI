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

        # Step 2: 收集模块上下文
        context_parts = []
        memory_used = result.get("memory_used", 0)
        if memory_used > 0:
            context_parts.append(f"[记忆系统] 检索到 {memory_used} 条相关记忆")
        if "knowledge_graph" in modules_used:
            try:
                kg = ai.knowledge_graph.ask(req.message)
                kg_ctx = kg.get("context", [])
                if kg_ctx:
                    context_parts.append(f"[知识图谱] 相关知识: {', '.join(str(k) for k in kg_ctx[:3])}")
            except: pass
        emotion = result.get("emotion", {})
        if emotion and isinstance(emotion, dict):
            emo_name = emotion.get("dominant_emotion", "")
            if emo_name:
                context_parts.append(f"[情感分析] 用户情绪: {emo_name}")
        confidence = result.get("confidence", 0)
        domain = result.get("domain", "other")
        context_parts.append(f"[元认知] 领域={domain}, 置信度={confidence:.2f}")
        insights = result.get("reflection_insights", [])
        if insights:
            context_parts.append(f"[反思] {insights[0]}")
        if "prompt_engineering" in modules_used:
            try:
                opt = ai.prompt_engineering.generate_prompt(domain=domain, task=req.message)
                if opt:
                    context_parts.append(f"[提示优化] {opt[:200]}")
            except: pass
        module_context = "\n".join(context_parts) if context_parts else ""
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"上下文收集失败: {str(e)}")

    # Step 3: 调用 LLM
    llm_answer = None
    if req.provider != "local" and req.provider_config:
        try:
            import urllib.request as _urlreq
            cfg = req.provider_config
            base_url = cfg.get("base_url", "").rstrip("/")
            api_key = cfg.get("api_key", "")
            model = cfg.get("model", "deepseek-chat")

            system_prompt = (
                "你是SelfEvolvingAI，一个具备自我进化能力的AI助手，集成了70个智能模块。"
                "你由杨元强（primaxlab）开发。请以SelfEvolvingAI的身份回复，不要说自己是DeepSeek或其他模型。\n\n"
                f"系统内部模块分析结果:\n{module_context}\n\n"
                "请基于以上模块分析结果，给出更准确、更有帮助的回答。保持简洁、友好。"
            )

            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message}
                ],
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
            llm_answer = llm_data["choices"][0]["message"]["content"]
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
        "modules_used": modules_used,
        "module_context": module_context,
        "provider": req.provider,
        "model": req.provider_config.get("model", "") if req.provider_config else "",
        "timestamp": time.time(),
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式聊天"""
    if not req.message:
        raise HTTPException(status_code=400, detail="message is required")

    async def generate():
        # 如果前端传了 provider_config，直接调用 LLM API
        llm_answer = None
        if req.provider != "local" and req.provider_config:
            try:
                import urllib.request as _urlreq
                cfg = req.provider_config
                base_url = cfg.get("base_url", "").rstrip("/")
                api_key = cfg.get("api_key", "")
                model = cfg.get("model", "deepseek-chat")

                payload = json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是SelfEvolvingAI，一个具备自我进化能力的AI助手，集成了70个智能模块。你由杨元强（primaxlab）开发。请以SelfEvolvingAI的身份回复，不要说自己是DeepSeek或其他模型。保持简洁、友好、有帮助。"},
                        {"role": "user", "content": req.message}
                    ],
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
                llm_answer = llm_data["choices"][0]["message"]["content"]
            except Exception:
                llm_answer = None

        result = ai.process(req.message)
        answer = result.get("answer", result.get("response", ""))
        if llm_answer:
            answer = llm_answer

        # 流式输出
        for i in range(0, len(answer), 3):
            chunk = answer[i:i+3]
            yield f"data: {json.dumps({'chunk': chunk, 'done': False}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.02)
        yield f"data: {json.dumps({'chunk': '', 'done': True, 'confidence': result.get('confidence', 0), 'domain': result.get('domain', 'other'), 'provider': req.provider, 'model': req.provider_config.get('model', '') if req.provider_config else ''}, ensure_ascii=False)}\n\n"

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
