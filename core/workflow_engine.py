"""工作流引擎 - 可视化工作流、条件分支、循环"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class NodeType(Enum):
    START = "start"
    END = "end"
    TASK = "task"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    MERGE = "merge"


class WorkflowStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowNode:
    node_id: str
    name: str
    node_type: str = "task"
    config: Dict[str, Any] = field(default_factory=dict)
    next_nodes: List[str] = field(default_factory=list)
    condition: str = ""


@dataclass
class WorkflowEdge:
    source: str
    target: str
    condition: str = ""
    label: str = ""


@dataclass
class Workflow:
    workflow_id: str
    name: str
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    edges: List[WorkflowEdge] = field(default_factory=list)
    status: str = "draft"
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    version: int = 1


@dataclass
class WorkflowExecution:
    execution_id: str
    workflow_id: str
    started_at: float = 0.0
    completed_at: float = 0.0
    duration: float = 0.0
    status: str = "running"
    current_node: str = ""
    trace: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self, storage_dir: str = "data/workflow"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.workflows: Dict[str, Workflow] = {}
        self.executions: List[WorkflowExecution] = []
        self.node_handlers: Dict[str, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {}

        self._register_defaults()
        self._load()

    def _register_defaults(self):
        self.node_handlers = {
            "task": self._handle_task,
            "condition": self._handle_condition,
            "loop": self._handle_loop,
        }
        self.condition_evaluators = {
            "eq": lambda vars, config: vars.get(config["key"]) == config["value"],
            "gt": lambda vars, config: vars.get(config["key"], 0) > config["value"],
            "lt": lambda vars, config: vars.get(config["key"], 0) < config["value"],
            "contains": lambda vars, config: config["value"] in str(vars.get(config["key"], "")),
        }

    def _load(self):
        path = os.path.join(self.storage_dir, "workflow_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("workflows", {}).items():
                    nodes = {nid: WorkflowNode(**ndata) for nid, ndata in v.pop("nodes", {}).items()}
                    edges = [WorkflowEdge(**e) for e in v.pop("edges", [])]
                    self.workflows[k] = Workflow(nodes=nodes, edges=edges, **v)
                self.executions = [WorkflowExecution(**e) for e in data.get("executions", [])]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "workflow_data.json")
        data = {
            "workflows": {
                k: {
                    **{field.name: getattr(v, field.name) for field in Workflow.__dataclass_fields__.values() if field.name not in ("nodes", "edges")},
                    "nodes": {nid: asdict(nd) for nid, nd in v.nodes.items()},
                    "edges": [asdict(e) for e in v.edges],
                }
                for k, v in self.workflows.items()
            },
            "executions": [asdict(e) for e in self.executions[-1000:]],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_workflow(self, name: str) -> str:
        """创建工作流"""
        wf_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        workflow = Workflow(
            workflow_id=wf_id, name=name,
            created_at=time.time(),
        )
        # 添加开始和结束节点
        workflow.nodes["start"] = WorkflowNode(node_id="start", name="开始", node_type="start")
        workflow.nodes["end"] = WorkflowNode(node_id="end", name="结束", node_type="end")
        self.workflows[wf_id] = workflow
        self._save()
        return wf_id

    def add_node(self, workflow_id: str, name: str, node_type: str = "task",
                 config: Dict[str, Any] = None, node_id: str = "") -> str:
        """添加节点"""
        if workflow_id not in self.workflows:
            return ""
        wf = self.workflows[workflow_id]
        if not node_id:
            node_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:8]
        node = WorkflowNode(
            node_id=node_id, name=name,
            node_type=node_type, config=config or {},
        )
        wf.nodes[node_id] = node
        self._save()
        return node_id

    def add_edge(self, workflow_id: str, source: str, target: str,
                 condition: str = "", label: str = "") -> bool:
        """添加边"""
        if workflow_id not in self.workflows:
            return False
        wf = self.workflows[workflow_id]
        if source not in wf.nodes or target not in wf.nodes:
            return False
        edge = WorkflowEdge(source=source, target=target, condition=condition, label=label)
        wf.edges.append(edge)
        wf.nodes[source].next_nodes.append(target)
        self._save()
        return True

    def execute(self, workflow_id: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行工作流"""
        if workflow_id not in self.workflows:
            return {"error": "工作流不存在"}

        wf = self.workflows[workflow_id]
        execution_id = hashlib.md5(f"{workflow_id}_{time.time()}".encode()).hexdigest()[:12]

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            started_at=time.time(),
            status="running",
            variables=variables or {},
        )

        # 从start开始
        current = "start"
        max_steps = 100
        step = 0

        while current and current != "end" and step < max_steps:
            step += 1
            node = wf.nodes.get(current)
            if not node:
                execution.status = "failed"
                execution.error = f"节点不存在: {current}"
                break

            execution.current_node = current
            execution.trace.append({
                "node": current,
                "name": node.name,
                "type": node.node_type,
                "timestamp": time.time(),
            })

            # 处理节点
            handler = self.node_handlers.get(node.node_type)
            if handler:
                result = handler(node, execution.variables, wf)
                execution.variables.update(result.get("variables", {}))
                next_node = result.get("next")
            else:
                next_node = node.next_nodes[0] if node.next_nodes else None

            if node.node_type == "end":
                break

            current = next_node

        execution.completed_at = time.time()
        execution.duration = execution.completed_at - execution.started_at
        execution.status = "completed" if execution.status == "running" else execution.status

        self.executions.append(execution)
        self._save()

        return {
            "execution_id": execution_id,
            "status": execution.status,
            "duration": execution.duration,
            "steps": len(execution.trace),
            "variables": execution.variables,
            "trace": execution.trace,
        }

    def _handle_task(self, node: WorkflowNode, variables: dict, wf: Workflow) -> Dict:
        """处理任务节点"""
        callback = self.node_handlers.get(f"task_{node.config.get('action', 'default')}")
        result_vars = {}
        if callback:
            result_vars = callback(node.config, variables)
        return {"next": node.next_nodes[0] if node.next_nodes else None, "variables": result_vars}

    def _handle_condition(self, node: WorkflowNode, variables: dict, wf: Workflow) -> Dict:
        """处理条件节点"""
        condition = node.config.get("condition", {})
        evaluator = self.condition_evaluators.get(condition.get("op", "eq"))
        if evaluator and evaluator(variables, condition):
            target = node.config.get("true_branch", node.next_nodes[0] if node.next_nodes else None)
        else:
            target = node.config.get("false_branch", node.next_nodes[1] if len(node.next_nodes) > 1 else None)
        return {"next": target, "variables": {}}

    def _handle_loop(self, node: WorkflowNode, variables: dict, wf: Workflow) -> Dict:
        """处理循环节点"""
        loop_var = node.config.get("variable", "i")
        max_iter = node.config.get("max_iterations", 10)
        current = variables.get(loop_var, 0)
        if current < max_iter:
            variables[loop_var] = current + 1
            return {"next": node.config.get("loop_body", node.next_nodes[0] if node.next_nodes else None), "variables": {}}
        return {"next": node.config.get("exit_node", node.next_nodes[-1] if node.next_nodes else None), "variables": {}}

    def register_task_handler(self, action: str, handler: Callable):
        """注册任务处理器"""
        self.node_handlers[f"task_{action}"] = handler

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流"""
        if workflow_id not in self.workflows:
            return None
        wf = self.workflows[workflow_id]
        return {
            "workflow_id": wf.workflow_id,
            "name": wf.name,
            "status": wf.status,
            "nodes": {nid: {"name": n.name, "type": n.node_type} for nid, n in wf.nodes.items()},
            "edges": [{"from": e.source, "to": e.target, "label": e.label} for e in wf.edges],
        }

    def get_execution_history(self, workflow_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        execs = self.executions
        if workflow_id:
            execs = [e for e in execs if e.workflow_id == workflow_id]
        return [asdict(e) for e in sorted(execs, key=lambda x: x.started_at, reverse=True)[:limit]]

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        return {
            "total_workflows": len(self.workflows),
            "total_executions": len(self.executions),
            "success_rate": sum(1 for e in self.executions if e.status == "completed") / max(len(self.executions), 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "workflows_count": len(self.workflows),
            "executions_count": len(self.executions),
            "node_handlers_count": len(self.node_handlers),
        }


if __name__ == "__main__":
    print("=== 工作流引擎测试 ===")
    engine = WorkflowEngine()

    # 创建工作流
    wf_id = engine.create_workflow("数据处理流程")
    print(f"工作流: {wf_id}")

    # 添加节点
    n1 = engine.add_node(wf_id, "数据收集", "task", {"action": "collect"})
    n2 = engine.add_node(wf_id, "数据量检查", "condition", {
        "condition": {"key": "count", "op": "gt", "value": 0},
        "true_branch": "process",
        "false_branch": "end",
    })
    n3 = engine.add_node(wf_id, "数据处理", "task", {"action": "process"}, "process")
    n4 = engine.add_node(wf_id, "生成报告", "task", {"action": "report"})

    # 添加边
    engine.add_edge(wf_id, "start", n1)
    engine.add_edge(wf_id, n1, n2)
    engine.add_edge(wf_id, n2, n3, condition="count > 0")
    engine.add_edge(wf_id, n2, "end", condition="count == 0")
    engine.add_edge(wf_id, n3, n4)
    engine.add_edge(wf_id, n4, "end")

    # 注册处理器
    engine.register_task_handler("collect", lambda cfg, vars: {"count": 100, "data": "collected"})
    engine.register_task_handler("process", lambda cfg, vars: {"processed": True})
    engine.register_task_handler("report", lambda cfg, vars: {"report": "generated"})

    # 执行
    result = engine.execute(wf_id, {"count": 100})
    print(f"\n执行结果:")
    print(f"  状态: {result['status']}")
    print(f"  步骤: {result['steps']}")
    print(f"  耗时: {result['duration']:.3f}s")
    print(f"  变量: {result['variables']}")

    # 查看工作流结构
    wf = engine.get_workflow(wf_id)
    print(f"\n工作流结构:")
    print(f"  节点: {list(wf['nodes'].keys())}")
    print(f"  边: {len(wf['edges'])} 条")

    report = engine.generate_report()
    print(f"\n工作流报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
