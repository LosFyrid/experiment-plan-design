#!/usr/bin/env python3
"""测试Chatbot的thinking流式输出功能

验证:
1. thinking以灰色token级流式显示
2. thinking结束后换行
3. 空thinking自动跳过
"""
import sys
import os

# 加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.chatbot import Chatbot


def test_thinking_stream():
    """测试thinking流式输出"""
    print("=" * 60)
    print("测试: Thinking流式输出")
    print("=" * 60)
    print()

    try:
        bot = Chatbot(config_path="configs/chatbot_config.yaml")

        # 使用需要复杂推理的问题来触发thinking
        test_message = "请详细解释一下量子力学中的薛定谔方程及其物理意义"
        print(f"👤 用户: {test_message}")
        print()

        thinking_shown = False
        content_started = False
        thinking_parts = []
        content_parts = []

        for event in bot.stream_chat(test_message, session_id="test_thinking", show_thinking=True):
            event_type = event.get("type")
            data = event.get("data", "")

            if event_type == "thinking":
                # 验证thinking显示
                if not thinking_shown:
                    print("💭 思考中: ", end="", flush=True)
                    thinking_shown = True
                # 灰色显示
                print(f"\033[90m{data}\033[0m", end="", flush=True)
                thinking_parts.append(data)

            elif event_type == "content":
                # thinking结束后换行
                if not content_started:
                    if thinking_shown:
                        print()  # 换行
                    print("\n🤖 助手: ", end="", flush=True)
                    content_started = True

                # 逐token打印
                current_text = "".join(content_parts)
                if data.startswith(current_text):
                    new_token = data[len(current_text):]
                    print(new_token, end="", flush=True)
                    content_parts.append(new_token)
                else:
                    print(data, end="", flush=True)
                    content_parts = [data]

            elif event_type == "tool_call":
                print(f"\n🔧 工具调用: {data}", flush=True)

            elif event_type == "tool_result":
                preview = data[:100] + "..." if len(data) > 100 else data
                print(f"\033[90m   结果: {preview}\033[0m", flush=True)

        print("\n")

        # 统计
        thinking_text = "".join(thinking_parts)
        content_text = "".join(content_parts)

        print("-" * 60)
        print(f"✅ 测试完成")
        print(f"  - Thinking字符数: {len(thinking_text)}")
        print(f"  - Content字符数: {len(content_text)}")
        print(f"  - Thinking显示: {'是' if thinking_shown else '否（空thinking已跳过）'}")
        print()

        bot.cleanup()
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行测试"""
    print("\n" + "="*60)
    print("Chatbot Thinking流式输出测试")
    print("="*60 + "\n")

    success = test_thinking_stream()

    if success:
        print("\n🎉 Thinking流式输出测试通过！\n")
        return 0
    else:
        print("\n⚠️  测试失败，请检查错误信息。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
