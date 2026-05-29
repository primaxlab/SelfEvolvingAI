"""消息队列系统 - 消息生产、消费、队列管理、死信处理"""

import json
import os
import time
import hashlib
import threading
import uuid
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
import heapq


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    COMMAND = "command"
    EVENT = "event"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class QueueType(Enum):
    """队列类型"""
    STANDARD = "standard"
    PRIORITY = "priority"
    FIFO = "fifo"
    LIFO = "lifo"
    DELAY = "delay"


@dataclass
class Message:
    """消息"""
    message_id: str
    queue_name: str
    content: Any
    message_type: str = "text"
    priority: int = 1
    status: str = "pending"
    created_at: float = 0.0
    scheduled_at: float = 0.0
    processed_at: float = 0.0
    completed_at: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    delay_seconds: float = 0
    ttl: float = 0  # 存活时间(秒)
    headers: Dict[str, str] = field(default_factory=dict)
    error: str = ""
    dead_letter_reason: str = ""


@dataclass
class Queue:
    """队列"""
    queue_id: str
    name: str
    queue_type: str = "standard"
    max_size: int = 10000
    message_ttl: float = 0
    dead_letter_queue: str = ""
    retry_limit: int = 3
    retry_delay: float = 5.0
    is_active: bool = True
    created_at: float = 0.0
    consumer_count: int = 0


@dataclass
class Consumer:
    """消费者"""
    consumer_id: str
    name: str
    queue_name: str
    is_active: bool = True
    prefetch_count: int = 1
    processing_count: int = 0
    processed_count: int = 0
    failed_count: int = 0
    last_message_at: float = 0.0
    created_at: float = 0.0


@dataclass
class Subscription:
    """订阅"""
    subscription_id: str
    queue_name: str
    pattern: str = ""  # 通配符模式
    callback_name: str = ""
    is_active: bool = True
    created_at: float = 0.0


class MessageQueueEngine:
    """消息队列引擎"""

    def __init__(self, storage_dir: str = "data/mq"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.queues: Dict[str, Queue] = {}
        self.messages: Dict[str, Message] = {}
        self.consumers: Dict[str, Consumer] = {}
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)

        # 内存队列(按优先级排序)
        self.queue_messages: Dict[str, List] = defaultdict(list)  # heap queue
        self.delayed_messages: List[Message] = []  # 延迟消息

        # 统计
        self.stats = {
            "total_produced": 0,
            "total_consumed": 0,
            "total_failed": 0,
            "total_dead": 0
        }

        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """加载数据"""
        path = os.path.join(self.storage_dir, "mq_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("queues", {}).items():
                    self.queues[k] = Queue(**v)
                for k, v in data.get("messages", {}).items():
                    self.messages[k] = Message(**v)
                for k, v in data.get("consumers", {}).items():
                    self.consumers[k] = Consumer(**v)
                self.stats = data.get("stats", self.stats)

                # 重建内存队列
                for msg in self.messages.values():
                    if msg.status == MessageStatus.PENDING.value:
                        self._add_to_queue(msg)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """保存数据"""
        path = os.path.join(self.storage_dir, "mq_data.json")
        data = {
            "queues": {k: asdict(v) for k, v in self.queues.items()},
            "messages": {k: asdict(v) for k, v in list(self.messages.items())[-50000:]},
            "consumers": {k: asdict(v) for k, v in self.consumers.items()},
            "stats": self.stats
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _add_to_queue(self, message: Message):
        """添加到内存队列"""
        # 使用负优先级实现最大堆(高优先级先出)
        heapq.heappush(
            self.queue_messages[message.queue_name],
            (-message.priority, message.created_at, message.message_id)
        )

    def create_queue(self, name: str, queue_type: str = "standard",
                     max_size: int = 10000, message_ttl: float = 0,
                     dead_letter_queue: str = "", retry_limit: int = 3) -> str:
        """创建队列"""
        queue_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        queue = Queue(
            queue_id=queue_id,
            name=name,
            queue_type=queue_type,
            max_size=max_size,
            message_ttl=message_ttl,
            dead_letter_queue=dead_letter_queue or f"{name}_dlq",
            retry_limit=retry_limit,
            is_active=True,
            created_at=time.time()
        )
        self.queues[name] = queue

        # 自动创建死信队列（避免无限递归：DLQ 不再创建自己的 DLQ）
        dlq_name = queue.dead_letter_queue
        if dlq_name not in self.queues and not dlq_name.endswith('_dlq'):
            self.create_queue(dlq_name, "standard", max_size=1000, dead_letter_queue="")

        self._save()
        return queue_id

    def produce(self, queue_name: str, content: Any,
                message_type: str = "text", priority: int = 1,
                delay_seconds: float = 0, ttl: float = 0,
                headers: Dict[str, str] = None) -> str:
        """生产消息"""
        if queue_name not in self.queues:
            self.create_queue(queue_name)

        queue = self.queues[queue_name]

        # 检查队列大小
        queue_size = sum(1 for m in self.messages.values()
                        if m.queue_name == queue_name and m.status == MessageStatus.PENDING.value)
        if queue_size >= queue.max_size:
            return ""

        message_id = str(uuid.uuid4())[:12]
        now = time.time()

        message = Message(
            message_id=message_id,
            queue_name=queue_name,
            content=content,
            message_type=message_type,
            priority=priority,
            status=MessageStatus.PENDING.value,
            created_at=now,
            scheduled_at=now + delay_seconds if delay_seconds > 0 else now,
            delay_seconds=delay_seconds,
            ttl=ttl,
            headers=headers or {},
            max_retries=queue.retry_limit
        )

        self.messages[message_id] = message

        if delay_seconds > 0:
            self.delayed_messages.append(message)
        else:
            self._add_to_queue(message)

        self.stats["total_produced"] += 1
        self._save()
        return message_id

    def consume(self, queue_name: str, consumer_id: str = "") -> Optional[Message]:
        """消费消息"""
        if queue_name not in self.queues:
            return None

        # 处理延迟消息
        self._process_delayed_messages()

        # 从队列获取消息
        with self._lock:
            while self.queue_messages[queue_name]:
                neg_priority, created_at, message_id = heapq.heappop(self.queue_messages[queue_name])

                if message_id not in self.messages:
                    continue

                message = self.messages[message_id]

                # 检查TTL
                if message.ttl > 0 and (time.time() - message.created_at) > message.ttl:
                    message.status = MessageStatus.DEAD.value
                    message.dead_letter_reason = "TTL过期"
                    self.stats["total_dead"] += 1
                    continue

                if message.status != MessageStatus.PENDING.value:
                    continue

                message.status = MessageStatus.PROCESSING.value
                message.processed_at = time.time()

                if consumer_id and consumer_id in self.consumers:
                    self.consumers[consumer_id].processing_count += 1
                    self.consumers[consumer_id].last_message_at = time.time()

                return message

        return None

    def _process_delayed_messages(self):
        """处理延迟消息"""
        now = time.time()
        ready = [m for m in self.delayed_messages if m.scheduled_at <= now]

        for message in ready:
            self.delayed_messages.remove(message)
            self._add_to_queue(message)

    def acknowledge(self, message_id: str, success: bool = True,
                    error: str = "") -> bool:
        """确认消息"""
        if message_id not in self.messages:
            return False

        message = self.messages[message_id]

        if success:
            message.status = MessageStatus.COMPLETED.value
            message.completed_at = time.time()
            self.stats["total_consumed"] += 1
        else:
            message.retry_count += 1
            message.error = error

            if message.retry_count >= message.max_retries:
                # 移入死信队列
                self._move_to_dead_letter(message)
            else:
                # 重新入队(带延迟)
                message.status = MessageStatus.PENDING.value
                queue = self.queues.get(message.queue_name)
                retry_delay = queue.retry_delay if queue else 5.0
                message.scheduled_at = time.time() + retry_delay * message.retry_count
                self.delayed_messages.append(message)

            self.stats["total_failed"] += 1

        self._save()
        return True

    def _move_to_dead_letter(self, message: Message):
        """移入死信队列"""
        queue = self.queues.get(message.queue_name)
        dlq_name = queue.dead_letter_queue if queue else f"{message.queue_name}_dlq"

        if dlq_name not in self.queues:
            self.create_queue(dlq_name)

        message.status = MessageStatus.DEAD.value
        message.dead_letter_reason = f"重试{message.retry_count}次后失败: {message.error}"
        message.queue_name = dlq_name

        self.stats["total_dead"] += 1

    def register_consumer(self, name: str, queue_name: str,
                          prefetch_count: int = 1) -> str:
        """注册消费者"""
        consumer_id = hashlib.md5(f"{name}_{queue_name}_{time.time()}".encode()).hexdigest()[:12]
        consumer = Consumer(
            consumer_id=consumer_id,
            name=name,
            queue_name=queue_name,
            prefetch_count=prefetch_count,
            is_active=True,
            created_at=time.time()
        )
        self.consumers[consumer_id] = consumer

        if queue_name in self.queues:
            self.queues[queue_name].consumer_count += 1

        self._save()
        return consumer_id

    def subscribe(self, queue_name: str, pattern: str = "",
                  callback_name: str = "") -> str:
        """订阅队列"""
        subscription_id = hashlib.md5(f"{queue_name}_{time.time()}".encode()).hexdigest()[:12]
        subscription = Subscription(
            subscription_id=subscription_id,
            queue_name=queue_name,
            pattern=pattern,
            callback_name=callback_name,
            is_active=True,
            created_at=time.time()
        )
        self.subscriptions[queue_name].append(subscription)
        self._save()
        return subscription_id

    def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """获取队列信息"""
        if queue_name not in self.queues:
            return {"error": "队列不存在"}

        queue = self.queues[queue_name]
        pending = sum(1 for m in self.messages.values()
                     if m.queue_name == queue_name and m.status == MessageStatus.PENDING.value)
        processing = sum(1 for m in self.messages.values()
                        if m.queue_name == queue_name and m.status == MessageStatus.PROCESSING.value)
        completed = sum(1 for m in self.messages.values()
                       if m.queue_name == queue_name and m.status == MessageStatus.COMPLETED.value)
        dead = sum(1 for m in self.messages.values()
                  if m.queue_name == queue_name and m.status == MessageStatus.DEAD.value)

        return {
            "queue_name": queue_name,
            "queue_type": queue.queue_type,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "dead": dead,
            "total": pending + processing + completed + dead,
            "consumer_count": queue.consumer_count,
            "is_active": queue.is_active
        }

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取消息详情"""
        if message_id not in self.messages:
            return None
        return asdict(self.messages[message_id])

    def peek_messages(self, queue_name: str, count: int = 10) -> List[Dict[str, Any]]:
        """预览消息(不消费)"""
        messages = [
            m for m in self.messages.values()
            if m.queue_name == queue_name and m.status == MessageStatus.PENDING.value
        ]
        messages.sort(key=lambda x: (-x.priority, x.created_at))
        return [asdict(m) for m in messages[:count]]

    def purge_queue(self, queue_name: str) -> int:
        """清空队列"""
        count = 0
        for message in list(self.messages.values()):
            if message.queue_name == queue_name and message.status == MessageStatus.PENDING.value:
                message.status = MessageStatus.DEAD.value
                message.dead_letter_reason = "队列清空"
                count += 1

        self.queue_messages[queue_name] = []
        self._save()
        return count

    def delete_queue(self, queue_name: str) -> bool:
        """删除队列"""
        if queue_name not in self.queues:
            return False

        # 删除队列中的消息
        for message in list(self.messages.values()):
            if message.queue_name == queue_name:
                del self.messages[message.message_id]

        del self.queues[queue_name]
        if queue_name in self.queue_messages:
            del self.queue_messages[queue_name]

        self._save()
        return True

    def get_dead_letter_messages(self, queue_name: str = "",
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """获取死信消息"""
        messages = [
            m for m in self.messages.values()
            if m.status == MessageStatus.DEAD.value
        ]

        if queue_name:
            dlq_name = f"{queue_name}_dlq"
            messages = [m for m in messages if m.queue_name == dlq_name]

        messages.sort(key=lambda x: x.created_at, reverse=True)
        return [asdict(m) for m in messages[:limit]]

    def retry_dead_message(self, message_id: str) -> bool:
        """重试死信消息"""
        if message_id not in self.messages:
            return False

        message = self.messages[message_id]
        if message.status != MessageStatus.DEAD.value:
            return False

        # 恢复到原始队列
        original_queue = message.queue_name.replace("_dlq", "")
        if original_queue in self.queues:
            message.queue_name = original_queue
            message.status = MessageStatus.PENDING.value
            message.retry_count = 0
            message.error = ""
            message.dead_letter_reason = ""
            message.created_at = time.time()
            self._add_to_queue(message)
            self._save()
            return True

        return False

    def get_consumer_stats(self) -> List[Dict[str, Any]]:
        """获取消费者统计"""
        stats = []
        for consumer in self.consumers.values():
            stats.append({
                "consumer_id": consumer.consumer_id,
                "name": consumer.name,
                "queue": consumer.queue_name,
                "is_active": consumer.is_active,
                "processing": consumer.processing_count,
                "processed": consumer.processed_count,
                "failed": consumer.failed_count
            })
        return stats

    def generate_report(self) -> Dict[str, Any]:
        """生成队列报告"""
        queue_stats = {}
        for queue_name in self.queues:
            queue_stats[queue_name] = self.get_queue_info(queue_name)

        return {
            "total_queues": len(self.queues),
            "total_messages": len(self.messages),
            "total_consumers": len(self.consumers),
            "total_subscriptions": sum(len(s) for s in self.subscriptions.values()),
            "stats": self.stats,
            "queue_stats": queue_stats,
            "pending_messages": sum(
                1 for m in self.messages.values()
                if m.status == MessageStatus.PENDING.value
            ),
            "dead_messages": sum(
                1 for m in self.messages.values()
                if m.status == MessageStatus.DEAD.value
            )
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "queues_count": len(self.queues),
            "messages_count": len(self.messages),
            "consumers_count": len(self.consumers),
            "subscriptions_count": sum(len(s) for s in self.subscriptions.values()),
            "total_produced": self.stats["total_produced"],
            "total_consumed": self.stats["total_consumed"],
            "total_failed": self.stats["total_failed"],
            "total_dead": self.stats["total_dead"]
        }


if __name__ == "__main__":
    engine = MessageQueueEngine()
    print("=== 消息队列系统测试 ===")

    # 创建队列
    q1 = engine.create_queue("tasks", "priority", max_size=1000)
    q2 = engine.create_queue("events", "fifo", max_size=5000)
    print(f"创建队列: {q1}, {q2}")

    # 生产消息
    for i in range(10):
        msg_id = engine.produce("tasks", f"任务 {i}", "text", priority=i % 4)
    print(f"生产了 10 条消息")

    # 高优先级消息
    engine.produce("tasks", "紧急任务", "text", priority=3)
    engine.produce("events", {"type": "user_login", "user": "test"}, "json")
    print("生产特殊消息")

    # 注册消费者
    c1 = engine.register_consumer("worker_1", "tasks")
    c2 = engine.register_consumer("worker_2", "tasks")
    print(f"注册消费者: {c1}, {c2}")

    # 消费消息(应该先消费高优先级)
    for i in range(5):
        msg = engine.consume("tasks", c1)
        if msg:
            print(f"消费消息: {msg.message_id}, 优先级={msg.priority}, 内容={msg.content[:30]}")
            engine.acknowledge(msg.message_id, True)

    # 模拟失败
    msg = engine.consume("tasks", c2)
    if msg:
        engine.acknowledge(msg.message_id, False, "处理失败")
        print(f"消息失败: {msg.message_id}")

    # 队列信息
    info = engine.get_queue_info("tasks")
    print(f"队列信息: {info}")

    # 预览消息
    peek = engine.peek_messages("tasks", 3)
    print(f"预览消息: {len(peek)} 条")

    # 报告
    report = engine.generate_report()
    print(f"\n队列报告: {json.dumps(report, indent=2, ensure_ascii=False)}")

    print("\n测试完成!")
