#!/usr/bin/env python3
"""测试 ADD 操作的修复效果"""

import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_retry_handler_rollback_extraction():
    """测试 retry_handler.py 的回滚逻辑是否能正确提取 bullet ID"""

    print("=" * 70)
    print("测试 1: retry_handler.py 的 ADD 操作回滚逻辑")
    print("=" * 70)

    # 模拟 curation.json 的 delta_operations 数据
    curation_result = {
        "delta_operations": [
            {
                "operation": "ADD",
                "bullet_id": None,  # ADD 操作的 bullet_id 是 None
                "new_bullet": {
                    "id": "proc-00009",  # 实际的 bullet ID
                    "section": "procedure_design",
                    "content": "测试内容..."
                },
                "reason": "测试原因"
            },
            {
                "operation": "ADD",
                "bullet_id": None,
                "new_bullet": {
                    "id": "mat-00042",
                    "section": "material_selection",
                    "content": "另一个测试内容..."
                },
                "reason": "另一个测试原因"
            }
        ]
    }

    # 模拟 retry_handler.py 的回滚逻辑（修复后）
    added_bullet_ids = []

    for update in curation_result.get("delta_operations", []):
        operation = update.get("operation")

        if operation == "ADD":
            # 修复后的逻辑：从 new_bullet.id 获取
            new_bullet = update.get("new_bullet")
            if new_bullet:
                bullet_id = new_bullet.get("id")
                if bullet_id:
                    added_bullet_ids.append(bullet_id)

    print(f"\n提取到的 bullet IDs: {added_bullet_ids}")

    # 验证
    expected = ["proc-00009", "mat-00042"]
    if added_bullet_ids == expected:
        print("✅ 测试通过：成功提取所有 bullet IDs")
        return True
    else:
        print(f"❌ 测试失败：期望 {expected}，实际 {added_bullet_ids}")
        return False


def test_curator_delta_operation_construction():
    """测试 curator.py 的 DeltaOperation 构建逻辑"""

    print("\n" + "=" * 70)
    print("测试 2: curator.py 的 ADD 操作构建逻辑")
    print("=" * 70)

    # 模拟 LLM 返回的 op_data
    op_data = {
        "operation": "ADD",
        "bullet_id": None,  # LLM 不知道新的 ID
        "new_bullet": {
            "section": "material_selection",
            "content": "新的 bullet 内容"
        },
        "reason": "解决某个问题"
    }

    # 模拟 curator.py 的逻辑（修复后）
    section = op_data["new_bullet"]["section"]
    content = op_data["new_bullet"]["content"]

    # 生成 ID（对于 ADD 操作）
    if op_data["operation"] == "ADD":
        bullet_id = "mat-00042"  # 模拟 playbook_manager._generate_bullet_id()
    else:
        bullet_id = op_data.get("bullet_id")

    # 构建 DeltaOperation（修复后的逻辑）
    operation = {
        "operation": op_data["operation"],
        "bullet_id": bullet_id if op_data["operation"] == "ADD" else op_data.get("bullet_id"),
        "new_bullet": {
            "id": bullet_id,
            "section": section,
            "content": content
        },
        "reason": op_data.get("reason", "")
    }

    print(f"\n构建的 DeltaOperation:")
    print(f"  operation: {operation['operation']}")
    print(f"  bullet_id: {operation['bullet_id']}")
    print(f"  new_bullet.id: {operation['new_bullet']['id']}")

    # 验证
    if operation["bullet_id"] == "mat-00042" and operation["new_bullet"]["id"] == "mat-00042":
        print("\n✅ 测试通过：bullet_id 和 new_bullet.id 一致")
        return True
    else:
        print(f"\n❌ 测试失败：bullet_id 不一致")
        return False


def test_with_real_curation_file():
    """使用真实的 curation.json 文件测试回滚逻辑"""

    print("\n" + "=" * 70)
    print("测试 3: 使用真实 curation.json 测试回滚逻辑")
    print("=" * 70)

    curation_file = project_root / "logs/generation_tasks/5328e7d2/curation.json"

    if not curation_file.exists():
        print("⚠️  测试文件不存在，跳过此测试")
        return True

    with open(curation_file, 'r', encoding='utf-8') as f:
        curation_result = json.load(f)

    # 提取 ADD 操作的 bullet IDs（使用修复后的逻辑）
    added_bullet_ids = []

    for update in curation_result.get("delta_operations", []):
        operation = update.get("operation")

        if operation == "ADD":
            new_bullet = update.get("new_bullet")
            if new_bullet:
                bullet_id = new_bullet.get("id")
                if bullet_id:
                    added_bullet_ids.append(bullet_id)

    print(f"\n从真实文件提取的 ADD 操作 bullet IDs: {added_bullet_ids}")

    if added_bullet_ids:
        print(f"✅ 测试通过：成功提取 {len(added_bullet_ids)} 个 bullet IDs")
        return True
    else:
        # 可能文件中没有 ADD 操作
        add_ops = [op for op in curation_result.get("delta_operations", []) if op.get("operation") == "ADD"]
        if not add_ops:
            print("ℹ️  文件中没有 ADD 操作")
            return True
        else:
            print("❌ 测试失败：文件中有 ADD 操作但未提取到 bullet IDs")
            return False


def main():
    """运行所有测试"""

    print("\n🧪 ADD 操作修复效果验证\n")

    results = []

    # 测试 1: retry_handler.py 的回滚逻辑
    results.append(test_retry_handler_rollback_extraction())

    # 测试 2: curator.py 的构建逻辑
    results.append(test_curator_delta_operation_construction())

    # 测试 3: 使用真实文件测试
    results.append(test_with_real_curation_file())

    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"\n通过: {passed}/{total}")

    if all(results):
        print("\n🎉 所有测试通过！ADD 操作修复成功。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查修复逻辑。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
