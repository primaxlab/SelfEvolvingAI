"""
进程管理 - 启动/停止/监控应用程序

纯标准库实现，零依赖
"""

import json
import os
import time
import hashlib
import subprocess
import signal
import platform
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Any


class ProcessStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    ZOMBIE = "zombie"


@dataclass
class ProcessInfo:
    pid: int
    name: str
    command: str = ""
    status: str = "running"
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    started_at: float = 0.0
    user: str = ""


@dataclass
class ProcessLog:
    log_id: str
    command: str
    pid: int = 0
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    timestamp: float = 0.0


class ProcessManagerEngine:
    """进程管理引擎"""

    def __init__(self, storage_dir: str = "data/process"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.managed_processes: Dict[str, subprocess.Popen] = {}
        self.process_logs: List[ProcessLog] = []
        self.system = platform.system()

    def execute(self, command: str, shell: bool = True,
                timeout: int = 30, cwd: str = None,
                capture: bool = True) -> Dict[str, Any]:
        """执行命令"""
        start_time = time.time()
        log_id = hashlib.md5(f"{command}_{time.time()}".encode()).hexdigest()[:12]

        try:
            result = subprocess.run(
                command, shell=shell, capture_output=capture,
                text=True, timeout=timeout, cwd=cwd,
            )

            log = ProcessLog(
                log_id=log_id, command=command,
                pid=result.pid, returncode=result.returncode,
                stdout=result.stdout[:5000] if result.stdout else "",
                stderr=result.stderr[:5000] if result.stderr else "",
                duration=time.time() - start_time,
                timestamp=time.time(),
            )
            self.process_logs.append(log)

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout[:2000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else "",
                "duration": log.duration,
                "log_id": log_id,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令超时", "duration": timeout}
        except Exception as e:
            return {"success": False, "error": str(e), "duration": time.time() - start_time}

    def execute_background(self, command: str, name: str = "",
                           shell: bool = True, cwd: str = None) -> str:
        """后台执行"""
        try:
            process = subprocess.Popen(
                command, shell=shell, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=cwd,
            )
            proc_name = name or command[:50]
            self.managed_processes[proc_name] = process
            return proc_name
        except Exception as e:
            return ""

    def stop_background(self, name: str) -> bool:
        """停止后台进程"""
        if name in self.managed_processes:
            process = self.managed_processes[name]
            try:
                if self.system == "Windows":
                    process.terminate()
                else:
                    process.send_signal(signal.SIGTERM)
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                del self.managed_processes[name]
                return True
            except Exception:
                pass
        return False

    def get_process_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取进程状态"""
        if name in self.managed_processes:
            process = self.managed_processes[name]
            return {
                "name": name,
                "pid": process.pid,
                "running": process.poll() is None,
                "returncode": process.returncode,
            }
        return None

    def list_processes(self) -> List[Dict[str, Any]]:
        """列出系统进程"""
        try:
            if self.system == "Windows":
                result = self.execute("tasklist /FO CSV /NH", timeout=10)
                processes = []
                for line in result.get("stdout", "").strip().split("\n")[:50]:
                    parts = line.strip().strip('"').split('","')
                    if len(parts) >= 5:
                        processes.append({
                            "name": parts[0],
                            "pid": int(parts[1]),
                            "memory": parts[4],
                        })
                return processes
            else:
                result = self.execute("ps aux --sort=-%mem | head -20", timeout=10)
                processes = []
                for line in result.get("stdout", "").strip().split("\n")[1:20]:
                    parts = line.split()
                    if len(parts) >= 11:
                        processes.append({
                            "name": parts[10],
                            "pid": int(parts[1]),
                            "cpu": parts[2],
                            "memory": parts[3],
                        })
                return processes
        except Exception:
            return []

    def find_process(self, name: str) -> List[Dict[str, Any]]:
        """查找进程"""
        try:
            if self.system == "Windows":
                result = self.execute(f'tasklist /FI "IMAGENAME eq {name}" /FO CSV', timeout=10)
            else:
                result = self.execute(f"pgrep -a {name}", timeout=10)
            return [{"raw": result.get("stdout", "")}]
        except Exception:
            return []

    def kill_process(self, pid: int) -> bool:
        """杀死进程"""
        try:
            if self.system == "Windows":
                self.execute(f"taskkill /PID {pid} /F", timeout=10)
            else:
                os.kill(pid, signal.SIGKILL)
            return True
        except Exception:
            return False

    def open_application(self, app_name: str) -> bool:
        """打开应用"""
        try:
            if self.system == "Windows":
                # 常见Windows应用
                apps = {
                    "notepad": "notepad.exe",
                    "calculator": "calc.exe",
                    "explorer": "explorer.exe",
                    "cmd": "cmd.exe",
                    "powershell": "powershell.exe",
                    "browser": "start msedge",
                    "chrome": "start chrome",
                }
                cmd = apps.get(app_name.lower(), f"start {app_name}")
                self.execute_background(cmd)
            elif self.system == "Darwin":
                self.execute_background(f"open -a {app_name}")
            else:
                self.execute_background(app_name)
            return True
        except Exception:
            return False

    def get_clipboard(self) -> str:
        """获取剪贴板内容"""
        try:
            if self.system == "Windows":
                result = self.execute("powershell Get-Clipboard", timeout=5)
                return result.get("stdout", "").strip()
            elif self.system == "Darwin":
                result = self.execute("pbpaste", timeout=5)
                return result.get("stdout", "").strip()
            else:
                result = self.execute("xclip -selection clipboard -o", timeout=5)
                return result.get("stdout", "").strip()
        except Exception:
            return ""

    def set_clipboard(self, text: str) -> bool:
        """设置剪贴板内容"""
        try:
            if self.system == "Windows":
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-16le'))
                return True
            elif self.system == "Darwin":
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(text.encode())
                return True
            else:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'],
                                         stdin=subprocess.PIPE)
                process.communicate(text.encode())
                return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "managed_processes": len(self.managed_processes),
            "process_logs": len(self.process_logs),
            "system": self.system,
        }


if __name__ == "__main__":
    print("=== 进程管理测试 ===")
    engine = ProcessManagerEngine()

    # 执行命令
    result = engine.execute("echo Hello World")
    print(f"执行: {result}")

    # 系统信息
    if engine.system == "Windows":
        result = engine.execute("systeminfo | findstr /B /C:\"OS Name\" /C:\"Total Physical Memory\"")
    else:
        result = engine.execute("uname -a")
    print(f"系统: {result.get('stdout', '')[:200]}")

    # 列出进程
    processes = engine.list_processes()
    print(f"\n进程数: {len(processes)}")
    for p in processes[:5]:
        print(f"  {p}")

    # 剪贴板
    engine.set_clipboard("测试剪贴板")
    print(f"\n剪贴板: {engine.get_clipboard()}")

    print(f"\n统计: {engine.get_stats()}")
    print("测试完成!")
