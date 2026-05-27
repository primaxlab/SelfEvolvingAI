"""日志分析系统 - 日志收集、模式识别、异常检测、趋势分析"""

import json
import os
import time
import hashlib
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import statistics


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogSource(Enum):
    """日志来源"""
    APPLICATION = "application"
    SYSTEM = "system"
    ACCESS = "access"
    ERROR_LOG = "error_log"
    AUDIT = "audit"
    CUSTOM = "custom"


class PatternType(Enum):
    """模式类型"""
    FREQUENT_ERROR = "frequent_error"
    ERROR_BURST = "error_burst"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    UNUSUAL_ACTIVITY = "unusual_activity"
    RECURRING_PATTERN = "recurring_pattern"
    ANOMALY = "anomaly"


@dataclass
class LogEntry:
    """日志条目"""
    log_id: str
    timestamp: float
    level: str
    source: str
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""


@dataclass
class LogPattern:
    """日志模式"""
    pattern_id: str
    pattern_type: str
    description: str
    regex: str = ""
    frequency: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    examples: List[str] = field(default_factory=list)
    severity: float = 0.0
    is_active: bool = True


@dataclass
class LogAnomaly:
    """日志异常"""
    anomaly_id: str
    anomaly_type: str
    description: str
    detected_at: float
    severity: float
    related_logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


@dataclass
class LogAnalysisReport:
    """分析报告"""
    report_id: str
    start_time: float
    end_time: float
    duration: float
    total_logs: int = 0
    level_distribution: Dict[str, int] = field(default_factory=dict)
    source_distribution: Dict[str, int] = field(default_factory=dict)
    top_errors: List[Dict[str, Any]] = field(default_factory=list)
    patterns_found: int = 0
    anomalies_detected: int = 0
    recommendations: List[str] = field(default_factory=list)


class LogAnalysisEngine:
    """日志分析引擎"""

    def __init__(self, storage_dir: str = "data/logs"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.logs: List[LogEntry] = []
        self.patterns: List[LogPattern] = []
        self.anomalies: List[LogAnomaly] = []
        self.reports: List[LogAnalysisReport] = []
        self.error_fingerprints: Dict[str, int] = defaultdict(int)
        self.hourly_counts: Dict[int, int] = defaultdict(int)
        self.level_counts: Dict[str, int] = defaultdict(int)

        self._load()

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "log_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.logs = [LogEntry(**l) for l in data.get("logs", [])]
                self.patterns = [LogPattern(**p) for p in data.get("patterns", [])]
                self.anomalies = [LogAnomaly(**a) for a in data.get("anomalies", [])]
                self.error_fingerprints = defaultdict(int, data.get("error_fingerprints", {}))
                self.hourly_counts = defaultdict(int, data.get("hourly_counts", {}))
                self.level_counts = defaultdict(int, data.get("level_counts", {}))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "log_data.json")
        data = {
            "logs": [asdict(l) for l in self.logs[-50000:]],
            "patterns": [asdict(p) for p in self.patterns],
            "anomalies": [asdict(a) for a in self.anomalies[-1000:]],
            "error_fingerprints": dict(self.error_fingerprints),
            "hourly_counts": {str(k): v for k, v in self.hourly_counts.items()},
            "level_counts": dict(self.level_counts)
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _compute_fingerprint(self, message: str) -> str:
        """计算日志指纹"""
        # 移除数字、时间戳、ID等变化部分
        normalized = re.sub(r'\d+', 'N', message)
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID', normalized)
        normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'IP', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def add_log(self, level: str, message: str, source: str = "application",
                module: str = "", function: str = "", line_number: int = 0,
                extra: Dict[str, Any] = None) -> str:
        """添加日志"""
        log_id = hashlib.md5(f"{message}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()

        fingerprint = self._compute_fingerprint(message)

        log = LogEntry(
            log_id=log_id,
            timestamp=now,
            level=level,
            source=source,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            extra=extra or {},
            fingerprint=fingerprint
        )

        self.logs.append(log)
        self.level_counts[level] += 1

        hour = int((now % 86400) / 3600)
        self.hourly_counts[hour] += 1

        if level in ["error", "critical"]:
            self.error_fingerprints[fingerprint] += 1

        # 实时异常检测
        self._check_realtime_anomaly(log)

        self._save()
        return log_id

    def _check_realtime_anomaly(self, log: LogEntry):
        """实时异常检测"""
        # 检查错误突发
        if log.level in ["error", "critical"]:
            recent_errors = [l for l in self.logs[-100:] if l.level in ["error", "critical"]]
            if len(recent_errors) > 10:
                time_span = recent_errors[-1].timestamp - recent_errors[0].timestamp
                if time_span < 60:  # 1分钟内超过10个错误
                    self._add_anomaly(
                        PatternType.ERROR_BURST.value,
                        f"错误突发: 1分钟内{len(recent_errors)}个错误",
                        0.8,
                        [l.log_id for l in recent_errors[-5:]]
                    )

        # 检查频繁错误
        if log.fingerprint in self.error_fingerprints:
            count = self.error_fingerprints[log.fingerprint]
            if count > 100:
                existing = [p for p in self.patterns if p.pattern_type == PatternType.FREQUENT_ERROR.value
                           and log.message[:50] in str(p.examples)]
                if not existing:
                    self._add_pattern(
                        PatternType.FREQUENT_ERROR.value,
                        f"频繁错误 (出现{count}次): {log.message[:100]}",
                        count
                    )

    def _add_anomaly(self, anomaly_type: str, description: str,
                     severity: float, related_logs: List[str] = None):
        """添加异常"""
        anomaly = LogAnomaly(
            anomaly_id=hashlib.md5(f"{anomaly_type}_{time.time()}".encode()).hexdigest()[:12],
            anomaly_type=anomaly_type,
            description=description,
            detected_at=time.time(),
            severity=severity,
            related_logs=related_logs or []
        )
        self.anomalies.append(anomaly)

    def _add_pattern(self, pattern_type: str, description: str,
                     frequency: int, examples: List[str] = None):
        """添加模式"""
        pattern = LogPattern(
            pattern_id=hashlib.md5(f"{pattern_type}_{time.time()}".encode()).hexdigest()[:12],
            pattern_type=pattern_type,
            description=description,
            frequency=frequency,
            first_seen=time.time(),
            last_seen=time.time(),
            examples=examples or []
        )
        self.patterns.append(pattern)

    def search_logs(self, query: str = "", level: str = "",
                    source: str = "", start_time: float = 0,
                    end_time: float = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """搜索日志"""
        results = self.logs

        if query:
            query_lower = query.lower()
            results = [l for l in results if query_lower in l.message.lower()]

        if level:
            results = [l for l in results if l.level == level]

        if source:
            results = [l for l in results if l.source == source]

        if start_time:
            results = [l for l in results if l.timestamp >= start_time]

        if end_time:
            results = [l for l in results if l.timestamp <= end_time]

        results = sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [asdict(l) for l in results]

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff = time.time() - hours * 3600
        recent_errors = [l for l in self.logs if l.level in ["error", "critical"] and l.timestamp > cutoff]

        # 按指纹分组
        grouped = defaultdict(list)
        for error in recent_errors:
            grouped[error.fingerprint].append(error)

        summary = []
        for fp, errors in grouped.items():
            summary.append({
                "fingerprint": fp,
                "count": len(errors),
                "first_seen": min(e.timestamp for e in errors),
                "last_seen": max(e.timestamp for e in errors),
                "sample_message": errors[0].message[:200],
                "modules": list(set(e.module for e in errors if e.module))
            })

        summary.sort(key=lambda x: x["count"], reverse=True)

        return {
            "time_range_hours": hours,
            "total_errors": len(recent_errors),
            "unique_errors": len(grouped),
            "top_errors": summary[:20]
        }

    def get_level_distribution(self, hours: int = 24) -> Dict[str, int]:
        """获取级别分布"""
        cutoff = time.time() - hours * 3600
        recent = [l for l in self.logs if l.timestamp > cutoff]

        distribution = defaultdict(int)
        for log in recent:
            distribution[log.level] += 1

        return dict(distribution)

    def get_source_distribution(self, hours: int = 24) -> Dict[str, int]:
        """获取来源分布"""
        cutoff = time.time() - hours * 3600
        recent = [l for l in self.logs if l.timestamp > cutoff]

        distribution = defaultdict(int)
        for log in recent:
            distribution[log.source] += 1

        return dict(distribution)

    def get_hourly_activity(self, hours: int = 24) -> Dict[int, int]:
        """获取每小时活动"""
        cutoff = time.time() - hours * 3600
        recent = [l for l in self.logs if l.timestamp > cutoff]

        hourly = defaultdict(int)
        for log in recent:
            hour = int((log.timestamp % 86400) / 3600)
            hourly[hour] += 1

        return dict(sorted(hourly.items()))

    def detect_patterns(self) -> List[Dict[str, Any]]:
        """检测模式"""
        detected = []

        # 检测周期性错误
        error_times = [l.timestamp for l in self.logs if l.level in ["error", "critical"]]
        if len(error_times) > 10:
            intervals = [error_times[i+1] - error_times[i] for i in range(len(error_times)-1)]
            if intervals:
                avg_interval = statistics.mean(intervals)
                std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0

                if std_interval < avg_interval * 0.2 and avg_interval > 0:
                    detected.append({
                        "type": PatternType.RECURRING_PATTERN.value,
                        "description": f"周期性错误，平均间隔 {avg_interval:.0f} 秒",
                        "interval": avg_interval
                    })

        # 检测日志量异常
        hourly = self.get_hourly_activity(24)
        if hourly:
            values = list(hourly.values())
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0

            for hour, count in hourly.items():
                if std_val > 0 and abs(count - mean_val) > 2 * std_val:
                    detected.append({
                        "type": PatternType.UNUSUAL_ACTIVITY.value,
                        "description": f"小时 {hour} 日志量异常: {count} (平均 {mean_val:.0f})",
                        "hour": hour,
                        "count": count
                    })

        return detected

    def parse_log_line(self, line: str, format: str = "auto") -> Dict[str, Any]:
        """解析日志行"""
        patterns = {
            "common": r'(?P<ip>[\d\.]+) - - \[(?P<time>[^\]]+)\] "(?P<method>\w+) (?P<url>[^\s]+) [^"]*" (?P<status>\d+) (?P<size>\d+)',
            "json": r'^\{.*\}$',
            "timestamp_level": r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*)\s+(?P<level>\w+)\s+(?P<message>.*)'
        }

        if format == "auto":
            for fmt, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    return {"format": fmt, "fields": match.groupdict()}
        elif format in patterns:
            match = re.match(patterns[format], line)
            if match:
                return {"format": format, "fields": match.groupdict()}

        return {"format": "unknown", "raw": line}

    def generate_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成分析报告"""
        cutoff = time.time() - hours * 3600
        recent = [l for l in self.logs if l.timestamp > cutoff]

        level_dist = self.get_level_distribution(hours)
        source_dist = self.get_source_distribution(hours)
        error_summary = self.get_error_summary(hours)
        patterns = self.detect_patterns()

        recommendations = []

        if level_dist.get("error", 0) > 100:
            recommendations.append("错误日志数量过多，建议排查根因")

        if level_dist.get("critical", 0) > 10:
            recommendations.append("存在严重错误，需要立即处理")

        error_ratio = level_dist.get("error", 0) / max(len(recent), 1)
        if error_ratio > 0.1:
            recommendations.append(f"错误率 {error_ratio:.1%}，超过阈值，建议优化")

        if not recommendations:
            recommendations.append("系统运行正常")

        return {
            "time_range_hours": hours,
            "total_logs": len(recent),
            "level_distribution": level_dist,
            "source_distribution": source_dist,
            "error_summary": error_summary,
            "patterns_detected": len(patterns),
            "anomalies_detected": len([a for a in self.anomalies if a.detected_at > cutoff]),
            "recommendations": recommendations
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_logs": len(self.logs),
            "patterns_count": len(self.patterns),
            "anomalies_count": len(self.anomalies),
            "unique_fingerprints": len(self.error_fingerprints),
            "level_distribution": dict(self.level_counts)
        }


if __name__ == "__main__":
    engine = LogAnalysisEngine()
    print("=== 日志分析系统测试 ===")

    # 添加日志
    for i in range(20):
        engine.add_log("info", f"用户登录成功 user_{i}", source="auth", module="auth_service")

    for i in range(5):
        engine.add_log("error", f"数据库连接失败: timeout after 30s", source="database", module="db_service")

    engine.add_log("critical", "系统内存不足，即将OOM", source="system", module="memory_manager")
    engine.add_log("warning", "磁盘空间低于10%", source="system", module="disk_monitor")

    print(f"添加了 {len(engine.logs)} 条日志")

    # 搜索
    results = engine.search_logs(query="数据库", level="error")
    print(f"搜索结果: {len(results)} 条")

    # 错误摘要
    error_summary = engine.get_error_summary()
    print(f"错误摘要: {error_summary['total_errors']} 个错误, {error_summary['unique_errors']} 种类型")

    # 级别分布
    distribution = engine.get_level_distribution()
    print(f"级别分布: {distribution}")

    # 模式检测
    patterns = engine.detect_patterns()
    print(f"检测到 {len(patterns)} 个模式")

    # 报告
    report = engine.generate_report()
    print(f"\n分析报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    print("\n测试完成!")
