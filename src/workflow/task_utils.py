#!/usr/bin/env python3
"""任务管理辅助函数

提供友好的任务展示和恢复功能，供CLI工具、Web界面和分析脚本复用。

设计原则：
- 单一职责：每个函数只做一件事
- 可测试性：不依赖全局状态，易于单元测试
- 可复用性：被多个入口（CLI、Web、脚本）调用

典型使用场景：
1. 外部CLI工具 (scripts/inspect_tasks.py) - 任务恢复
2. Web API (未来) - 返回任务列表JSON
3. 分析脚本 (未来) - 统计待恢复任务
"""

from typing import List, Optional, Dict
from workflow.task_manager import get_task_manager, GenerationTask, TaskStatus


def get_task_summary(task: GenerationTask) -> str:
    """获取任务的友好摘要

    从需求文件中提取objective或target_compound作为任务描述，
    生成易于人类识别的摘要字符串。

    Args:
        task: 任务对象

    Returns:
        摘要字符串，格式："[task_id] 目标描述 (创建时间)"

    Examples:
        >>> task = get_task_manager().get_task("a3b5c7d9")
        >>> get_task_summary(task)
        "[a3b5c7d9] 合成阿司匹林 (2025-10-25 14:23)"

        >>> # 如果需求文件不存在或损坏
        >>> get_task_summary(corrupted_task)
        "[a3b5c7d9] N/A (2025-10-25 14:23)"

    Notes:
        - 优先使用objective字段
        - 如果objective为空，使用target_compound
        - 如果都为空或文件不存在，使用"N/A"
        - 过长的描述会被截断到40字符
    """
    # 尝试从需求文件读取objective或target_compound
    objective = "N/A"

    try:
        req = task.load_requirements()
        if req:
            # 优先使用objective，其次target_compound
            objective = req.get('objective') or req.get('target_compound') or 'N/A'

            # 截断过长的描述（保留可读性）
            if len(objective) > 40:
                objective = objective[:37] + "..."

    except Exception as e:
        # 静默失败，使用默认值
        # 可能的异常：文件不存在、JSON解析失败、权限错误等
        pass

    # 格式化时间字符串（精确到分钟）
    time_str = task.created_at.strftime('%Y-%m-%d %H:%M')

    return f"[{task.task_id}] {objective} ({time_str})"


def list_resumable_tasks_friendly() -> List[Dict]:
    """列出可恢复的任务（友好格式）

    获取所有处于AWAITING_CONFIRM状态的任务，并为每个任务生成：
    - 显示编号（从1开始，方便用户选择）
    - 任务对象（完整的GenerationTask）
    - 友好摘要（易于识别）

    Returns:
        任务列表，每个任务包含：
        - index (int): 显示编号（1, 2, 3...）
        - task (GenerationTask): 完整的任务对象
        - summary (str): 友好摘要字符串

    Examples:
        >>> tasks = list_resumable_tasks_friendly()
        >>> for item in tasks:
        ...     print(f"{item['index']}. {item['summary']}")
        1. [a3b5c7d9] 合成阿司匹林 (2025-10-25 14:23)
        2. [b4c6d8e0] 萃取咖啡因 (2025-10-25 10:15)

        >>> # 如果没有可恢复的任务
        >>> list_resumable_tasks_friendly()
        []

    Notes:
        - 只返回AWAITING_CONFIRM状态的任务
        - 按创建时间倒序排序（最新的在前）
        - 如果TaskManager单例未初始化，会自动创建
    """
    tm = get_task_manager()
    resumable = tm.get_resumable_tasks()

    # 按创建时间倒序排序（最新的在前，通常是用户最关心的）
    resumable.sort(key=lambda t: t.created_at, reverse=True)

    # 生成带编号的友好列表
    return [
        {
            "index": i + 1,
            "task": task,
            "summary": get_task_summary(task)
        }
        for i, task in enumerate(resumable)
    ]


def resume_task_by_index(index: int) -> bool:
    """通过编号恢复任务（用户友好）

    允许用户通过简单的数字编号（1, 2, 3...）来恢复任务，
    而不是记住复杂的UUID。

    Args:
        index: 任务编号（从1开始，对应list_resumable_tasks_friendly的index）

    Returns:
        是否成功恢复
        - True: 恢复成功，Worker将继续执行任务
        - False: 恢复失败（编号无效、任务不存在等）

    Examples:
        >>> resume_task_by_index(1)
        [TaskManager] 恢复任务 a3b5c7d9（自动确认需求，继续生成）
        [TaskManager] 任务 a3b5c7d9 已恢复，Worker将继续执行
        True

        >>> resume_task_by_index(99)
        ❌ 无效编号: 99（有效范围: 1-2）
        False

    Notes:
        - 内部调用TaskManager.resume_task()
        - 只能恢复AWAITING_CONFIRM状态的任务
        - 恢复后Worker会自动启动（如果未运行）
    """
    tasks = list_resumable_tasks_friendly()

    # 验证编号范围
    if index < 1 or index > len(tasks):
        print(f"❌ 无效编号: {index}（有效范围: 1-{len(tasks)}）")
        return False

    # 获取对应任务
    task = tasks[index - 1]["task"]

    # 调用TaskManager恢复任务
    tm = get_task_manager()
    return tm.resume_task(task.task_id)


def resume_task_interactive() -> bool:
    """交互式选择要恢复的任务

    提供友好的交互式界面，让用户：
    1. 查看所有可恢复的任务列表
    2. 通过编号选择要恢复的任务
    3. 确认恢复操作

    Returns:
        是否成功恢复
        - True: 用户选择了任务并成功恢复
        - False: 用户取消、无效输入、或恢复失败

    Examples:
        >>> resume_task_interactive()

        可恢复的任务:
        ================================================================================
          1. [a3b5c7d9] 合成阿司匹林 (2025-10-25 14:23)
          2. [b4c6d8e0] 萃取咖啡因 (2025-10-25 10:15)

        请选择要恢复的任务（输入编号，按Enter取消）: 1

        [TaskManager] 恢复任务 a3b5c7d9（自动确认需求，继续生成）
        [TaskManager] 任务 a3b5c7d9 已恢复，Worker将继续执行
        True

        >>> # 用户按Enter取消
        >>> resume_task_interactive()
        请选择要恢复的任务（输入编号，按Enter取消）:
        已取消
        False

    Notes:
        - 如果没有可恢复的任务，直接返回False
        - 处理KeyboardInterrupt（Ctrl+C）
        - 处理无效输入（非数字、超出范围等）
    """
    tasks = list_resumable_tasks_friendly()

    # 检查是否有可恢复的任务
    if not tasks:
        print("没有可恢复的任务")
        return False

    # 显示任务列表
    print("\n可恢复的任务:")
    print("=" * 80)
    for item in tasks:
        print(f"  {item['index']}. {item['summary']}")
    print()

    # 用户选择
    try:
        choice = input("请选择要恢复的任务（输入编号，按Enter取消）: ").strip()

        # 用户取消
        if not choice:
            print("已取消")
            return False

        # 尝试解析为整数
        try:
            index = int(choice)
        except ValueError:
            print("❌ 无效输入，请输入数字")
            return False

        # 恢复任务
        return resume_task_by_index(index)

    except KeyboardInterrupt:
        # 用户按Ctrl+C
        print("\n已取消")
        return False
    except Exception as e:
        # 其他未预期的异常
        print(f"❌ 发生错误: {e}")
        return False


def display_resumable_tasks():
    """显示所有可恢复的任务（仅显示，不恢复）

    格式化输出所有AWAITING_CONFIRM状态的任务，包括：
    - 任务编号（用于后续恢复）
    - 任务摘要（objective或target_compound）
    - 任务ID（UUID前8位）
    - 会话ID
    - 需求文件路径

    此函数用于信息展示，不执行任何操作。

    Examples:
        >>> display_resumable_tasks()

        ================================================================================
        可恢复的任务 (AWAITING_CONFIRM 状态)
        ================================================================================

          1. [a3b5c7d9] 合成阿司匹林 (2025-10-25 14:23)
             任务ID: a3b5c7d9
             会话ID: cli_session
             需求文件: logs/generation_tasks/a3b5c7d9/requirements.json

          2. [b4c6d8e0] 萃取咖啡因 (2025-10-25 10:15)
             任务ID: b4c6d8e0
             会话ID: cli_session
             需求文件: logs/generation_tasks/b4c6d8e0/requirements.json

        💡 恢复任务:
          python scripts/inspect_tasks.py --resume           # 交互式选择
          python scripts/inspect_tasks.py --resume <task_id> # 指定任务ID

        >>> # 如果没有可恢复的任务
        >>> display_resumable_tasks()

        没有可恢复的任务

    Notes:
        - 输出到stdout，适合CLI工具调用
        - 提供恢复命令的使用提示
        - 不返回任何值
    """
    tasks = list_resumable_tasks_friendly()

    # 检查是否有可恢复的任务
    if not tasks:
        print("\n没有可恢复的任务\n")
        return

    # 打印标题
    print("\n" + "=" * 80)
    print("可恢复的任务 (AWAITING_CONFIRM 状态)")
    print("=" * 80)

    # 打印每个任务的详细信息
    for item in tasks:
        task = item["task"]

        print(f"\n  {item['index']}. {item['summary']}")
        print(f"     任务ID: {task.task_id}")
        print(f"     会话ID: {task.session_id}")
        print(f"     需求文件: {task.requirements_file}")

    # 打印使用提示
    print("\n💡 恢复任务:")
    print("  python scripts/inspect_tasks.py --resume           # 交互式选择")
    print("  python scripts/inspect_tasks.py --resume <task_id> # 指定任务ID")
    print()


# ============================================================================
# 未来扩展函数（占位符，可根据需要实现）
# ============================================================================

def get_tasks_by_session(session_id: str) -> List[GenerationTask]:
    """获取指定会话的所有任务

    Args:
        session_id: 会话ID

    Returns:
        任务列表

    Notes:
        此函数为未来Web API设计，目前仅调用TaskManager
    """
    tm = get_task_manager()
    return tm.get_session_tasks(session_id)


def get_task_statistics() -> Dict[str, int]:
    """获取任务统计信息

    Returns:
        统计字典，包含：
        - total: 总任务数
        - pending: 待处理任务数
        - awaiting_confirm: 等待确认任务数
        - generating: 生成中任务数
        - completed: 已完成任务数
        - failed: 失败任务数
        - cancelled: 已取消任务数

    Notes:
        此函数为未来分析脚本设计
    """
    tm = get_task_manager()
    all_tasks = tm.get_all_tasks()

    stats = {
        "total": len(all_tasks),
        "pending": 0,
        "awaiting_confirm": 0,
        "extracting": 0,
        "retrieving": 0,
        "generating": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0
    }

    for task in all_tasks:
        status_key = task.status.value
        if status_key in stats:
            stats[status_key] += 1

    return stats
