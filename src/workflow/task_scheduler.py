"""任务调度器 - 使用子进程执行任务

核心特性：
- subprocess.Popen 启动独立工作进程（start_new_session=True）
- 子进程输出直接写入日志文件（不使用管道）
- 通过 PID 文件管理进程生命周期
- 提供 get_logs() API 直接读取日志文件

设计理念：
- CLI是"任务管理器"，只负责UI交互
- 实际工作由完全独立的子进程完成
- 子进程脱离父进程，CLI退出后继续运行
- 日志持久化到文件，完全隔离业务print和聊天界面

重构要点（2025-10-27）：
- 移除管道依赖：避免CLI退出时触发SIGPIPE导致子进程崩溃
- 真正独立运行：子进程不受父进程退出影响
- 日志持久化：CLI重启后可继续查看日志

类比：类似docker、kubectl的模式
"""

import sys
import subprocess
import json
import os
import signal
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from workflow.task_manager import get_task_manager, TaskStatus


class TaskScheduler:
    """任务调度器 - 管理独立子进程

    重构后：
    - 子进程通过 start_new_session=True 完全独立
    - 输出直接写文件，不依赖管道
    - 通过 PID 文件管理进程生命周期
    - 日志持久化，CLI 重启后可继续查看
    """

    def __init__(self):
        """初始化调度器"""
        self.tasks_dir = Path("logs/generation_tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # 子进程跟踪（只用于 CLI 当前会话，非持久化）
        # 重启后通过 PID 文件恢复进程信息
        self.processes: Dict[str, subprocess.Popen] = {}

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
        created_at = datetime.now().isoformat()

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": task_id,
                "session_id": session_id,
                "history": history,
                "created_at": created_at
            }, f, ensure_ascii=False, indent=2)

        # ⚠️ 关键修复：在启动子进程前就创建 task.json
        # 这样即使子进程失败，TaskManager 也能找到任务对象
        from workflow.task_manager import GenerationTask, TaskStatus

        task = GenerationTask(
            task_id=task_id,
            session_id=session_id,
            status=TaskStatus.PENDING,
            task_dir=task_dir,
            log_file=task_dir / "task.log",
            created_at=datetime.fromisoformat(created_at)
        )

        # 使用 TaskManager 保存任务（确保格式一致）
        task_manager = get_task_manager()
        task_manager._save_task(task)

        # 启动独立子进程
        worker_script = Path(__file__).parent / "task_worker.py"
        log_file = task_dir / "task.log"
        pid_file = task_dir / "process.pid"

        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # 打开日志文件（不在 with 块内，让子进程继承文件句柄）
        log_fp = open(log_file, 'a', buffering=1, encoding='utf-8')

        try:
            process = subprocess.Popen(
                [sys.executable, str(worker_script), task_id],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # 关键：脱离父进程的进程组
                cwd=Path.cwd(),
                env=env
            )

            # 保存 PID 到文件
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))

            # 跟踪进程（仅当前 CLI 会话有效）
            self.processes[task_id] = process

            return task_id

        except Exception as e:
            log_fp.close()
            raise e

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

        # 启动独立子进程（resume模式）
        worker_script = Path(__file__).parent / "task_worker.py"
        task_dir = self.tasks_dir / task_id
        log_file = task_dir / "task.log"
        pid_file = task_dir / "process.pid"

        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # 打开日志文件（追加模式）
        log_fp = open(log_file, 'a', buffering=1, encoding='utf-8')

        try:
            process = subprocess.Popen(
                [sys.executable, str(worker_script), task_id, "--resume"],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # 完全独立
                cwd=Path.cwd(),
                env=env
            )

            # 更新 PID 文件
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))

            # 跟踪进程
            self.processes[task_id] = process

            return True

        except Exception as e:
            log_fp.close()
            print(f"❌ 启动子进程失败: {e}")
            return False

    def submit_feedback_task(
        self,
        task_id: str,
        evaluation_mode: Optional[str] = None
    ) -> bool:
        """提交反馈训练任务（启动独立子进程）

        Args:
            task_id: 已完成的任务ID
            evaluation_mode: 评估模式（auto/llm_judge/human），可选，默认从配置读取

        Returns:
            是否成功启动

        Examples:
            >>> scheduler = TaskScheduler()
            >>> # 使用配置默认模式
            >>> scheduler.submit_feedback_task("abc123")
            >>> # 指定模式
            >>> scheduler.submit_feedback_task("abc123", "auto")
        """
        from workflow.task_manager import get_task_manager, TaskStatus

        # 验证任务存在且已完成
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)

        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return False

        if task.status != TaskStatus.COMPLETED:
            print(f"❌ 任务未完成（{task.status.value}），无法进行反馈")
            return False

        # 检查是否已有反馈进程在运行
        feedback_process_id = f"{task_id}_feedback"
        if feedback_process_id in self.processes:
            proc = self.processes[feedback_process_id]
            if proc.poll() is None:  # 进程仍在运行
                print(f"⚠️  任务 {task_id} 的反馈进程已在运行")
                return False

        # 构建命令（直接调用脚本文件，而不是用-m模块方式）
        # 这样脚本自己的 sys.path 设置会生效，无需外部设置PYTHONPATH
        worker_script = Path(__file__).parent / "feedback_worker.py"
        cmd = [sys.executable, str(worker_script), task_id]
        if evaluation_mode:
            cmd.extend(["--mode", evaluation_mode])

        # 启动独立子进程
        task_dir = self.tasks_dir / task_id
        log_file = task_dir / "task.log"
        pid_file = task_dir / "feedback.pid"  # 使用独立的 PID 文件

        # 设置 PYTHONUNBUFFERED=1 禁用 Python 输出缓冲（确保日志实时可见）
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # 打开日志文件（追加模式，不在 with 块内，让子进程继承文件句柄）
        log_fp = open(log_file, 'a', buffering=1, encoding='utf-8')

        try:
            process = subprocess.Popen(
                cmd,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # 完全独立
                cwd=Path.cwd(),
                env=env
            )

            # 保存 PID 到文件
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))

            # 跟踪进程
            self.processes[feedback_process_id] = process

            return True

        except Exception as e:
            log_fp.close()
            print(f"❌ 启动反馈子进程失败: {e}")
            return False

    def get_logs(self, task_id: str, tail: int = 50) -> List[str]:
        """获取任务日志（直接读取文件）

        Args:
            task_id: 任务ID
            tail: 返回最后N行（类似tail -n），0 或负数表示全部

        Returns:
            日志行列表

        Examples:
            >>> logs = scheduler.get_logs("abc123", tail=20)
            >>> for log in logs:
            ...     print(log)

        Notes:
            - 直接从 task.log 文件读取（持久化）
            - 支持 CLI 重启后继续查看日志
            - 高效处理大文件（使用 deque 滚动窗口）
        """
        log_file = self.tasks_dir / task_id / "task.log"

        # 检查日志文件是否存在
        if not log_file.exists():
            return [f"❌ 任务 {task_id} 日志文件不存在"]

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                if tail <= 0:
                    # 返回所有行
                    lines = [line.rstrip('\n') for line in f]
                else:
                    # 返回最后 N 行（使用 deque 高效滚动窗口）
                    from collections import deque
                    lines = deque(maxlen=tail)
                    for line in f:
                        lines.append(line.rstrip('\n'))
                    lines = list(lines)

            # 如果文件为空
            if not lines:
                return ["(暂无日志)"]

            return lines

        except Exception as e:
            return [f"❌ 读取日志失败: {e}"]

    def get_process_status(self, task_id: str) -> str:
        """获取子进程状态（支持 PID 文件查找）

        Args:
            task_id: 任务ID

        Returns:
            "running" | "completed" | "failed" | "not_found"

        Examples:
            >>> status = scheduler.get_process_status("abc123")
            >>> print(f"Process status: {status}")

        Notes:
            - 优先查找主任务进程，如果没找到则查找 feedback 进程
            - 支持从 PID 文件恢复进程信息（CLI 重启场景）
            - 如果进程不在内存中，只能判断 running/not_found，无法获取 exit code
        """
        # Helper function to check process status
        def check_process(process_key: str, pid_file_path: Path) -> str:
            """检查进程状态

            Returns:
                "running" | "completed" | "failed" | None (not found)
            """
            # 1. 优先从内存中查找（可获取 returncode）
            if process_key in self.processes:
                process = self.processes[process_key]
                if process.poll() is None:
                    return "running"
                else:
                    exit_code = process.returncode
                    return "completed" if exit_code == 0 else "failed"

            # 2. 从 PID 文件恢复（只能判断是否运行）
            if pid_file_path.exists():
                try:
                    with open(pid_file_path, 'r') as f:
                        pid = int(f.read().strip())

                    # 检查进程是否存在
                    try:
                        os.kill(pid, 0)  # 信号 0 只检查进程存在
                        return "running"
                    except ProcessLookupError:
                        # 进程已退出，但无法获取 exit code
                        # 返回 None，让调用方继续查找其他进程
                        return None
                    except PermissionError:
                        # 权限不足，假设进程仍在运行
                        return "running"

                except Exception:
                    # PID 文件损坏，忽略
                    return None

            return None

        # 1. 先查找主任务进程
        main_pid_file = self.tasks_dir / task_id / "process.pid"
        status = check_process(task_id, main_pid_file)
        if status:
            return status

        # 2. 查找 feedback 进程
        feedback_pid_file = self.tasks_dir / task_id / "feedback.pid"
        feedback_process_id = f"{task_id}_feedback"
        status = check_process(feedback_process_id, feedback_pid_file)
        if status:
            return status

        # 3. 都没找到
        return "not_found"

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

            # 计算日志行数（从日志文件读取）
            log_file = self.tasks_dir / task_id / "task.log"
            log_lines = 0
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_lines = sum(1 for _ in f)
                except Exception:
                    log_lines = 0

            info[task_id] = {
                "status": "running" if poll_result is None else (
                    "completed" if process.returncode == 0 else "failed"
                ),
                "exit_code": process.returncode,
                "log_lines": log_lines
            }

        return info

    def terminate_task(self, task_id: str) -> bool:
        """终止任务子进程（支持 PID 文件查找）

        Args:
            task_id: 任务ID

        Returns:
            是否成功终止

        Notes:
            - 先尝试SIGTERM（优雅退出）
            - 如果5秒后仍未退出，强制SIGKILL
            - 支持终止主任务或反馈任务
            - 支持从 PID 文件恢复进程信息（CLI 重启场景）
        """
        # 1. 查找进程（优先查主任务，然后查反馈任务）
        pid = None
        pid_file = None
        process_key = None

        # 查找主任务
        if task_id in self.processes:
            process_key = task_id
            pid_file = self.tasks_dir / task_id / "process.pid"
        # 查找反馈任务
        elif f"{task_id}_feedback" in self.processes:
            process_key = f"{task_id}_feedback"
            pid_file = self.tasks_dir / task_id / "feedback.pid"
        # 从 PID 文件恢复（CLI 重启场景）
        else:
            # 先查主任务 PID 文件
            main_pid_file = self.tasks_dir / task_id / "process.pid"
            feedback_pid_file = self.tasks_dir / task_id / "feedback.pid"

            if main_pid_file.exists():
                pid_file = main_pid_file
            elif feedback_pid_file.exists():
                pid_file = feedback_pid_file
            else:
                print(f"❌ 任务 {task_id} 的子进程不存在（未找到 PID 文件）")
                return False

        # 2. 获取 PID
        if process_key and process_key in self.processes:
            # 从内存中的进程对象获取
            process = self.processes[process_key]
            pid = process.pid
        elif pid_file and pid_file.exists():
            # 从 PID 文件读取
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
            except Exception as e:
                print(f"❌ 读取 PID 文件失败: {e}")
                return False
        else:
            print(f"❌ 无法获取任务 {task_id} 的 PID")
            return False

        # 3. 检查进程是否存在
        try:
            os.kill(pid, 0)  # 信号 0 只检查进程存在，不发送信号
        except ProcessLookupError:
            print(f"⚠️  任务 {task_id} 子进程已退出（PID: {pid}）")
            # 清理 PID 文件
            if pid_file and pid_file.exists():
                pid_file.unlink()
            return False
        except PermissionError:
            print(f"❌ 无权限访问进程 {pid}")
            return False

        # 4. 发送 SIGTERM（优雅退出）
        print(f"[Scheduler] 终止任务 {task_id}（PID: {pid}）...")
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"❌ 发送 SIGTERM 失败: {e}")
            return False

        # 5. 等待最多 5 秒
        import time
        for i in range(50):  # 50 * 0.1s = 5s
            time.sleep(0.1)
            try:
                os.kill(pid, 0)  # 检查进程是否还存在
            except ProcessLookupError:
                print(f"[Scheduler] 任务 {task_id} 已终止")
                # 清理 PID 文件
                if pid_file and pid_file.exists():
                    pid_file.unlink()
                return True

        # 6. 强制 SIGKILL
        print(f"[Scheduler] 任务 {task_id} 未响应 SIGTERM，强制终止...")
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)  # 等待进程完全退出
            print(f"[Scheduler] 任务 {task_id} 已强制终止")
            # 清理 PID 文件
            if pid_file and pid_file.exists():
                pid_file.unlink()
            return True
        except Exception as e:
            print(f"❌ 发送 SIGKILL 失败: {e}")
            return False

    def cleanup(self):
        """清理所有资源

        Notes:
            - 终止所有运行中的子进程
            - 子进程独立运行，不会因父进程退出而终止
            - 这个方法主要用于优雅退出时的资源清理
        """
        print("[Scheduler] 正在清理资源...")

        # 终止所有子进程（如果需要的话）
        # 注意：由于使用 start_new_session=True，即使不终止，子进程也会继续运行
        for task_id, process in self.processes.items():
            if process.poll() is None:
                print(f"[Scheduler] 检测到运行中的子进程: {task_id}")
                # 不强制终止，让子进程继续在后台运行
                # 如果需要终止，用户可以使用 /cancel 命令

        print("[Scheduler] 清理完成（子进程继续在后台运行）")


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
