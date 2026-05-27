"""
================================================================================
知识演化系统 (Knowledge Evolution System)
================================================================================

核心能力：
  1. 知识版本管理 - 管理知识的版本
  2. 知识更新追踪 - 追踪知识的变化
  3. 知识冲突检测 - 检测知识间的冲突
  4. 知识合并 - 合并相关知识
  5. 知识废弃 - 标记和处理过时知识

设计原则：
  - 可追溯：所有知识变化都有记录
  - 一致性：维护知识的一致性
  - 时效性：及时更新过时知识
"""

import json
import os
import time
import hashlib
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class KnowledgeStatus(Enum):
    ACTIVE = "active"            # 活跃
    DEPRECATED = "deprecated"    # 已废弃
    SUPERSEDED = "superseded"    # 已被替代
    DISPUTED = "disputed"        # 有争议
    DRAFT = "draft"              # 草稿

class ChangeType(Enum):
    CREATE = "create"            # 创建
    UPDATE = "update"            # 更新
    MERGE = "merge"              # 合并
    DEPRECATE = "deprecate"      # 废弃
    DELETE = "delete"            # 删除

@dataclass
class KnowledgeVersion:
    """知识版本"""
    version_id: str
    knowledge_id: str
    content: str
    status: KnowledgeStatus
    confidence: float
    created_at: float = field(default_factory=time.time)
    created_by: str = "system"
    change_type: ChangeType = ChangeType.CREATE
    change_reason: str = ""
    parent_version: str = ""

@dataclass
class KnowledgeItem:
    """知识项"""
    id: str
    domain: str
    topic: str
    current_version: str
    versions: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: list = field(default_factory=list)

@dataclass
class KnowledgeConflict:
    """知识冲突"""
    id: str
    knowledge_ids: list
    conflict_type: str
    description: str
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""


# ============================================================================
# 版本管理器
# ============================================================================

class VersionManager:
    """版本管理器"""

    def __init__(self):
        self.versions: dict[str, KnowledgeVersion] = {}
        self.version_history: dict[str, list] = {}  # knowledge_id -> [version_ids]

    def create_version(self, knowledge_id: str, content: str,
                        status: KnowledgeStatus = KnowledgeStatus.ACTIVE,
                        confidence: float = 0.8,
                        change_type: ChangeType = ChangeType.CREATE,
                        change_reason: str = "",
                        parent_version: str = "") -> KnowledgeVersion:
        """创建新版本"""
        version_id = hashlib.md5(
            f"{knowledge_id}:{content}:{time.time()}".encode()
        ).hexdigest()[:12]

        version = KnowledgeVersion(
            version_id=version_id,
            knowledge_id=knowledge_id,
            content=content,
            status=status,
            confidence=confidence,
            change_type=change_type,
            change_reason=change_reason,
            parent_version=parent_version,
        )

        self.versions[version_id] = version

        if knowledge_id not in self.version_history:
            self.version_history[knowledge_id] = []
        self.version_history[knowledge_id].append(version_id)

        return version

    def get_version(self, version_id: str) -> Optional[KnowledgeVersion]:
        """获取版本"""
        return self.versions.get(version_id)

    def get_latest_version(self, knowledge_id: str) -> Optional[KnowledgeVersion]:
        """获取最新版本"""
        history = self.version_history.get(knowledge_id, [])
        if not history:
            return None
        return self.versions.get(history[-1])

    def get_version_history(self, knowledge_id: str) -> list:
        """获取版本历史"""
        history = self.version_history.get(knowledge_id, [])
        return [self.versions[vid] for vid in history if vid in self.versions]


# ============================================================================
# 知识冲突检测器
# ============================================================================

class ConflictDetector:
    """知识冲突检测器"""

    def __init__(self):
        self.conflicts: list[KnowledgeConflict] = []

    def detect(self, knowledge_items: list) -> list:
        """检测知识冲突"""
        conflicts = []

        # 两两比较
        for i in range(len(knowledge_items)):
            for j in range(i + 1, len(knowledge_items)):
                item_a = knowledge_items[i]
                item_b = knowledge_items[j]

                # 检查是否冲突
                conflict = self._check_conflict(item_a, item_b)
                if conflict:
                    conflicts.append(conflict)
                    self.conflicts.append(conflict)

        return conflicts

    def _check_conflict(self, item_a: KnowledgeItem,
                          item_b: KnowledgeItem) -> Optional[KnowledgeConflict]:
        """检查两个知识项是否冲突"""
        # 同主题不同内容可能是冲突
        if item_a.topic == item_b.topic and item_a.domain == item_b.domain:
            # 获取最新内容
            content_a = self._get_content(item_a)
            content_b = self._get_content(item_b)

            if content_a and content_b and content_a != content_b:
                # 简单相似度检查
                similarity = self._calculate_similarity(content_a, content_b)
                if similarity < 0.5:  # 差异较大
                    return KnowledgeConflict(
                        id=hashlib.md5(f"{item_a.id}:{item_b.id}".encode()).hexdigest()[:12],
                        knowledge_ids=[item_a.id, item_b.id],
                        conflict_type="content_conflict",
                        description=f"同主题 '{item_a.topic}' 存在不同内容",
                    )

        return None

    def _get_content(self, item: KnowledgeItem) -> str:
        """获取知识内容"""
        # 这里需要访问版本管理器，简化实现
        return ""

    def _calculate_similarity(self, text_a: str, text_b: str) -> float:
        """计算文本相似度"""
        words_a = set(text_a.split())
        words_b = set(text_b.split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0

    def resolve_conflict(self, conflict_id: str,
                          resolution: str) -> bool:
        """解决冲突"""
        for conflict in self.conflicts:
            if conflict.id == conflict_id:
                conflict.resolved = True
                conflict.resolution = resolution
                return True
        return False


# ============================================================================
# 知识合并器
# ============================================================================

class KnowledgeMerger:
    """知识合并器"""

    def merge(self, items: list,
              strategy: str = "combine") -> Optional[KnowledgeItem]:
        """合并知识"""
        if not items:
            return None

        if len(items) == 1:
            return items[0]

        # 按策略合并
        if strategy == "combine":
            return self._combine(items)
        elif strategy == "best":
            return self._select_best(items)
        else:
            return self._combine(items)

    def _combine(self, items: list) -> KnowledgeItem:
        """组合合并"""
        # 取第一个作为基础
        base = items[0]

        # 合并标签
        all_tags = set(base.tags)
        for item in items[1:]:
            all_tags.update(item.tags)

        # 创建合并后的知识
        merged = KnowledgeItem(
            id=hashlib.md5(f"merged:{base.id}:{time.time()}".encode()).hexdigest()[:12],
            domain=base.domain,
            topic=base.topic,
            current_version=base.current_version,
            tags=list(all_tags),
        )

        return merged

    def _select_best(self, items: list) -> KnowledgeItem:
        """选择最佳"""
        # 简单实现：返回第一个
        return items[0]


# ============================================================================
# 知识演化引擎
# ============================================================================

class KnowledgeEvolutionEngine:
    """
    知识演化引擎 - 整合所有组件

    核心功能：
    1. 管理知识版本
    2. 追踪知识变化
    3. 检测和解决冲突
    4. 合并相关知识
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "knowledge_evolution"
        os.makedirs(storage_dir, exist_ok=True)

        self.version_manager = VersionManager()
        self.conflict_detector = ConflictDetector()
        self.knowledge_merger = KnowledgeMerger()

        self.knowledge_base: dict[str, KnowledgeItem] = {}

        self.storage_path = os.path.join(storage_dir, "evolution.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 简化加载
                for k_data in data.get('knowledge', []):
                    item = KnowledgeItem(**k_data)
                    self.knowledge_base[item.id] = item

    def _save(self):
        """保存数据"""
        data = {
            'knowledge': [asdict(k) for k in self.knowledge_base.values()],
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_knowledge(self, domain: str, topic: str,
                      content: str, confidence: float = 0.8) -> KnowledgeItem:
        """添加知识"""
        item_id = hashlib.md5(f"{domain}:{topic}".encode()).hexdigest()[:12]

        # 创建版本
        version = self.version_manager.create_version(
            knowledge_id=item_id,
            content=content,
            confidence=confidence,
        )

        # 创建知识项
        item = KnowledgeItem(
            id=item_id,
            domain=domain,
            topic=topic,
            current_version=version.version_id,
            versions=[version.version_id],
        )

        self.knowledge_base[item_id] = item
        self._save()

        return item

    def update_knowledge(self, knowledge_id: str,
                          new_content: str,
                          reason: str = "") -> Optional[KnowledgeVersion]:
        """更新知识"""
        item = self.knowledge_base.get(knowledge_id)
        if not item:
            return None

        # 创建新版本
        version = self.version_manager.create_version(
            knowledge_id=knowledge_id,
            content=new_content,
            change_type=ChangeType.UPDATE,
            change_reason=reason,
            parent_version=item.current_version,
        )

        # 更新知识项
        item.current_version = version.version_id
        item.versions.append(version.version_id)
        item.updated_at = time.time()

        self._save()

        return version

    def deprecate_knowledge(self, knowledge_id: str,
                             reason: str = "") -> bool:
        """废弃知识"""
        item = self.knowledge_base.get(knowledge_id)
        if not item:
            return False

        # 创建废弃版本
        version = self.version_manager.create_version(
            knowledge_id=knowledge_id,
            content="[已废弃]",
            status=KnowledgeStatus.DEPRECATED,
            change_type=ChangeType.DEPRECATE,
            change_reason=reason,
            parent_version=item.current_version,
        )

        item.current_version = version.version_id
        item.versions.append(version.version_id)
        item.updated_at = time.time()

        self._save()

        return True

    def detect_conflicts(self) -> list:
        """检测冲突"""
        items = list(self.knowledge_base.values())
        return self.conflict_detector.detect(items)

    def get_knowledge_history(self, knowledge_id: str) -> list:
        """获取知识历史"""
        return self.version_manager.get_version_history(knowledge_id)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_knowledge': len(self.knowledge_base),
            'total_versions': len(self.version_manager.versions),
            'total_conflicts': len(self.conflict_detector.conflicts),
            'resolved_conflicts': sum(
                1 for c in self.conflict_detector.conflicts if c.resolved
            ),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("📈 知识演化报告")
        report.append("=" * 50)
        report.append(f"\n知识总数: {stats['total_knowledge']}")
        report.append(f"版本总数: {stats['total_versions']}")
        report.append(f"冲突总数: {stats['total_conflicts']}")
        report.append(f"已解决冲突: {stats['resolved_conflicts']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = KnowledgeEvolutionEngine("test_knowledge_evolution")

    # 添加知识
    print("=== 添加知识 ===")
    items = [
        ("python", "列表推导式", "列表推导式是Python中创建列表的简洁方式"),
        ("python", "装饰器", "装饰器是修改函数行为的函数"),
        ("python", "列表推导式", "列表推导式可以包含条件判断"),
    ]

    for domain, topic, content in items:
        item = engine.add_knowledge(domain, topic, content)
        print(f"添加: {topic} (ID: {item.id})")

    # 更新知识
    print("\n=== 更新知识 ===")
    first_id = list(engine.knowledge_base.keys())[0]
    engine.update_knowledge(first_id, "更新后的列表推导式说明", "添加了更多细节")

    # 检测冲突
    print("\n=== 冲突检测 ===")
    conflicts = engine.detect_conflicts()
    print(f"发现冲突: {len(conflicts)}")

    # 历史
    print("\n=== 知识历史 ===")
    history = engine.get_knowledge_history(first_id)
    print(f"版本数: {len(history)}")

    # 报告
    print("\n" + engine.generate_report())