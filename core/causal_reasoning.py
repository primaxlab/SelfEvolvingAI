"""
================================================================================
因果推理系统 (Causal Reasoning System)
================================================================================

核心能力：
  1. 因果识别 - 识别事件间的因果关系
  2. 因果图构建 - 构建因果关系图
  3. 因果推理 - 基于因果图进行推理
  4. 反事实推理 - 思考"如果...会怎样"
  5. 因果解释 - 解释为什么发生某事

设计原则：
  - 区分因果和相关：不把相关性当因果性
  - 考虑混杂因素：识别潜在的混淆变量
  - 可验证性：因果假设需要可验证
"""

import json
import os
import time
import hashlib
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict


# ============================================================================
# 数据结构
# ============================================================================

class CausalRelationType(Enum):
    DIRECT = "direct"           # 直接因果
    INDIRECT = "indirect"       # 间接因果
    CORRELATION = "correlation" # 相关性（非因果）
    CONFOUNDING = "confounding" # 混淆因素
    MEDIATOR = "mediator"       # 中介变量
    MODERATOR = "moderator"     # 调节变量

class CausalStrength(Enum):
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    CERTAIN = 4

@dataclass
class CausalNode:
    """因果图节点"""
    id: str
    name: str
    description: str
    category: str = ""
    probability: float = 0.5  # 发生概率
    observed: bool = False    # 是否已观察到
    timestamp: float = field(default_factory=time.time)

@dataclass
class CausalEdge:
    """因果图边"""
    id: str
    source_id: str           # 原因节点
    target_id: str           # 结果节点
    relation_type: CausalRelationType
    strength: CausalStrength
    confidence: float        # 置信度 0-1
    evidence: list = field(default_factory=list)  # 证据
    timestamp: float = field(default_factory=time.time)

@dataclass
class CausalHypothesis:
    """因果假设"""
    id: str
    cause: str
    effect: str
    mechanism: str           # 机制描述
    confidence: float
    testable: bool = True
    tested: bool = False
    supported: bool = False
    evidence_for: list = field(default_factory=list)
    evidence_against: list = field(default_factory=list)

@dataclass
class CounterfactualScenario:
    """反事实场景"""
    id: str
    original_event: str
    alternative_event: str
    predicted_outcome: str
    confidence: float
    reasoning: str


# ============================================================================
# 因果识别器
# ============================================================================

class CausalIdentifier:
    """因果识别器"""

    def __init__(self):
        # 因果关系指示词
        self.causal_indicators = [
            '因为', '由于', '导致', '造成', '引起', '使得',
            'because', 'cause', 'lead to', 'result in', 'due to',
            'therefore', 'consequently', 'hence', 'so',
        ]

        # 相关性指示词（非因果）
        self.correlation_indicators = [
            '相关', '关联', '联系', 'correlation', 'associated',
            'related', 'linked', 'connected',
        ]

    def identify_from_text(self, text: str) -> list:
        """从文本中识别因果关系"""
        relations = []
        text_lower = text.lower()

        # 查找因果指示词
        for indicator in self.causal_indicators:
            if indicator in text_lower:
                # 尝试提取原因和结果
                parts = text_lower.split(indicator, 1)
                if len(parts) == 2:
                    cause = parts[0].strip()[-50:]  # 取最后50字符作为原因
                    effect = parts[1].strip()[:50]   # 取前50字符作为结果

                    if cause and effect:
                        relations.append({
                            'cause': cause,
                            'effect': effect,
                            'type': CausalRelationType.DIRECT,
                            'indicator': indicator,
                        })

        return relations

    def identify_from_sequence(self, events: list) -> list:
        """从事件序列中识别因果关系"""
        relations = []

        # 时间顺序分析：A在B之前发生，可能是A导致B
        for i in range(len(events) - 1):
            event_a = events[i]
            event_b = events[i + 1]

            # 检查时间接近性
            time_diff = abs(event_b.get('timestamp', 0) - event_a.get('timestamp', 0))

            if time_diff < 3600:  # 1小时内
                relations.append({
                    'cause': event_a.get('description', ''),
                    'effect': event_b.get('description', ''),
                    'type': CausalRelationType.DIRECT,
                    'confidence': 0.5,  # 需要进一步验证
                    'time_diff': time_diff,
                })

        return relations

    def identify_from_correlation(self, variable_a: str, variable_b: str,
                                    correlation_data: dict) -> Optional[dict]:
        """从相关性中识别可能的因果关系"""
        correlation = correlation_data.get('correlation', 0)
        sample_size = correlation_data.get('sample_size', 0)

        # 强相关可能暗示因果
        if abs(correlation) > 0.7 and sample_size > 30:
            return {
                'cause': variable_a,
                'effect': variable_b,
                'type': CausalRelationType.CORRELATION,
                'confidence': abs(correlation) * 0.7,  # 相关性不等于因果，降低置信度
                'note': '相关性不等于因果性，需要进一步验证',
            }

        return None


# ============================================================================
# 因果图管理器
# ============================================================================

class CausalGraph:
    """因果图"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "causal_graph.json"
        self.nodes: dict[str, CausalNode] = {}
        self.edges: dict[str, CausalEdge] = {}
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for n_data in data.get('nodes', []):
                    node = CausalNode(**n_data)
                    self.nodes[node.id] = node

                for e_data in data.get('edges', []):
                    e_data['relation_type'] = CausalRelationType(e_data['relation_type'])
                    e_data['strength'] = CausalStrength(e_data['strength'])
                    edge = CausalEdge(**e_data)
                    self.edges[edge.id] = edge

    def _save(self):
        """保存数据"""
        data = {
            'nodes': [asdict(n) for n in self.nodes.values()],
            'edges': [],
        }

        for edge in self.edges.values():
            e_dict = asdict(edge)
            e_dict['relation_type'] = edge.relation_type.value
            e_dict['strength'] = edge.strength.value
            data['edges'].append(e_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_node(self, name: str, description: str,
                 category: str = "") -> CausalNode:
        """添加节点"""
        node_id = hashlib.md5(name.encode()).hexdigest()[:12]
        node = CausalNode(
            id=node_id,
            name=name,
            description=description,
            category=category,
        )
        self.nodes[node_id] = node
        self._save()
        return node

    def add_edge(self, source_id: str, target_id: str,
                 relation_type: CausalRelationType,
                 strength: CausalStrength,
                 confidence: float = 0.5) -> CausalEdge:
        """添加边"""
        edge_id = hashlib.md5(f"{source_id}:{target_id}".encode()).hexdigest()[:12]
        edge = CausalEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
        )
        self.edges[edge_id] = edge
        self._save()
        return edge

    def find_node_by_name(self, name: str) -> Optional[CausalNode]:
        """按名称查找节点"""
        name_lower = name.lower()
        for node in self.nodes.values():
            if node.name.lower() == name_lower:
                return node
        return None

    def get_causes(self, node_id: str) -> list:
        """获取某节点的所有原因"""
        causes = []
        for edge in self.edges.values():
            if edge.target_id == node_id:
                cause_node = self.nodes.get(edge.source_id)
                if cause_node:
                    causes.append({
                        'node': cause_node,
                        'edge': edge,
                    })
        return causes

    def get_effects(self, node_id: str) -> list:
        """获取某节点的所有结果"""
        effects = []
        for edge in self.edges.values():
            if edge.source_id == node_id:
                effect_node = self.nodes.get(edge.target_id)
                if effect_node:
                    effects.append({
                        'node': effect_node,
                        'edge': edge,
                    })
        return effects

    def find_path(self, source_id: str, target_id: str,
                  max_depth: int = 5) -> list:
        """查找因果路径"""
        from collections import deque

        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            current_id, path = queue.popleft()

            if current_id == target_id:
                return path

            if len(path) >= max_depth:
                continue

            # 查找直接结果
            for edge in self.edges.values():
                if edge.source_id == current_id:
                    next_id = edge.target_id
                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, path + [next_id]))

        return []

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'relation_types': {
                t.value: sum(1 for e in self.edges.values()
                            if e.relation_type == t)
                for t in CausalRelationType
            },
        }


# ============================================================================
# 因果推理器
# ============================================================================

class CausalReasoner:
    """因果推理器"""

    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def explain(self, event: str) -> dict:
        """解释事件的原因"""
        node = self.graph.find_node_by_name(event)
        if not node:
            return {
                'event': event,
                'explanation': '未找到相关因果信息',
                'causes': [],
            }

        causes = self.graph.get_causes(node.id)

        explanation_parts = []
        for cause_info in causes[:3]:  # 最多解释3个原因
            cause_node = cause_info['node']
            edge = cause_info['edge']
            explanation_parts.append(
                f"{cause_node.name} (强度: {edge.strength.value}, 置信度: {edge.confidence:.2f})"
            )

        return {
            'event': event,
            'causes': [asdict(c['node']) for c in causes],
            'explanation': f"{event} 可能是由以下原因导致的: " + "; ".join(explanation_parts) if explanation_parts else "未找到明确原因",
        }

    def predict_effects(self, event: str) -> dict:
        """预测事件的结果"""
        node = self.graph.find_node_by_name(event)
        if not node:
            return {
                'event': event,
                'effects': [],
                'prediction': '未找到相关信息',
            }

        effects = self.graph.get_effects(node.id)

        predictions = []
        for effect_info in effects[:3]:  # 最多预测3个结果
            effect_node = effect_info['node']
            edge = effect_info['edge']
            predictions.append({
                'effect': effect_node.name,
                'probability': edge.confidence,
                'strength': edge.strength.value,
            })

        return {
            'event': event,
            'effects': predictions,
            'prediction': f"{event} 可能导致: " + ", ".join(p['effect'] for p in predictions) if predictions else "未预测到明显结果",
        }

    def counterfactual(self, original_event: str,
                       alternative_event: str) -> CounterfactualScenario:
        """反事实推理：如果A没有发生，而是发生了B，会怎样？"""
        # 查找原始事件的结果
        original_node = self.graph.find_node_by_name(original_event)
        alternative_node = self.graph.find_node_by_name(alternative_event)

        original_effects = []
        alternative_effects = []

        if original_node:
            original_effects = [e['node'].name for e in self.graph.get_effects(original_node.id)]

        if alternative_node:
            alternative_effects = [e['node'].name for e in self.graph.get_effects(alternative_node.id)]

        # 比较差异
        different_effects = set(original_effects) - set(alternative_effects)
        new_effects = set(alternative_effects) - set(original_effects)

        reasoning_parts = []
        if different_effects:
            reasoning_parts.append(f"避免了: {', '.join(different_effects)}")
        if new_effects:
            reasoning_parts.append(f"可能产生: {', '.join(new_effects)}")

        predicted_outcome = "; ".join(reasoning_parts) if reasoning_parts else "结果可能相似"

        return CounterfactualScenario(
            id=f"cf_{hashlib.md5(f'{original_event}:{alternative_event}'.encode()).hexdigest()[:8]}",
            original_event=original_event,
            alternative_event=alternative_event,
            predicted_outcome=predicted_outcome,
            confidence=0.5,  # 反事实推理置信度通常较低
            reasoning=f"如果 {alternative_event} 发生而不是 {original_event}，{predicted_outcome}",
        )

    def find_root_causes(self, event: str, max_depth: int = 5) -> list:
        """查找根本原因"""
        node = self.graph.find_node_by_name(event)
        if not node:
            return []

        root_causes = []
        visited = set()

        def dfs(node_id, depth):
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)

            causes = self.graph.get_causes(node_id)
            if not causes:
                # 没有更多原因，这是根本原因
                node = self.graph.nodes.get(node_id)
                if node:
                    root_causes.append({
                        'node': asdict(node),
                        'depth': depth,
                    })
            else:
                for cause_info in causes:
                    dfs(cause_info['node'].id, depth + 1)

        dfs(node.id, 0)
        return root_causes

    def generate_hypothesis(self, cause: str, effect: str) -> CausalHypothesis:
        """生成因果假设"""
        hypothesis_id = hashlib.md5(f"{cause}:{effect}".encode()).hexdigest()[:12]

        # 检查图中是否已有关系
        cause_node = self.graph.find_node_by_name(cause)
        effect_node = self.graph.find_node_by_name(effect)

        mechanism = f"{cause} 通过某种机制导致 {effect}"
        confidence = 0.3  # 默认低置信度

        if cause_node and effect_node:
            # 检查是否有路径
            path = self.graph.find_path(cause_node.id, effect_node.id)
            if path:
                confidence = 0.7
                mechanism = f"{cause} 通过 {len(path)-1} 步因果链导致 {effect}"

        return CausalHypothesis(
            id=hypothesis_id,
            cause=cause,
            effect=effect,
            mechanism=mechanism,
            confidence=confidence,
        )


# ============================================================================
# 因果推理引擎
# ============================================================================

class CausalReasoningEngine:
    """
    因果推理引擎 - 整合所有组件

    核心功能：
    1. 从文本/事件中识别因果关系
    2. 构建和维护因果图
    3. 进行因果推理和解释
    4. 反事实推理
    5. 假设生成和验证
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "causal_reasoning"
        os.makedirs(storage_dir, exist_ok=True)

        self.identifier = CausalIdentifier()
        self.graph = CausalGraph(
            os.path.join(storage_dir, "causal_graph.json")
        )
        self.reasoner = CausalReasoner(self.graph)
        self.hypotheses: dict[str, CausalHypothesis] = {}

    def learn_from_text(self, text: str) -> dict:
        """从文本中学习因果关系"""
        # 识别因果关系
        relations = self.identifier.identify_from_text(text)

        added_nodes = 0
        added_edges = 0

        for rel in relations:
            # 添加节点
            cause_node = self.graph.find_node_by_name(rel['cause'])
            if not cause_node:
                cause_node = self.graph.add_node(rel['cause'], f"原因: {rel['cause']}")
                added_nodes += 1

            effect_node = self.graph.find_node_by_name(rel['effect'])
            if not effect_node:
                effect_node = self.graph.add_node(rel['effect'], f"结果: {rel['effect']}")
                added_nodes += 1

            # 添加边
            self.graph.add_edge(
                source_id=cause_node.id,
                target_id=effect_node.id,
                relation_type=rel.get('type', CausalRelationType.DIRECT),
                strength=CausalStrength.MODERATE,
                confidence=rel.get('confidence', 0.5),
            )
            added_edges += 1

        return {
            'relations_found': len(relations),
            'nodes_added': added_nodes,
            'edges_added': added_edges,
        }

    def learn_from_events(self, events: list) -> dict:
        """从事件序列中学习因果关系"""
        relations = self.identifier.identify_from_sequence(events)

        added = 0
        for rel in relations:
            cause_node = self.graph.find_node_by_name(rel['cause'])
            if not cause_node:
                cause_node = self.graph.add_node(rel['cause'], '')

            effect_node = self.graph.find_node_by_name(rel['effect'])
            if not effect_node:
                effect_node = self.graph.add_node(rel['effect'], '')

            self.graph.add_edge(
                source_id=cause_node.id,
                target_id=effect_node.id,
                relation_type=rel.get('type', CausalRelationType.DIRECT),
                strength=CausalStrength.WEAK,
                confidence=rel.get('confidence', 0.3),
            )
            added += 1

        return {'relations_added': added}

    def explain_event(self, event: str) -> dict:
        """解释事件"""
        return self.reasoner.explain(event)

    def predict_effects(self, event: str) -> dict:
        """预测结果"""
        return self.reasoner.predict_effects(event)

    def what_if(self, original_event: str,
                alternative_event: str) -> dict:
        """反事实推理"""
        scenario = self.reasoner.counterfactual(original_event, alternative_event)
        return asdict(scenario)

    def find_root_causes(self, event: str) -> list:
        """查找根本原因"""
        return self.reasoner.find_root_causes(event)

    def generate_hypothesis(self, cause: str, effect: str) -> dict:
        """生成假设"""
        hypothesis = self.reasoner.generate_hypothesis(cause, effect)
        self.hypotheses[hypothesis.id] = hypothesis
        return asdict(hypothesis)

    def get_graph_stats(self) -> dict:
        """获取图统计"""
        return self.graph.get_stats()

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_graph_stats()

        report = []
        report.append("=" * 50)
        report.append("🔗 因果推理报告")
        report.append("=" * 50)
        report.append(f"\n因果图节点数: {stats['total_nodes']}")
        report.append(f"因果图边数: {stats['total_edges']}")

        if stats['relation_types']:
            report.append("\n关系类型分布:")
            for rtype, count in stats['relation_types'].items():
                if count > 0:
                    report.append(f"  - {rtype}: {count}")

        report.append(f"\n生成假设数: {len(self.hypotheses)}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = CausalReasoningEngine("test_causal_reasoning")

    # 从文本学习
    texts = [
        "由于服务器过载，导致响应超时",
        "因为代码存在bug，造成系统崩溃",
        "持续学习导致能力提升",
    ]

    print("=== 学习因果关系 ===")
    for text in texts:
        result = engine.learn_from_text(text)
        print(f"文本: {text}")
        print(f"  发现关系: {result['relations_found']}")

    # 因果推理
    print("\n=== 因果推理 ===")
    explanation = engine.explain_event("响应超时")
    print(f"解释: {explanation['explanation']}")

    prediction = engine.predict_effects("代码存在bug")
    print(f"预测: {prediction['prediction']}")

    # 反事实推理
    print("\n=== 反事实推理 ===")
    what_if = engine.what_if("服务器过载", "服务器正常运行")
    print(f"如果: {what_if['reasoning']}")

    # 报告
    print("\n" + engine.generate_report())