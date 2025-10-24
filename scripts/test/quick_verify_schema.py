#!/usr/bin/env python3
"""
快速验证MOSES Schema修复 - 最小依赖版本
直接测试schemas.py，避免导入query_workflow
"""

import sys
from pathlib import Path

# 直接导入schemas模块，避免触发其他依赖
project_root = Path(__file__).parent.parent.parent
schemas_path = project_root / "src/external/MOSES/autology_constructor/idea/query_team"
sys.path.insert(0, str(schemas_path))

# 只导入schemas模块
import schemas

NormalizedQuery = schemas.NormalizedQuery
NormalizedQueryBody = schemas.NormalizedQueryBody

print("\n╔" + "=" * 58 + "╗")
print("║  MOSES Schema修复快速验证".center(60) + "║")
print("╚" + "=" * 58 + "╝\n")

# 测试1: 空字符串（原始bug）
print("[测试1] NormalizedQueryBody - filters空字符串 '' -> None")
try:
    body = NormalizedQueryBody(
        intent="test query",
        relevant_entities=["TestClass"],
        filters=""  # ⬅️ 这是导致原始错误的输入
    )
    assert body.filters is None
    print("  ✅ 通过\n")
except Exception as e:
    print(f"  ❌ 失败: {e}\n")
    sys.exit(1)

# 测试2: 空字典
print("[测试2] NormalizedQueryBody - filters空字典 {} -> None")
try:
    body = NormalizedQueryBody(
        intent="test",
        relevant_entities=["TestClass"],
        filters={}
    )
    assert body.filters is None
    print("  ✅ 通过\n")
except Exception as e:
    print(f"  ❌ 失败: {e}\n")
    sys.exit(1)

# 测试3: 正常字典
print("[测试3] NormalizedQueryBody - 正常字典保持不变")
try:
    test_filters = {"prop": "value"}
    body = NormalizedQueryBody(
        intent="test",
        relevant_entities=["TestClass"],
        filters=test_filters
    )
    assert body.filters == test_filters
    print(f"  ✅ 通过: {body.filters}\n")
except Exception as e:
    print(f"  ❌ 失败: {e}\n")
    sys.exit(1)

# 测试4: NormalizedQuery同样测试
print("[测试4] NormalizedQuery - filters空字符串 '' -> None")
try:
    query = NormalizedQuery(
        intent="test",
        relevant_entities=["TestClass"],
        relevant_properties=["prop1"],
        filters=""
    )
    assert query.filters is None
    print("  ✅ 通过\n")
except Exception as e:
    print(f"  ❌ 失败: {e}\n")
    sys.exit(1)

# 模拟真实LLM输出
print("[场景模拟] LLM返回空字符串filters（原始bug场景）")
llm_output = {
    "intent": "find information",
    "relevant_entities": ["DuplexStainlessSteel"],
    "filters": "",  # ⬅️ 导致原始Pydantic验证错误
    "query_type_suggestion": "fact-finding"
}

try:
    body = NormalizedQueryBody(**llm_output)
    print(f"  ✅ 成功创建Schema实例")
    print(f"     intent: {body.intent}")
    print(f"     relevant_entities: {body.relevant_entities}")
    print(f"     filters: {body.filters} (type: {type(body.filters).__name__})\n")
except Exception as e:
    print(f"  ❌ 失败（修复前会出现的错误）: {e}\n")
    sys.exit(1)

# 总结
print("=" * 60)
print("✅ 所有测试通过！修复验证成功！")
print("=" * 60)
print("\n修复内容：")
print("  - 添加了 NormalizedQueryBody.filters 字段验证器")
print("  - 添加了 NormalizedQuery.filters 字段验证器")
print("  - 空字符串 '' 和空字典 {} 会被转换为 None")
print("  - 正常字典值保持不变")
print("\n影响：")
print("  ✅ 解决了 'Input should be a valid dictionary' Pydantic错误")
print("  ✅ MOSES查询标准化流程可以正常执行")
print("\n下一步：")
print("  运行完整测试: python examples/chatbot_cli.py")
print("  输入查询验证端到端流程")
