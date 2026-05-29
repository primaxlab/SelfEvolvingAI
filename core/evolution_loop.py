"""
================================================================================
进化主循环 (Evolution Main Loop) - 终极版
================================================================================

整合全部64个模块，实现自我进化的核心循环：

  感知 → 记忆 → 思考 → 行动 → 反思 → 进化

模块清单（64个）：
  [核心] 1-7: 记忆、工具扩展、代码自改进、元认知、知识图谱、目标规划、反思循环
  [扩展一] 8-17: 主动探索、协作、情感智能、因果推理、迁移学习、
                 持续学习、知识蒸馏、创造性思维、多模态、对抗鲁棒性
  [扩展二] 18-32: 元学习、强化学习、注意力、上下文感知、自愈、
                  知识进化、预测学习、分布式协作、自适应架构、
                  神经符号、自监督、记忆宫殿、决策模式、自适应学习率、联邦学习
  [扩展三] 33-44: 提示工程、任务编排、代码生成、测试自动化、自动文档、
                  性能优化、配置管理、日志分析、监控告警、备份恢复、API网关、消息队列
  [扩展四] 45-54: 缓存管理、调度器、向量数据库、会话管理、自然语言理解、
                  推荐引擎、数据管道、特征工程、工作流引擎、通知中心
  [扩展五] 55-64: 加密服务、全文检索、限流器、插件系统、流式处理、
                  分布式锁、数据同步、模型服务、Web服务器、国际化
"""

import json
import os
import time
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field, asdict

# ============================================================================
# 导入全部44个模块
# ============================================================================

# --- 核心模块 (1-7) ---
from .memory import MemoryManager, MemoryType, MemoryImportance
from .tool_extender import ToolRegistry, ToolOrchestrator, ToolLearner, ToolCategory
from .self_improver import CodeSelfImprover
from .metacognition import MetacognitionEngine
from .knowledge_graph import KnowledgeGraphEngine
from .goal_planning import GoalPlanningEngine, TaskPriority
from .reflection import ReflectionEngine

# --- 扩展一 (8-17) ---
from .active_exploration import ActiveExplorationEngine
from .collaboration import CollaborationEngine
from .emotional_intelligence import EmotionalIntelligenceEngine
from .causal_reasoning import CausalReasoningEngine
from .transfer_learning import TransferLearningEngine
from .continual_learning import ContinualLearningEngine
from .knowledge_distillation import KnowledgeDistillationEngine
from .creative_thinking import CreativeThinkingEngine
from .multimodal import MultimodalPerceptionEngine as MultimodalEngine
from .adversarial_robustness import AdversarialRobustnessEngine

# --- 扩展二 (18-32) ---
from .meta_learning import MetaLearningEngine
from .reinforcement_learning import ReinforcementLearningEngine
from .attention import AttentionEngine
from .context_awareness import ContextAwarenessEngine
from .self_healing import SelfHealingEngine
from .knowledge_evolution import KnowledgeEvolutionEngine
from .predictive_learning import PredictiveLearningEngine
from .distributed_collaboration import DistributedCollaborationEngine
from .adaptive_architecture import AdaptiveArchitectureEngine
from .neuro_symbolic import NeuroSymbolicEngine
from .self_supervised import SelfSupervisedLearningEngine as SelfSupervisedEngine
from .memory_palace import MemoryPalaceEngine
from .decision_patterns import DecisionPatternLearningEngine as DecisionPatternsEngine
from .adaptive_learning_rate import AdaptiveLearningRateEngine
from .federated_learning import FederatedLearningEngine

# --- 扩展三 (33-44) ---
from .prompt_engineering import AdaptivePromptEngineeringEngine as PromptEngineeringEngine
from .task_orchestration import TaskOrchestrationEngine
from .code_generation import CodeGenerationOptimizationEngine as CodeGenerationEngine
from .test_automation import TestAutomationEngine
from .auto_documentation import AutoDocumentationEngine
from .performance_optimization import PerformanceOptimizationEngine
from .configuration_management import ConfigurationManager
from .log_analysis import LogAnalysisEngine
from .monitoring_alerting import MonitoringAlertingEngine
from .backup_recovery import BackupRecoveryEngine
from .api_gateway import APIGatewayEngine
from .message_queue import MessageQueueEngine

# --- 扩展四 (45-54) ---
from .cache_manager import CacheManager
from .scheduler import SchedulerEngine
from .vector_store import VectorStoreEngine
from .session_manager import SessionManagerEngine
from .nlu_engine import NLUEngine
from .recommendation import RecommendationEngine
from .data_pipeline import DataPipelineEngine
from .feature_engineering import FeatureEngineeringEngine
from .workflow_engine import WorkflowEngine
from .notification_center import NotificationCenterEngine

# --- 扩展五 (55-64) ---
from .encryption_service import EncryptionServiceEngine
from .search_engine import SearchEngine
from .rate_limiter import RateLimiterEngine
from .plugin_system import PluginSystemEngine
from .stream_processor import StreamProcessorEngine
from .distributed_lock import DistributedLockEngine
from .data_sync import DataSyncEngine
from .model_serving import ModelServingEngine
from .web_server import WebServerEngine
from .i18n import I18nEngine
from .llm_integration import LLMEngine, Message, ToolDefinition
from .desktop_automation import DesktopAutomationEngine
from .process_manager import ProcessManagerEngine
from .browser_automation import BrowserAutomationEngine
from .permission_control import PermissionControlEngine, Permission
from .toolkit import ToolKit


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class EvolutionState:
    """进化状态"""
    version: str = "4.0.0"
    generation: int = 0
    total_interactions: int = 0
    total_evolutions: int = 0
    last_evolution: float = 0.0
    capabilities: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    modules_loaded: int = 0


@dataclass
class Interaction:
    """交互记录"""
    id: str
    user_input: str
    ai_response: str
    confidence: float
    domain: str
    tools_used: list = field(default_factory=list)
    modules_involved: list = field(default_factory=list)
    success: bool = True
    feedback: str = ""
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 自我进化AI核心 - 超级版（64模块集成）
# ============================================================================

class SelfEvolvingAI:
    """
    自我进化AI核心引擎 - 超级版

    集成全部64个模块的完整进化循环：

    感知: 上下文感知 + 多模态 + 注意力 + NLU
    记忆: 记忆系统 + 记忆宫殿 + 知识图谱 + 向量数据库
    思考: 元认知 + 因果推理 + 神经符号 + 创造性思维 + 推荐
    行动: 目标规划 + 任务编排 + 工具调用 + 代码生成 + 工作流
    反思: 反思循环 + 决策模式 + 预测学习
    进化: 代码自改进 + 知识进化 + 自适应架构
    基础: 缓存 + 调度 + 会话 + 管道 + 特征 + 通知
    安全: 加密 + 限流 + 分布式锁
    扩展: 全文检索 + 插件 + 流式 + 同步 + 模型服务 + Web + 国际化
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = project_dir or os.getcwd()
        self.storage_dir = os.path.join(self.project_dir, '.evolution')
        os.makedirs(self.storage_dir, exist_ok=True)

        sd = lambda name: os.path.join(self.storage_dir, name)

        # ==================== 核心模块 (1-7) ====================
        self.memory = MemoryManager(sd('memory'))
        self.tool_registry = ToolRegistry()
        self.tool_orchestrator = ToolOrchestrator(self.tool_registry)
        self.tool_learner = ToolLearner(self.tool_registry)
        self.code_improver = CodeSelfImprover(self.project_dir)
        self.metacognition = MetacognitionEngine(sd('metacognition'))
        self.knowledge_graph = KnowledgeGraphEngine(sd('knowledge_graph'))
        self.goal_planner = GoalPlanningEngine(sd('goals'))
        self.reflection = ReflectionEngine(sd('reflection'))

        # ==================== 扩展一 (8-17) ====================
        self.active_exploration = ActiveExplorationEngine(sd('active_exploration'))
        self.collaboration = CollaborationEngine(sd('collaboration'))
        self.emotional_intelligence = EmotionalIntelligenceEngine(sd('emotional'))
        self.causal_reasoning = CausalReasoningEngine(sd('causal'))
        self.transfer_learning = TransferLearningEngine(sd('transfer'))
        self.continual_learning = ContinualLearningEngine(sd('continual'))
        self.knowledge_distillation = KnowledgeDistillationEngine(sd('distillation'))
        self.creative_thinking = CreativeThinkingEngine(sd('creative'))
        self.multimodal = MultimodalEngine(sd('multimodal'))
        self.adversarial_robustness = AdversarialRobustnessEngine(sd('adversarial'))

        # ==================== 扩展二 (18-32) ====================
        self.meta_learning = MetaLearningEngine(sd('meta_learning'))
        self.reinforcement_learning = ReinforcementLearningEngine(sd('rl'))
        self.attention = AttentionEngine(sd('attention'))
        self.context_awareness = ContextAwarenessEngine(sd('context'))
        self.self_healing = SelfHealingEngine(sd('self_healing'))
        self.knowledge_evolution = KnowledgeEvolutionEngine(sd('knowledge_evolution'))
        self.predictive_learning = PredictiveLearningEngine(sd('predictive'))
        self.distributed = DistributedCollaborationEngine(sd('distributed'))
        self.adaptive_arch = AdaptiveArchitectureEngine(sd('adaptive_arch'))
        self.neuro_symbolic = NeuroSymbolicEngine(sd('neuro_symbolic'))
        self.self_supervised = SelfSupervisedEngine(sd('self_supervised'))
        self.memory_palace = MemoryPalaceEngine(sd('memory_palace'))
        self.decision_patterns = DecisionPatternsEngine(sd('decision_patterns'))
        self.adaptive_lr = AdaptiveLearningRateEngine(sd('adaptive_lr'))
        self.federated = FederatedLearningEngine(sd('federated'))

        # ==================== 扩展三 (33-44) ====================
        self.prompt_engineering = PromptEngineeringEngine(sd('prompt'))
        self.task_orchestration = TaskOrchestrationEngine(sd('task_orchestration'))
        self.code_generation = CodeGenerationEngine(sd('code_generation'))
        self.test_automation = TestAutomationEngine(sd('test_automation'))
        self.auto_documentation = AutoDocumentationEngine(sd('documentation'))
        self.performance = PerformanceOptimizationEngine(sd('performance'))
        self.configuration = ConfigurationManager(sd('configuration'))
        self.log_analysis = LogAnalysisEngine(sd('logs'))
        self.monitoring = MonitoringAlertingEngine(sd('monitoring'))
        self.backup = BackupRecoveryEngine(sd('backup'), sd('backups'))
        self.api_gateway = APIGatewayEngine(sd('gateway'))
        self.message_queue = MessageQueueEngine(sd('mq'))

        # ==================== 扩展四 (45-54) ====================
        self.cache = CacheManager(sd('cache'))
        self.scheduler = SchedulerEngine(sd('scheduler'))
        self.vector_store = VectorStoreEngine(sd('vector_store'))
        self.session_manager = SessionManagerEngine(sd('sessions'))
        self.nlu = NLUEngine(sd('nlu'))
        self.recommendation = RecommendationEngine(sd('recommendation'))
        self.data_pipeline = DataPipelineEngine(sd('pipeline'))
        self.feature_eng = FeatureEngineeringEngine(sd('features'))
        self.workflow = WorkflowEngine(sd('workflow'))
        self.notification = NotificationCenterEngine(sd('notifications'))

        # ==================== 扩展五 (55-64) ====================
        self.encryption = EncryptionServiceEngine(sd('encryption'))
        self.search_engine = SearchEngine(sd('search'))
        self.rate_limiter = RateLimiterEngine(sd('ratelimit'))
        self.plugin_system = PluginSystemEngine(sd('plugins'))
        self.stream_processor = StreamProcessorEngine(sd('stream'))
        self.distributed_lock = DistributedLockEngine(sd('locks'))
        self.data_sync = DataSyncEngine(sd('sync'))
        self.model_serving = ModelServingEngine(sd('model_serving'))
        self.web_server = WebServerEngine(sd('webserver'))
        self.i18n = I18nEngine(sd('i18n'))

        # ==================== AI模型集成 ====================
        self.llm = LLMEngine(sd('llm'))
        self.llm.set_system_prompt(
            "你是自我进化AI助手，拥有65个智能模块和计算机操控能力。"
            "你能记忆、学习、推理、创造，并不断自我进化。"
            "你可以操作计算机：执行命令、控制鼠标键盘、浏览网页。"
            "请用中文回答，保持简洁准确。"
        )

        # ==================== 计算机操控层 ====================
        self.desktop = DesktopAutomationEngine(sd('desktop'))
        self.process_mgr = ProcessManagerEngine(sd('process'))
        self.browser = BrowserAutomationEngine(sd('browser'))
        self.permissions = PermissionControlEngine(sd('permissions'))
        self.toolkit = ToolKit(sd('toolkit'))

        # 注册工具到LLM
        self._register_tools()

        # ==================== 系统状态 ====================
        self.state = EvolutionState(modules_loaded=70)
        self.interactions: list = []

        # 加载持久化状态
        self._load_state()

        # 注册内置工具
        self._register_builtin_tools()

        # 记录启动日志
        self.log_analysis.add_log("info", "自我进化AI系统启动", "system",
                                  module="evolution_loop")

    def _register_tools(self):
        """注册工具供LLM调用"""
        self._tools = {
            "execute_command": {
                "handler": self._tool_execute_command,
                "definition": ToolDefinition(
                    name="execute_command",
                    description="执行系统命令(如: ls, dir, python script.py)",
                    parameters={"type": "object", "properties": {
                        "command": {"type": "string", "description": "要执行的命令"},
                    }, "required": ["command"]},
                ),
            },
            "read_file": {
                "handler": self._tool_read_file,
                "definition": ToolDefinition(
                    name="read_file",
                    description="读取文件内容",
                    parameters={"type": "object", "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                    }, "required": ["path"]},
                ),
            },
            "write_file": {
                "handler": self._tool_write_file,
                "definition": ToolDefinition(
                    name="write_file",
                    description="写入文件内容",
                    parameters={"type": "object", "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"},
                    }, "required": ["path", "content"]},
                ),
            },
            "open_url": {
                "handler": self._tool_open_url,
                "definition": ToolDefinition(
                    name="open_url",
                    description="打开网页并获取内容",
                    parameters={"type": "object", "properties": {
                        "url": {"type": "string", "description": "网址"},
                    }, "required": ["url"]},
                ),
            },
            "screenshot": {
                "handler": self._tool_screenshot,
                "definition": ToolDefinition(
                    name="screenshot",
                    description="截取屏幕截图",
                    parameters={"type": "object", "properties": {}},
                ),
            },
            "click": {
                "handler": self._tool_click,
                "definition": ToolDefinition(
                    name="click",
                    description="点击屏幕指定位置",
                    parameters={"type": "object", "properties": {
                        "x": {"type": "integer", "description": "X坐标"},
                        "y": {"type": "integer", "description": "Y坐标"},
                    }, "required": ["x", "y"]},
                ),
            },
            "type_text": {
                "handler": self._tool_type_text,
                "definition": ToolDefinition(
                    name="type_text",
                    description="输入文字",
                    parameters={"type": "object", "properties": {
                        "text": {"type": "string", "description": "要输入的文字"},
                    }, "required": ["text"]},
                ),
            },
            "search_web": {
                "handler": self._tool_search_web,
                "definition": ToolDefinition(
                    name="search_web",
                    description="搜索网页",
                    parameters={"type": "object", "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                    }, "required": ["query"]},
                ),
            },
        }

        # 注册Toolkit工具（15个实用工具）
        toolkit_defs = self.toolkit.get_tool_definitions()
        for tdef in toolkit_defs:
            self._tools[tdef["name"]] = {
                "handler": lambda params, tn=tdef["name"]: self._tool_toolkit(tn, params),
                "definition": ToolDefinition(
                    name=tdef["name"],
                    description=tdef["description"],
                    parameters=tdef["parameters"],
                ),
            }

    def _check_and_execute_tool(self, tool_name: str, params: dict) -> str:
        """检查权限并执行工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"未知工具: {tool_name}"

        # 权限检查
        perm_map = {
            "execute_command": Permission.SYSTEM_COMMAND.value,
            "read_file": Permission.FILE_READ.value,
            "write_file": Permission.FILE_WRITE.value,
            "open_url": Permission.BROWSER_NAVIGATE.value,
            "screenshot": Permission.SCREENSHOT.value,
            "click": Permission.MOUSE_CLICK.value,
            "type_text": Permission.KEYBOARD_INPUT.value,
            "search_web": Permission.NETWORK_REQUEST.value,
        }

        perm = perm_map.get(tool_name)
        if perm:
            target = str(params)[:200]
            check = self.permissions.check_permission(perm, target)
            if not check["allowed"]:
                return f"权限不足: {check['reason']}"
            if check.get("needs_confirmation"):
                self.log_analysis.add_log("warning",
                    f"高风险操作需要确认: {tool_name}({target})",
                    "permission", module="permission_control")

        # 执行
        try:
            handler = tool["handler"]
            return handler(params)
        except Exception as e:
            return f"工具执行失败: {str(e)}"

    def _tool_execute_command(self, params: dict) -> str:
        command = params.get("command", "")
        result = self.process_mgr.execute(command, timeout=30)
        if result["success"]:
            return f"命令执行成功:\n{result['stdout'][:1000]}"
        else:
            return f"命令执行失败:\n{result.get('stderr', result.get('error', ''))[:500]}"

    def _tool_read_file(self, params: dict) -> str:
        path = params.get("path", "")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(10000)
            return f"文件内容:\n{content}"
        except Exception as e:
            return f"读取失败: {e}"

    def _tool_write_file(self, params: dict) -> str:
        path = params.get("path", "")
        content = params.get("content", "")
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"已写入: {path} ({len(content)} 字符)"
        except Exception as e:
            return f"写入失败: {e}"

    def _tool_open_url(self, params: dict) -> str:
        url = params.get("url", "")
        result = self.browser.open_url(url)
        if result.get("success"):
            return f"页面: {result.get('title', '')}\n内容: {result.get('text_preview', '')[:500]}"
        return f"打开失败: {result.get('error', '')}"

    def _tool_screenshot(self, params: dict) -> str:
        path = self.desktop.screenshot()
        return f"截图已保存: {path}" if path else "截图失败"

    def _tool_click(self, params: dict) -> str:
        x, y = params.get("x", 0), params.get("y", 0)
        success = self.desktop.click(x, y)
        return f"点击 ({x}, {y}): {'成功' if success else '失败'}"

    def _tool_type_text(self, params: dict) -> str:
        text = params.get("text", "")
        success = self.desktop.type_text(text)
        return f"输入: '{text[:50]}': {'成功' if success else '失败'}"

    def _tool_search_web(self, params: dict) -> str:
        query = params.get("query", "")
        result = self.browser.search_web(query)
        if result.get("success"):
            return f"搜索结果: {result.get('text_preview', '')[:500]}"
        return f"搜索失败: {result.get('error', '')}"

    def _tool_toolkit(self, tool_name: str, params: dict) -> str:
        """Toolkit工具统一处理器"""
        result = self.toolkit.execute_tool(tool_name, params)
        if isinstance(result, dict):
            if result.get("success", True):
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                return f"工具执行失败: {result.get('error', '未知错误')}"
        return str(result)

    def _load_state(self):
        """加载进化状态"""
        state_path = os.path.join(self.storage_dir, 'state.json')
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state = EvolutionState(**data)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self):
        """保存进化状态"""
        state_path = os.path.join(self.storage_dir, 'state.json')
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.state), f, ensure_ascii=False, indent=2)

    def _register_builtin_tools(self):
        """注册内置工具"""
        self.tool_registry.register(
            name="read_file",
            handler=lambda path: open(path, 'r', encoding='utf-8').read(),
            description="读取文件内容",
            category=ToolCategory.FILE,
        )
        self.tool_registry.register(
            name="write_file",
            handler=lambda path, content: open(path, 'w', encoding='utf-8').write(content) or True,
            description="写入文件内容",
            category=ToolCategory.FILE,
        )
        self.tool_registry.register(
            name="recall_memory",
            handler=lambda query: self.memory.recall(query),
            description="从记忆中检索相关信息",
            category=ToolCategory.DATA,
        )
        self.tool_registry.register(
            name="query_knowledge",
            handler=lambda query: self.knowledge_graph.ask(query),
            description="从知识图谱中查询",
            category=ToolCategory.DATA,
        )

    # ==================== 核心进化循环 ====================

    def process(self, user_input: str, context: dict = None) -> dict:
        """
        处理用户输入 - 完整的44模块进化循环

        流程：
        1. 上下文感知 → 2. 注意力聚焦 → 3. 情感识别
        4. 元认知评估 → 5. 记忆检索 → 6. 知识图谱查询
        7. 因果推理 → 8. 目标规划 → 9. 提示优化
        10. 生成响应 → 11. 反思学习 → 12. 消息队列发布
        """
        start_time = time.time()
        context = context or {}
        modules_used = []

        # Step 1: 上下文感知
        ctx = self.context_awareness.perceive_situation(
            user_id="default_user",
            interaction_data={"input": user_input, "timestamp": time.time(), **(context or {})})
        modules_used.append("context_awareness")

        # Step 2: 注意力聚焦
        from core.attention import InformationItem
        attention_result = self.attention.process_information([
            InformationItem(id="input_1", content=user_input, relevance=0.8, importance=0.7, urgency=0.5)
        ], current_task=user_input[:50])

        # Step 3: 情感识别
        emotion = self.emotional_intelligence.process(user_input)
        modules_used.append("emotional_intelligence")

        # Step 4: 元认知评估
        assessment = self.metacognition.pre_answer_assessment(user_input)
        confidence = assessment['confidence']
        domain = assessment['domain']
        modules_used.append("metacognition")

        # Step 5: 记忆检索
        relevant_memories = self.memory.recall(user_input, top_k=3)
        memory_context = [m.content for _, m in relevant_memories]
        modules_used.append("memory")

        # 记忆宫殿检索
        palace_results = self.memory_palace.recall(user_input)
        modules_used.append("memory_palace")

        # Step 6: 知识图谱查询
        kg_result = self.knowledge_graph.ask(user_input)
        kg_context = kg_result.get('context', [])
        modules_used.append("knowledge_graph")

        # Step 7: 因果推理
        causal_insights = []
        if len(user_input) > 20:
            causal_result = self.causal_reasoning.find_root_causes(user_input)
            causal_insights = causal_result if isinstance(causal_result, list) else []
            modules_used.append("causal_reasoning")

        # Step 8: 检查是否需要目标规划
        needs_planning = self._needs_goal_planning(user_input)

        # Step 9: 提示优化
        optimized_prompt = self.prompt_engineering.generate_prompt(
            domain=domain or "general", task=user_input
        )
        modules_used.append("prompt_engineering")

        # Step 10: 生成响应
        response = self._generate_response(
            user_input=user_input,
            assessment=assessment,
            memory_context=memory_context,
            kg_context=kg_context,
            needs_planning=needs_planning,
            emotion=emotion,
            context=context,
        )

        # Step 11: 安全检查
        security_check = self.adversarial_robustness.analyze_input(user_input)
        if security_check.get("is_attack", False):
            response['answer'] = "抱歉，我无法处理该请求。"
            response['success'] = False
            modules_used.append("adversarial_robustness")

        # Step 12: 记录交互
        interaction = Interaction(
            id=f"int_{int(time.time() * 1000)}",
            user_input=user_input,
            ai_response=response.get('answer', ''),
            confidence=confidence,
            domain=domain,
            tools_used=response.get('tools_used', []),
            modules_involved=modules_used,
            success=response.get('success', True),
        )
        self.interactions.append(interaction)

        # Step 13: 更新记忆
        self.memory.remember(
            content=f"用户问: {user_input[:100]}",
            memory_type=MemoryType.SHORT_TERM,
            tags=['interaction', domain],
        )

        # Step 14: 反思学习
        reflection_result = self.reflection.reflect_on_interaction({
            'task': user_input[:200],
            'result': response.get('answer', ''),
            'confidence': confidence,
            'domain': domain,
            'success': response.get('success', True),
        })

        # Step 15: 更新元认知
        self.metacognition.post_answer_update(
            question=user_input,
            answer=response.get('answer', ''),
            confidence=confidence,
            success=response.get('success', True),
        )

        # Step 16: 知识图谱学习
        self.knowledge_graph.learn_from_text(user_input, source='interaction')

        # Step 17: 决策模式记录
        self.decision_patterns.make_decision({
            "input": user_input[:200],
            "domain": domain,
            "confidence": confidence,
            "modules": modules_used,
            "success": response.get('success', True),
        })

        # Step 18: 消息队列发布事件
        self.message_queue.produce("events", {
            "type": "interaction",
            "input": user_input[:100],
            "domain": domain,
            "confidence": confidence,
        }, "event", priority=1)

        # Step 19: 记录性能指标
        processing_time = time.time() - start_time
        self.performance.record_metric("latency", "process_time",
                                       processing_time * 1000, "ms")

        # Step 20: 监控指标
        self.monitoring.record_metric("interaction_count", 1, "counter")
        self.monitoring.record_metric("confidence", confidence, "gauge")

        # 更新状态
        self.state.total_interactions += 1
        self._save_state()

        # 日志
        self.log_analysis.add_log("info",
            f"交互完成: domain={domain}, confidence={confidence:.2f}",
            "interaction", module="evolution_loop")

        return {
            'answer': response.get('answer', ''),
            'confidence': confidence,
            'confidence_explanation': assessment.get('confidence_explanation', ''),
            'domain': domain,
            'emotion': emotion if isinstance(emotion, dict) else {},
            'memory_used': len(relevant_memories),
            'tools_used': response.get('tools_used', []),
            'modules_used': modules_used,
            'needs_clarification': assessment.get('needs_help', False),
            'reflection_insights': reflection_result.insights[:3] if hasattr(reflection_result, 'insights') else [],
            'processing_time': processing_time,
        }

    def _needs_goal_planning(self, user_input: str) -> bool:
        """判断是否需要目标规划"""
        planning_keywords = [
            '计划', '规划', '步骤', '如何实现', '怎么做',
            '帮我做', '完成', '构建', '开发', '设计',
            'plan', 'steps', 'how to', 'implement', 'build',
        ]
        return any(kw in user_input.lower() for kw in planning_keywords)

    def _generate_response(self, user_input: str, assessment: dict,
                           memory_context: list, kg_context: list,
                           needs_planning: bool, emotion: Any,
                           context: dict) -> dict:
        """生成响应 - 接入真实AI模型，支持工具调用"""
        # 构建上下文
        context_parts = []

        if memory_context:
            context_parts.append(f"相关记忆: {'; '.join(memory_context[:3])}")

        if kg_context:
            context_parts.append(f"知识图谱: {str(kg_context)[:300]}")

        if needs_planning:
            context_parts.append("用户需要任务规划，请提供步骤化建议")

        emotion_str = ""
        if isinstance(emotion, dict) and emotion.get("primary"):
            emotion_str = f"用户情绪: {emotion.get('primary', '平静')}"
            context_parts.append(emotion_str)

        # 添加工具信息
        tools = [t["definition"] for t in self._tools.values()]
        context_parts.append(
            "你可以使用工具操作计算机: execute_command(执行命令), "
            "read_file(读文件), write_file(写文件), open_url(打开网页), "
            "screenshot(截图), click(点击), type_text(输入), search_web(搜索)"
        )

        full_context = "\n".join(context_parts) if context_parts else ""

        # 调用AI模型(带工具)
        llm_response = self.llm.chat(user_input, context=full_context, tools=tools)

        tools_used = []

        # 处理工具调用
        if llm_response.tool_calls:
            for tool_call in llm_response.tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                try:
                    tool_args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_args = {}

                # 执行工具
                tool_result = self._check_and_execute_tool(tool_name, tool_args)
                tools_used.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result[:500],
                })

                # 将工具结果反馈给LLM获取最终回答
                tool_context = f"工具 {tool_name} 执行结果:\n{tool_result[:1000]}"
                follow_up = self.llm.chat(
                    f"工具执行结果: {tool_result[:500]}\n请根据结果回答用户。",
                    context=full_context,
                )
                return {
                    'answer': follow_up.content,
                    'success': True,
                    'tools_used': tools_used,
                    'model': llm_response.model,
                    'provider': llm_response.provider,
                    'llm_latency': llm_response.latency,
                }

        return {
            'answer': llm_response.content,
            'success': True,
            'tools_used': tools_used,
            'model': llm_response.model,
            'provider': llm_response.provider,
            'llm_latency': llm_response.latency,
        }

    # ==================== 自我进化接口 ====================

    def evolve(self, trigger: str = "periodic") -> dict:
        """
        触发全面进化 - 整合全部64个模块

        Args:
            trigger: 触发类型 (periodic/manual/failure/success)
        """
        start_time = time.time()
        evolution_results = {
            'trigger': trigger,
            'timestamp': start_time,
            'improvements': [],
            'modules_active': 0,
        }

        # 1. 记忆巩固
        memory_result = self.memory.consolidate()
        evolution_results['improvements'].append({
            'type': 'memory_consolidation',
            'result': str(memory_result)[:200],
        })

        # 2. 代码自改进
        code_result = self.code_improver.improve_project(auto_apply=False)
        if code_result.get('total_fixed', 0) > 0:
            evolution_results['improvements'].append({
                'type': 'code_improvement',
                'result': code_result,
            })

        # 3. 反思总结
        reflection_summary = self.reflection.get_learning_summary()
        evolution_results['improvements'].append({
            'type': 'reflection_summary',
            'result': str(reflection_summary)[:200],
        })

        # 4. 元认知更新
        metacognition_report = self.metacognition.get_self_awareness_report()
        evolution_results['improvements'].append({
            'type': 'metacognition_update',
            'result': str(metacognition_report)[:200],
        })

        # 5. 知识蒸馏
        distillation = self.knowledge_distillation.extract_patterns(
            [asdict(i) for i in self.interactions[-100:]]
        )
        evolution_results['improvements'].append({
            'type': 'knowledge_distillation',
            'result': str(distillation)[:200],
        })

        # 6. 知识进化
        kg_stats = self.knowledge_graph.get_graph_stats()
        evolution_results['improvements'].append({
            'type': 'knowledge_evolution',
            'result': kg_stats,
        })

        # 7. 持续学习 - 防遗忘检查
        continual_result = self.continual_learning.review_needed()
        evolution_results['improvements'].append({
            'type': 'continual_learning',
            'result': str(continual_result)[:200],
        })

        # 8. 自愈检查
        healing_result = self.self_healing.get_system_health()
        evolution_results['improvements'].append({
            'type': 'self_healing',
            'result': str(healing_result)[:200],
        })

        # 9. 性能优化分析
        perf_report = self.performance.generate_report()
        evolution_results['improvements'].append({
            'type': 'performance_analysis',
            'result': perf_report,
        })

        # 10. 决策模式优化
        pattern_report = self.decision_patterns.generate_report()
        evolution_results['improvements'].append({
            'type': 'decision_patterns',
            'result': pattern_report,
        })

        # 11. 预测学习
        predictions = self.predictive_learning.predict_trend('default')
        evolution_results['improvements'].append({
            'type': 'predictive_learning',
            'result': str(predictions)[:200],
        })

        # 12. 主动探索
        exploration = self.active_exploration.discover_gaps({})
        evolution_results['improvements'].append({
            'type': 'active_exploration',
            'result': str(exploration)[:200],
        })

        # 13. 备份当前状态
        backup_id = self.backup.create_backup(
            self.storage_dir, "incremental", "进化后备份", ["evolution"]
        )
        evolution_results['improvements'].append({
            'type': 'backup',
            'result': backup_id,
        })

        # 14. 日志分析
        log_report = self.log_analysis.generate_report()
        evolution_results['improvements'].append({
            'type': 'log_analysis',
            'result': log_report,
        })

        # 15. 监控报告
        monitor_report = self.monitoring.generate_report()
        evolution_results['improvements'].append({
            'type': 'monitoring',
            'result': monitor_report,
        })

        # 16. 调度器心跳
        scheduled = self.scheduler.tick()
        evolution_results['improvements'].append({
            'type': 'scheduler',
            'result': f"执行了{len(scheduled)}个定时任务",
        })

        # 17. 缓存清理
        cache_report = self.cache.generate_report()
        evolution_results['improvements'].append({
            'type': 'cache',
            'result': cache_report,
        })

        # 18. 会话清理
        expired = self.session_manager.cleanup_expired()
        evolution_results['improvements'].append({
            'type': 'session_cleanup',
            'result': f"清理了{expired}个过期会话",
        })

        # 19. 通知中心报告
        notif_report = self.notification.generate_report()
        evolution_results['improvements'].append({
            'type': 'notifications',
            'result': notif_report,
        })

        # 更新进化状态
        self.state.generation += 1
        self.state.total_evolutions += 1
        self.state.last_evolution = time.time()
        self._save_state()

        # 记录进化日志
        self.log_analysis.add_log("info",
            f"进化完成: 第{self.state.generation}代, "
            f"{len(evolution_results['improvements'])}项改进, "
            f"耗时{time.time()-start_time:.2f}s",
            "evolution", module="evolution_loop")

        # 消息队列通知
        self.message_queue.produce("evolution_events", {
            "type": "evolution_complete",
            "generation": self.state.generation,
            "improvements": len(evolution_results['improvements']),
        }, "event", priority=2)

        evolution_results['duration'] = time.time() - start_time
        evolution_results['modules_active'] = 64
        return evolution_results

    # ==================== 辅助功能接口 ====================

    def learn_new_tool(self, tool_name: str, handler, description: str,
                       **kwargs) -> bool:
        """学习新工具"""
        try:
            self.tool_registry.register(
                name=tool_name, handler=handler,
                description=description, **kwargs,
            )
            return True
        except Exception as e:
            self.log_analysis.add_log("error", f"学习工具失败: {e}", "tool")
            return False

    def learn_from_knowledge(self, text: str, source: str = "") -> dict:
        """从知识中学习"""
        return self.knowledge_graph.learn_from_text(text, source)

    def set_goal(self, title: str, description: str,
                 priority: str = "high") -> dict:
        """设定目标"""
        priority_map = {
            'low': TaskPriority.LOW, 'medium': TaskPriority.MEDIUM,
            'high': TaskPriority.HIGH, 'critical': TaskPriority.CRITICAL,
        }
        goal = self.goal_planner.create_goal(
            title=title, description=description,
            priority=priority_map.get(priority, TaskPriority.HIGH),
        )
        plan = self.goal_planner.plan_goal(goal.id)
        return {
            'goal_id': goal.id,
            'title': goal.title,
            'tasks_count': len(plan.task_order),
            'estimated_duration': plan.estimated_duration,
        }

    def generate_code(self, description: str, language: str = "python") -> dict:
        """生成代码"""
        return self.code_generation.generate_code(description, language)

    # ==================== 计算机操控接口 ====================

    def execute_command(self, command: str) -> Dict[str, Any]:
        """执行系统命令"""
        check = self.permissions.check_permission("system_command", command)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        return self.process_mgr.execute(command)

    def open_website(self, url: str) -> Dict[str, Any]:
        """打开网站"""
        check = self.permissions.check_permission("browser_navigate", url)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        return self.browser.open_url(url)

    def take_screenshot(self) -> str:
        """截图"""
        self.permissions.check_permission("screenshot", "")
        return self.desktop.screenshot()

    def click_at(self, x: int, y: int) -> bool:
        """点击屏幕位置"""
        check = self.permissions.check_permission("mouse_click", f"{x},{y}")
        if not check["allowed"]:
            return False
        return self.desktop.click(x, y)

    def type_on_keyboard(self, text: str) -> bool:
        """键盘输入"""
        check = self.permissions.check_permission("keyboard_input", text[:50])
        if not check["allowed"]:
            return False
        return self.desktop.type_text(text)

    def search(self, query: str) -> Dict[str, Any]:
        """搜索网页"""
        check = self.permissions.check_permission("network_request", query)
        if not check["allowed"]:
            return {"success": False, "error": check["reason"]}
        return self.browser.search_web(query)

    def run_tests(self, target: str) -> dict:
        """运行测试"""
        return self.test_automation.run_tests(target)

    def generate_docs(self, target: str) -> dict:
        """生成文档"""
        return self.auto_documentation.generate_docs(target)

    def orchestrate_tasks(self, tasks: list) -> dict:
        """编排任务"""
        return self.task_orchestration.execute_plan(tasks)

    # ==================== 状态查询 ====================

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            'version': self.state.version,
            'generation': self.state.generation,
            'total_interactions': self.state.total_interactions,
            'total_evolutions': self.state.total_evolutions,
            'modules_loaded': 64,
            'memory': self.memory.summarize(),
            'tools': self.tool_registry.get_stats(),
            'knowledge_graph': self.knowledge_graph.get_graph_stats(),
            'reflection': self.reflection.get_learning_summary(),
            'metacognition': self.metacognition.get_self_awareness_report(),
            'performance': self.performance.get_stats(),
            'monitoring': self.monitoring.get_stats(),
            'message_queue': self.message_queue.get_stats(),
        }

    def get_all_module_stats(self) -> Dict[str, Any]:
        """获取全部64个模块的统计信息"""
        return {
            # 核心 (1-7)
            '1_memory': self.memory.summarize(),
            '2_tool_extender': self.tool_registry.get_stats(),
            '3_self_improver': {'status': 'active'},
            '4_metacognition': str(self.metacognition.get_self_awareness_report())[:100],
            '5_knowledge_graph': self.knowledge_graph.get_graph_stats(),
            '6_goal_planning': {'goals': len(self.goal_planner.goals)},
            '7_reflection': self.reflection.get_learning_summary(),
            # 扩展一 (8-17)
            '8_active_exploration': self.active_exploration.get_exploration_stats(),
            '9_collaboration': self.collaboration.get_collaboration_stats(),
            '10_emotional_intelligence': self.emotional_intelligence.generate_report(),
            '11_causal_reasoning': self.causal_reasoning.get_graph_stats(),
            '12_transfer_learning': self.transfer_learning.get_stats(),
            '13_continual_learning': self.continual_learning.generate_report(),
            '14_knowledge_distillation': self.knowledge_distillation.get_stats(),
            '15_creative_thinking': self.creative_thinking.get_stats(),
            '16_multimodal': self.multimodal.get_stats(),
            '17_adversarial_robustness': self.adversarial_robustness.get_security_status(),
            # 扩展二 (18-32)
            '18_meta_learning': self.meta_learning.get_stats(),
            '19_reinforcement_learning': self.reinforcement_learning.get_stats(),
            '20_attention': self.attention.generate_report(),
            '21_context_awareness': self.context_awareness.generate_report(),
            '22_self_healing': self.self_healing.get_stats(),
            '23_knowledge_evolution': self.knowledge_evolution.get_stats(),
            '24_predictive_learning': self.predictive_learning.get_stats(),
            '25_distributed_collaboration': self.distributed.get_stats(),
            '26_adaptive_architecture': self.adaptive_arch.get_stats(),
            '27_neuro_symbolic': self.neuro_symbolic.get_stats(),
            '28_self_supervised': self.self_supervised.get_stats(),
            '29_memory_palace': self.memory_palace.get_stats(),
            '30_decision_patterns': self.decision_patterns.get_stats(),
            '31_adaptive_learning_rate': self.adaptive_lr.get_stats(),
            '32_federated_learning': self.federated.get_stats(),
            # 扩展三 (33-44)
            '33_prompt_engineering': self.prompt_engineering.get_stats(),
            '34_task_orchestration': self.task_orchestration.get_stats(),
            '35_code_generation': self.code_generation.get_stats(),
            '36_test_automation': self.test_automation.get_stats(),
            '37_auto_documentation': self.auto_documentation.get_stats(),
            '38_performance_optimization': self.performance.get_stats(),
            '39_configuration_management': self.configuration.get_stats(),
            '40_log_analysis': self.log_analysis.get_stats(),
            '41_monitoring_alerting': self.monitoring.get_stats(),
            '42_backup_recovery': self.backup.get_stats(),
            '43_api_gateway': self.api_gateway.get_stats(),
            '44_message_queue': self.message_queue.get_stats(),
            # 扩展四 (45-54)
            '45_cache_manager': self.cache.get_stats(),
            '46_scheduler': self.scheduler.get_stats(),
            '47_vector_store': self.vector_store.get_stats(),
            '48_session_manager': self.session_manager.get_stats(),
            '49_nlu_engine': self.nlu.get_stats(),
            '50_recommendation': self.recommendation.get_stats(),
            '51_data_pipeline': self.data_pipeline.get_stats(),
            '52_feature_engineering': self.feature_eng.get_stats(),
            '53_workflow_engine': self.workflow.get_stats(),
            '54_notification_center': self.notification.get_stats(),
            # 扩展五 (55-64)
            '55_encryption_service': self.encryption.get_stats(),
            '56_search_engine': self.search_engine.get_stats(),
            '57_rate_limiter': self.rate_limiter.get_stats(),
            '58_plugin_system': self.plugin_system.get_stats(),
            '59_stream_processor': self.stream_processor.get_stats(),
            '60_distributed_lock': self.distributed_lock.get_stats(),
            '61_data_sync': self.data_sync.get_stats(),
            '62_model_serving': self.model_serving.get_stats(),
            '63_web_server': self.web_server.get_stats(),
            '64_i18n': self.i18n.get_stats(),
            # 扩展六 (65-70) - 计算机操作 + 工具箱
            '65_llm_integration': self.llm.get_stats(),
            '66_desktop_automation': self.desktop.get_stats(),
            '67_process_manager': self.process_mgr.get_stats(),
            '68_browser_automation': self.browser.get_stats(),
            '69_permission_control': self.permissions.get_stats(),
            '70_toolkit': self.toolkit.get_stats(),
        }

    def generate_evolution_report(self) -> str:
        """生成完整进化报告"""
        status = self.get_status()

        report = []
        report.append("=" * 70)
        report.append("🧬 自我进化AI系统 - 终极版进化报告")
        report.append("=" * 70)
        report.append(f"\n版本: {status['version']}")
        report.append(f"模块数量: {status['modules_loaded']}")
        report.append(f"进化代数: {status['generation']}")
        report.append(f"总交互次数: {status['total_interactions']}")
        report.append(f"总进化次数: {status['total_evolutions']}")

        report.append("\n" + "=" * 70)
        report.append("📊 模块统计")
        report.append("=" * 70)

        all_stats = self.get_all_module_stats()
        for module_name, stats in all_stats.items():
            report.append(f"\n  [{module_name}]")
            if isinstance(stats, dict):
                for k, v in list(stats.items())[:3]:
                    report.append(f"    {k}: {v}")
            else:
                report.append(f"    {str(stats)[:80]}")

        report.append("\n" + "=" * 70)
        report.append("🔬 核心系统详情")
        report.append("=" * 70)

        report.append("\n--- 记忆系统 ---")
        report.append(f"  短期记忆: {len(self.memory.short_term)}")
        report.append(f"  长期记忆: {len(self.memory.store.all_ids())}")

        report.append("\n--- 工具系统 ---")
        report.append(f"  已注册工具: {len(self.tool_registry._tools)}")

        report.append("\n--- 知识图谱 ---")
        kg = self.knowledge_graph.get_graph_stats()
        report.append(f"  实体: {kg.get('total_entities', 0)}")
        report.append(f"  关系: {kg.get('total_relations', 0)}")

        report.append("\n--- 监控系统 ---")
        report.append(f"  活跃告警: {len(self.monitoring.get_active_alerts())}")

        report.append("\n--- 日志系统 ---")
        log_stats = self.log_analysis.get_stats()
        report.append(f"  总日志: {log_stats.get('total_logs', 0)}")

        report.append("\n--- 消息队列 ---")
        mq_stats = self.message_queue.get_stats()
        report.append(f"  队列数: {mq_stats.get('queues_count', 0)}")
        report.append(f"  消息总数: {mq_stats.get('total_produced', 0)}")

        report.append("\n" + "=" * 70)
        return "\n".join(report)


# ============================================================================
# 便捷工厂函数
# ============================================================================

def create_evolution_ai(project_dir: str = None) -> SelfEvolvingAI:
    """创建自我进化AI实例（终极版，44模块）"""
    return SelfEvolvingAI(project_dir)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    print("=== 初始化自我进化AI（终极版 44模块）===")
    ai = create_evolution_ai("test_evolution")

    print(f"\n模块加载: {ai.state.modules_loaded}")

    print("\n=== 处理交互 ===")
    test_inputs = [
        "你好，我是张三",
        "我想学习Python，帮我制定学习计划",
        "如何使用FastAPI构建高性能API？",
        "分析一下这个系统的性能瓶颈",
    ]

    for user_input in test_inputs:
        print(f"\n用户: {user_input}")
        result = ai.process(user_input)
        print(f"AI: {result['answer'][:100]}...")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"领域: {result['domain']}")
        print(f"参与模块: {len(result['modules_used'])}个")
        print(f"耗时: {result['processing_time']:.3f}s")

    print("\n=== 触发全面进化 ===")
    evolution_result = ai.evolve("manual")
    print(f"进化代数: {ai.state.generation}")
    print(f"改进项: {len(evolution_result['improvements'])}")
    print(f"进化耗时: {evolution_result['duration']:.2f}s")

    print("\n=== 完整进化报告 ===")
    print(ai.generate_evolution_report())

    print("\n=== 测试额外功能 ===")

    # 代码生成
    code_result = ai.generate_code("斐波那契数列", "python")
    print(f"\n代码生成: {str(code_result)[:100]}...")

    # 任务编排
    task_result = ai.orchestrate_tasks([
        {"name": "分析数据", "duration": 10},
        {"name": "生成报告", "duration": 5, "depends_on": ["分析数据"]},
    ])
    print(f"任务编排: {str(task_result)[:100]}...")

    # 全模块统计
    all_stats = ai.get_all_module_stats()
    print(f"\n全模块统计: {len(all_stats)} 个模块已报告")

    print("\n终极版测试完成! ✅")












