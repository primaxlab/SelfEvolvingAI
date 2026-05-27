"""
================================================================================
AI模型集成层 - 接入真实AI模型（OpenAI/Claude/Ollama/本地模型）
================================================================================

提供统一的LLM接口，支持：
- OpenAI GPT-4/3.5
- Claude (Anthropic)
- Ollama (本地模型)
- 自定义模型
- 流式输出
- 工具调用 (Function Calling)
"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Generator
import urllib.request
import urllib.error


class ModelProvider(Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class Message:
    role: str  # system/user/assistant/tool
    content: str = ""
    name: str = ""
    tool_call_id: str = ""
    tool_calls: List[Dict] = field(default_factory=list)


@dataclass
class LLMResponse:
    content: str = ""
    model: str = ""
    provider: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    latency: float = 0.0
    cached: bool = False


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30
    max_retries: int = 3


class LLMProvider:
    """LLM提供商基类"""

    def __init__(self, config: ModelConfig):
        self.config = config

    def chat(self, messages: List[Message], tools: List[ToolDefinition] = None,
             stream: bool = False) -> LLMResponse:
        raise NotImplementedError

    def chat_stream(self, messages: List[Message],
                    tools: List[ToolDefinition] = None) -> Generator[str, None, None]:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI API提供商"""

    def chat(self, messages: List[Message], tools: List[ToolDefinition] = None,
             stream: bool = False) -> LLMResponse:
        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = self.config.base_url or "https://api.openai.com/v1"

        if not api_key:
            return LLMResponse(content="[错误] 未配置OpenAI API Key", provider="openai")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        body = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if tools:
            body["tools"] = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            } for t in tools]

        start_time = time.time()

        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            choice = data["choices"][0]
            message = choice["message"]

            return LLMResponse(
                content=message.get("content", ""),
                model=data.get("model", self.config.model),
                provider="openai",
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", ""),
                tool_calls=message.get("tool_calls", []),
                latency=time.time() - start_time,
            )
        except Exception as e:
            return LLMResponse(
                content=f"[OpenAI错误] {str(e)}",
                provider="openai",
                latency=time.time() - start_time,
            )

    def chat_stream(self, messages: List[Message],
                    tools: List[ToolDefinition] = None) -> Generator[str, None, None]:
        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = self.config.base_url or "https://api.openai.com/v1"

        if not api_key:
            yield "[错误] 未配置OpenAI API Key"
            return

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        body = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }

        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                buffer = ""
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line.startswith('data: ') and line != 'data: [DONE]':
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception as e:
            yield f"[OpenAI流式错误] {str(e)}"


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API提供商"""

    def chat(self, messages: List[Message], tools: List[ToolDefinition] = None,
             stream: bool = False) -> LLMResponse:
        api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        base_url = self.config.base_url or "https://api.anthropic.com"

        if not api_key:
            return LLMResponse(content="[错误] 未配置Anthropic API Key", provider="claude")

        # 分离system消息
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        body = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": chat_messages,
        }
        if system_msg:
            body["system"] = system_msg

        start_time = time.time()

        try:
            req = urllib.request.Request(
                f"{base_url}/v1/messages",
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")

            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                provider="claude",
                usage=data.get("usage", {}),
                finish_reason=data.get("stop_reason", ""),
                latency=time.time() - start_time,
            )
        except Exception as e:
            return LLMResponse(
                content=f"[Claude错误] {str(e)}",
                provider="claude",
                latency=time.time() - start_time,
            )

    def chat_stream(self, messages: List[Message],
                    tools: List[ToolDefinition] = None) -> Generator[str, None, None]:
        api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        base_url = self.config.base_url or "https://api.anthropic.com"

        if not api_key:
            yield "[错误] 未配置Anthropic API Key"
            return

        system_msg = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        body = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": chat_messages,
            "stream": True,
        }
        if system_msg:
            body["system"] = system_msg

        try:
            req = urllib.request.Request(
                f"{base_url}/v1/messages",
                data=json.dumps(body).encode('utf-8'),
                headers=headers,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                buffer = ""
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if data.get("type") == "content_block_delta":
                                    text = data.get("delta", {}).get("text", "")
                                    if text:
                                        yield text
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception as e:
            yield f"[Claude流式错误] {str(e)}"


class OllamaProvider(LLMProvider):
    """Ollama本地模型提供商"""

    def chat(self, messages: List[Message], tools: List[ToolDefinition] = None,
             stream: bool = False) -> LLMResponse:
        base_url = self.config.base_url or "http://localhost:11434"

        body = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }

        start_time = time.time()

        try:
            req = urllib.request.Request(
                f"{base_url}/api/chat",
                data=json.dumps(body).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                model=data.get("model", self.config.model),
                provider="ollama",
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                },
                latency=time.time() - start_time,
            )
        except Exception as e:
            return LLMResponse(
                content=f"[Ollama错误] {str(e)}",
                provider="ollama",
                latency=time.time() - start_time,
            )

    def chat_stream(self, messages: List[Message],
                    tools: List[ToolDefinition] = None) -> Generator[str, None, None]:
        base_url = self.config.base_url or "http://localhost:11434"

        body = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }

        try:
            req = urllib.request.Request(
                f"{base_url}/api/chat",
                data=json.dumps(body).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                buffer = ""
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            yield f"[Ollama流式错误] {str(e)}"


class LocalProvider(LLMProvider):
    """本地模型提供商(简单规则引擎，无需API)"""

    def chat(self, messages: List[Message], tools: List[ToolDefinition] = None,
             stream: bool = False) -> LLMResponse:
        start_time = time.time()

        # 获取最后一条用户消息
        user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                user_msg = m.content
                break

        # 简单的本地响应生成
        response = self._generate_local_response(user_msg, messages)

        return LLMResponse(
            content=response,
            model="local",
            provider="local",
            latency=time.time() - start_time,
        )

    def _generate_local_response(self, user_input: str, messages: List[Message]) -> str:
        """本地响应生成"""
        user_lower = user_input.lower()

        # 问候
        greetings = ["你好", "hi", "hello", "嗨", "hey"]
        if any(g in user_lower for g in greetings):
            return "你好！我是自我进化AI助手，有什么可以帮你的吗？"

        # 询问能力
        if any(kw in user_lower for kw in ["你能做什么", "功能", "能力", "help"]):
            return ("我可以帮你：\n"
                    "1. 回答问题和知识查询\n"
                    "2. 代码生成和分析\n"
                    "3. 数据处理和分析\n"
                    "4. 学习和记忆新知识\n"
                    "5. 目标规划和任务管理\n"
                    "输入 'help' 查看所有命令")

        # 代码相关
        if any(kw in user_lower for kw in ["代码", "code", "编程", "python", "函数"]):
            return f"关于代码问题，我可以帮你分析。请提供更多细节，比如你想实现什么功能？"

        # 学习相关
        if any(kw in user_lower for kw in ["学习", "learn", "教程", "入门"]):
            return "学习是一个循序渐进的过程。建议你：\n1. 确定学习目标\n2. 制定学习计划\n3. 动手实践\n4. 定期复习"

        # 默认响应
        return f"我理解你的问题：「{user_input[:50]}」。作为本地模式运行的AI，我的能力有限。配置API Key后可以使用更强大的模型。"

    def chat_stream(self, messages: List[Message],
                    tools: List[ToolDefinition] = None) -> Generator[str, None, None]:
        response = self.chat(messages, tools)
        for char in response.content:
            yield char


class LLMEngine:
    """LLM统一引擎 - 管理多个模型提供商"""

    def __init__(self, storage_dir: str = "data/llm"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider: str = "local"
        self.conversation_history: List[Message] = []
        self.system_prompt: str = ""
        self.response_cache: Dict[str, LLMResponse] = {}
        self.usage_stats: Dict[str, Dict[str, int]] = {}

        self._init_providers()
        self._load()

    def _init_providers(self):
        """初始化提供商"""
        # 本地模型(始终可用)
        self.providers["local"] = LocalProvider(ModelConfig(provider="local"))

        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            self.providers["openai"] = OpenAIProvider(ModelConfig(
                provider="openai", model="gpt-4o-mini", api_key=openai_key,
            ))
            self.default_provider = "openai"

        # Claude
        claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if claude_key:
            self.providers["claude"] = ClaudeProvider(ModelConfig(
                provider="claude", model="claude-3-5-sonnet-20241022", api_key=claude_key,
            ))
            if not openai_key:
                self.default_provider = "claude"

        # Ollama
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", method='GET')
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    self.providers["ollama"] = OllamaProvider(ModelConfig(
                        provider="ollama", model=models[0],
                    ))
        except Exception:
            pass

    def _load(self):
        path = os.path.join(self.storage_dir, "llm_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.system_prompt = data.get("system_prompt", "")
                self.default_provider = data.get("default_provider", self.default_provider)
                self.usage_stats = data.get("usage_stats", {})
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "llm_data.json")
        data = {
            "system_prompt": self.system_prompt,
            "default_provider": self.default_provider,
            "usage_stats": self.usage_stats,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_system_prompt(self, prompt: str):
        """设置系统提示"""
        self.system_prompt = prompt
        self._save()

    def set_default_provider(self, provider: str):
        """设置默认提供商"""
        if provider in self.providers:
            self.default_provider = provider
            self._save()

    def configure_provider(self, provider: str, api_key: str = "",
                           model: str = "", base_url: str = ""):
        """配置提供商"""
        if provider == "openai":
            config = ModelConfig(
                provider="openai",
                model=model or "gpt-4o-mini",
                api_key=api_key,
                base_url=base_url,
            )
            self.providers["openai"] = OpenAIProvider(config)
            self.default_provider = "openai"
        elif provider == "claude":
            config = ModelConfig(
                provider="claude",
                model=model or "claude-3-5-sonnet-20241022",
                api_key=api_key,
                base_url=base_url,
            )
            self.providers["claude"] = ClaudeProvider(config)
            self.default_provider = "claude"
        elif provider == "ollama":
            config = ModelConfig(
                provider="ollama",
                model=model or "llama3",
                base_url=base_url or "http://localhost:11434",
            )
            self.providers["ollama"] = OllamaProvider(config)

        self._save()

    def chat(self, user_input: str, context: str = "",
             provider: str = "", tools: List[ToolDefinition] = None,
             use_history: bool = True) -> LLMResponse:
        """聊天"""
        provider_name = provider or self.default_provider
        llm_provider = self.providers.get(provider_name)
        if not llm_provider:
            llm_provider = self.providers["local"]
            provider_name = "local"

        # 构建消息
        messages = []

        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))

        if context:
            messages.append(Message(role="system", content=f"参考上下文:\n{context}"))

        if use_history:
            messages.extend(self.conversation_history[-20:])

        messages.append(Message(role="user", content=user_input))

        # 缓存检查
        cache_key = hashlib.md5(f"{provider_name}:{user_input}".encode()).hexdigest()
        if cache_key in self.response_cache:
            cached = self.response_cache[cache_key]
            cached.cached = True
            return cached

        # 调用
        response = llm_provider.chat(messages, tools)

        # 更新历史
        self.conversation_history.append(Message(role="user", content=user_input))
        self.conversation_history.append(Message(role="assistant", content=response.content))

        # 限制历史长度
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-40:]

        # 缓存
        self.response_cache[cache_key] = response

        # 统计
        if provider_name not in self.usage_stats:
            self.usage_stats[provider_name] = {"requests": 0, "tokens": 0}
        self.usage_stats[provider_name]["requests"] += 1
        self.usage_stats[provider_name]["tokens"] += response.usage.get("total_tokens", 0)

        self._save()
        return response

    def chat_stream(self, user_input: str, context: str = "",
                    provider: str = "") -> Generator[str, None, None]:
        """流式聊天"""
        provider_name = provider or self.default_provider
        llm_provider = self.providers.get(provider_name)
        if not llm_provider:
            yield "无可用的模型提供商"
            return

        messages = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        if context:
            messages.append(Message(role="system", content=f"参考上下文:\n{context}"))
        messages.extend(self.conversation_history[-20:])
        messages.append(Message(role="user", content=user_input))

        full_response = ""
        for chunk in llm_provider.chat_stream(messages):
            full_response += chunk
            yield chunk

        # 更新历史
        self.conversation_history.append(Message(role="user", content=user_input))
        self.conversation_history.append(Message(role="assistant", content=full_response))

    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []

    def get_available_providers(self) -> List[str]:
        """获取可用提供商"""
        return list(self.providers.keys())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "available_providers": list(self.providers.keys()),
            "default_provider": self.default_provider,
            "history_length": len(self.conversation_history),
            "usage_stats": self.usage_stats,
        }


if __name__ == "__main__":
    print("=== LLM集成测试 ===")
    engine = LLMEngine()

    print(f"可用提供商: {engine.get_available_providers()}")
    print(f"默认提供商: {engine.default_provider}")

    # 测试本地模型
    response = engine.chat("你好", provider="local")
    print(f"\n[local] {response.content}")
    print(f"延迟: {response.latency:.3f}s")

    # 如果有OpenAI
    if "openai" in engine.providers:
        response = engine.chat("你好", provider="openai")
        print(f"\n[openai] {response.content[:100]}")

    print(f"\n统计: {engine.get_stats()}")
    print("测试完成!")
