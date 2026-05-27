"""
================================================================================
知识蒸馏系统 (Knowledge Distillation System)
================================================================================

核心能力：
  1. 知识压缩 - 将复杂知识压缩为简单规则
  2. 模式提取 - 从经验中提取通用模式
  3. 规则生成 - 从模式中生成规则
  4. 知识简化 - 简化复杂概念
  5. 蒸馏验证 - 验证蒸馏后知识的有效性

设计原则：
  - 保留核心：保留最重要的信息
  - 可理解性：蒸馏后的知识要易于理解
  - 可应用性：蒸馏后的知识要能直接应用
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

class DistillationLevel(Enum):
    RAW = 0           # 原始知识
    SUMMARIZED = 1    # 摘要
    PATTERN = 2       # 模式
    RULE = 3          # 规则
    PRINCIPLE = 4     # 原则

@dataclass
class KnowledgeSource:
    """知识源"""
    id: str
    content: str
    domain: str
    complexity: float  # 复杂度 0-1
    quality: float    # 质量 0-1
    created_at: float = field(default_factory=time.time)

@dataclass
class DistilledKnowledge:
    """蒸馏后的知识"""
    id: str
    source_id: str
    level: DistillationLevel
    content: str
    domain: str
    confidence: float
    applicability: float  # 可应用性 0-1
    examples: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

@dataclass
class Pattern:
    """模式"""
    id: str
    name: str
    description: str
    occurrences: int = 0
    examples: list = field(default_factory=list)
    confidence: float = 0.5

@dataclass
class Rule:
    """规则"""
    id: str
    name: str
    condition: str
    action: str
    domain: str
    confidence: float
    exceptions: list = field(default_factory=list)


# ============================================================================
# 模式提取器
# ============================================================================

class PatternExtractor:
    """模式提取器"""

    def __init__(self):
        self.patterns: dict[str, Pattern] = {}

    def extract_from_examples(self, examples: list,
                                domain: str) -> list:
        """从示例中提取模式"""
        patterns = []

        # 分析共同特征
        common_features = self._find_common_features(examples)

        for feature in common_features:
            pattern_id = hashlib.md5(f"{domain}:{feature}".encode()).hexdigest()[:12]

            if pattern_id in self.patterns:
                # 更新现有模式
                self.patterns[pattern_id].occurrences += 1
                patterns.append(self.patterns[pattern_id])
            else:
                # 创建新模式
                pattern = Pattern(
                    id=pattern_id,
                    name=f"模式: {feature[:30]}",
                    description=feature,
                    occurrences=1,
                    examples=[e[:50] for e in examples[:3]],
                    confidence=0.5,
                )
                self.patterns[pattern_id] = pattern
                patterns.append(pattern)

        return patterns

    def _find_common_features(self, examples: list) -> list:
        """查找共同特征"""
        if not examples:
            return []

        # 提取关键词
        all_words = []
        for example in examples:
            words = set(re.findall(r'\w+', example.lower()))
            all_words.append(words)

        # 查找共同词汇
        if all_words:
            common_words = all_words[0]
            for words in all_words[1:]:
                common_words = common_words & words

            return [f"包含词汇: {', '.join(list(common_words)[:5])}"]

        return []

    def extract_from_text(self, text: str, domain: str) -> list:
        """从文本中提取模式"""
        patterns = []

        # 提取常见句式
        sentences = re.split(r'[。！？.!?]', text)
        sentence_patterns = {}

        for sentence in sentences:
            # 简化句子结构
            simplified = re.sub(r'[，,；;：:]', ' ', sentence)
            simplified = re.sub(r'\s+', ' ', simplified).strip()

            if len(simplified) > 10:
                key = simplified[:20]  # 用前20字符作为key
                if key not in sentence_patterns:
                    sentence_patterns[key] = []
                sentence_patterns[key].append(sentence)

        # 生成模式
        for key, occurrences in sentence_patterns.items():
            if len(occurrences) >= 2:  # 至少出现2次
                pattern_id = hashlib.md5(f"{domain}:{key}".encode()).hexdigest()[:12]
                pattern = Pattern(
                    id=pattern_id,
                    name=f"句式: {key}",
                    description=f"在{domain}领域常见: {key}...",
                    occurrences=len(occurrences),
                    examples=occurrences[:3],
                    confidence=min(0.9, 0.3 + len(occurrences) * 0.1),
                )
                patterns.append(pattern)

        return patterns


# ============================================================================
# 规则生成器
# ============================================================================

class RuleGenerator:
    """规则生成器"""

    def __init__(self):
        self.rules: dict[str, Rule] = {}

    def generate_from_pattern(self, pattern: Pattern,
                                domain: str) -> Optional[Rule]:
        """从模式生成规则"""
        if pattern.confidence < 0.4:
            return None

        rule_id = hashlib.md5(f"rule:{pattern.id}".encode()).hexdigest()[:12]

        # 生成条件和行动
        condition = f"当观察到 {pattern.description}"
        action = f"则预期会出现类似模式"

        rule = Rule(
            id=rule_id,
            name=f"规则: {pattern.name}",
            condition=condition,
            action=action,
            domain=domain,
            confidence=pattern.confidence,
        )

        self.rules[rule_id] = rule
        return rule

    def generate_from_examples(self, examples: list,
                                 domain: str) -> list:
        """从示例生成规则"""
        rules = []

        # 分析输入输出对
        for i in range(0, len(examples) - 1, 2):
            if i + 1 < len(examples):
                input_example = examples[i]
                output_example = examples[i + 1]

                rule_id = hashlib.md5(
                    f"rule:{input_example[:20]}:{output_example[:20]}".encode()
                ).hexdigest()[:12]

                rule = Rule(
                    id=rule_id,
                    name=f"规则_{i//2}",
                    condition=f"当输入类似: {input_example[:50]}",
                    action=f"则输出类似: {output_example[:50]}",
                    domain=domain,
                    confidence=0.5,
                )
                rules.append(rule)

        return rules

    def simplify_rule(self, rule: Rule) -> Rule:
        """简化规则"""
        # 缩短条件和行动
        simplified_condition = rule.condition[:100] + "..." if len(rule.condition) > 100 else rule.condition
        simplified_action = rule.action[:100] + "..." if len(rule.action) > 100 else rule.action

        return Rule(
            id=rule.id,
            name=rule.name,
            condition=simplified_condition,
            action=simplified_action,
            domain=rule.domain,
            confidence=rule.confidence,
            exceptions=rule.exceptions,
        )


# ============================================================================
# 知识压缩器
# ============================================================================

class KnowledgeCompressor:
    """知识压缩器"""

    def compress(self, content: str,
                  target_level: DistillationLevel) -> str:
        """压缩知识到目标级别"""
        if target_level == DistillationLevel.RAW:
            return content
        elif target_level == DistillationLevel.SUMMARIZED:
            return self._summarize(content)
        elif target_level == DistillationLevel.PATTERN:
            return self._extract_pattern(content)
        elif target_level == DistillationLevel.RULE:
            return self._extract_rule(content)
        elif target_level == DistillationLevel.PRINCIPLE:
            return self._extract_principle(content)
        return content

    def _summarize(self, content: str) -> str:
        """生成摘要"""
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) <= 2:
            return content

        # 取前两句作为摘要
        return '。'.join(sentences[:2]) + '。'

    def _extract_pattern(self, content: str) -> str:
        """提取模式"""
        # 提取关键短语
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}|[a-zA-Z]{3,}', content)
        if keywords:
            return f"模式: {', '.join(keywords[:5])}"
        return content[:100]

    def _extract_rule(self, content: str) -> str:
        """提取规则"""
        # 查找"如果...则..."结构
        if_match = re.search(r'如果(.+?)则(.+?)[。.，,]', content)
        if if_match:
            return f"规则: 如果{if_match.group(1).strip()}，则{if_match.group(2).strip()}"

        return f"规则: {content[:80]}"

    def _extract_principle(self, content: str) -> str:
        """提取原则"""
        return f"原则: {content[:60]}"


# ============================================================================
# 蒸馏验证器
# ============================================================================

class DistillationValidator:
    """蒸馏验证器"""

    def validate(self, original: KnowledgeSource,
                 distilled: DistilledKnowledge) -> dict:
        """验证蒸馏效果"""
        # 信息保留度
        retention = self._calculate_retention(original.content, distilled.content)

        # 简化程度
        simplification = 1 - (len(distilled.content) / max(1, len(original.content)))

        # 可理解性（简化启发式）
        understandability = min(1.0, 0.5 + simplification * 0.5)

        # 综合分数
        score = retention * 0.4 + simplification * 0.3 + understandability * 0.3

        return {
            'retention': retention,
            'simplification': simplification,
            'understandability': understandability,
            'overall_score': score,
            'success': score > 0.5,
        }

    def _calculate_retention(self, original: str,
                               distilled: str) -> float:
        """计算信息保留度"""
        original_words = set(re.findall(r'\w+', original.lower()))
        distilled_words = set(re.findall(r'\w+', distilled.lower()))

        if not original_words:
            return 0

        overlap = len(original_words & distilled_words)
        return overlap / len(original_words)


# ============================================================================
# 知识蒸馏引擎
# ============================================================================

class KnowledgeDistillationEngine:
    """
    知识蒸馏引擎 - 整合所有组件

    核心功能：
    1. 从经验中提取模式
    2. 从模式中生成规则
    3. 压缩复杂知识
    4. 验���蒸馏效果
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "distillation"
        os.makedirs(storage_dir, exist_ok=True)

        self.pattern_extractor = PatternExtractor()
        self.rule_generator = RuleGenerator()
        self.compressor = KnowledgeCompressor()
        self.validator = DistillationValidator()

        self.knowledge_sources: dict[str, KnowledgeSource] = {}
        self.distilled_knowledge: dict[str, DistilledKnowledge] = {}

        self.storage_path = os.path.join(storage_dir, "distilled.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for s_data in data.get('sources', []):
                    source = KnowledgeSource(**s_data)
                    self.knowledge_sources[source.id] = source

                for d_data in data.get('distilled', []):
                    d_data['level'] = DistillationLevel(d_data['level'])
                    distilled = DistilledKnowledge(**d_data)
                    self.distilled_knowledge[distilled.id] = distilled

    def _save(self):
        """保存数据"""
        data = {
            'sources': [asdict(s) for s in self.knowledge_sources.values()],
            'distilled': [],
        }

        for d in self.distilled_knowledge.values():
            d_dict = asdict(d)
            d_dict['level'] = d.level.value
            data['distilled'].append(d_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_source(self, content: str, domain: str,
                   complexity: float = 0.5,
                   quality: float = 0.8) -> KnowledgeSource:
        """添加知识源"""
        source_id = hashlib.md5(f"{domain}:{content[:50]}".encode()).hexdigest()[:12]
        source = KnowledgeSource(
            id=source_id,
            content=content,
            domain=domain,
            complexity=complexity,
            quality=quality,
        )
        self.knowledge_sources[source_id] = source
        self._save()
        return source

    def distill(self, source_id: str,
                target_level: DistillationLevel = DistillationLevel.RULE) -> dict:
        """蒸馏知识"""
        source = self.knowledge_sources.get(source_id)
        if not source:
            return {'error': '知识源不存在'}

        # 压缩内容
        compressed = self.compressor.compress(source.content, target_level)

        # 创建蒸馏后的知识
        distilled_id = hashlib.md5(f"distilled:{source_id}:{target_level.value}".encode()).hexdigest()[:12]
        distilled = DistilledKnowledge(
            id=distilled_id,
            source_id=source_id,
            level=target_level,
            content=compressed,
            domain=source.domain,
            confidence=source.quality * 0.9,
            applicability=0.7,
        )

        # 验证
        validation = self.validator.validate(source, distilled)

        self.distilled_knowledge[distilled_id] = distilled
        self._save()

        return {
            'distilled_id': distilled_id,
            'content': compressed,
            'level': target_level.value,
            'validation': validation,
        }

    def extract_patterns(self, domain: str) -> list:
        """提取领域模式"""
        # 收集该领域的所有知识
        sources = [
            s.content for s in self.knowledge_sources.values()
            if s.domain == domain
        ]

        if not sources:
            return []

        # 提取模式
        patterns = self.pattern_extractor.extract_from_examples(sources, domain)
        return [asdict(p) for p in patterns]

    def generate_rules(self, domain: str) -> list:
        """生成领域规则"""
        # 先提取模式
        patterns = self.extract_patterns(domain)

        rules = []
        for pattern_data in patterns:
            pattern = Pattern(**pattern_data)
            rule = self.rule_generator.generate_from_pattern(pattern, domain)
            if rule:
                rules.append(asdict(rule))

        return rules

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'sources': len(self.knowledge_sources),
            'distilled': len(self.distilled_knowledge),
            'patterns': len(self.pattern_extractor.patterns),
            'rules': len(self.rule_generator.rules),
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("🧪 知识蒸馏报告")
        report.append("=" * 50)
        report.append(f"\n知识源数量: {stats['sources']}")
        report.append(f"蒸馏后知识: {stats['distilled']}")
        report.append(f"提取模式数: {stats['patterns']}")
        report.append(f"生成规则数: {stats['rules']}")

        # 按级别统计
        by_level = {}
        for d in self.distilled_knowledge.values():
            level = d.level.value
            if level not in by_level:
                by_level[level] = 0
            by_level[level] += 1

        if by_level:
            report.append("\n蒸馏级别分布:")
            for level, count in sorted(by_level.items()):
                level_name = DistillationLevel(level).name
                report.append(f"  - {level_name}: {count}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = KnowledgeDistillationEngine("test_distillation")

    # 添加知识源
    print("=== 添加知识源 ===")
    sources = [
        ("Python列表推导式是一种简洁的创建列表的方式。"
         "它使用方括号和for循环，可以包含条件判断。"
         "例如 [x for x in range(10) if x % 2 == 0] 生成偶数列表。",
         "python"),
        ("机器学习是人工智能的一个子领域，它使用统计方法让计算机从数据中学习。"
         "主要分为监督学习、无监督学习和强化学习。"
         "常见算法包括线性回归、决策树、神经网络等。",
         "machine_learning"),
    ]

    for content, domain in sources:
        source = engine.add_source(content, domain, complexity=0.6)
        print(f"添加: {content[:30]}... (ID: {source.id})")

    # 蒸馏
    print("\n=== 知识蒸馏 ===")
    for source_id in engine.knowledge_sources:
        result = engine.distill(source_id, DistillationLevel.RULE)
        print(f"蒸馏: {result.get('content', '')[:50]}...")
        if result.get('validation'):
            print(f"  得分: {result['validation']['overall_score']:.2f}")

    # 提取模式
    print("\n=== 模式提取 ===")
    patterns = engine.extract_patterns("python")
    for p in patterns[:3]:
        print(f"  - {p['name']}: {p['description'][:40]}...")

    # 报告
    print("\n" + engine.generate_report())