"""
================================================================================
自适应提示工程系统 (Adaptive Prompt Engineering System)
================================================================================

核心能力：
  1. 提示词生成 - 自动生成提示词
  2. 提示词优化 - 优化现有提示词
  3. 效果评估 - 评估提示词效果
  4. A/B测试 - 测试不同提示词
  5. 模板管理 - 管理提示词模板

设计原则：
  - 数据驱动：基于效果优化
  - 持续迭代：不断优化提示词
  - 可复用：模板化管理
"""

import json
import os
import time
import hashlib
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class PromptType(Enum):
    SYSTEM = "system"            # 系统提示
    USER = "user"                # 用户提示
    ASSISTANT = "assistant"      # 助手提示
    TEMPLATE = "template"        # 模板提示

@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str
    name: str
    prompt_type: PromptType
    template: str
    variables: list              # 变量列表
    description: str = ""
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

@dataclass
class PromptVersion:
    """提示词版本"""
    version_id: str
    prompt_id: str
    content: str
    performance: float           # 性能分数
    created_at: float = field(default_factory=time.time)

@dataclass
class ABTestResult:
    """A/B测试结果"""
    test_id: str
    prompt_a_id: str
    prompt_b_id: str
    winner: str                  # 胜出的提示词ID
    confidence: float
    samples: int


# ============================================================================
# 提示词生成器
# ============================================================================

class PromptGenerator:
    """提示词生成器"""

    def __init__(self):
        # 提示词组件库
        self.components = {
            'role': [
                "你是一个专业的{domain}专家",
                "作为一个经验丰富的{domain}从业者",
                "你是{domain}领域的权威",
            ],
            'task': [
                "请帮我{task}",
                "我需要你{task}",
                "请执行以下任务: {task}",
            ],
            'format': [
                "请用{format}格式输出",
                "输出格式要求: {format}",
                "请按照{format}格式组织回答",
            ],
            'constraints': [
                "请注意以下约束: {constraints}",
                "在回答时请遵守: {constraints}",
                "限制条件: {constraints}",
            ],
        }

    def generate(self, domain: str, task: str,
                  output_format: str = "markdown",
                  constraints: list = None) -> str:
        """生成提示词"""
        parts = []

        # 角色设定
        role = self.components['role'][0].format(domain=domain)
        parts.append(role)

        # 任务描述
        task_desc = self.components['task'][0].format(task=task)
        parts.append(task_desc)

        # 输出格式
        if output_format:
            format_desc = self.components['format'][0].format(format=output_format)
            parts.append(format_desc)

        # 约束条件
        if constraints:
            constraints_str = ", ".join(constraints)
            constraints_desc = self.components['constraints'][0].format(constraints=constraints_str)
            parts.append(constraints_desc)

        return "\n\n".join(parts)

    def generate_system_prompt(self, role: str, capabilities: list,
                                 limitations: list = None) -> str:
        """生成系统提示词"""
        prompt_parts = [f"# 角色\n{role}"]

        if capabilities:
            cap_str = "\n".join([f"- {cap}" for cap in capabilities])
            prompt_parts.append(f"# 能力\n{cap_str}")

        if limitations:
            lim_str = "\n".join([f"- {lim}" for lim in limitations])
            prompt_parts.append(f"# 限制\n{lim_str}")

        return "\n\n".join(prompt_parts)


# ============================================================================
# 提示词优化器
# ============================================================================

class PromptOptimizer:
    """提示词优化器"""

    def __init__(self):
        self.optimization_strategies = [
            self._add_specificity,
            self._add_examples,
            self._add_constraints,
            self._simplify_language,
        ]

    def optimize(self, prompt: str, feedback: dict = None) -> str:
        """优化提示词"""
        optimized = prompt

        # 应用优化策略
        for strategy in self.optimization_strategies:
            optimized = strategy(optimized, feedback or {})

        return optimized

    def _add_specificity(self, prompt: str, feedback: dict) -> str:
        """增加具体性"""
        # 如果提示词太模糊，增加具体要求
        if len(prompt) < 50:
            prompt += "\n\n请提供详细、具体的回答。"
        return prompt

    def _add_examples(self, prompt: str, feedback: dict) -> str:
        """添加示例"""
        if feedback.get('needs_examples'):
            prompt += "\n\n请提供具体示例来说明。"
        return prompt

    def _add_constraints(self, prompt: str, feedback: dict) -> str:
        """添加约束"""
        if feedback.get('too_verbose'):
            prompt += "\n\n请简洁回答，避免冗余。"
        return prompt

    def _simplify_language(self, prompt: str, feedback: dict) -> str:
        """简化语言"""
        # 移除冗余词汇
        redundant = ["请务必", "一定要", "必须"]
        for word in redundant:
            prompt = prompt.replace(word, "")
        return prompt


# ============================================================================
# 效果评估器
# ============================================================================

class PromptEvaluator:
    """效果评估器"""

    def __init__(self):
        self.evaluation_history: list[dict] = []

    def evaluate(self, prompt: str, response: str,
                  expected: str = None) -> dict:
        """评估提示词效果"""
        # 相关性评估
        relevance = self._calculate_relevance(prompt, response)

        # 完整性评估
        completeness = self._calculate_completeness(response, expected)

        # 质量评估
        quality = self._calculate_quality(response)

        # 综合分数
        score = relevance * 0.3 + completeness * 0.4 + quality * 0.3

        evaluation = {
            'relevance': relevance,
            'completeness': completeness,
            'quality': quality,
            'overall_score': score,
        }

        self.evaluation_history.append({
            'prompt': prompt[:100],
            'score': score,
            'timestamp': time.time(),
        })

        return evaluation

    def _calculate_relevance(self, prompt: str, response: str) -> float:
        """计算相关性"""
        prompt_words = set(prompt.lower().split())
        response_words = set(response.lower().split())

        if not prompt_words:
            return 0.5

        overlap = len(prompt_words & response_words)
        return min(1.0, overlap / len(prompt_words) * 2)

    def _calculate_completeness(self, response: str,
                                  expected: str = None) -> float:
        """计算完整性"""
        if not expected:
            # 基于长度估计
            return min(1.0, len(response) / 200)

        expected_words = set(expected.lower().split())
        response_words = set(response.lower().split())

        if not expected_words:
            return 0.5

        coverage = len(expected_words & response_words) / len(expected_words)
        return coverage

    def _calculate_quality(self, response: str) -> float:
        """计算质量"""
        # 基于启发式规则
        score = 0.5

        # 长度适中
        if 50 < len(response) < 500:
            score += 0.2

        # 有结构
        if '\n' in response:
            score += 0.1

        # 有标点
        if '。' in response or '.' in response:
            score += 0.1

        return min(1.0, score)


# ============================================================================
# A/B测试管理器
# ============================================================================

class ABTestManager:
    """A/B测试管理器"""

    def __init__(self):
        self.tests: dict[str, dict] = {}
        self.results: list[ABTestResult] = []

    def create_test(self, prompt_a: str, prompt_b: str,
                     test_name: str = "") -> str:
        """创建A/B测试"""
        test_id = hashlib.md5(f"{prompt_a}:{prompt_b}".encode()).hexdigest()[:12]

        self.tests[test_id] = {
            'name': test_name or f"test_{test_id}",
            'prompt_a': prompt_a,
            'prompt_b': prompt_b,
            'scores_a': [],
            'scores_b': [],
            'created_at': time.time(),
        }

        return test_id

    def record_result(self, test_id: str, variant: str,
                       score: float) -> bool:
        """记录测试结果"""
        if test_id not in self.tests:
            return False

        test = self.tests[test_id]
        if variant == 'a':
            test['scores_a'].append(score)
        elif variant == 'b':
            test['scores_b'].append(score)
        else:
            return False

        return True

    def get_winner(self, test_id: str) -> Optional[dict]:
        """获取测试结果"""
        test = self.tests.get(test_id)
        if not test:
            return None

        scores_a = test['scores_a']
        scores_b = test['scores_b']

        if not scores_a or not scores_b:
            return {'status': 'insufficient_data'}

        avg_a = sum(scores_a) / len(scores_a)
        avg_b = sum(scores_b) / len(scores_b)

        if avg_a > avg_b:
            winner = 'a'
            winner_prompt = test['prompt_a']
        else:
            winner = 'b'
            winner_prompt = test['prompt_b']

        # 计算置信度
        confidence = abs(avg_a - avg_b) / max(avg_a, avg_b)

        result = ABTestResult(
            test_id=test_id,
            prompt_a_id=test['prompt_a'][:20],
            prompt_b_id=test['prompt_b'][:20],
            winner=winner,
            confidence=confidence,
            samples=len(scores_a) + len(scores_b),
        )

        self.results.append(result)

        return {
            'winner': winner,
            'avg_score_a': avg_a,
            'avg_score_b': avg_b,
            'confidence': confidence,
            'winner_prompt': winner_prompt,
        }


# ============================================================================
# 自适应提示工程引擎
# ============================================================================

class AdaptivePromptEngineeringEngine:
    """
    自适应提示工程引擎 - 整合所有组件

    核心功能：
    1. 生成提示词
    2. 优化提示词
    3. 评估效果
    4. A/B测试
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "prompt_engineering"
        os.makedirs(storage_dir, exist_ok=True)

        self.generator = PromptGenerator()
        self.optimizer = PromptOptimizer()
        self.evaluator = PromptEvaluator()
        self.ab_test_manager = ABTestManager()

        self.templates: dict[str, PromptTemplate] = {}
        self.prompt_history: list[dict] = []

        self.storage_path = os.path.join(storage_dir, "prompts.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.prompt_history = data.get('history', [])

    def _save(self):
        """保存数据"""
        data = {
            'history': self.prompt_history[-100:],
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generate_prompt(self, domain: str, task: str,
                         output_format: str = "markdown",
                         constraints: list = None) -> dict:
        """生成提示词"""
        prompt = self.generator.generate(domain, task, output_format, constraints)

        # 优化
        optimized = self.optimizer.optimize(prompt)

        # 记录
        self.prompt_history.append({
            'original': prompt,
            'optimized': optimized,
            'domain': domain,
            'task': task,
            'timestamp': time.time(),
        })
        self._save()

        return {
            'original': prompt,
            'optimized': optimized,
            'domain': domain,
        }

    def evaluate_response(self, prompt: str, response: str,
                           expected: str = None) -> dict:
        """评估响应"""
        return self.evaluator.evaluate(prompt, response, expected)

    def create_ab_test(self, prompt_a: str, prompt_b: str,
                        name: str = "") -> str:
        """创建A/B测试"""
        return self.ab_test_manager.create_test(prompt_a, prompt_b, name)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'prompts_generated': len(self.prompt_history),
            'templates': len(self.templates),
            'ab_tests': len(self.ab_test_manager.tests),
            'evaluations': len(self.evaluator.evaluation_history),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("✍️ 自适应提示工程报告")
        report.append("=" * 50)
        report.append(f"\n生成提示词: {stats['prompts_generated']}")
        report.append(f"模板数量: {stats['templates']}")
        report.append(f"A/B测试: {stats['ab_tests']}")
        report.append(f"评估次数: {stats['evaluations']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = AdaptivePromptEngineeringEngine("test_prompt_engineering")

    # 生成提示词
    print("=== 提示词生成 ===")
    result = engine.generate_prompt(
        domain="Python编程",
        task="帮我写一个排序算法",
        output_format="代码",
        constraints=["使用Python3", "添加注释"]
    )
    print(f"优化后提示词:\n{result['optimized']}")

    # 评估响应
    print("\n=== 响应评估 ===")
    response = "这是一个快速排序算法的实现..."
    evaluation = engine.evaluate_response(result['optimized'], response)
    print(f"评估结果: {evaluation}")

    # 报告
    print("\n" + engine.generate_report())