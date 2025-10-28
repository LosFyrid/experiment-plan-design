"""反馈工作进程 - 独立运行

用法:
    python -m workflow.feedback_worker <task_id>
    python -m workflow.feedback_worker <task_id> --mode <evaluation_mode>

流程:
    COMPLETED → EVALUATING → REFLECTING → CURATING → FEEDBACK_COMPLETED

特性:
- 作为独立进程运行（可脱离主CLI）
- 所有print输出被父进程管道捕获
- 状态更新写入文件系统（task.json）
- 从generation_result.json加载完整数据（trajectory + relevant_bullets）
"""

import sys
import json
import argparse
import os
from pathlib import Path
from typing import Optional

# 确保 src 在 Python 路径中
current_file = Path(__file__).resolve()
src_dir = current_file.parent.parent  # src/workflow -> src
project_root = src_dir.parent  # src -> 项目根

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")


def main():
    """反馈工作进程主入口"""
    # 解析参数
    parser = argparse.ArgumentParser(description="反馈训练工作进程")
    parser.add_argument("task_id", help="任务ID")
    parser.add_argument("--mode", default=None,
                       choices=["auto", "llm_judge", "human"],
                       help="评估模式（可选，默认从配置读取）")
    args = parser.parse_args()

    task_id = args.task_id
    evaluation_mode = args.mode

    print("=" * 70)
    print("🔧 Feedback Worker Started")
    print("=" * 70)
    print(f"  Task ID: {task_id}")
    print(f"  Evaluation Mode: {evaluation_mode or '(from config)'}")
    print(f"  PID: {os.getpid()}")
    print()

    try:
        # 执行反馈工作流
        run_feedback_workflow(task_id, evaluation_mode)

    except Exception as e:
        import traceback
        print()
        print("=" * 70)
        print(f"❌ Feedback Worker 异常: {e}")
        print("=" * 70)
        traceback.print_exc()

        # 更新任务状态为失败
        try:
            from workflow.task_manager import get_task_manager, TaskStatus
            tm = get_task_manager()
            task = tm.get_task(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.error = f"反馈流程失败: {str(e)}"
                tm._save_task(task)
        except:
            pass

        sys.exit(1)


def run_feedback_workflow(task_id: str, evaluation_mode: Optional[str] = None):
    """运行反馈工作流（状态机模式）

    Args:
        task_id: 任务ID
        evaluation_mode: 评估模式（可选），如果不指定则从配置读取

    流程:
        1. 验证任务状态（必须是COMPLETED）
        2. 加载generation_result.json（plan + trajectory + relevant_bullets）
        3. 评估方案（EVALUATING）
        4. 反思分析（REFLECTING）
        5. 更新playbook（CURATING）
        6. 完成（FEEDBACK_COMPLETED）
    """
    from workflow.task_manager import get_task_manager, TaskStatus
    from utils.config_loader import get_ace_config

    # 1. 加载任务
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        print(f"❌ 任务 {task_id} 不存在")
        sys.exit(1)

    # 验证状态
    if task.status != TaskStatus.COMPLETED:
        print(f"❌ 任务状态为 {task.status.value}，只能对已完成的任务进行反馈")
        sys.exit(1)

    print(f"[Worker] 任务已完成，开始反馈训练流程")

    # 2. 从配置读取默认评估模式（如果未指定）
    if evaluation_mode is None:
        ace_config = get_ace_config()
        evaluation_mode = ace_config.training.feedback_source
        print(f"[Worker] 使用配置的评估模式: {evaluation_mode}")
    else:
        print(f"[Worker] 使用指定的评估模式: {evaluation_mode}")

    # 3. 从 generation_result.json 加载完整数据
    print()
    print("=" * 70)
    print("加载生成结果")
    print("=" * 70)

    generation_result_data = task.load_generation_result()

    if not generation_result_data:
        # 旧任务（没有 generation_result.json）
        print("⚠️  旧任务缺少 generation_result.json，进行降级处理")

        # 降级：只加载 plan
        with open(task.plan_file, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        from ace_framework.playbook.schemas import ExperimentPlan
        plan = ExperimentPlan(**plan_data)

        trajectory = []
        relevant_bullets = []

        print(f"  ⚠️  Trajectory: 不可用（旧任务）")
        print(f"  ⚠️  Relevant bullets: 不可用（旧任务）")
        print(f"  ℹ️  反馈功能将受限")
    else:
        # 新任务（有完整数据）
        from ace_framework.playbook.schemas import ExperimentPlan, TrajectoryStep

        plan = ExperimentPlan(**generation_result_data["plan"])

        # 提取 trajectory（给 Reflector 分析推理过程）
        trajectory = [
            TrajectoryStep(**step)
            for step in generation_result_data.get("trajectory", [])
        ]

        # 提取 relevant_bullets（给 Reflector 标记有用/有害的 bullets）
        relevant_bullets = generation_result_data.get("relevant_bullets", [])

        print(f"  ✅ Plan: {plan.title}")
        print(f"  ✅ Trajectory 步骤: {len(trajectory)}")
        print(f"  ✅ Relevant bullets: {len(relevant_bullets)}")

        if trajectory:
            print(f"  ℹ️  Trajectory 预览: {trajectory[0].thought[:60]}...")
        if relevant_bullets:
            print(f"  ℹ️  Bullets 预览: {', '.join(relevant_bullets[:5])}")

    # 4. 初始化组件
    print()
    print("=" * 70)
    print("初始化ACE组件")
    print("=" * 70)

    # LLM Provider
    print("[1/4] 正在初始化LLM Provider...")
    from utils.llm_provider import QwenProvider

    llm_provider = QwenProvider(
        model_name="qwen-max",
        temperature=0.7,
        max_tokens=4096
    )
    print("  ✅ Qwen Provider 已初始化")

    # Playbook Manager
    print("[2/4] 正在加载Playbook...")
    from ace_framework.playbook.playbook_manager import PlaybookManager

    playbook_path = "data/playbooks/chemistry_playbook.json"
    playbook_manager = PlaybookManager(playbook_path=playbook_path)
    playbook_manager.load()
    print(f"  ✅ Playbook 已加载: {playbook_manager.playbook.size} bullets")

    # Reflector
    print("[3/4] 正在初始化Reflector...")
    from ace_framework.reflector.reflector import PlanReflector
    from utils.config_loader import ReflectorConfig

    reflector = PlanReflector(
        llm_provider=llm_provider,
        config=ReflectorConfig(),
        playbook_manager=playbook_manager
    )
    print("  ✅ Reflector 已初始化")

    # Curator
    print("[4/4] 正在初始化Curator...")
    from ace_framework.curator.curator import PlaybookCurator
    from utils.config_loader import CuratorConfig

    curator = PlaybookCurator(
        playbook_manager=playbook_manager,
        llm_provider=llm_provider,
        config=CuratorConfig()
        # 使用配置文件中的 allow_new_sections 设置（configs/playbook_sections.yaml）
        # 不在运行时覆盖，确保行为可预测且配置统一
    )
    print("  ✅ Curator 已初始化")

    # ========================================================================
    # Step 1: 评估
    # ========================================================================
    task.feedback_status = "evaluating"
    task_manager._save_task(task)

    print()
    print("=" * 70)
    print("STEP 1: 评估方案质量")
    print("=" * 70)

    from evaluation.evaluator import evaluate_plan

    try:
        feedback = evaluate_plan(
            plan=plan,
            source=evaluation_mode,
            llm_provider=llm_provider if evaluation_mode == "llm_judge" else None
        )

        task.save_feedback(feedback)
        print(f"  ✅ 评估完成: {feedback.overall_score:.2f}")

        # 显示评分详情
        print(f"\n  评分详情:")
        for score in feedback.scores:
            print(f"    - {score.criterion}: {score.score:.2f}")
        print(f"  评论: {feedback.comments}")
        print(f"  ✅ 反馈已保存: {task.feedback_file}")

    except Exception as e:
        # Feedback流程失败，不影响主任务
        task.feedback_status = "failed"
        task.feedback_error = f"评估失败: {str(e)}"
        task.failed_stage = "evaluating"  # 记录失败阶段
        task.status = TaskStatus.FAILED  # 标记整体失败（用于retry）
        task.error = task.feedback_error
        task_manager._save_task(task)
        print(f"  ❌ 评估失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # Step 2: 反思
    # ========================================================================
    task.feedback_status = "reflecting"
    task_manager._save_task(task)

    print()
    print("=" * 70)
    print("STEP 2: 反思分析")
    print("=" * 70)

    try:
        reflection_result = reflector.reflect(
            generated_plan=plan,
            feedback=feedback,
            trajectory=trajectory,
            playbook_bullets_used=relevant_bullets,
            verbose=True  # 启用详细进度输出
        )

        task.save_reflection(reflection_result)
        print(f"  ✅ 提取了 {len(reflection_result.insights)} 个 insights")
        print(f"  ✅ 标记了 {len(reflection_result.bullet_tags)} 个 bullets")

        # 显示insights示例
        if reflection_result.insights:
            print(f"\n  示例insight:")
            for i, insight in enumerate(reflection_result.insights[:3], 1):
                print(f"    {i}. [{insight.type}] {insight.description[:60]}...")
                print(f"       优先级: {insight.priority}")

        # 显示bullet标记统计
        if reflection_result.bullet_tags:
            helpful_count = sum(1 for tag in reflection_result.bullet_tags.values() if tag == "helpful")
            harmful_count = sum(1 for tag in reflection_result.bullet_tags.values() if tag == "harmful")
            neutral_count = sum(1 for tag in reflection_result.bullet_tags.values() if tag == "neutral")
            print(f"\n  Bullet 标记统计:")
            print(f"    - Helpful: {helpful_count}")
            print(f"    - Harmful: {harmful_count}")
            print(f"    - Neutral: {neutral_count}")

        print(f"  ✅ 反思结果已保存: {task.reflection_file}")

    except Exception as e:
        # Feedback流程失败
        task.feedback_status = "failed"
        task.feedback_error = f"反思失败: {str(e)}"
        task.failed_stage = "reflecting"  # 记录失败阶段
        task.status = TaskStatus.FAILED
        task.error = task.feedback_error
        task_manager._save_task(task)
        print(f"  ❌ 反思失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # Step 3: 更新 Playbook
    # ========================================================================
    task.feedback_status = "curating"
    task_manager._save_task(task)

    print()
    print("=" * 70)
    print("STEP 3: 更新 Playbook")
    print("=" * 70)

    size_before = playbook_manager.playbook.size

    try:
        curation_result = curator.update(
            reflection_result=reflection_result,
            verbose=True  # 启用详细进度输出
        )

        size_after = playbook_manager.playbook.size

        task.save_curation(curation_result)
        print(f"  ✅ Playbook已更新: {size_before} → {size_after} bullets")
        print(f"  ✅ 操作: +{curation_result.bullets_added} "
              f"-{curation_result.bullets_removed} ~{curation_result.bullets_updated}")

        # 显示新增bullets示例
        if curation_result.bullets_added > 0:
            print(f"\n  新增bullets预览:")
            # 获取最新的bullets（bullets是list，不是dict）
            new_bullets = playbook_manager.playbook.bullets[-min(3, curation_result.bullets_added):]
            for bullet in new_bullets:
                print(f"    - [{bullet.section}] {bullet.content[:60]}...")

        print(f"  ✅ 更新记录已保存: {task.curation_file}")

    except Exception as e:
        # Feedback流程失败
        task.feedback_status = "failed"
        task.feedback_error = f"Playbook更新失败: {str(e)}"
        task.failed_stage = "curating"  # 记录失败阶段
        task.status = TaskStatus.FAILED
        task.error = task.feedback_error
        task_manager._save_task(task)
        print(f"  ❌ Playbook更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # 完成
    # ========================================================================
    task.feedback_status = "completed"
    task_manager._save_task(task)

    print()
    print("=" * 70)
    print("✅ 反馈流程完成！")
    print("=" * 70)
    print(f"\n反馈数据:")
    print(f"  - 评估反馈: {task.feedback_file}")
    print(f"  - 反思结果: {task.reflection_file}")
    print(f"  - 更新记录: {task.curation_file}")
    print(f"\nPlaybook 变化:")
    print(f"  - 大小: {size_before} → {size_after} bullets")
    print(f"  - 新增: {curation_result.bullets_added}")
    print(f"  - 删除: {curation_result.bullets_removed}")
    print(f"  - 更新: {curation_result.bullets_updated}")
    print()


if __name__ == "__main__":
    main()
