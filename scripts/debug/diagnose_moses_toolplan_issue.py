#!/usr/bin/env python3
"""
诊断MOSES ToolPlan生成问题

模拟MOSES的完整调用链，找出Qwen返回字符串而不是对象的原因
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "external" / "MOSES"))

# Load .env file
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI


# 使用MOSES的实际schema
class ToolCallStep(BaseModel):
    """Represents a single step in a tool execution plan."""
    tool: str = Field(description="The name of the tool to be called. Must be one of the available OntologyTools methods.")
    params: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of parameters required to call the specified tool.")


class ToolPlan(BaseModel):
    """Represents the planned sequence of tool calls."""
    steps: List[ToolCallStep] = Field(default_factory=list, description="The sequence of tool calls to execute.")


def test_moses_style_prompt():
    """使用类似MOSES的prompt测试"""

    dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
    if not dashscope_api_key:
        print("错误: DASHSCOPE_API_KEY未设置")
        return

    base_url = os.getenv(
        "QWEN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    print("=" * 80)
    print("测试: 模拟MOSES ToolPlanner的完整调用链")
    print("=" * 80)

    # 使用qwen-plus（MOSES配置中使用的模型）
    llm = ChatOpenAI(
        model="qwen-plus",
        temperature=0,
        api_key=dashscope_api_key,
        base_url=base_url,
    )

    # 模拟MOSES的实际prompt
    system_prompt = """You are a tool planning agent. Given a structured query, you must generate an execution plan.

Available tools:
- parse_hierarchy(class_name: str): Parse the hierarchical structure
- get_class_info(class_name: str): Get class information
- search_entities(query: str): Search for entities

Output the plan as a JSON object with a "steps" array."""

    normalized_query = {
        "intent": "find information",
        "relevant_entities": ["Material", "Process"],
        "relevant_properties": ["temperature", "pressure"],
        "filters": None,
        "query_type_suggestion": "fact-finding"
    }

    user_message = f"""Generate an execution plan for the following normalized query:
{json.dumps(normalized_query, indent=2, ensure_ascii=False)}

Output the plan as a JSON object with a "steps" array. Each step should match the ToolCallStep structure (tool name and params dictionary)."""

    messages = [
        ("system", system_prompt),
        ("user", user_message)
    ]

    print(f"\n模型: qwen-plus")
    print(f"Base URL: {base_url}\n")

    # 测试1: 不使用structured output
    print("-" * 80)
    print("测试1: 不使用structured output (baseline)")
    print("-" * 80)

    response = llm.invoke(messages)
    print(f"返回类型: {type(response)}")
    print(f"Content类型: {type(response.content)}")
    print(f"Content值:\n{response.content}\n")

    # 测试2: 使用with_structured_output
    print("-" * 80)
    print("测试2: 使用with_structured_output(ToolPlan)")
    print("-" * 80)

    structured_llm = llm.with_structured_output(ToolPlan)
    print(f"Structured LLM类型: {type(structured_llm)}")

    raw_plan = structured_llm.invoke(messages)

    print(f"\nraw_plan类型: {type(raw_plan)}")
    print(f"raw_plan值: {raw_plan}")
    print(f"raw_plan是ToolPlan? {isinstance(raw_plan, ToolPlan)}")
    print(f"raw_plan是dict? {isinstance(raw_plan, dict)}")
    print(f"raw_plan是str? {isinstance(raw_plan, str)}")

    # 如果是dict，检查steps字段
    if isinstance(raw_plan, dict):
        print(f"\nraw_plan dict keys: {raw_plan.keys()}")
        if "steps" in raw_plan:
            steps = raw_plan["steps"]
            print(f"steps类型: {type(steps)}")
            print(f"steps值: {steps}")

            # 尝试构造ToolPlan
            try:
                plan = ToolPlan(**raw_plan)
                print(f"\n✓ 成功从dict构造ToolPlan")
                print(f"  步骤数: {len(plan.steps)}")
            except Exception as e:
                print(f"\n✗ 从dict构造ToolPlan失败: {e}")
                print(f"  异常类型: {type(e).__name__}")

                # 如果steps是字符串，尝试解析
                if isinstance(steps, str):
                    print(f"\n  检测到steps是字符串，尝试JSON解析...")
                    try:
                        parsed_steps = json.loads(steps)
                        print(f"  ✓ JSON解析成功")
                        print(f"  解析后类型: {type(parsed_steps)}")

                        # 尝试用解析后的steps构造
                        raw_plan["steps"] = parsed_steps
                        plan = ToolPlan(**raw_plan)
                        print(f"  ✓ 用解析后的steps成功构造ToolPlan")
                    except Exception as parse_err:
                        print(f"  ✗ JSON解析或构造失败: {parse_err}")

    # 测试3: 检查多次调用的一致性
    print("\n" + "-" * 80)
    print("测试3: 多次调用一致性测试（调用5次）")
    print("-" * 80)

    for i in range(5):
        raw_plan = structured_llm.invoke(messages)
        print(f"第{i+1}次调用: type={type(raw_plan).__name__}, is_ToolPlan={isinstance(raw_plan, ToolPlan)}")

        if isinstance(raw_plan, dict) and "steps" in raw_plan:
            print(f"  steps类型: {type(raw_plan['steps']).__name__}")

    # 测试4: 使用include_raw参数
    print("\n" + "-" * 80)
    print("测试4: 使用with_structured_output(ToolPlan, include_raw=True)")
    print("-" * 80)

    try:
        structured_llm_raw = llm.with_structured_output(ToolPlan, include_raw=True)
        result = structured_llm_raw.invoke(messages)
        print(f"返回类型: {type(result)}")
        print(f"返回keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        if isinstance(result, dict):
            if "parsed" in result:
                print(f"parsed类型: {type(result['parsed'])}")
                print(f"parsed值: {result['parsed']}")
            if "raw" in result:
                print(f"raw类型: {type(result['raw'])}")
                if hasattr(result['raw'], 'content'):
                    print(f"raw.content: {result['raw'].content[:200]}...")
    except Exception as e:
        print(f"include_raw测试失败: {e}")


if __name__ == "__main__":
    test_moses_style_prompt()
