#!/usr/bin/env python3
"""
完整工作流CLI - Chatbot + Generator + 任务管理

支持斜杠命令：
- /generate, /gen   - 生成实验方案（后台执行）
- /status           - 查看任务状态
- /confirm          - 确认需求，继续生成
- /cancel           - 取消任务
- /view <task_id>   - 查看生成的方案
- /tasks            - 列出所有任务
- /history          - 查看对话历史
- /clear            - 清屏
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
from workflow.command_handler import GenerateCommandHandler
from workflow.task_manager import get_task_manager, TaskStatus, GenerationTask
from ace_framework.generator.generator import create_generator
from ace_framework.playbook.schemas import ExperimentPlan
from utils.llm_provider import QwenProvider


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


def print_help():
    """打印帮助信息"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                     使用说明                                ║
╚════════════════════════════════════════════════════════════╝

📋 命令列表:
  /generate, /gen  - 根据对话历史生成实验方案（后台执行）
  /status          - 查看当前任务状态和文件路径
  /confirm         - 确认需求，继续生成方案
  /cancel          - 取消当前任务
  /view <task_id>  - 查看生成的方案（格式化显示）
  /tasks           - 列出所有任务
  /history         - 查看当前会话对话历史
  /clear           - 清屏
  /help            - 显示此帮助信息
  /quit, /exit     - 退出程序（任务继续在后台运行）

💡 工作流程:
  1. 与助手自然对话，描述你的实验需求
  2. 输入 /generate 触发方案生成（后台执行）
  3. 系统提取需求后会提醒你确认
  4. 查看需求文件，如需修改可直接编辑
  5. 输入 /confirm 确认，系统继续生成方案
  6. 使用 /status 或 /view 查看结果

🎯 示例对话:
  你: 我想合成阿司匹林
  助手: 好的！让我了解一些细节...
  你: 用水杨酸和乙酸酐，2小时内完成
  助手: 明白了。还有其他要求吗？
  你: /generate              ← 触发生成
  [系统后台提取需求]
  [系统提醒需要确认]
  你: /status                ← 查看需求文件路径
  你: /confirm               ← 确认继续
  [系统生成方案]
  你: /view <task_id>        ← 查看方案
  你: 第3步的温度可以调低吗？  ← 继续对话
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

    icon = status_icons.get(task.status, "❓")

    print("\n" + "=" * 70)
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
        print(f"\n✅ 任务完成!")
        print(f"  耗时: {task.metadata.get('duration', 0):.2f}s")
        print(f"  Tokens: {task.metadata.get('total_tokens', 0)}")
        print(f"\n💡 查看方案:")
        print(f"  cat {task.plan_file}  # JSON格式")
        print(f"  /view {task.task_id}  # 格式化显示")

    elif task.status == TaskStatus.FAILED:
        print(f"\n❌ 失败原因: {task.error}")
        print(f"\n💡 查看日志:")
        print(f"  cat {task.log_file}")

    print()


def check_and_notify_pending_tasks(task_manager, current_task_id):
    """检查并主动提醒待确认的任务"""
    if not current_task_id:
        return

    task = task_manager.get_task(current_task_id)
    if not task:
        return

    # 如果任务进入AWAITING_CONFIRM状态，主动提醒
    if task.status == TaskStatus.AWAITING_CONFIRM:
        # 使用颜色高亮提示
        print("\n" + "=" * 70)
        print("\033[93m⏸️  任务需要确认！\033[0m")  # 黄色
        print("=" * 70)
        print(f"  任务ID: {task.task_id}")
        print(f"  状态: {task.status.value}")
        print(f"\n📋 需求已提取，文件路径:")
        print(f"  {task.requirements_file}")
        print(f"\n💡 接下来可以:")
        print(f"  1. 查看需求: cat {task.requirements_file}")
        print(f"  2. 修改需求: nano/vim {task.requirements_file}")
        print(f"  3. 确认继续: /confirm")
        print(f"  4. 取消任务: /cancel")
        print("=" * 70 + "\n")


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


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print_banner()

    try:
        # 初始化组件
        print("正在初始化系统...")

        # 1. Chatbot
        print("  [1/3] 初始化Chatbot...")
        bot = Chatbot(config_path="configs/chatbot_config.yaml")

        # 2. LLM Provider
        print("  [2/3] 初始化LLM Provider...")
        llm_provider = QwenProvider(
            model_name="qwen-max",
            temperature=0.7,
            max_tokens=4096
        )

        # 3. Generator
        print("  [3/3] 初始化Generator...")
        generator = create_generator(
            playbook_path="data/playbooks/chemistry_playbook.json",
            llm_provider=llm_provider
        )

        # 4. Command Handler
        cmd_handler = GenerateCommandHandler(
            chatbot=bot,
            generator=generator,
            llm_provider=llm_provider
        )

        # 5. Task Manager
        task_manager = get_task_manager()

        print("\n✅ 初始化完成！输入 /help 查看使用说明。\n")

        session_id = "cli_session"
        current_task_id = None
        last_notification_check = 0

        # 主循环
        while True:
            try:
                # ============================================================
                # 定期检查任务状态（每隔5秒检查一次，避免过于频繁）
                # ============================================================
                current_time = time.time()
                if current_task_id and (current_time - last_notification_check > 5):
                    check_and_notify_pending_tasks(task_manager, current_task_id)
                    last_notification_check = current_time

                # 获取用户输入
                user_input = input("\n👤 你: ").strip()

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
                        # 检查是否有进行中的任务
                        if current_task_id:
                            task = task_manager.get_task(current_task_id)
                            if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                                confirm = input("\n⚠️  有任务正在运行，退出后任务会继续在后台执行。确认退出？(y/n): ")
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

                    # /clear
                    elif cmd == "/clear":
                        os.system('cls' if os.name == 'nt' else 'clear')
                        continue

                    # /generate, /gen
                    elif cmd in ["/generate", "/gen"]:
                        print("\n🚀 已提交生成任务（后台执行）")

                        task_id = cmd_handler.handle(session_id)
                        current_task_id = task_id

                        print(f"   任务ID: {task_id}")
                        print(f"   使用 /status 查看进度")
                        print(f"   日志: logs/generation_tasks/{task_id}/task.log\n")
                        continue

                    # /status
                    elif cmd == "/status":
                        if not current_task_id:
                            print("\n❌ 没有活跃的任务\n")
                            print("   使用 /generate 创建新任务")
                            print("   使用 /tasks 查看所有任务\n")
                            continue

                        task = task_manager.get_task(current_task_id)
                        if not task:
                            print(f"\n❌ 任务 {current_task_id} 不存在\n")
                            continue

                        print_task_status(task)
                        continue

                    # /confirm
                    elif cmd == "/confirm":
                        if not current_task_id:
                            print("\n❌ 没有待确认的任务\n")
                            continue

                        task = task_manager.get_task(current_task_id)
                        if not task:
                            print(f"\n❌ 任务 {current_task_id} 不存在\n")
                            continue

                        if task.status != TaskStatus.AWAITING_CONFIRM:
                            print(f"\n❌ 任务状态为 {task.status.value}，无需确认\n")
                            continue

                        # 确认需求，继续生成（通过修改任务状态）
                        task.status = TaskStatus.RETRIEVING  # 解除暂停
                        task_manager._save_task(task)
                        print("\n✅ 已确认需求，任务继续执行...\n")
                        continue

                    # /cancel
                    elif cmd == "/cancel":
                        if not current_task_id:
                            print("\n❌ 没有可取消的任务\n")
                            continue

                        task = task_manager.get_task(current_task_id)
                        if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                            task.status = TaskStatus.CANCELLED
                            task_manager._save_task(task)
                            print(f"\n✅ 已取消任务 {current_task_id}\n")
                            current_task_id = None
                        else:
                            print(f"\n❌ 任务已结束，无法取消\n")
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

                        for task in tasks:
                            icon = {
                                TaskStatus.COMPLETED: "✅",
                                TaskStatus.FAILED: "❌",
                                TaskStatus.AWAITING_CONFIRM: "⏸️",
                                TaskStatus.GENERATING: "⚙️",
                                TaskStatus.EXTRACTING: "🔍",
                                TaskStatus.RETRIEVING: "📚"
                            }.get(task.status, "🔄")

                            print(f"\n  {icon} {task.task_id} [{task.status.value}]")
                            print(f"     会话: {task.session_id}")
                            print(f"     时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                        print()
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


if __name__ == "__main__":
    main()
