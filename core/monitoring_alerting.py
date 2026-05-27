"""监控告警系统 - 指标收集、阈值监控、告警触发、健康检查"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import statistics


class MetricType(Enum):
    """指标类型"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(Enum):
    """告警状态"""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """监控指标"""
    metric_id: str
    name: str
    value: float
    metric_type: str = "gauge"
    unit: str = ""
    timestamp: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: str = "warning"
    duration: int = 0  # 持续时间(秒)
    description: str = ""
    is_active: bool = True
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """告警"""
    alert_id: str
    rule_id: str
    rule_name: str
    severity: str
    state: str = "pending"
    current_value: float = 0.0
    threshold: float = 0.0
    started_at: float = 0.0
    resolved_at: float = 0.0
    description: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    notifications_sent: int = 0


@dataclass
class HealthCheck:
    """健康检查"""
    check_id: str
    name: str
    target: str
    status: str = "unknown"
    last_check: float = 0.0
    last_success: float = 0.0
    consecutive_failures: int = 0
    response_time: float = 0.0
    message: str = ""
    is_active: bool = True


@dataclass
class Dashboard:
    """仪表盘"""
    dashboard_id: str
    name: str
    description: str = ""
    panels: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    is_public: bool = False


class MonitoringAlertingEngine:
    """监控告警引擎"""

    def __init__(self, storage_dir: str = "data/monitoring"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.metrics: List[Metric] = []
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        self.dashboards: Dict[str, Dashboard] = {}
        self.metric_values: Dict[str, List[float]] = defaultdict(list)
        self.notification_log: List[Dict[str, Any]] = []

        self._load()

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "monitoring_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.metrics = [Metric(**m) for m in data.get("metrics", [])]
                for k, v in data.get("alert_rules", {}).items():
                    self.alert_rules[k] = AlertRule(**v)
                self.alerts = [Alert(**a) for a in data.get("alerts", [])]
                for k, v in data.get("health_checks", {}).items():
                    self.health_checks[k] = HealthCheck(**v)
                for k, v in data.get("dashboards", {}).items():
                    self.dashboards[k] = Dashboard(**v)
                self.metric_values = defaultdict(list, data.get("metric_values", {}))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "monitoring_data.json")
        data = {
            "metrics": [asdict(m) for m in self.metrics[-10000:]],
            "alert_rules": {k: asdict(v) for k, v in self.alert_rules.items()},
            "alerts": [asdict(a) for a in self.alerts[-5000:]],
            "health_checks": {k: asdict(v) for k, v in self.health_checks.items()},
            "dashboards": {k: asdict(v) for k, v in self.dashboards.items()},
            "metric_values": {k: v[-1000:] for k, v in self.metric_values.items()}
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_metric(self, name: str, value: float, metric_type: str = "gauge",
                      unit: str = "", labels: Dict[str, str] = None) -> str:
        """记录指标"""
        metric_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        now = time.time()

        metric = Metric(
            metric_id=metric_id,
            name=name,
            value=value,
            metric_type=metric_type,
            unit=unit,
            timestamp=now,
            labels=labels or {}
        )

        self.metrics.append(metric)
        self.metric_values[name].append(value)

        if len(self.metric_values[name]) > 1000:
            self.metric_values[name] = self.metric_values[name][-1000:]

        # 检查告警规则
        self._check_alert_rules(name, value)

        self._save()
        return metric_id

    def _check_alert_rules(self, metric_name: str, value: float):
        """检查告警规则"""
        for rule in self.alert_rules.values():
            if rule.metric_name != metric_name or not rule.is_active:
                continue

            triggered = False
            if rule.condition == "gt" and value > rule.threshold:
                triggered = True
            elif rule.condition == "lt" and value < rule.threshold:
                triggered = True
            elif rule.condition == "eq" and value == rule.threshold:
                triggered = True
            elif rule.condition == "gte" and value >= rule.threshold:
                triggered = True
            elif rule.condition == "lte" and value <= rule.threshold:
                triggered = True

            if triggered:
                self._create_alert(rule, value)
            else:
                self._resolve_alert(rule.rule_id)

    def _create_alert(self, rule: AlertRule, current_value: float):
        """创建告警"""
        # 检查是否已有活跃告警
        existing = [a for a in self.alerts if a.rule_id == rule.rule_id and a.state in ["pending", "firing"]]
        if existing:
            existing[0].current_value = current_value
            existing[0].state = "firing"
            return

        alert = Alert(
            alert_id=hashlib.md5(f"{rule.rule_id}_{time.time()}".encode()).hexdigest()[:12],
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            state="firing",
            current_value=current_value,
            threshold=rule.threshold,
            started_at=time.time(),
            description=f"{rule.name}: {current_value} {rule.condition} {rule.threshold}",
            labels=rule.labels
        )
        self.alerts.append(alert)

        # 发送通知
        self._send_notification(alert)

    def _resolve_alert(self, rule_id: str):
        """解决告警"""
        for alert in self.alerts:
            if alert.rule_id == rule_id and alert.state in ["pending", "firing"]:
                alert.state = "resolved"
                alert.resolved_at = time.time()

    def _send_notification(self, alert: Alert):
        """发送通知"""
        notification = {
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "message": alert.description,
            "timestamp": time.time()
        }
        self.notification_log.append(notification)
        alert.notifications_sent += 1

    def create_alert_rule(self, name: str, metric_name: str, condition: str,
                          threshold: float, severity: str = "warning",
                          description: str = "", duration: int = 0) -> str:
        """创建告警规则"""
        rule_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=severity,
            duration=duration,
            description=description
        )
        self.alert_rules[rule_id] = rule
        self._save()
        return rule_id

    def silence_alert(self, alert_id: str, duration: int = 3600) -> bool:
        """静默告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.state = "silenced"
                self._save()
                return True
        return False

    def get_active_alerts(self, severity: str = "") -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = [a for a in self.alerts if a.state in ["pending", "firing"]]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [asdict(a) for a in sorted(alerts, key=lambda x: x.started_at, reverse=True)]

    def register_health_check(self, name: str, target: str) -> str:
        """注册健康检查"""
        check_id = hashlib.md5(f"{name}_{target}".encode()).hexdigest()[:12]
        check = HealthCheck(
            check_id=check_id,
            name=name,
            target=target,
            status="unknown",
            is_active=True
        )
        self.health_checks[check_id] = check
        self._save()
        return check_id

    def update_health_check(self, check_id: str, status: str,
                            response_time: float = 0, message: str = "") -> bool:
        """更新健康检查"""
        if check_id not in self.health_checks:
            return False

        check = self.health_checks[check_id]
        check.last_check = time.time()
        check.status = status
        check.response_time = response_time
        check.message = message

        if status == "healthy":
            check.last_success = time.time()
            check.consecutive_failures = 0
        else:
            check.consecutive_failures += 1

        self._save()
        return True

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        statuses = [c.status for c in self.health_checks.values() if c.is_active]

        if not statuses:
            overall = "unknown"
        elif all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "overall": overall,
            "checks": {k: asdict(v) for k, v in self.health_checks.items()},
            "total_checks": len(statuses),
            "healthy_count": statuses.count("healthy"),
            "unhealthy_count": statuses.count("unhealthy")
        }

    def get_metric_stats(self, metric_name: str) -> Dict[str, Any]:
        """获取指标统计"""
        values = self.metric_values.get(metric_name, [])
        if not values:
            return {"error": "无数据"}

        return {
            "metric": metric_name,
            "count": len(values),
            "current": values[-1],
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0
        }

    def create_dashboard(self, name: str, description: str = "",
                         panels: List[Dict[str, Any]] = None) -> str:
        """创建仪表盘"""
        dashboard_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            description=description,
            panels=panels or [],
            created_at=time.time(),
            updated_at=time.time()
        )
        self.dashboards[dashboard_id] = dashboard
        self._save()
        return dashboard_id

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """获取仪表盘"""
        dashboard = self.dashboards.get(dashboard_id)
        return asdict(dashboard) if dashboard else None

    def get_alert_history(self, hours: int = 24, severity: str = "") -> List[Dict[str, Any]]:
        """获取告警历史"""
        cutoff = time.time() - hours * 3600
        alerts = [a for a in self.alerts if a.started_at > cutoff]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [asdict(a) for a in sorted(alerts, key=lambda x: x.started_at, reverse=True)]

    def generate_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        active_alerts = [a for a in self.alerts if a.state in ["pending", "firing"]]
        health = self.get_health_status()

        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity] += 1

        return {
            "total_metrics_tracked": len(self.metric_values),
            "total_alert_rules": len(self.alert_rules),
            "active_alerts": len(active_alerts),
            "alert_severity_distribution": dict(severity_counts),
            "health_status": health["overall"],
            "health_checks": health["total_checks"],
            "healthy_checks": health["healthy_count"],
            "dashboards_count": len(self.dashboards),
            "notifications_sent": len(self.notification_log)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "metrics_count": len(self.metrics),
            "alert_rules_count": len(self.alert_rules),
            "alerts_count": len(self.alerts),
            "health_checks_count": len(self.health_checks),
            "dashboards_count": len(self.dashboards),
            "tracked_metrics": len(self.metric_values)
        }


if __name__ == "__main__":
    engine = MonitoringAlertingEngine()
    print("=== 监控告警系统测试 ===")

    # 记录指标
    engine.record_metric("cpu_usage", 45.5, "gauge", "%")
    engine.record_metric("memory_usage", 68.2, "gauge", "%")
    engine.record_metric("request_count", 1500, "counter", "req")
    engine.record_metric("response_time", 250, "gauge", "ms")
    print("指标记录完成")

    # 创建告警规则
    rule1 = engine.create_alert_rule("CPU过高", "cpu_usage", "gt", 80, "warning", "CPU使用率超过80%")
    rule2 = engine.create_alert_rule("内存过高", "memory_usage", "gt", 90, "critical", "内存使用率超过90%")
    rule3 = engine.create_alert_rule("响应慢", "response_time", "gt", 1000, "error", "响应时间超过1秒")
    print(f"创建告警规则: {rule1}, {rule2}, {rule3}")

    # 触发告警
    engine.record_metric("cpu_usage", 85.5)
    engine.record_metric("memory_usage", 92.1)
    print("触发告警")

    # 活跃告警
    active = engine.get_active_alerts()
    print(f"活跃告警: {len(active)} 个")

    # 健康检查
    check1 = engine.register_health_check("API服务", "http://localhost:8000/health")
    check2 = engine.register_health_check("数据库", "postgresql://localhost:5432")
    engine.update_health_check(check1, "healthy", 50, "正常")
    engine.update_health_check(check2, "healthy", 10, "正常")
    print(f"健康检查: {check1}, {check2}")

    # 仪表盘
    dashboard_id = engine.create_dashboard("系统监控", "系统整体监控面板", [
        {"type": "gauge", "metric": "cpu_usage", "title": "CPU使用率"},
        {"type": "line", "metric": "response_time", "title": "响应时间"}
    ])
    print(f"仪表盘: {dashboard_id}")

    # 指标统计
    stats = engine.get_metric_stats("cpu_usage")
    print(f"CPU统计: {stats}")

    # 报告
    report = engine.generate_report()
    print(f"\n监控报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    print("\n测试完成!")
