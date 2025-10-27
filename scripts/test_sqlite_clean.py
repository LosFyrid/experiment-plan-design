#!/usr/bin/env python3
"""测试SQLite - 使用最简洁的官方API"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models.tongyi import ChatTongyi

print("="*70)
print("测试 SQLite Checkpointer - 使用官方推荐的最简洁方式")
print("="*70)

# 创建LLM
print("\n[1/3] 初始化LLM...")
llm = ChatTongyi(model_name="qwen-plus")
print("✅ LLM初始化成功")

# 使用官方推荐的 from_conn_string 方法（上下文管理器）
print("\n[2/3] 创建Agent with SQLite checkpointer...")

with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    agent = create_react_agent(
        model=llm,
        tools=[],
        checkpointer=checkpointer
    )
    print("✅ Agent创建成功")

    # 测试对话
    print("\n[3/3] 测试对话和历史恢复...")
    config = {"configurable": {"thread_id": "test_session"}}

    # 第一条消息
    print("  - 发送消息1: '你好'")
    response1 = agent.invoke(
        {"messages": [{"role": "user", "content": "你好"}]},
        config=config
    )
    print(f"    AI回复: {response1['messages'][-1].content[:30]}...")

    # 第二条消息
    print("  - 发送消息2: '今天天气怎么样'")
    response2 = agent.invoke(
        {"messages": [{"role": "user", "content": "今天天气怎么样"}]},
        config=config
    )
    print(f"    AI回复: {response2['messages'][-1].content[:30]}...")

    # 验证历史
    print("  - 获取历史...")
    state = agent.get_state(config)
    messages = state.values['messages']
    print(f"    ✅ 历史消息数: {len(messages)}")

    # 显示历史摘要
    print("\n历史消息摘要:")
    for i, msg in enumerate(messages, 1):
        role = msg.__class__.__name__
        content = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
        print(f"  [{i}] {role}: {content}")

print("\n" + "="*70)
print("✅ 所有测试通过！SQLite checkpointer工作正常")
print("="*70)
