#!/usr/bin/env python3
"""
完整工作流CLI - Chatbot + Generator + 任务管理

支持斜杠命令：
- /generate, /gen   - 生成实验方案（后台执行）
- /status           - 查看任务状态
- /requirements     - 查看任务的需求文件
- /confirm          - 确认需求，继续生成
- /cancel           - 取消任务
- /retry <task_id>  - 重试失败的任务
- /view <task_id>   - 查看生成的方案
- /tasks            - 列出所有任务
- /history          - 查看当前会话对话历史
- /sessions         - 列出所有会话（仅SQLite模式）
- /switch <id>      - 切换到指定会话
- /new [name]       - 创建新会话
- /clear            - 清屏（不删除历史）
- /help             - 显示帮助
- /quit, /exit      - 退出
"""

import sys
import os
import time
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

from chatbot.chatbot import Chatbot
from workflow.task_scheduler import TaskScheduler
from workflow.task_manager import get_task_manager, TaskStatus, GenerationTask
from ace_framework.playbook.schemas import ExperimentPlan


# ============================================================================
# 显示函数
# ============================================================================

def print_banner():
    """打印欢迎横幅"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       🧪  化学实验方案设计助手                              ║
║                                                            ║
║          Chatbot + Generator + RAG                         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)


def generate_session_id(custom_name: str = None) -> str:
    """生成会话ID

    Args:
        custom_name: 自定义名称（可选）

    Returns:
        会话ID字符串
    """
    import uuid
    from datetime import datetime

    if custom_name:
        # 用户自定义名称
        return custom_name
    else:
        # 自动生成: YYYYMMDD_HHMM_<short_uuid>
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        short_id = str(uuid.uuid4())[:6]
        return f"{timestamp}_{short_id}"


def print_sessions_list(bot: Chatbot, current_session_id: str, is_sqlite_mode: bool = False):
    """打印会话列表

    Args:
        bot: Chatbot实例
        current_session_id: 当前会话ID
        is_sqlite_mode: 是否为SQLite模式
    """
    sessions = bot.list_sessions()

    if not sessions:
        if is_sqlite_mode:
            # SQLite模式但数据库为空
            print("\n暂无保存的会话")
            print("💡 提示: 当前为SQLite模式，会话会自动保存")
            print("         开始对话后会自动创建会话记录\n")
        else:
            # 内存模式
            print("\n暂无保存的会话")
            print("提示: 当前使用内存模式，会话不会持久化")
            print("      修改 configs/chatbot_config.yaml 中的 memory.type 为 'sqlite' 以启用持久化\n")
        return

    print("\n" + "=" * 70)
    print("所有会话列表")
    print("=" * 70)

    for session_id in sorted(sessions, reverse=True):
        history = bot.get_history(session_id)
        msg_count = len(history)

        # 当前会话标记
        marker = "👉" if session_id == current_session_id else "  "

        # 获取第一条用户消息作为预览
        preview = ""
        for msg in history:
            if msg["role"] == "user":
                preview = msg["content"][:50]
                if len(msg["content"]) > 50:
                    preview += "..."
                break

        print(f"\n{marker} {session_id}")
        print(f"   消息数: {msg_count}")
        if preview:
            print(f"   预览: {preview}")

    print("\n💡 使用 /switch <session_id> 切换会话")
    print("   使用 /new [name] 创建新会话\n")


def print_help():
    """打印帮助信息"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                     使用说明                                ║
╚════════════════════════════════════════════════════════════╝

📋 命令列表:
  /generate, /gen         - 根据对话历史生成实验方案（后台子进程）
  /feedback <task_id>     - 对已完成的方案进行反馈训练（ACE循环）
  /status [task_id]       - 查看任务状态和文件路径
  /requirements [task_id] - 查看任务的需求文件（JSON格式）
  /logs [task_id]         - 查看任务日志（实时缓冲区）
  /confirm [task_id]      - 确认需求，继续生成方案
  /cancel [task_id]       - 取消任务
  /retry <task_id>        - 重试失败的任务（支持--clean, --force, --mode选项）
  /view <task_id>         - 查看生成的方案（格式化显示）
  /tasks                  - 列出所有任务
  /history                - 查看当前会话对话历史
  /sessions               - 列出所有会话（仅SQLite模式）
  /switch <session_id>    - 切换到指定会话
  /new [session_name]     - 创建新会话
  /clear                  - 清屏（不删除历史）
  /help                   - 显示此帮助信息
  /quit, /exit            - 退出程序（子进程继续在后台运行）

💡 工作流程:
  1. 与助手自然对话，描述你的实验需求
  2. 输入 /generate 触发方案生成（后台子进程执行）
  3. 系统提取需求后会自动暂停
  4. 使用 /requirements 查看提取的需求（JSON格式）
  5. 如需修改，可直接编辑文件或重新对话
  6. 输入 /confirm 确认，系统继续生成方案
  7. 使用 /logs 查看实时日志
  8. 使用 /view 查看最终结果
  9. （可选）使用 /feedback 进行反馈训练，改进playbook

🎯 示例对话:
  你: 我想合成阿司匹林
  助手: 好的！让我了解一些细节...
  你: 用水杨酸和乙酸酐，2小时内完成
  助手: 明白了。还有其他要求吗？
  你: /generate              ← 触发生成（启动子进程）
  [子进程后台提取需求并暂停]
  你: /logs                  ← 查看日志
  [显示实时日志输出]
  你: /status                ← 查看状态（AWAITING_CONFIRM）
  你: /requirements          ← 查看提取的需求（格式化显示）
  [显示目标化合物、材料、约束等信息]
  你: /confirm               ← 确认继续（重新启动子进程）
  [子进程生成方案]
  你: /logs                  ← 实时查看生成进度
  你: /view <task_id>        ← 查看方案
  你: /feedback <task_id>    ← （可选）反馈训练，改进playbook
  你: 第3步的温度可以调低吗？  ← 继续对话

📂 会话管理（SQLite模式）:
  /sessions                  - 列出所有保存的会话
  /new aspirin_project       - 创建名为"aspirin_project"的新会话
  /switch aspirin_project    - 切换到指定会话
  /history                   - 查看当前会话历史

💡 内存模式 vs SQLite模式:
  内存模式（默认）：会话存在内存中，程序退出后丢失
  SQLite模式：会话持久化到数据库，可恢复历史会话

  切换方式：修改 configs/chatbot_config.yaml
  memory:
    type: "sqlite"  # 改为sqlite启用持久化
    sqlite_path: "data/chatbot_memory.db"
    """)


def print_history(bot: Chatbot, session_id: str):
    """打印会话历史"""
    history = bot.get_history(session_id)

    if not history:
        print("\n[暂无历史记录]\n")
        return

    print("\n" + "=" * 70)
    print("会话历史:")
    print("=" * 70)

    for i, msg in enumerate(history, 1):
        role_display = {
            "user": "👤 你",
            "assistant": "🤖 助手",
            "system": "⚙️  系统"
        }.get(msg["role"], msg["role"])

        print(f"\n[{i}] {role_display}:")
        content = msg["content"]
        # 截断过长内容
        if len(content) > 500:
            content = content[:500] + "..."
        print(f"{content}")
        print("-" * 70)

    print()


def print_task_status(task: GenerationTask):
    """打印任务状态（带文件路径）"""
    # 主任务状态图标
    status_icons = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.EXTRACTING: "🔍",
        TaskStatus.AWAITING_CONFIRM: "⏸️",
        TaskStatus.RETRIEVING: "📚",
        TaskStatus.GENERATING: "⚙️",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.CANCELLED: "🚫"
    }

    # Feedback状态图标（字符串状态，非枚举）
    feedback_icons = {
        "pending": "⏳",
        "running": "🔄",
        "evaluating": "📊",
        "reflecting": "💭",
        "curating": "📝",
        "completed": "🎓",
        "failed": "❌"
    }

    icon = status_icons.get(task.status, "❓")

    print("\n" + "=" * 70)

    # 组合显示主任务状态和feedback状态
    if task.status == TaskStatus.COMPLETED and task.feedback_status:
        feedback_icon = feedback_icons.get(task.feedback_status, "❓")
        if task.feedback_status == "completed":
            print(f"任务状态: {icon} {task.status.value.upper()} (🎓 Feedback完成)")
        elif task.feedback_status == "failed":
            print(f"任务状态: {icon} {task.status.value.upper()} (❌ Feedback失败)")
        elif task.feedback_status in ["pending", "evaluating", "reflecting", "curating"]:
            print(f"任务状态: {icon} {task.status.value.upper()} ({feedback_icon} Feedback进行中: {task.feedback_status})")
        else:
            print(f"任务状态: {icon} {task.status.value.upper()}")
            print(f"Feedback状态: {feedback_icon} {task.feedback_status.upper()}")
    else:
        print(f"任务状态: {icon} {task.status.value.upper()}")

    print("=" * 70)
    print(f"  任务ID: {task.task_id}")
    print(f"  会话ID: {task.session_id}")
    print(f"  创建时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  任务目录: {task.task_dir}")
    print(f"  日志文件: {task.log_file}")

    # 显示中间数据文件路径
    print(f"\n📁 数据文件:")

    if task.requirements_file.exists():
        print(f"  ✅ 需求: {task.requirements_file}")
    else:
        print(f"  ⏳ 需求: (生成中...)")

    if task.templates_file.exists():
        print(f"  ✅ 模板: {task.templates_file}")

    if task.plan_file.exists():
        print(f"  ✅ 方案: {task.plan_file}")

    # 显示反馈训练文件
    if task.feedback_file.exists():
        print(f"  ✅ 评估反馈: {task.feedback_file}")

    if task.reflection_file.exists():
        print(f"  ✅ 反思结果: {task.reflection_file}")

    if task.curation_file.exists():
        print(f"  ✅ 更新记录: {task.curation_file}")

    # 根据状态显示操作提示
    if task.status == TaskStatus.AWAITING_CONFIRM:
        print(f"\n💡 操作提示:")
        print(f"  # 查看需求")
        print(f"  cat {task.requirements_file}")
        print(f"  ")
        print(f"  # 修改需求（使用你喜欢的编辑器）")
        print(f"  nano {task.requirements_file}")
        print(f"  vim {task.requirements_file}")
        print(f"  ")
        print(f"  # 确认继续")
        print(f"  /confirm")
        print(f"  ")
        print(f"  # 取消任务")
        print(f"  /cancel")

    elif task.status == TaskStatus.COMPLETED:
        # 检查是否有feedback流程完成
        if task.feedback_status == "completed":
            print(f"\n🎓 反馈训练完成!")

            # 显示playbook变化（从curation文件读取）
            if task.curation_file.exists():
                import json
                with open(task.curation_file, 'r', encoding='utf-8') as f:
                    curation = json.load(f)

                print(f"\n📊 Playbook 更新:")
                print(f"  新增: {curation.get('bullets_added', 0)} bullets")
                print(f"  删除: {curation.get('bullets_removed', 0)} bullets")
                print(f"  更新: {curation.get('bullets_updated', 0)} bullets")

            print(f"\n💡 查看结果:")
            print(f"  cat {task.feedback_file}  # 评估反馈")
            print(f"  cat {task.reflection_file}  # 反思结果")
            print(f"  cat {task.curation_file}  # 更新记录")
        elif task.feedback_status in ["evaluating", "reflecting", "curating"]:
            # Feedback 流程进行中
            feedback_stage_names = {
                "evaluating": "评估方案质量",
                "reflecting": "反思分析",
                "curating": "更新Playbook"
            }
            stage_name = feedback_stage_names.get(task.feedback_status, task.feedback_status)

            print(f"\n🔄 反馈训练进行中...")
            print(f"  当前阶段: {stage_name}")
            print(f"  评估模式: {task.feedback_mode or '(配置默认)'}")

            print(f"\n💡 查看实时日志:")
            print(f"  /logs {task.task_id}  # 查看反馈流程日志")
            print(f"  /logs {task.task_id} --tail 100  # 查看更多日志")

            print(f"\n💡 主任务方案:")
            print(f"  /view {task.task_id}  # 查看生成的方案")
        elif task.feedback_status == "failed":
            # Feedback 流程失败
            print(f"\n❌ 反馈训练失败!")
            if task.feedback_error:
                print(f"  错误: {task.feedback_error}")

            print(f"\n💡 查看日志:")
            print(f"  /logs {task.task_id}  # 查看失败原因")

            print(f"\n💡 主任务方案:")
            print(f"  /view {task.task_id}  # 查看生成的方案")
        else:
            # 主任务完成，feedback 未开始
            print(f"\n✅ 任务完成!")
            print(f"  耗时: {task.metadata.get('duration', 0):.2f}s")
            print(f"  Tokens: {task.metadata.get('total_tokens', 0)}")
            print(f"\n💡 查看方案:")
            print(f"  cat {task.plan_file}  # JSON格式")
            print(f"  /view {task.task_id}  # 格式化显示")
            print(f"\n💡 反馈训练（可选，改进playbook）:")
            print(f"  /feedback {task.task_id}  # 使用配置默认模式")
            print(f"  /feedback {task.task_id} --mode auto  # 指定评估模式")

    elif task.status == TaskStatus.FAILED:
        print(f"\n❌ 失败原因: {task.error}")
        if task.failed_stage:
            print(f"   失败阶段: {task.failed_stage}")
        if task.retry_count > 0:
            print(f"   重试次数: {task.retry_count}/{task.max_retries}")

        print(f"\n💡 查看日志:")
        print(f"  cat {task.log_file}")

        print(f"\n💡 重试选项:")
        print(f"  /retry {task.task_id}              # 部分重试（从失败点继续）")
        print(f"  /retry {task.task_id} --clean      # 完全重试（从头开始）")
        print(f"  /retry {task.task_id} --force      # 强制重试（忽略次数限制）")

    print()


def format_plan_output(plan: ExperimentPlan, metadata: dict) -> str:
    """格式化实验方案输出"""
    lines = []

    lines.append("\n" + "=" * 70)
    lines.append(f"  {plan.title}")
    lines.append("=" * 70)

    lines.append(f"\n## 📋 实验目标")
    lines.append(f"{plan.objective}")

    lines.append(f"\n## 🧪 材料清单")
    for mat in plan.materials:
        line = f"  • {mat.name}: {mat.amount}"
        if mat.purity:
            line += f" (纯度: {mat.purity})"
        if mat.hazard_info:
            line += f" ⚠️  {mat.hazard_info}"
        lines.append(line)

    lines.append(f"\n## 📝 实验步骤")
    for step in plan.procedure:
        lines.append(f"\n  步骤 {step.step_number}:")
        lines.append(f"  {step.description}")

        details = []
        if step.duration:
            details.append(f"⏱️  {step.duration}")
        if step.temperature:
            details.append(f"🌡️  {step.temperature}")
        if details:
            lines.append(f"  {' | '.join(details)}")

        if step.critical:
            lines.append("  ⚡ 关键步骤")
        if step.notes:
            lines.append(f"  💡 {step.notes}")

    lines.append(f"\n## ⚠️  安全注意事项")
    for note in plan.safety_notes:
        lines.append(f"  • {note}")

    lines.append(f"\n## ✅ 预期结果")
    lines.append(f"{plan.expected_outcome}")

    if plan.quality_control:
        lines.append(f"\n## 🔍 质量控制")
        for qc in plan.quality_control:
            lines.append(f"  • {qc.check_point}")
            lines.append(f"    方法: {qc.method}")
            lines.append(f"    标准: {qc.acceptance_criteria}")
            if qc.timing:
                lines.append(f"    时机: {qc.timing}")

    if plan.estimated_duration:
        lines.append(f"\n⏰ 预计总时长: {plan.estimated_duration}")
    if plan.difficulty_level:
        levels = {"beginner": "初级", "intermediate": "中级", "advanced": "高级"}
        lines.append(f"🎯 难度等级: {levels.get(plan.difficulty_level, plan.difficulty_level)}")

    lines.append("\n" + "=" * 70)

    # 元数据
    lines.append(f"\n📊 生成统计:")
    lines.append(f"  • 耗时: {metadata.get('duration', 0):.2f}s")
    lines.append(f"  • Tokens: {metadata.get('total_tokens', 0)}")
    lines.append(f"  • 使用playbook: {metadata.get('retrieved_bullets_count', 0)}条")

    return "\n".join(lines)


def get_recent_task(session_id: str, task_manager) -> tuple[GenerationTask, list]:
    """获取当前session的最近任务（包括已完成/失败，用于查看状态和日志）

    Args:
        session_id: 会话ID
        task_manager: TaskManager实例

    Returns:
        (最近任务, 所有相关任务列表)
        如果没有任务，返回 (None, [])
    """
    # 获取当前session的所有任务
    tasks = task_manager.get_session_tasks(session_id)

    # 筛选相关任务（排除已取消的）
    relevant_tasks = [t for t in tasks if t.status != TaskStatus.CANCELLED]

    if not relevant_tasks:
        return None, []

    # 返回最新的任务
    relevant_tasks.sort(key=lambda t: t.created_at, reverse=True)
    return relevant_tasks[0], relevant_tasks


def get_running_task(session_id: str, task_manager) -> tuple[GenerationTask, list]:
    """获取当前session的运行中任务（用于取消操作和退出检查）

    Args:
        session_id: 会话ID
        task_manager: TaskManager实例

    Returns:
        (运行中任务, 所有运行中任务列表)
        如果没有运行中任务，返回 (None, [])

    Notes:
        "运行中"包括：
        1. 主任务未结束（PENDING, EXTRACTING, AWAITING_CONFIRM, RETRIEVING, GENERATING）
        2. 主任务已完成但feedback流程正在运行
    """
    # 获取当前session的所有任务
    tasks = task_manager.get_session_tasks(session_id)

    # 筛选运行中任务
    running_tasks = []
    for t in tasks:
        # 主任务运行中
        if t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            running_tasks.append(t)
        # 或 feedback流程运行中
        elif t.status == TaskStatus.COMPLETED and t.feedback_status in ["evaluating", "reflecting", "curating"]:
            running_tasks.append(t)

    if not running_tasks:
        return None, []

    # 返回最新的任务
    running_tasks.sort(key=lambda t: t.created_at, reverse=True)
    return running_tasks[0], running_tasks


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print_banner()

    try:
        # 初始化组件（只需要Chatbot和Scheduler）
        print("正在初始化系统...")

        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 1. Chatbot（直接初始化，输出自然显示）
        print("  [1/2] 初始化Chatbot...")
        bot = Chatbot(config_path="configs/chatbot_config.yaml")

        # 2. TaskScheduler（替换原来的Generator和LLM）
        print("  [2/2] 初始化TaskScheduler...")
        scheduler = TaskScheduler()

        # 3. Task Manager（用于查询任务状态）
        task_manager = get_task_manager()

        print("\n✅ 初始化完成！输入 /help 查看使用说明。\n")

        # 会话管理
        # 检查是否为SQLite模式
        is_sqlite_mode = bot.config["chatbot"]["memory"]["type"] == "sqlite"

        # 初始化会话ID
        if is_sqlite_mode:
            # SQLite模式：默认创建新会话
            existing_sessions = bot.list_sessions()

            # 始终创建新会话
            session_id = generate_session_id()

            if existing_sessions:
                print(f"📦 检测到 {len(existing_sessions)} 个历史会话")
                print("   使用 /sessions 查看所有会话")
                print("   使用 /switch <session_id> 切换到历史会话\n")

            print(f"📌 当前会话（新建）: {session_id}")
            print("   提示: 发送第一条消息后会自动保存到数据库\n")
        else:
            # 内存模式：使用固定会话ID
            session_id = "cli_session"
            print("💡 当前使用内存模式，会话不会持久化")
            print("   修改 configs/chatbot_config.yaml 中的 memory.type 为 'sqlite' 以启用会话管理\n")

        # 主循环
        while True:
            try:
                # 移除轮询检查（改为被动查询）

                # 获取用户输入（显示会话ID）
                if is_sqlite_mode:
                    # SQLite模式：显示简化的会话ID
                    session_display = session_id.split('_')[-1][:6]  # 只显示最后的UUID部分
                    prompt = f"\n👤 [{session_display}] 你: "
                else:
                    prompt = "\n👤 你: "

                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # ============================================================
                # 斜杠命令处理
                # ============================================================

                if user_input.startswith("/"):
                    cmd_parts = user_input.split()
                    cmd = cmd_parts[0].lower()

                    # /quit, /exit
                    if cmd in ["/quit", "/exit"]:
                        # 检查当前session是否有进行中的任务
                        task, running_tasks = get_running_task(session_id, task_manager)
                        if task:
                            confirm = input("\n⚠️  当前session有任务正在运行，退出后任务会继续在后台执行。确认退出？(y/n): ")
                            if confirm.lower() != 'y':
                                continue

                        print("\n👋 再见！（任务会继续在后台运行）\n")
                        break

                    # /help
                    elif cmd == "/help":
                        print_help()
                        continue

                    # /history
                    elif cmd == "/history":
                        print_history(bot, session_id)
                        continue

                    # /sessions
                    elif cmd == "/sessions":
                        print_sessions_list(bot, session_id, is_sqlite_mode)
                        continue

                    # /switch <session_id>
                    elif cmd == "/switch":
                        if len(cmd_parts) < 2:
                            print("\n用法: /switch <session_id>")
                            print("使用 /sessions 查看所有可用会话\n")
                            continue

                        new_session_id = cmd_parts[1]

                        # 验证会话是否存在（仅SQLite模式）
                        if is_sqlite_mode:
                            available_sessions = bot.list_sessions()
                            if new_session_id not in available_sessions:
                                print(f"\n❌ 会话 {new_session_id} 不存在")
                                print(f"可用会话: {', '.join(available_sessions)}\n")
                                continue

                        # 切换会话
                        session_id = new_session_id
                        history = bot.get_history(session_id)
                        print(f"\n✅ 已切换到会话: {session_id}")
                        print(f"   历史消息: {len(history)} 条")
                        print(f"   使用 /history 查看历史记录\n")
                        continue

                    # /new [session_name]
                    elif cmd == "/new":
                        # 可选：用户自定义会话名称
                        custom_name = cmd_parts[1] if len(cmd_parts) > 1 else None

                        # 生成新会话ID
                        new_session_id = generate_session_id(custom_name)

                        # 验证会话ID不重复（仅SQLite模式）
                        if is_sqlite_mode:
                            available_sessions = bot.list_sessions()
                            if new_session_id in available_sessions:
                                print(f"\n❌ 会话 {new_session_id} 已存在")
                                print(f"   请使用其他名称或使用 /switch {new_session_id}\n")
                                continue

                        # 切换到新会话
                        session_id = new_session_id
                        print(f"\n✅ 已切换到新会话: {session_id}")
                        if is_sqlite_mode:
                            print("   提示: 发送第一条消息后会自动保存到数据库\n")
                        else:
                            print()
                        continue

                    # /clear
                    elif cmd == "/clear":
                        os.system('cls' if os.name == 'nt' else 'clear')
                        continue

                    # /generate, /gen
                    elif cmd in ["/generate", "/gen"]:
                        print("\n🚀 已提交生成任务（后台子进程）")

                        # 启动子进程
                        task_id = scheduler.submit_task(
                            session_id=session_id,
                            history=bot.get_history(session_id)
                        )

                        print(f"   任务ID: {task_id}")
                        print(f"   使用 /logs 查看实时日志")
                        print(f"   使用 /status 查看任务状态")
                        print(f"   日志文件: logs/generation_tasks/{task_id}/task.log\n")
                        continue

                    # /status [task_id]
                    elif cmd == "/status":
                        # 支持两种用法：
                        # 1. /status - 自动选择当前session的最新任务（包括已完成）
                        # 2. /status <task_id> - 显式指定任务

                        if len(cmd_parts) > 1:
                            # 显式指定任务ID
                            task_id = cmd_parts[1]
                            task = task_manager.get_task(task_id)
                            if not task:
                                print(f"\n❌ 任务 {task_id} 不存在\n")
                                continue
                        else:
                            # 自动选择当前session的最近任务
                            task, recent_tasks = get_recent_task(session_id, task_manager)

                            if not task:
                                print("\n❌ 当前session没有任务\n")
                                print("   使用 /generate 创建新任务")
                                print("   使用 /tasks 查看所有任务\n")
                                continue

                            task_id = task.task_id

                            # 如果有多个任务，提示用户
                            if len(recent_tasks) > 1:
                                print(f"\n⚠️  当前session有 {len(recent_tasks)} 个任务，显示最新的：")
                                for i, t in enumerate(recent_tasks[:3], 1):
                                    marker = "👉" if t.task_id == task_id else "  "
                                    print(f"   {marker} {t.task_id} [{t.status.value}]{'  ← 正在显示' if marker == '👉' else ''}")
                                if len(recent_tasks) > 3:
                                    print(f"   ... 还有 {len(recent_tasks) - 3} 个任务")
                                print(f"\n   使用 /status <task_id> 查看其他任务")

                        print_task_status(task)

                        # 显示子进程状态
                        proc_status = scheduler.get_process_status(task_id)
                        print(f"  子进程状态: {proc_status}")
                        print()
                        continue

                    # /requirements [task_id]
                    elif cmd == "/requirements":
                        # 支持两种用法：
                        # 1. /requirements - 自动选择当前session的最新任务
                        # 2. /requirements <task_id> - 显式指定任务

                        if len(cmd_parts) > 1:
                            # 显式指定任务ID
                            task_id = cmd_parts[1]
                            task = task_manager.get_task(task_id)
                            if not task:
                                print(f"\n❌ 任务 {task_id} 不存在\n")
                                continue
                        else:
                            # 自动选择当前session的最近任务
                            task, recent_tasks = get_recent_task(session_id, task_manager)

                            if not task:
                                print("\n❌ 当前session没有任务\n")
                                print("   使用 /generate 创建新任务")
                                print("   使用 /tasks 查看所有任务\n")
                                continue

                            task_id = task.task_id

                            # 如果有多个任务，提示用户
                            if len(recent_tasks) > 1:
                                print(f"\n⚠️  当前session有 {len(recent_tasks)} 个任务，显示最新的：")
                                for i, t in enumerate(recent_tasks[:3], 1):
                                    marker = "👉" if t.task_id == task_id else "  "
                                    print(f"   {marker} {t.task_id}{'  ← 正在显示' if marker == '👉' else ''}")
                                if len(recent_tasks) > 3:
                                    print(f"   ... 还有 {len(recent_tasks) - 3} 个任务")
                                print(f"\n   使用 /requirements <task_id> 查看其他任务")

                        # 检查 requirements 文件是否存在
                        if not task.requirements_file.exists():
                            print(f"\n❌ 需求文件不存在: {task.requirements_file}")
                            print(f"   任务状态: {task.status.value}")
                            if task.status == TaskStatus.PENDING:
                                print(f"   提示: 任务尚未开始提取需求\n")
                            elif task.status == TaskStatus.EXTRACTING:
                                print(f"   提示: 任务正在提取需求中，请稍后再试\n")
                            else:
                                print(f"   提示: 任务可能已失败或被取消\n")
                            continue

                        # 读取并显示 requirements
                        try:
                            with open(task.requirements_file, 'r', encoding='utf-8') as f:
                                requirements = json.load(f)

                            print("\n" + "=" * 70)
                            print(f"任务需求: {task_id}")
                            print("=" * 70)
                            print(f"  任务状态: {task.status.value}")
                            print(f"  文件路径: {task.requirements_file}")
                            print("=" * 70)

                            # 格式化显示关键字段
                            if requirements.get("target_compound"):
                                print(f"\n🎯 目标化合物:")
                                print(f"  {requirements['target_compound']}")

                            if requirements.get("objective"):
                                print(f"\n📋 实验目标:")
                                print(f"  {requirements['objective']}")

                            if requirements.get("materials"):
                                print(f"\n🧪 材料列表:")
                                for mat in requirements["materials"]:
                                    if isinstance(mat, dict):
                                        mat_str = f"  • {mat.get('name', 'N/A')}"
                                        if mat.get('amount'):
                                            mat_str += f": {mat['amount']}"
                                        if mat.get('purity'):
                                            mat_str += f" (纯度: {mat['purity']})"
                                        print(mat_str)
                                    else:
                                        print(f"  • {mat}")

                            if requirements.get("constraints"):
                                print(f"\n⚠️  约束条件:")
                                for constraint in requirements["constraints"]:
                                    print(f"  • {constraint}")

                            if requirements.get("special_requirements"):
                                print(f"\n💡 特殊要求:")
                                print(f"  {requirements['special_requirements']}")

                            # 显示完整 JSON（折叠显示）
                            print(f"\n📄 完整JSON:")
                            print("-" * 70)
                            print(json.dumps(requirements, indent=2, ensure_ascii=False))
                            print("-" * 70)

                            # 操作提示
                            if task.status == TaskStatus.AWAITING_CONFIRM:
                                print(f"\n💡 操作提示:")
                                print(f"  # 编辑需求文件")
                                print(f"  nano {task.requirements_file}")
                                print(f"  vim {task.requirements_file}")
                                print(f"")
                                print(f"  # 确认继续生成")
                                print(f"  /confirm")
                            elif task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                                print(f"\n💡 其他命令:")
                                print(f"  /status {task_id}  # 查看任务状态")
                                if task.status == TaskStatus.COMPLETED:
                                    print(f"  /view {task_id}    # 查看生成的方案")

                            print()

                        except json.JSONDecodeError:
                            print(f"\n❌ 需求文件格式错误（无效的JSON）")
                            print(f"   文件路径: {task.requirements_file}\n")
                        except Exception as e:
                            print(f"\n❌ 读取需求文件时出错: {e}\n")

                        continue

                    # /logs [task_id] [--tail N]
                    elif cmd == "/logs":
                        # 支持两种用法：
                        # 1. /logs - 自动选择当前session的最新任务（包括已完成）
                        # 2. /logs <task_id> - 显式指定任务

                        target_task = None
                        if len(cmd_parts) > 1 and not cmd_parts[1].startswith("--"):
                            # 显式指定任务ID
                            target_task = cmd_parts[1]
                        else:
                            # 自动选择当前session的最近任务
                            task, _ = get_recent_task(session_id, task_manager)
                            if task:
                                target_task = task.task_id

                        if not target_task:
                            print("\n❌ 当前session没有任务")
                            print("   使用 /generate 创建新任务\n")
                            continue

                        # 解析 --tail 参数
                        tail = 50
                        if "--tail" in cmd_parts:
                            try:
                                tail_idx = cmd_parts.index("--tail")
                                tail = int(cmd_parts[tail_idx + 1])
                            except (IndexError, ValueError):
                                print("⚠️  --tail 参数格式错误，使用默认值50")

                        # 查看日志
                        logs = scheduler.get_logs(target_task, tail=tail)

                        # 获取任务信息
                        task = task_manager.get_task(target_task)
                        proc_status = scheduler.get_process_status(target_task)

                        # 判断是否为 feedback 流程
                        is_feedback_running = (
                            task and
                            task.status == TaskStatus.COMPLETED and
                            task.feedback_status in ["evaluating", "reflecting", "curating"] and
                            proc_status == "running"
                        )

                        print(f"\n📄 任务日志 (最后{tail}行): {target_task}")
                        if is_feedback_running:
                            print(f"    🔄 Feedback 子进程运行中 ({task.feedback_status})")
                        print("=" * 70)

                        if logs:
                            for log in logs:
                                print(log)
                        else:
                            print("(暂无日志)")
                            if is_feedback_running:
                                print("💡 提示: Feedback 子进程刚启动，日志可能还未生成，请稍后再查看")

                        print("=" * 70)

                        # 显示任务状态
                        if task:
                            if task.feedback_status:
                                print(f"任务状态: {task.status.value} (Feedback: {task.feedback_status})")
                            else:
                                print(f"任务状态: {task.status.value}")

                        # 显示子进程状态
                        print(f"子进程: {proc_status}")
                        print()
                        continue

                    # /confirm [task_id]
                    elif cmd == "/confirm":
                        # 支持两种用法：
                        # 1. /confirm - 自动选择当前session的AWAITING_CONFIRM任务
                        # 2. /confirm <task_id> - 显式指定任务

                        if len(cmd_parts) > 1:
                            # 显式指定任务ID
                            task_id = cmd_parts[1]
                            task = task_manager.get_task(task_id)
                            if not task:
                                print(f"\n❌ 任务 {task_id} 不存在\n")
                                continue
                        else:
                            # 自动选择当前session的待确认任务
                            tasks = task_manager.get_session_tasks(session_id)
                            awaiting_tasks = [t for t in tasks if t.status == TaskStatus.AWAITING_CONFIRM]

                            if not awaiting_tasks:
                                print("\n❌ 当前session没有待确认的任务\n")
                                continue

                            # 选择最新的待确认任务
                            awaiting_tasks.sort(key=lambda t: t.created_at, reverse=True)
                            task = awaiting_tasks[0]
                            task_id = task.task_id

                            # 如果有多个待确认任务，提示用户
                            if len(awaiting_tasks) > 1:
                                print(f"\n⚠️  当前session有 {len(awaiting_tasks)} 个待确认任务，确认最新的：")
                                for t in awaiting_tasks[:3]:
                                    marker = "👉" if t.task_id == task_id else "  "
                                    print(f"   {marker} {t.task_id}{'  ← 即将确认' if marker == '👉' else ''}")
                                if len(awaiting_tasks) > 3:
                                    print(f"   ... 还有 {len(awaiting_tasks) - 3} 个任务")
                                print(f"\n   使用 /confirm <task_id> 确认其他任务\n")

                        if task.status != TaskStatus.AWAITING_CONFIRM:
                            print(f"\n❌ 任务状态为 {task.status.value}，无需确认\n")
                            continue

                        # 确认需求，重新启动子进程（resume模式）
                        print(f"\n✅ 已确认需求 (任务: {task_id})，重新启动子进程...\n")

                        # 使用 scheduler.resume_task() 而非直接修改状态
                        success = scheduler.resume_task(task_id)

                        if success:
                            print(f"   子进程已启动，使用 /logs {task_id} 查看进度\n")
                        else:
                            print(f"   启动失败，请检查日志\n")

                        continue

                    # /cancel [task_id]
                    elif cmd == "/cancel":
                        # 支持两种用法：
                        # 1. /cancel - 自动选择当前session的最新运行中任务
                        # 2. /cancel <task_id> - 显式指定任务

                        if len(cmd_parts) > 1:
                            # 显式指定任务ID
                            task_id = cmd_parts[1]
                            task = task_manager.get_task(task_id)
                            if not task:
                                print(f"\n❌ 任务 {task_id} 不存在\n")
                                continue
                        else:
                            # 自动选择当前session的运行中任务
                            task, running_tasks = get_running_task(session_id, task_manager)

                            if not task:
                                print("\n❌ 当前session没有运行中的任务\n")
                                continue

                            task_id = task.task_id

                            # 如果有多个运行中任务，提示用户
                            if len(running_tasks) > 1:
                                print(f"\n⚠️  当前session有 {len(running_tasks)} 个运行中任务，取消最新的：")
                                for t in running_tasks[:3]:
                                    marker = "👉" if t.task_id == task_id else "  "
                                    print(f"   {marker} {t.task_id} [{t.status.value}]{'  ← 即将取消' if marker == '👉' else ''}")
                                if len(running_tasks) > 3:
                                    print(f"   ... 还有 {len(running_tasks) - 3} 个任务")
                                print(f"\n   使用 /cancel <task_id> 取消其他任务\n")

                        # 检查主任务状态
                        main_task_ended = task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

                        # 检查feedback流程状态
                        feedback_running = (
                            task.status == TaskStatus.COMPLETED and
                            task.feedback_status in ["evaluating", "reflecting", "curating"]
                        )

                        # 判断是否可取消
                        if main_task_ended and not feedback_running:
                            print(f"\n❌ 任务已结束 ({task.status.value})，无法取消\n")
                            continue

                        # 终止子进程（如果正在运行）
                        if feedback_running:
                            print(f"\n🔄 检测到feedback流程正在运行，正在终止...")

                        scheduler.terminate_task(task_id)

                        # 更新任务状态
                        if feedback_running:
                            # 取消feedback流程
                            task.feedback_status = "cancelled"
                            task.feedback_error = "用户取消"
                            print(f"✅ 已取消feedback流程 (主任务仍为COMPLETED)")
                        else:
                            # 取消主任务
                            task.status = TaskStatus.CANCELLED
                            print(f"✅ 已取消任务 {task_id}")

                        task_manager._save_task(task)
                        print()
                        continue

                    # /retry <task_id> [options]
                    elif cmd == "/retry":
                        if len(cmd_parts) < 2:
                            print("\n用法: /retry <task_id> [options]\n")
                            print("选项:")
                            print("  --clean             完全重试（清理所有文件，从头开始）")
                            print("  --force             强制重试（FAILED: 忽略次数限制; COMPLETED: 允许重新生成）")
                            print("  --stage <s>         手动指定从哪个阶段重试")
                            print("                      简写: generate, feedback")
                            print("                      详细: extracting, generating, evaluating, reflecting, curating")
                            print("  --mode <m>          覆盖评估模式（当 --stage 为 feedback 相关阶段时有效）")
                            print("                      可选值: auto, llm_judge, human")
                            print("  --keep-playbook     保留已生成的 playbook bullets（默认行为）")
                            print("  --discard-playbook  丢弃已生成的 playbook bullets，回滚 playbook\n")
                            print("示例:")
                            print("  /retry abc123 --force --stage generate")
                            print("  /retry abc123 --force --stage feedback --mode llm_judge")
                            print("  /retry abc123 --force --stage generate --discard-playbook\n")
                            continue

                        task_id = cmd_parts[1]

                        # 解析选项
                        clean = "--clean" in cmd_parts
                        force = "--force" in cmd_parts
                        force_stage = None
                        override_mode = None
                        keep_playbook = True  # 默认保留

                        if "--stage" in cmd_parts:
                            try:
                                stage_idx = cmd_parts.index("--stage")
                                force_stage = cmd_parts[stage_idx + 1]
                            except IndexError:
                                print("⚠️  --stage 参数缺少值\n")
                                continue

                        if "--mode" in cmd_parts:
                            try:
                                mode_idx = cmd_parts.index("--mode")
                                override_mode = cmd_parts[mode_idx + 1]
                                if override_mode not in ["auto", "llm_judge", "human"]:
                                    print(f"⚠️  不支持的评估模式: {override_mode}")
                                    print("   请使用: auto, llm_judge, 或 human\n")
                                    continue
                            except IndexError:
                                print("⚠️  --mode 参数缺少值\n")
                                continue

                        # 解析 --discard-playbook
                        if "--discard-playbook" in cmd_parts:
                            keep_playbook = False

                        # 使用 RetryCommandHandler
                        from workflow.command_handler import RetryCommandHandler
                        retry_handler = RetryCommandHandler(scheduler)

                        success = retry_handler.handle(
                            task_id=task_id,
                            clean=clean,
                            force=force,
                            force_stage=force_stage,
                            override_mode=override_mode,
                            keep_playbook=keep_playbook
                        )

                        print()
                        continue

                    # /view <task_id>
                    elif cmd == "/view":
                        if len(cmd_parts) < 2:
                            print("\n用法: /view <task_id>\n")
                            continue

                        task_id = cmd_parts[1]
                        task = task_manager.get_task(task_id)

                        if not task:
                            print(f"\n❌ 任务 {task_id} 不存在\n")
                            continue

                        if task.status != TaskStatus.COMPLETED:
                            print(f"\n❌ 任务未完成 (状态: {task.status.value})\n")
                            continue

                        # 读取并格式化显示方案
                        if task.plan_file.exists():
                            with open(task.plan_file, 'r', encoding='utf-8') as f:
                                plan_dict = json.load(f)

                            plan = ExperimentPlan(**plan_dict)
                            formatted = format_plan_output(plan, task.metadata)
                            print(formatted)
                        else:
                            print(f"\n❌ 方案文件不存在: {task.plan_file}\n")

                        continue

                    # /tasks
                    elif cmd == "/tasks":
                        tasks = task_manager.get_all_tasks()

                        if not tasks:
                            print("\n暂无任务\n")
                            continue

                        print("\n" + "=" * 70)
                        print("所有任务列表")
                        print("=" * 70)

                        tasks.sort(key=lambda t: t.created_at, reverse=True)

                        # Feedback状态图标
                        feedback_icons = {
                            "pending": "⏳",
                            "evaluating": "📊",
                            "reflecting": "💭",
                            "curating": "📝",
                            "completed": "🎓",
                            "failed": "❌",
                            "cancelled": "🚫"
                        }

                        for task in tasks:
                            # 主任务状态图标
                            icon = {
                                TaskStatus.COMPLETED: "✅",
                                TaskStatus.FAILED: "❌",
                                TaskStatus.AWAITING_CONFIRM: "⏸️",
                                TaskStatus.GENERATING: "⚙️",
                                TaskStatus.EXTRACTING: "🔍",
                                TaskStatus.RETRIEVING: "📚",
                                TaskStatus.CANCELLED: "🚫"
                            }.get(task.status, "🔄")

                            # 任务状态显示（包含feedback状态）
                            if task.status == TaskStatus.COMPLETED and task.feedback_status:
                                feedback_icon = feedback_icons.get(task.feedback_status, "❓")
                                # 根据feedback状态显示不同信息
                                if task.feedback_status == "completed":
                                    status_display = f"{task.status.value} (🎓 Feedback完成)"
                                elif task.feedback_status == "failed":
                                    status_display = f"{task.status.value} (❌ Feedback失败)"
                                elif task.feedback_status == "cancelled":
                                    status_display = f"{task.status.value} (🚫 Feedback取消)"
                                elif task.feedback_status in ["evaluating", "reflecting", "curating"]:
                                    status_display = f"{task.status.value} ({feedback_icon} Feedback: {task.feedback_status})"
                                else:
                                    status_display = task.status.value
                            else:
                                status_display = task.status.value

                            print(f"\n  {icon} {task.task_id} [{status_display}]")
                            print(f"     会话: {task.session_id}")
                            print(f"     时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                        print()
                        continue

                    # /feedback <task_id> [--mode auto|llm_judge|human]
                    elif cmd == "/feedback":
                        if len(cmd_parts) < 2:
                            print("\n用法: /feedback <task_id> [--mode <evaluation_mode>]")
                            print("\n评估模式说明:")
                            print("  auto       - 基于规则的自动评估（快速，免费）")
                            print("  llm_judge  - LLM评估（准确，消耗tokens）")
                            print("  human      - 人工评分（待实现）")

                            # 显示配置的默认模式
                            from utils.config_loader import get_ace_config
                            ace_config = get_ace_config()
                            default_mode = ace_config.training.feedback_source
                            print(f"\n💡 默认模式（configs/ace_config.yaml）: {default_mode}")
                            print("\n示例:")
                            print("  /feedback abc123              # 使用配置默认模式")
                            print("  /feedback abc123 --mode auto  # 指定auto模式\n")
                            continue

                        task_id = cmd_parts[1]

                        # 解析评估模式（如果不指定，传None，由worker从配置读取）
                        evaluation_mode = None  # 默认从配置读取

                        if "--mode" in cmd_parts:
                            try:
                                idx = cmd_parts.index("--mode")
                                evaluation_mode = cmd_parts[idx + 1]
                                if evaluation_mode not in ["auto", "llm_judge", "human"]:
                                    print(f"\n❌ 不支持的评估模式: {evaluation_mode}")
                                    print("   请使用: auto, llm_judge, 或 human\n")
                                    continue
                            except IndexError:
                                print("\n❌ --mode 参数缺少值\n")
                                continue

                        # 确定并存储评估模式
                        task = task_manager.get_task(task_id)
                        if not task:
                            print(f"\n❌ 任务 {task_id} 不存在\n")
                            continue

                        # 确定实际使用的模式
                        if evaluation_mode is None:
                            from utils.config_loader import get_ace_config
                            ace_config = get_ace_config()
                            actual_mode = ace_config.training.feedback_source
                        else:
                            actual_mode = evaluation_mode

                        # 存储到任务
                        task.feedback_mode = actual_mode
                        task_manager._save_task(task)

                        # 显示即将使用的模式
                        if evaluation_mode is None:
                            print(f"\n🚀 启动反馈训练流程（使用配置默认: {actual_mode}）")
                        else:
                            print(f"\n🚀 启动反馈训练流程（{actual_mode}模式）")

                        # 提交反馈任务
                        success = scheduler.submit_feedback_task(task_id, actual_mode)

                        if success:
                            print(f"   任务ID: {task_id}")
                            print(f"   使用 /logs {task_id} 查看实时日志")
                            print(f"   使用 /status {task_id} 查看反馈状态\n")
                        else:
                            print("   启动失败，请检查任务状态\n")

                        continue

                    # 未知命令
                    else:
                        print(f"\n❌ 未知命令: {cmd}")
                        print("   输入 /help 查看可用命令\n")
                        continue

                # ============================================================
                # 正常对话（流式响应）
                # ============================================================

                thinking_shown = False
                content_started = False
                current_content = []

                for event in bot.stream_chat(user_input, session_id=session_id, show_thinking=True):
                    event_type = event.get("type")
                    data = event.get("data", "")

                    if event_type == "thinking":
                        if not thinking_shown:
                            print("\n💭 思考中: ", end="", flush=True)
                            thinking_shown = True
                        print(f"\033[90m{data}\033[0m", end="", flush=True)

                    elif event_type == "tool_call":
                        print(f"\n🔧 调用工具: {data}", flush=True)

                    elif event_type == "tool_result":
                        preview = data[:100] + "..." if len(data) > 100 else data
                        print(f"\033[90m   结果: {preview}\033[0m", flush=True)

                    elif event_type == "content":
                        if not content_started:
                            if thinking_shown:
                                print()
                            print("\n🤖 助手: ", end="", flush=True)
                            content_started = True

                        current_text = "".join(current_content)
                        if data.startswith(current_text):
                            new_token = data[len(current_text):]
                            print(new_token, end="", flush=True)
                            current_content.append(new_token)
                        else:
                            print(data, end="", flush=True)
                            current_content = [data]

                if not content_started:
                    print()
                else:
                    print()

            except KeyboardInterrupt:
                print("\n\n👋 程序被中断，正在退出...")
                print("   任务会继续在后台运行\n")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}\n")
                import traceback
                traceback.print_exc()
                print("你可以继续对话或输入 /quit 退出。")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # 清理资源
        try:
            bot.cleanup()
        except:
            pass

        try:
            scheduler.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()
