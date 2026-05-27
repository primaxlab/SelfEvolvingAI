"""全文检索 - 倒排索引、BM25排序、模糊搜索"""

import json
import os
import time
import math
import hashlib
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict


class IndexType(Enum):
    INVERTED = "inverted"
    TRIE = "trie"
    NGRAM = "ngram"


@dataclass
class Document:
    doc_id: str
    content: str
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: List[str] = field(default_factory=list)
    created_at: float = 0.0


@dataclass
class SearchResult:
    doc_id: str
    score: float
    title: str = ""
    snippet: str = ""
    highlights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexEntry:
    term: str
    doc_freq: int = 0
    postings: Dict[str, int] = field(default_factory=dict)  # doc_id -> tf


class SearchEngine:
    """全文检索引擎"""

    def __init__(self, storage_dir: str = "data/search"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.documents: Dict[str, Document] = {}
        self.inverted_index: Dict[str, IndexEntry] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.total_docs: int = 0

        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "search_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("documents", {}).items():
                    self.documents[k] = Document(**v)
                for k, v in data.get("inverted_index", {}).items():
                    self.inverted_index[k] = IndexEntry(**v)
                self.doc_lengths = data.get("doc_lengths", {})
                self.avg_doc_length = data.get("avg_doc_length", 0)
                self.total_docs = data.get("total_docs", 0)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "search_data.json")
        data = {
            "documents": {k: asdict(v) for k, v in self.documents.items()},
            "inverted_index": {k: asdict(v) for k, v in self.inverted_index.items()},
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            "total_docs": self.total_docs,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        # 中文按字分，英文按词分
        tokens = []
        current_word = []

        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                if current_word:
                    tokens.append(''.join(current_word))
                    current_word = []
                tokens.append(char)
            elif char.isalnum():
                current_word.append(char)
            else:
                if current_word:
                    tokens.append(''.join(current_word))
                    current_word = []

        if current_word:
            tokens.append(''.join(current_word))

        # 添加2-gram
        ngrams = []
        for i in range(len(tokens) - 1):
            ngrams.append(tokens[i] + tokens[i + 1])

        return tokens + ngrams

    def add_document(self, content: str, title: str = "",
                     doc_id: str = "", metadata: Dict[str, Any] = None) -> str:
        """添加文档"""
        if not doc_id:
            doc_id = hashlib.md5(f"{content[:100]}_{time.time()}".encode()).hexdigest()[:12]

        tokens = self.tokenize(f"{title} {content}")

        doc = Document(
            doc_id=doc_id,
            content=content,
            title=title,
            tokens=tokens,
            metadata=metadata or {},
            created_at=time.time(),
        )
        self.documents[doc_id] = doc

        # 更新倒排索引
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1

        for term, freq in tf.items():
            if term not in self.inverted_index:
                self.inverted_index[term] = IndexEntry(term=term)
            entry = self.inverted_index[term]
            entry.postings[doc_id] = freq
            entry.doc_freq = len(entry.postings)

        # 更新统计
        self.doc_lengths[doc_id] = len(tokens)
        self.total_docs = len(self.documents)
        if self.total_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.total_docs

        self._save()
        return doc_id

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """批量添加"""
        doc_ids = []
        for doc in documents:
            doc_id = self.add_document(
                content=doc.get("content", ""),
                title=doc.get("title", ""),
                metadata=doc.get("metadata", {}),
            )
            doc_ids.append(doc_id)
        return doc_ids

    def search(self, query: str, top_k: int = 10,
               filters: Dict[str, Any] = None) -> List[SearchResult]:
        """搜索"""
        tokens = self.tokenize(query)
        if not tokens:
            return []

        # BM25参数
        k1 = 1.5
        b = 0.75

        scores: Dict[str, float] = defaultdict(float)

        for term in tokens:
            if term not in self.inverted_index:
                continue

            entry = self.inverted_index[term]
            df = entry.doc_freq
            if df == 0:
                continue

            # IDF
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1)

            for doc_id, tf in entry.postings.items():
                if doc_id not in self.doc_lengths:
                    continue

                doc_len = self.doc_lengths[doc_id]
                avg_len = self.avg_doc_length if self.avg_doc_length > 0 else 1

                # BM25得分
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
                scores[doc_id] += idf * tf_norm

        # 过滤
        if filters:
            filtered_scores = {}
            for doc_id, score in scores.items():
                doc = self.documents.get(doc_id)
                if doc and all(doc.metadata.get(k) == v for k, v in filters.items()):
                    filtered_scores[doc_id] = score
            scores = filtered_scores

        # 排序
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_id, score in sorted_results:
            doc = self.documents.get(doc_id)
            if doc:
                # 生成摘要
                snippet = doc.content[:200]
                highlights = [t for t in tokens if t in doc.content.lower()]

                results.append(SearchResult(
                    doc_id=doc_id,
                    score=round(score, 4),
                    title=doc.title,
                    snippet=snippet,
                    highlights=list(set(highlights))[:5],
                    metadata=doc.metadata,
                ))

        return results

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id not in self.documents:
            return False

        doc = self.documents[doc_id]

        # 从索引中删除
        for term in set(doc.tokens):
            if term in self.inverted_index:
                entry = self.inverted_index[term]
                entry.postings.pop(doc_id, None)
                entry.doc_freq = len(entry.postings)
                if entry.doc_freq == 0:
                    del self.inverted_index[term]

        del self.documents[doc_id]
        self.doc_lengths.pop(doc_id, None)
        self.total_docs = len(self.documents)

        self._save()
        return True

    def suggest(self, prefix: str, top_k: int = 5) -> List[str]:
        """搜索建议"""
        prefix = prefix.lower()
        suggestions = []

        for term in self.inverted_index:
            if term.startswith(prefix):
                suggestions.append((term, self.inverted_index[term].doc_freq))

        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions[:top_k]]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档"""
        doc = self.documents.get(doc_id)
        if doc:
            return asdict(doc)
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents_count": len(self.documents),
            "index_terms": len(self.inverted_index),
            "avg_doc_length": round(self.avg_doc_length, 1),
        }

    def generate_report(self) -> Dict[str, Any]:
        return {
            "total_documents": len(self.documents),
            "index_terms": len(self.inverted_index),
            "avg_doc_length": round(self.avg_doc_length, 1),
        }


if __name__ == "__main__":
    print("=== 全文检索测试 ===")
    engine = SearchEngine()

    docs = [
        {"content": "Python是一种广泛使用的高级编程语言，具有简洁的语法", "title": "Python入门"},
        {"content": "机器学习是人工智能的一个分支，使用算法从数据中学习", "title": "机器学习基础"},
        {"content": "深度学习使用神经网络来模拟人类大脑的工作方式", "title": "深度学习"},
        {"content": "Python在数据科学和机器学习领域非常流行", "title": "Python数据科学"},
        {"content": "自然语言处理是AI的重要应用方向", "title": "NLP入门"},
    ]

    ids = engine.add_documents_batch(docs)
    print(f"添加 {len(ids)} 个文档")

    results = engine.search("Python机器学习")
    print(f"\n搜索 'Python机器学习':")
    for r in results:
        print(f"  [{r.score:.4f}] {r.title}: {r.snippet[:50]}...")

    results = engine.search("人工智能")
    print(f"\n搜索 '人工智能':")
    for r in results:
        print(f"  [{r.score:.4f}] {r.title}")

    suggestions = engine.suggest("机")
    print(f"\n建议 '机': {suggestions}")

    report = engine.generate_report()
    print(f"\n检索报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
