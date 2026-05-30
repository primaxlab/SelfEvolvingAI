"""
Token 优化器 - 越用越省的核心模块

功能：
1. 语义缓存 - 相似问题复用结果
2. 上下文压缩 - 压缩历史对话
3. 提示词精简 - 自动精简冗余
4. 模型路由 - 简单问题用便宜模型
5. 增量学习 - 常见问题本地回答
"""

import os
import json
import time
import hashlib
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """缓存条目"""
    question: str
    question_hash: str
    answer: str
    tokens_saved: int
    hit_count: int
    created_at: float
    last_used: float
    model: str


class TokenOptimizer:
    """Token 优化器"""
    
    def __init__(self, data_dir: str = ".evolution/data"):
        self.data_dir = data_dir
        self.cache_file = os.path.join(data_dir, "token_cache.json")
        self.stats_file = os.path.join(data_dir, "token_stats.json")
        
        # 缓存存储
        self.cache: Dict[str, CacheEntry] = {}
        
        # 统计数据
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "tokens_original": 0,
            "tokens_optimized": 0,
            "tokens_saved": 0,
            "money_saved": 0.0,
            "start_time": time.time()
        }
        
        # 加载历史数据
        self._load_cache()
        self._load_stats()
    
    # ==================== 1. 语义缓存 ====================
    
    def get_cache(self, question: str) -> Optional[str]:
        """查询缓存"""
        question_hash = self._hash_question(question)
        
        # 精确匹配
        if question_hash in self.cache:
            entry = self.cache[question_hash]
            entry.hit_count += 1
            entry.last_used = time.time()
            self.stats["cache_hits"] += 1
            self._save_cache()
            return entry.answer
        
        # 模糊匹配（简单实现）
        question_lower = question.lower().strip()
        for entry in self.cache.values():
            if self._similarity(question_lower, entry.question.lower()) > 0.9:
                entry.hit_count += 1
                entry.last_used = time.time()
                self.stats["cache_hits"] += 1
                self._save_cache()
                return entry.answer
        
        return None
    
    def save_cache(self, question: str, answer: str, model: str = "unknown", tokens_used: int = 0):
        """保存到缓存"""
        question_hash = self._hash_question(question)
        
        entry = CacheEntry(
            question=question,
            question_hash=question_hash,
            answer=answer,
            tokens_saved=tokens_used,
            hit_count=0,
            created_at=time.time(),
            last_used=time.time(),
            model=model
        )
        
        self.cache[question_hash] = entry
        self._save_cache()
    
    # ==================== 2. 上下文压缩 ====================
    
    def compress_context(self, messages: List[Dict], max_tokens: int = 2000) -> List[Dict]:
        """压缩对话上下文"""
        if not messages:
            return messages
        
        # 计算当前 token 数
        total_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in messages)
        
        # 如果没超限，不压缩
        if total_tokens <= max_tokens:
            return messages
        
        # 保留最近 3 轮对话
        recent = messages[-6:]  # 最近 6 条（3轮）
        old = messages[:-6]
        
        if not old:
            return recent
        
        # 把旧对话总结成摘要
        summary = self._summarize_messages(old)
        
        # 返回：摘要 + 最近对话
        compressed = [{"role": "system", "content": f"[历史摘要] {summary}"}] + recent
        
        return compressed
    
    def _summarize_messages(self, messages: List[Dict]) -> str:
        """总结对话（简单实现）"""
        topics = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 20:
                # 提取关键信息
                topics.append(content[:50])
        
        if not topics:
            return "无历史对话"
        
        # 简单拼接
        return "；".join(topics[:3]) + "..."
    
    # ==================== 3. 提示词精简 ====================
    
    def optimize_prompt(self, system_prompt: str, question: str) -> str:
        """根据问题复杂度精简提示词"""
        complexity = self._classify_complexity(question)
        
        if complexity == "simple":
            # 简单问题，精简提示词
            return self._extract_core_prompt(system_prompt)
        elif complexity == "medium":
            # 中等问题，保留核心
            return self._extract_core_prompt(system_prompt, keep_details=True)
        else:
            # 复杂问题，保留完整
            return system_prompt
    
    def _extract_core_prompt(self, prompt: str, keep_details: bool = False) -> str:
        """提取核心提示词"""
        # 移除示例、详细说明等
        lines = prompt.split("\n")
        core_lines = []
        
        for line in lines:
            # 跳过示例
            if "例如" in line or "比如" in line or "For example" in line:
                if not keep_details:
                    continue
            # 跳过详细说明
            if len(line) > 100 and not keep_details:
                continue
            core_lines.append(line)
        
        return "\n".join(core_lines[:5])  # 只保留前5行
    
    # ==================== 4. 模型路由 ====================
    
    def select_model(self, question: str, available_models: List[Dict]) -> Dict:
        """选择最合适的模型"""
        complexity = self._classify_complexity(question)
        
        # 简单问题用便宜模型
        if complexity == "simple":
            # 找最便宜的模型
            return min(available_models, key=lambda m: m.get("input_price", 999))
        
        # 复杂问题用好模型
        elif complexity == "complex":
            # 找最好的模型（假设最贵的最好）
            return max(available_models, key=lambda m: m.get("quality", 0))
        
        # 中等问题用性价比模型
        else:
            # 找性价比最高的
            return min(available_models, key=lambda m: m.get("input_price", 999))
    
    def _classify_complexity(self, question: str) -> str:
        """分类问题复杂度"""
        question_lower = question.lower()
        
        # 简单问题特征
        simple_patterns = [
            "你好", "hi", "hello", "谢谢", "thanks",
            "是什么", "什么是", "定义", "意思",
            "天气", "时间", "日期",
            "对吗", "是吗", "好吗",
        ]
        
        # 复杂问题特征
        complex_patterns = [
            "分析", "优化", "设计", "架构", "推理",
            "比较", "对比", "评估", "预测",
            "实现", "开发", "构建", "重构",
            "为什么", "原因", "原理", "机制",
        ]
        
        # 中等特征
        medium_patterns = [
            "怎么做", "如何", "方法", "步骤",
            "解释", "说明", "介绍",
            "代码", "脚本", "程序",
        ]
        
        if any(p in question_lower for p in simple_patterns):
            return "simple"
        elif any(p in question_lower for p in complex_patterns):
            return "complex"
        elif any(p in question_lower for p in medium_patterns):
            return "medium"
        
        # 根据长度判断
        if len(question) < 20:
            return "simple"
        elif len(question) > 100:
            return "complex"
        
        return "medium"
    
    # ==================== 5. 增量学习 ====================
    
    def learn_from_interaction(self, question: str, answer: str, feedback: str = "positive"):
        """从交互中学习"""
        if feedback == "positive":
            # 正面反馈，保存到知识库
            self.save_cache(question, answer, tokens_used=self._estimate_tokens(answer))
    
    def get_learned_answer(self, question: str) -> Optional[str]:
        """获取学习过的答案"""
        return self.get_cache(question)
    
    # ==================== 统计和报告 ====================
    
    def record_usage(self, original_tokens: int, optimized_tokens: int, price_per_token: float = 0.000002):
        """记录使用情况"""
        self.stats["total_calls"] += 1
        self.stats["tokens_original"] += original_tokens
        self.stats["tokens_optimized"] += optimized_tokens
        self.stats["tokens_saved"] += (original_tokens - optimized_tokens)
        self.stats["money_saved"] += (original_tokens - optimized_tokens) * price_per_token
        self._save_stats()
    
    def get_stats(self) -> Dict:
        """获取统计数据"""
        total = self.stats["total_calls"]
        hits = self.stats["cache_hits"]
        
        return {
            "total_calls": total,
            "cache_hits": hits,
            "cache_hit_rate": f"{(hits/total*100):.1f}%" if total > 0 else "0%",
            "tokens_original": self.stats["tokens_original"],
            "tokens_optimized": self.stats["tokens_optimized"],
            "tokens_saved": self.stats["tokens_saved"],
            "savings_rate": f"{(self.stats['tokens_saved']/self.stats['tokens_original']*100):.1f}%" if self.stats["tokens_original"] > 0 else "0%",
            "money_saved_usd": f"${self.stats['money_saved']:.4f}",
            "cache_size": len(self.cache),
            "uptime_hours": f"{(time.time() - self.stats['start_time'])/3600:.1f}"
        }
    
    def get_report(self) -> str:
        """生成报告"""
        stats = self.get_stats()
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║                    Token 优化报告                          ║
╠════════════════════════════════════════════════════════════╣
║  📊 调用统计                                               ║
║  • 总调用次数: {stats['total_calls']:>10} 次                        ║
║  • 缓存命中:   {stats['cache_hits']:>10} 次                        ║
║  • 命中率:     {stats['cache_hit_rate']:>10}                           ║
╠════════════════════════════════════════════════════════════╣
║  💰 Token 统计                                             ║
║  • 原始 Token: {stats['tokens_original']:>10}                         ║
║  • 优化 Token: {stats['tokens_optimized']:>10}                         ║
║  • 节省 Token: {stats['tokens_saved']:>10}                         ║
║  • 节省率:     {stats['savings_rate']:>10}                           ║
╠════════════════════════════════════════════════════════════╣
║  💵 成本节省                                               ║
║  • 节省金额:   {stats['money_saved_usd']:>10}                         ║
║  • 缓存大小:   {stats['cache_size']:>10} 条                        ║
║  • 运行时间:   {stats['uptime_hours']:>10} 小时                      ║
╚════════════════════════════════════════════════════════════╝
"""
        return report
    
    # ==================== 内部方法 ====================
    
    def _hash_question(self, question: str) -> str:
        """生成问题哈希"""
        # 标准化问题
        normalized = question.lower().strip()
        # 移除标点
        normalized = normalized.replace("？", "").replace("?", "").replace("！", "").replace("!", "")
        # 生成哈希
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _similarity(self, s1: str, s2: str) -> float:
        """简单相似度计算"""
        # 基于字符重叠的相似度
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数（中文约 1.5 字/token，英文约 4 字符/token）"""
        if not text:
            return 0
        # 简单估算
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    def _load_cache(self):
        """加载缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self.cache[key] = CacheEntry(**value)
        except Exception:
            pass
    
    def _save_cache(self):
        """保存缓存"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            data = {key: asdict(entry) for key, entry in self.cache.items()}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _load_stats(self):
        """加载统计"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats.update(json.load(f))
        except Exception:
            pass
    
    def _save_stats(self):
        """保存统计"""
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# 全局实例
_token_optimizer = None

def get_token_optimizer() -> TokenOptimizer:
    """获取 Token 优化器单例"""
    global _token_optimizer
    if _token_optimizer is None:
        _token_optimizer = TokenOptimizer()
    return _token_optimizer
