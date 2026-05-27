"""
================================================================================
记忆宫殿系统 (Memory Palace System)
================================================================================

核心能力：
  1. 空间记忆 - 利用空间位置组织记忆
  2. 联想记忆 - 通过联想增强记忆
  3. 层次组织 - 层次化组织知识
  4. 快速检索 - 基于位置快速检索
  5. 记忆强化 - 通过复习强化记忆

设计原则：
  - 空间化：将知识映射到空间位置
  - 联想化：建立知识间的联想
  - 层次化：层次组织便于检索
"""

import json
import os
import time
import hashlib
import math
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class LocationType(Enum):
    BUILDING = "building"        # 建筑
    ROOM = "room"                # 房间
    FURNITURE = "furniture"      # 家具
    OBJECT = "object"            # 物品

@dataclass
class MemoryLocation:
    """记忆位置"""
    id: str
    name: str
    location_type: LocationType
    parent_id: Optional[str] = None
    children: list = field(default_factory=list)
    coordinates: tuple = (0, 0, 0)  # x, y, z
    metadata: dict = field(default_factory=dict)

@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    location_id: str             # 存放位置
    associations: list = field(default_factory=list)  # 联想
    strength: float = 1.0        # 记忆强度
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    created_at: float = field(default_factory=time.time)

@dataclass
class MemoryPath:
    """记忆路径"""
    id: str
    name: str
    locations: list              # 路径上的位置
    description: str = ""


# ============================================================================
# 空间管理器
# ============================================================================

class SpatialManager:
    """空间管理器"""

    def __init__(self):
        self.locations: dict[str, MemoryLocation] = {}
        self._create_default_palace()

    def _create_default_palace(self):
        """创建默认记忆宫殿"""
        # 创建主建筑
        main_building = MemoryLocation(
            id="palace_main",
            name="主宫殿",
            location_type=LocationType.BUILDING,
        )
        self.locations[main_building.id] = main_building

        # 创建房间
        rooms = [
            ("room_entrance", "入口大厅"),
            ("room_library", "图书馆"),
            ("room_lab", "实验室"),
            ("room_workshop", "工作室"),
            ("room_garden", "花园"),
        ]

        for room_id, room_name in rooms:
            room = MemoryLocation(
                id=room_id,
                name=room_name,
                location_type=LocationType.ROOM,
                parent_id="palace_main",
            )
            self.locations[room_id] = room
            main_building.children.append(room_id)

        # 创建家具和物品
        furniture = [
            ("furniture_desk", "书桌", "room_library"),
            ("furniture_shelf", "书架", "room_library"),
            ("furniture_table", "实验台", "room_lab"),
            ("furniture_bench", "工作台", "room_workshop"),
        ]

        for furn_id, furn_name, parent_room in furniture:
            furn = MemoryLocation(
                id=furn_id,
                name=furn_name,
                location_type=LocationType.FURNITURE,
                parent_id=parent_room,
            )
            self.locations[furn_id] = furn
            self.locations[parent_room].children.append(furn_id)

    def add_location(self, name: str, location_type: LocationType,
                      parent_id: str = None,
                      coordinates: tuple = (0, 0, 0)) -> MemoryLocation:
        """添加位置"""
        location_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

        location = MemoryLocation(
            id=location_id,
            name=name,
            location_type=location_type,
            parent_id=parent_id,
            coordinates=coordinates,
        )

        self.locations[location_id] = location

        if parent_id and parent_id in self.locations:
            self.locations[parent_id].children.append(location_id)

        return location

    def get_location(self, location_id: str) -> Optional[MemoryLocation]:
        """获取位置"""
        return self.locations.get(location_id)

    def get_children(self, location_id: str) -> list:
        """获取子位置"""
        location = self.locations.get(location_id)
        if not location:
            return []

        return [self.locations[cid] for cid in location.children
                if cid in self.locations]

    def get_path_to_root(self, location_id: str) -> list:
        """获取到根的路径"""
        path = []
        current_id = location_id

        while current_id:
            location = self.locations.get(current_id)
            if not location:
                break
            path.append(location)
            current_id = location.parent_id

        path.reverse()
        return path

    def get_all_locations(self) -> list:
        """获取所有位置"""
        return list(self.locations.values())


# ============================================================================
# 联想管理器
# ============================================================================

class AssociationManager:
    """联想管理器"""

    def __init__(self):
        self.associations: dict[str, list] = {}  # item_id -> [associated_item_ids]

    def create_association(self, item_a_id: str, item_b_id: str,
                            strength: float = 0.5):
        """创建联想"""
        if item_a_id not in self.associations:
            self.associations[item_a_id] = []
        if item_b_id not in self.associations:
            self.associations[item_b_id] = []

        self.associations[item_a_id].append({'target': item_b_id, 'strength': strength})
        self.associations[item_b_id].append({'target': item_a_id, 'strength': strength})

    def get_associations(self, item_id: str) -> list:
        """获取联想"""
        return self.associations.get(item_id, [])

    def find_related(self, item_id: str, max_depth: int = 2) -> list:
        """查找相关项"""
        visited = set()
        related = []

        def dfs(current_id, depth):
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)

            for assoc in self.associations.get(current_id, []):
                target_id = assoc['target']
                if target_id not in visited:
                    related.append({
                        'item_id': target_id,
                        'depth': depth,
                        'strength': assoc['strength'],
                    })
                    dfs(target_id, depth + 1)

        dfs(item_id, 0)
        return related


# ============================================================================
# 记忆存储器
# ============================================================================

class MemoryStore:
    """记忆存储器"""

    def __init__(self):
        self.memories: dict[str, MemoryItem] = {}

    def store(self, content: str, location_id: str,
              associations: list = None) -> MemoryItem:
        """存储记忆"""
        memory_id = hashlib.md5(f"{content}{location_id}".encode()).hexdigest()[:12]

        memory = MemoryItem(
            id=memory_id,
            content=content,
            location_id=location_id,
            associations=associations or [],
        )

        self.memories[memory_id] = memory
        return memory

    def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """检索记忆"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.last_accessed = time.time()
            # 访问增强记忆
            memory.strength = min(1.0, memory.strength + 0.05)
        return memory

    def get_by_location(self, location_id: str) -> list:
        """按位置获取记忆"""
        return [m for m in self.memories.values()
                if m.location_id == location_id]

    def search(self, query: str) -> list:
        """搜索记忆"""
        results = []
        query_lower = query.lower()

        for memory in self.memories.values():
            if query_lower in memory.content.lower():
                results.append(memory)

        # 按强度排序
        results.sort(key=lambda m: m.strength, reverse=True)
        return results

    def apply_decay(self, decay_rate: float = 0.01):
        """应用遗忘衰减"""
        for memory in self.memories.values():
            # 基于时间的衰减
            time_since_access = time.time() - memory.last_accessed
            days = time_since_access / 86400
            memory.strength = max(0.1, memory.strength - decay_rate * days)


# ============================================================================
# 记忆宫殿引擎
# ============================================================================

class MemoryPalaceEngine:
    """
    记忆宫殿引擎 - 整合所有组件

    核心功能：
    1. 空间化组织知识
    2. 建立知识联想
    3. 快速检索知识
    4. 记忆强化
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "memory_palace"
        os.makedirs(storage_dir, exist_ok=True)

        self.spatial_manager = SpatialManager()
        self.association_manager = AssociationManager()
        self.memory_store = MemoryStore()

        self.palace_paths: dict[str, MemoryPath] = {}
        self._create_default_paths()

        self.storage_path = os.path.join(storage_dir, "palace.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 简化加载

    def _save(self):
        """保存数据"""
        data = {
            'memories': len(self.memory_store.memories),
            'locations': len(self.spatial_manager.locations),
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _create_default_paths(self):
        """创建默认路径"""
        # 学习路径
        learning_path = MemoryPath(
            id="path_learning",
            name="学习之旅",
            locations=["room_entrance", "room_library", "furniture_desk", "furniture_shelf"],
            description="从入口到图书馆的学习路径",
        )
        self.palace_paths[learning_path.id] = learning_path

        # 实践路径
        practice_path = MemoryPath(
            id="path_practice",
            name="实践之路",
            locations=["room_entrance", "room_lab", "room_workshop", "furniture_bench"],
            description="从入口到工作室的实践路径",
        )
        self.palace_paths[practice_path.id] = practice_path

    def memorize(self, content: str, location_id: str = None,
                  associations: list = None) -> MemoryItem:
        """记忆内容"""
        # 如果没有指定位置，自动选择
        if not location_id:
            location_id = self._select_location(content)

        # 存储记忆
        memory = self.memory_store.store(content, location_id, associations)

        # 建立联想
        if associations:
            for assoc_id in associations:
                self.association_manager.create_association(memory.id, assoc_id)

        self._save()
        return memory

    def _select_location(self, content: str) -> str:
        """自动选择位置"""
        content_lower = content.lower()

        # 基于内容选择房间
        if any(kw in content_lower for kw in ['学习', '知识', '理论']):
            return "room_library"
        elif any(kw in content_lower for kw in ['实验', '测试', '验证']):
            return "room_lab"
        elif any(kw in content_lower for kw in ['实践', '开发', '编码']):
            return "room_workshop"
        else:
            return "room_entrance"

    def recall(self, query: str) -> list:
        """回忆"""
        # 搜索记忆
        memories = self.memory_store.search(query)

        # 增强找到的记忆
        for memory in memories:
            memory.strength = min(1.0, memory.strength + 0.1)
            memory.access_count += 1

        return memories

    def walk_path(self, path_id: str) -> list:
        """遍历路径"""
        path = self.palace_paths.get(path_id)
        if not path:
            return []

        journey = []
        for location_id in path.locations:
            location = self.spatial_manager.get_location(location_id)
            memories = self.memory_store.get_by_location(location_id)

            journey.append({
                'location': location.name if location else location_id,
                'memories': [m.content for m in memories],
            })

        return journey

    def strengthen_memory(self, memory_id: str) -> bool:
        """强化记忆"""
        memory = self.memory_store.retrieve(memory_id)
        if memory:
            memory.strength = min(1.0, memory.strength + 0.2)
            return True
        return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_memories': len(self.memory_store.memories),
            'total_locations': len(self.spatial_manager.locations),
            'total_paths': len(self.palace_paths),
            'total_associations': len(self.association_manager.associations),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🏛️ 记忆宫殿报告")
        report.append("=" * 50)
        report.append(f"\n记忆总数: {stats['total_memories']}")
        report.append(f"位置总数: {stats['total_locations']}")
        report.append(f"路径总数: {stats['total_paths']}")
        report.append(f"联想总数: {stats['total_associations']}")

        # 按位置统计
        location_counts = {}
        for memory in self.memory_store.memories.values():
            loc = memory.location_id
            location_counts[loc] = location_counts.get(loc, 0) + 1

        if location_counts:
            report.append("\n记忆分布:")
            for loc_id, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                location = self.spatial_manager.get_location(loc_id)
                name = location.name if location else loc_id
                report.append(f"  - {name}: {count}条记忆")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = MemoryPalaceEngine("test_memory_palace")

    # 记忆内容
    print("=== 记忆存储 ===")
    memories = [
        ("Python列表推导式", "room_library"),
        ("机器学习基础概念", "room_library"),
        ("数据库优化技巧", "room_lab"),
        ("API设计原则", "room_workshop"),
    ]

    for content, location in memories:
        memory = engine.memorize(content, location)
        print(f"记忆: {content} -> {location} (ID: {memory.id})")

    # 回忆
    print("\n=== 回忆测试 ===")
    results = engine.recall("Python")
    for r in results:
        print(f"  - {r.content} (强度: {r.strength:.2f})")

    # 遍历路径
    print("\n=== 路径遍历 ===")
    journey = engine.walk_path("path_learning")
    for step in journey:
        print(f"  {step['location']}: {len(step['memories'])}条记忆")

    # 报告
    print("\n" + engine.generate_report())