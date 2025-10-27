#!/usr/bin/env python3
"""快速测试会话管理辅助函数（不需要LLM调用）"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "examples"))

# 导入辅助函数
from workflow_cli import generate_session_id


def test_generate_session_id():
    """测试会话ID生成函数"""
    print("\n测试: generate_session_id()")
    print("="*50)

    # 测试1: 自定义名称
    print("\n1. 自定义名称")
    custom_id = generate_session_id("aspirin_project")
    print(f"   generate_session_id('aspirin_project') = '{custom_id}'")
    assert custom_id == "aspirin_project", "自定义名称应原样返回"
    print("   ✅ 通过")

    # 测试2: 自动生成
    print("\n2. 自动生成（格式：YYYYMMDD_HHMM_<uuid>）")
    auto_id = generate_session_id()
    print(f"   generate_session_id() = '{auto_id}'")

    # 验证格式
    parts = auto_id.split('_')
    assert len(parts) == 3, f"格式错误：应有3部分，实际有{len(parts)}部分"

    # 验证日期部分（YYYYMMDD）
    date_part = parts[0]
    assert len(date_part) == 8, f"日期部分长度错误：{date_part}"
    assert date_part.isdigit(), f"日期部分应为数字：{date_part}"

    # 验证时间部分（HHMM）
    time_part = parts[1]
    assert len(time_part) == 4, f"时间部分长度错误：{time_part}"
    assert time_part.isdigit(), f"时间部分应为数字：{time_part}"

    # 验证UUID部分（6位）
    uuid_part = parts[2]
    assert len(uuid_part) == 6, f"UUID部分长度错误：{uuid_part}"

    print(f"   ✅ 格式正确: {date_part}_{time_part}_{uuid_part}")

    # 测试3: 多次生成应不同
    print("\n3. 唯一性检查")
    id1 = generate_session_id()
    id2 = generate_session_id()
    print(f"   第1次: {id1}")
    print(f"   第2次: {id2}")
    assert id1 != id2, "多次生成应产生不同ID"
    print("   ✅ 通过")


def main():
    print("\n🧪 会话管理辅助函数测试\n")

    try:
        test_generate_session_id()

        print("\n" + "="*50)
        print("✅ 所有测试通过！")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
