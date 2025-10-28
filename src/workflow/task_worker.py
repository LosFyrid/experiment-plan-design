"""任务工作进程 - 独立运行

用法:
    python -m workflow.task_worker <task_id>
    python -m workflow.task_worker <task_id> --resume

特性:
- 作为独立进程运行（可脱离主CLI）
- 所有print输出被父进程管道捕获
- 状态更新写入文件系统（task.json）
- 支持断点恢复（状态机模式）

设计理念：
- 任务执行变成"状态机 + 幂等步骤"
- 每个步骤独立、可恢复
- 统一了"首次启动"和"断点恢复"
"""

import sys
import json
import time
import argparse
import os
from pathlib import Path

# 确保 src 在 Python 路径中（支持作为模块运行）
# 当前文件：src/workflow/task_worker.py
# 需要将 src 目录加入 sys.path
current_file = Path(__file__).resolve()
src_dir = current_file.parent.parent  # src/workflow -> src
project_root = src_dir.parent  # src -> 项目根

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")


def main():
    """工作进程主入口"""
    # 解析参数
    parser = argparse.ArgumentParser(description="任务工作进程")
    parser.add_argument("task_id", help="任务ID")
    parser.add_argument("--resume", action="store_true", help="断点恢复模式")
    args = parser.parse_args()

    task_id = args.task_id
    resume_mode = args.resume

    print("=" * 70)
    print("🔧 Task Worker Started")
    print("=" * 70)
    print(f"  Task ID: {task_id}")
    print(f"  Mode: {'Resume' if resume_mode else 'New'}")
    print(f"  PID: {os.getpid()}")
    print()

    try:
        # 执行任务工作流
        run_task_workflow(task_id, resume_mode)

    except Exception as e:
        import traceback
        print()
        print("=" * 70)
        print(f"❌ Worker异常: {e}")
        print("=" * 70)
        traceback.print_exc()

        # 更新任务状态为失败
        try:
            from workflow.task_manager import get_task_manager, TaskStatus
            tm = get_task_manager()
            task = tm.get_task(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                tm._save_task(task)
        except:
            pass

        sys.exit(1)


def run_task_workflow(task_id: str, resume_mode: bool):
    """运行任务工作流（状态机模式）

    Args:
        task_id: 任务ID
        resume_mode: 是否为断点恢复模式

    Notes:
        根据任务当前状态，决定从哪个步骤开始执行
    """
    import os
    from workflow.task_manager import get_task_manager, TaskStatus

    # 加载任务
    task_manager = get_task_manager()

    if resume_mode:
        # 断点恢复模式：从磁盘加载任务
        task = task_manager.get_task(task_id)
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            sys.exit(1)

        print(f"[Worker] 断点恢复模式，当前状态: {task.status.value}")

    else:
        # 首次启动模式：从 task.json 加载任务对象
        # （TaskScheduler 已在启动子进程前创建了 task.json）
        task = task_manager.get_task(task_id)

        if not task:
            print(f"❌ 任务 {task_id} 不存在（task.json 未找到）")
            sys.exit(1)

        print(f"[Worker] 新建任务，会话ID: {task.session_id}")

    # ========================================================================
    # 初始化组件（只在需要时初始化）
    # ========================================================================

    generator = None
    llm_provider = None

    def ensure_components_initialized():
        """惰性初始化组件"""
        nonlocal generator, llm_provider

        if generator is not None and llm_provider is not None:
            return

        print()
        print("=" * 70)
        print("初始化组件")
        print("=" * 70)

        print("[1/2] 正在初始化LLM Provider...")
        from utils.llm_provider import QwenProvider
        llm_provider = QwenProvider(
            model_name="qwen-max",
            temperature=0.7,
            max_tokens=4096
        )

        print("[2/2] 正在初始化Generator...")
        from ace_framework.generator.generator import create_generator
        generator = create_generator(
            playbook_path="data/playbooks/chemistry_playbook.json",
            llm_provider=llm_provider
        )

        print("✅ 组件初始化完成")
        print()

    # ========================================================================
    # 状态机：根据当前状态决定执行哪些步骤
    # ========================================================================

    if task.status == TaskStatus.PENDING:
        # Step 1: 提取需求
        print()
        print("=" * 70)
        print("STEP 1: 提取需求")
        print("=" * 70)

        ensure_components_initialized()

        # 加载对话历史
        if resume_mode:
            # 从任务目录加载
            config_file = task.task_dir / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            history = config['history']
        else:
            # 已在外层加载
            config_file = task.task_dir / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            history = config['history']

        # 提取需求
        task.status = TaskStatus.EXTRACTING
        task_manager._save_task(task)

        from workflow.command_handler import GenerateCommandHandler
        from workflow.task_manager import LogWriter

        # 子进程模式：只print，不写文件（TaskScheduler负责写文件）
        log_writer = LogWriter(task.log_file, write_to_file=False)

        try:
            requirements = GenerateCommandHandler._extract_requirements(
                history, llm_provider, log_writer
            )

            # 验证必需字段
            if not requirements.get("target_compound") and not requirements.get("objective"):
                raise ValueError("无法提取足够信息（缺少target_compound和objective）")

            # 保存需求到文件
            task.save_requirements(requirements)
            print(f"✅ 需求已提取: {task.requirements_file}")
            print(f"   - objective: {requirements.get('objective', 'N/A')}")
            print(f"   - target_compound: {requirements.get('target_compound', 'N/A')}")

            log_writer.write(f"需求已提取并保存: {task.requirements_file}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"需求提取失败: {str(e)}"
            task.failed_stage = "extracting"  # 记录失败阶段
            task_manager._save_task(task)
            log_writer.write(f"失败: {task.error}")
            log_writer.close()
            sys.exit(1)
        finally:
            log_writer.close()

        # 进入等待确认状态
        task.status = TaskStatus.AWAITING_CONFIRM
        task_manager._save_task(task)

        print()
        print("=" * 70)
        print("⏸️  等待用户确认")
        print("=" * 70)
        print(f"需求文件: {task.requirements_file}")
        print()
        print("💡 用户可以:")
        print(f"   1. 查看需求: cat {task.requirements_file}")
        print(f"   2. 修改需求: nano/vim {task.requirements_file}")
        print(f"   3. 在CLI中执行 /confirm 继续")
        print(f"   4. 在CLI中执行 /cancel 取消")
        print()
        print("[Worker] 子进程退出，等待用户确认...")
        print()

        # 正常退出（等待用户确认后重新启动）
        sys.exit(0)

    elif task.status == TaskStatus.AWAITING_CONFIRM:
        # 用户已确认，从Step 2继续（RAG检索）
        print("[Worker] 用户已确认需求，继续执行...")
        # 继续往下执行

    elif task.status == TaskStatus.RETRIEVING:
        # 从Step 3继续（生成方案）
        print("[Worker] 从RAG检索步骤继续...")
        # 继续往下执行

    elif task.status == TaskStatus.GENERATING:
        # 从Step 4继续
        print("[Worker] 从生成步骤继续...")
        # 继续往下执行

    elif task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        print(f"⚠️  任务已结束（{task.status.value}），无需执行")
        sys.exit(0)

    # ========================================================================
    # Step 2: RAG检索（如果状态 >= AWAITING_CONFIRM）
    # ========================================================================

    if task.status in [TaskStatus.AWAITING_CONFIRM, TaskStatus.RETRIEVING]:
        print()
        print("=" * 70)
        print("STEP 2: RAG检索模板")
        print("=" * 70)

        task.status = TaskStatus.RETRIEVING
        task_manager._save_task(task)

        # 加载需求
        requirements = task.load_requirements()
        if not requirements:
            task.status = TaskStatus.FAILED
            task.error = "需求文件不存在或已损坏"
            task_manager._save_task(task)
            print(f"❌ {task.error}")
            sys.exit(1)

        # 使用真实 RAG 检索
        try:
            from workflow.rag_adapter import RAGAdapter

            print("[Worker] 初始化 RAG 适配器...")

            # 创建 RAG 适配器（惰性初始化）
            rag_adapter = RAGAdapter()

            # 检索相关文档（使用配置的 top_k，默认 5）
            templates = rag_adapter.retrieve_templates(
                requirements=requirements,
                top_k=5  # 可以从配置读取
            )

            print(f"✅ 检索到 {len(templates)} 个相关文档")

            # 打印前3个结果预览
            for i, t in enumerate(templates[:3], 1):
                score = t.get('score', 0)
                title = t.get('title', 'Unknown')
                print(f"  {i}. [{score:.3f}] {title}")

        except Exception as e:
            import traceback
            print(f"⚠️  RAG 检索失败: {e}")
            traceback.print_exc()
            print("⚠️  回退到空模板列表（Generator 将仅使用 Playbook）")
            templates = []

        # 保存templates到文件
        task.save_templates(templates)
        print(f"✅ 检索结果已保存: {task.templates_file}")

    # ========================================================================
    # Step 3: 生成方案（如果状态 >= RETRIEVING）
    # ========================================================================

    if task.status in [TaskStatus.RETRIEVING, TaskStatus.GENERATING]:
        print()
        print("=" * 70)
        print("STEP 3: 生成实验方案")
        print("=" * 70)

        ensure_components_initialized()

        task.status = TaskStatus.GENERATING
        task_manager._save_task(task)

        # 加载需求和模板
        requirements = task.load_requirements()
        with open(task.templates_file, 'r', encoding='utf-8') as f:
            templates = json.load(f)

        try:
            start_time = time.time()

            generation_result = generator.generate(
                requirements=requirements,
                templates=templates,
                verbose=True  # 启用详细进度输出
            )

            duration = time.time() - start_time

            # 保存方案到文件（向后兼容）
            task.save_plan(generation_result.generated_plan)

            # 保存完整的 GenerationResult（包含 trajectory 和 bullets）
            task.save_generation_result(generation_result)

            # 保存元数据到 task.json
            task.metadata = generation_result.generation_metadata
            task.metadata['duration'] = duration

            print(f"✅ 方案已生成: {task.plan_file}")
            print(f"   标题: {generation_result.generated_plan.title}")
            print(f"   耗时: {duration:.2f}s")
            print(f"   Tokens: {task.metadata.get('total_tokens', 0)}")

            # 调试信息：显示 trajectory 和 bullets 保存情况
            print(f"\n📊 GenerationResult 详情:")
            print(f"   - Trajectory 步骤数: {len(generation_result.trajectory)}")
            print(f"   - Relevant bullets: {len(generation_result.relevant_bullets)}")
            if generation_result.trajectory:
                print(f"   - Trajectory 预览: {generation_result.trajectory[0].thought[:60]}...")
            if generation_result.relevant_bullets:
                print(f"   - Bullets 预览: {', '.join(generation_result.relevant_bullets[:5])}")
            print(f"   - 完整结果已保存: {task.generation_result_file}")

            # 完成
            task.status = TaskStatus.COMPLETED
            task_manager._save_task(task)

            print()
            print("=" * 70)
            print("✅ 任务完成！")
            print("=" * 70)
            print(f"方案文件: {task.plan_file}")
            print()

            sys.exit(0)

        except Exception as e:
            import traceback
            task.status = TaskStatus.FAILED
            task.error = f"生成失败: {str(e)}"
            task.failed_stage = "generating"  # 记录失败阶段
            task_manager._save_task(task)

            print(f"❌ 生成失败: {e}")
            traceback.print_exc()

            sys.exit(1)


if __name__ == "__main__":
    import os
    main()
