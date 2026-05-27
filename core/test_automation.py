"""
================================================================================
测试自动化系统 (Test Automation System)
================================================================================

核心能力：
  1. 测试生成 - 自动生成测试用例
  2. 测试执行 - 自动执行测试
  3. 结果分析 - 分析测试结果
  4. 覆盖率计算 - 计算代码覆盖率
  5. 回归测试 - 自动回归测试

设计原则：
  - 全面覆盖：尽可能覆盖所有代码路径
  - 自动化：减少人工干预
  - 可重复：测试可重复执行
"""

import json
import os
import time
import hashlib
import re
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class TestStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class TestType(Enum):
    UNIT = "unit"                # 单元测试
    INTEGRATION = "integration"  # 集成测试
    FUNCTIONAL = "functional"    # 功能测试
    REGRESSION = "regression"    # 回归测试

@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    test_type: TestType
    function_name: str
    input_data: Any
    expected_output: Any
    status: TestStatus = TestStatus.PENDING
    actual_output: Any = None
    error_message: str = ""
    duration: float = 0.0
    created_at: float = field(default_factory=time.time)

@dataclass
class TestSuite:
    """测试套件"""
    id: str
    name: str
    test_cases: list
    status: TestStatus = TestStatus.PENDING
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration: float = 0.0

@dataclass
class CoverageReport:
    """覆盖率报告"""
    total_lines: int
    covered_lines: int
    coverage_percentage: float
    uncovered_lines: list


# ============================================================================
# 测试生成器
# ============================================================================

class TestGenerator:
    """测试生成器"""

    def __init__(self):
        self.generated_tests: list[TestCase] = []

    def generate_from_function(self, func_name: str,
                                 parameters: list,
                                 return_type: str = None) -> list:
        """从函数生成测试"""
        tests = []

        # 生成基本测试
        basic_test = TestCase(
            id=hashlib.md5(f"{func_name}_basic".encode()).hexdigest()[:12],
            name=f"test_{func_name}_basic",
            test_type=TestType.UNIT,
            function_name=func_name,
            input_data=self._generate_sample_input(parameters),
            expected_output=self._generate_expected_output(return_type),
        )
        tests.append(basic_test)

        # 生成边界测试
        boundary_test = TestCase(
            id=hashlib.md5(f"{func_name}_boundary".encode()).hexdigest()[:12],
            name=f"test_{func_name}_boundary",
            test_type=TestType.UNIT,
            function_name=func_name,
            input_data=self._generate_boundary_input(parameters),
            expected_output=self._generate_expected_output(return_type),
        )
        tests.append(boundary_test)

        self.generated_tests.extend(tests)
        return tests

    def _generate_sample_input(self, parameters: list) -> dict:
        """生成样本输入"""
        sample = {}
        for param in parameters:
            if 'int' in param.lower():
                sample[param] = 1
            elif 'str' in param.lower():
                sample[param] = "test"
            elif 'list' in param.lower():
                sample[param] = [1, 2, 3]
            elif 'bool' in param.lower():
                sample[param] = True
            else:
                sample[param] = None
        return sample

    def _generate_boundary_input(self, parameters: list) -> dict:
        """生成边界输入"""
        boundary = {}
        for param in parameters:
            if 'int' in param.lower():
                boundary[param] = 0
            elif 'str' in param.lower():
                boundary[param] = ""
            elif 'list' in param.lower():
                boundary[param] = []
            else:
                boundary[param] = None
        return boundary

    def _generate_expected_output(self, return_type: str) -> Any:
        """生成预期输出"""
        if return_type and 'int' in return_type.lower():
            return 0
        elif return_type and 'str' in return_type.lower():
            return ""
        elif return_type and 'list' in return_type.lower():
            return []
        elif return_type and 'bool' in return_type.lower():
            return True
        return None


# ============================================================================
# 测试执行器
# ============================================================================

class TestExecutor:
    """测试执行器"""

    def __init__(self):
        self.test_functions: dict[str, Callable] = {}
        self.execution_history: list[dict] = []

    def register_function(self, func_name: str, func: Callable):
        """注册测试函数"""
        self.test_functions[func_name] = func

    def execute_test(self, test_case: TestCase) -> TestCase:
        """执行单个测试"""
        start_time = time.time()

        try:
            func = self.test_functions.get(test_case.function_name)
            if not func:
                test_case.status = TestStatus.ERROR
                test_case.error_message = f"函数 {test_case.function_name} 未注册"
                return test_case

            # 执行测试
            actual = func(**test_case.input_data)
            test_case.actual_output = actual

            # 比较结果
            if self._compare_outputs(actual, test_case.expected_output):
                test_case.status = TestStatus.PASSED
            else:
                test_case.status = TestStatus.FAILED
                test_case.error_message = f"期望 {test_case.expected_output}，实际 {actual}"

        except Exception as e:
            test_case.status = TestStatus.ERROR
            test_case.error_message = str(e)

        test_case.duration = time.time() - start_time

        # 记录执行
        self.execution_history.append({
            'test_id': test_case.id,
            'status': test_case.status.value,
            'duration': test_case.duration,
            'timestamp': time.time(),
        })

        return test_case

    def _compare_outputs(self, actual: Any, expected: Any) -> bool:
        """比较输出"""
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False
        return actual == expected

    def execute_suite(self, test_suite: TestSuite) -> TestSuite:
        """执行测试套件"""
        start_time = time.time()

        for test_case in test_suite.test_cases:
            self.execute_test(test_case)

        # 统计结果
        test_suite.passed = sum(1 for t in test_suite.test_cases
                               if t.status == TestStatus.PASSED)
        test_suite.failed = sum(1 for t in test_suite.test_cases
                               if t.status == TestStatus.FAILED)
        test_suite.skipped = sum(1 for t in test_suite.test_cases
                                if t.status == TestStatus.SKIPPED)

        test_suite.total_duration = time.time() - start_time

        if test_suite.failed > 0:
            test_suite.status = TestStatus.FAILED
        else:
            test_suite.status = TestStatus.PASSED

        return test_suite


# ============================================================================
# 覆盖率分析器
# ============================================================================

class CoverageAnalyzer:
    """覆盖率分析器"""

    def analyze(self, code: str, executed_lines: set) -> CoverageReport:
        """分析代码覆盖率"""
        lines = code.split('\n')
        total_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

        covered = len(executed_lines & set(range(total_lines)))
        percentage = covered / total_lines * 100 if total_lines > 0 else 0

        uncovered = [i for i in range(total_lines) if i not in executed_lines]

        return CoverageReport(
            total_lines=total_lines,
            covered_lines=covered,
            coverage_percentage=percentage,
            uncovered_lines=uncovered[:10],  # 只返回前10个
        )


# ============================================================================
# 测试自动化引擎
# ============================================================================

class TestAutomationEngine:
    """
    测试自动化引擎 - 整合所有组件

    核心功能：
    1. 自动生成测试用例
    2. 执行测试
    3. 分析结果
    4. 生成报告
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "test_automation"
        os.makedirs(storage_dir, exist_ok=True)

        self.generator = TestGenerator()
        self.executor = TestExecutor()
        self.coverage_analyzer = CoverageAnalyzer()

        self.test_suites: dict[str, TestSuite] = {}
        self.test_results: list[dict] = []

    def generate_tests(self, func_name: str,
                        parameters: list,
                        return_type: str = None) -> list:
        """生成测试"""
        return self.generator.generate_from_function(func_name, parameters, return_type)

    def create_test_suite(self, name: str,
                           test_cases: list) -> TestSuite:
        """创建测试套件"""
        suite_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

        suite = TestSuite(
            id=suite_id,
            name=name,
            test_cases=test_cases,
        )

        self.test_suites[suite_id] = suite
        return suite

    def run_tests(self, suite_id: str) -> dict:
        """运行测试"""
        suite = self.test_suites.get(suite_id)
        if not suite:
            return {'error': '测试套件不存在'}

        result = self.executor.execute_suite(suite)

        # 记录结果
        self.test_results.append({
            'suite_id': suite_id,
            'passed': result.passed,
            'failed': result.failed,
            'duration': result.total_duration,
            'timestamp': time.time(),
        })

        return {
            'suite_id': suite_id,
            'status': result.status.value,
            'passed': result.passed,
            'failed': result.failed,
            'total': len(result.test_cases),
            'duration': result.total_duration,
        }

    def get_stats(self) -> dict:
        """获取统计信息"""
        total_tests = sum(len(s.test_cases) for s in self.test_suites.values())
        total_passed = sum(s.passed for s in self.test_suites.values())
        total_failed = sum(s.failed for s in self.test_suites.values())

        return {
            'suites': len(self.test_suites),
            'total_tests': total_tests,
            'passed': total_passed,
            'failed': total_failed,
            'pass_rate': total_passed / max(1, total_tests),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🧪 测试自动化报告")
        report.append("=" * 50)
        report.append(f"\n测试套件: {stats['suites']}")
        report.append(f"总测试数: {stats['total_tests']}")
        report.append(f"通过: {stats['passed']}")
        report.append(f"失败: {stats['failed']}")
        report.append(f"通过率: {stats['pass_rate']:.1%}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = TestAutomationEngine("test_automation")

    # 注册测试函数
    def add(a: int, b: int) -> int:
        return a + b

    engine.executor.register_function("add", add)

    # 生成测试
    print("=== 生成测试 ===")
    test_cases = engine.generate_tests("add", ["a: int", "b: int"], "int")
    for tc in test_cases:
        print(f"  - {tc.name}: {tc.input_data}")

    # 创建测试套件
    suite = engine.create_test_suite("基础运算测试", test_cases)

    # 运行测试
    print("\n=== 运行测试 ===")
    result = engine.run_tests(suite.id)
    print(f"状态: {result['status']}")
    print(f"通过: {result['passed']}/{result['total']}")
    print(f"耗时: {result['duration']:.3f}秒")

    # 报告
    print("\n" + engine.generate_report())