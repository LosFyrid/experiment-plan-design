#!/usr/bin/env python3
"""
验证MOSES Schema修复 - filters字段验证器测试

问题：LLM返回空字符串""导致Pydantic验证失败
修复：添加field_validator将空字符串/空字典转换为None
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.external.MOSES.autology_constructor.idea.query_team.schemas import (
    NormalizedQuery,
    NormalizedQueryBody
)

def test_normalized_query_body():
    """测试NormalizedQueryBody的filters字段验证器"""
    print("=" * 60)
    print("测试 NormalizedQueryBody")
    print("=" * 60)

    # 测试1: 空字符串应转换为None
    print("\n[测试1] 空字符串 '' -> None")
    try:
        body = NormalizedQueryBody(
            intent="test query",
            relevant_entities=["TestClass"],
            filters=""  # 这是导致原始错误的输入
        )
        assert body.filters is None, f"期望None，但得到 {body.filters}"
        print("  ✅ 通过: 空字符串成功转换为None")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试2: 空字典应转换为None
    print("\n[测试2] 空字典 {} -> None")
    try:
        body = NormalizedQueryBody(
            intent="test query",
            relevant_entities=["TestClass"],
            filters={}
        )
        assert body.filters is None, f"期望None，但得到 {body.filters}"
        print("  ✅ 通过: 空字典成功转换为None")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试3: None应保持为None
    print("\n[测试3] None -> None (保持不变)")
    try:
        body = NormalizedQueryBody(
            intent="test query",
            relevant_entities=["TestClass"],
            filters=None
        )
        assert body.filters is None, f"期望None，但得到 {body.filters}"
        print("  ✅ 通过: None值保持不变")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试4: 正常字典应保持不变
    print("\n[测试4] 正常字典 {'key': 'value'} -> {'key': 'value'} (保持不变)")
    try:
        test_filters = {"property": "value", "another": 123}
        body = NormalizedQueryBody(
            intent="test query",
            relevant_entities=["TestClass"],
            filters=test_filters
        )
        assert body.filters == test_filters, f"期望 {test_filters}，但得到 {body.filters}"
        print(f"  ✅ 通过: 字典内容保持不变 {body.filters}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试5: 省略filters字段（使用默认值None）
    print("\n[测试5] 省略filters字段 -> None (默认值)")
    try:
        body = NormalizedQueryBody(
            intent="test query",
            relevant_entities=["TestClass"]
            # filters字段省略
        )
        assert body.filters is None, f"期望None，但得到 {body.filters}"
        print("  ✅ 通过: 默认值为None")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    return True


def test_normalized_query():
    """测试NormalizedQuery的filters字段验证器"""
    print("\n" + "=" * 60)
    print("测试 NormalizedQuery")
    print("=" * 60)

    # 测试1: 空字符串应转换为None
    print("\n[测试1] 空字符串 '' -> None")
    try:
        query = NormalizedQuery(
            intent="test query",
            relevant_entities=["TestClass"],
            relevant_properties=["prop1"],
            filters=""
        )
        assert query.filters is None, f"期望None，但得到 {query.filters}"
        print("  ✅ 通过: 空字符串成功转换为None")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 测试2: 正常字典应保持不变
    print("\n[测试2] 正常字典保持不变")
    try:
        test_filters = {"temperature": ">100", "pressure": "<5"}
        query = NormalizedQuery(
            intent="test query",
            relevant_entities=["TestClass"],
            relevant_properties=["prop1"],
            filters=test_filters
        )
        assert query.filters == test_filters, f"期望 {test_filters}，但得到 {query.filters}"
        print(f"  ✅ 通过: 字典内容保持不变 {query.filters}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    return True


def simulate_llm_output():
    """模拟LLM输出场景"""
    print("\n" + "=" * 60)
    print("模拟真实LLM输出场景")
    print("=" * 60)

    # 场景1: LLM返回空字符串（原始bug场景）
    print("\n[场景1] 模拟LLM返回filters=''")
    llm_output = {
        "intent": "find information",
        "relevant_entities": ["DuplexStainlessSteel", "HotDeformation"],
        "filters": "",  # ⬅️ 这是导致原始错误的LLM输出
        "query_type_suggestion": "fact-finding"
    }

    try:
        body = NormalizedQueryBody(**llm_output)
        print(f"  ✅ 成功创建Schema实例")
        print(f"     - intent: {body.intent}")
        print(f"     - relevant_entities: {body.relevant_entities}")
        print(f"     - filters: {body.filters} (类型: {type(body.filters).__name__})")
        print(f"     - query_type_suggestion: {body.query_type_suggestion}")
    except Exception as e:
        print(f"  ❌ 失败（这是修复前会发生的错误）:")
        print(f"     {e}")
        return False

    # 场景2: LLM返回有效的filters字典
    print("\n[场景2] 模拟LLM返回filters={'property': 'value'}")
    llm_output_with_filters = {
        "intent": "find entities with constraints",
        "relevant_entities": ["Material"],
        "filters": {"yield_strength": ">500 MPa", "corrosion_resistance": "excellent"},
        "query_type_suggestion": "filtered-search"
    }

    try:
        body = NormalizedQueryBody(**llm_output_with_filters)
        print(f"  ✅ 成功创建Schema实例")
        print(f"     - filters: {body.filters}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    return True


def main():
    """主测试入口"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  MOSES Schema修复验证 - filters字段验证器测试".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")

    all_passed = True

    # 运行测试
    if not test_normalized_query_body():
        all_passed = False

    if not test_normalized_query():
        all_passed = False

    if not simulate_llm_output():
        all_passed = False

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if all_passed:
        print("\n✅ 所有测试通过！")
        print("\n修复验证成功：")
        print("  - NormalizedQueryBody.filters 验证器工作正常")
        print("  - NormalizedQuery.filters 验证器工作正常")
        print("  - 能够正确处理LLM返回的空字符串")
        print("  - 不影响正常的字典输入")
        print("\n下一步：运行完整的chatbot_cli.py测试")
        return 0
    else:
        print("\n❌ 部分测试失败")
        print("\n请检查：")
        print("  1. src/external/MOSES/autology_constructor/idea/query_team/schemas.py")
        print("  2. 确认field_validator已正确添加")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
