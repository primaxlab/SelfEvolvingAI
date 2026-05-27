"""
================================================================================
知识图谱系统 (Knowledge Graph System)
================================================================================

核心能力：
  1. 实体识别 - 从文本中提取实体
  2. 关系抽取 - 识别实体间关系
  3. 图谱存储 - 持久化存储知识图谱
  4. 语义推理 - 基于图谱进行推理
  5. 知识融合 - 合并重复实体和关系

设计原则：
  - 结构化：所有知识都有明确的实体-关系-实体结构
  - 可追溯：每条知识都有来源和置信度
  - 动态更新：支持增量更新和冲突检测
"""

import json
import os
import re
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

class EntityType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    CONCEPT = "concept"
    TOOL = "tool"
    FRAMEWORK = "framework"
    LANGUAGE = "language"
    FILE = "file"
    PROJECT = "project"
    OTHER = "other"

class RelationType(Enum):
    USES = "uses"              # A使用B
    CONTAINS = "contains"      # A包含B
    DEPENDS_ON = "depends_on"  # A依赖B
    CREATES = "creates"        # A创建B
    SOLVES = "solves"          # A解决B
    RELATED_TO = "related_to"  # A相关于B
    PART_OF = "part_of"        # A是B的一部分
    SIMILAR_TO = "similar_to"  # A相似于B
    OPPOSITE_OF = "opposite_of" # A与B相反
    CAUSES = "causes"          # A导致B
    BELONGS_TO = "belongs_to"  # A属于B

@dataclass
class Entity:
    """实体"""
    id: str
    name: str
    entity_type: EntityType
    properties: dict = field(default_factory=dict)
    aliases: list = field(default_factory=list)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = ""

@dataclass
class Relation:
    """关系"""
    id: str
    source_id: str           # 源实体ID
    target_id: str           # 目标实体ID
    relation_type: RelationType
    properties: dict = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    source: str = ""

@dataclass
class KnowledgeTriple:
    """知识三元组"""
    subject: Entity
    predicate: RelationType
    object: Entity
    confidence: float = 1.0
    source: str = ""


# ============================================================================
# 实体识别器
# ============================================================================

class EntityExtractor:
    """实体识别器"""

    def __init__(self):
        # 简单的规则匹配，实际应用可用NER模型
        self.patterns = {
            EntityType.TECHNOLOGY: [
                r'Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|Ruby|PHP|Swift|Kotlin',
                r'Docker|Kubernetes|Redis|MongoDB|PostgreSQL|MySQL|Elasticsearch',
                r'Git|Linux|Windows|MacOS|Android|iOS',
            ],
            EntityType.FRAMEWORK: [
                r'FastAPI|Django|Flask|Spring|React|Vue|Angular|Express|Rails',
                r'TensorFlow|PyTorch|Keras|scikit-learn|Pandas|NumPy',
            ],
            EntityType.TOOL: [
                r'VSCode|PyCharm|Vim|Emacs|Sublime|Atom',
                r'pip|npm|yarn|cargo|maven|gradle',
                r'pytest|unittest|jest|mocha|junit',
            ],
            EntityType.CONCEPT: [
                r'算法|数据结构|设计模式|架构|微服务|容器化|CI/CD',
                r'机器学习|深度学习|自然语言处理|计算机视觉',
                r'OOP|函数式编程|响应式编程|事件驱动',
            ],
        }

    def extract(self, text: str) -> list:
        """从文本中提取实体"""
        entities = []

        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match.group()
                    entity_id = self._generate_id(name, entity_type)
                    entities.append(Entity(
                        id=entity_id,
                        name=name,
                        entity_type=entity_type,
                    ))

        return entities

    def extract_from_code(self, code: str) -> list:
        """从代码中提取实体"""
        entities = []

        # 提取导入
        import_pattern = r'(?:from\s+(\S+)\s+)?import\s+(\S+)'
        for match in re.finditer(import_pattern, code):
            module = match.group(1) or match.group(2)
            entities.append(Entity(
                id=self._generate_id(module, EntityType.TECHNOLOGY),
                name=module,
                entity_type=EntityType.TECHNOLOGY,
            ))

        # 提取函数定义
        func_pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, code):
            func_name = match.group(1)
            entities.append(Entity(
                id=self._generate_id(func_name, EntityType.CONCEPT),
                name=func_name,
                entity_type=EntityType.CONCEPT,
                properties={'type': 'function'},
            ))

        # 提取类定义
        class_pattern = r'class\s+(\w+)\s*[\(:]'
        for match in re.finditer(class_pattern, code):
            class_name = match.group(1)
            entities.append(Entity(
                id=self._generate_id(class_name, EntityType.CONCEPT),
                name=class_name,
                entity_type=EntityType.CONCEPT,
                properties={'type': 'class'},
            ))

        return entities

    def _generate_id(self, name: str, entity_type: EntityType) -> str:
        """生成实体ID"""
        raw = f"{name}:{entity_type.value}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


# ============================================================================
# 关系抽取器
# ============================================================================

class RelationExtractor:
    """关系抽取器"""

    def __init__(self):
        # 关系模式
        self.patterns = [
            (r'(\w+)\s*使用\s*(\w+)', RelationType.USES),
            (r'(\w+)\s*基于\s*(\w+)', RelationType.DEPENDS_ON),
            (r'(\w+)\s*依赖\s*(\w+)', RelationType.DEPENDS_ON),
            (r'(\w+)\s*包含\s*(\w+)', RelationType.CONTAINS),
            (r'(\w+)\s*解决\s*(\w+)', RelationType.SOLVES),
            (r'(\w+)\s*创建\s*(\w+)', RelationType.CREATES),
            (r'(\w+)\s*属于\s*(\w+)', RelationType.BELONGS_TO),
            (r'(\w+)\s*类似\s*(\w+)', RelationType.SIMILAR_TO),
            (r'(\w+)\s*导致\s*(\w+)', RelationType.CAUSES),
        ]

    def extract(self, text: str, entities: list = None) -> list:
        """从文本中提取关系"""
        relations = []

        for pattern, relation_type in self.patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                source_name = match.group(1)
                target_name = match.group(2)

                relations.append({
                    'source': source_name,
                    'target': target_name,
                    'type': relation_type,
                })

        return relations

    def extract_from_code(self, code: str) -> list:
        """从代码中提取关系"""
        relations = []

        # 导入关系 → 依赖
        import_pattern = r'(?:from\s+(\S+)\s+)?import\s+(\S+)'
        for match in re.finditer(import_pattern, code):
            module = match.group(1) or match.group(2)
            current_file = "current"  # 实际使用时传入
            relations.append({
                'source': current_file,
                'target': module,
                'type': RelationType.DEPENDS_ON,
            })

        # 函数调用关系
        call_pattern = r'(\w+)\s*\('
        # 这里简化处理，实际需要AST分析

        return relations


# ============================================================================
# 知识图谱存储
# ============================================================================

class KnowledgeGraphStore:
    """知识图谱存储"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "knowledge_graph.json"
        self.entities: dict[str, Entity] = {}
        self.relations: dict[str, Relation] = {}
        self._load()

    def _load(self):
        """加载图谱"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for e_data in data.get('entities', []):
                    e_data['entity_type'] = EntityType(e_data['entity_type'])
                    entity = Entity(**e_data)
                    self.entities[entity.id] = entity

                for r_data in data.get('relations', []):
                    r_data['relation_type'] = RelationType(r_data['relation_type'])
                    relation = Relation(**r_data)
                    self.relations[relation.id] = relation

    def _save(self):
        """保存图谱"""
        data = {
            'entities': [],
            'relations': [],
        }

        for entity in self.entities.values():
            e_dict = asdict(entity)
            e_dict['entity_type'] = entity.entity_type.value
            data['entities'].append(e_dict)

        for relation in self.relations.values():
            r_dict = asdict(relation)
            r_dict['relation_type'] = relation.relation_type.value
            data['relations'].append(r_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_entity(self, entity: Entity) -> str:
        """添加实体"""
        # 检查是否已存在（去重）
        for existing in self.entities.values():
            if existing.name.lower() == entity.name.lower():
                # 合并属性
                existing.properties.update(entity.properties)
                existing.aliases = list(set(existing.aliases + entity.aliases))
                existing.updated_at = time.time()
                return existing.id

        self.entities[entity.id] = entity
        self._save()
        return entity.id

    def add_relation(self, relation: Relation) -> str:
        """添加关系"""
        # 检查实体是否存在
        if relation.source_id not in self.entities:
            return ""
        if relation.target_id not in self.entities:
            return ""

        # 检查是否已存在相同关系
        for existing in self.relations.values():
            if (existing.source_id == relation.source_id and
                existing.target_id == relation.target_id and
                existing.relation_type == relation.relation_type):
                # 更新置信度
                existing.confidence = max(existing.confidence, relation.confidence)
                self._save()
                return existing.id

        self.relations[relation.id] = relation
        self._save()
        return relation.id

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional[Entity]:
        """按名称查找实体"""
        name_lower = name.lower()
        for entity in self.entities.values():
            if entity.name.lower() == name_lower:
                return entity
            if name_lower in [a.lower() for a in entity.aliases]:
                return entity
        return None

    def get_relations(self, entity_id: str,
                      direction: str = "both") -> list:
        """获取实体的关系"""
        results = []

        for relation in self.relations.values():
            if direction in ("outgoing", "both") and relation.source_id == entity_id:
                results.append(relation)
            if direction in ("incoming", "both") and relation.target_id == entity_id:
                results.append(relation)

        return results

    def get_neighbors(self, entity_id: str, max_depth: int = 2) -> dict:
        """获取邻居实体"""
        visited = set()
        result = {}

        def dfs(current_id, depth):
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)

            entity = self.entities.get(current_id)
            if not entity:
                return

            result[current_id] = {
                'entity': entity,
                'depth': depth,
                'relations': [],
            }

            for relation in self.get_relations(current_id):
                neighbor_id = (relation.target_id
                              if relation.source_id == current_id
                              else relation.source_id)

                result[current_id]['relations'].append({
                    'type': relation.relation_type.value,
                    'neighbor_id': neighbor_id,
                    'direction': 'outgoing' if relation.source_id == current_id else 'incoming',
                })

                dfs(neighbor_id, depth + 1)

        dfs(entity_id, 0)
        return result

    def query(self, query_type: str, **params) -> list:
        """查询图谱"""
        if query_type == "entities_by_type":
            entity_type = params.get('entity_type')
            return [e for e in self.entities.values()
                    if e.entity_type == entity_type]

        elif query_type == "relations_by_type":
            relation_type = params.get('relation_type')
            return [r for r in self.relations.values()
                    if r.relation_type == relation_type]

        elif query_type == "path":
            source_id = params.get('source_id')
            target_id = params.get('target_id')
            return self._find_path(source_id, target_id)

        return []

    def _find_path(self, source_id: str, target_id: str,
                   max_depth: int = 5) -> list:
        """查找两个实体间的路径"""
        from collections import deque

        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            current_id, path = queue.popleft()

            if current_id == target_id:
                return path

            if len(path) >= max_depth:
                continue

            for relation in self.get_relations(current_id):
                neighbor_id = (relation.target_id
                              if relation.source_id == current_id
                              else relation.source_id)

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return []

    def get_stats(self) -> dict:
        """获取图谱统计"""
        return {
            'total_entities': len(self.entities),
            'total_relations': len(self.relations),
            'entity_types': {
                t.value: sum(1 for e in self.entities.values()
                            if e.entity_type == t)
                for t in EntityType
            },
            'relation_types': {
                t.value: sum(1 for r in self.relations.values()
                            if r.relation_type == t)
                for t in RelationType
            },
        }


# ============================================================================
# 知识图谱引擎
# ============================================================================

class KnowledgeGraphEngine:
    """
    知识图谱引擎 - 整合所有组件

    核心功能：
    1. 从对话/代码中提取知识
    2. 构建和维护知识图谱
    3. 基于图谱进行推理
    4. 回答基于知识的问题
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "knowledge_graph"
        os.makedirs(storage_dir, exist_ok=True)

        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.store = KnowledgeGraphStore(
            os.path.join(storage_dir, "graph.json")
        )

    def learn_from_text(self, text: str, source: str = "") -> dict:
        """从文本中学习知识"""
        # 提取实体
        entities = self.entity_extractor.extract(text)

        # 提取关系
        relations = self.relation_extractor.extract(text, entities)

        # 添加到图谱
        added_entities = 0
        added_relations = 0

        entity_map = {}
        for entity in entities:
            entity.source = source
            entity_id = self.store.add_entity(entity)
            entity_map[entity.name] = entity_id
            added_entities += 1

        for rel in relations:
            source_name = rel['source']
            target_name = rel['target']

            if source_name in entity_map and target_name in entity_map:
                relation = Relation(
                    id=f"rel_{hashlib.md5(f'{source_name}:{target_name}:{rel["type"].value}'.encode()).hexdigest()[:12]}",
                    source_id=entity_map[source_name],
                    target_id=entity_map[target_name],
                    relation_type=rel['type'],
                    source=source,
                )
                if self.store.add_relation(relation):
                    added_relations += 1

        return {
            'entities_added': added_entities,
            'relations_added': added_relations,
        }

    def learn_from_code(self, code: str, file_path: str = "") -> dict:
        """从代码中学习知识"""
        # 提取实体
        entities = self.entity_extractor.extract_from_code(code)

        # 添加到图谱
        added = 0
        for entity in entities:
            entity.source = file_path
            self.store.add_entity(entity)
            added += 1

        return {'entities_added': added}

    def ask(self, question: str) -> dict:
        """基于知识图谱回答问题"""
        # 提取问题中的实体
        entities = self.entity_extractor.extract(question)

        if not entities:
            return {
                'answer': None,
                'confidence': 0.0,
                'reason': '未识别到实体',
            }

        # 查找相关实体
        found_entities = []
        for entity in entities:
            found = self.store.find_entity_by_name(entity.name)
            if found:
                found_entities.append(found)

        if not found_entities:
            return {
                'answer': None,
                'confidence': 0.0,
                'reason': '知识图谱中无相关实体',
            }

        # 获取邻居信息
        context = []
        for entity in found_entities[:3]:  # 最多查3个实体
            neighbors = self.store.get_neighbors(entity.id, max_depth=1)
            context.append(neighbors)

        return {
            'entities': [e.name for e in found_entities],
            'context': context,
            'confidence': 0.7,
        }

    def find_related(self, entity_name: str, max_depth: int = 2) -> dict:
        """查找相关知识"""
        entity = self.store.find_entity_by_name(entity_name)
        if not entity:
            return {'found': False, 'entity': entity_name}

        neighbors = self.store.get_neighbors(entity.id, max_depth)

        related = []
        for node_id, node_data in neighbors.items():
            if node_id != entity.id:
                related.append({
                    'name': node_data['entity'].name,
                    'type': node_data['entity'].entity_type.value,
                    'depth': node_data['depth'],
                    'relations': node_data['relations'],
                })

        return {
            'found': True,
            'entity': entity.name,
            'related': related,
        }

    def get_graph_stats(self) -> dict:
        """获取图谱统计"""
        return self.store.get_stats()

    def visualize_text(self) -> str:
        """文本可视化图谱"""
        stats = self.store.get_stats()
        lines = []
        lines.append("知识图谱概览:")
        lines.append(f"  实体数量: {stats['total_entities']}")
        lines.append(f"  关系数量: {stats['total_relations']}")
        lines.append("")

        lines.append("实体类型分布:")
        for etype, count in stats['entity_types'].items():
            if count > 0:
                lines.append(f"  {etype}: {count}")

        lines.append("")
        lines.append("关系类型分布:")
        for rtype, count in stats['relation_types'].items():
            if count > 0:
                lines.append(f"  {rtype}: {count}")

        # 显示一些示例
        lines.append("")
        lines.append("示例三元组:")
        shown = 0
        for relation in list(self.store.relations.values())[:5]:
            source = self.store.get_entity(relation.source_id)
            target = self.store.get_entity(relation.target_id)
            if source and target:
                lines.append(f"  {source.name} --[{relation.relation_type.value}]--> {target.name}")
                shown += 1

        return "\n".join(lines)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = KnowledgeGraphEngine("test_knowledge_graph")

    # 从文本学习
    texts = [
        "Python使用FastAPI框架构建Web应用",
        "FastAPI基于Starlette和Pydantic",
        "机器学习使用TensorFlow和PyTorch",
        "深度学习是机器学习的一部分",
        "Docker用于容器化部署",
    ]

    print("=== 从文本学习 ===")
    for text in texts:
        result = engine.learn_from_text(text)
        print(f"学习: {text}")
        print(f"  新增实体: {result['entities_added']}, 新增关系: {result['relations_added']}")

    # 查询
    print("\n=== 查询相关知识 ===")
    result = engine.find_related("Python")
    print(f"Python 相关: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 统计
    print("\n" + engine.visualize_text())