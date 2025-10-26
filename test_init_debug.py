#!/usr/bin/env python3
"""调试CLI初始化问题 - 逐步测试每个组件"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

def test_step(step_name, func):
    """测试某个步骤并记录耗时"""
    print(f"\n{'='*70}")
    print(f"[TEST] 开始: {step_name}")
    print(f"{'='*70}")
    start = time.time()

    try:
        result = func()
        duration = time.time() - start
        print(f"\n✅ {step_name} 完成 (耗时: {duration:.2f}s)")
        return result, duration
    except Exception as e:
        duration = time.time() - start
        print(f"\n❌ {step_name} 失败 (耗时: {duration:.2f}s)")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None, duration

def test_chatbot_config():
    """测试1: 加载Chatbot配置"""
    from chatbot.config import load_config
    config = load_config("configs/chatbot_config.yaml")
    print(f"配置加载成功: {config.keys()}")
    return config

def test_llm_init(config):
    """测试2: 初始化LLM"""
    from langchain_community.chat_models.tongyi import ChatTongyi

    llm_config = config["chatbot"]["llm"]
    model_kwargs = {
        "temperature": llm_config.get("temperature", 0.7),
        "max_tokens": llm_config.get("max_tokens", 4096),
    }

    if llm_config.get("enable_thinking", False):
        model_kwargs["enable_thinking"] = True
        model_kwargs["incremental_output"] = True

    llm = ChatTongyi(
        model_name=llm_config["model_name"],
        model_kwargs=model_kwargs
    )
    print(f"LLM初始化成功: {llm_config['model_name']}")
    return llm

def test_moses_wrapper_creation():
    """测试3: 创建MOSES Wrapper（不启动初始化）"""
    from chatbot.config import load_config
    from chatbot.tools import MOSESToolWrapper

    config = load_config("configs/chatbot_config.yaml")
    wrapper = MOSESToolWrapper(config["chatbot"]["moses"], auto_init=False)
    print("MOSES Wrapper创建成功（未启动后台初始化）")
    return wrapper

def test_moses_init():
    """测试4: MOSES后台初始化（带超时）"""
    from chatbot.config import load_config
    from chatbot.tools import MOSESToolWrapper
    import threading

    config = load_config("configs/chatbot_config.yaml")
    wrapper = MOSESToolWrapper(config["chatbot"]["moses"], auto_init=True)

    print("等待MOSES初始化完成...")
    print("（如果卡住超过30秒，说明问题在MOSES初始化）")

    # 等待初始化，最多30秒
    timeout = 30
    start = time.time()

    while not wrapper._init_event.is_set():
        elapsed = time.time() - start
        if elapsed > timeout:
            print(f"\n⚠️ MOSES初始化超时（{timeout}秒）")
            print("问题可能在：")
            print("  1. 本体文件加载")
            print("  2. QueryManager初始化")
            print("  3. 统计信息计算")
            return wrapper

        print(f"  等待中... ({elapsed:.1f}s / {timeout}s)", end="\r")
        time.sleep(0.5)

    print("\nMOSES初始化完成")
    return wrapper

def test_checkpointer():
    """测试5: 初始化Checkpointer"""
    from chatbot.config import load_config
    from langgraph.checkpoint.memory import MemorySaver

    config = load_config("configs/chatbot_config.yaml")
    memory_config = config["chatbot"]["memory"]
    memory_type = memory_config.get("type", "in_memory")

    if memory_type == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            sqlite_path = memory_config["sqlite_path"]
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            checkpointer = SqliteSaver.from_conn_string(sqlite_path)
            print(f"SQLite Checkpointer初始化成功: {sqlite_path}")
        except ImportError:
            checkpointer = MemorySaver()
            print("SQLite不可用，使用MemorySaver")
    else:
        checkpointer = MemorySaver()
        print("使用MemorySaver")

    return checkpointer

def test_agent_creation(llm, wrapper, checkpointer):
    """测试6: 创建LangGraph Agent"""
    from langgraph.prebuilt import create_react_agent
    from chatbot.config import load_config

    config = load_config("configs/chatbot_config.yaml")
    system_prompt = config["chatbot"].get(
        "system_prompt",
        "你是一个专业的化学实验助手。"
    )

    moses_tool = wrapper.get_tool()
    agent = create_react_agent(
        model=llm,
        tools=[moses_tool],
        checkpointer=checkpointer,
        state_modifier=system_prompt
    )
    print("LangGraph Agent创建成功")
    return agent

def test_task_scheduler():
    """测试7: 初始化TaskScheduler"""
    from workflow.task_scheduler import TaskScheduler

    scheduler = TaskScheduler()
    print("TaskScheduler初始化成功")
    return scheduler

def main():
    """主测试流程"""
    print("\n" + "="*70)
    print("CLI初始化调试 - 逐步测试")
    print("="*70)

    total_start = time.time()
    results = {}

    # 测试1: Chatbot配置
    config, t1 = test_step("加载Chatbot配置", test_chatbot_config)
    results["config"] = t1

    if config is None:
        print("\n❌ 配置加载失败，无法继续")
        return

    # 测试2: LLM初始化
    llm, t2 = test_step("初始化LLM", lambda: test_llm_init(config))
    results["llm"] = t2

    # 测试3: MOSES Wrapper创建（不启动初始化）
    wrapper_no_init, t3 = test_step(
        "创建MOSES Wrapper（无初始化）",
        test_moses_wrapper_creation
    )
    results["moses_wrapper_creation"] = t3

    # 测试4: MOSES初始化（这是可能卡住的地方）
    wrapper, t4 = test_step("MOSES后台初始化", test_moses_init)
    results["moses_init"] = t4

    # 测试5: Checkpointer
    checkpointer, t5 = test_step("初始化Checkpointer", test_checkpointer)
    results["checkpointer"] = t5

    # 测试6: Agent创建
    if llm and wrapper and checkpointer:
        agent, t6 = test_step(
            "创建LangGraph Agent",
            lambda: test_agent_creation(llm, wrapper, checkpointer)
        )
        results["agent"] = t6

    # 测试7: TaskScheduler
    scheduler, t7 = test_step("初始化TaskScheduler", test_task_scheduler)
    results["scheduler"] = t7

    # 总结
    total_duration = time.time() - total_start

    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"总耗时: {total_duration:.2f}s\n")

    print("各步骤耗时:")
    for step, duration in results.items():
        if duration:
            percentage = (duration / total_duration) * 100
            print(f"  {step:30s}: {duration:6.2f}s ({percentage:5.1f}%)")

    # 找出最慢的步骤
    if results:
        slowest = max(results.items(), key=lambda x: x[1] if x[1] else 0)
        print(f"\n⚠️ 最慢的步骤: {slowest[0]} ({slowest[1]:.2f}s)")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()
