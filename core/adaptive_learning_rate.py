"""
================================================================================
自适应学习率系统 (Adaptive Learning Rate System)
================================================================================

核心能力：
  1. 学习率监控 - 监控学习效果
  2. 动态调整 - 根据效果动态调整学习率
  3. 收敛检测 - 检测学习是否收敛
  4. 策略切换 - 在不同学习策略间切换
  5. 性能预测 - 预测学习率调整的效果

设计原则：
  - 自适应：根据学习效果自动调整
  - 稳定性：避免学习率震荡
  - 效率性：最大化学习效率
"""

import json
import os
import time
import hashlib
import math
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class LearningRateStrategy(Enum):
    CONSTANT = "constant"        # 恒定
    STEP_DECAY = "step_decay"    # 阶梯衰减
    EXPONENTIAL = "exponential"  # 指数衰减
    COSINE = "cosine"            # 余弦退火
    ADAPTIVE = "adaptive"        # 自适应

@dataclass
class LearningMetrics:
    """学习指标"""
    loss: float                  # 损失值
    accuracy: float              # 准确率
    learning_rate: float         # 当前学习率
    epoch: int                   # 轮次
    timestamp: float = field(default_factory=time.time)

@dataclass
class LearningRateSchedule:
    """学习率调度"""
    strategy: LearningRateStrategy
    initial_rate: float
    current_rate: float
    min_rate: float = 0.0001
    max_rate: float = 1.0
    decay_factor: float = 0.95
    step_size: int = 10


# ============================================================================
# 学习率调度器
# ============================================================================

class LearningRateScheduler:
    """学习率调度器"""

    def __init__(self, initial_rate: float = 0.01,
                 strategy: LearningRateStrategy = LearningRateStrategy.ADAPTIVE):
        self.schedule = LearningRateSchedule(
            strategy=strategy,
            initial_rate=initial_rate,
            current_rate=initial_rate,
        )
        self.metrics_history: list[LearningMetrics] = []

    def get_rate(self) -> float:
        """获取当前学习率"""
        return self.schedule.current_rate

    def update(self, metrics: LearningMetrics) -> float:
        """更新学习率"""
        self.metrics_history.append(metrics)

        if self.schedule.strategy == LearningRateStrategy.CONSTANT:
            return self.schedule.current_rate

        elif self.schedule.strategy == LearningRateStrategy.STEP_DECAY:
            return self._step_decay(metrics)

        elif self.schedule.strategy == LearningRateStrategy.EXPONENTIAL:
            return self._exponential_decay(metrics)

        elif self.schedule.strategy == LearningRateStrategy.COSINE:
            return self._cosine_annealing(metrics)

        elif self.schedule.strategy == LearningRateStrategy.ADAPTIVE:
            return self._adaptive(metrics)

        return self.schedule.current_rate

    def _step_decay(self, metrics: LearningMetrics) -> float:
        """阶梯衰减"""
        if metrics.epoch > 0 and metrics.epoch % self.schedule.step_size == 0:
            self.schedule.current_rate *= self.schedule.decay_factor
        return self.schedule.current_rate

    def _exponential_decay(self, metrics: LearningMetrics) -> float:
        """指数衰减"""
        self.schedule.current_rate = (
            self.schedule.initial_rate *
            (self.schedule.decay_factor ** metrics.epoch)
        )
        return self.schedule.current_rate

    def _cosine_annealing(self, metrics: LearningMetrics) -> float:
        """余弦退火"""
        progress = metrics.epoch / 100  # 假设100轮
        self.schedule.current_rate = (
            self.schedule.min_rate +
            (self.schedule.max_rate - self.schedule.min_rate) *
            (1 + math.cos(math.pi * progress)) / 2
        )
        return self.schedule.current_rate

    def _adaptive(self, metrics: LearningMetrics) -> float:
        """自适应调整"""
        if len(self.metrics_history) < 2:
            return self.schedule.current_rate

        # 检查损失变化
        prev_loss = self.metrics_history[-2].loss
        curr_loss = metrics.loss

        if curr_loss < prev_loss:
            # 损失下降，略微增加学习率
            self.schedule.current_rate = min(
                self.schedule.max_rate,
                self.schedule.current_rate * 1.05
            )
        elif curr_loss > prev_loss * 1.1:
            # 损失上升较多，减小学习率
            self.schedule.current_rate = max(
                self.schedule.min_rate,
                self.schedule.current_rate * 0.5
            )
        # 否则保持不变

        return self.schedule.current_rate

    def detect_convergence(self, window: int = 10,
                            threshold: float = 0.001) -> bool:
        """检测收敛"""
        if len(self.metrics_history) < window:
            return False

        recent_losses = [m.loss for m in self.metrics_history[-window:]]
        loss_change = abs(recent_losses[-1] - recent_losses[0])

        return loss_change < threshold

    def get_stats(self) -> dict:
        """获取统计信息"""
        if not self.metrics_history:
            return {}

        losses = [m.loss for m in self.metrics_history]
        accuracies = [m.accuracy for m in self.metrics_history]

        return {
            'total_epochs': len(self.metrics_history),
            'current_rate': self.schedule.current_rate,
            'initial_rate': self.schedule.initial_rate,
            'min_loss': min(losses),
            'max_accuracy': max(accuracies),
            'converged': self.detect_convergence(),
        }


# ============================================================================
# 学习效果分析器
# ============================================================================

class LearningEffectivenessAnalyzer:
    """学习效果分析器"""

    def __init__(self):
        self.analysis_history: list[dict] = []

    def analyze(self, metrics_history: list[LearningMetrics]) -> dict:
        """分析学习效果"""
        if len(metrics_history) < 2:
            return {'status': 'insufficient_data'}

        losses = [m.loss for m in metrics_history]
        accuracies = [m.accuracy for m in metrics_history]

        # 计算趋势
        loss_trend = self._calculate_trend(losses)
        accuracy_trend = self._calculate_trend(accuracies)

        # 计算稳定性
        loss_stability = self._calculate_stability(losses)

        # 判断效果
        if loss_trend < -0.01 and accuracy_trend > 0.01:
            effectiveness = 'good'
        elif loss_trend > 0.01:
            effectiveness = 'poor'
        else:
            effectiveness = 'moderate'

        analysis = {
            'effectiveness': effectiveness,
            'loss_trend': loss_trend,
            'accuracy_trend': accuracy_trend,
            'loss_stability': loss_stability,
        }

        self.analysis_history.append(analysis)
        return analysis

    def _calculate_trend(self, values: list) -> float:
        """计算趋势"""
        if len(values) < 2:
            return 0.0

        # 简单线性趋势
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        return numerator / denominator if denominator != 0 else 0.0

    def _calculate_stability(self, values: list) -> float:
        """计算稳定性"""
        if len(values) < 2:
            return 1.0

        # 计算变异系数
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)

        cv = std / mean if mean != 0 else 0
        return max(0, 1 - cv)

    def get_recommendations(self, analysis: dict) -> list:
        """获取优化建议"""
        recommendations = []

        if analysis.get('effectiveness') == 'poor':
            recommendations.append({
                'type': 'reduce_learning_rate',
                'description': '学习效果差，建议降低学习率',
                'priority': 'high',
            })

        if analysis.get('loss_stability', 1) < 0.5:
            recommendations.append({
                'type': 'increase_stability',
                'description': '损失不稳定，建议减小学习率或增加batch size',
                'priority': 'medium',
            })

        return recommendations


# ============================================================================
# 自适应学习率引擎
# ============================================================================

class AdaptiveLearningRateEngine:
    """
    自适应学习率引擎 - 整合所有组件

    核心功能：
    1. 动态调整学习率
    2. 监控学习效果
    3. 检测收敛
    4. 提供优化建议
    """

    def __init__(self, storage_dir: str = None,
                 initial_rate: float = 0.01):
        storage_dir = storage_dir or "adaptive_lr"
        os.makedirs(storage_dir, exist_ok=True)

        self.scheduler = LearningRateScheduler(initial_rate)
        self.analyzer = LearningEffectivenessAnalyzer()

        self.current_epoch = 0

    def step(self, loss: float, accuracy: float) -> dict:
        """执行一步学习"""
        # 创建指标
        metrics = LearningMetrics(
            loss=loss,
            accuracy=accuracy,
            learning_rate=self.scheduler.get_rate(),
            epoch=self.current_epoch,
        )

        # 更新学习率
        new_rate = self.scheduler.update(metrics)

        # 分析效果
        analysis = self.analyzer.analyze(self.scheduler.metrics_history)

        # 获取建议
        recommendations = self.analyzer.get_recommendations(analysis)

        self.current_epoch += 1

        return {
            'epoch': self.current_epoch,
            'loss': loss,
            'accuracy': accuracy,
            'learning_rate': new_rate,
            'analysis': analysis,
            'recommendations': recommendations,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.scheduler.get_stats()

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("📈 自适应学习率报告")
        report.append("=" * 50)

        if stats:
            report.append(f"\n总轮次: {stats.get('total_epochs', 0)}")
            report.append(f"当前学习率: {stats.get('current_rate', 0):.6f}")
            report.append(f"初始学习率: {stats.get('initial_rate', 0):.6f}")
            report.append(f"最小损失: {stats.get('min_loss', 0):.6f}")
            report.append(f"最高准确率: {stats.get('max_accuracy', 0):.2%}")
            report.append(f"是否收敛: {'是' if stats.get('converged') else '否'}")
        else:
            report.append("\n暂无学习数据")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = AdaptiveLearningRateEngine("test_adaptive_lr", initial_rate=0.01)

    # 模拟学习过程
    print("=== 自适应学习率 ===")
    import random

    loss = 1.0
    accuracy = 0.5

    for epoch in range(20):
        # 模拟损失和准确率变化
        loss = max(0.1, loss - random.uniform(0.01, 0.05))
        accuracy = min(0.99, accuracy + random.uniform(0.01, 0.03))

        result = engine.step(loss, accuracy)

        if epoch % 5 == 0:
            print(f"轮次 {result['epoch']}: "
                  f"损失={result['loss']:.4f}, "
                  f"准确率={result['accuracy']:.2%}, "
                  f"学习率={result['learning_rate']:.6f}")

    # 报告
    print("\n" + engine.generate_report())