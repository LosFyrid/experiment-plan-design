#!/usr/bin/env python3
"""
调试ToolPlan生成 - 打印实际的prompt和LLM响应
"""

import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
moses_root = project_root / "src/external/MOSES"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(moses_root))

os.environ["PROJECT_ROOT"] = str(moses_root) + "/"

from autology_constructor.idea.query_team.schemas import NormalizedQuery, ToolPlan, ToolCallStep
from autology_constructor.idea.query_team.ontology_tools import OntologyTools
from autology_constructor.idea.common.llm_provider import get_default_llm
import json

print("=" * 80)
print("ToolPlan生成调试")
print("=" * 80)

# 创建测试用的normalized query
test_query = NormalizedQuery(
    intent="find information",
    relevant_entities=["duplex_stainless_steel", "ferrite", "austenite"],
    relevant_properties=["mechanical_strength", "corrosion_resistance"],
    filters=None,
    query_type_suggestion="fact-finding"
)

print("\n[1] 测试用的Normalized Query:")
print(json.dumps(test_query.model_dump(), indent=2, ensure_ascii=False))

# 初始化ontology tools（模拟）
print("\n[2] 模拟OntologyTools (简化版):")
class MockOntologyTools:
    def get_class_info(self, class_name: str):
        """获取指定类的详细信息"""
        pass

    def search_classes(self, query: str):
        """搜索相关的类"""
        pass

    def get_properties(self, class_name: str):
        """获取类的属性"""
        pass

mock_tools = MockOntologyTools()

# 生成tool descriptions
import inspect
descriptions = []
for name, method in inspect.getmembers(mock_tools, predicate=inspect.ismethod):
    if not name.startswith("_"):
        sig = inspect.signature(method)
        doc = inspect.getdoc(method)
        desc = f"- {name}{sig}: {doc if doc else 'No description'}"
        descriptions.append(desc)

tool_descriptions_str = "\n" + "-" * 80 + "\n".join(descriptions)
print(tool_descriptions_str)

# 构建system prompt
system_prompt = f"""You are an expert planner for ontology tool execution.
Given a normalized query description and a list of available tools with their descriptions, create a sequential execution plan (a list of JSON objects) to fulfill the query.
Each step in the plan should be a JSON object with 'tool' (the tool name) and 'params' (a dictionary of parameters for the tool).
Only use the provided tools. Ensure the parameters match the tool's requirements based on its description.
Output ONLY the JSON list of plan steps, without any other text or explanation.

Available tools:
{tool_descriptions_str}"""

user_message = f"""Generate an execution plan for the following normalized query:
{test_query.model_dump_json(indent=2)}

Output the plan as a JSON list of steps matching the ToolCallStep structure."""

print("\n[3] System Prompt:")
print("-" * 80)
print(system_prompt)
print("-" * 80)

print("\n[4] User Message:")
print("-" * 80)
print(user_message)
print("-" * 80)

# 测试structured output
print("\n[5] 测试with_structured_output:")

llm = get_default_llm()

# 方法1: 不使用structured output
print("\n  [5.1] 不使用structured output - 直接调用:")
messages = [
    ("system", system_prompt),
    ("user", user_message)
]
try:
    raw_response = llm.invoke(messages)
    print(f"    类型: {type(raw_response)}")
    print(f"    内容: {raw_response.content[:500]}")
except Exception as e:
    print(f"    ❌ 失败: {e}")

# 方法2: 使用structured output
print("\n  [5.2] 使用with_structured_output(ToolPlan):")
try:
    structured_llm = llm.with_structured_output(ToolPlan)
    result = structured_llm.invoke(messages)

    print(f"    返回类型: {type(result)}")
    print(f"    返回值: {result}")

    if result is None:
        print("\n    ⚠️  返回了None！")
        print("    可能原因：")
        print("    1. Prompt说'输出JSON列表'，但Schema期望'{steps: [...]}'对象")
        print("    2. LLM被conflicting instructions搞糊涂了")
        print("    3. Function calling模式解析失败")
    elif isinstance(result, ToolPlan):
        print(f"    ✅ 成功返回ToolPlan对象")
        print(f"    steps数量: {len(result.steps)}")
        for i, step in enumerate(result.steps):
            print(f"      步骤{i+1}: {step.tool} - {step.params}")
    else:
        print(f"    ⚠️  返回了意外类型: {type(result)}")

except Exception as e:
    print(f"    ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 方法3: 修改prompt明确要求对象格式
print("\n  [5.3] 修改Prompt - 明确要求对象格式:")
modified_user_message = f"""Generate an execution plan for the following normalized query:
{test_query.model_dump_json(indent=2)}

Output the plan as a JSON object with a "steps" field containing an array of ToolCallStep objects.
Each step should have "tool" (string) and "params" (object) fields.

Example format:
{{
  "steps": [
    {{"tool": "get_class_info", "params": {{"class_name": "example"}}}},
    {{"tool": "search_classes", "params": {{"query": "example"}}}}
  ]
}}"""

modified_messages = [
    ("system", """You are an expert planner for ontology tool execution.
Given a normalized query and available tools, create an execution plan.
Output as JSON object with a "steps" array."""),
    ("user", modified_user_message)
]

try:
    structured_llm = llm.with_structured_output(ToolPlan)
    result = structured_llm.invoke(modified_messages)

    print(f"    返回类型: {type(result)}")

    if result is None:
        print("    ⚠️  仍然返回None")
    elif isinstance(result, ToolPlan):
        print(f"    ✅ 成功！steps数量: {len(result.steps)}")
    else:
        print(f"    返回值: {result}")

except Exception as e:
    print(f"    ❌ 失败: {e}")

print("\n" + "=" * 80)
print("调试完成")
print("=" * 80)
