"""任务调度器 - 使用子进程执行任务

核心特性：
- subprocess.Popen 启动独立工作进程
- 后台线程读取管道，捕获stdout/stderr
- 维护日志缓冲区 (collections.deque)
- 提供 get_logs() API 供CLI查看

设计理念：
- CLI是"任务管理器"，只负责UI交互
- 实际工作由独立子进程完成
- 日志通过管道自动捕获，完全隔离业务print和聊天界面

类比：类似docker、kubectl的模式
"""

import sys
import subprocess
import threading
import json
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from workflow.task_manager import get_task_manager, TaskStatus


class TaskScheduler:
    """任务调度器 - 管理子进程和日志缓冲区"""

    def __init__(self):
        """初始化调度器"""
        self.tasks_dir = Path("logs/generation_tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # 子进程管理
        self.processes: Dict[str, subprocess.Popen] = {}

        # 日志缓冲区 (每个任务一个deque，最多保留1000行)
        self.log_buffers: Dict[str, deque] = {}

        # 日志读取线程
        self.log_threads: Dict[str, threading.Thread] = {}

    def submit_task(
        self,
        session_id: str,
        history: List[Dict]
    ) -> str:
        """提交任务（启动子进程）

        Args:
            session_id: 会话ID
            history: 对话历史

        Returns:
            task_id

        Examples:
            >>> scheduler = TaskScheduler()
            >>> task_id = scheduler.submit_task(
            ...     session_id="cli_session",
            ...     history=[{"role": "user", "content": "我想合成阿司匹林"}]
            ... )
            >>> print(f"Task {task_id} submitted")
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]

        # 创建任务目录
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(exist_ok=True)

        # 保存任务配置到JSON（供工作进程读取）
        config_file = task_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": task_id,
                "session_id": session_id,
                "history": history,
                "created_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        # 启动子进程
        # 使用 python -m workflow.task_worker <task_id> 启动
        process = subprocess.Popen(
            [sys.executable, "-m", "workflow.task_worker", task_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并stderr到stdout
            text=True,
            bufsize=1,  # 行缓冲
            cwd=Path.cwd()  # 确保工作目录正确
        )

        self.processes[task_id] = process

        # 启动日志读取线程
        log_buffer = deque(maxlen=1000)  # 最多保留1000行
        self.log_buffers[task_id] = log_buffer

        log_thread = threading.Thread(
            target=self._read_process_output,
            args=(task_id, process, log_buffer),
            daemon=True,  # 守护线程，CLI退出时自动结束
            name=f"LogReader-{task_id}"
        )
        log_thread.start()
        self.log_threads[task_id] = log_thread

        return task_id

    def resume_task(self, task_id: str) -> bool:
        """恢复已中断的任务（重新启动子进程，resume模式）

        Args:
            task_id: 任务ID

        Returns:
            是否成功启动

        Notes:
            - 只支持恢复AWAITING_CONFIRM或其他中间状态的任务
            - 启动时传递 --resume 参数，工作进程会跳过已完成的步骤
        """
        # 检查任务是否存在
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)

        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return False

        # 检查任务状态
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            print(f"❌ 任务已结束（{task.status.value}），无法恢复")
            return False

        # 检查是否已有进程在运行
        if task_id in self.processes:
            proc = self.processes[task_id]
            if proc.poll() is None:  # 进程仍在运行
                print(f"⚠️  任务 {task_id} 已有子进程在运行")
                return False

        # 启动子进程（resume模式）
        process = subprocess.Popen(
            [sys.executable, "-m", "workflow.task_worker", task_id, "--resume"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=Path.cwd()
        )

        self.processes[task_id] = process

        # 如果日志缓冲区不存在，创建新的
        if task_id not in self.log_buffers:
            self.log_buffers[task_id] = deque(maxlen=1000)

        log_buffer = self.log_buffers[task_id]

        # 启动日志读取线程
        log_thread = threading.Thread(
            target=self._read_process_output,
            args=(task_id, process, log_buffer),
            daemon=True,
            name=f"LogReader-{task_id}-Resume"
        )
        log_thread.start()
        self.log_threads[task_id] = log_thread

        return True

    def _read_process_output(
        self,
        task_id: str,
        process: subprocess.Popen,
        log_buffer: deque
    ):
        """后台线程：读取子进程输出，写入日志文件和缓冲区

        Args:
            task_id: 任务ID
            process: 子进程对象
            log_buffer: 日志缓冲区

        Notes:
            - 此方法在后台线程中运行
            - 同时写入日志文件（持久化）和内存缓冲区（供/logs查看）
            - 进程退出后自动记录退出码
        """
        log_file = self.tasks_dir / task_id / "task.log"

        try:
            with open(log_file, 'a', encoding='utf-8') as f:  # append模式，支持resume
                for line in process.stdout:
                    line_stripped = line.rstrip()

                    # 智能时间戳：如果行已有时间戳（来自LogWriter），不重复添加
                    if line_stripped.startswith('[') and ']:' in line_stripped[:12]:
                        # 已有时间戳格式：[HH:MM:SS] 或 [HH:MM:SS.mmm]
                        log_line = line_stripped
                    else:
                        # 无时间戳（来自直接print），添加时间戳
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        log_line = f"[{timestamp}] {line_stripped}"

                    # 写入日志文件（持久化）
                    f.write(log_line + "\n")
                    f.flush()

                    # 加入缓冲区（供/logs命令查看）
                    log_buffer.append(log_line)

        except Exception as e:
            error_msg = f"[Scheduler] 日志读取异常: {e}"
            log_buffer.append(error_msg)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(error_msg + "\n")

        finally:
            # 等待子进程结束
            process.wait()

            # 记录退出码
            exit_code = process.returncode
            timestamp = datetime.now().strftime("%H:%M:%S")

            if exit_code == 0:
                final_msg = f"[{timestamp}] [Scheduler] 子进程正常退出"
            else:
                final_msg = f"[{timestamp}] [Scheduler] 子进程异常退出 (exit code: {exit_code})"

            log_buffer.append(final_msg)

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(final_msg + "\n")

    def get_logs(self, task_id: str, tail: int = 50) -> List[str]:
        """获取任务日志（最近N行）

        Args:
            task_id: 任务ID
            tail: 返回最后N行（类似tail -n）

        Returns:
            日志行列表

        Examples:
            >>> logs = scheduler.get_logs("abc123", tail=20)
            >>> for log in logs:
            ...     print(log)
        """
        if task_id not in self.log_buffers:
            return [f"❌ 任务 {task_id} 不存在或未启动"]

        log_buffer = self.log_buffers[task_id]

        # 返回最后N行
        if tail <= 0:
            return list(log_buffer)
        else:
            return list(log_buffer)[-tail:]

    def get_process_status(self, task_id: str) -> str:
        """获取子进程状态

        Args:
            task_id: 任务ID

        Returns:
            "running" | "completed" | "failed" | "not_found"

        Examples:
            >>> status = scheduler.get_process_status("abc123")
            >>> print(f"Process status: {status}")
        """
        if task_id not in self.processes:
            return "not_found"

        process = self.processes[task_id]

        if process.poll() is None:
            return "running"
        else:
            # 进程已退出
            exit_code = process.returncode
            return "completed" if exit_code == 0 else "failed"

    def get_all_process_info(self) -> Dict[str, Dict]:
        """获取所有子进程信息

        Returns:
            进程信息字典，格式：
            {
                "task_id": {
                    "status": "running" | "completed" | "failed",
                    "exit_code": int | None,
                    "log_lines": int
                }
            }

        Notes:
            供/tasks命令使用，显示所有任务的子进程状态
        """
        info = {}

        for task_id, process in self.processes.items():
            poll_result = process.poll()

            info[task_id] = {
                "status": "running" if poll_result is None else (
                    "completed" if process.returncode == 0 else "failed"
                ),
                "exit_code": process.returncode,
                "log_lines": len(self.log_buffers.get(task_id, []))
            }

        return info

    def terminate_task(self, task_id: str) -> bool:
        """终止任务子进程

        Args:
            task_id: 任务ID

        Returns:
            是否成功终止

        Notes:
            - 先尝试SIGTERM（优雅退出）
            - 如果5秒后仍未退出，强制SIGKILL
        """
        if task_id not in self.processes:
            print(f"❌ 任务 {task_id} 不存在")
            return False

        process = self.processes[task_id]

        if process.poll() is not None:
            print(f"⚠️  任务 {task_id} 子进程已退出")
            return False

        # 发送SIGTERM
        print(f"[Scheduler] 终止任务 {task_id}...")
        process.terminate()

        # 等待最多5秒
        try:
            process.wait(timeout=5)
            print(f"[Scheduler] 任务 {task_id} 已终止")
            return True
        except subprocess.TimeoutExpired:
            # 强制SIGKILL
            print(f"[Scheduler] 任务 {task_id} 未响应SIGTERM，强制终止...")
            process.kill()
            process.wait()
            print(f"[Scheduler] 任务 {task_id} 已强制终止")
            return True

    def cleanup(self):
        """清理所有资源

        Notes:
            - 终止所有运行中的子进程
            - 等待日志读取线程结束
            - 清空缓冲区
        """
        print("[Scheduler] 正在清理资源...")

        # 终止所有子进程
        for task_id, process in self.processes.items():
            if process.poll() is None:
                print(f"[Scheduler] 终止子进程: {task_id}")
                process.terminate()

        # 等待所有进程退出
        for task_id, process in self.processes.items():
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

        # 等待日志线程结束
        for task_id, thread in self.log_threads.items():
            if thread.is_alive():
                thread.join(timeout=1)

        print("[Scheduler] 清理完成")


# 全局单例（可选）
_scheduler_instance: Optional[TaskScheduler] = None

def get_scheduler() -> TaskScheduler:
    """获取全局调度器单例

    Returns:
        TaskScheduler实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
