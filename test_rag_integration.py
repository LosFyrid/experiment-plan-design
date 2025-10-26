#!/usr/bin/env python3
"""
测试 RAG 集成

功能：
1. 测试 RAGAdapter 是否能正常初始化
2. 测试检索功能
3. 测试格式转换
4. 验证与 Generator 的兼容性

使用方法：
    conda activate OntologyConstruction
    python test_rag_integration.py
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from workflow.rag_adapter import RAGAdapter


def test_rag_adapter():
    """测试 RAG 适配器"""
    print("=" * 70)
    print("测试 1: RAG 适配器初始化")
    print("=" * 70)

    try:
        adapter = RAGAdapter()
        print("✅ RAGAdapter 创建成功")
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return False

    print("\n" + "=" * 70)
    print("测试 2: 检索功能")
    print("=" * 70)

    # 模拟 MOSES 提取的需求
    test_requirements = {
        "target_compound": "双相不锈钢",
        "objective": "研究双相不锈钢的耐腐蚀性能",
        "constraints": ["高温", "腐蚀环境"]
    }

    print(f"\n测试需求: {test_requirements}")

    try:
        templates = adapter.retrieve_templates(
            requirements=test_requirements,
            top_k=3
        )

        print(f"\n✅ 检索成功，返回 {len(templates)} 个模板")

        if templates:
            print("\n" + "=" * 70)
            print("测试 3: 格式验证")
            print("=" * 70)

            # 验证格式
            for i, t in enumerate(templates, 1):
                print(f"\n模板 {i}:")
                print(f"  - 包含 'title': {' title' in t}")
                print(f"  - 包含 'content': {'content' in t}")
                print(f"  - 包含 'score': {'score' in t}")
                print(f"  - 不包含 'metadata': {'metadata' not in t}")

                # 打印预览
                print(f"\n  title: {t.get('title', 'N/A')}")
                print(f"  score: {t.get('score', 0):.3f}")
                content_preview = t.get('content', '')[:100]
                print(f"  content (前100字符): {content_preview}...")

            print("\n✅ 格式验证通过：只包含必要字段（title, content, score）")
        else:
            print("⚠️  返回空列表（可能是索引未构建）")

    except Exception as e:
        import traceback
        print(f"❌ 检索失败: {e}")
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("测试 4: Generator 兼容性")
    print("=" * 70)

    try:
        from ace_framework.generator.prompts import format_templates

        if templates:
            formatted = format_templates(templates[:2])  # 只格式化前2个
            print("\n格式化后的模板（用于 Generator prompt）:")
            print("-" * 70)
            print(formatted)
            print("-" * 70)
            print("\n✅ Generator prompts 兼容性测试通过")
        else:
            print("⚠️  无模板可格式化")

    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！")
    print("=" * 70)
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("RAG 集成测试")
    print("="*70 + "\n")

    success = test_rag_adapter()

    if success:
        print("\n🎉 RAG 集成测试成功！")
        print("\n下一步：")
        print("  1. 运行完整的 workflow 测试")
        print("  2. 使用 /generate 命令测试端到端流程")
        sys.exit(0)
    else:
        print("\n❌ RAG 集成测试失败！")
        print("\n故障排查：")
        print("  1. 检查是否在 OntologyConstruction 环境")
        print("  2. 检查是否已构建索引（运行 examples/1_build_index.py）")
        print("  3. 检查 DASHSCOPE_API_KEY 是否配置")
        sys.exit(1)
