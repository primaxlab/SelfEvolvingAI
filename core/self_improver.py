"""
================================================================================
层次4：代码自改进系统 (Code Self-Improvement System)
================================================================================

核心能力：
  1. 代码分析 - 理解代码结构、复杂度、依赖关系
  2. 缺陷检测 - 发现bug、性能问题、安全漏洞
  3. 自动修复 - 生成修复方案并应用
  4. 测试验证 - 验证修复是否正确
  5. 重构优化 - 改进代码质量
  6. 版本管理 - 管理代码演进历史

设计原则：
  - 安全第一：所有修改必须可回滚
  - 测试驱动：修改后必须验证
  - 渐进式：小步改进，不搞大重构
  - 学习导向：每次改进都记录教训
"""

import ast
import os
import re
import json
import time
import hashlib
import difflib
import subprocess
import tempfile
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path


# ============================================================================
# 数据结构
# ============================================================================

class IssueType(Enum):
    BUG = "bug"                    # 逻辑错误
    PERFORMANCE = "performance"    # 性能问题
    SECURITY = "security"         # 安全漏洞
    STYLE = "style"               # 代码风格
    COMPLEXITY = "complexity"     # 复杂度过高
    DUPLICATION = "duplication"   # 重复代码
    MISSING_TEST = "missing_test" # 缺少测试
    DEPENDENCY = "dependency"     # 依赖问题

class IssueSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class FixStatus(Enum):
    PENDING = "pending"
    APPLIED = "applied"
    VERIFIED = "verified"
    REVERTED = "reverted"
    FAILED = "failed"

@dataclass
class CodeIssue:
    """代码问题"""
    id: str
    file_path: str
    line_number: int
    issue_type: IssueType
    severity: IssueSeverity
    description: str
    suggestion: str = ""
    code_snippet: str = ""
    detected_at: float = field(default_factory=time.time)

@dataclass
class CodeFix:
    """代码修复"""
    id: str
    issue_id: str
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    status: FixStatus = FixStatus.PENDING
    applied_at: float = 0.0
    verified_at: float = 0.0
    test_result: Optional[dict] = None

@dataclass
class CodeSnapshot:
    """代码快照"""
    id: str
    file_path: str
    content: str
    hash: str
    timestamp: float = field(default_factory=time.time)
    description: str = ""

@dataclass
class ImprovementRecord:
    """改进记录"""
    id: str
    file_path: str
    issue: CodeIssue
    fix: CodeFix
    before_metrics: dict = field(default_factory=dict)
    after_metrics: dict = field(default_factory=dict)
    lesson_learned: str = ""
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 代码分析器
# ============================================================================

class CodeAnalyzer:
    """代码分析器 - 理解代码结构和质量"""

    def __init__(self):
        self.complexity_threshold = 10  # 圈复杂度阈值
        self.function_length_threshold = 50  # 函数长度阈值
        self.file_length_threshold = 500  # 文件长度阈值

    def analyze_file(self, file_path: str) -> dict:
        """分析单个文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {
                'file': file_path,
                'error': f'语法错误: {e}',
                'issues': [],
                'metrics': {}
            }

        issues = []
        metrics = {
            'lines': len(content.splitlines()),
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'avg_complexity': 0,
            'max_complexity': 0,
        }

        # 遍历AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics['functions'] += 1
                func_issues = self._analyze_function(node, file_path, content)
                issues.extend(func_issues)

            elif isinstance(node, ast.ClassDef):
                metrics['classes'] += 1

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics['imports'] += 1

        # 计算复杂度
        complexities = [self._calc_complexity(node) for node in ast.walk(tree)
                       if isinstance(node, ast.FunctionDef)]
        if complexities:
            metrics['avg_complexity'] = sum(complexities) / len(complexities)
            metrics['max_complexity'] = max(complexities)

        return {
            'file': file_path,
            'issues': [asdict(i) for i in issues],
            'metrics': metrics,
        }

    def _analyze_function(self, node: ast.FunctionDef, file_path: str,
                          content: str) -> list:
        """分析单个函数"""
        issues = []
        lines = content.splitlines()

        # 1. 函数长度检查
        func_length = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        if func_length > self.function_length_threshold:
            issues.append(CodeIssue(
                id=f"len_{node.name}_{node.lineno}",
                file_path=file_path,
                line_number=node.lineno,
                issue_type=IssueType.COMPLEXITY,
                severity=IssueSeverity.MEDIUM,
                description=f"函数 {node.name} 过长 ({func_length}行)",
                suggestion="考虑拆分为更小的函数",
            ))

        # 2. 圈复杂度检查
        complexity = self._calc_complexity(node)
        if complexity > self.complexity_threshold:
            issues.append(CodeIssue(
                id=f"cx_{node.name}_{node.lineno}",
                file_path=file_path,
                line_number=node.lineno,
                issue_type=IssueType.COMPLEXITY,
                severity=IssueSeverity.HIGH,
                description=f"函数 {node.name} 复杂度过高 ({complexity})",
                suggestion="减少条件分支，使用策略���式或提前返回",
            ))

        # 3. 参数数量检查
        if len(node.args.args) > 5:
            issues.append(CodeIssue(
                id=f"args_{node.name}_{node.lineno}",
                file_path=file_path,
                line_number=node.lineno,
                issue_type=IssueType.STYLE,
                severity=IssueSeverity.LOW,
                description=f"函数 {node.name} 参数过多 ({len(node.args.args)}个)",
                suggestion="考虑使用配置对象或数据类封装参数",
            ))

        # 4. 缺少文档字符串
        if not (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant) and isinstance(getattr(node.body[0].value, 'value', None), str)):
            issues.append(CodeIssue(
                id=f"doc_{node.name}_{node.lineno}",
                file_path=file_path,
                line_number=node.lineno,
                issue_type=IssueType.STYLE,
                severity=IssueSeverity.LOW,
                description=f"函数 {node.name} 缺少文档字符串",
                suggestion="添加docstring说明函数用途、参数和返回值",
            ))

        # 5. 裸异常捕获
        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler) and child.type is None:
                issues.append(CodeIssue(
                    id=f"bare_{node.name}_{child.lineno}",
                    file_path=file_path,
                    line_number=child.lineno,
                    issue_type=IssueType.BUG,
                    severity=IssueSeverity.HIGH,
                    description="裸异常捕获: except:",
                    suggestion="指定具体异常类型，避免吞掉所有异常",
                ))

        return issues

    def _calc_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def analyze_dependencies(self, file_path: str) -> dict:
        """分析依赖关系"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        return {
            'file': file_path,
            'imports': imports,
            'count': len(imports),
        }


# ============================================================================
# 缺陷检测器
# ============================================================================

class BugDetector:
    """缺陷检测器 - 发现代码中的问题"""

    def __init__(self):
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> list:
        """加载缺陷模式库"""
        return [
            # 常见bug模式
            {
                'pattern': r'except\s*:',
                'type': IssueType.BUG,
                'severity': IssueSeverity.HIGH,
                'message': '裸异常捕获',
                'suggestion': '指定具体异常类型',
            },
            {
                'pattern': r'except\s+\w+\s*:\s*pass',
                'type': IssueType.BUG,
                'severity': IssueSeverity.MEDIUM,
                'message': '静默吞掉异常',
                'suggestion': '至少记录日志',
            },
            {
                'pattern': r'==\s*True|==\s*False|==\s*None',
                'type': IssueType.STYLE,
                'severity': IssueSeverity.LOW,
                'message': '使用 == 而不是 is 进行比较',
                'suggestion': '使用 is True/False/None',
            },
            {
                'pattern': r'def\s+\w+\(.*=\s*\[\]|def\s+\w+\(.*=\s*\{\}',
                'type': IssueType.BUG,
                'severity': IssueSeverity.CRITICAL,
                'message': '可变默认参数',
                'suggestion': '使用 None 作为默认值，在函数体内初始化',
            },
            {
                'pattern': r'time\.sleep\(\d+\)',
                'type': IssueType.PERFORMANCE,
                'severity': IssueSeverity.LOW,
                'message': '硬编码的sleep',
                'suggestion': '考虑使用异步等待或事件驱动',
            },
            # 安全问题
            {
                'pattern': r'eval\(|exec\(',
                'type': IssueType.SECURITY,
                'severity': IssueSeverity.CRITICAL,
                'message': '使用eval/exec存在代码注入风险',
                'suggestion': '使用ast.literal_eval或重构逻辑',
            },
            {
                'pattern': r'subprocess\.call\(.*shell\s*=\s*True',
                'type': IssueType.SECURITY,
                'severity': IssueSeverity.HIGH,
                'message': 'shell=True存在命令注入风险',
                'suggestion': '使用列表形式的参数，避免shell=True',
            },
            {
                'pattern': r'pickle\.loads?\(',
                'type': IssueType.SECURITY,
                'severity': IssueSeverity.HIGH,
                'message': 'pickle反序列化可能执行任意代码',
                'suggestion': '使用json或其他安全的序列化方式',
            },
        ]

    def detect(self, file_path: str) -> list:
        """检测文件中的缺陷"""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        issues = []
        for i, line in enumerate(lines, 1):
            for pattern_info in self.patterns:
                if re.search(pattern_info['pattern'], line):
                    issues.append(CodeIssue(
                        id=f"det_{hashlib.md5(f'{file_path}:{i}'.encode()).hexdigest()[:8]}",
                        file_path=file_path,
                        line_number=i,
                        issue_type=pattern_info['type'],
                        severity=pattern_info['severity'],
                        description=pattern_info['message'],
                        suggestion=pattern_info['suggestion'],
                        code_snippet=line.strip(),
                    ))

        return issues

    def detect_unused_variables(self, file_path: str) -> list:
        """检测未使用的变量"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        issues = []
        defined = set()
        used = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    defined.add((node.id, node.lineno))
                elif isinstance(node.ctx, ast.Load):
                    used.add(node.id)

        for var_name, line_no in defined:
            if var_name not in used and not var_name.startswith('_'):
                issues.append(CodeIssue(
                    id=f"unused_{var_name}_{line_no}",
                    file_path=file_path,
                    line_number=line_no,
                    issue_type=IssueType.STYLE,
                    severity=IssueSeverity.LOW,
                    description=f"变量 {var_name} 已定义但未使用",
                    suggestion="删除未使用的变量或添加 _ 前缀",
                ))

        return issues


# ============================================================================
# 自动修复器
# ============================================================================

class AutoFixer:
    """自动修复器 - 生成并应用修复方案"""

    def __init__(self):
        self.fix_strategies = {
            IssueType.BUG: self._fix_bug,
            IssueType.STYLE: self._fix_style,
            IssueType.SECURITY: self._fix_security,
            IssueType.PERFORMANCE: self._fix_performance,
        }

    def generate_fix(self, issue: CodeIssue) -> Optional[CodeFix]:
        """根据问题生成修复方案"""
        strategy = self.fix_strategies.get(issue.issue_type)
        if strategy:
            return strategy(issue)
        return None

    def _fix_bug(self, issue: CodeIssue) -> Optional[CodeFix]:
        """修复bug类问题"""
        with open(issue.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if issue.line_number > len(lines):
            return None

        original = lines[issue.line_number - 1]
        fixed = original

        # 裸异常捕获 → 指定Exception
        if 'except:' in original:
            fixed = original.replace('except:', 'except Exception:')

        # 可变默认参数
        if 'def ' in original and ('=[]' in original or '={}' in original):
            fixed = re.sub(r'=\s*\[\]', '= None', original)
            fixed = re.sub(r'=\s*\{\}', '= None', fixed)
            # 需要在函数体开头添加初始化逻辑，这里只标记
            return CodeFix(
                id=f"fix_{issue.id}",
                issue_id=issue.id,
                file_path=issue.file_path,
                original_code=original,
                fixed_code=fixed,
                explanation="将可变默认参数改为None，需要手动添加函数体初始化逻辑",
            )

        if fixed != original:
            return CodeFix(
                id=f"fix_{issue.id}",
                issue_id=issue.id,
                file_path=issue.file_path,
                original_code=original,
                fixed_code=fixed,
                explanation=f"修复: {issue.description}",
            )

        return None

    def _fix_style(self, issue: CodeIssue) -> Optional[CodeFix]:
        """修复风格问题"""
        with open(issue.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if issue.line_number > len(lines):
            return None

        original = lines[issue.line_number - 1]
        fixed = original

        # == True → is True
        if '== True' in original:
            fixed = original.replace('== True', 'is True')
        elif '== False' in original:
            fixed = original.replace('== False', 'is False')
        elif '== None' in original:
            fixed = original.replace('== None', 'is None')

        if fixed != original:
            return CodeFix(
                id=f"fix_{issue.id}",
                issue_id=issue.id,
                file_path=issue.file_path,
                original_code=original,
                fixed_code=fixed,
                explanation="使用 is 替代 == 进行None/True/False比较",
            )

        return None

    def _fix_security(self, issue: CodeIssue) -> Optional[CodeFix]:
        """修复安全问题"""
        with open(issue.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if issue.line_number > len(lines):
            return None

        original = lines[issue.line_number - 1]

        # eval → ast.literal_eval
        if 'eval(' in original and 'literal_eval' not in original:
            fixed = original.replace('eval(', 'ast.literal_eval(')
            return CodeFix(
                id=f"fix_{issue.id}",
                issue_id=issue.id,
                file_path=issue.file_path,
                original_code=original,
                fixed_code=fixed,
                explanation="使用ast.literal_eval替代eval以防止代码注入",
            )

        return None

    def _fix_performance(self, issue: CodeIssue) -> Optional[CodeFix]:
        """修复性能问题"""
        # 性能问题通常需要更复杂的分析，这里只做标记
        return None

    def apply_fix(self, fix: CodeFix) -> bool:
        """应用修复"""
        try:
            with open(fix.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content.replace(fix.original_code, fix.fixed_code, 1)

            with open(fix.file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            fix.status = FixStatus.APPLIED
            fix.applied_at = time.time()
            return True

        except Exception as e:
            fix.status = FixStatus.FAILED
            return False

    def revert_fix(self, fix: CodeFix) -> bool:
        """回滚修复"""
        try:
            with open(fix.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content.replace(fix.fixed_code, fix.original_code, 1)

            with open(fix.file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            fix.status = FixStatus.REVERTED
            return True

        except Exception:
            return False


# ============================================================================
# 测试验证器
# ============================================================================

class TestValidator:
    """测试验证器 - 验证修复是否正确"""

    def __init__(self, test_dir: str = None):
        self.test_dir = test_dir

    def run_syntax_check(self, file_path: str) -> dict:
        """语法检查"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return {'success': True, 'error': None}
        except SyntaxError as e:
            return {'success': False, 'error': str(e)}

    def run_import_check(self, file_path: str) -> dict:
        """导入检查"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # 尝试导入
            missing = []
            for imp in imports:
                try:
                    __import__(imp.split('.')[0])
                except ImportError:
                    missing.append(imp)

            return {
                'success': len(missing) == 0,
                'missing': missing,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_tests(self, test_path: str = None) -> dict:
        """运行测试"""
        if test_path is None and self.test_dir is None:
            return {'success': False, 'error': '未指定测试目录'}

        target = test_path or self.test_dir

        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', target, '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '测试超时'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================================
# 版本管理器
# ============================================================================

class VersionManager:
    """版本管理器 - 管理代码演进历史"""

    def __init__(self, snapshot_dir: str = None):
        self.snapshot_dir = snapshot_dir or tempfile.mkdtemp()
        os.makedirs(self.snapshot_dir, exist_ok=True)
        self.history: list[CodeSnapshot] = []

    def create_snapshot(self, file_path: str, description: str = "") -> CodeSnapshot:
        """创建代码快照"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        snapshot = CodeSnapshot(
            id=f"snap_{int(time.time())}_{content_hash}",
            file_path=file_path,
            content=content,
            hash=content_hash,
            description=description,
        )

        # 保存到磁盘
        snap_path = os.path.join(self.snapshot_dir, f"{snapshot.id}.py")
        with open(snap_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.history.append(snapshot)
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """恢复到指定快照"""
        snapshot = None
        for s in self.history:
            if s.id == snapshot_id:
                snapshot = s
                break

        if snapshot is None:
            return False

        try:
            with open(snapshot.file_path, 'w', encoding='utf-8') as f:
                f.write(snapshot.content)
            return True
        except Exception:
            return False

    def get_diff(self, snapshot_id1: str, snapshot_id2: str) -> str:
        """比较两个快照的差异"""
        snap1 = next((s for s in self.history if s.id == snapshot_id1), None)
        snap2 = next((s for s in self.history if s.id == snapshot_id2), None)

        if not snap1 or not snap2:
            return ""

        diff = difflib.unified_diff(
            snap1.content.splitlines(keepends=True),
            snap2.content.splitlines(keepends=True),
            fromfile=f"snapshot:{snapshot_id1}",
            tofile=f"snapshot:{snapshot_id2}",
        )
        return ''.join(diff)

    def get_history(self, file_path: str = None) -> list:
        """获取历史记录"""
        if file_path:
            return [asdict(s) for s in self.history if s.file_path == file_path]
        return [asdict(s) for s in self.history]


# ============================================================================
# 代码自改进引擎
# ============================================================================

class CodeSelfImprover:
    """
    代码自改进引擎 - 整合所有组件

    工作流程：
    1. 分析代码 → 发现问题
    2. 生成修复方案
    3. 创建快照（备份）
    4. 应用修复
    5. 测试验证
    6. 成功则保留，失败则回滚
    7. 记录经验教训
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = project_dir or os.getcwd()
        self.analyzer = CodeAnalyzer()
        self.detector = BugDetector()
        self.fixer = AutoFixer()
        self.validator = TestValidator()
        self.version_mgr = VersionManager(
            os.path.join(self.project_dir, '.snapshots')
        )
        self.improvements: list[ImprovementRecord] = []
        self.lessons: list[str] = []

    def scan_project(self, extensions: list = None) -> dict:
        """扫描整个项目"""
        if extensions is None:
            extensions = ['.py']

        all_issues = []
        files_scanned = 0

        for root, dirs, files in os.walk(self.project_dir):
            # 跳过隐藏目录和虚拟环境
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__'
                       and d != 'venv' and d != 'node_modules']

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    files_scanned += 1

                    # 分析
                    analysis = self.analyzer.analyze_file(file_path)
                    issues = [CodeIssue(**i) for i in analysis.get('issues', [])]

                    # 检测缺陷
                    detected = self.detector.detect(file_path)
                    issues.extend(detected)

                    # 未使用变量
                    unused = self.detector.detect_unused_variables(file_path)
                    issues.extend(unused)

                    all_issues.extend(issues)

        # 按严重程度排序
        all_issues.sort(key=lambda x: x.severity.value, reverse=True)

        return {
            'files_scanned': files_scanned,
            'total_issues': len(all_issues),
            'critical': sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL),
            'high': sum(1 for i in all_issues if i.severity == IssueSeverity.HIGH),
            'medium': sum(1 for i in all_issues if i.severity == IssueSeverity.MEDIUM),
            'low': sum(1 for i in all_issues if i.severity == IssueSeverity.LOW),
            'issues': [asdict(i) for i in all_issues],
        }

    def improve_file(self, file_path: str, auto_apply: bool = False) -> dict:
        """改进单个文件"""
        # 1. 分析
        analysis = self.analyzer.analyze_file(file_path)
        detected = self.detector.detect(file_path)
        all_issues = [CodeIssue(**i) for i in analysis.get('issues', [])] + detected

        if not all_issues:
            return {'status': 'no_issues', 'message': '未发现问题'}

        # 2. 生成修复
        fixes = []
        for issue in all_issues:
            fix = self.fixer.generate_fix(issue)
            if fix:
                fixes.append((issue, fix))

        if not fixes:
            return {'status': 'no_fixes', 'message': '无法自动生成修复方案'}

        results = []

        # 3. 逐个应用修复
        for issue, fix in fixes:
            # 创建快照
            snapshot = self.version_mgr.create_snapshot(
                file_path,
                f"修复前: {issue.description}"
            )

            if auto_apply:
                # 应用修复
                if self.fixer.apply_fix(fix):
                    # 验证
                    syntax_ok = self.validator.run_syntax_check(file_path)

                    if syntax_ok['success']:
                        fix.status = FixStatus.VERIFIED
                        fix.verified_at = time.time()

                        # 记录改进
                        record = ImprovementRecord(
                            id=f"imp_{int(time.time())}",
                            file_path=file_path,
                            issue=issue,
                            fix=fix,
                        )
                        self.improvements.append(record)

                        results.append({
                            'issue': issue.description,
                            'fix': fix.explanation,
                            'status': 'applied',
                        })
                    else:
                        # 回滚
                        self.fixer.revert_fix(fix)
                        self.version_mgr.restore_snapshot(snapshot.id)

                        results.append({
                            'issue': issue.description,
                            'status': 'reverted',
                            'reason': syntax_ok['error'],
                        })

                        # 记录教训
                        self.lessons.append(
                            f"修复 {issue.description} 导致语法错误: {syntax_ok['error']}"
                        )
                else:
                    results.append({
                        'issue': issue.description,
                        'status': 'apply_failed',
                    })
            else:
                results.append({
                    'issue': issue.description,
                    'suggestion': fix.explanation,
                    'original': fix.original_code.strip(),
                    'fixed': fix.fixed_code.strip(),
                    'status': 'suggested',
                })

        return {
            'status': 'completed',
            'file': file_path,
            'fixes': results,
        }

    def improve_project(self, auto_apply: bool = False,
                        max_fixes: int = 10) -> dict:
        """改进整个项目"""
        scan_result = self.scan_project()

        if scan_result['total_issues'] == 0:
            return {'status': 'clean', 'message': '项目代码质量良好'}

        # 按严重程度修复
        issues = [CodeIssue(**i) for i in scan_result['issues']]
        issues.sort(key=lambda x: x.severity.value, reverse=True)

        fixed_count = 0
        results = []

        for issue in issues[:max_fixes]:
            result = self.improve_file(issue.file_path, auto_apply=auto_apply)
            if result.get('fixes'):
                results.append(result)
                fixed_count += len(result['fixes'])

        return {
            'status': 'completed',
            'scan': scan_result,
            'improvements': results,
            'total_fixed': fixed_count,
            'lessons': self.lessons,
        }

    def get_lessons(self) -> list:
        """获取经验教训"""
        return self.lessons

    def get_improvement_history(self) -> list:
        """获取改进历史"""
        return [asdict(r) for r in self.improvements]

    def generate_report(self) -> str:
        """生成改进报告"""
        report = []
        report.append("=" * 60)
        report.append("代码自改进报告")
        report.append("=" * 60)
        report.append(f"项目目录: {self.project_dir}")
        report.append(f"改进次数: {len(self.improvements)}")
        report.append(f"经验教训: {len(self.lessons)}")
        report.append("")

        if self.improvements:
            report.append("改进记录:")
            for imp in self.improvements[-10:]:  # 最近10条
                report.append(f"  - {imp.file_path}: {imp.issue.description}")
                report.append(f"    修复: {imp.fix.explanation}")
                report.append("")

        if self.lessons:
            report.append("经验教训:")
            for lesson in self.lessons[-5:]:  # 最近5条
                report.append(f"  - {lesson}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    # 创建测试文件
    test_code = '''
import os
import sys

def bad_function(x,y=[]):
    """测试函数"""
    try:
        result = eval(x)
        if result == True:
            return result
    except:
        pass
    return None

class TestClass:
    def method_without_doc(self):
        x = 1
        y = 2
        z = 3
        return x + y
'''

    test_file = "test_sample.py"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)

    # 测试自改进
    improver = CodeSelfImprover()

    # 扫描
    print("=== 扫描结果 ===")
    scan = improver.scan_project()
    print(f"扫描文件: {scan['files_scanned']}")
    print(f"发现问题: {scan['total_issues']}")
    print(f"  严重: {scan['critical']}")
    print(f"  高危: {scan['high']}")
    print(f"  中等: {scan['medium']}")
    print(f"  低危: {scan['low']}")

    # 改进
    print("\n=== 改进结果 ===")
    result = improver.improve_file(test_file, auto_apply=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 报告
    print("\n" + improver.generate_report())

    # 清理
    os.remove(test_file)