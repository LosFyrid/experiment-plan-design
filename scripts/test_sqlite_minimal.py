#!/usr/bin/env python3
"""最小化测试SQLite checkpointer"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models.tongyi import ChatTongyi

# 创建LLM
llm = ChatTongyi(model_name="qwen-plus")

# 创建SQLite checkpointer (with pickle_fallback)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
conn = sqlite3.connect(":memory:", check_same_thread=False)
checkpointer = SqliteSaver(
    conn,
    serde=JsonPlusSerializer(pickle_fallback=True)  # 关键修复！
)
checkpointer.setup()

# 创建agent
agent = create_react_agent(
    model=llm,
    tools=[],  # 无工具
    checkpointer=checkpointer
)

# 测试对话
print("测试1: 发送消息...")
config = {"configurable": {"thread_id": "test_001"}}

try:
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "你好"}]},
        config=config
    )
    print(f"✅ 成功！AI回复: {response['messages'][-1].content[:50]}...")
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试历史恢复
print("\n测试2: 获取历史...")
try:
    state = agent.get_state(config)
    print(f"✅ 成功！消息数: {len(state.values['messages'])}")
except Exception as e:
    print(f"❌ 失败: {e}")
