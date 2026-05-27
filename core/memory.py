"""
================================================================================
层次1：记忆积累系统 (Memory Accumulation System)
================================================================================

核心能力：
  1. 短期记忆 - 当前会话上下文 (滑动窗口 + 摘要压缩)
  2. 长期记忆 - 向量化存储 + 语义检索 (FAISS / ChromaDB)
  3. 情景记忆 - 关键事件/教训的结构化存储
  4. 用户画像 - 偏好、习惯、知识水平的持续学习
  5. 记忆巩固 - 睡眠式回放：将短期记忆提炼为长期记忆

设计原则：
  - 存储与计算分离：支持本地文件 / 向量DB / 云存储多后端
  - 遗忘曲线模拟：不重要的记忆随时间衰减
  - 冲突检测：新旧知识矛盾时触发反思
"""

import json
import os
import time
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from enum import Enum

# ============================================================================
# 数据结构
# ============================================================================

class MemoryType(Enum):
    SHORT_TERM = "short_term"      # 当前会话
    LONG_TERM = "long_term"        # 持久化知识
    EPISODIC = "episodic"          # 关键事件
    PROFILE = "profile"            # 用户画像
    LESSON = "lesson"              # 经验教训

class MemoryImportance(Enum):
    TRIVIAL = 0     # 琐碎，快速遗忘
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4    # 关键，永不遗忘

@dataclass
class MemoryItem:
    """单条记忆"""
    id: str
    content: str
    memory_type: MemoryType
    importance: MemoryImportance = MemoryImportance.MEDIUM
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 0.01       # 遗忘速率
    embedding: Optional[list] = None  # 向量嵌入（简化用hash模拟）
    tags: list = field(default_factory=list)
    source: str = ""               # 来源会话ID
    confidence: float = 1.0        # 置信度
    contradictions: list = field(default_factory=list)  # 冲突记忆ID列表

    def to_dict(self) -> dict:
        d = asdict(self)
        d['memory_type'] = self.memory_type.value
        d['importance'] = self.importance.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'MemoryItem':
        d['memory_type'] = MemoryType(d['memory_type'])
        d['importance'] = MemoryImportance(d['importance'])
        return cls(**d)

    def strength(self) -> float:
        """计算记忆强度（考虑遗忘）"""
        age = time.time() - self.created_at
        decay = self.decay_rate * (self.importance.value + 1)  # 重要记忆衰减更慢
        return max(0.01, 1.0 - decay * (age / 86400))  # 以天为单位

    def should_forget(self, threshold: float = 0.05) -> bool:
        """判断是否应该遗忘"""
        if self.importance == MemoryImportance.CRITICAL:
            return False
        return self.strength() < threshold


@dataclass
class UserProfile:
    """用户画像"""
    preferences: dict = field(default_factory=dict)      # 偏好设置
    expertise: dict = field(default_factory=dict)         # 各领域专业水平
    interaction_style: dict = field(default_factory=dict) # 交互风格
    goals: list = field(default_factory=list)             # 当前目标
    vocabulary: list = field(default_factory=list)        # 常用术语
    weaknesses: list = field(default_factory=list)        # 薄弱环节
    evolution_history: list = field(default_factory=list) # 画像演化历史


# ============================================================================
# 向量嵌入 (简易版 - 用语义hash模拟)
# ============================================================================

class SimpleEmbedder:
    """简易嵌入器：用 N-gram Hash 模拟语义向量
    生产环境应替换为 sentence-transformers 或 OpenAI embeddings
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, text: str) -> list:
        """生成简易嵌入向量"""
        vec = [0.0] * self.dim
        # 字符级 n-gram hash
        for i in range(len(text) - 2):
            ngram = text[i:i+3]
            h = hashlib.md5(ngram.encode()).digest()
            for j in range(0, len(h), 2):
                idx = int.from_bytes(h[j:j+2], 'big') % self.dim
                vec[idx] += 0.01
        # 归一化
        norm = max(0.0001, sum(v*v for v in vec) ** 0.5)
        return [v / norm for v in vec]

    def similarity(self, emb1: list, emb2: list) -> float:
        """余弦相似度"""
        if not emb1 or not emb2:
            return 0.0
        dot = sum(a * b for a, b in zip(emb1, emb2))
        return max(0.0, min(1.0, dot))


# ============================================================================
# 记忆存储后端
# ============================================================================

class MemoryStore:
    """文件系统持久化存储"""

    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._cache: dict[str, MemoryItem] = {}

    def _path(self, mem_id: str) -> str:
        return os.path.join(self.base_path, f"{mem_id}.json")

    def save(self, item: MemoryItem):
        self._cache[item.id] = item
        with open(self._path(item.id), 'w', encoding='utf-8') as f:
            json.dump(item.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, mem_id: str) -> Optional[MemoryItem]:
        if mem_id in self._cache:
            return self._cache[mem_id]
        path = self._path(mem_id)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                item = MemoryItem.from_dict(json.load(f))
                self._cache[item.id] = item
                return item
        return None

    def delete(self, mem_id: str):
        self._cache.pop(mem_id, None)
        path = self._path(mem_id)
        if os.path.exists(path):
            os.remove(path)

    def all_ids(self) -> list:
        ids = []
        for f in os.listdir(self.base_path):
            if f.endswith('.json') and not f.startswith('_'):
                ids.append(f[:-5])
        return ids

    def all_items(self) -> list:
        return [self.load(mid) for mid in self.all_ids() if self.load(mid)]


# ============================================================================
# 记忆管理器
# ============================================================================

class MemoryManager:
    """
    记忆管理器 - 自我进化AI的记忆核心

    特性：
    - 短期记忆：滑动窗口 + 自动摘要
    - 长期记忆：语义检索 + 遗忘曲线
    - 情景记忆：教训提取
    - 记忆巩固：定期将短期记忆提炼为长期记忆
    - 冲突检测：新旧知识矛盾时标记
    """

    def __init__(self, store_path: str = None):
        if store_path is None:
            store_path = os.path.join(os.path.dirname(__file__), '..', 'memory')
        self.store = MemoryStore(store_path)
        self.embedder = SimpleEmbedder()

        # 短期记忆窗口
        self.short_term: OrderedDict[str, MemoryItem] = OrderedDict()
        self.short_term_limit = 50  # 最多保留条数

        # 用户画像
        self._profile_path = os.path.join(store_path, '_user_profile.json')
        self.profile = self._load_profile()

        # 统计
        self.stats = {
            "total_created": 0,
            "total_forgotten": 0,
            "consolidations": 0,
            "conflicts_resolved": 0,
        }
        self._load_stats()

    def _load_profile(self) -> UserProfile:
        if os.path.exists(self._profile_path):
            with open(self._profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return UserProfile(**data)
        return UserProfile()

    def _save_profile(self):
        with open(self._profile_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.profile), f, ensure_ascii=False, indent=2)

    def _load_stats(self):
        stats_path = os.path.join(self.store.base_path, '_stats.json')
        if os.path.exists(stats_path):
            with open(stats_path, 'r', encoding='utf-8') as f:
                self.stats.update(json.load(f))

    def _save_stats(self):
        with open(os.path.join(self.store.base_path, '_stats.json'), 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    # ---- 创建记忆 ----

    def remember(self, content: str,
                 memory_type: MemoryType = MemoryType.SHORT_TERM,
                 importance: MemoryImportance = None,
                 tags: list = None,
                 source: str = "",
                 confidence: float = 1.0) -> MemoryItem:
        """创建一条新记忆"""
        # 自动评估重要性
        if importance is None:
            importance = self._auto_importance(content)

        # 生成ID
        raw = f"{content}{time.time()}{len(self.short_term)}"
        mem_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

        item = MemoryItem(
            id=mem_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags or [],
            source=source,
            confidence=confidence,
        )

        # 生成嵌入
        item.embedding = self.embedder.embed(content)

        # 存入短期记忆
        self.short_term[item.id] = item
        self._trim_short_term()

        # 重要或长期记忆直接持久化
        if memory_type in (MemoryType.LONG_TERM, MemoryType.EPISODIC, MemoryType.LESSON) \
           or importance.value >= MemoryImportance.HIGH.value:
            self.store.save(item)

        self.stats["total_created"] += 1
        self._save_stats()

        # 检查冲突
        self._detect_conflicts(item)

        return item

    def _auto_importance(self, content: str) -> MemoryImportance:
        """自动评估记忆重要性"""
        high_keywords = ['关键', '重要', '必须', '核心', '教训', '错误', 'bug',
                        'critical', 'important', 'lesson', 'profile', 'preference']
        medium_keywords = ['注意', '建议', '反馈', '修改', '优化', '配置']

        content_lower = content.lower()
        for kw in high_keywords:
            if kw in content_lower:
                return MemoryImportance.HIGH
        for kw in medium_keywords:
            if kw in content_lower:
                return MemoryImportance.MEDIUM
        return MemoryImportance.LOW

    def _trim_short_term(self):
        """裁剪短期记忆窗口"""
        while len(self.short_term) > self.short_term_limit:
            oldest_id, oldest = self.short_term.popitem(last=False)
            # 重要记忆提级保存
            if oldest.importance.value >= MemoryImportance.MEDIUM.value:
                oldest.memory_type = MemoryType.LONG_TERM
                self.store.save(oldest)

    # ---- 检索记忆 ----

    def recall(self, query: str, top_k: int = 5,
               memory_types: list = None,
               min_strength: float = 0.1) -> list:
        """语义检索记忆（先搜长期，再搜短期）"""
        query_emb = self.embedder.embed(query)
        candidates = []

        # 搜索长期记忆
        for item in self.store.all_items():
            if item is None:
                continue
            if memory_types and item.memory_type not in memory_types:
                continue
            if item.should_forget():
                continue
            sim = self.embedder.similarity(query_emb, item.embedding)
            if sim > 0.1:
                candidates.append((sim, item))

        # 搜索短期记忆
        for item in self.short_term.values():
            if memory_types and item.memory_type not in memory_types:
                continue
            sim = self.embedder.similarity(query_emb, item.embedding)
            if sim > 0.1:
                candidates.append((sim * 1.2, item))  # 短期记忆加权

        # 排序去重
        seen = set()
        results = []
        candidates.sort(key=lambda x: x[0], reverse=True)
        for sim, item in candidates:
            if item.id not in seen:
                seen.add(item.id)
                item.last_accessed = time.time()
                item.access_count += 1
                results.append((sim, item))
                if len(results) >= top_k:
                    break

        return results

    def recall_by_tags(self, tags: list, match_all: bool = False) -> list:
        """按标签检索"""
        results = []
        for item in list(self.short_term.values()) + self.store.all_items():
            if item is None:
                continue
            if match_all:
                if all(t in item.tags for t in tags):
                    results.append(item)
            else:
                if any(t in item.tags for t in tags):
                    results.append(item)
        return results

    def recall_lessons(self, context: str = "", top_k: int = 3) -> list:
        """回忆相关经验教训"""
        query = f"lesson mistake error bug 教训 错误 {context}"
        return self.recall(query, top_k, memory_types=[MemoryType.LESSON, MemoryType.EPISODIC])

    # ---- 冲突检测 ----

    def _detect_conflicts(self, new_item: MemoryItem):
        """检测新记忆是否与旧记忆冲突"""
        if new_item.confidence < 0.6:
            return  # 低置信度不检测

        query_emb = new_item.embedding
        for item in self.store.all_items():
            if item is None or item.id == new_item.id:
                continue
            sim = self.embedder.similarity(query_emb, item.embedding)
            # 高度相似但内容可能矛盾
            if sim > 0.7:
                # 检查矛盾关键词
                contradiction_signals = ['not', '不', 'no', '错误', 'wrong', 'false',
                                        'but', '但是', '然而', 'however', 'actually']
                has_signal = any(s in new_item.content.lower() for s in contradiction_signals)
                if has_signal:
                    new_item.contradictions.append(item.id)
                    item.contradictions.append(new_item.id)
                    self.store.save(item)

    def resolve_conflict(self, mem_id: str, keep: bool = True,
                        resolution_note: str = ""):
        """解决冲突"""
        item = self.store.load(mem_id)
        if item:
            for conflict_id in item.contradictions:
                conflict_item = self.store.load(conflict_id)
                if conflict_item:
                    if keep:
                        conflict_item.confidence *= 0.5
                        conflict_item.tags.append("resolved_conflict")
                        self.store.save(conflict_item)
                    else:
                        self.store.delete(conflict_id)
            item.contradictions = []
            item.tags.append("conflict_resolved")
            self.store.save(item)
        self.stats["conflicts_resolved"] += 1
        self._save_stats()

    # ---- 记忆巩固 ----

    def consolidate(self):
        """
        记忆巩固（模拟睡眠过程）
        - 短期记忆中的重要内容提炼为长期记忆
        - 整合相关记忆
        - 清理过期记忆
        """
        consolidated = 0

        for item in list(self.short_term.values()):
            # 高重要性 → 长期记忆
            if item.importance.value >= MemoryImportance.HIGH.value:
                item.memory_type = MemoryType.LONG_TERM
                self.store.save(item)
                consolidated += 1

            # 有多次访问 → 值得保留
            if item.access_count >= 3:
                item.memory_type = MemoryType.LONG_TERM
                item.importance = MemoryImportance(
                    min(4, item.importance.value + 1)
                )
                self.store.save(item)
                consolidated += 1

        # 清理已遗忘的长期记忆
        forgotten = 0
        for item in self.store.all_items():
            if item and item.should_forget():
                self.store.delete(item.id)
                forgotten += 1

        # 短期记忆中去重整合
        self._merge_similar_memories()

        self.stats["consolidations"] += 1
        self.stats["total_forgotten"] += forgotten
        self._save_stats()

        return {
            "consolidated": consolidated,
            "forgotten": forgotten,
            "short_term_size": len(self.short_term),
            "long_term_size": len(self.store.all_ids()),
        }

    def _merge_similar_memories(self):
        """合并相似记忆"""
        items = list(self.short_term.values())
        to_merge = []

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                sim = self.embedder.similarity(items[i].embedding, items[j].embedding)
                if sim > 0.85:
                    to_merge.append((items[i].id, items[j].id))

        merged = set()
        for id1, id2 in to_merge:
            if id1 in merged or id2 in merged:
                continue
            # 保留更重要的
            if id1 in self.short_term and id2 in self.short_term:
                keep, drop = (id1, id2) if \
                    self.short_term[id1].importance.value >= self.short_term[id2].importance.value \
                    else (id2, id1)
                self.short_term[keep].confidence = max(
                    self.short_term[keep].confidence,
                    self.short_term[drop].confidence
                )
                self.short_term[keep].access_count += self.short_term[drop].access_count
                del self.short_term[drop]
                merged.add(keep)
                merged.add(drop)

    # ---- 用户画像 ----

    def update_profile(self, field: str, key: str, value,
                       confidence: float = 0.8):
        """更新用户画像"""
        if field == 'preferences':
            self.profile.preferences[key] = {
                'value': value,
                'confidence': confidence,
                'updated_at': time.time(),
            }
        elif field == 'expertise':
            self.profile.expertise[key] = {
                'level': value,
                'confidence': confidence,
                'updated_at': time.time(),
            }
        elif field == 'interaction_style':
            self.profile.interaction_style[key] = value
        elif field == 'goals':
            if value not in self.profile.goals:
                self.profile.goals.append(value)
        elif field == 'learning':
            self.profile.weaknesses.append({
                'topic': key,
                'note': value,
                'timestamp': time.time(),
            })

        self.profile.evolution_history.append({
            'field': field,
            'key': key,
            'value': str(value)[:100],
            'timestamp': time.time(),
        })
        self._save_profile()

        # 同时创建一条长期记忆
        self.remember(
            f"[用户画像] {field}.{key} = {str(value)[:200]}",
            memory_type=MemoryType.PROFILE,
            importance=MemoryImportance.HIGH,
            tags=['profile', field],
        )

    def get_profile_summary(self) -> str:
        """生成用户画像摘要"""
        lines = ["📊 用户画像摘要:"]

        if self.profile.preferences:
            lines.append("  🎯 偏好:")
            for k, v in self.profile.preferences.items():
                conf = v.get('confidence', 1.0)
                lines.append(f"    - {k}: {v.get('value', v)} (置信度:{conf:.0%})")

        if self.profile.expertise:
            lines.append("  🧠 专业水平:")
            for k, v in self.profile.expertise.items():
                lines.append(f"    - {k}: {v.get('level', v)}")

        if self.profile.goals:
            lines.append("  🚀 当前目标:")
            for g in self.profile.goals[-5:]:
                lines.append(f"    - {g}")

        if self.profile.weaknesses:
            lines.append("  ⚡ 薄弱环节:")
            for w in self.profile.weaknesses[-5:]:
                lines.append(f"    - {w['topic']}: {w['note']}")

        return "\n".join(lines) if len(lines) > 1 else "暂无用户画像"

    # ---- 摘要 ----

    def summarize(self) -> dict:
        """生成记忆系统状态摘要"""
        return {
            "short_term_memories": len(self.short_term),
            "long_term_memories": len(self.store.all_ids()),
            "profile_updated": bool(self.profile.evolution_history),
            "profile_fields": len(self.profile.preferences) + len(self.profile.expertise),
            "pending_conflicts": sum(
                1 for m in self.store.all_items() if m and m.contradictions
            ),
            "stats": self.stats,
        }


# ============================================================================
# 简易测试
# ============================================================================

if __name__ == "__main__":
    mm = MemoryManager()

    # 模拟对话
    mm.remember("用户叫张三，是一名Python后端开发工程师", tags=["user_info"])
    mm.remember("用户偏好简洁的代码风格，不喜欢过度注释", tags=["preference"])
    mm.remember("上次项目使用了FastAPI框架，遇到了CORS配置问题",
                memory_type=MemoryType.EPISODIC, tags=["project", "issue"])

    # 用户画像
    mm.update_profile('preferences', 'code_style', '简洁')
    mm.update_profile('expertise', 'Python', '高级')
    mm.update_profile('expertise', '机器学习', '中级')
    mm.update_profile('goals', '', '构建自我进化的AI系统')

    # 检索
    results = mm.recall("用户用的什么技术栈？")
    print("\n=== 检索结果 ===")
    for sim, item in results:
        print(f"[{sim:.2f}] {item.content}")

    # 记忆巩固
    result = mm.consolidate()
    print(f"\n=== 记忆巩固 ===")
    print(result)

    # 用户画像
    print(f"\n{mm.get_profile_summary()}")

    print(f"\n=== 系统状态 ===")
    print(mm.summarize())