#!/usr/bin/env python3
"""调试会话 b4d838 的对话历史"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from chatbot.chatbot import Chatbot

# 初始化chatbot
bot = Chatbot(config_path="configs/chatbot_config.yaml")

# 获取会话历史
session_id = "20251027_1156_b4d838"
history = bot.get_history(session_id)

print(f"会话 {session_id} 的完整历史:")
print("=" * 80)

for i, msg in enumerate(history, 1):
    role = msg["role"]
    content = msg["content"]

    role_display = {
        "user": "👤 用户",
        "assistant": "🤖 助手",
        "ai": "🤖 助手",
        "human": "👤 用户"
    }.get(role, role)

    print(f"\n[{i}] {role_display}:")
    print(f"{content}")
    print("-" * 80)

print(f"\n总消息数: {len(history)}")
