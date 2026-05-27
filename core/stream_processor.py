"""流式处理 - 流式数据、窗口聚合、事件驱动"""

import json
import os
import time
import hashlib
import threading
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque


class WindowType(Enum):
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"


class EventType(Enum):
    DATA = "data"
    CONTROL = "control"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class StreamEvent:
    event_id: str
    stream_name: str
    event_type: str = "data"
    payload: Any = None
    timestamp: float = 0.0
    partition_key: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Window:
    window_id: str
    window_type: str = "tumbling"
    size_seconds: float = 60
    slide_seconds: float = 60
    start_time: float = 0.0
    end_time: float = 0.0
    events: List[StreamEvent] = field(default_factory=list)
    aggregated: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Stream:
    stream_id: str
    name: str
    created_at: float = 0.0
    event_count: int = 0
    consumers: List[str] = field(default_factory=list)
    is_active: bool = True


class StreamProcessorEngine:
    """流式处理引擎"""

    def __init__(self, storage_dir: str = "data/stream"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.streams: Dict[str, Stream] = {}
        self.event_buffers: Dict[str, deque] = {}
        self.windows: Dict[str, List[Window]] = defaultdict(list)
        self.processors: Dict[str, Callable] = {}
        self.consumers: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        self.stats = {"total_events": 0, "processed": 0, "errors": 0}

        self._lock = threading.Lock()

    def create_stream(self, name: str, buffer_size: int = 10000) -> str:
        """创建流"""
        stream_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        stream = Stream(
            stream_id=stream_id, name=name,
            created_at=time.time(),
        )
        self.streams[stream_id] = stream
        self.event_buffers[stream_id] = deque(maxlen=buffer_size)
        return stream_id

    def emit(self, stream_name: str, payload: Any,
             event_type: str = "data",
             partition_key: str = "",
             metadata: Dict[str, Any] = None) -> str:
        """发送事件"""
        # 查找或创建流
        stream = None
        for s in self.streams.values():
            if s.name == stream_name:
                stream = s
                break

        if not stream:
            stream_id = self.create_stream(stream_name)
            stream = self.streams[stream_id]

        event_id = hashlib.md5(f"{stream_name}_{time.time()}".encode()).hexdigest()[:12]
        event = StreamEvent(
            event_id=event_id,
            stream_name=stream_name,
            event_type=event_type,
            payload=payload,
            timestamp=time.time(),
            partition_key=partition_key,
            metadata=metadata or {},
        )

        with self._lock:
            self.event_buffers[stream.stream_id].append(event)
            stream.event_count += 1
            self.stats["total_events"] += 1

        # 触发处理器
        self._process_event(stream, event)

        return event_id

    def _process_event(self, stream: Stream, event: StreamEvent):
        """处理事件"""
        # 通用处理器
        for name, processor in self.processors.items():
            try:
                processor(event)
                self.stats["processed"] += 1
            except Exception as e:
                self.stats["errors"] += 1

        # 消费者
        for consumer_name, callback in self.consumers.get(stream.stream_id, {}).items():
            try:
                callback(event)
            except Exception:
                pass

        # 窗口聚合
        self._add_to_windows(stream.stream_id, event)

    def _add_to_windows(self, stream_id: str, event: StreamEvent):
        """添加到窗口"""
        now = event.timestamp

        for window in self.windows.get(stream_id, []):
            if window.start_time <= now < window.end_time:
                window.events.append(event)

    def register_processor(self, name: str, processor: Callable):
        """注册处理器"""
        self.processors[name] = processor

    def register_consumer(self, stream_id: str, name: str, callback: Callable):
        """注册消费者"""
        self.consumers[stream_id][name] = callback

    def create_window(self, stream_id: str, window_type: str = "tumbling",
                      size_seconds: float = 60, slide_seconds: float = 60) -> str:
        """创建窗口"""
        now = time.time()
        window_id = hashlib.md5(f"{stream_id}_{window_type}_{now}".encode()).hexdigest()[:12]
        window = Window(
            window_id=window_id,
            window_type=window_type,
            size_seconds=size_seconds,
            slide_seconds=slide_seconds,
            start_time=now,
            end_time=now + size_seconds,
        )
        self.windows[stream_id].append(window)
        return window_id

    def get_window_events(self, stream_id: str, window_id: str) -> List[Dict[str, Any]]:
        """获取窗口事件"""
        for window in self.windows.get(stream_id, []):
            if window.window_id == window_id:
                return [asdict(e) for e in window.events]
        return []

    def aggregate_window(self, stream_id: str, window_id: str,
                         agg_func: Callable = None) -> Dict[str, Any]:
        """窗口聚合"""
        for window in self.windows.get(stream_id, []):
            if window.window_id == window_id:
                if agg_func:
                    result = agg_func(window.events)
                    window.aggregated = result
                    return result
                else:
                    return {
                        "count": len(window.events),
                        "start": window.start_time,
                        "end": window.end_time,
                    }
        return {}

    def get_recent_events(self, stream_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近事件"""
        buffer = self.event_buffers.get(stream_id, deque())
        events = list(buffer)[-count:]
        return [asdict(e) for e in events]

    def get_stream_info(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """获取流信息"""
        if stream_id in self.streams:
            stream = self.streams[stream_id]
            return {
                "stream_id": stream.stream_id,
                "name": stream.name,
                "event_count": stream.event_count,
                "buffer_size": len(self.event_buffers.get(stream_id, [])),
                "is_active": stream.is_active,
            }
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "streams_count": len(self.streams),
            "total_events": self.stats["total_events"],
            "processed": self.stats["processed"],
            "errors": self.stats["errors"],
        }

    def generate_report(self) -> Dict[str, Any]:
        return {
            "total_streams": len(self.streams),
            "stats": self.stats,
            "processors": len(self.processors),
        }


if __name__ == "__main__":
    print("=== 流式处理测试 ===")
    engine = StreamProcessorEngine()

    # 创建流
    sid = engine.create_stream("sensor_data")
    print(f"流: {sid}")

    # 注册处理器
    processed_events = []
    engine.register_processor("logger", lambda e: processed_events.append(e.event_id))

    # 发送事件
    for i in range(10):
        engine.emit("sensor_data", {"temperature": 20 + i * 0.5, "humidity": 60 + i})
    print(f"发送 10 个事件")

    # 创建窗口
    wid = engine.create_window(sid, "tumbling", 60)
    print(f"窗口: {wid}")

    # 最近事件
    recent = engine.get_recent_events(sid, 5)
    print(f"最近事件: {len(recent)} 个")

    # 流信息
    info = engine.get_stream_info(sid)
    print(f"流信息: {info}")

    report = engine.generate_report()
    print(f"\n流式报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
