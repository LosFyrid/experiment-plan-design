#!/usr/bin/env python3
"""
快速测试修复后的MOSES ToolPlanner
"""

import os
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "external" / "MOSES"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from autology_constructor.idea.common.llm_provider import get_default_llm
from autology_constructor.idea.query_team.query_agents import ToolPlannerAgent
from autology_constructor.idea.query_team.ontology_tools import OntologyTools
from autology_constructor.idea.query_team.schemas import NormalizedQuery
from config.settings import OntologySettings

print("=" * 80)
print("测试修复后的ToolPlannerAgent")
print("=" * 80)

# 初始化LLM
llm = get_default_llm()
print(f"✓ LLM initialized: {getattr(llm, 'model', getattr(llm, 'model_name', 'unknown'))}\n")

# 初始化ToolPlannerAgent
planner = ToolPlannerAgent(llm)
print("✓ ToolPlannerAgent initialized\n")

# 创建测试用的normalized query
test_query = NormalizedQuery(
    intent="find information",
    relevant_entities=["duplex_stainless_steel", "mechanical_properties"],
    relevant_properties=["tensile_strength", "hardness"],
    filters=None,
    query_type_suggestion="fact-finding"
)
print(f"✓ Test query created\n")

# 初始化OntologyTools (简化版，不需要完整本体)
class MockOntologyTools:
    """模拟OntologyTools用于测试"""
    def get_class_info(self, class_names):
        """Get information about classes"""
        pass

    def get_class_properties(self, class_names):
        """Get properties of classes"""
        pass

    def get_related_classes(self, class_names):
        """Get related classes"""
        pass

mock_tools = MockOntologyTools()
print("✓ Mock OntologyTools created\n")

# 测试generate_plan
print("-" * 80)
print("调用generate_plan()...")
print("-" * 80)

try:
    plan_result = planner.generate_plan(test_query, mock_tools)

    print(f"\n返回类型: {type(plan_result)}")

    if hasattr(plan_result, 'steps'):
        print(f"✓ 成功返回ToolPlan对象")
        print(f"  步骤数: {len(plan_result.steps)}")
        for i, step in enumerate(plan_result.steps):
            print(f"  步骤{i+1}: {step.tool}({step.params})")
    elif isinstance(plan_result, dict) and plan_result.get("error"):
        print(f"✗ 返回错误: {plan_result['error']}")
    else:
        print(f"⚠ 意外的返回类型: {type(plan_result)}")
        print(f"  内容: {plan_result}")

except Exception as e:
    print(f"\n✗ 测试失败:")
    print(f"  异常类型: {type(e).__name__}")
    print(f"  异常信息: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
