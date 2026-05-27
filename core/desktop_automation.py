"""
桌面自动化 - 鼠标/键盘控制、屏幕截图、GUI操作

依赖: pip install pyautogui pillow (可选)
无依赖时使用标准库降级方案
"""

import json
import os
import time
import hashlib
import subprocess
import platform
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class ActionType(Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    MOVE = "move"
    DRAG = "drag"
    SCREENSHOT = "screenshot"


@dataclass
class Action:
    action_id: str
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    success: bool = True
    screenshot_before: str = ""
    screenshot_after: str = ""
    error: str = ""


@dataclass
class ScreenInfo:
    width: int = 0
    height: int = 0
    mouse_x: int = 0
    mouse_y: int = 0


class DesktopAutomationEngine:
    """桌面自动化引擎"""

    def __init__(self, storage_dir: str = "data/desktop"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "screenshots"), exist_ok=True)

        self.actions: List[Action] = []
        self.pyautogui = None
        self._try_import()

    def _try_import(self):
        """尝试导入pyautogui"""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True  # 鼠标移到左上角触发安全停止
            pyautogui.PAUSE = 0.1
            self.pyautogui = pyautogui
        except ImportError:
            pass

    def get_screen_info(self) -> ScreenInfo:
        """获取屏幕信息"""
        if self.pyautogui:
            size = self.pyautogui.size()
            pos = self.pyautogui.position()
            return ScreenInfo(width=size.width, height=size.height,
                            mouse_x=pos.x, mouse_y=pos.y)
        # 降级方案
        system = platform.system()
        if system == "Windows":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                return ScreenInfo(
                    width=user32.GetSystemMetrics(0),
                    height=user32.GetSystemMetrics(1),
                )
            except Exception:
                pass
        return ScreenInfo(width=1920, height=1080)

    def screenshot(self, region: Tuple[int, int, int, int] = None,
                   save: bool = True) -> str:
        """截图"""
        if not self.pyautogui:
            return ""

        timestamp = int(time.time() * 1000)
        path = os.path.join(self.storage_dir, "screenshots", f"shot_{timestamp}.png")

        try:
            if region:
                img = self.pyautogui.screenshot(region=region)
            else:
                img = self.pyautogui.screenshot()
            img.save(path)
            return path
        except Exception as e:
            return ""

    def click(self, x: int, y: int, button: str = "left",
              clicks: int = 1) -> bool:
        """点击"""
        action = self._log_action("click", {"x": x, "y": y, "button": button})

        if self.pyautogui:
            try:
                self.pyautogui.click(x, y, clicks=clicks, button=button)
                return True
            except Exception as e:
                action.error = str(e)
                action.success = False
                return False

        # 降级: 使用系统命令
        return self._system_click(x, y)

    def _system_click(self, x: int, y: int) -> bool:
        """系统级点击(降级方案)"""
        system = platform.system()
        try:
            if system == "Windows":
                # 使用PowerShell
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x},{y})
                [System.Windows.Forms.SendKeys]::SendWait(" ")
                '''
                subprocess.run(["powershell", "-Command", script],
                             capture_output=True, timeout=5)
                return True
        except Exception:
            pass
        return False

    def double_click(self, x: int, y: int) -> bool:
        """双击"""
        return self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int) -> bool:
        """右键点击"""
        return self.click(x, y, button="right")

    def type_text(self, text: str, interval: float = 0.02) -> bool:
        """输入文字"""
        action = self._log_action("type", {"text": text[:50]})

        if self.pyautogui:
            try:
                self.pyautogui.typewrite(text, interval=interval) if text.isascii() else \
                    self.pyautogui.write(text)
                return True
            except Exception as e:
                action.error = str(e)
                action.success = False

        # 降级: 剪贴板
        return self._clipboard_paste(text)

    def _clipboard_paste(self, text: str) -> bool:
        """通过剪贴板粘贴"""
        system = platform.system()
        try:
            if system == "Windows":
                import subprocess
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-16le'))
                time.sleep(0.1)
                self.hotkey('ctrl', 'v')
                return True
            elif system in ["Darwin", "Linux"]:
                import subprocess
                process = subprocess.Popen(['pbcopy'] if system == "Darwin" else ['xclip'],
                                         stdin=subprocess.PIPE)
                process.communicate(text.encode())
                time.sleep(0.1)
                self.hotkey('ctrl' if system == "Linux" else 'command', 'v')
                return True
        except Exception:
            pass
        return False

    def hotkey(self, *keys) -> bool:
        """快捷键"""
        action = self._log_action("hotkey", {"keys": list(keys)})

        if self.pyautogui:
            try:
                self.pyautogui.hotkey(*keys)
                return True
            except Exception as e:
                action.error = str(e)
                action.success = False

        # 降级
        system = platform.system()
        try:
            if system == "Windows":
                import subprocess
                key_map = {
                    'ctrl': '^', 'alt': '%', 'shift': '+',
                    'enter': '{ENTER}', 'tab': '{TAB}',
                    'esc': '{ESC}', 'delete': '{DELETE}',
                }
                keys_str = ""
                for k in keys:
                    keys_str += key_map.get(k.lower(), k)
                subprocess.run(["powershell", "-Command",
                              f"Add-Type -AssemblyName System.Windows.Forms; "
                              f"[System.Windows.Forms.SendKeys]::SendWait('{keys_str}')"],
                             capture_output=True, timeout=5)
                return True
        except Exception:
            pass
        return False

    def scroll(self, amount: int, x: int = None, y: int = None) -> bool:
        """滚动"""
        if self.pyautogui:
            try:
                if x is not None and y is not None:
                    self.pyautogui.scroll(amount, x, y)
                else:
                    self.pyautogui.scroll(amount)
                return True
            except Exception:
                pass
        return False

    def move(self, x: int, y: int, duration: float = 0.2) -> bool:
        """移动鼠标"""
        if self.pyautogui:
            try:
                self.pyautogui.moveTo(x, y, duration=duration)
                return True
            except Exception:
                pass
        return False

    def drag(self, start_x: int, start_y: int,
             end_x: int, end_y: int, duration: float = 0.5) -> bool:
        """拖拽"""
        if self.pyautogui:
            try:
                self.pyautogui.moveTo(start_x, start_y)
                self.pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
                return True
            except Exception:
                pass
        return False

    def find_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """在屏幕上查找图像"""
        if self.pyautogui:
            try:
                location = self.pyautogui.locateOnScreen(image_path, confidence=confidence)
                if location:
                    center = self.pyautogui.center(location)
                    return (center.x, center.y)
            except Exception:
                pass
        return None

    def get_pixel_color(self, x: int, y: int) -> Optional[Tuple[int, int, int]]:
        """获取像素颜色"""
        if self.pyautogui:
            try:
                return self.pyautogui.pixel(x, y)
            except Exception:
                pass
        return None

    def _log_action(self, action_type: str, params: dict) -> Action:
        """记录操作"""
        action = Action(
            action_id=hashlib.md5(f"{action_type}_{time.time()}".encode()).hexdigest()[:12],
            action_type=action_type,
            params=params,
            timestamp=time.time(),
        )
        self.actions.append(action)
        return action

    def get_action_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取操作历史"""
        return [asdict(a) for a in self.actions[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "actions_count": len(self.actions),
            "pyautogui_available": self.pyautogui is not None,
            "system": platform.system(),
        }


if __name__ == "__main__":
    print("=== 桌面自动化测试 ===")
    engine = DesktopAutomationEngine()

    info = engine.get_screen_info()
    print(f"屏幕: {info.width}x{info.height}")
    print(f"pyautogui: {'可用' if engine.pyautogui else '不可用(降级模式)'}")

    # 截图
    path = engine.screenshot()
    print(f"截图: {path}")

    # 移动鼠标(安全)
    print(f"移动鼠标到中心: {engine.move(info.width//2, info.height//2)}")

    print("测试完成!")
