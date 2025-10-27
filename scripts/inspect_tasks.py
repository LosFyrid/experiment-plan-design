#!/usr/bin/env python3
"""
独立任务检查工具 - 可在新终端中运行

用法:
  # 任务管理
  python scripts/inspect_tasks.py --list              # 列出所有任务
  python scripts/inspect_tasks.py --task <id>         # 查看任务详情
  python scripts/inspect_tasks.py --watch <id>        # 实时监控任务
  python scripts/inspect_tasks.py --log <id>          # 查看任务日志
  python scripts/inspect_tasks.py --requirements <id> # 查看需求
  python scripts/inspect_tasks.py --plan <id>         # 查看方案
  python scripts/inspect_tasks.py --resumable         # 列出可恢复的任务
  python scripts/inspect_tasks.py --resume            # 交互式恢复任务
  python scripts/inspect_tasks.py --resume <id>       # 恢复指定任务

  # Playbook管理
  python scripts/inspect_tasks.py --playbook-stats    # 统计当前playbook信息
  python scripts/inspect_tasks.py --playbook-stats --full  # 显示完整playbook内容
  python scripts/inspect_tasks.py --list-snapshots    # 列出所有playbook快照
  python scripts/inspect_tasks.py --snapshot <ver>    # 统计指定快照信息
  python scripts/inspect_tasks.py --snapshot <ver> --full  # 显示快照完整内容
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
from workflow.task_utils import (
    display_resumable_tasks,
    resume_task_interactive
)

# Playbook相关路径
PLAYBOOK_PATH = project_root / "data" / "playbooks" / "chemistry_playbook.json"
PLAYBOOK_VERSIONS_DIR = project_root / "logs" / "playbook_versions"


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


def show_feedback(task_id: str):
    """查看反馈循环数据"""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        return

    task_dir = Path(task.task_dir)
    feedback_file = task_dir / "feedback.json"
    curation_file = task_dir / "curation.json"

    print("\n" + "=" * 80)
    print(f"反馈循环数据: {task_id}")
    print("=" * 80)

    # 显示反馈评分
    if feedback_file.exists():
        print("\n🔍 反馈评分:")
        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedback = json.load(f)

        scores = feedback.get('scores', [])
        overall_score = feedback.get('overall_score', 0)

        for item in scores:
            criterion = item.get('criterion', 'N/A')
            score = item.get('score', 0)
            explanation = item.get('explanation', '')
            print(f"\n  • {criterion}: {score:.2f}")
            print(f"    {explanation}")

        print(f"\n  📊 总分: {overall_score:.2f}")
        print(f"  🤖 评分来源: {feedback.get('feedback_source', 'N/A')}")

        if feedback.get('comments'):
            print(f"\n  💬 总体评价:")
            print(f"    {feedback['comments']}")

    else:
        print("\n⏳ 反馈文件不存在")

    # 显示策展更新
    if curation_file.exists():
        print("\n📚 Playbook更新:")

        try:
            with open(curation_file, 'r', encoding='utf-8') as f:
                curation = json.load(f)

            updated_playbook = curation.get('updated_playbook', {})
            bullets = updated_playbook.get('bullets', [])

            # 1. 更新后的规则总数
            print(f"\n  📦 更新后的Playbook包含 {len(bullets)} 条规则")

            # 2. 各section的规则分布
            section_counts = {}
            for bullet in bullets:
                section = bullet.get('section', 'unknown')
                section_counts[section] = section_counts.get(section, 0) + 1

            print(f"\n  📑 各部分规则数量:")
            for section, count in section_counts.items():
                print(f"    • {section}: {count}")

            # 3. 规则来源统计
            source_counts = {}
            for bullet in bullets:
                source = bullet.get('metadata', {}).get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1

            print(f"\n  🏷️  规则来源分布:")
            for source, count in source_counts.items():
                print(f"    • {source}: {count}")

            # 4. 变更统计
            bullets_added = curation.get('bullets_added', 0)
            bullets_updated = curation.get('bullets_updated', 0)
            bullets_removed = curation.get('bullets_removed', 0)

            print(f"\n  📊 本次变更统计:")
            print(f"    ✅ 新增: {bullets_added} 条")
            print(f"    ✏️  修改: {bullets_updated} 条")
            print(f"    ❌ 删除: {bullets_removed} 条")
            print(f"    📝 总计: {bullets_added + bullets_updated + bullets_removed} 项变更")

            # 显示详细的变更操作
            delta_operations = curation.get('delta_operations', [])

            if delta_operations:
                print(f"\n  🔄 详细变更:")

                # 按操作类型分组
                adds = [op for op in delta_operations if op.get('operation') == 'ADD']
                updates = [op for op in delta_operations if op.get('operation') == 'UPDATE']
                removes = [op for op in delta_operations if op.get('operation') == 'REMOVE']

                # 显示新增
                if adds:
                    print(f"\n    ✅ 新增 ({len(adds)} 条):")
                    for op in adds[:5]:  # 最多显示5条
                        new_bullet = op.get('new_bullet', {})
                        bullet_id = new_bullet.get('id', 'N/A')
                        section = new_bullet.get('section', 'N/A')
                        content = new_bullet.get('content', '')[:80] + "..."
                        reason = op.get('reason', '')[:100]
                        print(f"       [{bullet_id}] ({section})")
                        print(f"       {content}")
                        print(f"       原因: {reason}")
                        print()
                    if len(adds) > 5:
                        print(f"       ... 还有 {len(adds) - 5} 条新增")

                # 显示修改
                if updates:
                    print(f"\n    ✏️  修改 ({len(updates)} 条):")
                    for op in updates[:5]:  # 最多显示5条
                        bullet_id = op.get('bullet_id', 'N/A')
                        new_bullet = op.get('new_bullet', {})
                        content = new_bullet.get('content', '')[:80] + "..."
                        reason = op.get('reason', '')[:100]
                        print(f"       [{bullet_id}]")
                        print(f"       新内容: {content}")
                        print(f"       原因: {reason}")
                        print()
                    if len(updates) > 5:
                        print(f"       ... 还有 {len(updates) - 5} 条修改")

                # 显示删除
                if removes:
                    print(f"\n    ❌ 删除 ({len(removes)} 条):")
                    for op in removes[:5]:  # 最多显示5条
                        bullet_id = op.get('bullet_id', 'N/A')
                        reason = op.get('reason', '')[:100]
                        print(f"       [{bullet_id}]")
                        print(f"       原因: {reason}")
                        print()
                    if len(removes) > 5:
                        print(f"       ... 还有 {len(removes) - 5} 条删除")

            else:
                print("\n  ⚠️  没有记录到变更操作（可能是旧版本数据）")

        except json.JSONDecodeError:
            print("  ⚠️  策展文件太大或格式错误，无法完整显示")
            print(f"  💡 请直接查看: {curation_file}")

    else:
        print("\n⏳ 策展文件不存在")

    print()


def show_resumable_tasks():
    """显示所有可恢复的任务

    调用 task_utils.display_resumable_tasks() 显示所有
    处于 AWAITING_CONFIRM 状态的任务。
    """
    display_resumable_tasks()


def resume_task_cmd(task_id: str = None):
    """恢复任务

    Args:
        task_id: 任务ID（可选）。如果不提供，则交互式选择

    Notes:
        - 如果提供task_id，直接恢复指定任务
        - 如果不提供task_id，调用交互式选择
        - 只能恢复AWAITING_CONFIRM状态的任务
        - 恢复后Worker会自动启动（如果未运行）
    """
    if task_id:
        # 直接恢复指定任务
        tm = get_task_manager()
        success = tm.resume_task(task_id)

        if success:
            print(f"\n✅ 已恢复任务 {task_id}")
            print(f"   Worker将在后台继续执行")
            print(f"\n💡 使用以下命令监控进度:")
            print(f"     python scripts/inspect_tasks.py --watch {task_id}")
            print(f"     python scripts/inspect_tasks.py --log {task_id}\n")
        else:
            print(f"\n❌ 恢复失败")
            print(f"   任务可能不存在或不在AWAITING_CONFIRM状态")
            print(f"\n💡 查看可恢复的任务:")
            print(f"     python scripts/inspect_tasks.py --resumable\n")

    else:
        # 交互式选择
        success = resume_task_interactive()

        if success:
            print("\n✅ 任务已恢复")
            print("\n💡 后续操作:")
            print("   python scripts/inspect_tasks.py --list           # 查看所有任务")
            print("   python scripts/inspect_tasks.py --watch <id>     # 监控进度")
            print("   python scripts/inspect_tasks.py --log <id>       # 查看日志\n")


# ============================================================================
# Playbook 相关功能
# ============================================================================


def show_playbook_stats(full: bool = False):
    """统计当前playbook文件信息

    Args:
        full: 是否显示完整的JSON内容（格式化展示）
    """
    if not PLAYBOOK_PATH.exists():
        print(f"❌ Playbook文件不存在: {PLAYBOOK_PATH}")
        return

    print("\n" + "=" * 80)
    print("当前Playbook统计信息")
    print("=" * 80)

    # 读取playbook文件
    with open(PLAYBOOK_PATH, 'r', encoding='utf-8') as f:
        playbook = json.load(f)

    bullets = playbook.get('bullets', [])
    sections = playbook.get('sections', [])
    version = playbook.get('version', 'N/A')
    last_updated = playbook.get('last_updated', 'N/A')
    total_generations = playbook.get('total_generations', 0)

    # 基本信息
    print(f"\n📋 基本信息:")
    print(f"  文件路径: {PLAYBOOK_PATH}")
    print(f"  版本: {version}")
    print(f"  最后更新: {last_updated}")
    print(f"  总生成次数: {total_generations}")
    print(f"  规则总数: {len(bullets)}")
    print(f"  部分数量: {len(sections)}")

    # 各section的规则分布
    section_counts = {}
    for bullet in bullets:
        section = bullet.get('section', 'unknown')
        section_counts[section] = section_counts.get(section, 0) + 1

    print(f"\n📑 各部分规则数量:")
    for section in sections:
        count = section_counts.get(section, 0)
        print(f"  • {section}: {count}")

    # 规则来源统计
    source_counts = {}
    for bullet in bullets:
        source = bullet.get('metadata', {}).get('source', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1

    print(f"\n🏷️  规则来源分布:")
    for source, count in sorted(source_counts.items()):
        print(f"  • {source}: {count}")

    # 帮助性统计
    helpful_bullets = []
    harmful_bullets = []
    neutral_bullets = []

    for bullet in bullets:
        metadata = bullet.get('metadata', {})
        helpful_count = metadata.get('helpful_count', 0)
        harmful_count = metadata.get('harmful_count', 0)
        neutral_count = metadata.get('neutral_count', 0)

        if helpful_count > 0:
            helpful_bullets.append(bullet)
        if harmful_count > 0:
            harmful_bullets.append(bullet)
        if helpful_count == 0 and harmful_count == 0 and neutral_count == 0:
            neutral_bullets.append(bullet)

    print(f"\n📊 规则使用情况:")
    print(f"  • 有帮助的规则: {len(helpful_bullets)}")
    print(f"  • 有害的规则: {len(harmful_bullets)}")
    print(f"  • 未使用的规则: {len(neutral_bullets)}")

    # 显示top-5有帮助的规则
    if helpful_bullets:
        print(f"\n🌟 Top-5 最有帮助的规则:")
        sorted_helpful = sorted(
            helpful_bullets,
            key=lambda b: b.get('metadata', {}).get('helpful_count', 0),
            reverse=True
        )[:5]

        for i, bullet in enumerate(sorted_helpful, 1):
            bullet_id = bullet.get('id', 'N/A')
            section = bullet.get('section', 'N/A')
            helpful_count = bullet.get('metadata', {}).get('helpful_count', 0)
            content = bullet.get('content', '')[:80] + "..."
            print(f"  {i}. [{bullet_id}] ({section}) - 被标记有帮助 {helpful_count} 次")
            print(f"     {content}")

    # 显示完整内容
    if full:
        print("\n" + "=" * 80)
        print("完整Playbook内容")
        print("=" * 80)

        for section in sections:
            section_bullets = [b for b in bullets if b.get('section') == section]

            if section_bullets:
                print(f"\n\n{'='*80}")
                print(f"【{section}】- {len(section_bullets)} 条规则")
                print('='*80)

                for bullet in section_bullets:
                    bullet_id = bullet.get('id', 'N/A')
                    content = bullet.get('content', '')
                    metadata = bullet.get('metadata', {})

                    print(f"\n🔹 ID: {bullet_id}")
                    print(f"   内容: {content}")
                    print(f"   元数据:")
                    print(f"     - 来源: {metadata.get('source', 'N/A')}")
                    print(f"     - 创建时间: {metadata.get('created_at', 'N/A')}")
                    print(f"     - 最后更新: {metadata.get('last_updated', 'N/A')}")
                    print(f"     - 有帮助次数: {metadata.get('helpful_count', 0)}")
                    print(f"     - 有害次数: {metadata.get('harmful_count', 0)}")
                    print(f"     - 中性次数: {metadata.get('neutral_count', 0)}")

    print("\n" + "=" * 80)
    print()


def list_playbook_snapshots():
    """列出所有playbook快照"""
    if not PLAYBOOK_VERSIONS_DIR.exists():
        print(f"❌ Playbook版本目录不存在: {PLAYBOOK_VERSIONS_DIR}")
        return

    print("\n" + "=" * 80)
    print("Playbook快照列表")
    print("=" * 80)

    # 获取所有meta文件
    meta_files = sorted(PLAYBOOK_VERSIONS_DIR.glob("meta_*.json"))

    if not meta_files:
        print("  (无快照)")
        print()
        return

    print(f"\n共 {len(meta_files)} 个快照\n")

    # 读取并显示每个快照的基本信息
    for meta_file in meta_files:
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)

            version = meta.get('version', 'N/A')
            timestamp = meta.get('timestamp', 'N/A')
            reason = meta.get('reason', 'N/A')
            trigger = meta.get('trigger', 'N/A')
            size = meta.get('size', 0)
            changes = meta.get('changes', {})
            added = changes.get('added', 0)
            updated = changes.get('updated', 0)
            removed = changes.get('removed', 0)

            # 格式化时间戳
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp)
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                timestamp_str = timestamp

            print(f"  📸 {version}")
            print(f"     时间: {timestamp_str}")
            print(f"     原因: {reason}")
            print(f"     触发器: {trigger}")
            print(f"     规则数: {size}")
            if added > 0 or updated > 0 or removed > 0:
                print(f"     变更: +{added} ~{updated} -{removed}")
            print()

        except Exception as e:
            print(f"  ⚠️  读取快照失败: {meta_file.name} - {e}")
            continue

    print("=" * 80)
    print()


def show_snapshot_stats(version: str, full: bool = False):
    """统计指定playbook快照信息

    Args:
        version: 快照版本号（如 v001）
        full: 是否显示完整内容
    """
    if not PLAYBOOK_VERSIONS_DIR.exists():
        print(f"❌ Playbook版本目录不存在: {PLAYBOOK_VERSIONS_DIR}")
        return

    # 查找对应的meta和playbook文件
    meta_files = list(PLAYBOOK_VERSIONS_DIR.glob(f"meta_*_{version}.json"))
    playbook_files = list(PLAYBOOK_VERSIONS_DIR.glob(f"playbook_*_{version}.json"))

    if not meta_files:
        print(f"❌ 未找到快照 {version} 的元数据文件")
        print(f"\n💡 使用以下命令查看所有快照:")
        print(f"   python scripts/inspect_tasks.py --list-snapshots")
        return

    if not playbook_files:
        print(f"❌ 未找到快照 {version} 的playbook文件")
        return

    meta_file = meta_files[0]
    playbook_file = playbook_files[0]

    # 读取meta文件
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    print("\n" + "=" * 80)
    print(f"Playbook快照统计: {version}")
    print("=" * 80)

    # 基本信息（从meta文件获取）
    print(f"\n📋 快照元数据:")
    print(f"  版本: {meta.get('version', 'N/A')}")
    print(f"  时间戳: {meta.get('timestamp', 'N/A')}")
    print(f"  运行ID: {meta.get('run_id', 'N/A')}")
    print(f"  原因: {meta.get('reason', 'N/A')}")
    print(f"  触发器: {meta.get('trigger', 'N/A')}")
    print(f"  规则总数: {meta.get('size', 0)}")

    # 变更统计
    changes = meta.get('changes', {})
    print(f"\n📊 变更统计:")
    print(f"  • 新增: {changes.get('added', 0)}")
    print(f"  • 修改: {changes.get('updated', 0)}")
    print(f"  • 删除: {changes.get('removed', 0)}")

    # 各section分布
    section_dist = meta.get('section_distribution', {})
    if section_dist:
        print(f"\n📑 各部分规则数量:")
        for section, count in section_dist.items():
            print(f"  • {section}: {count}")

    # 平均帮助性得分
    avg_helpfulness = meta.get('avg_helpfulness_score', 0)
    print(f"\n⭐ 平均帮助性得分: {avg_helpfulness:.2f}")

    # 生成元数据
    gen_meta = meta.get('generation_metadata', {})
    if gen_meta:
        print(f"\n🔍 生成元数据:")
        for key, value in gen_meta.items():
            print(f"  • {key}: {value}")

    # 显示变更的具体规则ID
    if changes.get('added_bullets'):
        print(f"\n✅ 新增的规则ID:")
        for bullet_id in changes.get('added_bullets', [])[:10]:
            print(f"  • {bullet_id}")
        if len(changes.get('added_bullets', [])) > 10:
            print(f"  ... 还有 {len(changes.get('added_bullets', [])) - 10} 个")

    if changes.get('updated_bullets'):
        print(f"\n✏️  修改的规则ID:")
        for bullet_id in changes.get('updated_bullets', [])[:10]:
            print(f"  • {bullet_id}")
        if len(changes.get('updated_bullets', [])) > 10:
            print(f"  ... 还有 {len(changes.get('updated_bullets', [])) - 10} 个")

    if changes.get('removed_bullets'):
        print(f"\n❌ 删除的规则ID:")
        for bullet_id in changes.get('removed_bullets', [])[:10]:
            print(f"  • {bullet_id}")
        if len(changes.get('removed_bullets', [])) > 10:
            print(f"  ... 还有 {len(changes.get('removed_bullets', [])) - 10} 个")

    # 显示完整内容
    if full:
        print("\n" + "=" * 80)
        print("完整Playbook快照内容")
        print("=" * 80)

        with open(playbook_file, 'r', encoding='utf-8') as f:
            playbook = json.load(f)

        bullets = playbook.get('bullets', [])
        sections = playbook.get('sections', [])

        for section in sections:
            section_bullets = [b for b in bullets if b.get('section') == section]

            if section_bullets:
                print(f"\n\n{'='*80}")
                print(f"【{section}】- {len(section_bullets)} 条规则")
                print('='*80)

                for bullet in section_bullets:
                    bullet_id = bullet.get('id', 'N/A')
                    content = bullet.get('content', '')
                    metadata = bullet.get('metadata', {})

                    print(f"\n🔹 ID: {bullet_id}")
                    print(f"   内容: {content}")
                    print(f"   元数据:")
                    print(f"     - 来源: {metadata.get('source', 'N/A')}")
                    print(f"     - 创建时间: {metadata.get('created_at', 'N/A')}")
                    print(f"     - 最后更新: {metadata.get('last_updated', 'N/A')}")
                    print(f"     - 有帮助次数: {metadata.get('helpful_count', 0)}")
                    print(f"     - 有害次数: {metadata.get('harmful_count', 0)}")
                    print(f"     - 中性次数: {metadata.get('neutral_count', 0)}")

    print("\n" + "=" * 80)
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

  # 查看反馈循环（评分 + Playbook更新）
  python scripts/inspect_tasks.py --feedback abc123

  # 列出可恢复的任务
  python scripts/inspect_tasks.py --resumable

  # 交互式恢复任务
  python scripts/inspect_tasks.py --resume

  # 恢复指定任务
  python scripts/inspect_tasks.py --resume abc123

  # 统计当前playbook信息
  python scripts/inspect_tasks.py --playbook-stats

  # 统计当前playbook信息（显示完整内容）
  python scripts/inspect_tasks.py --playbook-stats --full

  # 列出所有playbook快照
  python scripts/inspect_tasks.py --list-snapshots

  # 统计指定快照信息
  python scripts/inspect_tasks.py --snapshot v001

  # 统计指定快照信息（显示完整内容）
  python scripts/inspect_tasks.py --snapshot v001 --full
        """
    )

    parser.add_argument("--list", action="store_true", help="列出所有任务")
    parser.add_argument("--task", type=str, metavar="ID", help="查看任务详情")
    parser.add_argument("--watch", type=str, metavar="ID", help="实时监控任务")
    parser.add_argument("--log", type=str, metavar="ID", help="查看任务日志（实时追踪）")
    parser.add_argument("--requirements", type=str, metavar="ID", help="查看需求")
    parser.add_argument("--plan", type=str, metavar="ID", help="查看方案")
    parser.add_argument("--feedback", type=str, metavar="ID", help="查看反馈循环数据（评分 + Playbook更新）")
    parser.add_argument("--resumable", action="store_true", help="列出所有可恢复的任务（AWAITING_CONFIRM状态）")
    parser.add_argument("--resume", nargs="?", const=None, metavar="ID", help="恢复任务（不指定ID则交互式选择）")
    parser.add_argument("--no-follow", action="store_true", help="日志不实时追踪")

    # Playbook相关参数
    parser.add_argument("--playbook-stats", action="store_true", help="统计当前playbook文件信息")
    parser.add_argument("--list-snapshots", action="store_true", help="列出所有playbook快照")
    parser.add_argument("--snapshot", type=str, metavar="VERSION", help="统计指定playbook快照（如 v001）")
    parser.add_argument("--full", action="store_true", help="显示完整内容（与--playbook-stats或--snapshot配合使用）")

    args = parser.parse_args()

    # 至少需要一个参数
    if not any([args.list, args.task, args.watch, args.log, args.requirements, args.plan, args.feedback,
                args.resumable, args.resume is not None, args.playbook_stats, args.list_snapshots, args.snapshot]):
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
    elif args.feedback:
        show_feedback(args.feedback)
    elif args.resumable:
        show_resumable_tasks()
    elif args.resume is not None:
        # args.resume 可能是 None（交互式）或 task_id（直接恢复）
        resume_task_cmd(args.resume)
    elif args.playbook_stats:
        show_playbook_stats(full=args.full)
    elif args.list_snapshots:
        list_playbook_snapshots()
    elif args.snapshot:
        show_snapshot_stats(args.snapshot, full=args.full)


if __name__ == "__main__":
    main()
