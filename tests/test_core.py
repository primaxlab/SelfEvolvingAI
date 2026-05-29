"""
================================================================================
SelfEvolvingAI 核心测试套件 v3 (最终版)
================================================================================

运行: pytest tests/ -v
"""

import pytest
import json
import os
import sys
import time
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import (
    MemoryManager, MemoryItem, MemoryType, MemoryImportance,
    SimpleEmbedder, MemoryStore, UserProfile
)


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def memory_manager(temp_dir):
    return MemoryManager(temp_dir)


@pytest.fixture
def sample_memory_item():
    return MemoryItem(
        id="test_001",
        content="Python的GIL限制了多线程性能",
        memory_type=MemoryType.LONG_TERM,
        importance=MemoryImportance.HIGH,
        tags=["python", "performance"],
        source="test_session"
    )


# ============================================================================
# MemoryItem 测试
# ============================================================================

class TestMemoryItem:

    def test_creation(self, sample_memory_item):
        assert sample_memory_item.id == "test_001"
        assert sample_memory_item.content == "Python的GIL限制了多线程性能"
        assert sample_memory_item.memory_type == MemoryType.LONG_TERM
        assert sample_memory_item.importance == MemoryImportance.HIGH
        assert "python" in sample_memory_item.tags

    def test_strength_decay(self, sample_memory_item):
        strength = sample_memory_item.strength()
        assert 0.9 <= strength <= 1.0

    def test_strength_critical_never_forgets(self):
        item = MemoryItem(
            id="critical_001", content="重要密码",
            memory_type=MemoryType.LONG_TERM,
            importance=MemoryImportance.CRITICAL,
            created_at=time.time() - 86400 * 365
        )
        assert item.should_forget() is False

    def test_should_forget_low_importance_old(self):
        item = MemoryItem(
            id="low_001", content="随便记的",
            memory_type=MemoryType.SHORT_TERM,
            importance=MemoryImportance.LOW,
            created_at=time.time() - 86400 * 60,
            decay_rate=0.05
        )
        assert item.should_forget(threshold=0.3) is True

    def test_to_dict_and_from_dict(self, sample_memory_item):
        d = sample_memory_item.to_dict()
        assert d['id'] == "test_001"
        assert d['memory_type'] == "long_term"
        assert d['importance'] == 3
        restored = MemoryItem.from_dict(d)
        assert restored.id == sample_memory_item.id
        assert restored.content == sample_memory_item.content

    def test_access_count(self, sample_memory_item):
        assert sample_memory_item.access_count == 0
        sample_memory_item.access_count += 1
        assert sample_memory_item.access_count == 1


# ============================================================================
# SimpleEmbedder 测试
# ============================================================================

class TestSimpleEmbedder:

    def test_embed_dimensions(self):
        embedder = SimpleEmbedder(dim=128)
        vec = embedder.embed("hello world")
        assert len(vec) == 128

    def test_embed_deterministic(self):
        embedder = SimpleEmbedder()
        assert embedder.embed("test text") == embedder.embed("test text")

    def test_embed_different_texts(self):
        embedder = SimpleEmbedder()
        assert embedder.embed("hello") != embedder.embed("world")

    def test_similarity_same_text(self):
        embedder = SimpleEmbedder()
        vec = embedder.embed("test")
        assert embedder.similarity(vec, vec) == pytest.approx(1.0, abs=0.01)

    def test_similarity_different_texts(self):
        embedder = SimpleEmbedder()
        vec1 = embedder.embed("hello world")
        vec2 = embedder.embed("completely different")
        assert embedder.similarity(vec1, vec2) < 1.0


# ============================================================================
# MemoryStore 测试
# ============================================================================

class TestMemoryStore:

    def test_save_and_load(self, temp_dir):
        store = MemoryStore(temp_dir)
        item = MemoryItem(id="s1", content="test", memory_type=MemoryType.LONG_TERM)
        store.save(item)
        loaded = store.load("s1")
        assert loaded is not None
        assert loaded.content == "test"

    def test_load_nonexistent(self, temp_dir):
        assert MemoryStore(temp_dir).load("nope") is None

    def test_delete(self, temp_dir):
        store = MemoryStore(temp_dir)
        store.save(MemoryItem(id="d1", content="x", memory_type=MemoryType.SHORT_TERM))
        store.delete("d1")
        assert store.load("d1") is None

    def test_all_ids_excludes_private_files(self, temp_dir):
        store = MemoryStore(temp_dir)
        store.save(MemoryItem(id="r1", content="real", memory_type=MemoryType.LONG_TERM))
        with open(os.path.join(temp_dir, "_profile.json"), 'w') as f:
            json.dump({}, f)
        with open(os.path.join(temp_dir, "_stats.json"), 'w') as f:
            json.dump({}, f)
        ids = store.all_ids()
        assert "r1" in ids
        assert "_profile" not in ids
        assert "_stats" not in ids

    def test_all_items(self, temp_dir):
        store = MemoryStore(temp_dir)
        for i in range(3):
            store.save(MemoryItem(id=f"i{i}", content=f"c{i}", memory_type=MemoryType.LONG_TERM))
        assert len(store.all_items()) == 3


# ============================================================================
# MemoryManager 测试
# ============================================================================

class TestMemoryManager:

    def test_remember_and_recall(self, memory_manager):
        memory_manager.remember(
            "Python的GIL限制了多线程性能",
            memory_type=MemoryType.LONG_TERM,
            tags=["python", "performance"]
        )
        results = memory_manager.recall("Python GIL")
        assert len(results) > 0
        # recall返回(similarity, MemoryItem)元组
        sim, item = results[0]
        assert "GIL" in item.content

    def test_remember_with_tags(self, memory_manager):
        memory_manager.remember("Docker容器化部署", tags=["docker", "devops"])
        results = memory_manager.recall_by_tags(["docker"])
        assert len(results) > 0

    def test_recall_by_tags_match_all(self, memory_manager):
        memory_manager.remember("K8s集群管理", tags=["k8s", "devops"])
        memory_manager.remember("Docker容器", tags=["docker", "devops"])
        results = memory_manager.recall_by_tags(["k8s", "devops"], match_all=True)
        assert len(results) == 1
        assert "K8s" in results[0].content

    def test_user_profile_update(self, memory_manager):
        memory_manager.update_profile("preferences", "language", "Python")
        profile = memory_manager._load_profile()
        # profile存储的是嵌套dict: {key: {value, confidence, updated_at}}
        assert profile.preferences.get("language", {}).get("value") == "Python"

    def test_consolidate(self, memory_manager):
        for i in range(10):
            memory_manager.remember(
                f"短期记忆 {i}",
                memory_type=MemoryType.SHORT_TERM,
                importance=MemoryImportance.LOW
            )
        memory_manager.consolidate()  # 不崩溃即可

    def test_recall_lessons(self, memory_manager):
        memory_manager.remember(
            "不要在循环中创建大列表",
            memory_type=MemoryType.LESSON,
            importance=MemoryImportance.HIGH,
            tags=["performance"]
        )
        lessons = memory_manager.recall_lessons("性能优化")
        assert len(lessons) > 0

    def test_multiple_recalls_update_access(self, memory_manager):
        memory_manager.remember("机器学习基础", tags=["ml"])
        for _ in range(3):
            memory_manager.recall("机器学习")
        results = memory_manager.recall("机器学习")
        if results:
            sim, item = results[0]
            assert item.access_count >= 1


# ============================================================================
# KnowledgeGraphEngine 测试
# ============================================================================

class TestKnowledgeGraph:

    @pytest.fixture
    def kg(self, temp_dir):
        from core.knowledge_graph import KnowledgeGraphEngine, Entity, EntityType
        engine = KnowledgeGraphEngine(temp_dir)
        return engine, Entity, EntityType

    def test_add_and_find_entity(self, kg):
        engine, Entity, EntityType = kg
        entity = Entity(
            id="e1", name="Python",
            entity_type=EntityType.LANGUAGE,
            properties={"paradigm": "multi"}
        )
        # add_entity is on the store sub-component
        eid = engine.store.add_entity(entity)
        assert eid is not None
        found = engine.store.find_entity_by_name("Python")
        assert found is not None
        assert found.name == "Python"

    def test_get_stats(self, kg):
        engine, Entity, EntityType = kg
        entity = Entity(id="e1", name="Test", entity_type=EntityType.OTHER)
        engine.store.add_entity(entity)
        stats = engine.get_graph_stats()
        assert isinstance(stats, dict)


# ============================================================================
# MetacognitionEngine 测试
# ============================================================================

class TestMetacognition:

    @pytest.fixture
    def meta(self, temp_dir):
        from core.metacognition import MetacognitionEngine
        return MetacognitionEngine(temp_dir)

    def test_pre_answer_assessment(self, meta):
        result = meta.pre_answer_assessment("如何用Python读取文件?")
        assert isinstance(result, dict)
        assert 'confidence' in result or 'domain' in result

    def test_gap_detector(self, meta):
        assert hasattr(meta, 'gap_detector')
        assert hasattr(meta.gap_detector, 'get_unfilled_gaps')

    def test_capability_manager(self, meta):
        assert hasattr(meta, 'capability_mgr')


# ============================================================================
# SelfEvolvingAI 集成测试
# ============================================================================

class TestSelfEvolvingAI:

    @pytest.fixture
    def ai(self, temp_dir):
        from core.evolution_loop import SelfEvolvingAI
        return SelfEvolvingAI(temp_dir)

    def test_initialization(self, ai):
        assert ai.state is not None
        assert ai.state.version == "4.0.0"
        assert ai.state.modules_loaded > 0

    def test_process_input(self, ai):
        result = ai.process("你好")
        assert 'answer' in result or 'response' in result
        assert 'confidence' in result
        answer = result.get('response', result.get('answer', ''))
        assert len(answer) > 0

    def test_evolve(self, ai):
        result = ai.evolve("manual")
        assert 'improvements' in result
        assert 'duration' in result
        assert result['duration'] > 0

    def test_generate_report(self, ai):
        report = ai.generate_evolution_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_get_module_stats(self, ai):
        stats = ai.get_all_module_stats()
        assert isinstance(stats, dict)
        assert len(stats) > 0

    def test_learn_from_knowledge(self, ai):
        result = ai.learn_from_knowledge("Python是一种解释型编程语言", source="test")
        assert isinstance(result, dict)

    def test_multiple_interactions(self, ai):
        for i in range(3):
            result = ai.process(f"测试消息 {i}")
            assert 'answer' in result or 'response' in result

    def test_state_persistence(self, temp_dir):
        from core.evolution_loop import SelfEvolvingAI
        ai1 = SelfEvolvingAI(temp_dir)
        ai1.process("测试持久化")
        ai1._save_state()
        ai2 = SelfEvolvingAI(temp_dir)
        assert ai2.state.version == ai1.state.version


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
