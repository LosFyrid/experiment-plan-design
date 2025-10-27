#!/usr/bin/env python3
"""
简化版ACE运行示例 - 使用真实Qwen API

这是一个最小化的ACE运行示例，展示：
1. 如何初始化观测系统
2. 如何运行完整的ACE循环
3. 如何查看生成的观测数据

运行前确保：
1. 已安装依赖: pip install -r requirements.txt && pip install dashscope
2. 已配置.env文件中的DASHSCOPE_API_KEY
3. 已创建必要目录: mkdir -p data/playbooks logs
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("ACE框架运行示例 - 使用真实Qwen API")
print("=" * 80)

# ============================================================================
# 步骤1: 初始化环境
# ============================================================================
print("\n[1/8] 初始化环境...")

# 检查API Key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 错误: 未找到DASHSCOPE_API_KEY")
    print("\n请确保：")
    print("1. 已复制.env.example为.env")
    print("2. 在.env中填写你的DASHSCOPE_API_KEY")
    print("\n获取API Key: https://dashscope.console.aliyun.com/")
    sys.exit(1)

print(f"  ✓ API Key已配置: {api_key[:10]}...")
print(f"  ✓ 项目根目录: {project_root}")

# ============================================================================
# 步骤2: 初始化观测系统
# ============================================================================
print("\n[2/8] 初始化观测系统...")

from utils.logs_manager import get_logs_manager
from utils.structured_logger import (
    create_generator_logger,
    create_reflector_logger,
    create_curator_logger
)
from utils.performance_monitor import create_performance_monitor
from utils.llm_call_tracker import create_llm_call_tracker
from utils.playbook_version_tracker import PlaybookVersionTracker

# 启动新run
logs_manager = get_logs_manager()
run_id = logs_manager.start_run()

print(f"  ✓ 启动新run: {run_id}")
print(f"  ✓ 日志目录: {logs_manager.get_run_dir(run_id)}")

# 创建观测工具
perf_monitor = create_performance_monitor(run_id=run_id, logs_manager=logs_manager)
perf_monitor.start_run()

generator_logger = create_generator_logger(logs_manager=logs_manager)
reflector_logger = create_reflector_logger(logs_manager=logs_manager)
curator_logger = create_curator_logger(logs_manager=logs_manager)

generator_llm_tracker = create_llm_call_tracker("generator", run_id=run_id, logs_manager=logs_manager)
reflector_llm_tracker = create_llm_call_tracker("reflector", run_id=run_id, logs_manager=logs_manager)
curator_llm_tracker = create_llm_call_tracker("curator", run_id=run_id, logs_manager=logs_manager)

# 注意：PlaybookVersionTracker需要playbook_path，会在后面创建playbook后初始化

print("  ✓ 所有观测工具已初始化")

# ============================================================================
# 步骤3: 创建Playbook
# ============================================================================
print("\n[3/8] 创建Playbook...")

from ace_framework.playbook.playbook_manager import PlaybookManager
from ace_framework.playbook.schemas import PlaybookBullet, BulletMetadata

playbook_path = str(project_root / "data" / "playbooks" / "chemistry_playbook.json")
playbook_manager = PlaybookManager(playbook_path=playbook_path)

# 创建新playbook或加载现有的
try:
    playbook_manager.load()
    print(f"  ✓ 已加载现有Playbook: {playbook_manager.playbook.size} bullets")
except FileNotFoundError:
    # 创建新playbook并添加初始bullets
    playbook_manager.get_or_create()

    initial_bullets = [
        PlaybookBullet(
            id="mat-00001",
            section="material_selection",
            content="始终验证试剂纯度是否符合实验要求，并在材料清单中明确标注纯度规格",
            metadata=BulletMetadata(
                helpful_count=5,
                harmful_count=0,
                created_at=datetime.now().isoformat(),
                source="manual"
            )
        ),
        PlaybookBullet(
            id="proc-00001",
            section="procedure_design",
            content="对于挥发性或有毒试剂，必须在通风橱中操作，并在步骤中明确标注",
            metadata=BulletMetadata(
                helpful_count=8,
                harmful_count=0,
                created_at=datetime.now().isoformat(),
                source="manual"
            )
        ),
        PlaybookBullet(
            id="safe-00001",
            section="safety_protocols",
            content="所有实验操作必须佩戴个人防护装备（实验服、护目镜、手套）",
            metadata=BulletMetadata(
                helpful_count=10,
                harmful_count=0,
                created_at=datetime.now().isoformat(),
                source="manual"
            )
        )
    ]

    for bullet in initial_bullets:
        playbook_manager.add_bullet(bullet)

    playbook_manager.save()
    print(f"  ✓ Playbook已创建: {playbook_path}")
    print(f"  ✓ 初始bullets: {len(initial_bullets)}个")

# 现在创建version_tracker（需要playbook_path）
version_tracker = PlaybookVersionTracker(
    playbook_path=playbook_path,
    logs_manager=logs_manager
)

# 保存初始版本
version_tracker.save_version(
    reason="Playbook初始化",
    trigger="initialization",
    run_id=run_id
)

# ============================================================================
# 步骤4: 初始化LLM Provider
# ============================================================================
print("\n[4/8] 初始化LLM Provider...")

from utils.llm_provider import QwenProvider

llm_provider = QwenProvider(
    model_name="qwen-max",  # 使用qwen-max获得最佳效果
    temperature=0.7,
    max_tokens=4096
)

print("  ✓ Qwen Provider已初始化 (qwen-max)")

# ============================================================================
# 步骤5: 运行Generator
# ============================================================================
print("\n[5/8] 运行Generator...")
print("  → 正在生成实验方案...")

from ace_framework.generator.generator import PlanGenerator
from utils.config_loader import GeneratorConfig

generator = PlanGenerator(
    playbook_manager=playbook_manager,
    llm_provider=llm_provider,
    config=GeneratorConfig(),
    logger=generator_logger,
    perf_monitor=perf_monitor,
    llm_tracker=generator_llm_tracker
)

# 定义实验需求
requirements = {
    "objective": "合成阿司匹林（乙酰水杨酸）",
    "target_compound": "阿司匹林 (C9H8O4)",
    "constraints": [
        "使用常规实验室设备",
        "2小时内完成",
        "产率目标 >75%"
    ]
}

try:
    generation_result = generator.generate(requirements=requirements)

    print(f"  ✓ 方案已生成: \"{generation_result.generated_plan.title}\"")
    print(f"  ✓ 使用了 {len(generation_result.relevant_bullets)} 个playbook bullets")
    print(f"  ✓ 耗时: {generation_result.generation_metadata['duration']:.2f}s")
    print(f"  ✓ Tokens: {generation_result.generation_metadata['total_tokens']}")

except Exception as e:
    print(f"  ❌ Generator失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# 步骤6: 评估生成的方案
# ============================================================================
print("\n[6/9] 评估生成的方案...")

from evaluation.evaluator import evaluate_plan
from utils.config_loader import get_ace_config

# 从配置文件读取评估模式
ace_config = get_ace_config()
evaluation_mode = os.getenv("EVALUATION_MODE", ace_config.training.feedback_source)  # 默认使用配置文件中的设置

print(f"  → 使用 '{evaluation_mode}' 模式评估...")

try:
    if evaluation_mode == "llm_judge":
        # LLM评估模式（消耗额外tokens，但更准确）
        feedback = evaluate_plan(
            plan=generation_result.generated_plan,
            source="llm_judge",
            llm_provider=llm_provider
        )
        print(f"  ✓ LLM评估完成: {feedback.overall_score:.2f}")
    else:
        # 自动评估模式（基于规则，快速免费）
        feedback = evaluate_plan(
            plan=generation_result.generated_plan,
            source="auto"
        )
        print(f"  ✓ 自动评估完成: {feedback.overall_score:.2f}")

    # 显示评分详情
    print(f"\n  评分详情:")
    for score in feedback.scores:
        print(f"    - {score.criterion}: {score.score:.2f}")
    print(f"  评论: {feedback.comments}")

except Exception as e:
    print(f"  ⚠️  评估失败，使用默认反馈: {e}")
    # 如果评估失败，使用默认反馈
    from ace_framework.playbook.schemas import Feedback, FeedbackScore
    feedback = Feedback(
        scores=[
            FeedbackScore(criterion="completeness", score=0.8, explanation="默认"),
            FeedbackScore(criterion="safety", score=0.8, explanation="默认"),
            FeedbackScore(criterion="clarity", score=0.8, explanation="默认"),
            FeedbackScore(criterion="executability", score=0.8, explanation="默认"),
            FeedbackScore(criterion="cost_effectiveness", score=0.7, explanation="默认"),
        ],
        overall_score=0.78,
        feedback_source="auto",
        comments="评估系统异常，使用默认评分"
    )

# ============================================================================
# 步骤7: 运行Reflector
# ============================================================================
print("\n[7/9] 运行Reflector...")
print("  → 正在分析方案质量...")

from ace_framework.reflector.reflector import PlanReflector
from utils.config_loader import ReflectorConfig

reflector = PlanReflector(
    llm_provider=llm_provider,
    config=ReflectorConfig(),
    playbook_manager=playbook_manager,
    logger=reflector_logger,
    perf_monitor=perf_monitor,
    llm_tracker=reflector_llm_tracker
)

try:
    reflection_result = reflector.reflect(
        generated_plan=generation_result.generated_plan,
        feedback=feedback,
        trajectory=generation_result.trajectory,
        playbook_bullets_used=generation_result.relevant_bullets
    )

    print(f"  ✓ 提取了 {len(reflection_result.insights)} 个insights")
    print(f"  ✓ 标记了 {len(reflection_result.bullet_tags)} 个bullets")

    # 显示insights示例
    if reflection_result.insights:
        print(f"\n  示例insight:")
        first_insight = reflection_result.insights[0]
        print(f"    - 类别: {first_insight.type}")
        print(f"    - 内容: {first_insight.description[:60]}...")
        print(f"    - 优先级: {first_insight.priority}")

except Exception as e:
    print(f"  ❌ Reflector失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# 步骤8: 运行Curator
# ============================================================================
print("\n[8/9] 运行Curator...")
print("  → 正在更新Playbook...")

from ace_framework.curator.curator import PlaybookCurator
from utils.config_loader import CuratorConfig

# 是否允许Curator提议新的sections
# - True: Curator可以根据insights提议新的section类别
# - False: 只能使用预定义的6个core sections
# - None: 使用配置文件(playbook_sections.yaml)中的设置
allow_new_sections = None  # 默认使用配置文件

curator = PlaybookCurator(
    playbook_manager=playbook_manager,
    llm_provider=llm_provider,
    config=CuratorConfig(),
    logger=curator_logger,
    perf_monitor=perf_monitor,
    llm_tracker=curator_llm_tracker,
    allow_new_sections=allow_new_sections  # 使用上面定义的变量（默认None=配置文件）
)

size_before = playbook_manager.playbook.size

try:
    curation_result = curator.update(reflection_result=reflection_result)

    size_after = playbook_manager.playbook.size

    print(f"  ✓ Playbook已更新: {size_before} → {size_after} bullets")
    print(f"  ✓ 操作: +{curation_result.bullets_added} "
          f"-{curation_result.bullets_removed} ~{curation_result.bullets_updated}")

    # 保存更新后的版本
    version_tracker.save_version(
        reason=f"Curator更新（+{curation_result.bullets_added} -{curation_result.bullets_removed} ~{curation_result.bullets_updated}）",
        trigger="curation",
        run_id=run_id,
        changes={
            "added": curation_result.bullets_added,
            "updated": curation_result.bullets_updated,
            "removed": curation_result.bullets_removed
        }
    )

except Exception as e:
    print(f"  ❌ Curator失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# 步骤9: 保存观测数据
# ============================================================================
print("\n[9/9] 保存观测数据...")

perf_monitor.end_run()
perf_monitor.save_report(run_id=run_id)
logs_manager.end_run()

print("  ✓ 性能报告已保存")
print("  ✓ Playbook版本已保存")

# ============================================================================
# 完成 - 显示结果
# ============================================================================
print("\n" + "=" * 80)
print("✅ ACE运行成功！")
print("=" * 80)

print(f"\nRun ID: {run_id}")

print("\n观测数据位置:")
today = datetime.now().strftime("%Y%m%d")
print(f"  - 运行日志: logs/runs/{today}/run_{run_id}/")
print(f"  - LLM调用: logs/llm_calls/{today}/")
print(f"  - Playbook版本: logs/playbook_versions/")

print("\n生成的文件:")
run_dir = logs_manager.get_run_dir(run_id)
for file in run_dir.iterdir():
    print(f"  - {file.name}")

print("\n性能概览:")
perf_monitor.print_summary()

print("\n" + "=" * 80)
print("完成！查看上方的分析脚本命令来探索观测数据。")
print("=" * 80)

print("\n下一步: 使用分析脚本查询数据")
print("-" * 80)
print(f"# 查看这次运行的详情")
print(f"python scripts/analysis/query_runs.py --run-id {run_id}")
print()
print(f"# 查看LLM调用")
print(f"python scripts/analysis/query_llm_calls.py --run-id {run_id}")
print()
print(f"# 分析性能")
print(f"python scripts/analysis/analyze_performance.py --run-id {run_id}")
print()
print(f"# 查看playbook演化")
print(f"python scripts/analysis/analyze_playbook_evolution.py --growth-stats")
print("-" * 80)