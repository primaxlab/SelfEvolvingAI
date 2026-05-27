"""特征工程 - 特征提取、特征选择、特征变换"""

import json
import os
import time
import math
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict


class FeatureType(Enum):
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    TEXT = "text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    VECTOR = "vector"


class TransformMethod(Enum):
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    LOG = "log"
    ENCODE = "encode"
    BIN = "bin"
    POLYNOMIAL = "polynomial"
    ONEHOT = "onehot"


@dataclass
class Feature:
    feature_id: str
    name: str
    feature_type: str = "numerical"
    description: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.0
    created_at: float = 0.0


@dataclass
class FeatureSet:
    set_id: str
    name: str
    features: List[str] = field(default_factory=list)
    created_at: float = 0.0
    sample_count: int = 0


@dataclass
class Transform:
    transform_id: str
    feature_name: str
    method: str = "normalize"
    params: Dict[str, Any] = field(default_factory=dict)
    fitted: bool = False


class FeatureEngineeringEngine:
    """特征工程引擎"""

    def __init__(self, storage_dir: str = "data/features"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.features: Dict[str, Feature] = {}
        self.feature_sets: Dict[str, FeatureSet] = {}
        self.transforms: Dict[str, Transform] = {}
        self.feature_values: Dict[str, List[Any]] = defaultdict(list)

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "feature_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("features", {}).items():
                    self.features[k] = Feature(**v)
                for k, v in data.get("feature_sets", {}).items():
                    self.feature_sets[k] = FeatureSet(**v)
                for k, v in data.get("transforms", {}).items():
                    self.transforms[k] = Transform(**v)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "feature_data.json")
        data = {
            "features": {k: asdict(v) for k, v in self.features.items()},
            "feature_sets": {k: asdict(v) for k, v in self.feature_sets.items()},
            "transforms": {k: asdict(v) for k, v in self.transforms.items()},
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register_feature(self, name: str, feature_type: str = "numerical",
                         description: str = "") -> str:
        """注册特征"""
        feature_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        feature = Feature(
            feature_id=feature_id, name=name,
            feature_type=feature_type, description=description,
            created_at=time.time(),
        )
        self.features[name] = feature
        self._save()
        return feature_id

    def ingest_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """摄入数据并计算统计"""
        if not data:
            return {"count": 0}

        for row in data:
            for key, value in row.items():
                if key not in self.features:
                    self.register_feature(key, self._infer_type(value))
                self.feature_values[key].append(value)

        # 计算统计
        stats = {}
        for name, values in self.feature_values.items():
            if name in self.features:
                feature = self.features[name]
                feature.stats = self._compute_stats(values, feature.feature_type)
                stats[name] = feature.stats

        self._save()
        return {"count": len(data), "features": len(stats)}

    def _infer_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "numerical"
        if isinstance(value, str):
            return "text"
        return "text"

    def _compute_stats(self, values: List[Any], feature_type: str) -> Dict[str, Any]:
        """计算特征统计"""
        if feature_type == "numerical":
            nums = [v for v in values if isinstance(v, (int, float))]
            if not nums:
                return {}
            return {
                "count": len(nums),
                "mean": sum(nums) / len(nums),
                "min": min(nums),
                "max": max(nums),
                "std": math.sqrt(sum((x - sum(nums)/len(nums))**2 for x in nums) / len(nums)) if len(nums) > 1 else 0,
            }
        elif feature_type == "categorical":
            counts = defaultdict(int)
            for v in values:
                counts[str(v)] += 1
            return {
                "count": len(values),
                "unique": len(counts),
                "top": sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5],
            }
        return {"count": len(values)}

    def create_feature_set(self, name: str, feature_names: List[str]) -> str:
        """创建特征集"""
        set_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        feature_set = FeatureSet(
            set_id=set_id, name=name,
            features=feature_names,
            created_at=time.time(),
        )
        self.feature_sets[set_id] = feature_set
        self._save()
        return set_id

    def normalize(self, feature_name: str, method: str = "minmax") -> Dict[str, Any]:
        """归一化/标准化"""
        values = self.feature_values.get(feature_name, [])
        nums = [v for v in values if isinstance(v, (int, float))]
        if not nums:
            return {"error": "无数值数据"}

        if method == "minmax":
            min_val, max_val = min(nums), max(nums)
            range_val = max_val - min_val
            if range_val == 0:
                normalized = [0.5] * len(nums)
            else:
                normalized = [(x - min_val) / range_val for x in nums]
            params = {"min": min_val, "max": max_val, "method": "minmax"}
        elif method == "zscore":
            mean = sum(nums) / len(nums)
            std = math.sqrt(sum((x - mean)**2 for x in nums) / len(nums))
            if std == 0:
                normalized = [0] * len(nums)
            else:
                normalized = [(x - mean) / std for x in nums]
            params = {"mean": mean, "std": std, "method": "zscore"}
        else:
            return {"error": f"未知方法: {method}"}

        transform_id = hashlib.md5(f"{feature_name}_{method}_{time.time()}".encode()).hexdigest()[:12]
        self.transforms[transform_id] = Transform(
            transform_id=transform_id,
            feature_name=feature_name,
            method=method,
            params=params,
            fitted=True,
        )
        self._save()

        return {
            "transform_id": transform_id,
            "method": method,
            "params": params,
            "output_sample": normalized[:10],
        }

    def one_hot_encode(self, feature_name: str) -> Dict[str, Any]:
        """独热编码"""
        values = self.feature_values.get(feature_name, [])
        unique_values = list(set(str(v) for v in values))

        encoded = []
        for v in values:
            row = {f"{feature_name}_{uv}": (1 if str(v) == uv else 0) for uv in unique_values}
            encoded.append(row)

        return {
            "categories": unique_values,
            "encoded_sample": encoded[:5],
            "new_features": len(unique_values),
        }

    def bin_feature(self, feature_name: str, bins: int = 5) -> Dict[str, Any]:
        """分箱"""
        values = self.feature_values.get(feature_name, [])
        nums = [v for v in values if isinstance(v, (int, float))]
        if not nums:
            return {"error": "无数值数据"}

        min_val, max_val = min(nums), max(nums)
        bin_width = (max_val - min_val) / bins if max_val != min_val else 1

        binned = []
        for v in nums:
            bin_idx = min(int((v - min_val) / bin_width), bins - 1)
            binned.append(bin_idx)

        return {
            "bins": bins,
            "range": [min_val, max_val],
            "bin_width": bin_width,
            "binned_sample": binned[:10],
        }

    def compute_correlation(self, feature1: str, feature2: str) -> float:
        """计算相关系数"""
        vals1 = [v for v in self.feature_values.get(feature1, []) if isinstance(v, (int, float))]
        vals2 = [v for v in self.feature_values.get(feature2, []) if isinstance(v, (int, float))]

        n = min(len(vals1), len(vals2))
        if n < 2:
            return 0.0

        vals1, vals2 = vals1[:n], vals2[:n]
        mean1 = sum(vals1) / n
        mean2 = sum(vals2) / n

        cov = sum((a - mean1) * (b - mean2) for a, b in zip(vals1, vals2)) / n
        std1 = math.sqrt(sum((a - mean1)**2 for a in vals1) / n)
        std2 = math.sqrt(sum((b - mean2)**2 for b in vals2) / n)

        if std1 == 0 or std2 == 0:
            return 0.0
        return cov / (std1 * std2)

    def select_features(self, target: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """特征选择(基于相关性)"""
        correlations = []
        for name in self.features:
            if name == target:
                continue
            corr = self.compute_correlation(name, target)
            correlations.append({
                "feature": name,
                "correlation": abs(corr),
                "direction": "positive" if corr > 0 else "negative",
            })

        correlations.sort(key=lambda x: x["correlation"], reverse=True)
        return correlations[:top_k]

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        type_counts = defaultdict(int)
        for f in self.features.values():
            type_counts[f.feature_type] += 1

        return {
            "total_features": len(self.features),
            "feature_sets": len(self.feature_sets),
            "transforms_applied": len(self.transforms),
            "type_distribution": dict(type_counts),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "features_count": len(self.features),
            "feature_sets_count": len(self.feature_sets),
            "transforms_count": len(self.transforms),
        }


if __name__ == "__main__":
    print("=== 特征工程测试 ===")
    engine = FeatureEngineeringEngine()

    # 摄入数据
    data = [
        {"age": 25, "salary": 5000, "city": "Beijing", "score": 85},
        {"age": 30, "salary": 8000, "city": "Shanghai", "score": 90},
        {"age": 35, "salary": 12000, "city": "Beijing", "score": 75},
        {"age": 28, "salary": 6000, "city": "Guangzhou", "score": 88},
        {"age": 40, "salary": 15000, "city": "Shanghai", "score": 92},
    ]
    result = engine.ingest_data(data)
    print(f"摄入: {result}")

    # 统计
    print(f"\nage统计: {engine.features['age'].stats}")
    print(f"salary统计: {engine.features['salary'].stats}")

    # 归一化
    norm = engine.normalize("salary", "minmax")
    print(f"\n归一化: {norm['method']}, 样本: {norm['output_sample'][:3]}")

    # 独热编码
    ohe = engine.one_hot_encode("city")
    print(f"\n独热编码: {ohe['categories']}")

    # 相关性
    corr = engine.compute_correlation("age", "salary")
    print(f"\nage-salary相关性: {corr:.4f}")

    # 特征选择
    selected = engine.select_features("score", top_k=3)
    print(f"\n特征选择(目标=score):")
    for s in selected:
        print(f"  {s['feature']}: {s['correlation']:.4f} ({s['direction']})")

    report = engine.generate_report()
    print(f"\n特征工程报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
