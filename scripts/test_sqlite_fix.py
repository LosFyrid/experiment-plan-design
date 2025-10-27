#!/usr/bin/env python3
"""测试SQLite会话持久化修复"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

def test_sqlite_persistence():
    """测试SQLite持久化功能"""
    print("\n" + "="*70)
    print("测试SQLite会话持久化")
    print("="*70)

    import tempfile
    import yaml
    from chatbot.chatbot import Chatbot

    # 创建临时数据库
    temp_db = Path(tempfile.mktemp(suffix='.db'))
    print(f"\n临时数据库: {temp_db}")

    # 创建临时配置
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
                "sqlite_path": str(temp_db)
            },
            "system_prompt": "你是化学实验助手"
        }
    }

    temp_config_path = Path(tempfile.mktemp(suffix='.yaml'))
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    try:
        print("\n[1/4] 初始化Chatbot（SQLite模式）...")
        bot = Chatbot(str(temp_config_path))
        print("    ✅ 初始化成功")

        print("\n[2/4] 发送测试消息...")
        session_id = "test_session_001"

        try:
            response = bot.chat("你好，这是一条测试消息", session_id=session_id)
            print(f"    ✅ AI回复: {response[:50]}...")
        except Exception as e:
            print(f"    ❌ 对话失败: {e}")
            raise

        print("\n[3/4] 验证数据库写入...")
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("SELECT DISTINCT thread_id FROM checkpoints")
        sessions = [row[0] for row in cursor.fetchall()]
        conn.close()

        if session_id in sessions:
            print(f"    ✅ 找到会话: {session_id}")
        else:
            print(f"    ❌ 未找到会话: {session_id}")
            print(f"    数据库中的会话: {sessions}")
            raise AssertionError("会话未保存到数据库")

        print("\n[4/4] 验证历史恢复...")
        history = bot.get_history(session_id)
        print(f"    消息数: {len(history)}")

        if len(history) >= 2:  # user + assistant
            print(f"    ✅ 历史恢复成功")
            for i, msg in enumerate(history[:2], 1):
                print(f"      [{i}] {msg['role']}: {msg['content'][:30]}...")
        else:
            print(f"    ❌ 历史不完整: {history}")
            raise AssertionError("历史恢复失败")

        bot.cleanup()

        print("\n" + "="*70)
        print("✅ 所有测试通过！SQLite持久化工作正常")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # 清理
        if temp_config_path.exists():
            temp_config_path.unlink()
        if temp_db.exists():
            temp_db.unlink()


if __name__ == "__main__":
    test_sqlite_persistence()
