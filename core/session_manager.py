"""会话管理 - 会话创建/恢复、状态持久化、超时管理"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict


class SessionStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    CLOSED = "closed"


@dataclass
class Session:
    session_id: str
    user_id: str = ""
    status: str = "active"
    created_at: float = 0.0
    last_active: float = 0.0
    expires_at: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    interaction_count: int = 0


@dataclass
class SessionConfig:
    default_timeout: float = 3600  # 1小时
    max_history: int = 100
    max_sessions_per_user: int = 10


class SessionManagerEngine:
    """会话管理引擎"""

    def __init__(self, storage_dir: str = "data/sessions"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.sessions: Dict[str, Session] = {}
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)
        self.config = SessionConfig()
        self._load()

    def _load(self):
        path = os.path.join(self.storage_dir, "session_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.get("sessions", {}).items():
                    self.sessions[k] = Session(**v)
                self.user_sessions = defaultdict(list, data.get("user_sessions", {}))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "session_data.json")
        data = {
            "sessions": {k: asdict(v) for k, v in self.sessions.items()},
            "user_sessions": dict(self.user_sessions),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_session(self, user_id: str = "", timeout: float = 0,
                       metadata: Dict[str, Any] = None) -> str:
        """创建会话"""
        session_id = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16]
        now = time.time()
        timeout = timeout or self.config.default_timeout

        # 限制每用户会话数
        if user_id:
            user_sids = self.user_sessions[user_id]
            active = [s for s in user_sids if s in self.sessions and self.sessions[s].status == "active"]
            while len(active) >= self.config.max_sessions_per_user:
                oldest = active.pop(0)
                self.close_session(oldest)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            status=SessionStatus.ACTIVE.value,
            created_at=now,
            last_active=now,
            expires_at=now + timeout,
            metadata=metadata or {},
        )
        self.sessions[session_id] = session
        if user_id:
            self.user_sessions[user_id].append(session_id)
        self._save()
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        if session_id not in self.sessions:
            return None
        session = self.sessions[session_id]
        if session.status == SessionStatus.EXPIRED.value:
            return None
        if session.expires_at > 0 and time.time() > session.expires_at:
            session.status = SessionStatus.EXPIRED.value
            self._save()
            return None
        session.last_active = time.time()
        return asdict(session)

    def update_session(self, session_id: str, data: Dict[str, Any] = None,
                       history_entry: Dict[str, Any] = None) -> bool:
        """更新会话"""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        if session.status not in [SessionStatus.ACTIVE.value, SessionStatus.IDLE.value]:
            return False
        if data:
            session.data.update(data)
        if history_entry:
            session.history.append(history_entry)
            if len(session.history) > self.config.max_history:
                session.history = session.history[-self.config.max_history:]
        session.interaction_count += 1
        session.last_active = time.time()
        self._save()
        return True

    def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """设置会话数据"""
        if session_id not in self.sessions:
            return False
        self.sessions[session_id].data[key] = value
        self.sessions[session_id].last_active = time.time()
        self._save()
        return True

    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """获取会话数据"""
        session = self.sessions.get(session_id)
        if not session or session.status == SessionStatus.EXPIRED.value:
            return default
        return session.data.get(key, default)

    def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        if session_id in self.sessions:
            self.sessions[session_id].status = SessionStatus.CLOSED.value
            self._save()
            return True
        return False

    def extend_session(self, session_id: str, additional_time: float = 3600) -> bool:
        """延长会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.expires_at = max(session.expires_at, time.time()) + additional_time
            session.status = SessionStatus.ACTIVE.value
            self._save()
            return True
        return False

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有会话"""
        session_ids = self.user_sessions.get(user_id, [])
        sessions = []
        for sid in session_ids:
            if sid in self.sessions:
                sessions.append(asdict(self.sessions[sid]))
        return sessions

    def cleanup_expired(self) -> int:
        """清理过期会话"""
        now = time.time()
        expired = []
        for sid, session in self.sessions.items():
            if session.status == SessionStatus.ACTIVE.value and session.expires_at > 0 and now > session.expires_at:
                session.status = SessionStatus.EXPIRED.value
                expired.append(sid)
        self._save()
        return len(expired)

    def get_active_count(self) -> int:
        """获取活跃会话数"""
        return sum(1 for s in self.sessions.values()
                   if s.status == SessionStatus.ACTIVE.value)

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        status_counts = defaultdict(int)
        for s in self.sessions.values():
            status_counts[s.status] += 1

        return {
            "total_sessions": len(self.sessions),
            "active_sessions": self.get_active_count(),
            "unique_users": len(self.user_sessions),
            "status_distribution": dict(status_counts),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self.sessions),
            "active_count": self.get_active_count(),
            "users_count": len(self.user_sessions),
        }


if __name__ == "__main__":
    print("=== 会话管理测试 ===")
    engine = SessionManagerEngine()

    # 创建会话
    s1 = engine.create_session("user_1", metadata={"device": "mobile"})
    s2 = engine.create_session("user_2")
    print(f"会话: {s1}, {s2}")

    # 更新会话
    engine.update_session(s1, data={"theme": "dark"}, history_entry={"action": "login"})
    engine.set_session_data(s1, "language", "zh-CN")

    # 获取
    session = engine.get_session(s1)
    print(f"会话数据: {session['data']}")
    print(f"语言: {engine.get_session_data(s1, 'language')}")

    # 用户会话
    user_sessions = engine.get_user_sessions("user_1")
    print(f"用户会话: {len(user_sessions)}")

    # 报告
    report = engine.generate_report()
    print(f"\n会话报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
