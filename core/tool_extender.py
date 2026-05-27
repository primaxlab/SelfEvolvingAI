"""
================================================================================
层次2：工具扩展系统 (Tool Extension System)
================================================================================

核心能力：
  1. 工具注册表 - 动态注册/发现工具
  2. 工具描述生成 - 从代码自动生成工具文档
  3. 工具学习器 - 从API文档/示例自动学习新工具
  4. 工具编排器 - 组合多个工具解决复杂任务
  5. 工具性能追踪 - 记录工具使用效果、自动择优

设计原则：
  - 插件化架构：热插拔工具
  - 自描述：每个工具自带schema/documentation
  - 失败恢复：工具调用失败自动重试/降级
"""

import json
import os
import re
import time
import importlib
import inspect
import traceback
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from functools import wraps


# ============================================================================
# 数据结构
# ============================================================================

class ToolCategory(Enum):
    FILE = "file"               # 文件操作
    NETWORK = "network"         # 网络请求
    DATA = "data"              # 数据处理
    CODE = "code"              # 代码执行
    AI = "ai"                  # AI模型
    SYSTEM = "system"          # 系统操作
    CUSTOM = "custom"          # 自定义

class ToolStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BROKEN = "broken"
    TESTING = "testing"

@dataclass
class ToolSchema:
    """工具参数Schema"""
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list = None
    examples: list = None

@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory
    parameters: list  # list of ToolSchema
    return_type: str = "any"
    status: ToolStatus = ToolStatus.ACTIVE
    version: str = "1.0.0"
    author: str = "system"
    tags: list = field(default_factory=list)
    examples: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)  # 依赖的其他工具
    timeout: float = 30.0
    retry_count: int = 2
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ToolExecution:
    """工具执行记录"""
    tool_name: str
    params: dict
    result: Any
    success: bool
    error: str = ""
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 工具注册表
# ============================================================================

class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, dict] = {}  # name -> {definition, handler, stats}
        self._execution_history: list[ToolExecution] = []
        self._categories: dict[ToolCategory, list] = {}
        self._aliases: dict[str, str] = {}
        self._hooks: dict[str, list[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_error": [],
            "on_register": [],
        }

    # ---- 注册 ----

    def register(self,
                 name: str,
                 handler: Callable,
                 description: str,
                 parameters: list = None,
                 category: ToolCategory = ToolCategory.CUSTOM,
                 tags: list = None,
                 examples: list = None,
                 timeout: float = 30.0,
                 retry_count: int = 2,
                 auto_schema: bool = True,
                 **kwargs) -> 'ToolRegistry':
        """注册工具"""
        # 自动生成参数schema
        if auto_schema and parameters is None:
            parameters = self._infer_schema(handler)

        definition = ToolDefinition(
            name=name,
            description=description,
            category=category,
            parameters=parameters or [],
            tags=tags or [],
            examples=examples or [],
            timeout=timeout,
            retry_count=retry_count,
            **{k: v for k, v in kwargs.items() if k in ToolDefinition.__dataclass_fields__}
        )

        self._tools[name] = {
            'definition': definition,
            'handler': handler,
            'stats': {
                'total_calls': 0,
                'success_calls': 0,
                'failed_calls': 0,
                'avg_duration': 0.0,
                'last_used': None,
                'success_rate': 0.0,
            }
        }

        # 分类索引
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        # 触发注册钩子
        for hook in self._hooks.get("on_register", []):
            try:
                hook(name, definition)
            except Exception:
                pass

        return self

    def alias(self, name: str, alias_name: str):
        """添加别名"""
        if name in self._tools:
            self._aliases[alias_name] = name

    def _infer_schema(self, handler: Callable) -> list:
        """从函数签名推断参数schema"""
        schemas = []
        try:
            sig = inspect.signature(handler)
            doc = inspect.getdoc(handler) or ""

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    annotation = param.annotation
                    if annotation == int:
                        param_type = "integer"
                    elif annotation == float:
                        param_type = "number"
                    elif annotation == bool:
                        param_type = "boolean"
                    elif annotation == list:
                        param_type = "array"
                    elif annotation == dict:
                        param_type = "object"
                    else:
                        param_type = str(annotation)

                required = param.default == inspect.Parameter.empty
                default = None if required else param.default

                # 从docstring提取描述
                desc = ""
                for line in doc.split('\n'):
                    if param_name in line:
                        desc = line.strip().lstrip('- :').strip()
                        break

                schemas.append(ToolSchema(
                    name=param_name,
                    type=param_type,
                    description=desc or f"参数 {param_name}",
                    required=required,
                    default=default,
                ))
        except Exception:
            pass
        return schemas

    # ---- 发现 ----

    def discover(self, module_path: str, prefix: str = "tool_"):
        """从模块自动发现工具函数"""
        try:
            module = importlib.import_module(module_path)
            for attr_name in dir(module):
                if attr_name.startswith(prefix):
                    attr = getattr(module, attr_name)
                    if callable(attr):
                        name = attr_name[len(prefix):]
                        doc = inspect.getdoc(attr) or name
                        self.register(
                            name=name,
                            handler=attr,
                            description=doc.split('\n')[0] if doc else name,
                        )
        except Exception as e:
            print(f"[ToolRegistry] 模块发现失败 {module_path}: {e}")

    def discover_from_file(self, file_path: str):
        """从单个文件发现工具"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("dynamic_tools", file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '_is_tool'):
                    self.register(
                        name=getattr(attr, '_tool_name', attr_name),
                        handler=attr,
                        description=getattr(attr, '_tool_description', ''),
                        parameters=getattr(attr, '_tool_params', []),
                    )

    # ---- 执行 ----

    def execute(self, name_or_alias: str, **params) -> ToolExecution:
        """执行工具"""
        name = self._aliases.get(name_or_alias, name_or_alias)

        if name not in self._tools:
            return ToolExecution(
                tool_name=name,
                params=params,
                result=None,
                success=False,
                error=f"工具 '{name}' 未找到",
            )

        tool = self._tools[name]
        definition = tool['definition']
        handler = tool['handler']

        # 验证参数
        errors = self._validate_params(definition, params)
        if errors:
            return ToolExecution(
                tool_name=name,
                params=params,
                result=None,
                success=False,
                error=f"参数验证失败: {', '.join(errors)}",
            )

        # before 钩子
        for hook in self._hooks.get("before_execute", []):
            try:
                hook(name, params)
            except Exception:
                pass

        # 执行（含重试）
        last_error = ""
        for attempt in range(definition.retry_count + 1):
            start = time.time()
            try:
                result = handler(**params)
                duration = time.time() - start

                exec_record = ToolExecution(
                    tool_name=name,
                    params=params,
                    result=result,
                    success=True,
                    duration=duration,
                )

                # 更新统计
                stats = tool['stats']
                stats['total_calls'] += 1
                stats['success_calls'] += 1
                stats['last_used'] = time.time()
                stats['avg_duration'] = (
                    stats['avg_duration'] * (stats['total_calls'] - 1) + duration
                ) / stats['total_calls']
                stats['success_rate'] = stats['success_calls'] / stats['total_calls']
                self._execution_history.append(exec_record)

                # after 钩子
                for hook in self._hooks.get("after_execute", []):
                    try:
                        hook(name, result)
                    except Exception:
                        pass

                return exec_record

            except Exception as e:
                last_error = str(e)
                duration = time.time() - start

                if attempt < definition.retry_count:
                    time.sleep(0.5 * (attempt + 1))
                    continue

        # 全部失败
        stats = tool['stats']
        stats['total_calls'] += 1
        stats['failed_calls'] += 1
        stats['success_rate'] = stats['success_calls'] / max(1, stats['total_calls'])

        failed_record = ToolExecution(
            tool_name=name,
            params=params,
            result=None,
            success=False,
            error=last_error,
            duration=time.time() - start,
        )
        self._execution_history.append(failed_record)

        for hook in self._hooks.get("on_error", []):
            try:
                hook(name, last_error)
            except Exception:
                pass

        return failed_record

    def _validate_params(self, definition: ToolDefinition, params: dict) -> list:
        """验证参数"""
        errors = []
        for p in definition.parameters:
            if p.required and p.name not in params:
                errors.append(f"缺少必要参数: {p.name}")
        return errors

    # ---- 学习 ----

    def learn_from_api_doc(self, api_spec: dict) -> list:
        """
        从API文档自动学习并注册工具
        支持 OpenAPI/Swagger 格式
        """
        registered = []

        # OpenAPI 3.x
        if 'paths' in api_spec:
            for path, methods in api_spec['paths'].items():
                for method, spec in methods.items():
                    if method.lower() not in ('get', 'post', 'put', 'delete', 'patch'):
                        continue

                    tool_name = spec.get('operationId',
                        f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}")

                    params = []
                    if 'parameters' in spec:
                        for p in spec['parameters']:
                            params.append(ToolSchema(
                                name=p['name'],
                                type=p.get('schema', {}).get('type', 'string'),
                                description=p.get('description', ''),
                                required=p.get('required', False),
                            ))

                    # 创建处理函数
                    def make_handler(path, method, base_url=""):
                        async def handler(**kwargs):
                            import urllib.request
                            import urllib.parse
                            url = base_url + path
                            for k, v in kwargs.items():
                                url = url.replace(f'{{{k}}}', str(v))
                            data = json.dumps(kwargs).encode() if method in ('post', 'put') else None
                            req = urllib.request.Request(url, data=data, method=method.upper())
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                return json.loads(resp.read())
                        return handler

                    self.register(
                        name=tool_name,
                        handler=make_handler(path, method),
                        description=spec.get('summary', spec.get('description', '')),
                        parameters=params,
                        category=ToolCategory.NETWORK,
                        tags=['api', method.lower()],
                    )
                    registered.append(tool_name)

        return registered

    def learn_from_code(self, code: str) -> Optional[str]:
        """
        从代码片段自动提取并注册为工具
        """
        # 提取函数定义
        pattern = r'def\s+(\w+)\s*\((.*?)\)\s*:(?:\s*"""(.*?)""")?'
        matches = re.findall(pattern, code, re.DOTALL)

        for func_name, params_str, docstring in matches:
            doc_lines = docstring.strip().split('\n') if docstring else []
            description = doc_lines[0] if doc_lines else func_name

            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        pname, ptype = param.split(':', 1)
                        params.append(ToolSchema(
                            name=pname.strip(),
                            type=ptype.strip(),
                        ))
                    else:
                        params.append(ToolSchema(
                            name=param,
                            type='any',
                            required=True,
                        ))

            # 动态创建函数
            namespace = {}
            exec(f"""
def {func_name}({params_str}):
    {code}
""", namespace)

            if func_name in namespace:
                self.register(
                    name=func_name,
                    handler=namespace[func_name],
                    description=description,
                    parameters=params,
                )
                return func_name
        return None

    # ---- 钩子 ----

    def add_hook(self, event: str, callback: Callable):
        """添加钩子"""
        if event in self._hooks:
            self._hooks[event].append(callback)

    # ---- 查询 ----

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        t = self._tools.get(name)
        return t['definition'] if t else None

    def list_tools(self, category: ToolCategory = None, tag: str = None) -> list:
        """列出工具"""
        results = []
        for name, tool in self._tools.items():
            if category and tool['definition'].category != category:
                continue
            if tag and tag not in tool['definition'].tags:
                continue
            results.append({
                'name': name,
                'description': tool['definition'].description,
                'category': tool['definition'].category.value,
                'stats': tool['stats'],
            })
        return results

    def get_best_tool_for(self, task_description: str) -> Optional[str]:
        """根据任务描述推荐最佳工具（基于历史成功率）"""
        best_score = -1
        best_tool = None

        keywords = set(task_description.lower().split())

        for name, tool in self._tools.items():
            score = 0
            # 名称匹配
            if any(kw in name.lower() for kw in keywords):
                score += 3
            # 描述匹配
            if any(kw in tool['definition'].description.lower() for kw in keywords):
                score += 2
            # 标签匹配
            if any(kw in tag for tag in tool['definition'].tags for kw in keywords):
                score += 1
            # 成功率加权
            score *= tool['stats']['success_rate'] if tool['stats']['total_calls'] > 0 else 0.5

            if score > best_score:
                best_score = score
                best_tool = name

        return best_tool

    def get_stats(self) -> dict:
        """获取整体统计"""
        total = sum(t['stats']['total_calls'] for t in self._tools.values())
        success = sum(t['stats']['success_calls'] for t in self._tools.values())
        return {
            'total_tools': len(self._tools),
            'total_executions': total,
            'overall_success_rate': success / max(1, total),
            'categories': {k.value: len(v) for k, v in self._categories.items()},
        }

    def export_manifest(self) -> dict:
        """导出工具清单（供AI理解可用能力）"""
        tools_info = []
        for name, tool in self._tools.items():
            d = tool['definition']
            tools_info.append({
                'name': name,
                'description': d.description,
                'category': d.category.value,
                'parameters': [
                    {
                        'name': p.name,
                        'type': p.type,
                        'description': p.description,
                        'required': p.required,
                    }
                    for p in d.parameters
                ],
                'examples': d.examples,
            })

        return {
            'tools': tools_info,
            'total': len(tools_info),
            'generated_at': datetime.now().isoformat(),
        }


# ============================================================================
# 工具装饰器
# ============================================================================

def tool(name: str = None, description: str = "",
         category: ToolCategory = ToolCategory.CUSTOM,
         tags: list = None, **kwargs):
    """工具装饰器：标记函数为可注册工具"""
    def decorator(func):
        func._is_tool = True
        func._tool_name = name or func.__name__
        func._tool_description = description or inspect.getdoc(func) or ""
        func._tool_params = kwargs.pop('parameters', None)
        func._tool_tags = tags or []
        func._tool_category = category

        @wraps(func)
        def wrapper(*args, **kwargs_inner):
            return func(*args, **kwargs_inner)
        return wrapper
    return decorator


# ============================================================================
# 工具编排器
# ============================================================================

class ToolOrchestrator:
    """
    工具编排器 - 将多个工具组合成工作流
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.pipelines: dict[str, list] = {}

    def define_pipeline(self, name: str, steps: list):
        """
        定义工具流水线
        steps: [{"tool": "tool_name", "params": {...}, "output_key": "key"}, ...]
        每个步骤的输出可作为后续步骤的输入（用 {{key}} 引用）
        """
        self.pipelines[name] = steps

    def run_pipeline(self, name: str, initial_context: dict = None) -> dict:
        """执行工具流水线"""
        if name not in self.pipelines:
            return {"error": f"流水线 '{name}' 未定义"}

        context = initial_context or {}
        results = []

        for step in self.pipelines[name]:
            # 解析参数中的引用
            params = {}
            for k, v in step.get('params', {}).items():
                if isinstance(v, str) and v.startswith('{{') and v.endswith('}}'):
                    ref_key = v[2:-2].strip()
                    params[k] = context.get(ref_key, v)
                else:
                    params[k] = v

            # 执行工具
            exec_result = self.registry.execute(step['tool'], **params)
            results.append(exec_result)

            if exec_result.success:
                output_key = step.get('output_key')
                if output_key:
                    context[output_key] = exec_result.result
            else:
                if not step.get('continue_on_error', False):
                    return {
                        "success": False,
                        "error": exec_result.error,
                        "failed_step": step['tool'],
                        "results": results,
                        "context": context,
                    }

        return {
            "success": True,
            "results": results,
            "context": context,
        }

    def auto_pipeline(self, task: str, available_tools: list = None) -> list:
        """根据任务自动生成工具流水线"""
        tools = available_tools or [t['name'] for t in self.registry.list_tools()]

        # 智能编排：尝试找到能完成任务的最小工具组合
        best_tool = self.registry.get_best_tool_for(task)
        if best_tool:
            return [{"tool": best_tool, "params": {}, "output_key": "result"}]
        return []


# ============================================================================
# 工具学习器
# ============================================================================

class ToolLearner:
    """
    工具学习器 - 从文档/示例中自动学习新工具

    学习来源：
    1. API文档 (OpenAPI/Swagger)
    2. 代码仓库
    3. 使用示例
    4. 错误日志（从失败中学习正确用法）
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.learned_count = 0

    def learn_from_url(self, url: str) -> int:
        """从URL获取API文档并学习"""
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
            registered = self.registry.learn_from_api_doc(data)
            self.learned_count += len(registered)
            return len(registered)
        except Exception as e:
            print(f"[ToolLearner] 学习失败: {e}")
            return 0

    def learn_from_failure(self, failure: ToolExecution) -> Optional[str]:
        """
        从失败中学习 — 分析错误，尝试生成修正版本的工具
        """
        # 分析错误模式
        error = failure.error.lower()

        # 参数类型错误 → 尝试自动转换
        if 'type' in error or 'expected' in error:
            # 生成包装器
            def make_safe_handler(original_handler, param_name, target_type):
                def safe_handler(**kwargs):
                    if param_name in kwargs:
                        kwargs[param_name] = target_type(kwargs[param_name])
                    return original_handler(**kwargs)
                return safe_handler

        return None

    def learn_from_example(self, tool_name: str, example_input: dict,
                           example_output: Any):
        """从一对输入输出示例中学习工具行为模式"""
        # 记录示例作为工具的ground truth
        tool = self.registry._tools.get(tool_name)
        if tool:
            if 'examples' not in tool['definition'].__dict__:
                tool['definition'].examples = []
            tool['definition'].examples.append({
                'input': example_input,
                'output': str(example_output)[:500],
            })
            return True
        return False

    def generate_tool_from_description(self, description: str) -> Optional[str]:
        """
        根据自然语言描述，尝试生成一个工具
        （这需要LLM能力，此处提供框架）
        """
        # 框架占位 — 实际使用时由LLM填充
        keywords = description.lower()

        if '文件' in keywords or 'file' in keywords or '读取' in keywords:
            tool_name = "auto_read_file"
            def handler(path: str) -> str:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            self.registry.register(
                name=tool_name,
                handler=handler,
                description="自动生成: 读取文件内容",
                category=ToolCategory.FILE,
            )
            return tool_name

        if '搜索' in keywords or 'search' in keywords or '查找' in keywords:
            tool_name = "auto_search_content"
            def handler(path: str, pattern: str) -> list:
                import re
                results = []
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                results.append(f"{i}: {line.strip()}")
                except Exception:
                    pass
                return results
            self.registry.register(
                name=tool_name,
                handler=handler,
                description="自动生成: 在文件中搜索内容",
                category=ToolCategory.FILE,
            )
            return tool_name

        if '请求' in keywords or 'http' in keywords or 'api' in keywords:
            tool_name = "auto_http_request"
            def handler(url: str, method: str = "GET", data: dict = None) -> dict:
                import urllib.request
                json_data = json.dumps(data).encode() if data else None
                req = urllib.request.Request(url, data=json_data, method=method.upper())
                req.add_header('Content-Type', 'application/json')
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read())
            self.registry.register(
                name=tool_name,
                handler=handler,
                description="自动生成: HTTP请求工具",
                category=ToolCategory.NETWORK,
            )
            return tool_name

        return None


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    registry = ToolRegistry()

    # 注册内置工具
    @tool(name="read_file", description="读取文件内容",
          category=ToolCategory.FILE, tags=["file", "read"])
    def read_file(path: str, encoding: str = "utf-8") -> str:
        """读取指定路径的文件内容"""
        with open(path, 'r', encoding=encoding) as f:
            return f.read()

    @tool(name="write_file", description="写入文件内容",
          category=ToolCategory.FILE, tags=["file", "write"])
    def write_file(path: str, content: str) -> bool:
        """写入内容到文件"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    @tool(name="search_content", description="搜索文件内容",
          category=ToolCategory.DATA, tags=["search"])
    def search_content(path: str, pattern: str) -> list:
        """在文件中搜索匹配的内容"""
        results = []
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if pattern in line:
                    results.append({"line": i, "content": line.strip()})
        return results

    # 注册工具
    registry.register(
        name="read_file",
        handler=read_file,
        description="读取文件内容，支持指定编码",
        category=ToolCategory.FILE,
        tags=["file", "read"],
    )

    registry.register(
        name="write_file",
        handler=write_file,
        description="写入内容到文件",
        category=ToolCategory.FILE,
        tags=["file", "write"],
    )

    # 测试执行
    print("=== 工具列表 ===")
    for t in registry.list_tools():
        print(f"  {t['name']}: {t['description']}")

    print("\n=== 最佳工具推荐 ===")
    best = registry.get_best_tool_for("读取一个文件")
    print(f"  推荐: {best}")

    print("\n=== 工具统计 ===")
    print(registry.get_stats())

    # 工具学习器
    learner = ToolLearner(registry)
    learner.learn_from_example("read_file",
                               {"path": "/tmp/test.txt", "encoding": "utf-8"},
                               "file content here")

    generated = learner.generate_tool_from_description("帮我搜索文件中的内容")
    print(f"\n=== 自动生成工具: {generated} ===")

    # 导出清单
    print("\n=== 工具清单 ===")
    print(json.dumps(registry.export_manifest(), ensure_ascii=False, indent=2))