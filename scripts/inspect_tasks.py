#!/usr/bin/env python3
"""
独立任务检查工具 - 可在新终端中运行

用法:
  python scripts/inspect_tasks.py --list              # 列出所有任务
  python scripts/inspect_tasks.py --task <id>         # 查看任务详情
  python scripts/inspect_tasks.py --watch <id>        # 实时监控任务
  python scripts/inspect_tasks.py --log <id>          # 查看任务日志
  python scripts/inspect_tasks.py --requirements <id> # 查看需求
  python scripts/inspect_tasks.py --plan <id>         # 查看方案
"""

import sys
import argparse
import time
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from workflow.task_manager import get_task_manager, TaskStatus


def list_tasks():
    """列出所有任务"""
    manager = get_task_manager()

    print("\n" + "=" * 80)
    print("所有任务列表")
    print("=" * 80)

    tasks = manager.get_all_tasks()

    if not tasks:
        print("  (无任务)")
        print()
        return

    # 按创建时间排序
    tasks.sort(key=lambda t: t.created_at, reverse=True)

    for task in tasks:
        status_icon = {
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.AWAITING_CONFIRM: "⏸️",
            TaskStatus.GENERATING: "⚙️",
            TaskStatus.EXTRACTING: "🔍",
            TaskStatus.RETRIEVING: "📚",
            TaskStatus.PENDING: "⏳",
            TaskStatus.CANCELLED: "🚫"
        }.get(task.status, "🔄")

        print(f"\n  {status_icon} {task.task_id} ({task.status.value})")
        print(f"     会话: {task.session_id}")
        print(f"     时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     目录: {task.task_dir}")

        if task.status == TaskStatus.COMPLETED and task.plan_file.exists():
            # 读取方案标题
            try:
                with open(task.plan_file, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    title = plan_data.get('title', 'N/A')
                    print(f"     方案: {title}")
            except:
                pass

        if task.status == TaskStatus.FAILED:
            print(f"     错误: {task.error}")

    print()


def show_task_detail(task_id: str):
    """显示任务详情"""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return

    print("\n" + "=" * 80)
    print(f"任务详情: {task_id}")
    print("=" * 80)

    # 基本信息
    print("\n📋 基本信息:")
    task_dict = task.to_dict()
    for key, value in task_dict.items():
        if key in ['metadata']:
            continue
        print(f"  {key}: {value}")

    # 元数据
    if task.metadata:
        print("\n📊 元数据:")
        for key, value in task.metadata.items():
            print(f"  {key}: {value}")

    # 文件路径
    print("\n📁 文件:")
    files = [
        ("需求", task.requirements_file),
        ("模板", task.templates_file),
        ("方案", task.plan_file),
        ("日志", task.log_file)
    ]

    for name, path in files:
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {name}: {path} ({size} bytes)")
        else:
            print(f"  ⏳ {name}: {path} (不存在)")

    print()


def watch_task(task_id: str):
    """实时监控任务"""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return

    print(f"\n👀 实时监控任务 {task_id} (Ctrl+C 退出)\n")

    last_status = None

    try:
        while True:
            task = manager.get_task(task_id)

            if task.status != last_status:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] 状态变更: {task.status.value}")
                last_status = task.status

                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    print(f"\n任务已结束: {task.status.value}")

                    if task.status == TaskStatus.COMPLETED:
                        print(f"方案文件: {task.plan_file}")
                    elif task.status == TaskStatus.FAILED:
                        print(f"错误: {task.error}")

                    break

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n监控已停止")


def tail_log(task_id: str, follow: bool = True):
    """查看任务日志（tail -f效果）"""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return

    log_file = task.log_file

    if not log_file.exists():
        print(f"❌ 日志文件不存在: {log_file}")
        return

    print(f"\n📄 任务日志: {log_file}\n")
    print("=" * 80)

    # 读取已有内容
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)

    if not follow:
        return

    # 实时追踪新内容
    print("\n(实时追踪中，Ctrl+C 退出)\n")

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 移到文件末尾
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    print(line, end='')
                else:
                    time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\n日志追踪已停止")


def show_requirements(task_id: str):
    """查看需求"""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return

    if not task.requirements_file.exists():
        print(f"❌ 需求文件不存在: {task.requirements_file}")
        return

    print(f"\n📋 需求文件: {task.requirements_file}\n")
    print("=" * 80)

    with open(task.requirements_file, 'r', encoding='utf-8') as f:
        requirements = json.load(f)

    print(json.dumps(requirements, indent=2, ensure_ascii=False))
    print()


def show_plan(task_id: str):
    """查看方案"""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return

    if task.status != TaskStatus.COMPLETED:
        print(f"❌ 任务未完成 (状态: {task.status.value})")
        return

    if not task.plan_file.exists():
        print(f"❌ 方案文件不存在: {task.plan_file}")
        return

    print(f"\n📄 方案文件: {task.plan_file}\n")
    print("=" * 80)

    with open(task.plan_file, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    # 格式化显示
    print(f"\n标题: {plan.get('title', 'N/A')}")
    print(f"目标: {plan.get('objective', 'N/A')}")

    materials = plan.get('materials', [])
    print(f"\n材料清单 ({len(materials)}项):")
    for mat in materials:
        print(f"  • {mat.get('name')}: {mat.get('amount')}")

    procedure = plan.get('procedure', [])
    print(f"\n实验步骤 ({len(procedure)}步):")
    for step in procedure[:5]:  # 只显示前5步
        print(f"  {step.get('step_number')}. {step.get('description', '')[:60]}...")

    if len(procedure) > 5:
        print(f"  ... (还有 {len(procedure) - 5} 步)")

    safety = plan.get('safety_notes', [])
    print(f"\n安全注意事项 ({len(safety)}项):")
    for note in safety:
        print(f"  • {note}")

    print(f"\n完整内容请查看: {task.plan_file}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="任务检查工具 - 独立运行，可在新终端中使用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有任务
  python scripts/inspect_tasks.py --list

  # 查看任务详情
  python scripts/inspect_tasks.py --task abc123

  # 实时监控任务
  python scripts/inspect_tasks.py --watch abc123

  # 查看日志（实时追踪）
  python scripts/inspect_tasks.py --log abc123

  # 查看需求
  python scripts/inspect_tasks.py --requirements abc123

  # 查看方案
  python scripts/inspect_tasks.py --plan abc123
        """
    )

    parser.add_argument("--list", action="store_true", help="列出所有任务")
    parser.add_argument("--task", type=str, metavar="ID", help="查看任务详情")
    parser.add_argument("--watch", type=str, metavar="ID", help="实时监控任务")
    parser.add_argument("--log", type=str, metavar="ID", help="查看任务日志（实时追踪）")
    parser.add_argument("--requirements", type=str, metavar="ID", help="查看需求")
    parser.add_argument("--plan", type=str, metavar="ID", help="查看方案")
    parser.add_argument("--no-follow", action="store_true", help="日志不实时追踪")

    args = parser.parse_args()

    # 至少需要一个参数
    if not any([args.list, args.task, args.watch, args.log, args.requirements, args.plan]):
        parser.print_help()
        return

    if args.list:
        list_tasks()
    elif args.task:
        show_task_detail(args.task)
    elif args.watch:
        watch_task(args.watch)
    elif args.log:
        tail_log(args.log, follow=not args.no_follow)
    elif args.requirements:
        show_requirements(args.requirements)
    elif args.plan:
        show_plan(args.plan)


if __name__ == "__main__":
    main()
