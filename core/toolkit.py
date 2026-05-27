"""
工具集 - AI可调用的实用工具集合

每个工具都是独立的、可被LLM Function Calling调用的
"""

import json
import os
import time
import hashlib
import math
import csv
import re
import urllib.request
import urllib.parse
import subprocess
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class ToolKit:
    """工具集 - 提供给AI使用的实用工具"""

    def __init__(self, storage_dir: str = "data/toolkit"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    # ==================== 数学计算 ====================

    def calculate(self, expression: str) -> Dict[str, Any]:
        """安全数学计算"""
        try:
            # 只允许安全的数学操作
            allowed = set("0123456789+-*/.() ")
            allowed_funcs = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
                'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                'log': math.log, 'log10': math.log10, 'log2': math.log2,
                'pi': math.pi, 'e': math.e, 'ceil': math.ceil, 'floor': math.floor,
            }

            # 检查安全性
            clean = expression.replace(' ', '')
            for func in allowed_funcs:
                clean = clean.replace(func, '')

            if not all(c in allowed for c in clean):
                return {"success": False, "error": "不安全的表达式"}

            result = eval(expression, {"__builtins__": {}}, allowed_funcs)
            return {"success": True, "expression": expression, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== 单位换算 ====================

    def convert_unit(self, value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
        """单位换算"""
        conversions = {
            # 长度
            ("m", "km"): lambda x: x / 1000,
            ("km", "m"): lambda x: x * 1000,
            ("m", "cm"): lambda x: x * 100,
            ("cm", "m"): lambda x: x / 100,
            ("m", "ft"): lambda x: x * 3.28084,
            ("ft", "m"): lambda x: x / 3.28084,
            ("mile", "km"): lambda x: x * 1.60934,
            ("km", "mile"): lambda x: x / 1.60934,
            ("inch", "cm"): lambda x: x * 2.54,
            ("cm", "inch"): lambda x: x / 2.54,

            # 重量
            ("kg", "g"): lambda x: x * 1000,
            ("g", "kg"): lambda x: x / 1000,
            ("kg", "lb"): lambda x: x * 2.20462,
            ("lb", "kg"): lambda x: x / 2.20462,
            ("kg", "oz"): lambda x: x * 35.274,
            ("oz", "kg"): lambda x: x / 35.274,

            # 温度
            ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
            ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
            ("celsius", "kelvin"): lambda x: x + 273.15,
            ("kelvin", "celsius"): lambda x: x - 273.15,

            # 时间
            ("s", "min"): lambda x: x / 60,
            ("min", "s"): lambda x: x * 60,
            ("h", "min"): lambda x: x * 60,
            ("min", "h"): lambda x: x / 60,
            ("d", "h"): lambda x: x * 24,
            ("h", "d"): lambda x: x / 24,

            # 数据
            ("b", "kb"): lambda x: x / 1024,
            ("kb", "b"): lambda x: x * 1024,
            ("kb", "mb"): lambda x: x / 1024,
            ("mb", "kb"): lambda x: x * 1024,
            ("mb", "gb"): lambda x: x / 1024,
            ("gb", "mb"): lambda x: x * 1024,
            ("gb", "tb"): lambda x: x / 1024,
            ("tb", "gb"): lambda x: x * 1024,
        }

        key = (from_unit.lower(), to_unit.lower())
        if key in conversions:
            result = conversions[key](value)
            return {"success": True, "from": f"{value} {from_unit}",
                    "to": f"{result:.6g} {to_unit}", "result": result}
        return {"success": False, "error": f"不支持的换算: {from_unit} → {to_unit}"}

    # ==================== 日期时间 ====================

    def get_datetime(self, format: str = "full") -> Dict[str, Any]:
        """获取当前日期时间"""
        now = datetime.now()
        formats = {
            "full": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "iso": now.isoformat(),
            "timestamp": time.time(),
            "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        }
        return {"success": True, "current": formats.get(format, formats["full"]), "all": formats}

    def date_diff(self, date1: str, date2: str) -> Dict[str, Any]:
        """计算日期差"""
        try:
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            diff = abs((d2 - d1).days)
            return {"success": True, "days": diff, "weeks": diff // 7, "months": diff // 30}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== 文本处理 ====================

    def text_stats(self, text: str) -> Dict[str, Any]:
        """文本统计"""
        chars = len(text)
        words = len(text.split())
        lines = text.count('\n') + 1
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        english = len(re.findall(r'[a-zA-Z]', text))
        numbers = len(re.findall(r'\d', text))

        return {
            "success": True,
            "characters": chars,
            "words": words,
            "lines": lines,
            "chinese_chars": chinese,
            "english_chars": english,
            "numbers": numbers,
        }

    def text_replace(self, text: str, old: str, new: str,
                     all_occurrences: bool = True) -> Dict[str, Any]:
        """文本替换"""
        if all_occurrences:
            result = text.replace(old, new)
        else:
            result = text.replace(old, new, 1)
        count = text.count(old)
        return {"success": True, "result": result, "replacements": count}

    def text_extract(self, text: str, pattern: str) -> Dict[str, Any]:
        """正则提取"""
        try:
            matches = re.findall(pattern, text)
            return {"success": True, "matches": matches, "count": len(matches)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def text_to_json(self, text: str) -> Dict[str, Any]:
        """文本转JSON"""
        try:
            result = json.loads(text)
            return {"success": True, "result": result}
        except json.JSONDecodeError as e:
            return {"success": False, "error": str(e)}

    # ==================== URL处理 ====================

    def fetch_url(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """抓取URL内容"""
        try:
            headers = {"User-Agent": "SelfEvolvingAI/1.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode('utf-8', errors='replace')
                return {
                    "success": True,
                    "status": resp.status,
                    "content_type": resp.headers.get('Content-Type', ''),
                    "content": content[:10000],
                    "length": len(content),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def encode_url(self, text: str) -> str:
        """URL编码"""
        return urllib.parse.quote(text)

    def decode_url(self, text: str) -> str:
        """URL解码"""
        return urllib.parse.unquote(text)

    # ==================== JSON处理 ====================

    def json_format(self, data: str) -> Dict[str, Any]:
        """JSON格式化"""
        try:
            parsed = json.loads(data)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            return {"success": True, "formatted": formatted}
        except json.JSONDecodeError as e:
            return {"success": False, "error": str(e)}

    def json_query(self, data: str, path: str) -> Dict[str, Any]:
        """JSON查询(简单路径)"""
        try:
            obj = json.loads(data)
            parts = path.split('.')
            current = obj
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    current = current[int(part)]
                else:
                    return {"success": False, "error": f"路径不存在: {path}"}
            return {"success": True, "result": current}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== CSV处理 ====================

    def csv_parse(self, csv_text: str, delimiter: str = ",") -> Dict[str, Any]:
        """解析CSV"""
        try:
            reader = csv.DictReader(csv_text.strip().split('\n'), delimiter=delimiter)
            rows = list(reader)
            return {
                "success": True,
                "headers": reader.fieldnames,
                "rows": rows[:100],
                "total_rows": len(rows),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def csv_to_json(self, csv_text: str, delimiter: str = ",") -> Dict[str, Any]:
        """CSV转JSON"""
        result = self.csv_parse(csv_text, delimiter)
        if result["success"]:
            return {"success": True, "json": json.dumps(result["rows"], ensure_ascii=False)}
        return result

    # ==================== Base64 ====================

    def base64_encode(self, text: str) -> Dict[str, Any]:
        """Base64编码"""
        import base64
        encoded = base64.b64encode(text.encode()).decode()
        return {"success": True, "encoded": encoded}

    def base64_decode(self, encoded: str) -> Dict[str, Any]:
        """Base64解码"""
        import base64
        try:
            decoded = base64.b64decode(encoded).decode()
            return {"success": True, "decoded": decoded}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== 哈希 ====================

    def hash_text(self, text: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """计算哈希"""
        try:
            if algorithm == "md5":
                result = hashlib.md5(text.encode()).hexdigest()
            elif algorithm == "sha1":
                result = hashlib.sha1(text.encode()).hexdigest()
            elif algorithm == "sha256":
                result = hashlib.sha256(text.encode()).hexdigest()
            elif algorithm == "sha512":
                result = hashlib.sha512(text.encode()).hexdigest()
            else:
                return {"success": False, "error": f"不支持的算法: {algorithm}"}
            return {"success": True, "algorithm": algorithm, "hash": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== 随机数 ====================

    def random_number(self, min_val: int = 0, max_val: int = 100) -> Dict[str, Any]:
        """生成随机数"""
        import random
        result = random.randint(min_val, max_val)
        return {"success": True, "result": result, "range": f"{min_val}-{max_val}"}

    def random_choice(self, choices: List[str]) -> Dict[str, Any]:
        """随机选择"""
        import random
        if not choices:
            return {"success": False, "error": "选项列表为空"}
        result = random.choice(choices)
        return {"success": True, "result": result, "from": choices}

    def generate_uuid(self) -> Dict[str, Any]:
        """生成UUID"""
        import uuid
        return {"success": True, "uuid": str(uuid.uuid4())}

    # ==================== 文件操作 ====================

    def list_files(self, path: str = ".", pattern: str = "*") -> Dict[str, Any]:
        """列出文件"""
        import glob
        try:
            full_pattern = os.path.join(path, pattern)
            files = glob.glob(full_pattern)
            result = []
            for f in files[:100]:
                stat = os.stat(f)
                result.append({
                    "name": os.path.basename(f),
                    "path": f,
                    "size": stat.st_size,
                    "is_dir": os.path.isdir(f),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
            return {"success": True, "files": result, "count": len(result)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            stat = os.stat(path)
            return {
                "success": True,
                "name": os.path.basename(path),
                "path": os.path.abspath(path),
                "size": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "is_dir": os.path.isdir(path),
                "is_file": os.path.isfile(path),
                "extension": os.path.splitext(path)[1],
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _human_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    # ==================== 代码执行 ====================

    def run_python(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """执行Python代码(沙箱)"""
        try:
            # 安全检查
            dangerous = ['import os', 'import sys', 'import subprocess',
                        'open(', '__import__', 'eval(', 'exec(']
            for d in dangerous:
                if d in code:
                    return {"success": False, "error": f"安全限制: 禁止 {d}"}

            # 限制可用函数
            safe_globals = {
                "__builtins__": {
                    "print": print, "range": range, "len": len,
                    "int": int, "float": float, "str": str,
                    "list": list, "dict": dict, "tuple": tuple,
                    "set": set, "bool": bool, "abs": abs,
                    "min": min, "max": max, "sum": sum,
                    "sorted": sorted, "reversed": reversed,
                    "enumerate": enumerate, "zip": zip,
                    "map": map, "filter": filter,
                    "round": round, "pow": pow,
                },
                "math": math, "json": json, "time": time,
                "datetime": datetime, "re": re,
            }

            import io
            old_stdout = __import__('sys').stdout
            __import__('sys').stdout = buffer = io.StringIO()

            exec(code, safe_globals)

            __import__('sys').stdout = old_stdout
            output = buffer.getvalue()

            return {"success": True, "output": output[:5000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== 获取所有工具定义 ====================

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具的LLM Function Calling定义"""
        return [
            {
                "name": "calculate",
                "description": "数学计算，支持加减乘除、三角函数、对数等",
                "parameters": {"type": "object", "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如: 2+3*4, sqrt(16), sin(pi/2)"},
                }, "required": ["expression"]},
            },
            {
                "name": "convert_unit",
                "description": "单位换算(长度/重量/温度/时间/数据)",
                "parameters": {"type": "object", "properties": {
                    "value": {"type": "number", "description": "数值"},
                    "from_unit": {"type": "string", "description": "源单位(m,km,kg,lb,celsius,fahrenheit,s,min,h,mb,gb等)"},
                    "to_unit": {"type": "string", "description": "目标单位"},
                }, "required": ["value", "from_unit", "to_unit"]},
            },
            {
                "name": "get_datetime",
                "description": "获取当前日期时间",
                "parameters": {"type": "object", "properties": {
                    "format": {"type": "string", "enum": ["full", "date", "time", "iso", "weekday"], "description": "格式"},
                }},
            },
            {
                "name": "text_stats",
                "description": "文本统计(字数、行数、中英文字符数)",
                "parameters": {"type": "object", "properties": {
                    "text": {"type": "string", "description": "要统计的文本"},
                }, "required": ["text"]},
            },
            {
                "name": "fetch_url",
                "description": "抓取网页内容",
                "parameters": {"type": "object", "properties": {
                    "url": {"type": "string", "description": "网址"},
                }, "required": ["url"]},
            },
            {
                "name": "csv_parse",
                "description": "解析CSV数据",
                "parameters": {"type": "object", "properties": {
                    "csv_text": {"type": "string", "description": "CSV文本"},
                    "delimiter": {"type": "string", "description": "分隔符，默认逗号"},
                }, "required": ["csv_text"]},
            },
            {
                "name": "hash_text",
                "description": "计算文本哈希值",
                "parameters": {"type": "object", "properties": {
                    "text": {"type": "string", "description": "文本"},
                    "algorithm": {"type": "string", "enum": ["md5", "sha1", "sha256", "sha512"]},
                }, "required": ["text"]},
            },
            {
                "name": "run_python",
                "description": "执行Python代码(安全沙箱，禁止文件/网络操作)",
                "parameters": {"type": "object", "properties": {
                    "code": {"type": "string", "description": "Python代码"},
                }, "required": ["code"]},
            },
            {
                "name": "list_files",
                "description": "列出目录下的文件",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string", "description": "目录路径"},
                    "pattern": {"type": "string", "description": "匹配模式，如 *.py"},
                }},
            },
            {
                "name": "file_info",
                "description": "获取文件详细信息",
                "parameters": {"type": "object", "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                }, "required": ["path"]},
            },
            {
                "name": "json_format",
                "description": "JSON格式化",
                "parameters": {"type": "object", "properties": {
                    "data": {"type": "string", "description": "JSON字符串"},
                }, "required": ["data"]},
            },
            {
                "name": "base64_encode",
                "description": "Base64编码",
                "parameters": {"type": "object", "properties": {
                    "text": {"type": "string", "description": "要编码的文本"},
                }, "required": ["text"]},
            },
            {
                "name": "base64_decode",
                "description": "Base64解码",
                "parameters": {"type": "object", "properties": {
                    "encoded": {"type": "string", "description": "Base64字符串"},
                }, "required": ["encoded"]},
            },
            {
                "name": "random_number",
                "description": "生成随机数",
                "parameters": {"type": "object", "properties": {
                    "min_val": {"type": "integer", "description": "最小值"},
                    "max_val": {"type": "integer", "description": "最大值"},
                }},
            },
            {
                "name": "generate_uuid",
                "description": "生成UUID",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    def execute_tool(self, tool_name: str, params: dict) -> Any:
        """执行工具"""
        handler = getattr(self, tool_name, None)
        if handler and callable(handler):
            try:
                return handler(**params)
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"未知工具: {tool_name}"}

    def get_stats(self) -> Dict[str, Any]:
        tools = self.get_tool_definitions()
        return {
            "tools_count": len(tools),
            "categories": ["数学", "单位", "时间", "文本", "网络", "数据", "文件", "编码", "代码"],
        }


if __name__ == "__main__":
    print("=== 工具集测试 ===")
    tk = ToolKit()

    # 数学
    print(f"\n计算: {tk.calculate('2**10 + sqrt(144)')}")
    print(f"三角: {tk.calculate('sin(pi/2)')}")

    # 单位换算
    print(f"\n温度: {tk.convert_unit(100, 'celsius', 'fahrenheit')}")
    print(f"距离: {tk.convert_unit(5, 'km', 'mile')}")
    print(f"数据: {tk.convert_unit(1024, 'mb', 'gb')}")

    # 日期时间
    print(f"\n时间: {tk.get_datetime()}")
    print(f"日期差: {tk.date_diff('2024-01-01', '2024-12-31')}")

    # 文本
    print(f"\n文本统计: {tk.text_stats('Hello 你好 World 世界 123')}")
    print(f"哈希: {tk.hash_text('hello')}")

    # 编码
    print(f"\nBase64: {tk.base64_encode('Hello World')}")
    print(f"解码: {tk.base64_decode('SGVsbG8gV29ybGQ=')}")

    # 随机
    print(f"\n随机数: {tk.random_number(1, 100)}")
    print(f"UUID: {tk.generate_uuid()}")

    # 代码执行
    print(f"\nPython: {tk.run_python('print(sum(range(100)))')}")

    # JSON
    print(f"\nJSON: {tk.json_format('{\"name\":\"test\",\"value\":42}')}")

    # 工具列表
    tools = tk.get_tool_definitions()
    print(f"\n可用工具: {len(tools)} 个")
    for t in tools:
        print(f"  - {t['name']}: {t['description']}")

    print(f"\n统计: {tk.get_stats()}")
    print("测试完成!")
