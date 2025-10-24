#!/usr/bin/env python3
"""Chatbot基本功能测试脚本

测试内容：
1. 配置加载
2. Chatbot初始化
3. 简单对话（不调用MOSES）
"""
import sys
import os

# 加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("测试1: 配置加载")
    print("=" * 60)

    try:
        from src.chatbot.config import load_config

        config = load_config("configs/chatbot_config.yaml")
        print("✅ 配置文件加载成功")

        # 检查关键配置项
        assert "chatbot" in config
        assert "llm" in config["chatbot"]
        assert "moses" in config["chatbot"]
        assert "memory" in config["chatbot"]

        print(f"  - LLM模型: {config['chatbot']['llm']['model_name']}")
        print(f"  - 记忆类型: {config['chatbot']['memory']['type']}")
        print(f"  - MOSES超时: {config['chatbot']['moses']['query_timeout']}秒")

        print("✅ 配置验证通过\n")
        return True

    except Exception as e:
        print(f"❌ 配置加载失败: {e}\n")
        return False


def test_chatbot_init():
    """测试Chatbot初始化（不启动MOSES）"""
    print("=" * 60)
    print("测试2: Chatbot初始化")
    print("=" * 60)

    try:
        from src.chatbot import Chatbot

        print("正在初始化Chatbot...")
        bot = Chatbot(config_path="configs/chatbot_config.yaml")
        print("✅ Chatbot初始化成功")

        # 检查组件
        assert bot.llm is not None
        assert bot.agent is not None
        assert bot.checkpointer is not None

        print("  - LLM: OK")
        print("  - Agent: OK")
        print("  - Checkpointer: OK")

        print("\n✅ 组件验证通过\n")

        # 清理
        bot.cleanup()
        return True

    except Exception as e:
        print(f"❌ Chatbot初始化失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_simple_chat():
    """测试简单对话（无工具调用）"""
    print("=" * 60)
    print("测试3: 简单对话测试")
    print("=" * 60)

    try:
        from src.chatbot import Chatbot

        bot = Chatbot(config_path="configs/chatbot_config.yaml")

        # 简单的闲聊，不应触发MOSES工具
        test_message = "你好"
        print(f"用户: {test_message}")
        print("助手: ", end="", flush=True)

        # 测试流式响应
        response_parts = []
        for event in bot.stream_chat(test_message, session_id="test_session", show_thinking=False):
            if event.get("type") == "content":
                data = event.get("data", "")
                print(data, end="", flush=True)
                response_parts.append(data)

        full_response = "".join(response_parts)
        print("\n")
        print(f"✅ 收到回复（{len(full_response)}字符）\n")

        # 清理
        bot.cleanup()
        return True

    except Exception as e:
        print(f"\n❌ 对话测试失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Chatbot 基本功能测试")
    print("="*60 + "\n")

    results = []

    # 测试1: 配置加载
    results.append(("配置加载", test_config_loading()))

    # 测试2: Chatbot初始化
    results.append(("Chatbot初始化", test_chatbot_init()))

    # 测试3: 简单对话
    results.append(("简单对话", test_simple_chat()))

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！\n")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
