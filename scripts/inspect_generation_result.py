#!/usr/bin/env python3
"""
检查 generation_result.json 的内容

用法:
    python scripts/inspect_generation_result.py <task_id>
    python scripts/inspect_generation_result.py --latest
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from workflow.task_manager import get_task_manager


def inspect_generation_result(task_id: str):
    """检查指定任务的 generation_result.json"""

    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return False

    print("=" * 70)
    print(f"任务: {task_id}")
    print("=" * 70)
    print(f"状态: {task.status.value}")
    print(f"会话: {task.session_id}")
    print()

    # 检查文件存在性
    print("📁 文件状态:")
    print(f"  plan.json: {'✅' if task.plan_file.exists() else '❌'}")
    print(f"  generation_result.json: {'✅' if task.generation_result_file.exists() else '❌'}")
    print()

    # 如果 generation_result.json 不存在，退出
    if not task.generation_result_file.exists():
        print("⚠️  generation_result.json 不存在")
        print("   这可能是旧任务（功能未实现前生成的）")
        return False

    # 加载并显示 generation_result
    result = task.load_generation_result()

    if not result:
        print("❌ 无法加载 generation_result.json")
        return False

    print("=" * 70)
    print("📊 GenerationResult 内容")
    print("=" * 70)

    # Plan 信息
    plan = result.get("plan", {})
    print(f"\n🧪 Plan:")
    print(f"  标题: {plan.get('title', 'N/A')}")
    print(f"  材料数: {len(plan.get('materials', []))}")
    print(f"  步骤数: {len(plan.get('procedure', []))}")

    # Trajectory 信息
    trajectory = result.get("trajectory", [])
    print(f"\n🔍 Trajectory:")
    print(f"  步骤数: {len(trajectory)}")

    if trajectory:
        print(f"\n  前3步预览:")
        for step in trajectory[:3]:
            step_num = step.get("step_number", "?")
            thought = step.get("thought", "N/A")
            print(f"\n  [{step_num}] Thought: {thought[:80]}...")
            if step.get("action"):
                print(f"      Action: {step['action'][:80]}...")
            if step.get("observation"):
                print(f"      Observation: {step['observation'][:80]}...")
    else:
        print("  ⚠️ Trajectory 为空（LLM 可能没有生成）")

    # Relevant bullets 信息
    bullets = result.get("relevant_bullets", [])
    print(f"\n📌 Relevant Bullets:")
    print(f"  数量: {len(bullets)}")
    if bullets:
        print(f"  列表: {', '.join(bullets)}")
    else:
        print("  ⚠️ 没有引用 playbook bullets")

    # Metadata 信息
    metadata = result.get("metadata", {})
    print(f"\n📈 Metadata:")
    print(f"  Model: {metadata.get('model', 'N/A')}")
    print(f"  Tokens: {metadata.get('total_tokens', 0)}")
    print(f"  Duration: {metadata.get('duration', 0):.2f}s")
    print(f"  Retrieved bullets: {metadata.get('retrieved_bullets_count', 0)}")

    # Timestamp
    timestamp = result.get("timestamp", "N/A")
    print(f"\n⏰ Timestamp: {timestamp}")

    print("\n" + "=" * 70)

    return True


def get_latest_task():
    """获取最新的已完成任务"""
    from workflow.task_manager import TaskStatus

    task_manager = get_task_manager()
    tasks = task_manager.get_all_tasks()

    # 过滤已完成的任务
    completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

    if not completed_tasks:
        return None

    # 按创建时间排序，返回最新的
    completed_tasks.sort(key=lambda t: t.created_at, reverse=True)
    return completed_tasks[0].task_id


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python scripts/inspect_generation_result.py <task_id>")
        print("  python scripts/inspect_generation_result.py --latest")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--latest":
        task_id = get_latest_task()
        if not task_id:
            print("❌ 没有找到已完成的任务")
            sys.exit(1)
        print(f"🔍 检查最新任务: {task_id}\n")
    else:
        task_id = arg

    success = inspect_generation_result(task_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
