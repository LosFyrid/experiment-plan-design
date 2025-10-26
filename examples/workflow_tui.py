#!/usr/bin/env python3
"""化学实验方案设计助手 - TUI版本

基于textual的三栏布局界面：
- 左侧：任务列表（实时更新）
- 中间：对话区（流式聊天）
- 右侧：任务详情
- 底部：系统日志
"""

import sys
import time
import threading
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, RichLog, Static,
    DataTable, Button, Label
)
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding

from chatbot.chatbot import Chatbot
from workflow.task_scheduler import TaskScheduler
from workflow.task_manager import get_task_manager, TaskStatus


# 状态图标映射
STATUS_ICONS = {
    "pending": "⏳",
    "extracting": "🔍",
    "awaiting_confirm": "⏸️",
    "retrieving": "📚",
    "generating": "⚙️",
    "completed": "✅",
    "failed": "❌",
    "cancelled": "🚫"
}


class ChemistryAssistantTUI(App):
    """化学实验方案设计助手 TUI"""

    CSS = """
    /* 整体布局 */
    #main-container {
        height: 80%;
    }

    #log-container {
        height: 28%;
        border-top: solid green;
    }

    /* 三栏布局 */
    #task-panel {
        width: 25%;
        border-right: solid blue;
    }

    #chat-panel {
        width: 45%;
        border-right: solid blue;
    }

    #detail-panel {
        width: 30%;
    }

    /* 任务列表 */
    #task-list {
        height: 100%;
    }

    DataTable {
        height: 1fr;
    }

    /* 对话区 */
    #chat-display {
        height: 1fr;
        border: solid blue;
    }

    #chat-display:focus {
        border: solid green;
    }

    #streaming-display {
        min-height: 0;
        max-height: 20;
        overflow-y: auto;
        border: solid yellow;
        padding: 1;
    }

    #chat-input {
        dock: bottom;
        height: 3;
    }

    /* 任务详情 */
    #detail-content {
        height: 100%;
        border: solid blue;
    }

    #detail-content:focus {
        border: solid green;
    }

    /* 系统日志 */
    #system-log {
        height: 100%;
        border: solid blue;
    }

    #system-log:focus {
        border: solid green;
    }

    /* 标题 */
    Static.panel-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", priority=True),
        ("q", "quit", "退出"),
        ("ctrl+l", "clear_chat", "清空对话"),
        ("f1", "show_help_overlay", "帮助"),
        ("tab", "focus_next", "切换焦点"),
        ("shift+tab", "focus_previous", "反向焦点"),
    ]

    def __init__(self):
        super().__init__()
        self.session_id = f"tui_session_{uuid.uuid4().hex[:8]}"
        self.selected_task_id: Optional[str] = None
        self.running = True

        # 业务组件（初始化在 on_mount 中）
        self.chatbot: Optional[Chatbot] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.task_manager = None

    def compose(self) -> ComposeResult:
        """构建UI布局"""
        yield Header()

        # 主容器（三栏布局）
        with Horizontal(id="main-container"):
            # 左侧：任务列表
            with Vertical(id="task-panel"):
                yield Static("📋 任务列表", classes="panel-title")
                yield DataTable(id="task-list")

            # 中间：对话区
            with Vertical(id="chat-panel"):
                yield Static("💬 对话区 (Shift+鼠标可选择复制)", classes="panel-title")
                yield RichLog(
                    id="chat-display",
                    highlight=True,
                    markup=True,
                    wrap=True
                )
                yield Static(
                    id="streaming-display",
                    markup=True
                )
                yield Input(
                    placeholder="输入消息或斜杠命令 (/help 查看帮助)...",
                    id="chat-input"
                )

            # 右侧：任务详情
            with Vertical(id="detail-panel"):
                yield Static("📊 任务详情 (Shift+鼠标可选择复制)", classes="panel-title")
                yield RichLog(
                    id="detail-content",
                    highlight=True,
                    markup=True,
                    wrap=True
                )

        # 底部：系统日志
        with Vertical(id="log-container"):
            yield Static("🔧 系统日志 (Shift+鼠标可选择复制)", classes="panel-title")
            yield RichLog(
                id="system-log",
                highlight=True,
                markup=True,
                wrap=True
            )

        yield Footer()

    def on_mount(self):
        """启动时初始化"""
        system_log = self.query_one("#system-log", RichLog)
        chat_display = self.query_one("#chat-display", RichLog)

        system_log.write("[yellow]正在初始化系统...[/yellow]")

        try:
            # 初始化业务组件（不阻塞UI）
            init_thread = threading.Thread(
                target=self._init_components,
                daemon=True
            )
            init_thread.start()

        except Exception as e:
            system_log.write(f"[red]初始化失败: {e}[/red]")

    def _init_components(self):
        """后台线程：初始化业务组件"""
        system_log = self.query_one("#system-log", RichLog)

        try:
            # 1. Chatbot（MOSES会在内部初始化）
            self.call_from_thread(
                system_log.write,
                "[yellow][1/3] 初始化Chatbot...[/yellow]"
            )

            self.chatbot = Chatbot(config_path="configs/chatbot_config.yaml")

            # 注册MOSES初始化完成回调
            def on_moses_ready(summary):
                self.call_from_thread(
                    system_log.write,
                    f"[green]✓ MOSES就绪: {summary['classes']} classes, "
                    f"{summary['data_properties']} data props, "
                    f"{summary['object_properties']} object props[/green]"
                )

            # 如果MOSES已经初始化完成，直接调用回调
            if self.chatbot.moses_wrapper._initialized:
                try:
                    from src.external.MOSES.config.settings import ONTOLOGY_SETTINGS
                    summary = {
                        "classes": len(list(ONTOLOGY_SETTINGS.ontology.classes())),
                        "data_properties": len(list(ONTOLOGY_SETTINGS.ontology.data_properties())),
                        "object_properties": len(list(ONTOLOGY_SETTINGS.ontology.object_properties()))
                    }
                    on_moses_ready(summary)
                except:
                    pass

            self.call_from_thread(
                system_log.write,
                "[green]✓ Chatbot初始化完成[/green]"
            )

            # 2. TaskScheduler
            self.call_from_thread(
                system_log.write,
                "[yellow][2/3] 初始化TaskScheduler...[/yellow]"
            )

            self.scheduler = TaskScheduler()

            self.call_from_thread(
                system_log.write,
                "[green]✓ TaskScheduler初始化完成[/green]"
            )

            # 3. TaskManager
            self.call_from_thread(
                system_log.write,
                "[yellow][3/3] 初始化TaskManager...[/yellow]"
            )

            self.task_manager = get_task_manager()

            self.call_from_thread(
                system_log.write,
                "[green]✓ TaskManager初始化完成[/green]"
            )

            # 初始化完成
            self.call_from_thread(
                system_log.write,
                "\n[bold green]✅ 系统初始化完成！[/bold green]"
            )

            self.call_from_thread(
                system_log.write,
                f"[dim]会话ID: {self.session_id}[/dim]\n"
            )

            # 显示欢迎消息
            chat_display = self.query_one("#chat-display", RichLog)
            self.call_from_thread(
                chat_display.write,
                "[bold cyan]🧪 欢迎使用化学实验方案设计助手！[/bold cyan]\n"
            )
            self.call_from_thread(
                chat_display.write,
                "请描述你的实验需求，或输入 [yellow]/help[/yellow] 查看帮助。\n"
            )

            # 启动任务监控线程
            self.call_from_thread(self._start_task_monitor)

        except Exception as e:
            self.call_from_thread(
                system_log.write,
                f"[red]初始化失败: {e}[/red]"
            )
            import traceback
            self.call_from_thread(
                system_log.write,
                f"[dim]{traceback.format_exc()}[/dim]"
            )

    def _start_task_monitor(self):
        """启动任务监控线程"""
        # 初始化任务列表表格
        task_table = self.query_one("#task-list", DataTable)
        task_table.add_columns("状态", "任务ID", "标题", "时间")

        # 启动监控线程
        monitor_thread = threading.Thread(
            target=self._monitor_tasks,
            daemon=True
        )
        monitor_thread.start()

    def _monitor_tasks(self):
        """后台线程：监控任务状态（每2秒刷新）"""
        while self.running:
            try:
                if self.task_manager:
                    # 获取当前会话的任务（自动刷新缓存）
                    tasks = self.task_manager.get_session_tasks(self.session_id)

                    # 更新任务列表UI
                    self.call_from_thread(self._update_task_list_ui, tasks)

            except Exception as e:
                pass  # 静默失败

            time.sleep(2)  # 每2秒刷新

    def _update_task_list_ui(self, tasks):
        """更新任务列表UI"""
        task_table = self.query_one("#task-list", DataTable)

        # 清空并重新填充
        task_table.clear()

        # 按创建时间倒序排列（最新的在前）
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        for task in tasks:
            icon = STATUS_ICONS.get(task.status.value, "❓")
            task_id_short = task.task_id[:8]

            # 获取标题（从metadata或默认值）
            title = task.metadata.get("title", "生成中...")
            if len(title) > 20:
                title = title[:20] + "..."

            # 时间格式化
            time_str = task.created_at.strftime("%m-%d %H:%M")

            # 添加行（可点击选中）
            task_table.add_row(icon, task_id_short, title, time_str)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """点击任务列表时显示详情"""
        task_table = self.query_one("#task-list", DataTable)
        row = event.row_key

        # 获取任务ID（从表格第二列）
        task_id_short = task_table.get_row(row)[1]

        # 找到完整任务ID
        tasks = self.task_manager.get_session_tasks(self.session_id)
        for task in tasks:
            if task.task_id.startswith(task_id_short):
                self.selected_task_id = task.task_id
                self._show_task_detail(task)
                break

    def _show_task_detail(self, task):
        """显示任务详情"""
        detail_content = self.query_one("#detail-content", RichLog)
        detail_content.clear()

        # 任务基本信息
        detail_content.write(f"[bold]任务ID:[/bold] {task.task_id}")
        detail_content.write(f"[bold]状态:[/bold] {STATUS_ICONS.get(task.status.value)} {task.status.value.upper()}")
        detail_content.write(f"[bold]创建时间:[/bold] {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        detail_content.write("")

        # 文件状态
        detail_content.write("[bold]📁 数据文件:[/bold]")
        if task.requirements_file.exists():
            detail_content.write("  ✅ 需求已提取")
        else:
            detail_content.write("  ⏳ 需求未提取")

        if task.templates_file.exists():
            detail_content.write("  ✅ 模板已检索")

        if task.plan_file.exists():
            detail_content.write("  ✅ 方案已生成")

        detail_content.write("")

        # 元数据
        if task.metadata:
            detail_content.write("[bold]📊 元数据:[/bold]")
            for key, value in task.metadata.items():
                detail_content.write(f"  {key}: {value}")

        # 错误信息
        if task.error:
            detail_content.write("")
            detail_content.write(f"[bold red]❌ 错误:[/bold red]")
            detail_content.write(f"[red]{task.error}[/red]")

        # 操作提示
        detail_content.write("")
        detail_content.write("[bold]💡 操作:[/bold]")

        if task.status == TaskStatus.AWAITING_CONFIRM:
            detail_content.write("  [yellow]/confirm[/yellow] - 确认需求，继续生成")
            detail_content.write("  [yellow]/cancel[/yellow] - 取消任务")

        detail_content.write(f"  [yellow]/logs {task.task_id[:8]}[/yellow] - 查看日志")

        if task.status == TaskStatus.COMPLETED:
            detail_content.write(f"  [yellow]/view {task.task_id[:8]}[/yellow] - 查看方案")

    async def on_input_submitted(self, event: Input.Submitted):
        """处理用户输入"""
        user_input = event.value.strip()

        if not user_input:
            return

        # 清空输入框
        input_widget = self.query_one("#chat-input", Input)
        input_widget.value = ""

        chat_display = self.query_one("#chat-display", RichLog)
        system_log = self.query_one("#system-log", RichLog)

        # 显示用户输入
        chat_display.write(f"\n[bold cyan]👤 你:[/bold cyan] {user_input}\n")

        # 处理斜杠命令
        if user_input.startswith("/"):
            await self._handle_command(user_input, chat_display, system_log)
        else:
            # 正常对话
            await self._handle_chat(user_input, chat_display)

    async def _handle_command(self, command: str, chat_display, system_log):
        """处理斜杠命令"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd in ["/help", "/h"]:
            self._show_help(chat_display)

        elif cmd in ["/generate", "/gen"]:
            self._handle_generate(chat_display, system_log)

        elif cmd == "/confirm":
            self._handle_confirm(chat_display, system_log)

        elif cmd == "/cancel":
            self._handle_cancel(chat_display, system_log)

        elif cmd == "/logs":
            task_id = parts[1] if len(parts) > 1 else None
            self._handle_logs(task_id, chat_display, system_log)

        elif cmd == "/view":
            if len(parts) < 2:
                chat_display.write("[red]用法: /view <task_id>[/red]\n")
            else:
                self._handle_view(parts[1], chat_display)

        elif cmd == "/tasks":
            self._handle_tasks(chat_display)

        elif cmd == "/history":
            self._handle_history(chat_display)

        elif cmd == "/clear":
            self._handle_clear_history(chat_display, system_log)

        else:
            chat_display.write(f"[red]未知命令: {cmd}[/red]")
            chat_display.write("[yellow]输入 /help 查看可用命令[/yellow]\n")

    def _show_help(self, chat_display):
        """显示帮助信息"""
        help_text = """
[bold cyan]📋 可用命令:[/bold cyan]

[yellow]/generate, /gen[/yellow]   - 根据对话历史生成实验方案
[yellow]/status[/yellow]           - 查看当前任务状态
[yellow]/confirm[/yellow]          - 确认需求，继续生成
[yellow]/cancel[/yellow]           - 取消当前任务
[yellow]/view <task_id>[/yellow]   - 查看生成的方案
[yellow]/logs <task_id>[/yellow]   - 查看任务日志
[yellow]/tasks[/yellow]            - 列出所有任务
[yellow]/history[/yellow]          - 查看对话历史
[yellow]/clear[/yellow]            - 清空对话历史（解决工具调用错误）
[yellow]/help[/yellow]             - 显示此帮助
[yellow]/quit, q[/yellow]          - 退出程序

[bold cyan]⌨️  快捷键:[/bold cyan]

[yellow]Tab / Shift+Tab[/yellow]   - 在面板间切换焦点（聚焦后边框变绿）
[yellow]F1[/yellow]                - 显示此帮助
[yellow]Ctrl+L[/yellow]            - 清空对话区
[yellow]Ctrl+C, q[/yellow]         - 退出程序

[bold cyan]📋 复制文本:[/bold cyan]

[bold yellow]方法：使用 Shift+鼠标 选择文本[/bold yellow]

1. [yellow]按住 Shift 键[/yellow]
2. [yellow]鼠标拖动[/yellow]选择文本（绕过TUI应用捕获）
3. 复制（取决于你的终端）：
   • [yellow]Ctrl+Shift+C[/yellow] (大多数Linux终端)
   • [yellow]Cmd+C[/yellow] (macOS iTerm2/Terminal)
   • [yellow]鼠标右键 → 复制[/yellow] (Windows Terminal)

[dim]注意：不要按Tab聚焦，直接 Shift+鼠标拖动即可[/dim]

[bold cyan]📁 备用方案:[/bold cyan]

如果Shift+鼠标不工作，任务日志文件位于：
[dim]logs/generation_tasks/<task_id>/task.log[/dim]

可以直接用终端命令复制：
[dim]cat logs/generation_tasks/<task_id>/task.log | xclip -sel c  # Linux[/dim]
[dim]cat logs/generation_tasks/<task_id>/task.log | pbcopy        # macOS[/dim]

[bold cyan]💡 提示:[/bold cyan]
- 左侧任务列表会自动更新（每2秒）
- 点击任务可查看详细信息
- 任务ID可以只输入前8位
"""
        chat_display.write(help_text)

    def action_show_help_overlay(self):
        """F1快捷键显示帮助"""
        chat_display = self.query_one("#chat-display", RichLog)
        self._show_help(chat_display)

    def _handle_generate(self, chat_display, system_log):
        """处理生成命令"""
        if not self.chatbot or not self.scheduler:
            chat_display.write("[red]系统未初始化完成[/red]\n")
            return

        # 获取对话历史
        history = self.chatbot.get_history(self.session_id)

        if not history:
            chat_display.write("[red]请先描述你的实验需求[/red]\n")
            return

        # 提交任务
        task_id = self.scheduler.submit_task(self.session_id, history)

        chat_display.write(f"[green]✅ 已提交生成任务[/green]")
        chat_display.write(f"[dim]任务ID: {task_id}[/dim]")
        chat_display.write(f"[yellow]使用 /logs {task_id[:8]} 查看实时日志[/yellow]\n")

        system_log.write(f"[green]任务 {task_id[:8]} 已提交[/green]")

    def _handle_confirm(self, chat_display, system_log):
        """处理确认命令"""
        if not self.selected_task_id:
            chat_display.write("[red]请先在左侧选择一个任务[/red]\n")
            return

        task = self.task_manager.get_task(self.selected_task_id)

        if not task:
            chat_display.write("[red]任务不存在[/red]\n")
            return

        if task.status != TaskStatus.AWAITING_CONFIRM:
            chat_display.write(f"[red]任务状态为 {task.status.value}，无需确认[/red]\n")
            return

        # 确认任务
        success = self.scheduler.resume_task(self.selected_task_id)

        if success:
            chat_display.write(f"[green]✅ 任务已确认，继续生成...[/green]\n")
            system_log.write(f"[green]任务 {self.selected_task_id[:8]} 已确认[/green]")
        else:
            chat_display.write(f"[red]确认失败，请检查日志[/red]\n")

    def _handle_cancel(self, chat_display, system_log):
        """处理取消命令"""
        if not self.selected_task_id:
            chat_display.write("[red]请先在左侧选择一个任务[/red]\n")
            return

        task = self.task_manager.get_task(self.selected_task_id)

        if not task:
            chat_display.write("[red]任务不存在[/red]\n")
            return

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            chat_display.write(f"[red]任务已结束，无法取消[/red]\n")
            return

        # 取消任务
        self.scheduler.terminate_task(self.selected_task_id)
        task.status = TaskStatus.CANCELLED
        self.task_manager._save_task(task)

        chat_display.write(f"[green]✅ 任务已取消[/green]\n")
        system_log.write(f"[yellow]任务 {self.selected_task_id[:8]} 已取消[/yellow]")

    def _handle_logs(self, task_id, chat_display, system_log):
        """处理日志命令"""
        if not task_id:
            chat_display.write("[red]用法: /logs <task_id>[/red]\n")
            return

        # 查找任务（支持短ID）
        tasks = self.task_manager.get_session_tasks(self.session_id)
        task = None
        for t in tasks:
            if t.task_id.startswith(task_id):
                task = t
                break

        if not task:
            chat_display.write(f"[red]任务 {task_id} 不存在[/red]\n")
            return

        # 获取日志
        logs = self.scheduler.get_logs(task.task_id, tail=50)

        chat_display.write(f"\n[bold]📄 任务日志 (最后50行): {task.task_id[:8]}[/bold]")
        chat_display.write("[dim]" + "=" * 60 + "[/dim]")

        for log in logs:
            chat_display.write(log)

        chat_display.write("[dim]" + "=" * 60 + "[/dim]\n")

    def _handle_view(self, task_id, chat_display):
        """处理查看方案命令"""
        # 查找任务
        tasks = self.task_manager.get_session_tasks(self.session_id)
        task = None
        for t in tasks:
            if t.task_id.startswith(task_id):
                task = t
                break

        if not task:
            chat_display.write(f"[red]任务 {task_id} 不存在[/red]\n")
            return

        if task.status != TaskStatus.COMPLETED:
            chat_display.write(f"[red]任务未完成 (状态: {task.status.value})[/red]\n")
            return

        if not task.plan_file.exists():
            chat_display.write(f"[red]方案文件不存在[/red]\n")
            return

        # 读取方案
        import json
        with open(task.plan_file, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        # 格式化显示
        chat_display.write(f"\n[bold green]✅ 实验方案: {plan_data.get('title', '未命名')}[/bold green]\n")

        chat_display.write(f"[bold]📋 实验目标:[/bold]")
        chat_display.write(f"{plan_data.get('objective', 'N/A')}\n")

        chat_display.write(f"[bold]🧪 材料清单:[/bold]")
        for mat in plan_data.get('materials', []):
            chat_display.write(f"  • {mat.get('name')}: {mat.get('amount')}")

        chat_display.write(f"\n[bold]📝 实验步骤:[/bold]")
        for step in plan_data.get('procedure', []):
            chat_display.write(f"  {step.get('step_number')}. {step.get('description')}")

        chat_display.write("")

    def _handle_tasks(self, chat_display):
        """处理任务列表命令"""
        tasks = self.task_manager.get_session_tasks(self.session_id)

        if not tasks:
            chat_display.write("[yellow]当前会话暂无任务[/yellow]\n")
            return

        chat_display.write("\n[bold]📋 任务列表:[/bold]\n")

        tasks.sort(key=lambda t: t.created_at, reverse=True)

        for task in tasks:
            icon = STATUS_ICONS.get(task.status.value)
            title = task.metadata.get("title", "生成中...")
            time_str = task.created_at.strftime("%Y-%m-%d %H:%M:%S")

            chat_display.write(f"{icon} {task.task_id[:8]} [{task.status.value}]")
            chat_display.write(f"   {title}")
            chat_display.write(f"   {time_str}\n")

    def _handle_history(self, chat_display):
        """处理历史命令"""
        if not self.chatbot:
            chat_display.write("[red]Chatbot未初始化[/red]\n")
            return

        history = self.chatbot.get_history(self.session_id)

        if not history:
            chat_display.write("[yellow]暂无对话历史[/yellow]\n")
            return

        chat_display.write("\n[bold]📜 对话历史:[/bold]\n")

        for i, msg in enumerate(history, 1):
            role = "👤 你" if msg["role"] == "user" else "🤖 助手"
            content = msg["content"]
            if len(content) > 100:
                content = content[:100] + "..."

            chat_display.write(f"[{i}] {role}: {content}\n")

    def _handle_clear_history(self, chat_display, system_log):
        """处理清空历史命令"""
        if not self.chatbot:
            chat_display.write("[red]Chatbot未初始化[/red]\n")
            return

        # 生成新的session_id（相当于开始新会话）
        old_session_id = self.session_id
        self.session_id = f"tui_session_{uuid.uuid4().hex[:8]}"

        chat_display.write(f"[green]✅ 对话历史已清空[/green]\n")
        chat_display.write(f"[dim]旧会话ID: {old_session_id}[/dim]\n")
        chat_display.write(f"[dim]新会话ID: {self.session_id}[/dim]\n")

        system_log.write(f"[yellow]会话已重置: {old_session_id} → {self.session_id}[/yellow]")

    async def _handle_chat(self, message: str, chat_display):
        """处理正常对话"""
        if not self.chatbot:
            chat_display.write("[red]Chatbot未初始化完成[/red]\n")
            return

        # 在后台线程中执行聊天（避免阻塞UI）
        chat_thread = threading.Thread(
            target=self._run_chat_in_background,
            args=(message, chat_display),
            daemon=True
        )
        chat_thread.start()

    def _run_chat_in_background(self, message: str, chat_display):
        """后台线程：执行聊天并更新UI"""
        system_log = self.query_one("#system-log")
        streaming_display = self.query_one("#streaming-display")

        try:
            full_thinking = ""
            full_content = ""
            last_update_time = time.time()
            UPDATE_INTERVAL = 0.1  # 100ms刷新一次（真正流式）

            for event in self.chatbot.stream_chat(message, self.session_id, show_thinking=True):
                event_type = event.get("type")
                data = event.get("data", "")

                # 累积thinking
                if event_type == "thinking":
                    full_thinking = data

                # 工具调用 - 显示在系统日志
                elif event_type == "tool_call":
                    self.call_from_thread(
                        system_log.write,
                        f"[cyan]🔧 调用工具: {data}[/cyan]"
                    )

                # 工具结果 - 显示在系统日志
                elif event_type == "tool_result":
                    preview = data[:100] + "..." if len(data) > 100 else data
                    self.call_from_thread(
                        system_log.write,
                        f"[dim]   结果: {preview}[/dim]"
                    )

                # 累积content
                elif event_type == "content":
                    full_content = data

                # 定期刷新流式显示（真正的流式效果）
                current_time = time.time()
                if current_time - last_update_time > UPDATE_INTERVAL:
                    # 构建当前显示内容
                    display_text = "[bold green]🤖 助手:[/bold green]"

                    if full_thinking:
                        display_text += f"\n\n💭 思考中:\n[dim]{full_thinking}[/dim]"

                    if full_content:
                        if full_thinking:
                            display_text += "\n"
                        # 转义content中的方括号
                        escaped_content = full_content.replace("[", "\\[").replace("]", "\\]")
                        display_text += f"\n{escaped_content}"

                    # 更新流式显示区（Static可以频繁update）
                    self.call_from_thread(streaming_display.update, display_text)
                    last_update_time = current_time

            # 最后一次更新（确保显示完整内容）
            final_text = "[bold green]🤖 助手:[/bold green]"
            if full_thinking:
                final_text += f"\n\n💭 思考中:\n[dim]{full_thinking}[/dim]"
            if full_content:
                if full_thinking:
                    final_text += "\n"
                # 转义content中的方括号，避免Rich标签冲突
                escaped_content = full_content.replace("[", "\\[").replace("]", "\\]")
                final_text += f"\n{escaped_content}"

            self.call_from_thread(streaming_display.update, final_text)

            # 等待一小段时间让用户看到完整消息
            time.sleep(0.5)

            # 调试：输出到系统日志查看
            self.call_from_thread(
                system_log.write,
                f"[yellow]DEBUG: 准备写入历史，长度={len(final_text)}，content长度={len(full_content)}[/yellow]"
            )

            # 将完整消息追加到历史RichLog
            try:
                self.call_from_thread(chat_display.write, final_text + "\n")
                self.call_from_thread(
                    system_log.write,
                    f"[green]DEBUG: 成功写入历史[/green]"
                )
            except Exception as write_error:
                self.call_from_thread(
                    system_log.write,
                    f"[red]DEBUG: 写入历史失败: {write_error}[/red]"
                )
                # 尝试不使用markup写入
                self.call_from_thread(
                    system_log.write,
                    f"[yellow]DEBUG: 尝试无markup写入...[/yellow]"
                )
                plain_text = f"🤖 助手:\n\n💭 思考中:\n{full_thinking}\n\n{full_content}"
                self.call_from_thread(chat_display.write, plain_text + "\n")

            # 清空流式显示区，等待下次输入
            self.call_from_thread(streaming_display.update, "")

        except Exception as e:
            # 详细错误信息
            error_msg = str(e)

            # 检查是否是工具调用历史错误
            if "tool_calls that do not have a corresponding ToolMessage" in error_msg:
                self.call_from_thread(
                    chat_display.write,
                    f"\n[red]发生错误：对话历史中有未完成的工具调用[/red]\n"
                )
                self.call_from_thread(
                    chat_display.write,
                    "[yellow]这通常是因为上一次对话中MOSES工具调用失败导致。[/yellow]\n"
                )
                self.call_from_thread(
                    chat_display.write,
                    "[yellow]解决方法：输入 /clear 清空对话历史[/yellow]\n"
                )
            else:
                self.call_from_thread(
                    chat_display.write,
                    f"\n[red]对话失败: {error_msg}[/red]\n"
                )

            # 打印详细错误到系统日志
            import traceback
            system_log = self.query_one("#system-log")
            self.call_from_thread(
                system_log.write,
                f"[red]聊天错误详情:\n{traceback.format_exc()}[/red]"
            )

    def action_quit(self):
        """退出应用"""
        self.running = False
        self.exit()

    def action_clear_chat(self):
        """清空对话"""
        chat_display = self.query_one("#chat-display", RichLog)
        chat_display.clear()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("启动 TUI...")
    print("="*70)
    print()

    app = ChemistryAssistantTUI()
    app.run()
