#!/usr/bin/env python3
"""化学实验助手Chatbot - CLI交互模式

提供命令行交互界面，支持：
- 流式响应（实时打字效果）
- 多轮对话记忆
- 会话历史查看
- MOSES本体查询集成

使用方法:
    python examples/chatbot_cli.py

命令:
    quit/exit/q - 退出程序
    history - 查看当前会话历史
    help - 显示帮助信息
"""
import sys
import os

# 加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.chatbot import Chatbot


def print_help():
    """打印帮助信息"""
    print("""
╔════════════════════════════════════════════════════════════╗
║          化学实验助手 - 使用说明                            ║
╚════════════════════════════════════════════════════════════╝

命令:
  quit/exit/q    - 退出程序
  history        - 查看当前会话历史
  clear          - 清屏
  help           - 显示此帮助信息

功能:
  - 自动查询化学本体知识库（MOSES）
  - 多轮对话记忆
  - 流式响应（实时显示）

示例问题:
  - 什么是奎宁？
  - 告诉我关于指示剂置换分析法（IDA）的信息
  - 电化学传感器的工作原理是什么？
    """)


def print_banner():
    """打印欢迎横幅"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       🧪  化学实验助手 - Chemistry Lab Assistant  🧪       ║
║                                                            ║
║          基于 LangGraph + MOSES 本体知识库                 ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

初始化中，请稍候...
    """)


def print_history(bot: Chatbot, session_id: str):
    """打印会话历史"""
    history = bot.get_history(session_id)

    if not history:
        print("\n[暂无历史记录]\n")
        return

    print("\n" + "="*60)
    print("会话历史:")
    print("="*60)

    for i, msg in enumerate(history, 1):
        role = msg["role"]
        content = msg["content"]

        # 格式化角色名
        role_display = {
            "user": "👤 你",
            "assistant": "🤖 助手",
            "system": "⚙️  系统"
        }.get(role, role)

        print(f"\n[{i}] {role_display}:")
        print(f"{content}")
        print("-" * 60)

    print()


def main():
    """主函数"""
    print_banner()

    try:
        # 初始化Chatbot
        print("[DEBUG CLI] About to create Chatbot...")
        bot = Chatbot(config_path="configs/chatbot_config.yaml")
        print("[DEBUG CLI] Chatbot created successfully")
        session_id = "cli_session"

        print("\n✅ 初始化完成！输入 'help' 查看使用说明，输入 'quit' 退出。\n")

        # 主循环
        while True:
            try:
                # 获取用户输入
                user_input = input("\n👤 你: ").strip()

                # 空输入
                if not user_input:
                    continue

                # 退出命令
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 再见！\n")
                    break

                # 帮助命令
                if user_input.lower() == "help":
                    print_help()
                    continue

                # 历史命令
                if user_input.lower() == "history":
                    print_history(bot, session_id)
                    continue

                # 清屏命令
                if user_input.lower() == "clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue

                # 正常对话 - 流式响应
                thinking_shown = False
                content_started = False
                current_content = []

                for event in bot.stream_chat(user_input, session_id=session_id, show_thinking=True):
                    event_type = event.get("type")
                    data = event.get("data", "")

                    if event_type == "thinking":
                        # 显示thinking过程（灰色文字）
                        if not thinking_shown:
                            print("\n💭 思考中: ", end="", flush=True)
                            thinking_shown = True
                        print(f"\033[90m{data}\033[0m", end="", flush=True)  # 灰色

                    elif event_type == "tool_call":
                        # 显示工具调用
                        print(f"\n🔧 调用工具: {data}", flush=True)

                    elif event_type == "tool_result":
                        # 显示工具结果（灰色，截断显示）
                        preview = data[:100] + "..." if len(data) > 100 else data
                        print(f"\033[90m   结果: {preview}\033[0m", flush=True)

                    elif event_type == "content":
                        # 显示实际回复（逐token流式）
                        if not content_started:
                            if thinking_shown:
                                print()  # thinking后换行
                            print("\n🤖 助手: ", end="", flush=True)
                            content_started = True

                        # 打印新token（打字效果）
                        current_text = "".join(current_content)
                        if data.startswith(current_text):
                            new_token = data[len(current_text):]
                            print(new_token, end="", flush=True)
                            current_content.append(new_token)
                        else:
                            # 非增量更新，直接打印
                            print(data, end="", flush=True)
                            current_content = [data]

                if not content_started:
                    print()  # 如果没有content，确保换行
                else:
                    print()  # 最后换行

            except KeyboardInterrupt:
                print("\n\n👋 程序被中断，正在退出...\n")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}\n")
                print("你可以继续对话或输入 'quit' 退出。")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        print("请检查配置文件和依赖是否正确安装。")
        sys.exit(1)

    finally:
        # 清理资源
        try:
            bot.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()
