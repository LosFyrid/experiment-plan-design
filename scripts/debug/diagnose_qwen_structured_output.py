#!/usr/bin/env python3
"""
诊断Qwen模型的structured output行为

这个脚本测试LangChain的with_structured_output()方法在Qwen上的表现
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


class TestStep(BaseModel):
    """测试用的步骤模型"""
    tool: str = Field(description="工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="参数字典")


class TestPlan(BaseModel):
    """测试用的计划模型"""
    steps: List[TestStep] = Field(default_factory=list, description="步骤列表")


def test_qwen_structured_output():
    """测试Qwen的structured output"""

    # 初始化Qwen模型（通过OpenAI兼容接口）
    dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
    if not dashscope_api_key:
        print("错误: DASHSCOPE_API_KEY未设置")
        return

    base_url = os.getenv(
        "QWEN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    print(f"初始化Qwen模型...")
    print(f"  Model: qwen-plus")
    print(f"  Base URL: {base_url}")
    print()

    llm = ChatOpenAI(
        model="qwen-plus",
        temperature=0,
        api_key=dashscope_api_key,
        base_url=base_url,
    )

    # 测试1: 直接调用LLM
    print("=" * 80)
    print("测试1: 直接调用LLM (无结构化输出)")
    print("=" * 80)

    messages = [
        ("system", "You are a helpful assistant."),
        ("user", '''Generate a tool execution plan with 2 steps.
Output as JSON with this structure:
{
  "steps": [
    {"tool": "tool_name", "params": {"param1": "value1"}},
    {"tool": "tool_name2", "params": {"param2": "value2"}}
  ]
}''')
    ]

    response = llm.invoke(messages)
    print(f"\n返回类型: {type(response)}")
    print(f"返回内容类型: {type(response.content)}")
    print(f"\n返回内容:\n{response.content}\n")

    # 测试2: 使用with_structured_output
    print("\n" + "=" * 80)
    print("测试2: 使用with_structured_output(TestPlan)")
    print("=" * 80)

    try:
        structured_llm = llm.with_structured_output(TestPlan)
        print(f"\nStructured LLM类型: {type(structured_llm)}")

        result = structured_llm.invoke(messages)

        print(f"\n返回类型: {type(result)}")
        print(f"返回内容: {result}")

        if isinstance(result, TestPlan):
            print("\n✓ 成功返回TestPlan对象")
            print(f"  steps数量: {len(result.steps)}")
            for i, step in enumerate(result.steps):
                print(f"  步骤{i+1}: tool={step.tool}, params={step.params}")
        elif isinstance(result, dict):
            print("\n⚠ 返回dict而非TestPlan对象")
            print(f"  dict内容: {json.dumps(result, indent=2, ensure_ascii=False)}")

            # 尝试手动构造
            if "steps" in result:
                print("\n尝试手动构造TestPlan...")
                try:
                    manual_plan = TestPlan(**result)
                    print("✓ 手动构造成功")
                except Exception as e:
                    print(f"✗ 手动构造失败: {e}")
        else:
            print(f"\n✗ 意外的返回类型: {type(result)}")
            print(f"  原始返回: {result}")

            # 检查是否有content属性
            if hasattr(result, 'content'):
                print(f"\n  result.content类型: {type(result.content)}")
                print(f"  result.content值: {result.content}")

                # 尝试解析content
                if isinstance(result.content, str):
                    print("\n尝试解析content字符串为JSON...")
                    try:
                        parsed = json.loads(result.content)
                        print("✓ JSON解析成功")
                        print(f"  解析结果: {json.dumps(parsed, indent=2, ensure_ascii=False)}")

                        # 尝试构造TestPlan
                        if isinstance(parsed, dict) and "steps" in parsed:
                            plan = TestPlan(**parsed)
                            print("✓ 从解析的JSON构造TestPlan成功")
                    except json.JSONDecodeError as e:
                        print(f"✗ JSON解析失败: {e}")

    except Exception as e:
        print(f"\n✗ 异常发生: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # 测试3: 使用method="json_mode"参数
    print("\n" + "=" * 80)
    print("测试3: 使用with_structured_output(TestPlan, method='json_mode')")
    print("=" * 80)

    try:
        structured_llm_json = llm.with_structured_output(TestPlan, method="json_mode")
        print(f"\nStructured LLM类型: {type(structured_llm_json)}")

        result = structured_llm_json.invoke(messages)

        print(f"\n返回类型: {type(result)}")
        print(f"返回内容: {result}")

        if isinstance(result, TestPlan):
            print("\n✓ 成功返回TestPlan对象")
        else:
            print(f"\n⚠ 返回类型: {type(result)}")

    except Exception as e:
        print(f"\n✗ 异常发生: {type(e).__name__}: {e}")
        print("注意: 某些模型可能不支持json_mode")


if __name__ == "__main__":
    test_qwen_structured_output()
