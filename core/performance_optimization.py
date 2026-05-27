"""性能优化系统 - 代码生成、性能分析、瓶颈检测、自动优化"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics


class MetricType(Enum):
    """性能指标类型"""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


class BottleneckType(Enum):
    """瓶颈类型"""
    CPU_BOUND = "cpu_bound"
    MEMORY_BOUND = "memory_bound"
    IO_BOUND = "io_bound"
    NETWORK_BOUND = "network_bound"
    ALGORITHM = "algorithm"
    CONCURRENCY = "concurrency"
    DATA_SIZE = "data_size"
    UNKNOWN = "unknown"


class OptimizationStrategy(Enum):
    """优化策略"""
    CACHING = "caching"
    BATCHING = "batching"
    PARALLELIZATION = "parallelization"
    LAZY_LOADING = "lazy_loading"
    DATA_STRUCTURE = "data_structure"
    ALGORITHM = "algorithm"
    MEMORY_POOL = "memory_pool"
    COMPRESSION = "compression"
    INDEXING = "indexing"
    PREFETCHING = "prefetching"


class ProfileLevel(Enum):
    """分析级别"""
    BASIC = "basic"
    DETAILED = "detailed"
    DEEP = "deep"


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_id: str
    metric_type: str
    name: str
    value: float
    unit: str
    timestamp: float
    source: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProfileResult:
    """分析结果"""
    profile_id: str
    target: str
    level: str
    start_time: float
    end_time: float
    duration: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Bottleneck:
    """瓶颈信息"""
    bottleneck_id: str
    bottleneck_type: str
    location: str
    severity: float  # 0.0-1.0
    impact: str
    description: str
    metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class OptimizationRecord:
    """优化记录"""
    optimization_id: str
    strategy: str
    target: str
    before_metrics: Dict[str, float] = field(default_factory=dict)
    after_metrics: Dict[str, float] = field(default_factory=dict)
    improvement: float = 0.0
    applied: bool = False
    timestamp: float = 0.0
    notes: str = ""


@dataclass
class PerformanceBaseline:
    """性能基线"""
    baseline_id: str
    name: str
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0
    is_active: bool = True


class PerformanceOptimizationEngine:
    """性能优化引擎"""

    def __init__(self, storage_dir: str = "data/performance"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.metrics: List[PerformanceMetric] = []
        self.profiles: List[ProfileResult] = []
        self.bottlenecks: List[Bottleneck] = []
        self.optimizations: List[OptimizationRecord] = []
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.metric_history: Dict[str, List[float]] = defaultdict(list)

        self._load()

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "performance_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.metrics = [PerformanceMetric(**m) for m in data.get("metrics", [])]
                self.profiles = [ProfileResult(**p) for p in data.get("profiles", [])]
                self.bottlenecks = [Bottleneck(**b) for b in data.get("bottlenecks", [])]
                self.optimizations = [OptimizationRecord(**o) for o in data.get("optimizations", [])]
                for k, v in data.get("baselines", {}).items():
                    self.baselines[k] = PerformanceBaseline(**v)
                self.metric_history = defaultdict(list, data.get("metric_history", {}))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "performance_data.json")
        data = {
            "metrics": [asdict(m) for m in self.metrics[-10000:]],
            "profiles": [asdict(p) for p in self.profiles[-500:]],
            "bottlenecks": [asdict(b) for b in self.bottlenecks[-1000:]],
            "optimizations": [asdict(o) for o in self.optimizations[-1000:]],
            "baselines": {k: asdict(v) for k, v in self.baselines.items()},
            "metric_history": dict(self.metric_history)
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_metric(self, metric_type: str, name: str, value: float,
                      unit: str = "", source: str = "", tags: Dict[str, str] = None) -> str:
        """记录性能指标"""
        metric_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        metric = PerformanceMetric(
            metric_id=metric_id,
            metric_type=metric_type,
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            source=source,
            tags=tags or {}
        )
        self.metrics.append(metric)
        self.metric_history[name].append(value)
        if len(self.metric_history[name]) > 1000:
            self.metric_history[name] = self.metric_history[name][-1000:]
        self._save()
        return metric_id

    def start_profile(self, target: str, level: str = "basic") -> str:
        """开始性能分析"""
        profile_id = hashlib.md5(f"{target}_{time.time()}".encode()).hexdigest()[:12]
        profile = ProfileResult(
            profile_id=profile_id,
            target=target,
            level=level,
            start_time=time.time(),
            end_time=0.0,
            duration=0.0
        )
        self.profiles.append(profile)
        return profile_id

    def end_profile(self, profile_id: str, metrics: Dict[str, Any] = None) -> ProfileResult:
        """结束性能分析"""
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                profile.end_time = time.time()
                profile.duration = profile.end_time - profile.start_time
                profile.metrics = metrics or {}
                profile.bottlenecks = self._detect_bottlenecks(profile)
                profile.recommendations = self._generate_recommendations(profile)
                self._save()
                return profile
        return None

    def _detect_bottlenecks(self, profile: ProfileResult) -> List[Dict[str, Any]]:
        """检测瓶颈"""
        bottlenecks = []
        metrics = profile.metrics

        if metrics.get("cpu_percent", 0) > 80:
            bottlenecks.append({
                "type": BottleneckType.CPU_BOUND.value,
                "severity": min(metrics["cpu_percent"] / 100, 1.0),
                "description": f"CPU使用率过高: {metrics['cpu_percent']}%"
            })

        if metrics.get("memory_percent", 0) > 80:
            bottlenecks.append({
                "type": BottleneckType.MEMORY_BOUND.value,
                "severity": min(metrics["memory_percent"] / 100, 1.0),
                "description": f"内存使用率过高: {metrics['memory_percent']}%"
            })

        if metrics.get("io_wait", 0) > 30:
            bottlenecks.append({
                "type": BottleneckType.IO_BOUND.value,
                "severity": min(metrics["io_wait"] / 100, 1.0),
                "description": f"IO等待时间过长: {metrics['io_wait']}%"
            })

        if metrics.get("latency_ms", 0) > 1000:
            bottlenecks.append({
                "type": BottleneckType.NETWORK_BOUND.value,
                "severity": min(metrics["latency_ms"] / 5000, 1.0),
                "description": f"网络延迟过高: {metrics['latency_ms']}ms"
            })

        return bottlenecks

    def _generate_recommendations(self, profile: ProfileResult) -> List[str]:
        """生成优化建议"""
        recommendations = []
        for bn in profile.bottlenecks:
            bn_type = bn.get("type", "")
            if bn_type == BottleneckType.CPU_BOUND.value:
                recommendations.append("考虑使用多线程/多进程并行化处理")
                recommendations.append("优化算法复杂度，减少不必要的计算")
                recommendations.append("使用缓存减少重复计算")
            elif bn_type == BottleneckType.MEMORY_BOUND.value:
                recommendations.append("使用生成器替代列表，减少内存占用")
                recommendations.append("实现数据分批处理，避免一次性加载全部数据")
                recommendations.append("使用__slots__减少对象内存开销")
            elif bn_type == BottleneckType.IO_BOUND.value:
                recommendations.append("使用异步IO减少等待时间")
                recommendations.append("实现数据预取机制")
                recommendations.append("使用内存映射文件(mmap)处理大文件")
            elif bn_type == BottleneckType.NETWORK_BOUND.value:
                recommendations.append("实现请求批处理，减少网络往返")
                recommendations.append("使用连接池复用连接")
                recommendations.append("压缩传输数据减少带宽占用")

        if not recommendations:
            recommendations.append("当前性能良好，建议建立性能基线以便持续监控")

        return list(set(recommendations))

    def detect_anomaly(self, metric_name: str, current_value: float,
                       threshold_std: float = 2.0) -> Dict[str, Any]:
        """异常检测"""
        history = self.metric_history.get(metric_name, [])
        if len(history) < 10:
            return {"is_anomaly": False, "reason": "数据不足"}

        mean = statistics.mean(history)
        std = statistics.stdev(history)

        if std == 0:
            return {"is_anomaly": False, "reason": "数据无变化"}

        z_score = abs(current_value - mean) / std

        return {
            "is_anomaly": z_score > threshold_std,
            "z_score": round(z_score, 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "current": current_value,
            "threshold": threshold_std,
            "reason": f"Z分数 {z_score:.2f} {'超过' if z_score > threshold_std else '未超过'}阈值 {threshold_std}"
        }

    def create_baseline(self, name: str, metrics: Dict[str, float]) -> str:
        """创建性能基线"""
        baseline_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()
        baseline = PerformanceBaseline(
            baseline_id=baseline_id,
            name=name,
            metrics=metrics,
            created_at=now,
            updated_at=now
        )
        self.baselines[baseline_id] = baseline
        self._save()
        return baseline_id

    def compare_with_baseline(self, baseline_id: str,
                              current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """与基线对比"""
        baseline = self.baselines.get(baseline_id)
        if not baseline:
            return {"error": "基线不存在"}

        comparison = {}
        for key in set(list(baseline.metrics.keys()) + list(current_metrics.keys())):
            base_val = baseline.metrics.get(key, 0)
            curr_val = current_metrics.get(key, 0)
            if base_val != 0:
                change_pct = ((curr_val - base_val) / base_val) * 100
            else:
                change_pct = 0

            comparison[key] = {
                "baseline": base_val,
                "current": curr_val,
                "change_percent": round(change_pct, 2),
                "status": "improved" if change_pct < 0 else "degraded" if change_pct > 5 else "stable"
            }

        return comparison

    def record_optimization(self, strategy: str, target: str,
                            before: Dict[str, float], after: Dict[str, float]) -> str:
        """记录优化效果"""
        opt_id = hashlib.md5(f"{target}_{time.time()}".encode()).hexdigest()[:12]

        improvement = 0.0
        if before and after:
            improvements = []
            for key in before:
                if key in after and before[key] != 0:
                    imp = ((before[key] - after[key]) / before[key]) * 100
                    improvements.append(imp)
            if improvements:
                improvement = statistics.mean(improvements)

        record = OptimizationRecord(
            optimization_id=opt_id,
            strategy=strategy,
            target=target,
            before_metrics=before,
            after_metrics=after,
            improvement=round(improvement, 2),
            applied=True,
            timestamp=time.time()
        )
        self.optimizations.append(record)
        self._save()
        return opt_id

    def get_optimization_history(self, target: str = None) -> List[Dict[str, Any]]:
        """获取优化历史"""
        records = self.optimizations
        if target:
            records = [r for r in records if r.target == target]
        return [asdict(r) for r in sorted(records, key=lambda x: x.timestamp, reverse=True)]

    def get_metric_trend(self, metric_name: str, window: int = 20) -> Dict[str, Any]:
        """获取指标趋势"""
        history = self.metric_history.get(metric_name, [])
        if len(history) < 2:
            return {"trend": "insufficient_data"}

        recent = history[-window:]
        older = history[-window*2:-window] if len(history) >= window*2 else history[:len(recent)]

        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)

        if older_avg == 0:
            change = 0
        else:
            change = ((recent_avg - older_avg) / older_avg) * 100

        if change > 10:
            trend = "increasing"
        elif change < -10:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "metric": metric_name,
            "trend": trend,
            "recent_avg": round(recent_avg, 2),
            "older_avg": round(older_avg, 2),
            "change_percent": round(change, 2),
            "data_points": len(history)
        }

    def suggest_optimizations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """智能优化建议"""
        suggestions = []

        if context.get("response_time", 0) > 500:
            suggestions.append({
                "strategy": OptimizationStrategy.CACHING.value,
                "priority": "high",
                "description": "实现响应缓存，减少重复计算",
                "expected_improvement": "50-80% 响应时间降低"
            })

        if context.get("request_count", 0) > 1000:
            suggestions.append({
                "strategy": OptimizationStrategy.BATCHING.value,
                "priority": "medium",
                "description": "批量处理请求，减少IO开销",
                "expected_improvement": "30-50% 吞吐量提升"
            })

        if context.get("data_size_mb", 0) > 100:
            suggestions.append({
                "strategy": OptimizationStrategy.COMPRESSION.value,
                "priority": "medium",
                "description": "压缩数据减少存储和传输开销",
                "expected_improvement": "40-60% 存储空间节省"
            })

        if context.get("query_count", 0) > 100:
            suggestions.append({
                "strategy": OptimizationStrategy.INDEXING.value,
                "priority": "high",
                "description": "添加索引加速查询",
                "expected_improvement": "10-100x 查询速度提升"
            })

        if context.get("concurrent_users", 0) > 50:
            suggestions.append({
                "strategy": OptimizationStrategy.PARALLELIZATION.value,
                "priority": "high",
                "description": "并行化处理提升并发能力",
                "expected_improvement": "2-8x 并发处理能力"
            })

        return suggestions

    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        total_metrics = len(self.metrics)
        total_profiles = len(self.profiles)
        total_bottlenecks = len(self.bottlenecks)
        total_optimizations = len(self.optimizations)

        avg_improvement = 0.0
        if self.optimizations:
            improvements = [o.improvement for o in self.optimizations if o.applied]
            if improvements:
                avg_improvement = statistics.mean(improvements)

        bottleneck_types = defaultdict(int)
        for b in self.bottlenecks:
            bottleneck_types[b.bottleneck_type] += 1

        return {
            "total_metrics": total_metrics,
            "total_profiles": total_profiles,
            "total_bottlenecks": total_bottlenecks,
            "total_optimizations": total_optimizations,
            "avg_improvement_percent": round(avg_improvement, 2),
            "bottleneck_distribution": dict(bottleneck_types),
            "baselines_count": len(self.baselines),
            "tracked_metrics": len(self.metric_history)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "metrics_count": len(self.metrics),
            "profiles_count": len(self.profiles),
            "bottlenecks_count": len(self.bottlenecks),
            "optimizations_count": len(self.optimizations),
            "baselines_count": len(self.baselines),
            "tracked_metrics": len(self.metric_history)
        }


if __name__ == "__main__":
    engine = PerformanceOptimizationEngine()
    print("=== 性能优化系统测试 ===")

    # 记录指标
    mid = engine.record_metric("latency", "api_response_time", 150, "ms", "api_server")
    print(f"记录指标: {mid}")

    # 性能分析
    pid = engine.start_profile("api_endpoint", "detailed")
    result = engine.end_profile(pid, {
        "cpu_percent": 85,
        "memory_percent": 60,
        "io_wait": 10,
        "latency_ms": 1200,
        "duration": 2.5
    })
    print(f"分析完成: {len(result.bottlenecks)} 个瓶颈, {len(result.recommendations)} 条建议")

    # 创建基线
    bid = engine.create_baseline("initial_baseline", {
        "response_time": 200,
        "throughput": 500,
        "error_rate": 0.01
    })
    print(f"基线创建: {bid}")

    # 优化记录
    oid = engine.record_optimization(
        "caching", "api_endpoint",
        {"response_time": 200, "throughput": 500},
        {"response_time": 50, "throughput": 800}
    )
    print(f"优化记录: {oid}")

    # 异常检测
    anomaly = engine.detect_anomaly("api_response_time", 500)
    print(f"异常检测: {anomaly}")

    # 趋势分析
    for v in [100, 110, 105, 115, 120, 125, 130, 135, 140, 145, 150]:
        engine.record_metric("latency", "api_response_time", v, "ms")
    trend = engine.get_metric_trend("api_response_time")
    print(f"趋势分析: {trend}")

    # 报告
    report = engine.generate_report()
    print(f"\n性能报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    print("\n测试完成!")
