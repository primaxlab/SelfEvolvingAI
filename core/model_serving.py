"""模型服务 - 模型注册、版本管理、A/B部署、推理路由"""

import json
import os
import time
import hashlib
import random
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class ModelStatus(Enum):
    REGISTERED = "registered"
    LOADING = "loading"
    READY = "ready"
    SERVING = "serving"
    FAILED = "failed"
    RETIRED = "retired"


class DeploymentStrategy(Enum):
    DIRECT = "direct"
    AB_TEST = "ab_test"
    CANARY = "canary"
    SHADOW = "shadow"


@dataclass
class Model:
    model_id: str
    name: str
    version: str = "1.0.0"
    status: str = "registered"
    framework: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    loaded_at: float = 0.0
    inference_count: int = 0
    avg_latency: float = 0.0
    error_count: int = 0


@dataclass
class Deployment:
    deployment_id: str
    model_id: str
    strategy: str = "direct"
    traffic_percent: float = 100.0
    is_active: bool = True
    created_at: float = 0.0


@dataclass
class InferenceRequest:
    request_id: str
    model_id: str
    input_data: Any = None
    output_data: Any = None
    latency: float = 0.0
    success: bool = True
    error: str = ""
    timestamp: float = 0.0


class ModelServingEngine:
    """模型服务引擎"""

    def __init__(self, storage_dir: str = "data/model_serving"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.models: Dict[str, Model] = {}
        self.deployments: Dict[str, Deployment] = {}
        self.inference_handlers: Dict[str, Callable] = {}
        self.request_log: List[InferenceRequest] = []

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "model_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("models", {}).items():
                    self.models[k] = Model(**v)
                for k, v in data.get("deployments", {}).items():
                    self.deployments[k] = Deployment(**v)
                self.request_log = [InferenceRequest(**r) for r in data.get("request_log", [])]
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "model_data.json")
        data = {
            "models": {k: asdict(v) for k, v in self.models.items()},
            "deployments": {k: asdict(v) for k, v in self.deployments.items()},
            "request_log": [asdict(r) for r in self.request_log[-10000:]],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register_model(self, name: str, version: str = "1.0.0",
                       framework: str = "", description: str = "",
                       config: Dict[str, Any] = None) -> str:
        """注册模型"""
        model_id = hashlib.md5(f"{name}_{version}_{time.time()}".encode()).hexdigest()[:12]
        model = Model(
            model_id=model_id, name=name, version=version,
            framework=framework, description=description,
            config=config or {},
            status=ModelStatus.REGISTERED.value,
            created_at=time.time(),
        )
        self.models[model_id] = model
        self._save()
        return model_id

    def load_model(self, model_id: str, handler: Callable = None) -> bool:
        """加载模型"""
        if model_id not in self.models:
            return False

        model = self.models[model_id]
        model.status = ModelStatus.LOADING.value

        if handler:
            self.inference_handlers[model_id] = handler

        model.status = ModelStatus.READY.value
        model.loaded_at = time.time()
        self._save()
        return True

    def deploy(self, model_id: str, strategy: str = "direct",
               traffic_percent: float = 100.0) -> str:
        """部署模型"""
        if model_id not in self.models:
            return ""

        deployment_id = hashlib.md5(f"{model_id}_{time.time()}".encode()).hexdigest()[:12]
        deployment = Deployment(
            deployment_id=deployment_id,
            model_id=model_id,
            strategy=strategy,
            traffic_percent=traffic_percent,
            created_at=time.time(),
        )
        self.deployments[deployment_id] = deployment
        self.models[model_id].status = ModelStatus.SERVING.value
        self._save()
        return deployment_id

    def predict(self, model_name: str, input_data: Any) -> Dict[str, Any]:
        """推理"""
        # 查找模型
        model = None
        for m in self.models.values():
            if m.name == model_name and m.status in [ModelStatus.READY.value, ModelStatus.SERVING.value]:
                model = m
                break

        if not model:
            return {"error": "模型不可用", "success": False}

        request_id = hashlib.md5(f"{model_name}_{time.time()}".encode()).hexdigest()[:12]
        start_time = time.time()

        # 执行推理
        handler = self.inference_handlers.get(model.model_id)
        if handler:
            try:
                output = handler(input_data)
                success = True
                error = ""
            except Exception as e:
                output = None
                success = False
                error = str(e)
        else:
            # 默认处理
            output = {"prediction": str(input_data)[:100], "model": model_name}
            success = True
            error = ""

        latency = time.time() - start_time

        # 记录
        request = InferenceRequest(
            request_id=request_id,
            model_id=model.model_id,
            input_data=str(input_data)[:200],
            output_data=str(output)[:200] if output else None,
            latency=latency,
            success=success,
            error=error,
            timestamp=time.time(),
        )
        self.request_log.append(request)

        # 更新模型统计
        model.inference_count += 1
        model.avg_latency = (model.avg_latency * (model.inference_count - 1) + latency) / model.inference_count
        if not success:
            model.error_count += 1

        self._save()

        return {
            "request_id": request_id,
            "output": output,
            "latency": latency,
            "success": success,
            "model": model_name,
            "version": model.version,
        }

    def ab_predict(self, model_a: str, model_b: str,
                   input_data: Any, split_ratio: float = 0.5) -> Dict[str, Any]:
        """A/B测试推理"""
        if random.random() < split_ratio:
            return self.predict(model_a, input_data)
        else:
            return self.predict(model_b, input_data)

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        if model_id in self.models:
            return asdict(self.models[model_id])
        return None

    def list_models(self, status: str = "") -> List[Dict[str, Any]]:
        """列出模型"""
        models = self.models.values()
        if status:
            models = [m for m in models if m.status == status]
        return [asdict(m) for m in models]

    def get_model_metrics(self, model_id: str) -> Dict[str, Any]:
        """获取模型指标"""
        if model_id not in self.models:
            return {}

        model = self.models[model_id]
        requests = [r for r in self.request_log if r.model_id == model_id]

        return {
            "model_id": model_id,
            "name": model.name,
            "version": model.version,
            "inference_count": model.inference_count,
            "avg_latency": round(model.avg_latency, 4),
            "error_count": model.error_count,
            "error_rate": round(model.error_count / max(model.inference_count, 1), 4),
            "recent_requests": len(requests[-100:]),
        }

    def retire_model(self, model_id: str) -> bool:
        """退役模型"""
        if model_id in self.models:
            self.models[model_id].status = ModelStatus.RETIRED.value
            self._save()
            return True
        return False

    def generate_report(self) -> Dict[str, Any]:
        status_counts = defaultdict(int)
        for m in self.models.values():
            status_counts[m.status] += 1

        return {
            "total_models": len(self.models),
            "total_deployments": len(self.deployments),
            "total_inferences": sum(m.inference_count for m in self.models.values()),
            "status_distribution": dict(status_counts),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "models_count": len(self.models),
            "deployments_count": len(self.deployments),
            "inferences_count": sum(m.inference_count for m in self.models.values()),
        }


if __name__ == "__main__":
    print("=== 模型服务测试 ===")
    engine = ModelServingEngine()

    # 注册模型
    m1 = engine.register_model("情感分析", "1.0.0", "pytorch", "文本情感分析模型")
    m2 = engine.register_model("情感分析", "2.0.0", "pytorch", "升级版情感分析")
    print(f"模型: {m1}, {m2}")

    # 加载
    engine.load_model(m1, lambda x: {"sentiment": "positive", "score": 0.95})
    engine.load_model(m2, lambda x: {"sentiment": "positive", "score": 0.98})

    # 部署
    d1 = engine.deploy(m1, "direct")
    d2 = engine.deploy(m2, "ab_test", 30)
    print(f"部署: {d1}, {d2}")

    # 推理
    for i in range(5):
        result = engine.predict("情感分析", f"这是第{i}条评论")
        print(f"推理: {result['output']} (延迟: {result['latency']:.4f}s)")

    # A/B测试
    ab_result = engine.ab_predict("情感分析", "情感分析", "测试文本")
    print(f"\nA/B推理: {ab_result['output']}")

    # 指标
    metrics = engine.get_model_metrics(m1)
    print(f"\n模型指标: {metrics}")

    report = engine.generate_report()
    print(f"\n模型服务报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
