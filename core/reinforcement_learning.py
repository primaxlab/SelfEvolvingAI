"""
================================================================================
强化学习系统 (Reinforcement Learning System)
================================================================================

核心能力：
  1. 状态感知 - 感知当前环境状态
  2. 动作选择 - 选择最优动作
  3. 奖励计算 - 计算奖励信号
  4. 策略更新 - 根据奖励更新策略
  5. 价值估计 - 估计状态/动作价值

设计原则：
  - 探索与利用平衡：既要尝试新方法，也要用已知的好方法
  - 延迟奖励：考虑长期收益而非短期
  - 持续优化：不断从经验中学习
"""

import json
import os
import time
import hashlib
import random
import math
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict


# ============================================================================
# 数据结构
# ============================================================================

class Action(Enum):
    RESPOND = "respond"           # 回答问题
    ASK_CLARIFY = "ask_clarify"   # 请求澄清
    SEARCH = "search"             # 搜索信息
    DELEGATE = "delegate"         # 委派给其他
    REFUSE = "refuse"             # 拒绝回答
    LEARN = "learn"               # 学习新知识

@dataclass
class State:
    """环境状态"""
    id: str
    features: dict               # 状态特征
    context: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class Experience:
    """经验"""
    state: State
    action: Action
    reward: float
    next_state: Optional[State]
    done: bool = False

@dataclass
class Policy:
    """策略"""
    state_action_values: dict = field(default_factory=dict)  # Q值表
    visit_counts: dict = field(default_factory=dict)         # 访问次数
    learning_rate: float = 0.1
    discount_factor: float = 0.9
    exploration_rate: float = 0.1


# ============================================================================
# 状态编码器
# ============================================================================

class StateEncoder:
    """状态编码器"""

    def encode(self, context: dict) -> State:
        """将上下文编码为状态"""
        features = {
            'complexity': self._estimate_complexity(context),
            'confidence': context.get('confidence', 0.5),
            'domain_encoded': self._encode_domain(context.get('domain', 'general')),
            'has_context': 1.0 if context.get('has_context') else 0.0,
            'urgency': context.get('urgency', 0.5),
        }

        state_id = hashlib.md5(str(features).encode()).hexdigest()[:12]

        return State(
            id=state_id,
            features=features,
            context=context,
        )

    def _estimate_complexity(self, context: dict) -> float:
        """估计任务复杂度"""
        task = context.get('task', '')
        # 基于长度和关键词估计
        complexity = min(1.0, len(task) / 200)

        complex_keywords = ['复杂', '多个', '系统', '优化', '设计']
        for keyword in complex_keywords:
            if keyword in task:
                complexity = min(1.0, complexity + 0.1)

        return complexity

    def _encode_domain(self, domain: str) -> float:
        """编码领域"""
        domain_map = {
            'programming': 0.1,
            'math': 0.2,
            'science': 0.3,
            'language': 0.4,
            'general': 0.5,
        }
        return domain_map.get(domain, 0.5)


# ============================================================================
# Q学习器
# ============================================================================

class QLearner:
    """Q学习器"""

    def __init__(self, learning_rate: float = 0.1,
                 discount_factor: float = 0.9,
                 exploration_rate: float = 0.1):
        self.q_table: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.visit_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate

    def get_q_value(self, state_id: str, action: Action) -> float:
        """获取Q值"""
        return self.q_table[state_id][action.value]

    def update(self, state_id: str, action: Action,
               reward: float, next_state_id: str, done: bool):
        """更新Q值"""
        current_q = self.get_q_value(state_id, action)

        if done:
            target = reward
        else:
            # 下一状态的最大Q值
            next_max_q = max(
                self.q_table[next_state_id].values(),
                default=0
            )
            target = reward + self.discount_factor * next_max_q

        # Q值更新
        self.q_table[state_id][action.value] = (
            current_q + self.learning_rate * (target - current_q)
        )

        # 更新访问次数
        self.visit_counts[state_id][action.value] += 1

    def choose_action(self, state_id: str,
                       available_actions: list) -> Action:
        """选择动作（ε-贪心策略）"""
        if random.random() < self.exploration_rate:
            # 探索：随机选择
            return random.choice(available_actions)
        else:
            # 利用：选择最优
            return self.get_best_action(state_id, available_actions)

    def get_best_action(self, state_id: str,
                         available_actions: list) -> Action:
        """获取最优动作"""
        if not available_actions:
            return Action.RESPOND

        best_action = available_actions[0]
        best_value = self.get_q_value(state_id, best_action)

        for action in available_actions[1:]:
            value = self.get_q_value(state_id, action)
            if value > best_value:
                best_value = value
                best_action = action

        return best_action

    def get_policy(self, state_id: str) -> dict:
        """获取状态策略"""
        return dict(self.q_table[state_id])


# ============================================================================
# 奖励计算器
# ============================================================================

class RewardCalculator:
    """奖励计算器"""

    def __init__(self):
        # 奖励规则
        self.reward_rules = {
            'success': 1.0,
            'partial_success': 0.5,
            'failure': -1.0,
            'timeout': -0.5,
            'user_satisfied': 1.5,
            'user_dissatisfied': -1.5,
            'learned_something': 0.3,
            'saved_time': 0.5,
        }

    def calculate(self, action: Action, outcome: dict) -> float:
        """计算奖励"""
        reward = 0.0

        # 基础奖励
        if outcome.get('success'):
            reward += self.reward_rules['success']
        elif outcome.get('partial'):
            reward += self.reward_rules['partial_success']
        else:
            reward += self.reward_rules['failure']

        # 用户反馈
        if outcome.get('user_satisfied'):
            reward += self.reward_rules['user_satisfied']
        elif outcome.get('user_dissatisfied'):
            reward += self.reward_rules['user_dissatisfied']

        # 效率奖励
        if outcome.get('time_saved'):
            reward += self.reward_rules['saved_time']

        # 学习奖励
        if outcome.get('learned'):
            reward += self.reward_rules['learned_something']

        return reward


# ============================================================================
# 策略优化器
# ============================================================================

class PolicyOptimizer:
    """策略优化器"""

    def __init__(self):
        self.optimization_history: list[dict] = []

    def optimize(self, policy: Policy,
                 experiences: list) -> Policy:
        """优化策略"""
        # 分析经验
        action_values = {}
        for exp in experiences:
            action = exp.action.value
            if action not in action_values:
                action_values[action] = []
            action_values[action].append(exp.reward)

        # 更新策略偏好
        for action, rewards in action_values.items():
            avg_reward = sum(rewards) / len(rewards)
            # 增加好动作的概率，减少差动作的概率
            if action in policy.state_action_values:
                policy.state_action_values[action] = (
                    policy.state_action_values[action] * 0.9 + avg_reward * 0.1
                )
            else:
                policy.state_action_values[action] = avg_reward

        # 记录优化
        self.optimization_history.append({
            'timestamp': time.time(),
            'experiences_count': len(experiences),
            'action_values': action_values,
        })

        return policy


# ============================================================================
# 强化学习引擎
# ============================================================================

class ReinforcementLearningEngine:
    """
    强化学习引擎 - 整合所有组件

    核心功能：
    1. 感知环境状态
    2. 选择最优动作
    3. 计算奖励
    4. 更新策略
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "reinforcement_learning"
        os.makedirs(storage_dir, exist_ok=True)

        self.state_encoder = StateEncoder()
        self.q_learner = QLearner()
        self.reward_calculator = RewardCalculator()
        self.policy_optimizer = PolicyOptimizer()

        self.experience_buffer: list[Experience] = []
        self.episode_rewards: list[float] = []

        self.storage_path = os.path.join(storage_dir, "rl.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.episode_rewards = data.get('episode_rewards', [])

    def _save(self):
        """保存数据"""
        data = {
            'episode_rewards': self.episode_rewards[-100:],
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def choose_action(self, context: dict,
                       available_actions: list) -> dict:
        """选择动作"""
        # 编码状态
        state = self.state_encoder.encode(context)

        # 选择动作
        action = self.q_learner.choose_action(
            state.id,
            available_actions
        )

        # 获取Q值
        q_value = self.q_learner.get_q_value(state.id, action)

        return {
            'action': action.value,
            'state_id': state.id,
            'q_value': q_value,
            'exploration': self.q_learner.exploration_rate,
        }

    def learn(self, context: dict, action: Action,
              outcome: dict, next_context: dict = None) -> dict:
        """从经验中学习"""
        # 编码状态
        state = self.state_encoder.encode(context)
        next_state = self.state_encoder.encode(next_context) if next_context else None

        # 计算奖励
        reward = self.reward_calculator.calculate(action, outcome)

        # 创建经验
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=outcome.get('done', False),
        )
        self.experience_buffer.append(experience)

        # 更新Q值
        if next_state:
            self.q_learner.update(
                state.id, action, reward,
                next_state.id, experience.done
            )

        # 记录奖励
        self.episode_rewards.append(reward)
        self._save()

        return {
            'reward': reward,
            'q_value': self.q_learner.get_q_value(state.id, action),
            'experience_count': len(self.experience_buffer),
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_experiences': len(self.experience_buffer),
            'total_episodes': len(self.episode_rewards),
            'avg_reward': sum(self.episode_rewards) / max(1, len(self.episode_rewards)),
            'exploration_rate': self.q_learner.exploration_rate,
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🎯 强化学习报告")
        report.append("=" * 50)
        report.append(f"\n总经验数: {stats['total_experiences']}")
        report.append(f"总回合数: {stats['total_episodes']}")
        report.append(f"平均奖励: {stats['avg_reward']:.3f}")
        report.append(f"探索率: {stats['exploration_rate']:.3f}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = ReinforcementLearningEngine("test_reinforcement_learning")

    # 模拟学习
    print("=== 强化学习 ===")
    contexts = [
        {'task': '简单问题', 'domain': 'general', 'confidence': 0.9},
        {'task': '复杂问题', 'domain': 'programming', 'confidence': 0.5},
        {'task': '紧急问题', 'domain': 'general', 'urgency': 0.9},
    ]

    for context in contexts:
        # 选择动作
        result = engine.choose_action(
            context,
            [Action.RESPOND, Action.ASK_CLARIFY, Action.SEARCH]
        )
        print(f"状态: {context['task']}")
        print(f"  选择动作: {result['action']}")
        print(f"  Q值: {result['q_value']:.3f}")

        # 模拟学习
        outcome = {'success': random.random() > 0.3, 'user_satisfied': random.random() > 0.5}
        learn_result = engine.learn(context, Action(result['action']), outcome)
        print(f"  奖励: {learn_result['reward']:.3f}")

    # 报告
    print("\n" + engine.generate_report())