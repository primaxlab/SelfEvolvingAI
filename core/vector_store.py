"""向量数据库 - 向量存储、相似度检索、索引管理"""

import json
import os
import time
import hashlib
import math
import random
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict


class DistanceMetric(Enum):
    """距离度量"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class IndexType(Enum):
    """索引类型"""
    FLAT = "flat"       # 暴力搜索
    IVF = "ivf"         # 倒排索引
    HNSW = "hnsw"       # 层次化可导航小世界图
    LSH = "lsh"         # 局部敏感哈希


@dataclass
class Vector:
    """向量"""
    vector_id: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    collection: str = "default"
    created_at: float = 0.0


@dataclass
class Collection:
    """集合"""
    collection_id: str
    name: str
    dimension: int = 0
    distance_metric: str = "cosine"
    index_type: str = "flat"
    vector_count: int = 0
    created_at: float = 0.0


@dataclass
class SearchResult:
    """搜索结果"""
    vector_id: str
    score: float
    distance: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStoreEngine:
    """向量数据库引擎"""

    def __init__(self, storage_dir: str = "data/vector_store"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.collections: Dict[str, Collection] = {}
        self.vectors: Dict[str, Dict[str, Vector]] = defaultdict(dict)  # collection -> {id -> Vector}

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "vector_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("collections", {}).items():
                    self.collections[k] = Collection(**v)
                for coll_name, vectors in data.get("vectors", {}).items():
                    for vid, vdata in vectors.items():
                        self.vectors[coll_name][vid] = Vector(**vdata)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "vector_data.json")
        data = {
            "collections": {k: asdict(v) for k, v in self.collections.items()},
            "vectors": {
                coll: {vid: asdict(v) for vid, v in vectors.items()}
                for coll, vectors in self.vectors.items()
            }
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_collection(self, name: str, dimension: int,
                          distance_metric: str = "cosine",
                          index_type: str = "flat") -> str:
        """创建集合"""
        collection_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        collection = Collection(
            collection_id=collection_id,
            name=name,
            dimension=dimension,
            distance_metric=distance_metric,
            index_type=index_type,
            created_at=time.time(),
        )
        self.collections[name] = collection
        self._save()
        return collection_id

    def insert(self, collection: str, embedding: List[float],
               vector_id: str = "", metadata: Dict[str, Any] = None) -> str:
        """插入向量"""
        if collection not in self.collections:
            self.create_collection(collection, len(embedding))

        coll = self.collections[collection]
        if len(embedding) != coll.dimension:
            return ""

        if not vector_id:
            vector_id = hashlib.md5(f"{collection}_{time.time()}_{random.random()}".encode()).hexdigest()[:12]

        vector = Vector(
            vector_id=vector_id,
            embedding=embedding,
            metadata=metadata or {},
            collection=collection,
            created_at=time.time(),
        )
        self.vectors[collection][vector_id] = vector
        coll.vector_count = len(self.vectors[collection])
        self._save()
        return vector_id

    def insert_batch(self, collection: str, embeddings: List[List[float]],
                     ids: List[str] = None, metadatas: List[Dict] = None) -> List[str]:
        """批量插入"""
        if collection not in self.collections and embeddings:
            self.create_collection(collection, len(embeddings[0]))

        vector_ids = []
        for i, embedding in enumerate(embeddings):
            vid = ids[i] if ids else ""
            meta = metadatas[i] if metadatas else {}
            result = self.insert(collection, embedding, vid, meta)
            if result:
                vector_ids.append(result)
        return vector_ids

    def search(self, collection: str, query_embedding: List[float],
               top_k: int = 10, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """相似度搜索"""
        if collection not in self.collections:
            return []

        coll = self.collections[collection]
        if len(query_embedding) != coll.dimension:
            return []

        vectors = self.vectors.get(collection, {})
        if not vectors:
            return []

        # 计算距离
        results = []
        for vid, vector in vectors.items():
            # 元数据过滤
            if filter_metadata:
                match = all(vector.metadata.get(k) == v for k, v in filter_metadata.items())
                if not match:
                    continue

            distance = self._compute_distance(query_embedding, vector.embedding, coll.distance_metric)
            score = self._distance_to_score(distance, coll.distance_metric)
            results.append(SearchResult(
                vector_id=vid,
                score=score,
                distance=distance,
                metadata=vector.metadata,
            ))

        # 排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _compute_distance(self, a: List[float], b: List[float], metric: str) -> float:
        """计算距离"""
        if metric == DistanceMetric.COSINE.value:
            return self._cosine_distance(a, b)
        elif metric == DistanceMetric.EUCLIDEAN.value:
            return self._euclidean_distance(a, b)
        elif metric == DistanceMetric.DOT_PRODUCT.value:
            return self._dot_product(a, b)
        elif metric == DistanceMetric.MANHATTAN.value:
            return self._manhattan_distance(a, b)
        return 0.0

    def _cosine_distance(self, a: List[float], b: List[float]) -> float:
        """余弦距离"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 1.0
        return 1.0 - (dot / (norm_a * norm_b))

    def _euclidean_distance(self, a: List[float], b: List[float]) -> float:
        """欧氏距离"""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _dot_product(self, a: List[float], b: List[float]) -> float:
        """点积"""
        return sum(x * y for x, y in zip(a, b))

    def _manhattan_distance(self, a: List[float], b: List[float]) -> float:
        """曼哈顿距离"""
        return sum(abs(x - y) for x, y in zip(a, b))

    def _distance_to_score(self, distance: float, metric: str) -> float:
        """距离转相似度分数"""
        if metric == DistanceMetric.COSINE.value:
            return 1.0 - distance
        elif metric == DistanceMetric.EUCLIDEAN.value:
            return 1.0 / (1.0 + distance)
        elif metric == DistanceMetric.DOT_PRODUCT.value:
            return distance
        elif metric == DistanceMetric.MANHATTAN.value:
            return 1.0 / (1.0 + distance)
        return 0.0

    def get_vector(self, collection: str, vector_id: str) -> Optional[Dict[str, Any]]:
        """获取向量"""
        vector = self.vectors.get(collection, {}).get(vector_id)
        if vector:
            return asdict(vector)
        return None

    def delete_vector(self, collection: str, vector_id: str) -> bool:
        """删除向量"""
        if collection in self.vectors and vector_id in self.vectors[collection]:
            del self.vectors[collection][vector_id]
            if collection in self.collections:
                self.collections[collection].vector_count = len(self.vectors[collection])
            self._save()
            return True
        return False

    def delete_collection(self, name: str) -> bool:
        """删除集合"""
        if name in self.collections:
            del self.collections[name]
            self.vectors.pop(name, None)
            self._save()
            return True
        return False

    def generate_random_embedding(self, dimension: int) -> List[float]:
        """生成随机嵌入(测试用)"""
        return [random.uniform(-1, 1) for _ in range(dimension)]

    def text_to_simple_embedding(self, text: str, dimension: int = 128) -> List[float]:
        """文本转简单嵌入(基于哈希的伪嵌入)"""
        hash_val = hashlib.md5(text.encode()).hexdigest()
        embedding = []
        for i in range(dimension):
            byte_idx = (i * 2) % len(hash_val)
            val = int(hash_val[byte_idx:byte_idx+2], 16) / 255.0 * 2 - 1
            embedding.append(val)
        # 归一化
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding

    def get_collection_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取集合信息"""
        if name not in self.collections:
            return None
        coll = self.collections[name]
        return {
            "name": coll.name,
            "dimension": coll.dimension,
            "distance_metric": coll.distance_metric,
            "index_type": coll.index_type,
            "vector_count": coll.vector_count,
            "created_at": coll.created_at,
        }

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        total_vectors = sum(len(v) for v in self.vectors.values())

        return {
            "total_collections": len(self.collections),
            "total_vectors": total_vectors,
            "collections": {
                name: {
                    "vectors": len(self.vectors.get(name, {})),
                    "dimension": coll.dimension,
                    "metric": coll.distance_metric,
                }
                for name, coll in self.collections.items()
            }
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "collections_count": len(self.collections),
            "total_vectors": sum(len(v) for v in self.vectors.values()),
        }


if __name__ == "__main__":
    print("=== 向量数据库测试 ===")
    engine = VectorStoreEngine()

    # 创建集合
    engine.create_collection("documents", dimension=8, distance_metric="cosine")
    print("创建集合: documents (dim=8)")

    # 插入向量
    vectors_data = [
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
        [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ]
    metadata_list = [
        {"text": "Python编程", "category": "programming"},
        {"text": "机器学习", "category": "ml"},
        {"text": "Python机器学习", "category": "ml"},
        {"text": "烹饪美食", "category": "food"},
        {"text": "Python教程", "category": "programming"},
    ]

    ids = engine.insert_batch("documents", vectors_data, metadatas=metadata_list)
    print(f"插入 {len(ids)} 个向量")

    # 搜索
    query = [0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    results = engine.search("documents", query, top_k=3)
    print(f"\n搜索结果 (查询: Python相关):")
    for r in results:
        print(f"  {r.vector_id}: score={r.score:.4f}, text={r.metadata.get('text', '')}")

    # 带过滤的搜索
    results_filtered = engine.search("documents", query, top_k=3,
                                      filter_metadata={"category": "programming"})
    print(f"\n过滤搜索 (category=programming):")
    for r in results_filtered:
        print(f"  {r.vector_id}: score={r.score:.4f}, text={r.metadata.get('text', '')}")

    # 文本嵌入
    embedding = engine.text_to_simple_embedding("Hello World", dimension=8)
    print(f"\n文本嵌入: {[round(x, 3) for x in embedding]}")

    # 报告
    report = engine.generate_report()
    print(f"\n向量数据库报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
