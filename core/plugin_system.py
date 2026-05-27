"""插件系统 - 插件注册/加载/卸载、生命周期管理"""

import json
import os
import time
import hashlib
import importlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable


class PluginStatus(Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class PluginType(Enum):
    TOOL = "tool"
    TRANSFORM = "transform"
    HANDLER = "handler"
    MIDDLEWARE = "middleware"
    EXTENSION = "extension"


@dataclass
class Plugin:
    plugin_id: str
    name: str
    version: str = "1.0.0"
    plugin_type: str = "extension"
    description: str = ""
    author: str = ""
    status: str = "registered"
    entry_point: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    hooks: Dict[str, str] = field(default_factory=dict)
    created_at: float = 0.0
    loaded_at: float = 0.0
    error: str = ""


@dataclass
class PluginHook:
    hook_name: str
    plugin_id: str
    callback: Any = None
    priority: int = 0


class PluginSystemEngine:
    """插件系统引擎"""

    def __init__(self, storage_dir: str = "data/plugins"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[PluginHook]] = {}
        self.plugin_callbacks: Dict[str, Dict[str, Callable]] = {}
        self.lifecycle_callbacks: Dict[str, Dict[str, Callable]] = {}

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "plugin_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("plugins", {}).items():
                    self.plugins[k] = Plugin(**v)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "plugin_data.json")
        data = {
            "plugins": {k: asdict(v) for k, v in self.plugins.items()},
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register(self, name: str, version: str = "1.0.0",
                 plugin_type: str = "extension", description: str = "",
                 author: str = "", entry_point: str = "",
                 config: Dict[str, Any] = None,
                 dependencies: List[str] = None) -> str:
        """注册插件"""
        plugin_id = hashlib.md5(f"{name}_{version}_{time.time()}".encode()).hexdigest()[:12]

        # 检查依赖
        for dep in (dependencies or []):
            if dep not in self.plugins:
                return ""

        plugin = Plugin(
            plugin_id=plugin_id, name=name, version=version,
            plugin_type=plugin_type, description=description,
            author=author, entry_point=entry_point,
            config=config or {}, dependencies=dependencies or [],
            created_at=time.time(),
        )
        self.plugins[plugin_id] = plugin
        self._save()
        return plugin_id

    def load(self, plugin_id: str) -> bool:
        """加载插件"""
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        # 检查依赖是否已加载
        for dep in plugin.dependencies:
            if dep not in self.plugins or self.plugins[dep].status != PluginStatus.ACTIVE.value:
                plugin.status = PluginStatus.ERROR.value
                plugin.error = f"依赖未加载: {dep}"
                self._save()
                return False

        # 生命周期回调
        on_load = self.lifecycle_callbacks.get(plugin_id, {}).get("on_load")
        if on_load:
            try:
                on_load(plugin.config)
            except Exception as e:
                plugin.status = PluginStatus.ERROR.value
                plugin.error = str(e)
                self._save()
                return False

        plugin.status = PluginStatus.ACTIVE.value
        plugin.loaded_at = time.time()
        self._save()
        return True

    def unload(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        # 检查是否有其他插件依赖此插件
        for other in self.plugins.values():
            if plugin_id in other.dependencies and other.status == PluginStatus.ACTIVE.value:
                return False

        # 生命周期回调
        on_unload = self.lifecycle_callbacks.get(plugin_id, {}).get("on_unload")
        if on_unload:
            try:
                on_unload()
            except Exception:
                pass

        plugin.status = PluginStatus.DISABLED.value
        self._save()
        return True

    def enable(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].status = PluginStatus.ACTIVE.value
            self._save()
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].status = PluginStatus.DISABLED.value
            self._save()
            return True
        return False

    def register_hook(self, hook_name: str, plugin_id: str,
                      callback: Callable, priority: int = 0):
        """注册钩子"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []

        hook = PluginHook(
            hook_name=hook_name,
            plugin_id=plugin_id,
            callback=callback,
            priority=priority,
        )
        self.hooks[hook_name].append(hook)
        self.hooks[hook_name].sort(key=lambda h: h.priority, reverse=True)

    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        results = []
        for hook in self.hooks.get(hook_name, []):
            plugin = self.plugins.get(hook.plugin_id)
            if plugin and plugin.status == PluginStatus.ACTIVE.value and hook.callback:
                try:
                    result = hook.callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        return results

    def register_lifecycle(self, plugin_id: str, event: str, callback: Callable):
        """注册生命周期回调"""
        if plugin_id not in self.lifecycle_callbacks:
            self.lifecycle_callbacks[plugin_id] = {}
        self.lifecycle_callbacks[plugin_id][event] = callback

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """获取插件信息"""
        if plugin_id in self.plugins:
            return asdict(self.plugins[plugin_id])
        return None

    def list_plugins(self, status: str = "") -> List[Dict[str, Any]]:
        """列出插件"""
        plugins = self.plugins.values()
        if status:
            plugins = [p for p in plugins if p.status == status]
        return [asdict(p) for p in plugins]

    def get_hooks(self) -> Dict[str, List[str]]:
        """获取所有钩子"""
        return {
            hook_name: [h.plugin_id for h in hooks]
            for hook_name, hooks in self.hooks.items()
        }

    def generate_report(self) -> Dict[str, Any]:
        status_counts = {}
        for p in self.plugins.values():
            status_counts[p.status] = status_counts.get(p.status, 0) + 1

        return {
            "total_plugins": len(self.plugins),
            "active_plugins": sum(1 for p in self.plugins.values() if p.status == "active"),
            "total_hooks": len(self.hooks),
            "status_distribution": status_counts,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "plugins_count": len(self.plugins),
            "active_count": sum(1 for p in self.plugins.values() if p.status == "active"),
            "hooks_count": len(self.hooks),
        }


if __name__ == "__main__":
    print("=== 插件系统测试 ===")
    engine = PluginSystemEngine()

    # 注册插件
    p1 = engine.register("数据分析", "1.0.0", "tool", "数据分析插件")
    p2 = engine.register("可视化", "1.2.0", "extension", "数据可视化插件")
    p3 = engine.register("导出", "1.0.0", "handler", "数据导出插件", dependencies=[p1])
    print(f"插件: {p1}, {p2}, {p3}")

    # 加载
    print(f"加载数据分析: {engine.load(p1)}")
    print(f"加载导出(依赖): {engine.load(p3)}")

    # 注册钩子
    engine.register_hook("on_data_ready", p1, lambda data: f"处理了{len(data)}条数据")
    engine.register_hook("on_export", p3, lambda fmt: f"导出为{fmt}格式")

    # 触发钩子
    results = engine.trigger_hook("on_data_ready", [1, 2, 3, 4, 5])
    print(f"钩子结果: {results}")

    # 列出插件
    plugins = engine.list_plugins()
    print(f"\n所有插件:")
    for p in plugins:
        print(f"  [{p['status']}] {p['name']} v{p['version']}")

    report = engine.generate_report()
    print(f"\n插件报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
