#!/usr/bin/env python3
"""调试metadata内容"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.pregel import Pregel
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models.tongyi import ChatTongyi

# 创建LLM
llm = ChatTongyi(model_name="qwen-plus")

# 创建checkpointer
conn = sqlite3.connect(":memory:", check_same_thread=False)
checkpointer = SqliteSaver(
    conn,
    serde=JsonPlusSerializer(pickle_fallback=True)
)
checkpointer.setup()

# 创建agent
agent = create_react_agent(
    model=llm,
    tools=[],
    checkpointer=checkpointer
)

# Monkey patch put方法来查看metadata
original_put = checkpointer.put

def debug_put(config, checkpoint, metadata, new_versions):
    print("\n" + "="*70)
    print("DEBUG: checkpointer.put() called")
    print("="*70)
    print(f"Config: {config}")
    print(f"Metadata type: {type(metadata)}")
    print(f"Metadata keys: {metadata.keys() if isinstance(metadata, dict) else 'N/A'}")
    print(f"Metadata content:")

    if isinstance(metadata, dict):
        for key, value in metadata.items():
            print(f"  {key}: {type(value)} = {value if not isinstance(value, (dict, list)) else '...'}")
            if isinstance(value, (dict, list)):
                print(f"       {value}")

    # 调用原始方法
    return original_put(config, checkpoint, metadata, new_versions)

checkpointer.put = debug_put

# 测试
print("\n发送测试消息...")
config = {"configurable": {"thread_id": "test_001"}}

try:
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "你好"}]},
        config=config
    )
    print(f"✅ 成功！")
except Exception as e:
    print(f"❌ 失败: {e}")
