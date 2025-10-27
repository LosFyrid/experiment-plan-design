#!/usr/bin/env python3
"""测试 datetime 序列化修复

验证 Feedback 对象能否正确序列化为 JSON
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ace_framework.playbook.schemas import Feedback, FeedbackScore
from workflow.task_manager import GenerationTask, TaskStatus

def test_feedback_serialization():
    """测试 Feedback 对象的 JSON 序列化"""
    print("=" * 70)
    print("测试 Feedback JSON 序列化")
    print("=" * 70)

    # 创建测试 Feedback 对象
    feedback = Feedback(
        plan_id="test-plan-001",
        scores=[
            FeedbackScore(
                criterion="completeness",
                score=0.9,
                explanation="方案完整"
            ),
            FeedbackScore(
                criterion="safety",
                score=0.95,
                explanation="安全提示充分"
            )
        ],
        overall_score=0.925,
        feedback_source="auto",
        comments="测试反馈",
        timestamp=datetime.now()
    )

    print(f"\n✅ 创建 Feedback 对象:")
    print(f"   - Overall score: {feedback.overall_score}")
    print(f"   - Timestamp: {feedback.timestamp}")
    print(f"   - Scores: {len(feedback.scores)}")

    # 测试 model_dump(mode='json')
    print(f"\n🔧 测试 model_dump(mode='json')...")
    try:
        feedback_dict = feedback.model_dump(mode='json')
        print(f"✅ model_dump() 成功")
        print(f"   - timestamp 类型: {type(feedback_dict['timestamp'])}")
        print(f"   - timestamp 值: {feedback_dict['timestamp']}")
    except Exception as e:
        print(f"❌ model_dump() 失败: {e}")
        return False

    # 测试 JSON 序列化
    print(f"\n🔧 测试 json.dump()...")
    import json
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(feedback_dict, f, indent=2, ensure_ascii=False)
            temp_path = f.name

        print(f"✅ json.dump() 成功")
        print(f"   - 临时文件: {temp_path}")

        # 读取并验证
        with open(temp_path, 'r') as f:
            loaded = json.load(f)

        print(f"✅ json.load() 成功")
        print(f"   - timestamp 值: {loaded['timestamp']}")

        # 清理
        Path(temp_path).unlink()

    except Exception as e:
        print(f"❌ json.dump() 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n{'=' * 70}")
    print("✅ 所有测试通过！")
    print("=" * 70)
    return True


def test_task_save_feedback():
    """测试 GenerationTask.save_feedback() 方法"""
    print("\n" + "=" * 70)
    print("测试 GenerationTask.save_feedback()")
    print("=" * 70)

    import tempfile
    import shutil

    # 创建临时任务目录
    temp_dir = Path(tempfile.mkdtemp())
    print(f"\n📁 临时目录: {temp_dir}")

    try:
        # 创建 GenerationTask 对象
        task = GenerationTask(
            task_id="test-task",
            session_id="test-session",
            status=TaskStatus.COMPLETED,
            task_dir=temp_dir
        )

        # 创建测试 Feedback
        feedback = Feedback(
            plan_id="test-plan-002",
            scores=[
                FeedbackScore(
                    criterion="clarity",
                    score=0.88,
                    explanation="清晰度良好"
                )
            ],
            overall_score=0.88,
            feedback_source="llm_judge",
            comments="LLM评估结果",
            timestamp=datetime.now()
        )

        print(f"\n🔧 调用 task.save_feedback()...")
        task.save_feedback(feedback)

        print(f"✅ save_feedback() 成功")
        print(f"   - 文件路径: {task.feedback_file}")
        print(f"   - 文件存在: {task.feedback_file.exists()}")

        # 验证文件内容
        if task.feedback_file.exists():
            with open(task.feedback_file, 'r') as f:
                loaded = task.load_feedback()

            print(f"✅ load_feedback() 成功")
            print(f"   - Overall score: {loaded['overall_score']}")
            print(f"   - Timestamp: {loaded['timestamp']}")

        print(f"\n{'=' * 70}")
        print("✅ GenerationTask.save_feedback() 测试通过！")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)

    return True


if __name__ == "__main__":
    # 测试1: 基础序列化
    success1 = test_feedback_serialization()

    # 测试2: Task 方法
    success2 = test_task_save_feedback()

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"  基础序列化: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  GenerationTask.save_feedback(): {'✅ PASS' if success2 else '❌ FAIL'}")

    if success1 and success2:
        print("\n🎉 所有测试通过！datetime 序列化问题已修复。")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查修复。")
        sys.exit(1)
