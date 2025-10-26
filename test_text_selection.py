#!/usr/bin/env python3
"""测试textual的文本选择功能"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Static
from textual.containers import Vertical
from textual.binding import Binding

class TextSelectionTest(App):
    """测试文本选择"""

    CSS = """
    RichLog {
        border: solid blue;
        height: 1fr;
    }

    RichLog:focus {
        border: solid green;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("tab", "focus_next", "切换焦点"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static("按Tab聚焦RichLog（边框变绿），然后鼠标选择文本")
            yield RichLog(id="log1")

        with Vertical():
            yield Static("第二个RichLog")
            yield RichLog(id="log2")

        yield Footer()

    def on_mount(self):
        log1 = self.query_one("#log1", RichLog)
        log2 = self.query_one("#log2", RichLog)

        log1.write("[yellow]这是第一个日志区[/yellow]")
        log1.write("可以尝试：")
        log1.write("1. 按Tab聚焦（边框变绿）")
        log1.write("2. 用鼠标选择这段文本")
        log1.write("3. Ctrl+Shift+C复制（Linux）")
        log1.write("4. 或者Cmd+C（macOS）")

        log2.write("[cyan]这是第二个日志区[/cyan]")
        log2.write("也可以选择复制这里的文本")

if __name__ == "__main__":
    print("启动文本选择测试...")
    print("操作步骤：")
    print("1. 按Tab键在两个RichLog之间切换焦点")
    print("2. 聚焦后边框会变绿")
    print("3. 用鼠标选择文本")
    print("4. 复制（取决于终端）：")
    print("   - Linux: Ctrl+Shift+C")
    print("   - macOS: Cmd+C")
    print("   - Windows: Ctrl+Shift+C 或右键")
    print()

    app = TextSelectionTest()
    app.run()
