"""
================================================================================
代码生成优化系统 (Code Generation Optimization System)
================================================================================

核心能力：
  1. 代码生成 - 根据需求生成代码
  2. 代码优化 - 优化生成的代码
  3. 模式匹配 - 匹配最佳代码模式
  4. 质量评估 - 评估代码质量
  5. 重构建议 - 提供重构建议

设计原则：
  - 模板驱动：基于最佳实践模板
  - 质量优先：生成高质量代码
  - 可维护性：代码易于维护
"""

import json
import os
import time
import hashlib
import re
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class CodePattern(Enum):
    FUNCTION = "function"        # 函数模式
    CLASS = "class"              # 类模式
    MODULE = "module"            # 模块模式
    ALGORITHM = "algorithm"      # 算法模式
    DESIGN_PATTERN = "design_pattern"  # 设计模式

@dataclass
class CodeTemplate:
    """代码模板"""
    id: str
    name: str
    pattern: CodePattern
    language: str
    template: str
    description: str
    usage_count: int = 0
    quality_score: float = 0.8

@dataclass
class CodeQuality:
    """代码质量"""
    readability: float           # 可读性
    maintainability: float       # 可维护性
    efficiency: float            # 效率
    testability: float           # 可测试性
    overall: float               # 综合分数

@dataclass
class RefactoringSuggestion:
    """重构建议"""
    line_range: tuple            # 行范围
    issue: str                   # 问题描述
    suggestion: str              # 建议
    priority: str                # 优先级


# ============================================================================
# 代码生成器
# ============================================================================

class CodeGenerator:
    """代码生成器"""

    def __init__(self):
        self.templates: dict[str, CodeTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """加载默认模板"""
        defaults = [
            CodeTemplate(
                id="func_basic",
                name="基础函数",
                pattern=CodePattern.FUNCTION,
                language="python",
                template='''def {function_name}({parameters}):
    """
    {docstring}
    """
    {body}
    return {return_value}''',
                description="基础函数模板",
            ),
            CodeTemplate(
                id="class_basic",
                name="基础类",
                pattern=CodePattern.CLASS,
                language="python",
                template='''class {class_name}:
    """
    {docstring}
    """

    def __init__(self{init_params}):
        {init_body}

    {methods}''',
                description="基础类模板",
            ),
            CodeTemplate(
                id="algorithm_sort",
                name="排序算法",
                pattern=CodePattern.ALGORITHM,
                language="python",
                template='''def {sort_name}(arr):
    """
    {sort_name}排序算法
    时间复杂度: {time_complexity}
    空间复杂度: {space_complexity}
    """
    {algorithm_body}
    return arr''',
                description="排序算法模板",
            ),
        ]

        for template in defaults:
            self.templates[template.id] = template

    def generate(self, template_id: str, variables: dict) -> str:
        """根据模板生成代码"""
        template = self.templates.get(template_id)
        if not template:
            return f"# 模板 {template_id} 不存在"

        code = template.template
        for key, value in variables.items():
            code = code.replace(f"{{{key}}}", str(value))

        template.usage_count += 1
        return code

    def generate_function(self, name: str, parameters: list,
                           return_type: str = "None",
                           body: str = "pass") -> str:
        """生成函数"""
        params_str = ", ".join(parameters)
        return f'''def {name}({params_str}) -> {return_type}:
    """
    {name}函数
    """
    {body}
'''

    def generate_class(self, name: str, methods: list,
                        base_class: str = None) -> str:
        """生成类"""
        base = f"({base_class})" if base_class else ""
        methods_str = "\n\n".join(methods)

        return f'''class {name}{base}:
    """
    {name}类
    """

    def __init__(self):
        pass

    {methods_str}
'''


# ============================================================================
# 代码优化器
# ============================================================================

class CodeOptimizer:
    """代码优化器"""

    def __init__(self):
        self.optimization_rules = [
            self._remove_redundancy,
            self._improve_naming,
            self._add_type_hints,
            self._optimize_loops,
        ]

    def optimize(self, code: str) -> str:
        """优化代码"""
        optimized = code

        for rule in self.optimization_rules:
            optimized = rule(optimized)

        return optimized

    def _remove_redundancy(self, code: str) -> str:
        """移除冗余代码"""
        # 移除多余的空行
        lines = code.split('\n')
        optimized = []
        prev_empty = False

        for line in lines:
            is_empty = line.strip() == ''
            if is_empty and prev_empty:
                continue
            optimized.append(line)
            prev_empty = is_empty

        return '\n'.join(optimized)

    def _improve_naming(self, code: str) -> str:
        """改进命名"""
        # 简化实现
        return code

    def _add_type_hints(self, code: str) -> str:
        """添加类型提示"""
        # 简化实现
        return code

    def _optimize_loops(self, code: str) -> str:
        """优化循环"""
        # 简化实现
        return code


# ============================================================================
# 代码质量评估器
# ============================================================================

class CodeQualityEvaluator:
    """代码质量评估器"""

    def evaluate(self, code: str) -> CodeQuality:
        """评估代码质量"""
        readability = self._evaluate_readability(code)
        maintainability = self._evaluate_maintainability(code)
        efficiency = self._evaluate_efficiency(code)
        testability = self._evaluate_testability(code)

        overall = (readability + maintainability + efficiency + testability) / 4

        return CodeQuality(
            readability=readability,
            maintainability=maintainability,
            efficiency=efficiency,
            testability=testability,
            overall=overall,
        )

    def _evaluate_readability(self, code: str) -> float:
        """评估可读性"""
        score = 0.5

        # 有注释
        if '"""' in code or "'''" in code:
            score += 0.2

        # 命名规范
        if re.search(r'def [a-z_]+', code):
            score += 0.1

        # 长度适中
        lines = code.split('\n')
        if 5 < len(lines) < 50:
            score += 0.1

        return min(1.0, score)

    def _evaluate_maintainability(self, code: str) -> float:
        """评估可维护性"""
        score = 0.5

        # 函数长度
        functions = re.findall(r'def \w+\(.*?\):', code)
        if functions:
            score += 0.2

        # 模块化
        classes = re.findall(r'class \w+', code)
        if classes:
            score += 0.2

        return min(1.0, score)

    def _evaluate_efficiency(self, code: str) -> float:
        """评估效率"""
        # 简化实现
        return 0.7

    def _evaluate_testability(self, code: str) -> float:
        """评估可测试性"""
        score = 0.5

        # 有返回值
        if 'return' in code:
            score += 0.2

        # 函数独立
        if code.count('def ') > 0:
            score += 0.2

        return min(1.0, score)


# ============================================================================
# 重构建议器
# ============================================================================

class RefactoringAdvisor:
    """重构建议器"""

    def analyze(self, code: str) -> list:
        """分析重构建议"""
        suggestions = []

        lines = code.split('\n')

        # 检查长函数
        func_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                if func_start is not None and i - func_start > 20:
                    suggestions.append(RefactoringSuggestion(
                        line_range=(func_start, i),
                        issue="函数过长",
                        suggestion="考虑拆分为更小的函数",
                        priority="medium",
                    ))
                func_start = i

        # 检查重复代码
        # 简化实现

        return suggestions


# ============================================================================
# 代码生成优化引擎
# ============================================================================

class CodeGenerationOptimizationEngine:
    """
    代码生成优化引擎 - 整合所有组件

    核心功能：
    1. 根据需求生成代码
    2. 优化生成的代码
    3. 评估代码质量
    4. 提供重构建议
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "code_generation"
        os.makedirs(storage_dir, exist_ok=True)

        self.generator = CodeGenerator()
        self.optimizer = CodeOptimizer()
        self.evaluator = CodeQualityEvaluator()
        self.advisor = RefactoringAdvisor()

        self.generated_code: list[dict] = []

    def generate_code(self, template_id: str,
                       variables: dict,
                       optimize: bool = True) -> dict:
        """生成代码"""
        # 生成代码
        code = self.generator.generate(template_id, variables)

        # 优化代码
        if optimize:
            code = self.optimizer.optimize(code)

        # 评估质量
        quality = self.evaluator.evaluate(code)

        # 记录
        record = {
            'template_id': template_id,
            'code': code,
            'quality': asdict(quality),
            'timestamp': time.time(),
        }
        self.generated_code.append(record)

        return {
            'code': code,
            'quality': asdict(quality),
        }

    def analyze_code(self, code: str) -> dict:
        """分析代码"""
        quality = self.evaluator.evaluate(code)
        suggestions = self.advisor.analyze(code)

        return {
            'quality': asdict(quality),
            'suggestions': [asdict(s) for s in suggestions],
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'generated_count': len(self.generated_code),
            'templates': len(self.generator.templates),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("💻 代码生成优化报告")
        report.append("=" * 50)
        report.append(f"\n生成代码数: {stats['generated_count']}")
        report.append(f"模板数量: {stats['templates']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = CodeGenerationOptimizationEngine("test_code_generation")

    # 生成函数
    print("=== 代码生成 ===")
    result = engine.generate_code(
        template_id="func_basic",
        variables={
            'function_name': 'calculate_sum',
            'parameters': 'a: int, b: int',
            'docstring': '计算两个数的和',
            'body': 'result = a + b',
            'return_value': 'result',
        }
    )
    print(f"生成的代码:\n{result['code']}")
    print(f"质量分数: {result['quality']['overall']:.2f}")

    # 分析代码
    print("\n=== 代码分析 ===")
    analysis = engine.analyze_code(result['code'])
    print(f"可读性: {analysis['quality']['readability']:.2f}")
    print(f"可维护性: {analysis['quality']['maintainability']:.2f}")

    # 报告
    print("\n" + engine.generate_report())