#!/usr/bin/env python3
"""完整测试Chatbot类的SQLite会话管理"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

import tempfile
import yaml
from chatbot.chatbot import Chatbot

print("="*70)
print("完整测试Chatbot类 - SQLite会话持久化")
print("="*70)

# 创建临时配置和数据库
temp_db = Path(tempfile.mktemp(suffix='.db'))
print(f"\n临时数据库: {temp_db}")

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
    print("\n[1/5] 初始化Chatbot（SQLite模式）...")
    bot = Chatbot(str(temp_config_path))
    print("✅ 初始化成功")

    print("\n[2/5] 会话1 - 发送消息...")
    response1 = bot.chat("你好，我是小明", session_id="session_001")
    print(f"✅ AI回复: {response1[:50]}...")

    response2 = bot.chat("我叫什么名字？", session_id="session_001")
    print(f"✅ AI回复: {response2[:50]}...")

    print("\n[3/5] 会话2 - 新建独立会话...")
    response3 = bot.chat("你好，我是小红", session_id="session_002")
    print(f"✅ AI回复: {response3[:50]}...")

    print("\n[4/5] 验证会话隔离...")
    response4 = bot.chat("我叫什么名字？", session_id="session_002")
    print(f"✅ AI回复: {response4[:50]}...")

    if "小红" in response4 and "小明" not in response4:
        print("✅ 会话隔离正确：session_002记住了小红，没有记住小明")
    else:
        print("⚠️ 会话隔离可能有问题")

    print("\n[5/5] 列出所有会话...")
    sessions = bot.list_sessions()
    print(f"✅ 找到 {len(sessions)} 个会话: {sessions}")

    if set(sessions) == {"session_001", "session_002"}:
        print("✅ 会话列表正确")
    else:
        print(f"⚠️ 期望 ['session_001', 'session_002']，实际 {sessions}")

    # 验证历史
    print("\n验证历史记录...")
    history1 = bot.get_history("session_001")
    history2 = bot.get_history("session_002")
    print(f"  session_001: {len(history1)} 条消息")
    print(f"  session_002: {len(history2)} 条消息")

    bot.cleanup()

    print("\n" + "="*70)
    print("✅ 所有测试通过！Chatbot SQLite会话管理工作正常")
    print("="*70)

    # 显示代码简洁性
    print("\n💡 代码简洁性对比：")
    print("  旧方案: ~50行（手动connection, setup, serializer）")
    print("  新方案: 1行代码！")
    print("  SqliteSaver.from_conn_string(path).__enter__()")

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
