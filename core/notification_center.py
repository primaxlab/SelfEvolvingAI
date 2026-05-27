"""通知中心 - 多渠道通知(邮件/WebSocket/推送)"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


class Channel(Enum):
    EMAIL = "email"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    PUSH = "push"
    SMS = "sms"


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class Priority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Notification:
    notification_id: str
    title: str
    content: str
    channel: str = "console"
    priority: int = 1
    status: str = "pending"
    recipient: str = ""
    sender: str = "system"
    created_at: float = 0.0
    sent_at: float = 0.0
    read_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    retry_count: int = 0
    error: str = ""


@dataclass
class Subscription:
    subscription_id: str
    user_id: str
    channel: str = "console"
    topics: List[str] = field(default_factory=list)
    is_active: bool = True
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Template:
    template_id: str
    name: str
    title_template: str = ""
    content_template: str = ""
    channel: str = "console"
    variables: List[str] = field(default_factory=list)


class NotificationCenterEngine:
    """通知中心引擎"""

    def __init__(self, storage_dir: str = "data/notifications"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.notifications: List[Notification] = []
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self.templates: Dict[str, Template] = {}
        self.channel_handlers: Dict[str, Callable] = {}
        self.user_notifications: Dict[str, List[str]] = defaultdict(list)

        self._register_default_channels()
        self._load()

    def _register_default_channels(self):
        self.channel_handlers = {
            Channel.CONSOLE.value: self._send_console,
        }

    def _load(self):
        path = os.path.join(self.storage_dir, "notif_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.notifications = [Notification(**n) for n in data.get("notifications", [])]
                for k, v in data.get("subscriptions", {}).items():
                    self.subscriptions[k] = [Subscription(**s) for s in v]
                for k, v in data.get("templates", {}).items():
                    self.templates[k] = Template(**v)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        path = os.path.join(self.storage_dir, "notif_data.json")
        data = {
            "notifications": [asdict(n) for n in self.notifications[-5000:]],
            "subscriptions": {k: [asdict(s) for s in v] for k, v in self.subscriptions.items()},
            "templates": {k: asdict(v) for k, v in self.templates.items()},
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def send(self, title: str, content: str, channel: str = "console",
             recipient: str = "", priority: int = 1,
             tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """发送通知"""
        notif_id = hashlib.md5(f"{title}_{time.time()}".encode()).hexdigest()[:12]
        notification = Notification(
            notification_id=notif_id,
            title=title, content=content,
            channel=channel, priority=priority,
            recipient=recipient, tags=tags or [],
            metadata=metadata or {},
            created_at=time.time(),
        )

        # 尝试发送
        handler = self.channel_handlers.get(channel)
        if handler:
            try:
                success = handler(notification)
                if success:
                    notification.status = NotificationStatus.SENT.value
                    notification.sent_at = time.time()
                else:
                    notification.status = NotificationStatus.FAILED.value
            except Exception as e:
                notification.status = NotificationStatus.FAILED.value
                notification.error = str(e)
        else:
            notification.status = NotificationStatus.FAILED.value
            notification.error = f"未知渠道: {channel}"

        self.notifications.append(notification)
        if recipient:
            self.user_notifications[recipient].append(notif_id)

        self._save()
        return notif_id

    def _send_console(self, notification: Notification) -> bool:
        """控制台发送"""
        return True

    def broadcast(self, title: str, content: str, topic: str,
                  priority: int = 1) -> List[str]:
        """广播通知"""
        notif_ids = []
        for user_id, subs in self.subscriptions.items():
            for sub in subs:
                if sub.is_active and topic in sub.topics:
                    nid = self.send(title, content, sub.channel, user_id, priority)
                    notif_ids.append(nid)
        return notif_ids

    def subscribe(self, user_id: str, channel: str,
                  topics: List[str]) -> str:
        """订阅"""
        sub_id = hashlib.md5(f"{user_id}_{channel}_{time.time()}".encode()).hexdigest()[:12]
        subscription = Subscription(
            subscription_id=sub_id,
            user_id=user_id, channel=channel,
            topics=topics, is_active=True,
        )
        self.subscriptions[user_id].append(subscription)
        self._save()
        return sub_id

    def unsubscribe(self, user_id: str, subscription_id: str) -> bool:
        """取消订阅"""
        for sub in self.subscriptions.get(user_id, []):
            if sub.subscription_id == subscription_id:
                sub.is_active = False
                self._save()
                return True
        return False

    def register_channel(self, channel_name: str, handler: Callable):
        """注册通知渠道"""
        self.channel_handlers[channel_name] = handler

    def register_template(self, name: str, title_template: str,
                          content_template: str, channel: str = "console",
                          variables: List[str] = None) -> str:
        """注册模板"""
        template_id = hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        template = Template(
            template_id=template_id, name=name,
            title_template=title_template,
            content_template=content_template,
            channel=channel, variables=variables or [],
        )
        self.templates[template_id] = template
        self._save()
        return template_id

    def send_from_template(self, template_id: str, variables: Dict[str, str],
                           recipient: str = "", priority: int = 1) -> str:
        """使用模板发送"""
        if template_id not in self.templates:
            return ""
        template = self.templates[template_id]
        title = template.title_template
        content = template.content_template
        for key, value in variables.items():
            title = title.replace(f"{{{{{key}}}}}", str(value))
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return self.send(title, content, template.channel, recipient, priority)

    def mark_read(self, notification_id: str) -> bool:
        """标记已读"""
        for notif in self.notifications:
            if notif.notification_id == notification_id:
                notif.status = NotificationStatus.READ.value
                notif.read_at = time.time()
                self._save()
                return True
        return False

    def get_user_notifications(self, user_id: str, status: str = "",
                               limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户通知"""
        notif_ids = self.user_notifications.get(user_id, [])
        results = []
        for nid in reversed(notif_ids):
            for notif in self.notifications:
                if notif.notification_id == nid:
                    if status and notif.status != status:
                        continue
                    results.append(asdict(notif))
                    break
            if len(results) >= limit:
                break
        return results

    def get_unread_count(self, user_id: str) -> int:
        """获取未读数"""
        notif_ids = self.user_notifications.get(user_id, [])
        count = 0
        for nid in notif_ids:
            for notif in self.notifications:
                if notif.notification_id == nid and notif.status != NotificationStatus.READ.value:
                    count += 1
                    break
        return count

    def generate_report(self) -> Dict[str, Any]:
        """生成报告"""
        status_counts = defaultdict(int)
        channel_counts = defaultdict(int)
        for n in self.notifications:
            status_counts[n.status] += 1
            channel_counts[n.channel] += 1

        return {
            "total_notifications": len(self.notifications),
            "total_subscriptions": sum(len(v) for v in self.subscriptions.values()),
            "total_templates": len(self.templates),
            "status_distribution": dict(status_counts),
            "channel_distribution": dict(channel_counts),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "notifications_count": len(self.notifications),
            "subscriptions_count": sum(len(v) for v in self.subscriptions.values()),
            "templates_count": len(self.templates),
            "channels_count": len(self.channel_handlers),
        }


if __name__ == "__main__":
    print("=== 通知中心测试 ===")
    engine = NotificationCenterEngine()

    # 订阅
    s1 = engine.subscribe("user_1", "console", ["system", "marketing"])
    s2 = engine.subscribe("user_2", "console", ["system"])
    print(f"订阅: {s1}, {s2}")

    # 发送
    n1 = engine.send("系统通知", "欢迎使用系统！", recipient="user_1", tags=["welcome"])
    n2 = engine.send("紧急通知", "服务器异常！", priority=3, recipient="user_1")
    print(f"通知: {n1}, {n2}")

    # 广播
    broadcast_ids = engine.broadcast("公告", "系统升级通知", "system")
    print(f"广播: {len(broadcast_ids)} 条")

    # 模板
    tid = engine.register_template("欢迎邮件", "欢迎 {{name}}!", "亲爱的 {{name}}，欢迎加入我们的平台！")
    n3 = engine.send_from_template(tid, {"name": "张三"}, recipient="user_1")
    print(f"模板通知: {n3}")

    # 未读数
    unread = engine.get_unread_count("user_1")
    print(f"未读通知: {unread}")

    # 用户通知
    user_notifs = engine.get_user_notifications("user_1")
    print(f"用户通知: {len(user_notifs)} 条")

    report = engine.generate_report()
    print(f"\n通知报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    print("测试完成!")
