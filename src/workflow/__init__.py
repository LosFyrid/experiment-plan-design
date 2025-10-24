"""工作流模块

提供完整的实验方案设计工作流：
- 任务管理（持久化、后台执行）
- 命令处理（/generate等）
- 需求提取、RAG检索、方案生成
"""

from workflow.task_manager import (
    TaskManager,
    TaskStatus,
    GenerationTask,
    LogWriter,
    get_task_manager
)

from workflow.command_handler import GenerateCommandHandler

__all__ = [
    'TaskManager',
    'TaskStatus',
    'GenerationTask',
    'LogWriter',
    'get_task_manager',
    'GenerateCommandHandler',
]
