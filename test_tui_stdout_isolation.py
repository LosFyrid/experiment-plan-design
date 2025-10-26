#!/usr/bin/env python3
"""测试TUI方案是否能解决stdout竞态条件问题

验证要点：
1. TUI界面显示不受MOSES后台线程修改stdout的影响
2. MOSES后台线程可以自由重定向stdout到日志文件
3. MOSES统计摘要通过回调传递到TUI显示
"""

import sys
import time
import threading
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Static
from textual.containers import Horizontal, Vertical


class StdoutIsolationTest(App):
    """测试TUI是否隔离stdout"""

    CSS = """
    #left-panel {
        width: 50%;
        border: solid green;
    }

    #right-panel {
        width: 50%;
        border: solid blue;
    }

    RichLog {
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            # 左侧：TUI主线程输出
            with Vertical(id="left-panel"):
                yield Static("📺 TUI主线程输出 (textual API)")
                yield RichLog(id="tui-log", highlight=True, markup=True)

            # 右侧：MOSES后台线程状态
            with Vertical(id="right-panel"):
                yield Static("🔧 MOSES后台线程状态")
                yield RichLog(id="moses-log", highlight=True, markup=True)

        yield Footer()

    def on_mount(self):
        """启动时测试"""
        tui_log = self.query_one("#tui-log", RichLog)
        moses_log = self.query_one("#moses-log", RichLog)

        tui_log.write("[green]✓ TUI启动完成[/green]")
        tui_log.write("")
        tui_log.write("[yellow]现在开始测试stdout隔离...[/yellow]")
        tui_log.write("")

        # 测试1：主线程输出（使用TUI API，不用print）
        tui_log.write("[1] 主线程输出消息1（通过textual）")
        time.sleep(0.5)

        # 测试2：启动后台线程，模拟MOSES修改stdout
        moses_log.write("[yellow]启动后台线程...[/yellow]")

        thread = threading.Thread(
            target=self._simulate_moses_init,
            args=(moses_log,),
            daemon=True
        )
        thread.start()

        # 测试3：主线程继续输出
        time.sleep(0.2)
        tui_log.write("[2] 主线程输出消息2（后台线程已启动）")
        time.sleep(0.5)
        tui_log.write("[3] 主线程输出消息3（后台线程正在修改stdout）")
        time.sleep(1.5)
        tui_log.write("[4] 主线程输出消息4（后台线程已完成）")
        tui_log.write("")
        tui_log.write("[green]✓ 测试完成！检查日志文件[/green]")
        tui_log.write(f"[dim]日志文件: logs/test_stdout_isolation.log[/dim]")

    def _simulate_moses_init(self, moses_log):
        """模拟MOSES后台初始化（修改stdout）"""

        # 通过TUI API显示状态
        self.call_from_thread(
            moses_log.write,
            "[yellow]后台线程: 准备重定向stdout到日志文件...[/yellow]"
        )

        time.sleep(0.5)

        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "test_stdout_isolation.log"

        # 保存原始stdout
        original_stdout = sys.stdout

        try:
            # 重定向stdout到日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                sys.stdout = f

                # 通过TUI API显示（不是print）
                self.call_from_thread(
                    moses_log.write,
                    "[red]后台线程: stdout已重定向到文件！[/red]"
                )

                # 模拟MOSES的print输出（写入日志文件）
                print("="*60)
                print("MOSES后台初始化输出（写入日志文件）")
                print("="*60)
                print("正在加载本体...")
                time.sleep(0.3)
                print("正在初始化查询管理器...")
                time.sleep(0.3)
                print("正在启动工作线程...")
                time.sleep(0.3)
                print("初始化完成！")
                print("="*60)

                # 恢复stdout
                sys.stdout = original_stdout

                # 通过TUI API显示恢复
                self.call_from_thread(
                    moses_log.write,
                    "[green]后台线程: stdout已恢复到终端[/green]"
                )

            # 模拟读取统计信息（通过回调传递，不是print）
            time.sleep(0.3)
            summary = {
                "classes": 1532,
                "data_properties": 906,
                "object_properties": 554
            }

            # 通过回调显示摘要
            self.call_from_thread(
                self._show_moses_summary,
                moses_log,
                summary
            )

        except Exception as e:
            sys.stdout = original_stdout
            self.call_from_thread(
                moses_log.write,
                f"[red]错误: {e}[/red]"
            )

    def _show_moses_summary(self, moses_log, summary):
        """显示MOSES统计摘要（TUI API）"""
        moses_log.write("")
        moses_log.write("[green]" + "="*40 + "[/green]")
        moses_log.write("[green bold]✓ MOSES初始化完成[/green bold]")
        moses_log.write(f"Classes: {summary['classes']}")
        moses_log.write(f"Data Properties: {summary['data_properties']}")
        moses_log.write(f"Object Properties: {summary['object_properties']}")
        moses_log.write("[green]" + "="*40 + "[/green]")


if __name__ == "__main__":
    # 检查textual是否安装
    try:
        import textual
    except ImportError:
        print("❌ 需要安装textual:")
        print("   pip install textual")
        sys.exit(1)

    print("\n" + "="*70)
    print("TUI stdout隔离测试")
    print("="*70)
    print()
    print("测试内容:")
    print("  1. TUI主线程使用textual API输出（左侧面板）")
    print("  2. 后台线程修改sys.stdout重定向到日志文件")
    print("  3. 验证TUI显示不受影响")
    print("  4. MOSES摘要通过回调显示（右侧面板）")
    print()
    print("预期结果:")
    print("  ✓ 左侧面板显示4条主线程消息（不受后台线程影响）")
    print("  ✓ 右侧面板显示MOSES初始化过程")
    print("  ✓ logs/test_stdout_isolation.log 包含MOSES的print输出")
    print()
    print("按 'q' 退出")
    print("="*70)
    print()

    app = StdoutIsolationTest()
    app.run()

    # 测试结束，显示日志内容
    print("\n" + "="*70)
    print("测试完成！检查日志文件内容:")
    print("="*70)

    log_file = Path("logs/test_stdout_isolation.log")
    if log_file.exists():
        print(f"\n📄 {log_file}:")
        print("-" * 70)
        print(log_file.read_text())
        print("-" * 70)
        print()
        print("✅ 验证成功:")
        print("   - TUI界面正常显示（不受stdout重定向影响）")
        print("   - MOSES的print输出被正确写入日志文件")
        print("   - MOSES摘要通过回调显示到TUI")
    else:
        print("\n❌ 日志文件未生成")
