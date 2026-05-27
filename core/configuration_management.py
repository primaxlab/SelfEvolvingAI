"""配置管理系统 - 配置存储、版本控制、热更新、环境管理"""

import json
import os
import time
import hashlib
import copy
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict


class ConfigScope(Enum):
    """配置作用域"""
    GLOBAL = "global"
    ENVIRONMENT = "environment"
    MODULE = "module"
    USER = "user"
    SESSION = "session"


class ConfigFormat(Enum):
    """配置格式"""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"
    PROPERTIES = "properties"


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    ROLLBACK = "rollback"


@dataclass
class ConfigEntry:
    """配置项"""
    key: str
    value: Any
    scope: str = "global"
    environment: str = "default"
    description: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    created_by: str = "system"
    is_secret: bool = False
    tags: List[str] = field(default_factory=list)
    validation_rule: str = ""


@dataclass
class ConfigVersion:
    """配置版本"""
    version_id: str
    config_key: str
    old_value: Any
    new_value: Any
    change_type: str
    timestamp: float
    changed_by: str = "system"
    reason: str = ""


@dataclass
class Environment:
    """环境配置"""
    env_id: str
    name: str
    description: str = ""
    parent_env: str = ""
    is_active: bool = True
    created_at: float = 0.0
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigSchema:
    """配置模式"""
    schema_id: str
    key_pattern: str
    value_type: str
    default_value: Any = None
    required: bool = False
    description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigWatcher:
    """配置监听器"""
    watcher_id: str
    config_key: str
    callback_name: str
    is_active: bool = True
    created_at: float = 0.0


class ConfigurationManager:
    """配置管理引擎"""

    def __init__(self, storage_dir: str = "data/configuration"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.configs: Dict[str, ConfigEntry] = {}
        self.versions: List[ConfigVersion] = []
        self.environments: Dict[str, Environment] = {}
        self.schemas: Dict[str, ConfigSchema] = {}
        self.watchers: Dict[str, List[ConfigWatcher]] = defaultdict(list)
        self.active_environment: str = "default"

        self._init_default_environment()
        self._load()

    def _init_default_environment(self):
        """初始化默认环境"""
        if "default" not in self.environments:
            self.environments["default"] = Environment(
                env_id="default",
                name="默认环境",
                description="默认配置环境",
                is_active=True,
                created_at=time.time()
            )

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "config_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("configs", {}).items():
                    self.configs[k] = ConfigEntry(**v)
                self.versions = [ConfigVersion(**v) for v in data.get("versions", [])]
                for k, v in data.get("environments", {}).items():
                    self.environments[k] = Environment(**v)
                for k, v in data.get("schemas", {}).items():
                    self.schemas[k] = ConfigSchema(**v)
                self.active_environment = data.get("active_environment", "default")
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "config_data.json")
        data = {
            "configs": {k: asdict(v) for k, v in self.configs.items()},
            "versions": [asdict(v) for v in self.versions[-5000:]],
            "environments": {k: asdict(v) for k, v in self.environments.items()},
            "schemas": {k: asdict(v) for k, v in self.schemas.items()},
            "active_environment": self.active_environment
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_config(self, key: str, value: Any, scope: str = "global",
                   environment: str = "", description: str = "",
                   is_secret: bool = False, tags: List[str] = None) -> bool:
        """设置配置"""
        env = environment or self.active_environment
        config_key = f"{env}:{scope}:{key}"

        old_value = None
        change_type = ChangeType.CREATE.value

        if config_key in self.configs:
            old_value = self.configs[config_key].value
            change_type = ChangeType.UPDATE.value

        now = time.time()
        entry = ConfigEntry(
            key=key,
            value=value,
            scope=scope,
            environment=env,
            description=description,
            created_at=now if change_type == ChangeType.CREATE.value else self.configs.get(config_key, ConfigEntry(key="", value="")).created_at,
            updated_at=now,
            is_secret=is_secret,
            tags=tags or []
        )
        self.configs[config_key] = entry

        # 记录版本
        version = ConfigVersion(
            version_id=hashlib.md5(f"{config_key}_{now}".encode()).hexdigest()[:12],
            config_key=config_key,
            old_value=old_value,
            new_value=value,
            change_type=change_type,
            timestamp=now
        )
        self.versions.append(version)

        # 通知监听器
        self._notify_watchers(config_key, old_value, value)

        self._save()
        return True

    def get_config(self, key: str, scope: str = "global",
                   environment: str = "", default: Any = None) -> Any:
        """获取配置"""
        env = environment or self.active_environment
        config_key = f"{env}:{scope}:{key}"

        if config_key in self.configs:
            return self.configs[config_key].value

        # 回退到默认环境
        default_key = f"default:{scope}:{key}"
        if default_key in self.configs:
            return self.configs[default_key].value

        return default

    def get_all_configs(self, scope: str = "", environment: str = "") -> Dict[str, Any]:
        """获取所有配置"""
        env = environment or self.active_environment
        result = {}
        for k, v in self.configs.items():
            if (not scope or v.scope == scope) and (not environment or v.environment == env):
                result[v.key] = v.value
        return result

    def delete_config(self, key: str, scope: str = "global",
                      environment: str = "") -> bool:
        """删除配置"""
        env = environment or self.active_environment
        config_key = f"{env}:{scope}:{key}"

        if config_key in self.configs:
            old_value = self.configs[config_key].value
            del self.configs[config_key]

            version = ConfigVersion(
                version_id=hashlib.md5(f"{config_key}_{time.time()}".encode()).hexdigest()[:12],
                config_key=config_key,
                old_value=old_value,
                new_value=None,
                change_type=ChangeType.DELETE.value,
                timestamp=time.time()
            )
            self.versions.append(version)
            self._save()
            return True
        return False

    def create_environment(self, name: str, description: str = "",
                           parent_env: str = "") -> str:
        """创建环境"""
        env_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        env = Environment(
            env_id=env_id,
            name=name,
            description=description,
            parent_env=parent_env,
            is_active=True,
            created_at=time.time()
        )
        self.environments[env_id] = env
        self._save()
        return env_id

    def switch_environment(self, env_id: str) -> bool:
        """切换环境"""
        if env_id in self.environments:
            self.active_environment = env_id
            self._save()
            return True
        return False

    def define_schema(self, key_pattern: str, value_type: str,
                      default_value: Any = None, required: bool = False,
                      description: str = "", constraints: Dict[str, Any] = None) -> str:
        """定义配置模式"""
        schema_id = hashlib.md5(f"{key_pattern}_{time.time()}".encode()).hexdigest()[:12]
        schema = ConfigSchema(
            schema_id=schema_id,
            key_pattern=key_pattern,
            value_type=value_type,
            default_value=default_value,
            required=required,
            description=description,
            constraints=constraints or {}
        )
        self.schemas[schema_id] = schema
        self._save()
        return schema_id

    def validate_config(self, key: str, value: Any) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []

        for schema in self.schemas.values():
            if self._match_pattern(schema.key_pattern, key):
                # 类型检查
                expected_type = schema.value_type
                actual_type = type(value).__name__

                type_map = {
                    "str": str, "string": str,
                    "int": int, "integer": int,
                    "float": float, "number": (int, float),
                    "bool": boolean, "boolean": bool,
                    "list": list, "array": list,
                    "dict": dict, "object": dict
                }

                expected = type_map.get(expected_type)
                if expected and not isinstance(value, expected):
                    errors.append(f"类型不匹配: 期望 {expected_type}, 实际 {actual_type}")

                # 约束检查
                constraints = schema.constraints
                if "min" in constraints and value < constraints["min"]:
                    errors.append(f"值不能小于 {constraints['min']}")
                if "max" in constraints and value > constraints["max"]:
                    errors.append(f"值不能大于 {constraints['max']}")
                if "min_length" in constraints and len(str(value)) < constraints["min_length"]:
                    errors.append(f"长度不能小于 {constraints['min_length']}")
                if "max_length" in constraints and len(str(value)) > constraints["max_length"]:
                    errors.append(f"长度不能大于 {constraints['max_length']}")
                if "enum" in constraints and value not in constraints["enum"]:
                    errors.append(f"值必须是 {constraints['enum']} 之一")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _match_pattern(self, pattern: str, key: str) -> bool:
        """模式匹配"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        return pattern == key

    def add_watcher(self, config_key: str, callback_name: str) -> str:
        """添加配置监听器"""
        watcher_id = hashlib.md5(f"{config_key}_{callback_name}_{time.time()}".encode()).hexdigest()[:12]
        watcher = ConfigWatcher(
            watcher_id=watcher_id,
            config_key=config_key,
            callback_name=callback_name,
            is_active=True,
            created_at=time.time()
        )
        self.watchers[config_key].append(watcher)
        self._save()
        return watcher_id

    def _notify_watchers(self, config_key: str, old_value: Any, new_value: Any):
        """通知监听器"""
        for watcher in self.watchers.get(config_key, []):
            if watcher.is_active:
                # 实际应用中会调用回调函数
                pass

    def get_version_history(self, config_key: str = None,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """获取版本历史"""
        versions = self.versions
        if config_key:
            versions = [v for v in versions if v.config_key == config_key]
        return [asdict(v) for v in sorted(versions, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def rollback(self, config_key: str, version_id: str) -> bool:
        """回滚配置"""
        for version in self.versions:
            if version.version_id == version_id and version.config_key == config_key:
                if version.old_value is not None:
                    parts = config_key.split(":")
                    if len(parts) == 3:
                        env, scope, key = parts
                        self.set_config(key, version.old_value, scope, env,
                                        reason=f"回滚到版本 {version_id}")
                        return True
        return False

    def merge_configs(self, base_env: str, overlay_env: str) -> Dict[str, Any]:
        """合并配置"""
        base_configs = self.get_all_configs(environment=base_env)
        overlay_configs = self.get_all_configs(environment=overlay_env)

        merged = copy.deepcopy(base_configs)
        merged.update(overlay_configs)
        return merged

    def export_configs(self, environment: str = "",
                       scope: str = "", format: str = "json") -> str:
        """导出配置"""
        configs = self.get_all_configs(scope=scope, environment=environment)

        if format == "json":
            return json.dumps(configs, indent=2, ensure_ascii=False)
        elif format == "env":
            lines = []
            for k, v in configs.items():
                env_key = k.upper().replace(".", "_")
                lines.append(f"{env_key}={v}")
            return "\n".join(lines)
        elif format == "properties":
            lines = []
            for k, v in configs.items():
                lines.append(f"{k}={v}")
            return "\n".join(lines)
        return ""

    def import_configs(self, data: str, format: str = "json",
                       environment: str = "", scope: str = "global") -> int:
        """导入配置"""
        count = 0

        if format == "json":
            try:
                configs = json.loads(data)
                for k, v in configs.items():
                    self.set_config(k, v, scope, environment)
                    count += 1
            except json.JSONDecodeError:
                pass
        elif format == "env":
            for line in data.strip().split("\n"):
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    self.set_config(k.lower().replace("_", "."), v, scope, environment)
                    count += 1

        return count

    def search_configs(self, query: str) -> List[Dict[str, Any]]:
        """搜索配置"""
        results = []
        query_lower = query.lower()

        for k, v in self.configs.items():
            if (query_lower in v.key.lower() or
                query_lower in str(v.value).lower() or
                query_lower in v.description.lower()):
                results.append({
                    "key": v.key,
                    "value": v.value,
                    "scope": v.scope,
                    "environment": v.environment,
                    "description": v.description
                })

        return results

    def generate_report(self) -> Dict[str, Any]:
        """生成配置报告"""
        scope_counts = defaultdict(int)
        env_counts = defaultdict(int)

        for v in self.configs.values():
            scope_counts[v.scope] += 1
            env_counts[v.environment] += 1

        return {
            "total_configs": len(self.configs),
            "total_versions": len(self.versions),
            "total_environments": len(self.environments),
            "total_schemas": len(self.schemas),
            "active_environment": self.active_environment,
            "scope_distribution": dict(scope_counts),
            "environment_distribution": dict(env_counts)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "configs_count": len(self.configs),
            "versions_count": len(self.versions),
            "environments_count": len(self.environments),
            "schemas_count": len(self.schemas),
            "watchers_count": sum(len(w) for w in self.watchers.values()),
            "active_environment": self.active_environment
        }


if __name__ == "__main__":
    engine = ConfigurationManager()
    print("=== 配置管理系统测试 ===")

    # 设置配置
    engine.set_config("app.name", "SelfEvolvingAI", description="应用名称")
    engine.set_config("app.version", "1.0.0", description="应用版本")
    engine.set_config("database.host", "localhost", description="数据库主机")
    engine.set_config("database.port", 5432, description="数据库端口")
    engine.set_config("api.secret", "xxx123", is_secret=True, description="API密钥")
    print("配置设置完成")

    # 获取配置
    name = engine.get_config("app.name")
    print(f"应用名称: {name}")

    # 创建环境
    dev_env = engine.create_environment("开发环境", "用于开发测试")
    prod_env = engine.create_environment("生产环境", "正式运行环境")
    print(f"创建环境: dev={dev_env}, prod={prod_env}")

    # 环境切换
    engine.switch_environment(dev_env)
    engine.set_config("debug.mode", True, environment=dev_env)
    print(f"当前环境: {engine.active_environment}")

    # 定义模式
    schema_id = engine.define_schema(
        "database.port", "int",
        default_value=5432,
        constraints={"min": 1, "max": 65535},
        description="数据库端口"
    )
    print(f"模式定义: {schema_id}")

    # 验证配置
    valid = engine.validate_config("database.port", 5432)
    invalid = engine.validate_config("database.port", 99999)
    print(f"验证 5432: {valid['valid']}, 验证 99999: {invalid['valid']}")

    # 版本历史
    engine.set_config("app.version", "1.1.0")
    history = engine.get_version_history("default:global:app.version")
    print(f"版本历史: {len(history)} 条记录")

    # 搜索
    results = engine.search_configs("database")
    print(f"搜索 'database': {len(results)} 个结果")

    # 导出
    exported = engine.export_configs(format="env")
    print(f"导出配置:\n{exported[:200]}...")

    # 报告
    report = engine.generate_report()
    print(f"\n配置报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    print("\n测试完成!")
