"""
权限控制 - 计算机操作的权限管理和安全控制

确保AI操作计算机时的安全性
"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class Permission(Enum):
    # 文件操作
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    FILE_EXECUTE = "file_execute"

    # 进程操作
    PROCESS_START = "process_start"
    PROCESS_STOP = "process_stop"
    PROCESS_LIST = "process_list"

    # 网络操作
    NETWORK_REQUEST = "network_request"
    NETWORK_LISTEN = "network_listen"

    # 桌面操作
    MOUSE_CLICK = "mouse_click"
    KEYBOARD_INPUT = "keyboard_input"
    SCREENSHOT = "screenshot"
    CLIPBOARD = "clipboard"

    # 浏览器
    BROWSER_OPEN = "browser_open"
    BROWSER_NAVIGATE = "browser_navigate"

    # 系统
    SYSTEM_COMMAND = "system_command"
    REGISTRY_WRITE = "registry_write"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PermissionRule:
    permission: str
    granted: bool = True
    risk_level: str = "low"
    requires_confirmation: bool = False
    allowed_targets: List[str] = field(default_factory=list)
    denied_targets: List[str] = field(default_factory=list)
    max_per_hour: int = 0  # 0=无限制
    description: str = ""


@dataclass
class AuditEntry:
    entry_id: str
    permission: str
    action: str
    target: str = ""
    granted: bool = True
    reason: str = ""
    timestamp: float = 0.0
    risk_level: str = "low"


@dataclass
class SandboxConfig:
    enabled: bool = True
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    denied_commands: List[str] = field(default_factory=list)
    max_file_size_mb: int = 100
    allow_network: bool = True
    allow_process_start: bool = True


class PermissionControlEngine:
    """权限控制引擎"""

    def __init__(self, storage_dir: str = "data/permissions"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.rules: Dict[str, PermissionRule] = {}
        self.audit_log: List[AuditEntry] = []
        self.confirmation_callbacks: Dict[str, Callable] = {}
        self.sandbox = SandboxConfig()

        self._init_default_rules()
        self._load()

    def _init_default_rules(self):
        """初始化默认规则"""
        defaults = {
            Permission.FILE_READ.value: PermissionRule(
                permission=Permission.FILE_READ.value,
                granted=True, risk_level=RiskLevel.LOW.value,
                description="读取文件",
            ),
            Permission.FILE_WRITE.value: PermissionRule(
                permission=Permission.FILE_WRITE.value,
                granted=True, risk_level=RiskLevel.MEDIUM.value,
                requires_confirmation=False,
                denied_targets=["/etc", "/System", "C:\\Windows"],
                description="写入文件",
            ),
            Permission.FILE_DELETE.value: PermissionRule(
                permission=Permission.FILE_DELETE.value,
                granted=True, risk_level=RiskLevel.HIGH.value,
                requires_confirmation=True,
                denied_targets=["/etc", "/System", "C:\\Windows", "C:\\Program Files"],
                description="删除文件",
            ),
            Permission.PROCESS_START.value: PermissionRule(
                permission=Permission.PROCESS_START.value,
                granted=True, risk_level=RiskLevel.MEDIUM.value,
                requires_confirmation=False,
                denied_targets=["rm -rf", "format", "del /f /s /q"],
                description="启动进程",
            ),
            Permission.SYSTEM_COMMAND.value: PermissionRule(
                permission=Permission.SYSTEM_COMMAND.value,
                granted=True, risk_level=RiskLevel.HIGH.value,
                requires_confirmation=True,
                denied_targets=["rm -rf /", "format c:", "shutdown", "reboot"],
                description="系统命令",
            ),
            Permission.MOUSE_CLICK.value: PermissionRule(
                permission=Permission.MOUSE_CLICK.value,
                granted=True, risk_level=RiskLevel.LOW.value,
                description="鼠标点击",
            ),
            Permission.KEYBOARD_INPUT.value: PermissionRule(
                permission=Permission.KEYBOARD_INPUT.value,
                granted=True, risk_level=RiskLevel.MEDIUM.value,
                description="键盘输入",
            ),
            Permission.SCREENSHOT.value: PermissionRule(
                permission=Permission.SCREENSHOT.value,
                granted=True, risk_level=RiskLevel.LOW.value,
                description="截图",
            ),
            Permission.NETWORK_REQUEST.value: PermissionRule(
                permission=Permission.NETWORK_REQUEST.value,
                granted=True, risk_level=RiskLevel.MEDIUM.value,
                description="网络请求",
            ),
            Permission.BROWSER_NAVIGATE.value: PermissionRule(
                permission=Permission.BROWSER_NAVIGATE.value,
                granted=True, risk_level=RiskLevel.LOW.value,
                description="浏览器导航",
            ),
        }
        for k, v in defaults.items():
            if k not in self.rules:
                self.rules[k] = v

    def _load(self):
        path = os.path.join(self.storage_dir, "permission_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("rules", {}).items():
                    self.rules[k] = PermissionRule(**v)
                self.audit_log = [AuditEntry(**e) for e in data.get("audit_log", [])]
                sandbox_data = data.get("sandbox", {})
                if sandbox_data:
                    self.sandbox = SandboxConfig(**sandbox_data)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "permission_data.json")
        data = {
            "rules": {k: asdict(v) for k, v in self.rules.items()},
            "audit_log": [asdict(e) for e in self.audit_log[-5000:]],
            "sandbox": asdict(self.sandbox),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def check_permission(self, permission: str, target: str = "",
                         auto_log: bool = True) -> Dict[str, Any]:
        """检查权限"""
        rule = self.rules.get(permission)
        if not rule:
            return {"allowed": False, "reason": f"未知权限: {permission}"}

        # 基础检查
        if not rule.granted:
            result = {"allowed": False, "reason": "权限未授予"}
            if auto_log:
                self._log_audit(permission, "check", target, False, "权限未授予", rule.risk_level)
            return result

        # 黑名单检查
        for denied in rule.denied_targets:
            if denied and denied.lower() in target.lower():
                result = {"allowed": False, "reason": f"目标在黑名单中: {denied}"}
                if auto_log:
                    self._log_audit(permission, "check", target, False, result["reason"], rule.risk_level)
                return result

        # 沙箱检查
        if self.sandbox.enabled:
            sandbox_check = self._check_sandbox(permission, target)
            if not sandbox_check["allowed"]:
                if auto_log:
                    self._log_audit(permission, "check", target, False,
                                   sandbox_check["reason"], rule.risk_level)
                return sandbox_check

        # 需要确认
        if rule.requires_confirmation:
            result = {
                "allowed": True,
                "needs_confirmation": True,
                "risk_level": rule.risk_level,
                "reason": f"操作需要确认 (风险: {rule.risk_level})",
            }
        else:
            result = {"allowed": True, "risk_level": rule.risk_level}

        if auto_log:
            self._log_audit(permission, "check", target, True, "", rule.risk_level)

        return result

    def _check_sandbox(self, permission: str, target: str) -> Dict[str, Any]:
        """沙箱检查"""
        # 路径检查
        if permission in [Permission.FILE_READ.value, Permission.FILE_WRITE.value,
                          Permission.FILE_DELETE.value]:
            for denied in self.sandbox.denied_paths:
                if target.startswith(denied):
                    return {"allowed": False, "reason": f"沙箱禁止访问: {denied}"}

        # 命令检查
        if permission == Permission.SYSTEM_COMMAND.value:
            for denied in self.sandbox.denied_commands:
                if denied.lower() in target.lower():
                    return {"allowed": False, "reason": f"沙箱禁止命令: {denied}"}

        return {"allowed": True}

    def _log_audit(self, permission: str, action: str, target: str,
                   granted: bool, reason: str, risk_level: str):
        """记录审计"""
        entry = AuditEntry(
            entry_id=hashlib.md5(f"{permission}_{time.time()}".encode()).hexdigest()[:12],
            permission=permission, action=action,
            target=target[:200], granted=granted,
            reason=reason, risk_level=risk_level,
            timestamp=time.time(),
        )
        self.audit_log.append(entry)

    def grant_permission(self, permission: str) -> bool:
        """授予权限"""
        if permission in self.rules:
            self.rules[permission].granted = True
            self._save()
            return True
        return False

    def revoke_permission(self, permission: str) -> bool:
        """撤销权限"""
        if permission in self.rules:
            self.rules[permission].granted = False
            self._save()
            return True
        return False

    def set_rule(self, permission: str, granted: bool = True,
                 risk_level: str = "low", requires_confirmation: bool = False,
                 denied_targets: List[str] = None):
        """设置规则"""
        self.rules[permission] = PermissionRule(
            permission=permission, granted=granted,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            denied_targets=denied_targets or [],
        )
        self._save()

    def confirm_action(self, entry_id: str, approved: bool) -> bool:
        """确认操作"""
        # 实际应用中会触发回调
        return approved

    def update_sandbox(self, **kwargs):
        """更新沙箱配置"""
        for key, value in kwargs.items():
            if hasattr(self.sandbox, key):
                setattr(self.sandbox, key, value)
        self._save()

    def get_audit_log(self, limit: int = 100,
                      permission: str = "") -> List[Dict[str, Any]]:
        """获取审计日志"""
        logs = self.audit_log
        if permission:
            logs = [e for e in logs if e.permission == permission]
        return [asdict(e) for e in sorted(logs, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def get_denied_actions(self) -> List[Dict[str, Any]]:
        """获取被拒绝的操作"""
        return [asdict(e) for e in self.audit_log if not e.granted][-50:]

    def generate_report(self) -> Dict[str, Any]:
        """生成安全报告"""
        total_checks = len(self.audit_log)
        denied = sum(1 for e in self.audit_log if not e.granted)
        high_risk = sum(1 for e in self.audit_log if e.risk_level in ["high", "critical"])

        permission_counts = defaultdict(int)
        for e in self.audit_log:
            permission_counts[e.permission] += 1

        return {
            "total_checks": total_checks,
            "denied_actions": denied,
            "denial_rate": round(denied / max(total_checks, 1), 4),
            "high_risk_operations": high_risk,
            "permission_distribution": dict(permission_counts),
            "sandbox_enabled": self.sandbox.enabled,
            "rules_count": len(self.rules),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "rules_count": len(self.rules),
            "audit_entries": len(self.audit_log),
            "sandbox_enabled": self.sandbox.enabled,
        }


if __name__ == "__main__":
    print("=== 权限控制测试 ===")
    engine = PermissionControlEngine()

    # 检查权限
    checks = [
        ("file_read", "/home/user/doc.txt"),
        ("file_write", "/home/user/output.txt"),
        ("file_delete", "/etc/passwd"),
        ("system_command", "ls -la"),
        ("system_command", "rm -rf /"),
        ("mouse_click", "100,200"),
        ("screenshot", ""),
    ]

    for perm, target in checks:
        result = engine.check_permission(perm, target)
        status = "✅" if result["allowed"] else "❌"
        print(f"  {status} {perm} ({target}): {result.get('reason', 'OK')}")

    # 审计日志
    denied = engine.get_denied_actions()
    print(f"\n被拒绝的操作: {len(denied)}")

    # 安全报告
    report = engine.generate_report()
    print(f"\n安全报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
