"""自然语言理解 - 意图识别、实体抽取、槽位填充"""

import json
import os
import re
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict


class IntentType(Enum):
    QUERY = "query"
    COMMAND = "command"
    GREETING = "greeting"
    FAREWELL = "farewell"
    REQUEST = "request"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


class EntityType(Enum):
    PERSON = "person"
    LOCATION = "location"
    TIME = "time"
    NUMBER = "number"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    ACTION = "action"
    OBJECT = "object"
    CUSTOM = "custom"


@dataclass
class Entity:
    entity_type: str
    value: str
    start: int = 0
    end: int = 0
    confidence: float = 0.0


@dataclass
class Intent:
    intent_type: str
    confidence: float = 0.0
    keywords: List[str] = field(default_factory=list)


@dataclass
class Slot:
    slot_name: str
    slot_type: str
    value: Any = None
    required: bool = False
    filled: bool = False


@dataclass
class NLUResult:
    text: str
    intent: Intent
    entities: List[Entity]
    slots: Dict[str, Slot]
    language: str = "zh"
    processing_time: float = 0.0


@dataclass
class IntentPattern:
    intent_type: str
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


class NLUEngine:
    """自然语言理解引擎"""

    def __init__(self, storage_dir: str = "data/nlu"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.intent_patterns: Dict[str, IntentPattern] = {}
        self.entity_patterns: Dict[str, List[str]] = defaultdict(list)
        self.slot_definitions: Dict[str, List[Slot]] = {}
        self.training_data: List[Dict[str, Any]] = []

        self._init_defaults()
        self._load()

    def _init_defaults(self):
        """初始化默认意图和实体模式"""
        defaults = {
            "greeting": IntentPattern(
                intent_type="greeting",
                keywords=["你好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好", "hey"],
                patterns=[r"^(你好|hi|hello|hey|嗨)"],
            ),
            "farewell": IntentPattern(
                intent_type="farewell",
                keywords=["再见", "bye", "拜拜", "回头见", "goodbye", "晚安"],
                patterns=[r"(再见|bye|拜拜|goodbye)"],
            ),
            "query": IntentPattern(
                intent_type="query",
                keywords=["什么是", "怎么", "如何", "为什么", "哪里", "哪个", "多少", "?", "？"],
                patterns=[r"(什么是|怎么|如何|为什么|哪里|哪个|多少).*"],
            ),
            "request": IntentPattern(
                intent_type="request",
                keywords=["帮我", "请", "能不能", "可以", "麻烦", "需要"],
                patterns=[r"(帮我|请|能不能|可以|麻烦).+"],
            ),
            "command": IntentPattern(
                intent_type="command",
                keywords=["执行", "运行", "启动", "停止", "创建", "删除", "更新", "显示"],
                patterns=[r"(执行|运行|启动|停止|创建|删除|更新|显示).+"],
            ),
            "feedback": IntentPattern(
                intent_type="feedback",
                keywords=["好的", "不错", "很好", "太棒了", "谢谢", "感谢", "赞"],
                patterns=[r"(好的|不错|很好|太棒了|谢谢|感谢|赞)"],
            ),
        }
        for k, v in defaults.items():
            if k not in self.intent_patterns:
                self.intent_patterns[k] = v

        # 默认实体模式
        self.entity_patterns = {
            "technology": ["python", "java", "javascript", "机器学习", "深度学习", "AI", "API", "数据库", "docker", "kubernetes"],
            "action": ["学习", "创建", "删除", "更新", "查询", "分析", "优化", "部署", "测试", "运行"],
            "number": [r"\d+"],
            "time": [r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", r"\d{1,2}:\d{2}", r"\d+(秒|分钟|小时|天|周|月|年)"],
        }

    def _load(self):
        path = os.path.join(self.storage_dir, "nlu_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("intent_patterns", {}).items():
                    self.intent_patterns[k] = IntentPattern(**v)
                self.entity_patterns = defaultdict(list, data.get("entity_patterns", {}))
                self.training_data = data.get("training_data", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "nlu_data.json")
        data = {
            "intent_patterns": {k: asdict(v) for k, v in self.intent_patterns.items()},
            "entity_patterns": dict(self.entity_patterns),
            "training_data": self.training_data[-5000:],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def parse(self, text: str) -> NLUResult:
        """解析文本"""
        start_time = time.time()

        # 意图识别
        intent = self._detect_intent(text)

        # 实体抽取
        entities = self._extract_entities(text)

        # 槽位填充
        slots = self._fill_slots(text, intent.intent_type, entities)

        result = NLUResult(
            text=text,
            intent=intent,
            entities=entities,
            slots=slots,
            processing_time=time.time() - start_time,
        )

        return result

    def _detect_intent(self, text: str) -> Intent:
        """意图识别"""
        text_lower = text.lower()
        scores: Dict[str, float] = {}

        for intent_name, pattern in self.intent_patterns.items():
            score = 0.0

            # 关键词匹配
            for keyword in pattern.keywords:
                if keyword.lower() in text_lower:
                    score += 0.3

            # 正则匹配
            for regex in pattern.patterns:
                if re.search(regex, text_lower):
                    score += 0.5

            if score > 0:
                scores[intent_name] = min(score, 1.0)

        if not scores:
            return Intent(intent_type="unknown", confidence=0.0)

        best_intent = max(scores, key=scores.get)
        return Intent(
            intent_type=best_intent,
            confidence=scores[best_intent],
            keywords=[kw for kw in self.intent_patterns[best_intent].keywords if kw in text_lower],
        )

    def _extract_entities(self, text: str) -> List[Entity]:
        """实体抽取"""
        entities = []

        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        entities.append(Entity(
                            entity_type=entity_type,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=0.8,
                        ))
                except re.error:
                    if pattern.lower() in text.lower():
                        idx = text.lower().find(pattern.lower())
                        entities.append(Entity(
                            entity_type=entity_type,
                            value=pattern,
                            start=idx,
                            end=idx + len(pattern),
                            confidence=0.7,
                        ))

        return entities

    def _fill_slots(self, text: str, intent: str, entities: List[Entity]) -> Dict[str, Slot]:
        """槽位填充"""
        slot_defs = self.slot_definitions.get(intent, [])
        slots = {}

        for slot_def in slot_defs:
            slot = Slot(
                slot_name=slot_def.slot_name,
                slot_type=slot_def.slot_type,
                required=slot_def.required,
            )

            # 尝试从实体中匹配
            for entity in entities:
                if entity.entity_type == slot_def.slot_type:
                    slot.value = entity.value
                    slot.filled = True
                    break

            slots[slot_def.slot_name] = slot

        return slots

    def define_slots(self, intent: str, slots: List[Dict[str, Any]]):
        """定义意图的槽位"""
        self.slot_definitions[intent] = [
            Slot(
                slot_name=s["name"],
                slot_type=s.get("type", "text"),
                required=s.get("required", False),
            )
            for s in slots
        ]

    def add_intent_pattern(self, intent_type: str, keywords: List[str] = None,
                           patterns: List[str] = None, examples: List[str] = None):
        """添加意图模式"""
        if intent_type in self.intent_patterns:
            existing = self.intent_patterns[intent_type]
            if keywords:
                existing.keywords.extend(keywords)
            if patterns:
                existing.patterns.extend(patterns)
            if examples:
                existing.examples.extend(examples)
        else:
            self.intent_patterns[intent_type] = IntentPattern(
                intent_type=intent_type,
                keywords=keywords or [],
                patterns=patterns or [],
                examples=examples or [],
            )
        self._save()

    def add_entity_pattern(self, entity_type: str, pattern: str):
        """添加实体模式"""
        self.entity_patterns[entity_type].append(pattern)
        self._save()

    def add_training_data(self, text: str, intent: str, entities: List[Dict] = None):
        """添加训练数据"""
        self.training_data.append({
            "text": text,
            "intent": intent,
            "entities": entities or [],
            "timestamp": time.time(),
        })
        self._save()

    def batch_parse(self, texts: List[str]) -> List[NLUResult]:
        """批量解析"""
        return [self.parse(text) for text in texts]

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        return {
            "intent_patterns": len(self.intent_patterns),
            "entity_types": len(self.entity_patterns),
            "slot_definitions": len(self.slot_definitions),
            "training_data_count": len(self.training_data),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "intents": len(self.intent_patterns),
            "entity_types": len(self.entity_patterns),
            "training_samples": len(self.training_data),
        }


if __name__ == "__main__":
    print("=== NLU测试 ===")
    engine = NLUEngine()

    tests = [
        "你好，我是张三",
        "什么是机器学习？",
        "帮我创建一个Python项目",
        "如何使用深度学习进行图像分类？",
        "请运行测试",
        "谢谢你的帮助",
        "再见",
        "执行数据分析任务",
    ]

    for text in tests:
        result = engine.parse(text)
        print(f"\n输入: {text}")
        print(f"  意图: {result.intent.intent_type} (置信度: {result.intent.confidence:.2f})")
        if result.entities:
            print(f"  实体: {[(e.entity_type, e.value) for e in result.entities]}")

    # 自定义意图
    engine.add_intent_pattern("deploy", keywords=["部署", "上线", "发布"])
    result = engine.parse("帮我部署到生产环境")
    print(f"\n自定义意图: {result.intent.intent_type}")

    report = engine.generate_report()
    print(f"\nNLU报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
