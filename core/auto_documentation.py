"""
================================================================================
文档自动生成系统 (Auto Documentation System)
================================================================================

核心能力：
  1. 代码解析 - 解析代码结构
  2. 文档生成 - 自动生成文档
  3. API文档 - 生成API文档
  4. 变更日志 - 自动生成变更日志
  5. 文档更新 - 自动更新文档

设计原则：
  - 自动化：从代码自动生成
  - 准确性：文档与代码一致
  - 可读性：文档易于理解
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

class DocType(Enum):
    API = "api"                  # API文档
    MODULE = "module"            # 模块文档
    CHANGELOG = "changelog"      # 变更日志
    README = "readme"            # README

@dataclass
class FunctionDoc:
    """函数文档"""
    name: str
    description: str
    parameters: list
    return_type: str
    examples: list = field(default_factory=list)

@dataclass
class ClassDoc:
    """类文档"""
    name: str
    description: str
    methods: list
    attributes: list = field(default_factory=list)

@dataclass
class ModuleDoc:
    """模块文档"""
    name: str
    description: str
    functions: list
    classes: list
    imports: list = field(default_factory=list)

@dataclass
class ChangeLogEntry:
    """变更日志条目"""
    version: str
    date: str
    changes: list
    author: str = ""


# ============================================================================
# 代码解析器
# ============================================================================

class CodeParser:
    """代码解析器"""

    def __init__(self):
        self.parsed_modules: dict[str, ModuleDoc] = {}

    def parse_python(self, code: str, module_name: str = "") -> ModuleDoc:
        """解析Python代码"""
        functions = self._extract_functions(code)
        classes = self._extract_classes(code)
        imports = self._extract_imports(code)

        # 提取模块描述
        description = self._extract_module_description(code)

        module_doc = ModuleDoc(
            name=module_name,
            description=description,
            functions=functions,
            classes=classes,
            imports=imports,
        )

        self.parsed_modules[module_name] = module_doc
        return module_doc

    def _extract_functions(self, code: str) -> list:
        """提取函数"""
        functions = []

        # 匹配函数定义
        pattern = r'def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?:'
        matches = re.finditer(pattern, code)

        for match in matches:
            func_name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3) or "Any"

            # 解析参数
            parameters = self._parse_parameters(params_str)

            # 提取文档字符串
            description = self._extract_docstring(code, match.end())

            functions.append(FunctionDoc(
                name=func_name,
                description=description,
                parameters=parameters,
                return_type=return_type,
            ))

        return functions

    def _extract_classes(self, code: str) -> list:
        """提取类"""
        classes = []

        # 匹配类定义
        pattern = r'class\s+(\w+)(?:\((.*?)\))?:'
        matches = re.finditer(pattern, code)

        for match in matches:
            class_name = match.group(1)
            description = self._extract_docstring(code, match.end())

            classes.append(ClassDoc(
                name=class_name,
                description=description,
                methods=[],
            ))

        return classes

    def _extract_imports(self, code: str) -> list:
        """提取导入"""
        imports = []

        # 匹配import语句
        patterns = [
            r'import\s+(\w+)',
            r'from\s+(\w+)\s+import',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                imports.append(match.group(1))

        return list(set(imports))

    def _extract_module_description(self, code: str) -> str:
        """提取模块描述"""
        # 查找模块级别的文档字符串
        match = re.search(r'^"""(.*?)"""', code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_docstring(self, code: str, start_pos: int) -> str:
        """提取文档字符串"""
        # 从start_pos开始查找文档字符串
        remaining = code[start_pos:]
        match = re.search(r'"""(.*?)"""', remaining, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_parameters(self, params_str: str) -> list:
        """解析参数"""
        if not params_str.strip():
            return []

        parameters = []
        for param in params_str.split(','):
            param = param.strip()
            if ':' in param:
                name, type_hint = param.split(':', 1)
                parameters.append({
                    'name': name.strip(),
                    'type': type_hint.strip(),
                })
            else:
                parameters.append({
                    'name': param,
                    'type': 'Any',
                })

        return parameters


# ============================================================================
# 文档生成器
# ============================================================================

class DocGenerator:
    """文档生成器"""

    def __init__(self):
        self.templates = {
            DocType.API: self._generate_api_doc,
            DocType.MODULE: self._generate_module_doc,
            DocType.README: self._generate_readme,
        }

    def generate(self, doc_type: DocType,
                  data: dict) -> str:
        """生成文档"""
        generator = self.templates.get(doc_type)
        if generator:
            return generator(data)
        return ""

    def _generate_api_doc(self, data: dict) -> str:
        """生成API文档"""
        module = data.get('module')
        if not module:
            return ""

        lines = [f"# {module.name} API文档\n"]
        lines.append(f"{module.description}\n")

        if module.functions:
            lines.append("## 函数\n")
            for func in module.functions:
                lines.append(f"### {func.name}\n")
                lines.append(f"{func.description}\n")
                if func.parameters:
                    lines.append("**参数:**\n")
                    for param in func.parameters:
                        lines.append(f"- `{param['name']}` ({param['type']})")
                lines.append(f"\n**返回值:** `{func.return_type}`\n")

        return "\n".join(lines)

    def _generate_module_doc(self, data: dict) -> str:
        """生成模块文档"""
        module = data.get('module')
        if not module:
            return ""

        lines = [f"# {module.name}\n"]
        lines.append(f"{module.description}\n")

        if module.imports:
            lines.append("## 依赖\n")
            for imp in module.imports:
                lines.append(f"- {imp}")
            lines.append("")

        return "\n".join(lines)

    def _generate_readme(self, data: dict) -> str:
        """生成README"""
        project_name = data.get('name', 'Project')
        description = data.get('description', '')

        lines = [f"# {project_name}\n"]
        lines.append(f"{description}\n")
        lines.append("## 安装\n")
        lines.append("```bash\npip install {project_name}\n```\n")
        lines.append("## 使用\n")
        lines.append("```python\nimport {project_name}\n```\n")

        return "\n".join(lines)


# ============================================================================
# 文档自动生成引擎
# ============================================================================

class AutoDocumentationEngine:
    """
    文档自动生成引擎 - 整合所有组件

    核心功能：
    1. 解析代码结构
    2. 自动生成文档
    3. 管理文档版本
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "documentation"
        os.makedirs(storage_dir, exist_ok=True)

        self.parser = CodeParser()
        self.generator = DocGenerator()

        self.generated_docs: dict[str, str] = {}
        self.changelog: list[ChangeLogEntry] = []

    def generate_from_code(self, code: str,
                            module_name: str,
                            doc_type: DocType = DocType.API) -> str:
        """从代码生成文档"""
        # 解析代码
        module = self.parser.parse_python(code, module_name)

        # 生成文档
        doc = self.generator.generate(doc_type, {'module': module})

        # 存储
        self.generated_docs[f"{module_name}_{doc_type.value}"] = doc

        return doc

    def add_changelog_entry(self, version: str,
                             changes: list,
                             author: str = ""):
        """添加变更日志"""
        entry = ChangeLogEntry(
            version=version,
            date=datetime.now().strftime("%Y-%m-%d"),
            changes=changes,
            author=author,
        )
        self.changelog.append(entry)

    def generate_changelog(self) -> str:
        """生成变更日志"""
        lines = ["# 变更日志\n"]

        for entry in sorted(self.changelog, key=lambda e: e.date, reverse=True):
            lines.append(f"## {entry.version} ({entry.date})\n")
            for change in entry.changes:
                lines.append(f"- {change}")
            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'generated_docs': len(self.generated_docs),
            'parsed_modules': len(self.parser.parsed_modules),
            'changelog_entries': len(self.changelog),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("📝 文档自动生成报告")
        report.append("=" * 50)
        report.append(f"\n生成文档数: {stats['generated_docs']}")
        report.append(f"解析模块数: {stats['parsed_modules']}")
        report.append(f"变更日志条目: {stats['changelog_entries']}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = AutoDocumentationEngine("test_documentation")

    # 示例代码
    code = '''
def calculate_sum(a: int, b: int) -> int:
    """
    计算两个数的和
    
    参数:
        a: 第一个数
        b: 第二个数
    
    返回:
        两数之和
    """
    return a + b

class Calculator:
    """
    计算器类
    """
    
    def add(self, a: int, b: int) -> int:
        """加法"""
        return a + b
'''

    # 生成文档
    print("=== 生成API文档 ===")
    doc = engine.generate_from_code(code, "calculator", DocType.API)
    print(doc)

    # 添加变更日志
    engine.add_changelog_entry("1.0.0", ["初始版本", "实现基本计算功能"])

    print("\n=== 变更日志 ===")
    print(engine.generate_changelog())

    # 报告
    print("\n" + engine.generate_report())