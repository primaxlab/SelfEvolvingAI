"""
================================================================================
自愈系统 (Self-Healing System)
================================================================================

核心能力：
  1. 故障检测 - 自动检测系统故障
  2. 故障诊断 - 诊断故障原因
  3. 自动修复 - 自动修复故障
  4. 预防维护 - 预防性维护
  5. 健康监控 - 持续监控系统健康

设计原则：
  - 快速响应：故障发生后快速检测和修复
  - 最小影响：修复过程尽量不影响正常服务
  - 持续学习：从故障中学习，防止再发
"""

import json
import os
import time
import hashlib
import traceback
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class HealthStatus(Enum):
    HEALTHY = "healthy"          # 健康
    DEGRADED = "degraded"        # 性能下降
    UNHEALTHY = "unhealthy"      # 不健康
    CRITICAL = "critical"        # 严重故障
    DOWN = "down"                # 宕机

class FaultType(Enum):
    PERFORMANCE = "performance"  # 性能问题
    FUNCTIONAL = "functional"    # 功能故障
    RESOURCE = "resource"        # 资源问题
    DEPENDENCY = "dependency"    # 依赖问题
    CONFIGURATION = "configuration"  # 配置问题
    UNKNOWN = "unknown"

class RepairAction(Enum):
    RESTART = "restart"          # 重启
    RECONFIGURE = "reconfigure"  # 重新配置
    ROLLBACK = "rollback"        # 回滚
    SCALE = "scale"              # 扩容
    ISOLATE = "isolate"          # 隔离
    NOTIFY = "notify"            # 通知

@dataclass
class HealthCheck:
    """健康检查"""
    component: str
    status: HealthStatus
    metrics: dict
    timestamp: float = field(default_factory=time.time)
    details: str = ""

@dataclass
class Fault:
    """故障"""
    id: str
    fault_type: FaultType
    component: str
    description: str
    severity: HealthStatus
    detected_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    resolved: bool = False
    repair_action: Optional[RepairAction] = None
    root_cause: str = ""

@dataclass
class RepairRecord:
    """修复记录"""
    fault_id: str
    action: RepairAction
    success: bool
    duration: float
    details: str
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 故障检测器
# ============================================================================

class FaultDetector:
    """故障检测器"""

    def __init__(self):
        # 检测规则
        self.detection_rules = {
            'high_error_rate': {
                'threshold': 0.1,
                'metric': 'error_rate',
                'fault_type': FaultType.FUNCTIONAL,
            },
            'high_latency': {
                'threshold': 5.0,
                'metric': 'response_time',
                'fault_type': FaultType.PERFORMANCE,
            },
            'low_memory': {
                'threshold': 0.9,
                'metric': 'memory_usage',
                'fault_type': FaultType.RESOURCE,
            },
            'high_cpu': {
                'threshold': 0.9,
                'metric': 'cpu_usage',
                'fault_type': FaultType.RESOURCE,
            },
        }

        self.detected_faults: list[Fault] = []

    def detect(self, component: str, metrics: dict) -> list:
        """检测故障"""
        faults = []

        for rule_name, rule in self.detection_rules.items():
            metric_value = metrics.get(rule['metric'], 0)
            threshold = rule['threshold']

            if metric_value > threshold:
                fault = Fault(
                    id=hashlib.md5(f"{component}:{rule_name}:{time.time()}".encode()).hexdigest()[:12],
                    fault_type=rule['fault_type'],
                    component=component,
                    description=f"{rule_name}: {rule['metric']}={metric_value:.2f} > {threshold}",
                    severity=self._determine_severity(metric_value, threshold),
                )
                faults.append(fault)
                self.detected_faults.append(fault)

        return faults

    def _determine_severity(self, value: float,
                             threshold: float) -> HealthStatus:
        """确定严重程度"""
        ratio = value / threshold

        if ratio > 2.0:
            return HealthStatus.CRITICAL
        elif ratio > 1.5:
            return HealthStatus.UNHEALTHY
        elif ratio > 1.2:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.DEGRADED

    def get_active_faults(self) -> list:
        """获取活跃故障"""
        return [f for f in self.detected_faults if not f.resolved]

    def get_fault_history(self) -> list:
        """获取故障历史"""
        return self.detected_faults


# ============================================================================
# 故障诊断器
# ============================================================================

class FaultDiagnoser:
    """故障诊断器"""

    def __init__(self):
        # 诊断规则
        self.diagnostic_rules = {
            FaultType.PERFORMANCE: [
                {'cause': '资源不足', 'check': 'resource_usage'},
                {'cause': '算法效率低', 'check': 'algorithm_complexity'},
                {'cause': '并发过高', 'check': 'concurrent_requests'},
            ],
            FaultType.FUNCTIONAL: [
                {'cause': '代码错误', 'check': 'error_logs'},
                {'cause': '输入异常', 'check': 'input_validation'},
                {'cause': '状态不一致', 'check': 'state_consistency'},
            ],
            FaultType.RESOURCE: [
                {'cause': '内存泄漏', 'check': 'memory_trend'},
                {'cause': '磁盘空间不足', 'check': 'disk_usage'},
                {'cause': '连接池耗尽', 'check': 'connection_pool'},
            ],
        }

    def diagnose(self, fault: Fault,
                  system_state: dict = None) -> dict:
        """诊断故障"""
        # 获取诊断规则
        rules = self.diagnostic_rules.get(fault.fault_type, [])

        possible_causes = []
        for rule in rules:
            # 检查相关指标
            check_result = self._perform_check(rule['check'], system_state or {})
            if check_result.get('abnormal'):
                possible_causes.append({
                    'cause': rule['cause'],
                    'confidence': check_result.get('confidence', 0.5),
                    'evidence': check_result.get('evidence', ''),
                })

        # 按置信度排序
        possible_causes.sort(key=lambda x: x['confidence'], reverse=True)

        return {
            'fault_id': fault.id,
            'fault_type': fault.fault_type.value,
            'possible_causes': possible_causes,
            'recommended_action': self._recommend_action(fault, possible_causes),
        }

    def _perform_check(self, check_name: str,
                        state: dict) -> dict:
        """执行检查"""
        # 简化实现
        return {
            'abnormal': check_name in state,
            'confidence': 0.5,
            'evidence': state.get(check_name, ''),
        }

    def _recommend_action(self, fault: Fault,
                           causes: list) -> RepairAction:
        """推荐修复动作"""
        if fault.severity == HealthStatus.CRITICAL:
            return RepairAction.RESTART
        elif fault.fault_type == FaultType.RESOURCE:
            return RepairAction.SCALE
        elif fault.fault_type == FaultType.FUNCTIONAL:
            return RepairAction.ROLLBACK
        else:
            return RepairAction.RECONFIGURE


# ============================================================================
# 自动修复器
# ============================================================================

class AutoRepairer:
    """自动修复器"""

    def __init__(self):
        # 修复策略
        self.repair_strategies = {
            RepairAction.RESTART: self._restart,
            RepairAction.RECONFIGURE: self._reconfigure,
            RepairAction.ROLLBACK: self._rollback,
            RepairAction.SCALE: self._scale,
            RepairAction.ISOLATE: self._isolate,
            RepairAction.NOTIFY: self._notify,
        }

        self.repair_history: list[RepairRecord] = []

    def repair(self, fault: Fault,
                action: RepairAction,
                context: dict = None) -> RepairRecord:
        """执行修复"""
        start_time = time.time()

        # 执行修复策略
        strategy = self.repair_strategies.get(action, self._notify)
        success, details = strategy(fault, context or {})

        duration = time.time() - start_time

        # 记录修复
        record = RepairRecord(
            fault_id=fault.id,
            action=action,
            success=success,
            duration=duration,
            details=details,
        )
        self.repair_history.append(record)

        # 更新故障状态
        if success:
            fault.resolved = True
            fault.resolved_at = time.time()
            fault.repair_action = action

        return record

    def _restart(self, fault: Fault, context: dict) -> tuple:
        """重启组件"""
        # 模拟重启
        return True, f"重启 {fault.component} 成功"

    def _reconfigure(self, fault: Fault, context: dict) -> tuple:
        """重新配置"""
        return True, f"重新配置 {fault.component}"

    def _rollback(self, fault: Fault, context: dict) -> tuple:
        """回滚"""
        return True, f"回滚 {fault.component} 到上一个稳定版本"

    def _scale(self, fault: Fault, context: dict) -> tuple:
        """扩容"""
        return True, f"扩容 {fault.component}"

    def _isolate(self, fault: Fault, context: dict) -> tuple:
        """隔离"""
        return True, f"隔离故障组件 {fault.component}"

    def _notify(self, fault: Fault, context: dict) -> tuple:
        """通知"""
        return True, f"通知相关人员: {fault.description}"

    def get_repair_stats(self) -> dict:
        """获取修复统计"""
        total = len(self.repair_history)
        successful = sum(1 for r in self.repair_history if r.success)

        return {
            'total_repairs': total,
            'successful': successful,
            'success_rate': successful / max(1, total),
            'avg_duration': sum(r.duration for r in self.repair_history) / max(1, total),
        }


# ============================================================================
# 健康监控器
# ============================================================================

class HealthMonitor:
    """健康监控器"""

    def __init__(self):
        self.health_checks: dict[str, HealthCheck] = {}
        self.health_history: list[dict] = []

    def check_health(self, component: str,
                      metrics: dict) -> HealthCheck:
        """检查组件健康状态"""
        # 基于指标判断状态
        status = self._evaluate_health(metrics)

        check = HealthCheck(
            component=component,
            status=status,
            metrics=metrics,
        )

        self.health_checks[component] = check

        # 记录历史
        self.health_history.append({
            'component': component,
            'status': status.value,
            'timestamp': time.time(),
        })

        return check

    def _evaluate_health(self, metrics: dict) -> HealthStatus:
        """评估健康状态"""
        # 综合多个指标
        scores = []

        if 'error_rate' in metrics:
            scores.append(1.0 - metrics['error_rate'])

        if 'response_time' in metrics:
            scores.append(max(0, 1.0 - metrics['response_time'] / 10))

        if 'memory_usage' in metrics:
            scores.append(1.0 - metrics['memory_usage'])

        if not scores:
            return HealthStatus.HEALTHY

        avg_score = sum(scores) / len(scores)

        if avg_score > 0.8:
            return HealthStatus.HEALTHY
        elif avg_score > 0.6:
            return HealthStatus.DEGRADED
        elif avg_score > 0.4:
            return HealthStatus.UNHEALTHY
        elif avg_score > 0.2:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.DOWN

    def get_overall_health(self) -> dict:
        """获取整体健康状态"""
        if not self.health_checks:
            return {'status': 'unknown', 'components': 0}

        statuses = [c.status for c in self.health_checks.values()]

        # 整体状态取最差的
        worst = min(statuses, key=lambda s: list(HealthStatus).index(s))

        return {
            'status': worst.value,
            'components': len(self.health_checks),
            'healthy': sum(1 for s in statuses if s == HealthStatus.HEALTHY),
            'degraded': sum(1 for s in statuses if s == HealthStatus.DEGRADED),
            'unhealthy': sum(1 for s in statuses if s == HealthStatus.UNHEALTHY),
        }


# ============================================================================
# 自愈引擎
# ============================================================================

class SelfHealingEngine:
    """
    自愈引擎 - 整合所有组件

    核心功能：
    1. 持续监控系统健康
    2. 自动检测故障
    3. 诊断故障原因
    4. 自动修复故障
    5. 从故障中学习
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "self_healing"
        os.makedirs(storage_dir, exist_ok=True)

        self.fault_detector = FaultDetector()
        self.fault_diagnoser = FaultDiagnoser()
        self.auto_repairer = AutoRepairer()
        self.health_monitor = HealthMonitor()

        self.incident_history: list[dict] = []

        self.storage_path = os.path.join(storage_dir, "healing.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.incident_history = data.get('incidents', [])

    def _save(self):
        """保存数据"""
        data = {
            'incidents': self.incident_history[-100:],
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def monitor_component(self, component: str,
                           metrics: dict) -> dict:
        """监控组件"""
        # 1. 健康检查
        health_check = self.health_monitor.check_health(component, metrics)

        # 2. 故障检测
        faults = self.fault_detector.detect(component, metrics)

        # 3. 如果有故障，诊断并修复
        repairs = []
        for fault in faults:
            # 诊断
            diagnosis = self.fault_diagnoser.diagnose(fault, metrics)

            # 修复
            recommended_action = diagnosis['recommended_action']
            repair_record = self.auto_repairer.repair(fault, recommended_action)

            repairs.append({
                'fault': asdict(fault),
                'diagnosis': diagnosis,
                'repair': asdict(repair_record),
            })

            # 记录事件
            self.incident_history.append({
                'component': component,
                'fault_type': fault.fault_type.value,
                'severity': fault.severity.value,
                'action': recommended_action.value,
                'success': repair_record.success,
                'timestamp': time.time(),
            })

        self._save()

        return {
            'health': health_check.status.value,
            'faults_detected': len(faults),
            'repairs': repairs,
        }

    def get_system_health(self) -> dict:
        """获取系统健康状态"""
        return self.health_monitor.get_overall_health()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_incidents': len(self.incident_history),
            'repair_stats': self.auto_repairer.get_repair_stats(),
            'active_faults': len(self.fault_detector.get_active_faults()),
            'system_health': self.get_system_health(),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🔧 自愈系统报告")
        report.append("=" * 50)

        report.append(f"\n系统健康: {stats['system_health']['status']}")
        report.append(f"总事件数: {stats['total_incidents']}")
        report.append(f"活跃故障: {stats['active_faults']}")
        report.append(f"修复成功率: {stats['repair_stats']['success_rate']:.0%}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = SelfHealingEngine("test_self_healing")

    # 模拟监控
    print("=== 组件监控 ===")
    components = [
        ("api_server", {'error_rate': 0.05, 'response_time': 0.5, 'memory_usage': 0.6}),
        ("database", {'error_rate': 0.15, 'response_time': 2.0, 'memory_usage': 0.8}),
        ("cache", {'error_rate': 0.01, 'response_time': 0.1, 'memory_usage': 0.95}),
    ]

    for component, metrics in components:
        result = engine.monitor_component(component, metrics)
        print(f"\n{component}:")
        print(f"  健康: {result['health']}")
        print(f"  故障: {result['faults_detected']}")
        if result['repairs']:
            for repair in result['repairs']:
                print(f"  修复: {repair['repair']['action']} - {'成功' if repair['repair']['success'] else '失败'}")

    # 报告
    print("\n" + engine.generate_report())