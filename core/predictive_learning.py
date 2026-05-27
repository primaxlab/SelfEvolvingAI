"""
================================================================================
预测学习系统 (Predictive Learning System)
================================================================================

核心能力：
  1. 趋势预测 - 预测未来趋势
  2. 行为预测 - 预测用户行为
  3. 需求预测 - 预测用户需求
  4. 异常预测 - 预测潜在异常
  5. 效果预测 - 预测行动效果

设计原则：
  - 数据驱动：基于历史数据预测
  - 不确定性量化：给出预测的置信度
  - 持续更新：随新数据不断修正预测
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

class PredictionType(Enum):
    TREND = "trend"              # 趋势预测
    BEHAVIOR = "behavior"        # 行为预测
    DEMAND = "demand"            # 需求预测
    ANOMALY = "anomaly"          # 异常预测
    OUTCOME = "outcome"          # 效果预测

@dataclass
class TimeSeriesPoint:
    """时间序列点"""
    timestamp: float
    value: float
    metadata: dict = field(default_factory=dict)

@dataclass
class Prediction:
    """预测"""
    id: str
    prediction_type: PredictionType
    target: str
    predicted_value: float
    confidence: float
    time_horizon: float          # 预测时间跨度(秒)
    created_at: float = field(default_factory=time.time)
    features_used: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

@dataclass
class PredictionResult:
    """预测结果"""
    prediction_id: str
    actual_value: float
    predicted_value: float
    error: float
    accuracy: float
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 趋势分析器
# ============================================================================

class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.time_series: dict[str, list[TimeSeriesPoint]] = {}

    def add_data_point(self, series_id: str,
                        timestamp: float, value: float):
        """添加数据点"""
        if series_id not in self.time_series:
            self.time_series[series_id] = []

        self.time_series[series_id].append(
            TimeSeriesPoint(timestamp=timestamp, value=value)
        )

        # 保持最近1000个点
        if len(self.time_series[series_id]) > 1000:
            self.time_series[series_id] = self.time_series[series_id][-1000:]

    def analyze_trend(self, series_id: str) -> dict:
        """分析趋势"""
        points = self.time_series.get(series_id, [])
        if len(points) < 2:
            return {'trend': 'insufficient_data', 'slope': 0}

        # 计算简单线性趋势
        values = [p.value for p in points]
        n = len(values)

        # 计算斜率
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # 判断趋势
        if slope > 0.01:
            trend = 'increasing'
        elif slope < -0.01:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'slope': slope,
            'current_value': values[-1],
            'data_points': n,
        }

    def predict_next(self, series_id: str,
                      steps: int = 1) -> dict:
        """预测下一个值"""
        analysis = self.analyze_trend(series_id)

        if analysis['trend'] == 'insufficient_data':
            return {'predicted_value': None, 'confidence': 0}

        points = self.time_series.get(series_id, [])
        current_value = points[-1].value
        slope = analysis['slope']

        # 简单线性预测
        predicted_value = current_value + slope * steps

        # 置信度基于数据点数量和趋势稳定性
        confidence = min(0.9, 0.3 + len(points) * 0.01)

        return {
            'predicted_value': predicted_value,
            'confidence': confidence,
            'trend': analysis['trend'],
        }


# ============================================================================
# 行为预测器
# ============================================================================

class BehaviorPredictor:
    """行为预测器"""

    def __init__(self):
        self.user_patterns: dict[str, dict] = {}
        self.behavior_history: dict[str, list] = {}

    def record_behavior(self, user_id: str, behavior: str,
                         context: dict = None):
        """记录用户行为"""
        if user_id not in self.behavior_history:
            self.behavior_history[user_id] = []

        self.behavior_history[user_id].append({
            'behavior': behavior,
            'context': context or {},
            'timestamp': time.time(),
        })

        # 更新模式
        self._update_patterns(user_id)

    def _update_patterns(self, user_id: str):
        """更新用户模式"""
        history = self.behavior_history.get(user_id, [])
        if not history:
            return

        # 统计行为频率
        behavior_counts = {}
        for record in history[-100:]:  # 最近100条
            behavior = record['behavior']
            behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1

        # 找出最常见行为
        if behavior_counts:
            most_common = max(behavior_counts, key=behavior_counts.get)
            self.user_patterns[user_id] = {
                'most_common': most_common,
                'patterns': behavior_counts,
                'total_interactions': len(history),
            }

    def predict_behavior(self, user_id: str,
                          context: dict = None) -> dict:
        """预测用户行为"""
        pattern = self.user_patterns.get(user_id)

        if not pattern:
            return {
                'predicted_behavior': None,
                'confidence': 0,
                'reason': '无历史数据',
            }

        # 基于模式预测
        most_common = pattern['most_common']
        total = pattern['total_interactions']
        common_count = pattern['patterns'].get(most_common, 0)

        confidence = common_count / total if total > 0 else 0

        return {
            'predicted_behavior': most_common,
            'confidence': confidence,
            'alternatives': [
                b for b in pattern['patterns']
                if b != most_common
            ][:3],
        }


# ============================================================================
# 需求预测器
# ============================================================================

class DemandPredictor:
    """需求预测器"""

    def __init__(self):
        self.demand_history: dict[str, list] = {}
        self.seasonal_patterns: dict[str, dict] = {}

    def record_demand(self, item: str, quantity: float,
                       timestamp: float = None):
        """记录需求"""
        if timestamp is None:
            timestamp = time.time()

        if item not in self.demand_history:
            self.demand_history[item] = []

        self.demand_history[item].append({
            'quantity': quantity,
            'timestamp': timestamp,
        })

    def predict_demand(self, item: str,
                        time_horizon: float = 86400) -> dict:
        """预测需求"""
        history = self.demand_history.get(item, [])

        if not history:
            return {
                'predicted_demand': 0,
                'confidence': 0,
                'reason': '无历史数据',
            }

        # 计算平均需求
        quantities = [h['quantity'] for h in history]
        avg_demand = sum(quantities) / len(quantities)

        # 考虑时间因素
        recent = [h for h in history if h['timestamp'] > time.time() - 86400]
        if recent:
            recent_avg = sum(h['quantity'] for h in recent) / len(recent)
            # 加权平均
            predicted = avg_demand * 0.3 + recent_avg * 0.7
        else:
            predicted = avg_demand

        confidence = min(0.9, 0.3 + len(history) * 0.02)

        return {
            'predicted_demand': predicted,
            'confidence': confidence,
            'historical_avg': avg_demand,
            'data_points': len(history),
        }


# ============================================================================
# 预测学习引擎
# ============================================================================

class PredictiveLearningEngine:
    """
    预测学习引擎 - 整合所有组件

    核心功能：
    1. 趋势预测
    2. 行为预测
    3. 需求预测
    4. 预测评估
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "predictive_learning"
        os.makedirs(storage_dir, exist_ok=True)

        self.trend_analyzer = TrendAnalyzer()
        self.behavior_predictor = BehaviorPredictor()
        self.demand_predictor = DemandPredictor()

        self.predictions: dict[str, Prediction] = {}
        self.prediction_results: list[PredictionResult] = []

        self.storage_path = os.path.join(storage_dir, "predictions.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 简化加载

    def _save(self):
        """保存数据"""
        data = {
            'predictions': len(self.predictions),
            'results': len(self.prediction_results),
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_time_series_data(self, series_id: str,
                              timestamp: float, value: float):
        """添加时间序列数据"""
        self.trend_analyzer.add_data_point(series_id, timestamp, value)

    def record_user_behavior(self, user_id: str, behavior: str,
                               context: dict = None):
        """记录用户行为"""
        self.behavior_predictor.record_behavior(user_id, behavior, context)

    def predict_trend(self, series_id: str,
                       steps: int = 1) -> dict:
        """预测趋势"""
        return self.trend_analyzer.predict_next(series_id, steps)

    def predict_user_behavior(self, user_id: str,
                                context: dict = None) -> dict:
        """预测用户行为"""
        return self.behavior_predictor.predict_behavior(user_id, context)

    def predict_demand(self, item: str,
                        time_horizon: float = 86400) -> dict:
        """预测需求"""
        return self.demand_predictor.predict_demand(item, time_horizon)

    def evaluate_prediction(self, prediction_id: str,
                             actual_value: float) -> dict:
        """评估预测"""
        prediction = self.predictions.get(prediction_id)
        if not prediction:
            return {'error': '预测不存在'}

        error = abs(actual_value - prediction.predicted_value)
        accuracy = 1.0 - min(1.0, error / max(1.0, abs(actual_value)))

        result = PredictionResult(
            prediction_id=prediction_id,
            actual_value=actual_value,
            predicted_value=prediction.predicted_value,
            error=error,
            accuracy=accuracy,
        )

        self.prediction_results.append(result)
        self._save()

        return {
            'accuracy': accuracy,
            'error': error,
            'predicted': prediction.predicted_value,
            'actual': actual_value,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        total_predictions = len(self.prediction_results)
        if total_predictions > 0:
            avg_accuracy = sum(r.accuracy for r in self.prediction_results) / total_predictions
        else:
            avg_accuracy = 0

        return {
            'total_predictions': len(self.predictions),
            'evaluated_predictions': total_predictions,
            'average_accuracy': avg_accuracy,
            'time_series': len(self.trend_analyzer.time_series),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🔮 预测学习报告")
        report.append("=" * 50)
        report.append(f"\n预测总数: {stats['total_predictions']}")
        report.append(f"已评估: {stats['evaluated_predictions']}")
        report.append(f"平均准确率: {stats['average_accuracy']:.2%}")
        report.append(f"时间序列数: {stats['time_series']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = PredictiveLearningEngine("test_predictive_learning")

    # 添加时间序列数据
    print("=== 时间序列预测 ===")
    base_time = time.time()
    for i in range(10):
        engine.add_time_series_data("user_activity", base_time + i * 3600, 10 + i * 2 + (i % 3))

    trend_result = engine.predict_trend("user_activity")
    print(f"趋势预测: {trend_result}")

    # 行为预测
    print("\n=== 行为预测 ===")
    for _ in range(5):
        engine.record_user_behavior("user1", "ask_question")
    for _ in range(3):
        engine.record_user_behavior("user1", "write_code")

    behavior_result = engine.predict_user_behavior("user1")
    print(f"行为预测: {behavior_result}")

    # 需求预测
    print("\n=== 需求预测 ===")
    for i in range(7):
        engine.demand_predictor.record_demand("api_calls", 100 + i * 10)

    demand_result = engine.predict_demand("api_calls")
    print(f"需求预测: {demand_result}")

    # 报告
    print("\n" + engine.generate_report())