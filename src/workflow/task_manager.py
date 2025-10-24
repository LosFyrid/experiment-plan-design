"""后台任务管理器 - 支持持久化和守护进程

特性：
- 任务持久化到磁盘（CLI退出后任务继续运行）
- 文件锁机制（防止多实例冲突）
- 工作线程自动管理（空闲超时自动退出）
- 优雅关闭和资源清理
"""

import threading
import queue
import time
import signal
import atexit
import json
import os
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"                 # 等待开始
    EXTRACTING = "extracting"           # 提取需求
    AWAITING_CONFIRM = "awaiting_confirm"  # 等待用户确认需求
    RETRIEVING = "retrieving"           # RAG检索
    GENERATING = "generating"           # 生成方案
    COMPLETED = "completed"             # 完成
    FAILED = "failed"                   # 失败
    CANCELLED = "cancelled"             # 取消


@dataclass
class GenerationTask:
    """生成任务（持久化版本）"""
    task_id: str
    session_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)

    # 文件路径
    task_dir: Optional[Path] = None
    log_file: Optional[Path] = None

    # 元数据
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def requirements_file(self) -> Path:
        """需求文件路径"""
        return self.task_dir / "requirements.json"

    @property
    def templates_file(self) -> Path:
        """模板文件路径"""
        return self.task_dir / "templates.json"

    @property
    def plan_file(self) -> Path:
        """方案文件路径"""
        return self.task_dir / "plan.json"

    def save_requirements(self, requirements: Dict):
        """保存需求到文件"""
        with open(self.requirements_file, 'w', encoding='utf-8') as f:
            json.dump(requirements, f, indent=2, ensure_ascii=False)

    def load_requirements(self) -> Optional[Dict]:
        """从文件加载需求"""
        if not self.requirements_file.exists():
            return None
        with open(self.requirements_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_templates(self, templates: List[Dict]):
        """保存模板到文件"""
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)

    def save_plan(self, plan):
        """保存方案到文件"""
        # 将Pydantic模型转为dict
        if hasattr(plan, 'model_dump'):
            plan_dict = plan.model_dump()
        elif hasattr(plan, 'dict'):
            plan_dict = plan.dict()
        else:
            plan_dict = plan

        with open(self.plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan_dict, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "has_requirements": self.requirements_file.exists() if self.task_dir else False,
            "has_templates": self.templates_file.exists() if self.task_dir else False,
            "has_plan": self.plan_file.exists() if self.task_dir else False,
            "error": self.error,
            "metadata": self.metadata,
            "task_dir": str(self.task_dir) if self.task_dir else None,
            "log_file": str(self.log_file) if self.log_file else None
        }

    @classmethod
    def from_dict(cls, data: Dict, task_dir: Path):
        """从字典反序列化"""
        return cls(
            task_id=data["task_id"],
            session_id=data["session_id"],
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            task_dir=task_dir,
            log_file=Path(data["log_file"]) if data.get("log_file") else None,
            metadata=data.get("metadata", {}),
            error=data.get("error")
        )


class LogWriter:
    """线程安全的日志写入器"""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.file = open(log_file, 'w', encoding='utf-8')
        self.lock = threading.Lock()

    def write(self, message: str):
        """写入日志（带时间戳）"""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.file.write(f"[{timestamp}] {message}\n")
            self.file.flush()

    def close(self):
        """关闭日志文件"""
        if self.file and not self.file.closed:
            self.file.close()


class TaskManager:
    """持久化任务管理器（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 任务目录
        self.tasks_dir = Path("logs/generation_tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        # 锁文件（用于防止多实例冲突）
        self.lock_file_path = self.tasks_dir / ".worker.lock"
        self.lock_file_fd = None

        # 任务存储（内存缓存）
        self.tasks: Dict[str, GenerationTask] = {}
        self.task_lock = threading.Lock()

        # 任务队列
        self.task_queue = queue.Queue()

        # 工作线程控制
        self.worker_thread = None
        self.running = False
        self.idle_timeout = 300  # 空闲5分钟后自动退出
        self.last_activity_time = time.time()

        # 从磁盘恢复任务
        self._restore_tasks()

        # 注册清理函数
        atexit.register(self._cleanup_on_exit)

        # 注册信号处理（优雅关闭）
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def start(self, as_daemon: bool = False):
        """启动工作线程

        Args:
            as_daemon: 是否作为守护线程（False=CLI退出后继续运行）
        """
        # 尝试获取文件锁
        if not self._try_acquire_lock():
            print("[TaskManager] Worker已在其他进程运行，跳过启动")
            return

        if self.running:
            return

        self.running = True
        self.last_activity_time = time.time()

        # 非守护线程，CLI退出后继续运行
        self.worker_thread = threading.Thread(
            target=self._worker,
            daemon=as_daemon,
            name="TaskWorker"
        )
        self.worker_thread.start()

        print(f"[TaskManager] Worker线程已启动 (daemon={as_daemon}, pid={os.getpid()})")

    def stop(self):
        """停止工作线程（优雅关闭）"""
        if not self.running:
            return

        print("[TaskManager] 正在停止Worker线程...")
        self.running = False

        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

        self._release_lock()
        print("[TaskManager] Worker线程已停止")

    def _try_acquire_lock(self) -> bool:
        """尝试获取Worker线程锁（使用文件锁）"""
        try:
            # 打开锁文件（如果不存在则创建）
            self.lock_file_fd = os.open(
                self.lock_file_path,
                os.O_CREAT | os.O_RDWR
            )

            # 尝试非阻塞独占锁
            import fcntl
            fcntl.flock(self.lock_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # 写入进程信息
            lock_info = {
                "pid": os.getpid(),
                "started_at": datetime.now().isoformat(),
                "heartbeat": datetime.now().isoformat()
            }
            os.write(self.lock_file_fd, json.dumps(lock_info).encode())

            return True

        except (IOError, OSError, BlockingIOError) as e:
            # 锁已被占用
            if self.lock_file_fd is not None:
                try:
                    os.close(self.lock_file_fd)
                except:
                    pass
                self.lock_file_fd = None
            return False

    def _release_lock(self):
        """释放Worker线程锁"""
        if self.lock_file_fd is not None:
            try:
                import fcntl
                fcntl.flock(self.lock_file_fd, fcntl.LOCK_UN)
                os.close(self.lock_file_fd)

                # 删除锁文件
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()

            except Exception as e:
                print(f"[TaskManager] 释放锁失败: {e}")
            finally:
                self.lock_file_fd = None

    def _update_heartbeat(self):
        """更新心跳时间戳（表明进程还活着）"""
        if self.lock_file_fd is not None:
            try:
                lock_info = {
                    "pid": os.getpid(),
                    "heartbeat": datetime.now().isoformat()
                }

                # 清空文件并写入新内容
                os.lseek(self.lock_file_fd, 0, os.SEEK_SET)
                os.ftruncate(self.lock_file_fd, 0)
                os.write(self.lock_file_fd, json.dumps(lock_info).encode())
            except Exception as e:
                print(f"[TaskManager] 更新心跳失败: {e}")

    def _cleanup_on_exit(self):
        """退出时清理（由atexit调用）"""
        self.stop()

    def _signal_handler(self, signum, frame):
        """信号处理器（优雅关闭）"""
        print(f"\n[TaskManager] 收到信号 {signum}，正在关闭...")
        self.stop()
        exit(0)

    def submit_task(
        self,
        session_id: str,
        handler: Callable,
        **kwargs
    ) -> str:
        """提交任务（持久化到磁盘）

        Args:
            session_id: 会话ID
            handler: 处理函数（接收task、log、kwargs）
            **kwargs: 传递给handler的参数

        Returns:
            task_id
        """
        import uuid
        task_id = str(uuid.uuid4())[:8]

        # 创建任务目录
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(exist_ok=True)

        # 创建任务
        task = GenerationTask(
            task_id=task_id,
            session_id=session_id,
            task_dir=task_dir,
            log_file=task_dir / "task.log"
        )

        with self.task_lock:
            self.tasks[task_id] = task

        # 持久化任务状态
        self._save_task(task)

        # 提交到队列
        self.task_queue.put((task_id, handler, kwargs))

        # 更新活动时间
        self.last_activity_time = time.time()

        return task_id

    def get_task(self, task_id: str) -> Optional[GenerationTask]:
        """获取任务（从内存或磁盘）"""
        with self.task_lock:
            # 先从内存查找
            if task_id in self.tasks:
                return self.tasks[task_id]

        # 从磁盘加载
        task_dir = self.tasks_dir / task_id
        if not task_dir.exists():
            return None

        task_file = task_dir / "task.json"
        if not task_file.exists():
            return None

        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)

            task = GenerationTask.from_dict(task_data, task_dir)

            # 缓存到内存
            with self.task_lock:
                self.tasks[task_id] = task

            return task

        except Exception as e:
            print(f"[TaskManager] 加载任务失败 {task_id}: {e}")
            return None

    def get_all_tasks(self) -> List[GenerationTask]:
        """获取所有任务"""
        tasks = []

        # 从磁盘扫描所有任务
        if not self.tasks_dir.exists():
            return tasks

        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            task = self.get_task(task_dir.name)
            if task:
                tasks.append(task)

        return tasks

    def get_session_tasks(self, session_id: str) -> List[GenerationTask]:
        """获取会话的所有任务"""
        all_tasks = self.get_all_tasks()
        return [t for t in all_tasks if t.session_id == session_id]

    def _save_task(self, task: GenerationTask):
        """保存任务状态到磁盘"""
        if not task.task_dir:
            return

        task_file = task.task_dir / "task.json"

        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)

    def _restore_tasks(self):
        """从磁盘恢复任务"""
        if not self.tasks_dir.exists():
            return

        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            task_file = task_dir / "task.json"
            if not task_file.exists():
                continue

            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)

                # 重建任务对象
                task = GenerationTask.from_dict(task_data, task_dir)
                self.tasks[task.task_id] = task

                # 如果任务未完成，重新加入队列
                # （这里简化处理，不重新执行，只是恢复状态）

            except Exception as e:
                print(f"[TaskManager] 恢复任务失败 {task_dir.name}: {e}")

    def _worker(self):
        """工作线程主循环"""
        print("[TaskWorker] 工作线程开始运行")

        heartbeat_interval = 10  # 每10秒更新一次心跳
        last_heartbeat = time.time()

        while self.running:
            try:
                # 更新心跳
                if time.time() - last_heartbeat > heartbeat_interval:
                    self._update_heartbeat()
                    last_heartbeat = time.time()

                # 检查空闲超时
                if time.time() - self.last_activity_time > self.idle_timeout:
                    print("[TaskWorker] 空闲超时，自动退出")
                    self.running = False
                    break

                # 获取任务（超时1秒）
                try:
                    task_id, handler, kwargs = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # 更新活动时间
                self.last_activity_time = time.time()

                # 从内存或磁盘加载任务
                task = self.get_task(task_id)
                if not task:
                    print(f"[TaskWorker] 任务 {task_id} 不存在")
                    continue

                # 执行任务
                self._execute_task(task, handler, kwargs)

            except Exception as e:
                print(f"[TaskWorker] Worker异常: {e}")
                import traceback
                traceback.print_exc()

        print("[TaskWorker] 工作线程已停止")
        self._release_lock()

    def _execute_task(
        self,
        task: GenerationTask,
        handler: Callable,
        kwargs: Dict
    ):
        """执行任务（在工作线程中）"""
        log_writer = LogWriter(task.log_file)

        try:
            log_writer.write(f"Task {task.task_id} started")
            log_writer.write(f"Session: {task.session_id}")
            log_writer.write(f"Handler: {handler.__name__}")

            # 调用handler（handler负责更新task状态）
            handler(task, log_writer, **kwargs)

            log_writer.write(f"Task {task.task_id} finished")

        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()

            with self.task_lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)

            self._save_task(task)

            log_writer.write(f"Task {task.task_id} failed: {e}")
            log_writer.write(error_msg)

        finally:
            log_writer.close()


# 全局单例
_task_manager = None

def get_task_manager() -> TaskManager:
    """获取全局任务管理器（单例）"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
