"""国际化 - 多语言翻译、区域设置、语言检测"""

import json
import os
import time
import hashlib
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict


class Language(Enum):
    ZH_CN = "zh-CN"
    EN_US = "en-US"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    ES_ES = "es-ES"


@dataclass
class Translation:
    key: str
    language: str
    value: str
    context: str = ""
    updated_at: float = 0.0


@dataclass
class Locale:
    locale_id: str
    language: str
    country: str = ""
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    number_format: Dict[str, str] = field(default_factory=dict)
    currency: str = "USD"
    direction: str = "ltr"


class I18nEngine:
    """国际化引擎"""

    def __init__(self, storage_dir: str = "data/i18n"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.translations: Dict[str, Dict[str, Translation]] = defaultdict(dict)
        self.locales: Dict[str, Locale] = {}
        self.default_language: str = "zh-CN"
        self.fallback_language: str = "en-US"

        self._init_defaults()
        self._load()

    def _init_defaults(self):
        """初始化默认翻译"""
        defaults = {
            "zh-CN": {
                "hello": "你好",
                "goodbye": "再见",
                "yes": "是",
                "no": "否",
                "ok": "确定",
                "cancel": "取消",
                "save": "保存",
                "delete": "删除",
                "edit": "编辑",
                "create": "创建",
                "search": "搜索",
                "loading": "加载中...",
                "error": "错误",
                "success": "成功",
                "warning": "警告",
                "info": "信息",
                "welcome": "欢迎",
                "login": "登录",
                "logout": "退出",
                "settings": "设置",
                "help": "帮助",
            },
            "en-US": {
                "hello": "Hello",
                "goodbye": "Goodbye",
                "yes": "Yes",
                "no": "No",
                "ok": "OK",
                "cancel": "Cancel",
                "save": "Save",
                "delete": "Delete",
                "edit": "Edit",
                "create": "Create",
                "search": "Search",
                "loading": "Loading...",
                "error": "Error",
                "success": "Success",
                "warning": "Warning",
                "info": "Info",
                "welcome": "Welcome",
                "login": "Login",
                "logout": "Logout",
                "settings": "Settings",
                "help": "Help",
            },
        }

        for lang, translations in defaults.items():
            for key, value in translations.items():
                if key not in self.translations[lang]:
                    self.translations[lang][key] = Translation(
                        key=key, language=lang, value=value,
                        updated_at=time.time(),
                    )

        # 默认区域
        self.locales["zh-CN"] = Locale(
            locale_id="zh-CN", language="zh-CN", country="CN",
            date_format="%Y年%m月%d日", currency="CNY",
        )
        self.locales["en-US"] = Locale(
            locale_id="en-US", language="en-US", country="US",
            date_format="%m/%d/%Y", currency="USD",
        )

    def _load(self):
        path = os.path.join(self.storage_dir, "i18n_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for lang, trans in data.get("translations", {}).items():
                    for k, v in trans.items():
                        self.translations[lang][k] = Translation(**v)
                for k, v in data.get("locales", {}).items():
                    self.locales[k] = Locale(**v)
                self.default_language = data.get("default_language", "zh-CN")
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "i18n_data.json")
        data = {
            "translations": {
                lang: {k: asdict(v) for k, v in trans.items()}
                for lang, trans in self.translations.items()
            },
            "locales": {k: asdict(v) for k, v in self.locales.items()},
            "default_language": self.default_language,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def t(self, key: str, language: str = "", **kwargs) -> str:
        """翻译"""
        lang = language or self.default_language

        # 尝试目标语言
        if lang in self.translations and key in self.translations[lang]:
            value = self.translations[lang][key].value
        elif self.fallback_language in self.translations and key in self.translations[self.fallback_language]:
            value = self.translations[self.fallback_language][key].value
        else:
            value = key

        # 变量替换
        if kwargs:
            for k, v in kwargs.items():
                value = value.replace(f"{{{k}}}", str(v))

        return value

    def set_translation(self, key: str, language: str, value: str,
                        context: str = ""):
        """设置翻译"""
        self.translations[language][key] = Translation(
            key=key, language=language, value=value,
            context=context, updated_at=time.time(),
        )
        self._save()

    def set_translations_batch(self, language: str,
                               translations: Dict[str, str]):
        """批量设置翻译"""
        for key, value in translations.items():
            self.set_translation(key, language, value)

    def get_translations(self, language: str) -> Dict[str, str]:
        """获取语言的所有翻译"""
        return {
            k: v.value
            for k, v in self.translations.get(language, {}).items()
        }

    def detect_language(self, text: str) -> str:
        """语言检测"""
        # 简单检测
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))

        total = len(text)
        if total == 0:
            return self.default_language

        if chinese_chars / total > 0.1:
            return "zh-CN"
        if japanese_chars / total > 0.1:
            return "ja-JP"
        if korean_chars / total > 0.1:
            return "ko-KR"

        return "en-US"

    def format_number(self, number: float, language: str = "") -> str:
        """格式化数字"""
        lang = language or self.default_language
        locale = self.locales.get(lang)

        if lang.startswith("zh"):
            if number >= 10000:
                return f"{number/10000:.1f}万"
            return f"{number:,.0f}"
        else:
            return f"{number:,.2f}"

    def format_date(self, timestamp: float, language: str = "") -> str:
        """格式化日期"""
        import datetime
        lang = language or self.default_language
        locale = self.locales.get(lang)

        dt = datetime.datetime.fromtimestamp(timestamp)
        fmt = locale.date_format if locale else "%Y-%m-%d"
        return dt.strftime(fmt)

    def set_default_language(self, language: str):
        """设置默认语言"""
        self.default_language = language
        self._save()

    def add_locale(self, locale_id: str, language: str, country: str = "",
                   date_format: str = "%Y-%m-%d", currency: str = "USD"):
        """添加区域"""
        self.locales[locale_id] = Locale(
            locale_id=locale_id, language=language,
            country=country, date_format=date_format,
            currency=currency,
        )
        self._save()

    def get_missing_keys(self, language: str) -> List[str]:
        """获取缺失的翻译"""
        base_keys = set(self.translations.get(self.fallback_language, {}).keys())
        lang_keys = set(self.translations.get(language, {}).keys())
        return list(base_keys - lang_keys)

    def generate_report(self) -> Dict[str, Any]:
        return {
            "supported_languages": len(self.translations),
            "total_keys": len(set(k for t in self.translations.values() for k in t.keys())),
            "locales": len(self.locales),
            "default_language": self.default_language,
            "language_stats": {
                lang: len(trans) for lang, trans in self.translations.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "languages": len(self.translations),
            "total_translations": sum(len(t) for t in self.translations.values()),
            "locales_count": len(self.locales),
        }


if __name__ == "__main__":
    print("=== 国际化测试 ===")
    engine = I18nEngine()

    # 翻译
    print(f"中文: {engine.t('hello', 'zh-CN')}")
    print(f"英文: {engine.t('hello', 'en-US')}")
    print(f"欢迎: {engine.t('welcome', 'zh-CN')}")

    # 自定义翻译
    engine.set_translation("app_name", "zh-CN", "自我进化AI")
    engine.set_translation("app_name", "en-US", "Self-Evolving AI")
    engine.set_translation("greeting", "zh-CN", "你好，{name}！欢迎使用{app}。")
    engine.set_translation("greeting", "en-US", "Hello, {name}! Welcome to {app}.")

    print(f"\n{engine.t('greeting', 'zh-CN', name='张三', app='自我进化AI')}")
    print(f"{engine.t('greeting', 'en-US', name='Alice', app='Self-Evolving AI')}")

    # 语言检测
    print(f"\n语言检测:")
    print(f"  '你好世界': {engine.detect_language('你好世界')}")
    print(f"  'Hello World': {engine.detect_language('Hello World')}")
    print(f"  'こんにちは': {engine.detect_language('こんにちは')}")

    # 数字格式化
    print(f"\n数字格式化:")
    print(f"  中文: {engine.format_number(12345.67, 'zh-CN')}")
    print(f"  英文: {engine.format_number(12345.67, 'en-US')}")

    # 日期格式化
    print(f"\n日期: {engine.format_date(time.time(), 'zh-CN')}")

    # 缺失翻译
    missing = engine.get_missing_keys("ja-JP")
    print(f"\n日语缺失翻译: {len(missing)} 个")

    report = engine.generate_report()
    print(f"\n国际化报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
