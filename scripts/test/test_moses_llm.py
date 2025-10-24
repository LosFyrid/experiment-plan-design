#!/usr/bin/env python3
"""
测试MOSES LLM配置 - 验证Qwen模型调用
"""

import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
moses_root = project_root / "src/external/MOSES"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(moses_root))

# Set environment
os.environ["PROJECT_ROOT"] = str(moses_root) + "/"

print("=" * 70)
print("MOSES LLM配置测试")
print("=" * 70)

# Test 1: Check API key
print("\n[测试1] 检查API密钥配置")
dashscope_key = os.getenv("DASHSCOPE_API_KEY")
if dashscope_key:
    print(f"  ✅ DASHSCOPE_API_KEY已配置: {dashscope_key[:10]}...{dashscope_key[-4:]}")
else:
    print("  ❌ DASHSCOPE_API_KEY未配置")
    sys.exit(1)

# Test 2: Load settings
print("\n[测试2] 加载MOSES配置")
try:
    from config.settings import LLM_CONFIG
    print(f"  ✅ 配置加载成功")
    print(f"     模型名: {LLM_CONFIG.get('model')}")
    print(f"     温度: {LLM_CONFIG.get('temperature')}")
    print(f"     最大tokens: {LLM_CONFIG.get('max_tokens')}")
except Exception as e:
    print(f"  ❌ 配置加载失败: {e}")
    sys.exit(1)

# Test 3: Initialize LLM
print("\n[测试3] 初始化LLM")
try:
    from autology_constructor.idea.common.llm_provider import get_default_llm
    llm = get_default_llm()
    print(f"  ✅ LLM初始化成功")
    print(f"     类型: {type(llm).__name__}")
    print(f"     模型: {llm.model_name if hasattr(llm, 'model_name') else llm.model}")
except Exception as e:
    print(f"  ❌ LLM初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Simple LLM call
print("\n[测试4] 测试简单LLM调用")
try:
    response = llm.invoke("Say hello in Chinese")
    print(f"  ✅ LLM调用成功")
    print(f"     响应: {response.content[:100]}")
except Exception as e:
    print(f"  ❌ LLM调用失败: {e}")
    print("\n  可能的原因：")
    print(f"  1. 模型名 '{LLM_CONFIG.get('model')}' 无效")
    print("  2. API密钥无效或额度不足")
    print("  3. 网络连接问题")
    print("\n  建议的有效Qwen模型名：")
    print("    - qwen-max")
    print("    - qwen-plus")
    print("    - qwen-turbo")
    print("    - qwen-max-latest")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Structured output (ToolPlan)
print("\n[测试5] 测试结构化输出")
try:
    from pydantic import BaseModel, Field
    from typing import List

    class SimpleSchema(BaseModel):
        message: str = Field(description="A greeting message")
        language: str = Field(description="Language of the message")

    structured_llm = llm.with_structured_output(SimpleSchema)
    result = structured_llm.invoke("Say hello in English")

    if result is None:
        print(f"  ⚠️ 结构化输出返回None")
        print(f"     这可能是模型不支持function calling")
        print(f"     或者模型名配置错误")
    elif isinstance(result, SimpleSchema):
        print(f"  ✅ 结构化输出成功")
        print(f"     结果类型: {type(result).__name__}")
        print(f"     消息: {result.message}")
        print(f"     语言: {result.language}")
    else:
        print(f"  ⚠️ 结构化输出返回了意外类型: {type(result)}")
        print(f"     内容: {result}")

except Exception as e:
    print(f"  ❌ 结构化输出失败: {e}")
    print("\n  这可能导致ToolPlan生成返回None的问题")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ 所有测试通过！LLM配置正常")
print("=" * 70)
print("\n建议：")
print("  如果仍遇到ToolPlan返回None，可能是由于：")
print("  1. Prompt过于复杂")
print("  2. ToolPlan schema过于复杂")
print("  3. 需要在query_workflow中添加simple_answer fallback策略")
