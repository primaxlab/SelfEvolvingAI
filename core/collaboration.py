"""
================================================================================
协作感知系统 (Collaboration Awareness System)
================================================================================

核心能力：
  1. 能力自评估 - 知道自己擅长什么、不擅长什么
  2. 协作者发现 - 找到合适的协作者（其他AI/工具/人）
  3. 任务分配 - 将任务分配给最合适的执行者
  4. 协作协调 - 协调多个执行者完成任务
  5. 结果整合 - 整合多方结果

设计原则：
  - 优势互补：找最合适的，不是找最好的
  - 效率优先：减少不必要的协作开销
  - 质量保证：多方验证提高质量
"""

import json
import os
import time
import hashlib
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# 数据结构
# ============================================================================

class CollaboratorType(Enum):
    SELF = "self"              # 自己处理
    AI_MODEL = "ai_model"      # 其他AI模型
    TOOL = "tool"             # 工具
    HUMAN = "human"           # 人类专家
    EXTERNAL_SERVICE = "external_service"  # 外部服务

class TaskComplexity(Enum):
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    EXPERT = 4

@dataclass
class Capability:
    """能力描述"""
    domain: str
    skill: str
    proficiency: float  # 0-1
    confidence: float   # 0-1
    last_used: float = 0.0

@dataclass
class Collaborator:
    """协作者"""
    id: str
    name: str
    collaborator_type: CollaboratorType
    capabilities: list  # list of Capability
    availability: float = 1.0  # 可用性 0-1
    reliability: float = 0.8   # 可靠性 0-1
    cost: float = 0.0          # 成本
    latency: float = 0.0       # 延迟(秒)
    contact_info: dict = field(default_factory=dict)

@dataclass
class TaskAssignment:
    """任务分配"""
    id: str
    task: str
    assigned_to: str  # collaborator id
    reason: str
    expected_quality: float
    expected_duration: float
    status: str = "pending"
    result: Any = None
    created_at: float = field(default_factory=time.time)

@dataclass
class CollaborationPlan:
    """协作计划"""
    id: str
    task: str
    assignments: list  # list of TaskAssignment
    coordination_strategy: str
    expected_quality: float
    expected_duration: float
    created_at: float = field(default_factory=time.time)


# ============================================================================
# 能力评估器
# ============================================================================

class CapabilityAssessor:
    """能力评估器"""

    def __init__(self):
        self.capabilities: dict[str, Capability] = {}
        self.performance_history: list[dict] = []

    def assess(self, domain: str, skill: str) -> Capability:
        """评估某项能力"""
        key = f"{domain}:{skill}"

        if key not in self.capabilities:
            self.capabilities[key] = Capability(
                domain=domain,
                skill=skill,
                proficiency=0.5,  # 默认中等
                confidence=0.3,   # 默认低置信度
            )

        return self.capabilities[key]

    def update_from_feedback(self, domain: str, skill: str,
                              success: bool, difficulty: float = 0.5):
        """根据反馈更新能力评估"""
        key = f"{domain}:{skill}"
        cap = self.assess(domain, skill)

        # 更新熟练度
        if success:
            cap.proficiency = min(1.0, cap.proficiency + 0.05 * difficulty)
        else:
            cap.proficiency = max(0.0, cap.proficiency - 0.03 * difficulty)

        # 更新置信度
        cap.confidence = min(0.95, cap.confidence + 0.02)
        cap.last_used = time.time()

        # 记录历史
        self.performance_history.append({
            'domain': domain,
            'skill': skill,
            'success': success,
            'difficulty': difficulty,
            'timestamp': time.time(),
        })

    def get_strengths(self, threshold: float = 0.7) -> list:
        """获取优势领域"""
        return [
            cap for cap in self.capabilities.values()
            if cap.proficiency >= threshold
        ]

    def get_weaknesses(self, threshold: float = 0.4) -> list:
        """获取薄弱领域"""
        return [
            cap for cap in self.capabilities.values()
            if cap.proficiency < threshold
        ]

    def can_handle(self, domain: str, skill: str,
                   min_proficiency: float = 0.5) -> bool:
        """判断是否能处理某任务"""
        cap = self.assess(domain, skill)
        return cap.proficiency >= min_proficiency


# ============================================================================
# 协作者管理器
# ============================================================================

class CollaboratorManager:
    """协作者管理器"""

    def __init__(self):
        self.collaborators: dict[str, Collaborator] = {}
        self._register_defaults()

    def _register_defaults(self):
        """注册默认协作者"""
        # 自己
        self.collaborators['self'] = Collaborator(
            id='self',
            name='Self',
            collaborator_type=CollaboratorType.SELF,
            capabilities=[],
            availability=1.0,
            reliability=0.9,
            cost=0.0,
            latency=0.0,
        )

        # 代码分析工具
        self.collaborators['code_analyzer'] = Collaborator(
            id='code_analyzer',
            name='Code Analyzer',
            collaborator_type=CollaboratorType.TOOL,
            capabilities=[
                Capability('programming', 'code_analysis', 0.9, 0.9),
                Capability('programming', 'bug_detection', 0.85, 0.85),
            ],
            availability=1.0,
            reliability=0.95,
            cost=0.0,
            latency=0.1,
        )

        # 搜索引擎
        self.collaborators['search_engine'] = Collaborator(
            id='search_engine',
            name='Search Engine',
            collaborator_type=CollaboratorType.EXTERNAL_SERVICE,
            capabilities=[
                Capability('general', 'information_retrieval', 0.9, 0.8),
            ],
            availability=0.99,
            reliability=0.85,
            cost=0.001,
            latency=0.5,
        )

    def register(self, collaborator: Collaborator):
        """注册协作者"""
        self.collaborators[collaborator.id] = collaborator

    def find_capable(self, domain: str, skill: str,
                     min_proficiency: float = 0.5) -> list:
        """找到有能力的协作者"""
        capable = []

        for collab in self.collaborators.values():
            for cap in collab.capabilities:
                if (cap.domain == domain and
                    cap.skill == skill and
                    cap.proficiency >= min_proficiency):
                    capable.append(collab)
                    break

        # 按熟练度排序
        capable.sort(
            key=lambda c: max(
                (cap.proficiency for cap in c.capabilities
                 if cap.domain == domain and cap.skill == skill),
                default=0
            ),
            reverse=True
        )

        return capable

    def find_best(self, domain: str, skill: str,
                  consider_cost: bool = True) -> Optional[Collaborator]:
        """找到最佳协作者"""
        capable = self.find_capable(domain, skill)

        if not capable:
            return None

        if not consider_cost:
            return capable[0]

        # 综合考虑质量、成本、延迟
        def score(c: Collaborator) -> float:
            quality = max(
                (cap.proficiency for cap in c.capabilities
                 if cap.domain == domain and cap.skill == skill),
                default=0
            )
            cost_factor = 1.0 / (1.0 + c.cost)
            latency_factor = 1.0 / (1.0 + c.latency)
            return quality * 0.6 + cost_factor * 0.2 + latency_factor * 0.2

        capable.sort(key=score, reverse=True)
        return capable[0]


# ============================================================================
# 任务分配器
# ============================================================================

class TaskAllocator:
    """任务分配器"""

    def __init__(self, capability_assessor: CapabilityAssessor,
                 collaborator_manager: CollaboratorManager):
        self.assessor = capability_assessor
        self.collab_mgr = collaborator_manager

    def analyze_task(self, task: str) -> dict:
        """分析任务"""
        # 简单的关键词分析
        task_lower = task.lower()

        # 识别领域
        domain = 'general'
        if any(kw in task_lower for kw in ['代码', '编程', '函数', 'code', 'function']):
            domain = 'programming'
        elif any(kw in task_lower for kw in ['数学', '计算', 'math', 'calculate']):
            domain = 'math'
        elif any(kw in task_lower for kw in ['搜索', '查找', 'search', 'find']):
            domain = 'information'

        # 识别复杂度
        complexity = TaskComplexity.MODERATE
        if len(task) < 50:
            complexity = TaskComplexity.SIMPLE
        elif len(task) > 200:
            complexity = TaskComplexity.COMPLEX

        return {
            'domain': domain,
            'complexity': complexity,
            'estimated_duration': len(task) * 0.01,  # 简单估算
        }

    def allocate(self, task: str) -> TaskAssignment:
        """分配任务"""
        analysis = self.analyze_task(task)
        domain = analysis['domain']

        # 检查自己是否能处理
        if self.assessor.can_handle(domain, 'general', min_proficiency=0.6):
            # 自己处理
            return TaskAssignment(
                id=f"assign_{hashlib.md5(task.encode()).hexdigest()[:8]}",
                task=task,
                assigned_to='self',
                reason='自身能力足够',
                expected_quality=0.8,
                expected_duration=analysis['estimated_duration'],
            )

        # 找外部协作者
        best_collab = self.collab_mgr.find_best(domain, 'general')

        if best_collab:
            return TaskAssignment(
                id=f"assign_{hashlib.md5(task.encode()).hexdigest()[:8]}",
                task=task,
                assigned_to=best_collab.id,
                reason=f'找到更合适的协作者: {best_collab.name}',
                expected_quality=max(
                    (cap.proficiency for cap in best_collab.capabilities
                     if cap.domain == domain),
                    default=0.5
                ),
                expected_duration=analysis['estimated_duration'] + best_collab.latency,
            )

        # 没有合适的协作者，自己尝试
        return TaskAssignment(
            id=f"assign_{hashlib.md5(task.encode()).hexdigest()[:8]}",
            task=task,
            assigned_to='self',
            reason='没有找到合适的协作者',
            expected_quality=0.5,
            expected_duration=analysis['estimated_duration'],
        )


# ============================================================================
# 协作协调器
# ============================================================================

class CollaborationCoordinator:
    """协作协调器"""

    def __init__(self):
        self.active_collaborations: dict[str, CollaborationPlan] = {}

    def create_plan(self, task: str, assignments: list) -> CollaborationPlan:
        """创建协作计划"""
        plan_id = hashlib.md5(f"{task}{time.time()}".encode()).hexdigest()[:12]

        # 计算整体预期质量
        if assignments:
            expected_quality = sum(a.expected_quality for a in assignments) / len(assignments)
        else:
            expected_quality = 0.5

        # 计算预期时长（并行取最大，串行求和）
        expected_duration = max(a.expected_duration for a in assignments) if assignments else 0

        plan = CollaborationPlan(
            id=plan_id,
            task=task,
            assignments=assignments,
            coordination_strategy='parallel',
            expected_quality=expected_quality,
            expected_duration=expected_duration,
        )

        self.active_collaborations[plan_id] = plan
        return plan

    def execute_plan(self, plan_id: str) -> dict:
        """执行协作计划"""
        plan = self.active_collaborations.get(plan_id)
        if not plan:
            return {'error': '计划不存在'}

        results = []
        for assignment in plan.assignments:
            # 这里是框架，实际使用时调用对应的协作者
            assignment.status = 'completed'
            assignment.result = f"模拟结果: {assignment.task[:50]}"
            results.append(asdict(assignment))

        return {
            'plan_id': plan_id,
            'results': results,
            'overall_success': all(r['status'] == 'completed' for r in results),
        }


# ============================================================================
# 协作感知引擎
# ============================================================================

class CollaborationEngine:
    """
    协作感知引擎 - 整合所有组件

    核心功能：
    1. 评估自身能力
    2. 发现合适的协作者
    3. 智能分配任务
    4. 协调多方协作
    5. 整合结果
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "collaboration"
        os.makedirs(storage_dir, exist_ok=True)

        self.assessor = CapabilityAssessor()
        self.collab_mgr = CollaboratorManager()
        self.allocator = TaskAllocator(self.assessor, self.collab_mgr)
        self.coordinator = CollaborationCoordinator()

        self.collaboration_history: list[dict] = []

        self.storage_path = os.path.join(storage_dir, "collaboration.json")
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.collaboration_history = data.get('history', [])

    def _save(self):
        """保存数据"""
        data = {
            'history': self.collaboration_history[-100:],  # 只保留最近100条
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def should_collaborate(self, task: str) -> dict:
        """判断是否需要协作"""
        analysis = self.allocator.analyze_task(task)
        domain = analysis['domain']

        # 检查自身能力
        can_self_handle = self.assessor.can_handle(domain, 'general', min_proficiency=0.6)

        # 检查是否有更好的协作者
        best_collab = self.collab_mgr.find_best(domain, 'general')
        self_proficiency = self.assessor.assess(domain, 'general').proficiency

        if best_collab:
            best_proficiency = max(
                (cap.proficiency for cap in best_collab.capabilities
                 if cap.domain == domain),
                default=0
            )
        else:
            best_proficiency = 0

        should_collab = best_proficiency > self_proficiency * 1.2  # 协作者要好20%以上

        return {
            'should_collaborate': should_collab,
            'self_proficiency': self_proficiency,
            'best_collaborator': best_collab.name if best_collab else None,
            'collaborator_proficiency': best_proficiency,
            'reason': '找到更合适的协作者' if should_collab else '自身能力足够',
        }

    def collaborate(self, task: str) -> dict:
        """执行协作"""
        # 1. 分配任务
        assignment = self.allocator.allocate(task)

        # 2. 创建协作计划
        plan = self.coordinator.create_plan(task, [assignment])

        # 3. 执行协作
        result = self.coordinator.execute_plan(plan.id)

        # 4. 记录协作历史
        self.collaboration_history.append({
            'task': task,
            'assignment': asdict(assignment),
            'result': result,
            'timestamp': time.time(),
        })

        self._save()

        return {
            'assignment': asdict(assignment),
            'result': result,
        }

    def update_capability(self, domain: str, skill: str,
                          success: bool, difficulty: float = 0.5):
        """更新能力评估"""
        self.assessor.update_from_feedback(domain, skill, success, difficulty)

    def register_collaborator(self, collaborator: Collaborator):
        """注册协作者"""
        self.collab_mgr.register(collaborator)

    def get_collaboration_stats(self) -> dict:
        """获取协作统计"""
        total = len(self.collaboration_history)
        self_handled = sum(
            1 for h in self.collaboration_history
            if h['assignment']['assigned_to'] == 'self'
        )
        delegated = total - self_handled

        return {
            'total_tasks': total,
            'self_handled': self_handled,
            'delegated': delegated,
            'delegation_rate': delegated / max(1, total),
            'strengths': [
                {'domain': s.domain, 'skill': s.skill, 'proficiency': s.proficiency}
                for s in self.assessor.get_strengths()
            ],
            'weaknesses': [
                {'domain': w.domain, 'skill': w.skill, 'proficiency': w.proficiency}
                for w in self.assessor.get_weaknesses()
            ],
        }

    def generate_report(self) -> str:
        """生成协作报告"""
        stats = self.get_collaboration_stats()

        report = []
        report.append("=" * 50)
        report.append("🤝 协作感知报告")
        report.append("=" * 50)
        report.append(f"\n总任务数: {stats['total_tasks']}")
        report.append(f"自行处理: {stats['self_handled']}")
        report.append(f"委派处理: {stats['delegated']}")
        report.append(f"委派率: {stats['delegation_rate']:.0%}")

        if stats['strengths']:
            report.append("\n优势领域:")
            for s in stats['strengths'][:5]:
                report.append(f"  - {s['domain']}/{s['skill']}: {s['proficiency']:.0%}")

        if stats['weaknesses']:
            report.append("\n薄弱领域:")
            for w in stats['weaknesses'][:5]:
                report.append(f"  - {w['domain']}/{w['skill']}: {w['proficiency']:.0%}")

        return "\n".join(report)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    engine = CollaborationEngine("test_collaboration")

    # 测试任务
    tasks = [
        "写一个Python函数读取文件",
        "解释量子力学的基本原理",
        "优化数据库查询性能",
        "设计一个微服务架构",
    ]

    print("=== 协作决策 ===")
    for task in tasks:
        decision = engine.should_collaborate(task)
        print(f"\n任务: {task}")
        print(f"  需要协作: {decision['should_collaborate']}")
        print(f"  自身能力: {decision['self_proficiency']:.2f}")
        if decision['best_collaborator']:
            print(f"  最佳协作者: {decision['best_collaborator']}")

    # 执行协作
    print("\n=== 执行协作 ===")
    result = engine.collaborate("分析代码中的安全漏洞")
    print(f"分配给: {result['assignment']['assigned_to']}")
    print(f"原因: {result['assignment']['reason']}")

    # 报告
    print("\n" + engine.generate_report())