"""
================================================================================
联邦学习系统 (Federated Learning System)
================================================================================

核心能力：
  1. 本地训练 - 在本地数据上训练模型
  2. 模型聚合 - 聚合多个客户端的模型更新
  3. 隐私保护 - 保护数据隐私
  4. 去中心化 - 无需集中数据
  5. 异步更新 - 支持异步模型更新

设计原则：
  - 隐私优先：数据不出本地
  - 去中心化：无中心数据存储
  - 安全聚合：安全地聚合模型更新
"""

import json
import os
import time
import hashlib
import random
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class ClientStatus(Enum):
    ACTIVE = "active"            # 活跃
    INACTIVE = "inactive"        # 不活跃
    TRAINING = "training"        # 训练中
    AGGREGATING = "aggregating"  # 聚合中

@dataclass
class ModelUpdate:
    """模型更新"""
    client_id: str
    round_id: str
    parameters: dict             # 模型参数
    sample_count: int            # 训练样本数
    loss: float                  # 损失值
    timestamp: float = field(default_factory=time.time)

@dataclass
class FederatedClient:
    """联邦学习客户端"""
    id: str
    name: str
    status: ClientStatus = ClientStatus.ACTIVE
    data_size: int = 0           # 本地数据量
    last_update: float = 0.0
    total_rounds: int = 0

@dataclass
class FederatedRound:
    """联邦学习轮次"""
    round_id: str
    participants: list           # 参与客户端
    global_parameters: dict      # 全局参数
    aggregated_loss: float
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 本地训练器
# ============================================================================

class LocalTrainer:
    """本地训练器"""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.local_data: list = []
        self.local_parameters: dict = {}

    def load_data(self, data: list):
        """加载本地数据"""
        self.local_data = data

    def train(self, global_parameters: dict,
              epochs: int = 5) -> ModelUpdate:
        """本地训练"""
        # 初始化本地参数
        self.local_parameters = global_parameters.copy()

        # 模拟训练过程
        total_loss = 0
        for epoch in range(epochs):
            # 模拟一个epoch的训练
            epoch_loss = self._train_epoch()
            total_loss += epoch_loss

        avg_loss = total_loss / epochs if epochs > 0 else 0

        # 生成模型更新
        update = ModelUpdate(
            client_id=self.client_id,
            round_id=f"round_{int(time.time())}",
            parameters=self.local_parameters,
            sample_count=len(self.local_data),
            loss=avg_loss,
        )

        return update

    def _train_epoch(self) -> float:
        """训练一个epoch"""
        # 简化实现：模拟训练
        if not self.local_data:
            return 0.0

        # 模拟参数更新
        for key in self.local_parameters:
            if isinstance(self.local_parameters[key], (int, float)):
                self.local_parameters[key] += random.uniform(-0.01, 0.01)

        # 模拟损失
        return random.uniform(0.1, 0.5)

    def evaluate(self, test_data: list = None) -> dict:
        """评估模型"""
        # 简化实现
        return {
            'loss': random.uniform(0.1, 0.5),
            'accuracy': random.uniform(0.7, 0.95),
            'samples': len(test_data) if test_data else 0,
        }


# ============================================================================
# 模型聚合器
# ============================================================================

class ModelAggregator:
    """模型聚合器"""

    def __init__(self):
        self.aggregation_history: list[dict] = []

    def aggregate(self, updates: list,
                   strategy: str = "fedavg") -> dict:
        """聚合模型更新"""
        if not updates:
            return {}

        if strategy == "fedavg":
            return self._federated_averaging(updates)
        elif strategy == "weighted":
            return self._weighted_aggregation(updates)
        else:
            return self._federated_averaging(updates)

    def _federated_averaging(self, updates: list) -> dict:
        """联邦平均"""
        if not updates:
            return {}

        # 获取参数键
        param_keys = updates[0].parameters.keys()

        # 计算总样本数
        total_samples = sum(u.sample_count for u in updates)

        # 加权平均
        aggregated = {}
        for key in param_keys:
            weighted_sum = 0
            for update in updates:
                weight = update.sample_count / total_samples
                weighted_sum += update.parameters.get(key, 0) * weight
            aggregated[key] = weighted_sum

        # 计算平均损失
        avg_loss = sum(u.loss for u in updates) / len(updates)

        # 记录聚合
        self.aggregation_history.append({
            'participants': len(updates),
            'total_samples': total_samples,
            'avg_loss': avg_loss,
            'timestamp': time.time(),
        })

        return {
            'parameters': aggregated,
            'avg_loss': avg_loss,
            'participants': len(updates),
            'total_samples': total_samples,
        }

    def _weighted_aggregation(self, updates: list) -> dict:
        """加权聚合"""
        if not updates:
            return {}

        # 基于损失的加权（损失越低权重越高）
        inverse_losses = [1.0 / (u.loss + 0.001) for u in updates]
        total_weight = sum(inverse_losses)

        param_keys = updates[0].parameters.keys()

        aggregated = {}
        for key in param_keys:
            weighted_sum = 0
            for i, update in enumerate(updates):
                weight = inverse_losses[i] / total_weight
                weighted_sum += update.parameters.get(key, 0) * weight
            aggregated[key] = weighted_sum

        avg_loss = sum(u.loss for u in updates) / len(updates)

        return {
            'parameters': aggregated,
            'avg_loss': avg_loss,
            'participants': len(updates),
        }


# ============================================================================
# 隐私保护器
# ============================================================================

class PrivacyProtector:
    """隐私保护器"""

    def __init__(self, noise_scale: float = 0.01):
        self.noise_scale = noise_scale

    def add_noise(self, parameters: dict) -> dict:
        """添加差分隐私噪声"""
        noisy_params = {}

        for key, value in parameters.items():
            if isinstance(value, (int, float)):
                # 添加高斯噪声
                noise = random.gauss(0, self.noise_scale)
                noisy_params[key] = value + noise
            else:
                noisy_params[key] = value

        return noisy_params

    def secure_aggregate(self, updates: list) -> dict:
        """安全聚合"""
        # 简化实现：实际应使用安全多方计算
        # 这里只做简单的混淆
        aggregated = {}

        if not updates:
            return aggregated

        param_keys = updates[0].parameters.keys()

        for key in param_keys:
            values = [u.parameters.get(key, 0) for u in updates]
            # 添加随机偏移
            offset = random.uniform(-0.001, 0.001)
            aggregated[key] = sum(values) / len(values) + offset

        return aggregated


# ============================================================================
# 联邦学习引擎
# ============================================================================

class FederatedLearningEngine:
    """
    联邦学习引擎 - 整合所有组件

    核心功能：
    1. 管理联邦学习客户端
    2. 协调训练轮次
    3. 聚合模型更新
    4. 保护数据隐私
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "federated_learning"
        os.makedirs(storage_dir, exist_ok=True)

        self.clients: dict[str, FederatedClient] = {}
        self.trainers: dict[str, LocalTrainer] = {}
        self.aggregator = ModelAggregator()
        self.privacy_protector = PrivacyProtector()

        self.global_parameters: dict = {}
        self.round_history: list[FederatedRound] = []
        self.current_round = 0

    def register_client(self, client_id: str, name: str,
                         data_size: int = 0) -> FederatedClient:
        """注册客户端"""
        client = FederatedClient(
            id=client_id,
            name=name,
            data_size=data_size,
        )
        self.clients[client_id] = client

        # 创建本地训练器
        self.trainers[client_id] = LocalTrainer(client_id)

        return client

    def load_client_data(self, client_id: str, data: list):
        """加载客户端数据"""
        if client_id in self.trainers:
            self.trainers[client_id].load_data(data)
            self.clients[client_id].data_size = len(data)

    def initialize_global_model(self, parameters: dict):
        """初始化全局模型"""
        self.global_parameters = parameters

    def run_round(self, selected_clients: list = None,
                   local_epochs: int = 5) -> dict:
        """执行一轮联邦学习"""
        self.current_round += 1
        round_id = f"round_{self.current_round}"

        # 选择参与客户端
        if selected_clients is None:
            selected_clients = [
                cid for cid, client in self.clients.items()
                if client.status == ClientStatus.ACTIVE
            ]

        if not selected_clients:
            return {'error': '没有可用的客户端'}

        # 本地训练
        updates = []
        for client_id in selected_clients:
            if client_id in self.trainers:
                # 更新客户端状态
                self.clients[client_id].status = ClientStatus.TRAINING

                # 本地训练
                update = self.trainers[client_id].train(
                    self.global_parameters, local_epochs
                )
                updates.append(update)

                # 更新客户端信息
                self.clients[client_id].status = ClientStatus.ACTIVE
                self.clients[client_id].last_update = time.time()
                self.clients[client_id].total_rounds += 1

        # 隐私保护
        for update in updates:
            update.parameters = self.privacy_protector.add_noise(update.parameters)

        # 聚合更新
        aggregated = self.aggregator.aggregate(updates)

        if 'parameters' in aggregated:
            self.global_parameters = aggregated['parameters']

        # 记录轮次
        round_record = FederatedRound(
            round_id=round_id,
            participants=selected_clients,
            global_parameters=self.global_parameters,
            aggregated_loss=aggregated.get('avg_loss', 0),
        )
        self.round_history.append(round_record)

        return {
            'round_id': round_id,
            'participants': len(selected_clients),
            'avg_loss': aggregated.get('avg_loss', 0),
            'total_samples': aggregated.get('total_samples', 0),
        }

    def get_global_parameters(self) -> dict:
        """获取��局参数"""
        return self.global_parameters

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_clients': len(self.clients),
            'active_clients': sum(
                1 for c in self.clients.values()
                if c.status == ClientStatus.ACTIVE
            ),
            'total_rounds': self.current_round,
            'total_aggregations': len(self.aggregator.aggregation_history),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🔗 联邦学习报告")
        report.append("=" * 50)
        report.append(f"\n总客户端数: {stats['total_clients']}")
        report.append(f"活跃客户端: {stats['active_clients']}")
        report.append(f"训练轮次: {stats['total_rounds']}")
        report.append(f"聚合次数: {stats['total_aggregations']}")

        # 最近轮次信息
        if self.round_history:
            last_round = self.round_history[-1]
            report.append(f"\n最近轮次: {last_round.round_id}")
            report.append(f"  参与者: {len(last_round.participants)}")
            report.append(f"  损失: {last_round.aggregated_loss:.4f}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = FederatedLearningEngine("test_federated_learning")

    # 注册客户端
    print("=== 注册客户端 ===")
    clients = [
        ("client_1", "Alice的设备", 100),
        ("client_2", "Bob的设备", 150),
        ("client_3", "Charlie的设备", 80),
    ]

    for client_id, name, data_size in clients:
        engine.register_client(client_id, name, data_size)
        print(f"注册: {name} (数据量: {data_size})")

    # 初始化全局模型
    initial_params = {
        'weight_1': 0.5,
        'weight_2': 0.3,
        'bias': 0.1,
    }
    engine.initialize_global_model(initial_params)

    # 模拟客户端数据
    print("\n=== 加载数据 ===")
    for client_id, _, data_size in clients:
        data = [f"sample_{i}" for i in range(data_size)]
        engine.load_client_data(client_id, data)

    # 执行联邦学习轮次
    print("\n=== 联邦学习 ===")
    for round_num in range(3):
        result = engine.run_round(local_epochs=3)
        print(f"轮次 {result['round_id']}: "
              f"参与者={result['participants']}, "
              f"损失={result['avg_loss']:.4f}")

    # 获取全局参数
    print(f"\n=== 全局参数 ===")
    global_params = engine.get_global_parameters()
    for key, value in global_params.items():
        print(f"  {key}: {value:.4f}")

    # 报告
    print("\n" + engine.generate_report())