"""
================================================================================
创造性思维系统 (Creative Thinking System)
================================================================================

核心能力：
  1. 发散思维 - 从一个问题出发，产生多种可能的解决方案
  2. 类比推理 - 从不同领域寻找相似性，借鉴解决方案
  3. 组合创新 - 将现有知识重新组合，产生新想法
  4. 约束突破 - 挑战现有假设，寻找突破性解决方案
  5. 创意评估 - 评估创意的新颖性、可行性和价值

设计原则：
  - 数量优先：先产生大量想法，再筛选
  - 多样性：鼓励不同类型的想法
  - 延迟评判：不急于否定任何想法
"""

import json
import os
import time
import hashlib
import random
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class CreativityType(Enum):
    DIVERGENT = "divergent"     # 发散思维
    CONVERGENT = "convergent"   # 收敛思维
    LATERAL = "lateral"         # 横向思维
    ANALOGICAL = "analogical"   # 类比思维

@dataclass
class Idea:
    """创意"""
    id: str
    content: str
    creativity_type: CreativityType
    domain: str
    novelty: float = 0.5       # 新颖性 0-1
    feasibility: float = 0.5   # 可行性 0-1
    value: float = 0.5         # 价值 0-1
    score: float = 0.0         # 综合分数
    sources: list = field(default_factory=list)  # 灵感来源
    created_at: float = field(default_factory=time.time)

@dataclass
class Analogy:
    """类比"""
    id: str
    source_domain: str
    target_domain: str
    source_concept: str
    target_concept: str
    similarity: float
    mapping: dict = field(default_factory=dict)

@dataclass
class CreativeConstraint:
    """创造性约束"""
    name: str
    description: str
    can_break: bool = True  # 是否可以打破


# ============================================================================
# 发散思维器
# ============================================================================

class DivergentThinker:
    """发散思维器"""

    def __init__(self):
        # 思维策略
        self.strategies = [
            self._brainstorm,
            self._reverse_thinking,
            self._random_stimulation,
            self._scamper,
        ]

    def generate_ideas(self, problem: str, domain: str,
                        count: int = 10) -> list:
        """生成创意"""
        ideas = []

        for strategy in self.strategies:
            try:
                strategy_ideas = strategy(problem, domain)
                ideas.extend(strategy_ideas)
            except Exception:
                continue

        # 去重
        unique_ideas = self._deduplicate(ideas)

        # 限制数量
        return unique_ideas[:count]

    def _brainstorm(self, problem: str, domain: str) -> list:
        """头脑风暴"""
        ideas = []

        # 基于问题关键词扩展
        keywords = problem.split()
        for keyword in keywords[:3]:
            idea = Idea(
                id=hashlib.md5(f"brainstorm:{keyword}".encode()).hexdigest()[:12],
                content=f"从{keyword}角度思考: 寻找{keyword}的替代方案",
                creativity_type=CreativityType.DIVERGENT,
                domain=domain,
                novelty=0.5,
                feasibility=0.7,
            )
            ideas.append(idea)

        return ideas

    def _reverse_thinking(self, problem: str, domain: str) -> list:
        """逆向思维"""
        ideas = []

        # 思考相反的情况
        idea = Idea(
            id=hashlib.md5(f"reverse:{problem[:20]}".encode()).hexdigest()[:12],
            content=f"逆向思考: 如果目标是让问题变得更糟，会怎么做？然后避免这些做法",
            creativity_type=CreativityType.LATERAL,
            domain=domain,
            novelty=0.7,
            feasibility=0.5,
        )
        ideas.append(idea)

        return ideas

    def _random_stimulation(self, problem: str, domain: str) -> list:
        """随机刺激"""
        ideas = []

        # 随机词汇刺激
        random_words = ['水', '光', '音乐', '游戏', '旅行', '烹饪']
        random_word = random.choice(random_words)

        idea = Idea(
            id=hashlib.md5(f"random:{random_word}".encode()).hexdigest()[:12],
            content=f"随机联想: {random_word}与问题有什么联系？能否借鉴{random_word}的特性？",
            creativity_type=CreativityType.LATERAL,
            domain=domain,
            novelty=0.8,
            feasibility=0.3,
        )
        ideas.append(idea)

        return ideas

    def _scamper(self, problem: str, domain: str) -> list:
        """SCAMPER方法"""
        ideas = []

        scamper_prompts = [
            ("替代", "有什么可以被替代？"),
            ("组合", "可以和什么组合？"),
            ("调整", "可以调整哪些方面？"),
            ("修改", "可以放大或缩小什么？"),
            ("其他用途", "有其他用途吗？"),
            ("消除", "可以去掉什么？"),
            ("重排", "可以重新排列吗？"),
        ]

        for action, prompt in scamper_prompts[:3]:  # 只用前3个
            idea = Idea(
                id=hashlib.md5(f"scamper:{action}".encode()).hexdigest()[:12],
                content=f"SCAMPER-{action}: {prompt}",
                creativity_type=CreativityType.DIVERGENT,
                domain=domain,
                novelty=0.6,
                feasibility=0.6,
            )
            ideas.append(idea)

        return ideas

    def _deduplicate(self, ideas: list) -> list:
        """去重"""
        seen = set()
        unique = []

        for idea in ideas:
            key = idea.content[:30]
            if key not in seen:
                seen.add(key)
                unique.append(idea)

        return unique


# ============================================================================
# 类比推理器
# ============================================================================

class AnalogicalReasoner:
    """类比推理器"""

    def __init__(self):
        # 领域知识库
        self.domain_knowledge: dict[str, list] = {
            'biology': ['进化', '适应', '生态系统', '细胞', '基因'],
            'physics': ['力', '能量', '运动', '波', '粒子'],
            'computer': ['算法', '数据结构', '网络', '内存', '进程'],
            'economics': ['供需', '市场', '成本', '收益', '风险'],
        }

    def find_analogies(self, problem: str, source_domain: str,
                        target_domain: str) -> list:
        """查找类比"""
        analogies = []

        # 获取两个领域的概念
        source_concepts = self.domain_knowledge.get(source_domain, [])
        target_concepts = self.domain_knowledge.get(target_domain, [])

        # 查找相似概念
        for sc in source_concepts:
            for tc in target_concepts:
                similarity = self._calculate_similarity(sc, tc)
                if similarity > 0.3:
                    analogy = Analogy(
                        id=hashlib.md5(f"{sc}:{tc}".encode()).hexdigest()[:12],
                        source_domain=source_domain,
                        target_domain=target_domain,
                        source_concept=sc,
                        target_concept=tc,
                        similarity=similarity,
                        mapping={sc: tc},
                    )
                    analogies.append(analogy)

        # 按相似度排序
        analogies.sort(key=lambda a: a.similarity, reverse=True)
        return analogies[:5]

    def _calculate_similarity(self, concept_a: str,
                                concept_b: str) -> float:
        """计算概念相似度"""
        # 简单实现：字符重叠度
        chars_a = set(concept_a)
        chars_b = set(concept_b)

        if not chars_a or not chars_b:
            return 0.0

        intersection = len(chars_a & chars_b)
        union = len(chars_a | chars_b)

        return intersection / union

    def apply_analogy(self, analogy: Analogy,
                      solution_in_source: str) -> str:
        """应用类比，将源领域的解决方案映射到目标领域"""
        # 替换概念
        mapped_solution = solution_in_source
        for source, target in analogy.mapping.items():
            mapped_solution = mapped_solution.replace(source, target)

        return f"在{analogy.target_domain}领域: {mapped_solution}"


# ============================================================================
# 组合创新器
# ============================================================================

class CombinatorialInnovator:
    """组合创新器"""

    def __init__(self):
        self.knowledge_elements: dict[str, list] = {}

    def add_elements(self, domain: str, elements: list):
        """添加知识元素"""
        if domain not in self.knowledge_elements:
            self.knowledge_elements[domain] = []
        self.knowledge_elements[domain].extend(elements)

    def combine(self, domain_a: str, domain_b: str,
                count: int = 5) -> list:
        """组合两个领域的知识元素"""
        elements_a = self.knowledge_elements.get(domain_a, [])
        elements_b = self.knowledge_elements.get(domain_b, [])

        if not elements_a or not elements_b:
            return []

        combinations = []

        # 随机组合
        for _ in range(count):
            elem_a = random.choice(elements_a)
            elem_b = random.choice(elements_b)

            combination = f"{elem_a} + {elem_b}"
            idea = Idea(
                id=hashlib.md5(combination.encode()).hexdigest()[:12],
                content=f"组合创新: 将{elem_a}与{elem_b}结合",
                creativity_type=CreativityType.DIVERGENT,
                domain=f"{domain_a}+{domain_b}",
                novelty=0.7,
                feasibility=0.4,
                sources=[domain_a, domain_b],
            )
            combinations.append(idea)

        return combinations


# ============================================================================
# 创意评估器
# ============================================================================

class IdeaEvaluator:
    """创意评估器"""

    def evaluate(self, idea: Idea) -> dict:
        """评估创意"""
        # 计算综合分数
        idea.score = (
            idea.novelty * 0.4 +
            idea.feasibility * 0.3 +
            idea.value * 0.3
        )

        return {
            'id': idea.id,
            'content': idea.content,
            'novelty': idea.novelty,
            'feasibility': idea.feasibility,
            'value': idea.value,
            'score': idea.score,
            'recommendation': self._get_recommendation(idea),
        }

    def _get_recommendation(self, idea: Idea) -> str:
        """获取推荐"""
        if idea.score >= 0.7:
            return "强烈推荐: 新颖且可行"
        elif idea.score >= 0.5:
            return "推荐: 值得进一步探索"
        elif idea.score >= 0.3:
            return "考虑: 需要改进可行性"
        else:
            return "暂缓: 新颖性或可行性不足"

    def rank_ideas(self, ideas: list) -> list:
        """对创意排名"""
        evaluated = [self.evaluate(idea) for idea in ideas]
        evaluated.sort(key=lambda x: x['score'], reverse=True)
        return evaluated


# ============================================================================
# 创造性思维引擎
# ============================================================================

class CreativeThinkingEngine:
    """
    创造性思维引擎 - 整合所有组件

    核心功能：
    1. 发散思维产生创意
    2. 类比推理借鉴跨领域知识
    3. 组合创新产生新想法
    4. 评估和筛选创意
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "creative_thinking"
        os.makedirs(storage_dir, exist_ok=True)

        self.divergent_thinker = DivergentThinker()
        self.analogical_reasoner = AnalogicalReasoner()
        self.combinatorial_innovator = CombinatorialInnovator()
        self.idea_evaluator = IdeaEvaluator()

        self.ideas: dict[str, Idea] = {}
        self.analogies: dict[str, Analogy] = {}

        self.storage_path = os.path.join(storage_dir, "ideas.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for i_data in data.get('ideas', []):
                    i_data['creativity_type'] = CreativityType(i_data['creativity_type'])
                    idea = Idea(**i_data)
                    self.ideas[idea.id] = idea

    def _save(self):
        """保存数据"""
        data = {
            'ideas': [],
        }

        for idea in self.ideas.values():
            i_dict = asdict(idea)
            i_dict['creativity_type'] = idea.creativity_type.value
            data['ideas'].append(i_dict)

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def brainstorm(self, problem: str, domain: str,
                    count: int = 10) -> list:
        """头脑风暴"""
        ideas = self.divergent_thinker.generate_ideas(problem, domain, count)

        # 保存创意
        for idea in ideas:
            self.ideas[idea.id] = idea

        self._save()

        # 评估和排名
        ranked = self.idea_evaluator.rank_ideas(ideas)
        return ranked

    def find_analogies(self, problem: str, source_domain: str,
                        target_domain: str) -> list:
        """查找类比"""
        analogies = self.analogical_reasoner.find_analogies(
            problem, source_domain, target_domain
        )

        # 保存类比
        for analogy in analogies:
            self.analogies[analogy.id] = analogy

        return [asdict(a) for a in analogies]

    def combine_ideas(self, domain_a: str, domain_b: str,
                       count: int = 5) -> list:
        """组合创新"""
        ideas = self.combinatorial_innovator.combine(domain_a, domain_b, count)

        # 保存创意
        for idea in ideas:
            self.ideas[idea.id] = idea

        self._save()

        # 评估
        evaluated = [self.idea_evaluator.evaluate(idea) for idea in ideas]
        return evaluated

    def get_best_ideas(self, top_k: int = 5) -> list:
        """获取最佳创意"""
        all_ideas = list(self.ideas.values())
        ranked = self.idea_evaluator.rank_ideas(all_ideas)
        return ranked[:top_k]

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_ideas': len(self.ideas),
            'total_analogies': len(self.analogies),
            'by_type': {
                t.value: sum(1 for i in self.ideas.values()
                            if i.creativity_type == t)
                for t in CreativityType
            },
        }

    def generate_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()

        report = []
        report.append("=" * 50)
        report.append("💡 创造性思维报告")
        report.append("=" * 50)
        report.append(f"\n创意总数: {stats['total_ideas']}")
        report.append(f"类比数量: {stats['total_analogies']}")

        if stats['by_type']:
            report.append("\n创意类型分布:")
            for ctype, count in stats['by_type'].items():
                if count > 0:
                    report.append(f"  - {ctype}: {count}")

        # 最佳创意
        best = self.get_best_ideas(3)
        if best:
            report.append("\n最佳创意:")
            for idea in best:
                report.append(f"  - [{idea['score']:.2f}] {idea['content'][:50]}...")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = CreativeThinkingEngine("test_creative_thinking")

    # 头脑风暴
    print("=== 头脑风暴 ===")
    ideas = engine.brainstorm("如何提高代码质量", "programming", count=5)
    for idea in ideas:
        print(f"  [{idea['score']:.2f}] {idea['content'][:60]}...")

    # 类比推理
    print("\n=== 类比推理 ===")
    analogies = engine.find_analogies("代码优化", "biology", "computer")
    for a in analogies[:3]:
        print(f"  {a['source_concept']} -> {a['target_concept']} (相似度: {a['similarity']:.2f})")

    # 组合创新
    print("\n=== 组合创新 ===")
    engine.combinatorial_innovator.add_elements("programming", ["算法", "数据结构", "设计模式"])
    engine.combinatorial_innovator.add_elements("biology", ["进化", "适应", "生态系统"])
    combinations = engine.combine_ideas("programming", "biology", count=3)
    for c in combinations:
        print(f"  [{c['score']:.2f}] {c['content'][:60]}...")

    # 报告
    print("\n" + engine.generate_report())