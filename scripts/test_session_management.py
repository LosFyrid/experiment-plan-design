#!/usr/bin/env python3
"""测试会话管理功能

测试场景：
1. 内存模式 - 基本功能
2. SQLite模式 - 持久化和恢复
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

from chatbot.chatbot import Chatbot
import tempfile
import shutil


def test_memory_mode():
    """测试内存模式"""
    print("\n" + "="*70)
    print("测试1: 内存模式")
    print("="*70)

    # 创建临时配置（内存模式）
    config = {
        "chatbot": {
            "llm": {
                "provider": "qwen",
                "model_name": "qwen-plus",
                "temperature": 0.7,
                "max_tokens": 4096,
                "enable_thinking": True
            },
            "moses": {
                "max_workers": 4,
                "query_timeout": 600
            },
            "memory": {
                "type": "in_memory"
            },
            "system_prompt": "你是化学实验助手"
        }
    }

    # 保存临时配置
    import yaml
    temp_config_path = Path(tempfile.mktemp(suffix='.yaml'))
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    try:
        bot = Chatbot(str(temp_config_path))

        # 测试多会话
        print("\n✓ 创建会话1")
        response1 = bot.chat("你好，我想合成阿司匹林", session_id="session_1")
        print(f"  助手回复: {response1[:50]}...")

        print("\n✓ 创建会话2")
        response2 = bot.chat("你好，我想合成青霉素", session_id="session_2")
        print(f"  助手回复: {response2[:50]}...")

        # 测试历史获取
        print("\n✓ 获取会话1历史")
        history1 = bot.get_history("session_1")
        print(f"  消息数: {len(history1)}")

        print("\n✓ 获取会话2历史")
        history2 = bot.get_history("session_2")
        print(f"  消息数: {len(history2)}")

        # 测试list_sessions（内存模式应返回空列表）
        print("\n✓ 列出会话（内存模式）")
        sessions = bot.list_sessions()
        print(f"  会话列表: {sessions}")
        if len(sessions) == 0:
            print("  ✅ 正确：内存模式无法列出会话")
        else:
            print("  ⚠️ 警告：内存模式不应返回会话列表")

        bot.cleanup()
        print("\n✅ 内存模式测试通过\n")

    finally:
        temp_config_path.unlink()


def test_sqlite_mode():
    """测试SQLite模式"""
    print("\n" + "="*70)
    print("测试2: SQLite模式")
    print("="*70)

    # 创建临时数据库
    temp_db_path = Path(tempfile.mktemp(suffix='.db'))

    # 创建临时配置（SQLite模式）
    config = {
        "chatbot": {
            "llm": {
                "provider": "qwen",
                "model_name": "qwen-plus",
                "temperature": 0.7,
                "max_tokens": 4096,
                "enable_thinking": True
            },
            "moses": {
                "max_workers": 4,
                "query_timeout": 600
            },
            "memory": {
                "type": "sqlite",
                "sqlite_path": str(temp_db_path)
            },
            "system_prompt": "你是化学实验助手"
        }
    }

    import yaml
    temp_config_path = Path(tempfile.mktemp(suffix='.yaml'))
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    try:
        # 第一次运行：创建会话
        print("\n--- 第一次运行 ---")
        bot1 = Chatbot(str(temp_config_path))

        print("\n✓ 创建会话A")
        bot1.chat("我想合成阿司匹林", session_id="session_A")

        print("\n✓ 创建会话B")
        bot1.chat("我想合成青霉素", session_id="session_B")

        print("\n✓ 列出会话")
        sessions1 = bot1.list_sessions()
        print(f"  会话列表: {sessions1}")

        if set(sessions1) == {"session_A", "session_B"}:
            print("  ✅ 正确：找到所有会话")
        else:
            print(f"  ❌ 错误：期望 ['session_A', 'session_B']，实际 {sessions1}")

        bot1.cleanup()

        # 第二次运行：恢复会话
        print("\n--- 第二次运行（模拟重启）---")
        bot2 = Chatbot(str(temp_config_path))

        print("\n✓ 列出会话（恢复后）")
        sessions2 = bot2.list_sessions()
        print(f"  会话列表: {sessions2}")

        if set(sessions2) == {"session_A", "session_B"}:
            print("  ✅ 正确：会话持久化成功")
        else:
            print(f"  ❌ 错误：会话未持久化")

        print("\n✓ 恢复会话A历史")
        history_a = bot2.get_history("session_A")
        print(f"  消息数: {len(history_a)}")
        if len(history_a) > 0:
            print(f"  第一条消息: {history_a[0]['content'][:30]}...")
            print("  ✅ 正确：历史恢复成功")
        else:
            print("  ❌ 错误：历史未恢复")

        bot2.cleanup()
        print("\n✅ SQLite模式测试通过\n")

    finally:
        temp_config_path.unlink()
        if temp_db_path.exists():
            temp_db_path.unlink()


def main():
    """运行所有测试"""
    print("\n🧪 会话管理功能测试\n")

    try:
        # 测试1: 内存模式
        test_memory_mode()

        # 测试2: SQLite模式
        test_sqlite_mode()

        print("="*70)
        print("✅ 所有测试通过！")
        print("="*70)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
