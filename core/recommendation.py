"""推荐引擎 - 协同过滤、内容推荐、个性化排序"""

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


class RecommendStrategy(Enum):
    COLLABORATIVE = "collaborative"      # 协同过滤
    CONTENT_BASED = "content_based"      # 基于内容
    POPULARITY = "popularity"            # 热门推荐
    HYBRID = "hybrid"                    # 混合推荐


@dataclass
class UserProfile:
    user_id: str
    preferences: Dict[str, float] = field(default_factory=dict)
    interaction_history: List[str] = field(default_factory=list)
    ratings: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class Item:
    item_id: str
    name: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    features: Dict[str, Any] = field(default_factory=dict)
    popularity_score: float = 0.0
    created_at: float = 0.0


@dataclass
class Recommendation:
    item_id: str
    score: float
    reason: str = ""
    strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self, storage_dir: str = "data/recommendation"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.users: Dict[str, UserProfile] = {}
        self.items: Dict[str, Item] = {}
        self.interactions: List[Dict[str, Any]] = []
        self.item_similarities: Dict[str, Dict[str, float]] = defaultdict(dict)

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "rec_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("users", {}).items():
                    self.users[k] = UserProfile(**v)
                for k, v in data.get("items", {}).items():
                    self.items[k] = Item(**v)
                self.interactions = data.get("interactions", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "rec_data.json")
        data = {
            "users": {k: asdict(v) for k, v in self.users.items()},
            "items": {k: asdict(v) for k, v in self.items.items()},
            "interactions": self.interactions[-10000:],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_user(self, user_id: str, tags: List[str] = None) -> str:
        """添加用户"""
        self.users[user_id] = UserProfile(
            user_id=user_id, tags=tags or [],
            created_at=time.time(), updated_at=time.time(),
        )
        self._save()
        return user_id

    def add_item(self, item_id: str, name: str, category: str = "",
                 tags: List[str] = None, features: Dict[str, Any] = None) -> str:
        """添加物品"""
        self.items[item_id] = Item(
            item_id=item_id, name=name, category=category,
            tags=tags or [], features=features or {},
            created_at=time.time(),
        )
        self._save()
        return item_id

    def record_interaction(self, user_id: str, item_id: str,
                           interaction_type: str = "view",
                           rating: float = 0, metadata: Dict[str, Any] = None):
        """记录交互"""
        interaction = {
            "user_id": user_id,
            "item_id": item_id,
            "type": interaction_type,
            "rating": rating,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self.interactions.append(interaction)

        # 更新用户
        if user_id in self.users:
            user = self.users[user_id]
            if item_id not in user.interaction_history:
                user.interaction_history.append(item_id)
            if rating > 0:
                user.ratings[item_id] = rating
            user.updated_at = time.time()

        # 更新物品热度
        if item_id in self.items:
            self.items[item_id].popularity_score += 1

        self._save()

    def recommend(self, user_id: str, strategy: str = "hybrid",
                  top_k: int = 10, exclude_interacted: bool = True) -> List[Recommendation]:
        """生成推荐"""
        if user_id not in self.users:
            return self._recommend_popular(top_k)

        user = self.users[user_id]
        recommendations = []

        if strategy == RecommendStrategy.COLLABORATIVE.value:
            recommendations = self._collaborative_filter(user, top_k)
        elif strategy == RecommendStrategy.CONTENT_BASED.value:
            recommendations = self._content_based(user, top_k)
        elif strategy == RecommendStrategy.POPULARITY.value:
            recommendations = self._recommend_popular(top_k)
        elif strategy == RecommendStrategy.HYBRID.value:
            collab = self._collaborative_filter(user, top_k)
            content = self._content_based(user, top_k)
            popular = self._recommend_popular(top_k)
            recommendations = self._merge_recommendations(collab, content, popular, top_k)

        # 排除已交互
        if exclude_interacted:
            recommendations = [
                r for r in recommendations
                if r.item_id not in user.interaction_history
            ]

        return recommendations[:top_k]

    def _collaborative_filter(self, user: UserProfile, top_k: int) -> List[Recommendation]:
        """协同过滤"""
        scores: Dict[str, float] = defaultdict(float)

        # 找相似用户
        for other_user in self.users.values():
            if other_user.user_id == user.user_id:
                continue
            similarity = self._user_similarity(user, other_user)
            if similarity <= 0:
                continue

            for item_id, rating in other_user.ratings.items():
                if item_id not in user.ratings:
                    scores[item_id] += similarity * rating

        recommendations = [
            Recommendation(
                item_id=item_id, score=score,
                reason="相似用户喜欢",
                strategy="collaborative",
            )
            for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]
        return recommendations[:top_k]

    def _user_similarity(self, user1: UserProfile, user2: UserProfile) -> float:
        """用户相似度"""
        common_items = set(user1.ratings.keys()) & set(user2.ratings.keys())
        if len(common_items) < 2:
            return 0.0

        ratings1 = [user1.ratings[i] for i in common_items]
        ratings2 = [user2.ratings[i] for i in common_items]

        return self._pearson_correlation(ratings1, ratings2)

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """皮尔逊相关系数"""
        n = len(x)
        if n == 0:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
        denom_x = math.sqrt(sum((a - mean_x) ** 2 for a in x))
        denom_y = math.sqrt(sum((b - mean_y) ** 2 for b in y))

        if denom_x == 0 or denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    def _content_based(self, user: UserProfile, top_k: int) -> List[Recommendation]:
        """基于内容推荐"""
        # 构建用户偏好画像
        tag_scores: Dict[str, float] = defaultdict(float)
        category_scores: Dict[str, float] = defaultdict(float)

        for item_id in user.interaction_history:
            if item_id in self.items:
                item = self.items[item_id]
                weight = user.ratings.get(item_id, 1.0)
                for tag in item.tags:
                    tag_scores[tag] += weight
                if item.category:
                    category_scores[item.category] += weight

        # 打分
        scores: Dict[str, float] = defaultdict(float)
        for item_id, item in self.items.items():
            for tag in item.tags:
                scores[item_id] += tag_scores.get(tag, 0)
            if item.category:
                scores[item_id] += category_scores.get(item.category, 0)

        recommendations = [
            Recommendation(
                item_id=item_id, score=score,
                reason="内容匹配",
                strategy="content_based",
            )
            for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]
        return recommendations[:top_k]

    def _recommend_popular(self, top_k: int) -> List[Recommendation]:
        """热门推荐"""
        sorted_items = sorted(
            self.items.values(),
            key=lambda x: x.popularity_score,
            reverse=True,
        )
        return [
            Recommendation(
                item_id=item.item_id,
                score=item.popularity_score,
                reason="热门推荐",
                strategy="popularity",
            )
            for item in sorted_items[:top_k]
        ]

    def _merge_recommendations(self, *rec_lists: List[Recommendation],
                               top_k: int) -> List[Recommendation]:
        """合并多种推荐结果"""
        scores: Dict[str, float] = defaultdict(float)
        reasons: Dict[str, str] = {}
        strategies: Dict[str, str] = {}

        weights = [0.5, 0.3, 0.2]  # 协同 > 内容 > 热门

        for i, rec_list in enumerate(rec_lists):
            weight = weights[i] if i < len(weights) else 0.1
            for rec in rec_list:
                scores[rec.item_id] += rec.score * weight
                if rec.item_id not in reasons:
                    reasons[rec.item_id] = rec.reason
                    strategies[rec.item_id] = rec.strategy

        recommendations = [
            Recommendation(
                item_id=item_id, score=score,
                reason=reasons.get(item_id, ""),
                strategy="hybrid",
            )
            for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]
        return recommendations[:top_k]

    def similar_items(self, item_id: str, top_k: int = 5) -> List[Recommendation]:
        """相似物品"""
        if item_id not in self.items:
            return []

        target = self.items[item_id]
        scores = []

        for other_id, other in self.items.items():
            if other_id == item_id:
                continue
            sim = self._item_similarity(target, other)
            if sim > 0:
                scores.append(Recommendation(
                    item_id=other_id, score=sim,
                    reason="相似物品", strategy="item_similarity",
                ))

        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:top_k]

    def _item_similarity(self, item1: Item, item2: Item) -> float:
        """物品相似度"""
        score = 0.0
        if item1.category and item1.category == item2.category:
            score += 0.3
        common_tags = set(item1.tags) & set(item2.tags)
        if item1.tags and item2.tags:
            score += 0.7 * len(common_tags) / max(len(set(item1.tags) | set(item2.tags)), 1)
        return score

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        return {
            "total_users": len(self.users),
            "total_items": len(self.items),
            "total_interactions": len(self.interactions),
            "avg_items_per_user": sum(len(u.interaction_history) for u in self.users.values()) / max(len(self.users), 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "users_count": len(self.users),
            "items_count": len(self.items),
            "interactions_count": len(self.interactions),
        }


if __name__ == "__main__":
    print("=== 推荐引擎测试 ===")
    engine = RecommendationEngine()

    # 添加物品
    items = [
        ("py1", "Python入门", "programming", ["python", "入门"]),
        ("py2", "Python高级编程", "programming", ["python", "高级"]),
        ("ml1", "机器学习实战", "ml", ["机器学习", "python"]),
        ("dl1", "深度学习基础", "ml", ["深度学习", "python"]),
        ("web1", "Web开发指南", "web", ["javascript", "web"]),
        ("cook1", "烹饪入门", "food", ["烹饪", "美食"]),
    ]
    for item_id, name, cat, tags in items:
        engine.add_item(item_id, name, cat, tags)

    # 添加用户
    engine.add_user("user_1", tags=["编程", "AI"])
    engine.add_user("user_2", tags=["编程", "Web"])

    # 记录交互
    engine.record_interaction("user_1", "py1", "rate", 5.0)
    engine.record_interaction("user_1", "ml1", "rate", 4.5)
    engine.record_interaction("user_2", "py1", "rate", 4.0)
    engine.record_interaction("user_2", "web1", "rate", 5.0)

    # 推荐
    for strategy in ["collaborative", "content_based", "popularity", "hybrid"]:
        recs = engine.recommend("user_1", strategy=strategy, top_k=3)
        print(f"\n[{strategy}] 推荐给user_1:")
        for r in recs:
            print(f"  {r.item_id}: {r.score:.2f} ({r.reason})")

    # 相似物品
    similar = engine.similar_items("py1", top_k=3)
    print(f"\n与Python入门相似:")
    for s in similar:
        print(f"  {s.item_id}: {s.score:.2f}")

    report = engine.generate_report()
    print(f"\n推荐报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
