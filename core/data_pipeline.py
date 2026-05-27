"""数据管道 - ETL流程、数据清洗、数据转换"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class PipelineStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class TransformType(Enum):
    FILTER = "filter"
    MAP = "map"
    AGGREGATE = "aggregate"
    JOIN = "join"
    SORT = "sort"
    DEDUPLICATE = "deduplicate"
    RENAME = "rename"
    CAST = "cast"
    FILL_NULL = "fill_null"
    CUSTOM = "custom"


@dataclass
class PipelineStep:
    step_id: str
    name: str
    transform_type: str = "map"
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class Pipeline:
    pipeline_id: str
    name: str
    steps: List[PipelineStep] = field(default_factory=list)
    status: str = "draft"
    created_at: float = 0.0
    last_run: float = 0.0
    run_count: int = 0
    last_error: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineRun:
    run_id: str
    pipeline_id: str
    started_at: float = 0.0
    completed_at: float = 0.0
    duration: float = 0.0
    status: str = "running"
    input_count: int = 0
    output_count: int = 0
    error: str = ""
    step_results: List[Dict[str, Any]] = field(default_factory=list)


class DataPipelineEngine:
    """数据管道引擎"""

    def __init__(self, storage_dir: str = "data/pipeline"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.pipelines: Dict[str, Pipeline] = {}
        self.runs: List[PipelineRun] = []
        self.transforms: Dict[str, Callable] = {}

        self._register_default_transforms()
        self._load()

    def _register_default_transforms(self):
        """注册默认转换函数"""
        self.transforms = {
            "filter": lambda data, config: [d for d in data if self._eval_condition(d, config.get("condition", {}))],
            "map": lambda data, config: [self._apply_mapping(d, config.get("mapping", {})) for d in data],
            "sort": lambda data, config: sorted(data, key=lambda x: x.get(config.get("key", ""), 0), reverse=config.get("reverse", False)),
            "deduplicate": lambda data, config: self._deduplicate(data, config.get("key", "")),
            "flatten": lambda data, config: [item for sublist in data for item in (sublist if isinstance(sublist, list) else [sublist])],
        }

    def _eval_condition(self, item: dict, condition: dict) -> bool:
        for key, value in condition.items():
            if key not in item:
                return False
            if isinstance(value, dict):
                op = value.get("op", "eq")
                val = value.get("value")
                if op == "eq" and item[key] != val:
                    return False
                if op == "gt" and item[key] <= val:
                    return False
                if op == "lt" and item[key] >= val:
                    return False
                if op == "contains" and val not in str(item[key]):
                    return False
            elif item[key] != value:
                return False
        return True

    def _apply_mapping(self, item: dict, mapping: dict) -> dict:
        result = dict(item)
        for new_key, source in mapping.items():
            if isinstance(source, str) and source in item:
                result[new_key] = item[source]
            elif isinstance(source, dict) and "value" in source:
                result[new_key] = source["value"]
        return result

    def _deduplicate(self, data: list, key: str) -> list:
        seen = set()
        result = []
        for item in data:
            k = item.get(key, str(item)) if key else str(item)
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result

    def _load(self):
        path = os.path.join(self.storage_dir, "pipeline_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("pipelines", {}).items():
                    steps = [PipelineStep(**s) for s in v.pop("steps", [])]
                    self.pipelines[k] = Pipeline(steps=steps, **v)
                self.runs = [PipelineRun(**r) for r in data.get("runs", [])]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "pipeline_data.json")
        data = {
            "pipelines": {
                k: {**asdict(v), "steps": [asdict(s) for s in v.steps]}
                for k, v in self.pipelines.items()
            },
            "runs": [asdict(r) for r in self.runs[-1000:]],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_pipeline(self, name: str, steps: List[Dict[str, Any]] = None) -> str:
        """创建管道"""
        pipeline_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        pipeline_steps = []
        for i, step_config in enumerate(steps or []):
            step = PipelineStep(
                step_id=f"{pipeline_id}_s{i}",
                name=step_config.get("name", f"Step {i}"),
                transform_type=step_config.get("type", "map"),
                config=step_config.get("config", {}),
            )
            pipeline_steps.append(step)

        pipeline = Pipeline(
            pipeline_id=pipeline_id,
            name=name,
            steps=pipeline_steps,
            status=PipelineStatus.DRAFT.value,
            created_at=time.time(),
        )
        self.pipelines[pipeline_id] = pipeline
        self._save()
        return pipeline_id

    def add_step(self, pipeline_id: str, name: str, transform_type: str,
                 config: Dict[str, Any] = None) -> bool:
        """添加步骤"""
        if pipeline_id not in self.pipelines:
            return False
        pipeline = self.pipelines[pipeline_id]
        step = PipelineStep(
            step_id=f"{pipeline_id}_s{len(pipeline.steps)}",
            name=name,
            transform_type=transform_type,
            config=config or {},
        )
        pipeline.steps.append(step)
        self._save()
        return True

    def execute(self, pipeline_id: str, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行管道"""
        if pipeline_id not in self.pipelines:
            return {"error": "管道不存在"}

        pipeline = self.pipelines[pipeline_id]
        run_id = hashlib.md5(f"{pipeline_id}_{time.time()}".encode()).hexdigest()[:12]
        run = PipelineRun(
            run_id=run_id,
            pipeline_id=pipeline_id,
            started_at=time.time(),
            input_count=len(input_data),
        )

        pipeline.status = PipelineStatus.RUNNING.value
        current_data = input_data
        step_results = []

        for step in pipeline.steps:
            if not step.is_active:
                continue

            transform = self.transforms.get(step.transform_type)
            if not transform:
                step_results.append({
                    "step": step.name,
                    "status": "skipped",
                    "reason": f"未知转换: {step.transform_type}",
                })
                continue

            try:
                before_count = len(current_data)
                current_data = transform(current_data, step.config)
                after_count = len(current_data)

                step_results.append({
                    "step": step.name,
                    "status": "success",
                    "input": before_count,
                    "output": after_count,
                })
            except Exception as e:
                step_results.append({
                    "step": step.name,
                    "status": "failed",
                    "error": str(e),
                })
                run.status = PipelineStatus.FAILED.value
                run.error = str(e)
                pipeline.status = PipelineStatus.FAILED.value
                pipeline.last_error = str(e)
                break

        if run.status != PipelineStatus.FAILED.value:
            run.status = PipelineStatus.COMPLETED.value
            pipeline.status = PipelineStatus.COMPLETED.value

        run.completed_at = time.time()
        run.duration = run.completed_at - run.started_at
        run.output_count = len(current_data)
        run.step_results = step_results

        pipeline.last_run = time.time()
        pipeline.run_count += 1
        pipeline.stats = {
            "last_input": run.input_count,
            "last_output": run.output_count,
            "last_duration": run.duration,
        }

        self.runs.append(run)
        self._save()

        return {
            "run_id": run_id,
            "status": run.status,
            "input_count": run.input_count,
            "output_count": run.output_count,
            "duration": run.duration,
            "step_results": step_results,
            "output_data": current_data[:100],  # 只返回前100条
        }

    def register_transform(self, name: str, func: Callable):
        """注册自定义转换"""
        self.transforms[name] = func

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """获取管道"""
        if pipeline_id not in self.pipelines:
            return None
        p = self.pipelines[pipeline_id]
        return {
            "pipeline_id": p.pipeline_id,
            "name": p.name,
            "status": p.status,
            "steps": [{"name": s.name, "type": s.transform_type} for s in p.steps],
            "run_count": p.run_count,
            "stats": p.stats,
        }

    def get_run_history(self, pipeline_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取运行历史"""
        runs = self.runs
        if pipeline_id:
            runs = [r for r in runs if r.pipeline_id == pipeline_id]
        return [asdict(r) for r in sorted(runs, key=lambda x: x.started_at, reverse=True)[:limit]]

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        return {
            "total_pipelines": len(self.pipelines),
            "total_runs": len(self.runs),
            "active_pipelines": sum(1 for p in self.pipelines.values() if p.status != "draft"),
            "success_rate": sum(1 for r in self.runs if r.status == "completed") / max(len(self.runs), 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pipelines_count": len(self.pipelines),
            "runs_count": len(self.runs),
            "transforms_count": len(self.transforms),
        }


if __name__ == "__main__":
    print("=== 数据管道测试 ===")
    engine = DataPipelineEngine()

    # 创建管道
    pid = engine.create_pipeline("用户数据处理", [
        {"name": "过滤无效", "type": "filter", "config": {"condition": {"age": {"op": "gt", "value": 0}}}},
        {"name": "字段映射", "type": "map", "config": {"mapping": {"user_name": "name", "user_age": "age"}}},
        {"name": "排序", "type": "sort", "config": {"key": "user_age", "reverse": True}},
    ])
    print(f"管道: {pid}")

    # 测试数据
    data = [
        {"name": "Alice", "age": 30, "city": "Beijing"},
        {"name": "Bob", "age": 0, "city": "Shanghai"},
        {"name": "Charlie", "age": 25, "city": "Guangzhou"},
        {"name": "David", "age": 35, "city": "Shenzhen"},
    ]

    # 执行
    result = engine.execute(pid, data)
    print(f"\n执行结果:")
    print(f"  状态: {result['status']}")
    print(f"  输入: {result['input_count']}, 输出: {result['output_count']}")
    print(f"  耗时: {result['duration']:.3f}s")
    print(f"  输出数据: {result['output_data']}")

    report = engine.generate_report()
    print(f"\n管道报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
