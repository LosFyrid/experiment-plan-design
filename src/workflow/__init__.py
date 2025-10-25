"""工作流模块

提供完整的实验方案设计工作流：
- 任务管理（持久化、后台执行）
- 命令处理（/generate等）
- 需求提取、RAG检索、方案生成
- 任务辅助函数（友好展示、任务恢复）
"""

from workflow.task_manager import (
    TaskManager,
    TaskStatus,
    GenerationTask,
    LogWriter,
    get_task_manager
)

from workflow.command_handler import GenerateCommandHandler

from workflow.task_utils import (
    get_task_summary,
    list_resumable_tasks_friendly,
    resume_task_by_index,
    resume_task_interactive,
    display_resumable_tasks,
    get_tasks_by_session,
    get_task_statistics
)

__all__ = [
    # 任务管理核心
    'TaskManager',
    'TaskStatus',
    'GenerationTask',
    'LogWriter',
    'get_task_manager',

    # 命令处理
    'GenerateCommandHandler',

    # 任务辅助函数
    'get_task_summary',
    'list_resumable_tasks_friendly',
    'resume_task_by_index',
    'resume_task_interactive',
    'display_resumable_tasks',
    'get_tasks_by_session',
    'get_task_statistics',
]
