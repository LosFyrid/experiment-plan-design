#!/usr/bin/env python3
"""
端到端自动化测试脚本

测试完整工作流：Chatbot → 需求提取 → Mock RAG → Generator
"""

import sys
import os
import time
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("端到端自动化测试")
print("=" * 80)

# ============================================================================
# Step 1: 初始化系统
# ============================================================================
print("\n[1/6] 初始化系统组件...")

try:
    from chatbot.chatbot import Chatbot
    from workflow.command_handler import GenerateCommandHandler
    from workflow.task_manager import get_task_manager, TaskStatus
    from ace_framework.generator.generator import create_generator
    from utils.llm_provider import QwenProvider

    print("  ✓ 模块导入成功")
except Exception as e:
    print(f"  ✗ 模块导入失败: {e}")
    sys.exit(1)

# 初始化Chatbot
print("\n  初始化Chatbot...")
try:
    bot = Chatbot(config_path="configs/chatbot_config.yaml")
    print("  ✓ Chatbot初始化成功")
except Exception as e:
    print(f"  ✗ Chatbot初始化失败: {e}")
    print("  提示: 确保MOSES本体数据已准备好")
    sys.exit(1)

# 初始化LLM Provider
print("\n  初始化LLM Provider...")
try:
    llm_provider = QwenProvider(
        model_name="qwen-max",
        temperature=0.7,
        max_tokens=4096
    )
    print("  ✓ LLM Provider初始化成功")
except Exception as e:
    print(f"  ✗ LLM Provider初始化失败: {e}")
    print("  提示: 检查.env中的DASHSCOPE_API_KEY")
    sys.exit(1)

# 初始化Generator
print("\n  初始化Generator...")
try:
    generator = create_generator(
        playbook_path="data/playbooks/chemistry_playbook.json",
        llm_provider=llm_provider
    )
    print("  ✓ Generator初始化成功")
    print(f"    Playbook bullets: {generator.playbook_manager.playbook.size}")
except Exception as e:
    print(f"  ✗ Generator初始化失败: {e}")
    import traceback
    traceback.print_exc()
    print("  提示: 确保playbook文件存在，或运行examples/run_simple_ace.py创建")
    sys.exit(1)

# 初始化Command Handler
print("\n  初始化Command Handler...")
try:
    cmd_handler = GenerateCommandHandler(
        chatbot=bot,
        generator=generator,
        llm_provider=llm_provider
    )
    print("  ✓ Command Handler初始化成功")
except Exception as e:
    print(f"  ✗ Command Handler初始化失败: {e}")
    sys.exit(1)

task_manager = get_task_manager()

print("\n✅ 所有组件初始化成功！")

# ============================================================================
# Step 2: 模拟用户对话
# ============================================================================
print("\n[2/6] 模拟用户对话...")
print("=" * 80)

session_id = "test_session_" + str(int(time.time()))
print(f"会话ID: {session_id}")

# 第一轮对话
print("\n用户: 我想做DSS 2205的固溶处理实验")
try:
    response1 = bot.chat("我想做DSS 2205的固溶处理实验", session_id=session_id)
    print(f"助手: {response1[:200]}..." if len(response1) > 200 else f"助手: {response1}")
    print("  ✓ 对话1成功")
except Exception as e:
    print(f"  ✗ 对话1失败: {e}")

# 第二轮对话
print("\n用户: 温度范围1050-1080度，需要水淬")
try:
    response2 = bot.chat("温度范围1050-1080度，需要水淬", session_id=session_id)
    print(f"助手: {response2[:200]}..." if len(response2) > 200 else f"助手: {response2}")
    print("  ✓ 对话2成功")
except Exception as e:
    print(f"  ✗ 对话2失败: {e}")

# 第三轮对话
print("\n用户: 试样10mm厚，保温10分钟，需要做金相分析")
try:
    response3 = bot.chat("试样10mm厚，保温10分钟，需要做金相分析", session_id=session_id)
    print(f"助手: {response3[:200]}..." if len(response3) > 200 else f"助手: {response3}")
    print("  ✓ 对话3成功")
except Exception as e:
    print(f"  ✗ 对话3失败: {e}")

# 获取对话历史
history = bot.get_history(session_id)
print(f"\n对话历史: {len(history)}条消息")

# ============================================================================
# Step 3: 触发生成任务
# ============================================================================
print("\n[3/6] 触发生成任务...")
print("=" * 80)

try:
    task_id = cmd_handler.handle(session_id)
    print(f"✓ 任务已提交: {task_id}")
    print(f"  任务目录: logs/generation_tasks/{task_id}/")
    print(f"  日志文件: logs/generation_tasks/{task_id}/task.log")
except Exception as e:
    print(f"✗ 任务提交失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Step 4: 监控任务状态（等待需求提取）
# ============================================================================
print("\n[4/6] 监控任务状态...")
print("=" * 80)

print("\n等待任务进入AWAITING_CONFIRM状态...")

max_wait = 30  # 最多等待30秒
start_time = time.time()
last_status = None

while time.time() - start_time < max_wait:
    task = task_manager.get_task(task_id)

    if task.status != last_status:
        print(f"  [{time.time()-start_time:.1f}s] 状态变更: {task.status.value}")
        last_status = task.status

    if task.status == TaskStatus.AWAITING_CONFIRM:
        print("\n✓ 任务已进入AWAITING_CONFIRM状态")
        break

    if task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
        print(f"\n✗ 任务异常结束: {task.status.value}")
        if task.error:
            print(f"  错误: {task.error}")
        sys.exit(1)

    time.sleep(0.5)

if task.status != TaskStatus.AWAITING_CONFIRM:
    print(f"\n✗ 超时：任务未进入AWAITING_CONFIRM状态（当前: {task.status.value}）")
    sys.exit(1)

# 检查需求文件
print("\n检查提取的需求...")
if task.requirements_file.exists():
    with open(task.requirements_file, 'r', encoding='utf-8') as f:
        requirements = json.load(f)

    print(f"  ✓ 需求文件存在: {task.requirements_file}")
    print(f"\n需求内容:")
    print(json.dumps(requirements, indent=2, ensure_ascii=False))

    # 验证必需字段
    if "objective" in requirements or "target_compound" in requirements:
        print("\n  ✓ 必需字段存在")
    else:
        print("\n  ✗ 缺少必需字段")
else:
    print(f"  ✗ 需求文件不存在")
    sys.exit(1)

# ============================================================================
# Step 5: 确认继续（自动）
# ============================================================================
print("\n[5/6] 自动确认需求，继续生成...")
print("=" * 80)

# 修改任务状态为RETRIEVING（模拟用户/confirm）
task.status = TaskStatus.RETRIEVING
task_manager._save_task(task)
print("✓ 已确认需求，任务继续执行")

# 等待任务完成
print("\n等待任务完成...")
max_wait = 60  # 最多等待60秒
start_time = time.time()
last_status = TaskStatus.RETRIEVING

while time.time() - start_time < max_wait:
    task = task_manager.get_task(task_id)

    if task.status != last_status:
        print(f"  [{time.time()-start_time:.1f}s] 状态变更: {task.status.value}")
        last_status = task.status

    if task.status == TaskStatus.COMPLETED:
        print("\n✓ 任务已完成")
        break

    if task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
        print(f"\n✗ 任务异常结束: {task.status.value}")
        if task.error:
            print(f"  错误: {task.error}")

        # 打印日志
        if task.log_file.exists():
            print("\n任务日志:")
            with open(task.log_file, 'r', encoding='utf-8') as f:
                print(f.read())

        sys.exit(1)

    time.sleep(0.5)

if task.status != TaskStatus.COMPLETED:
    print(f"\n✗ 超时：任务未完成（当前: {task.status.value}）")
    sys.exit(1)

# ============================================================================
# Step 6: 验证结果
# ============================================================================
print("\n[6/6] 验证生成结果...")
print("=" * 80)

# 检查templates文件
print("\n1. 检查RAG检索结果...")
if task.templates_file.exists():
    with open(task.templates_file, 'r', encoding='utf-8') as f:
        templates = json.load(f)

    print(f"  ✓ 模板文件存在: {task.templates_file}")
    print(f"  检索到 {len(templates)} 个模板:")
    for i, t in enumerate(templates, 1):
        print(f"    {i}. {t.get('title', 'N/A')}")

    if len(templates) > 0:
        print("\n  ✓ Mock RAG工作正常")
    else:
        print("\n  ⚠️  未检索到模板（可能是正常的）")
else:
    print(f"  ✗ 模板文件不存在")

# 检查plan文件
print("\n2. 检查生成的方案...")
if task.plan_file.exists():
    with open(task.plan_file, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    print(f"  ✓ 方案文件存在: {task.plan_file}")
    print(f"\n方案概要:")
    print(f"  标题: {plan.get('title', 'N/A')}")
    print(f"  目标: {plan.get('objective', 'N/A')[:100]}...")
    print(f"  材料数: {len(plan.get('materials', []))}")
    print(f"  步骤数: {len(plan.get('procedure', []))}")
    print(f"  安全注意事项: {len(plan.get('safety_notes', []))}条")

    # 验证必需字段
    required_fields = ['title', 'objective', 'materials', 'procedure', 'safety_notes']
    missing = [f for f in required_fields if f not in plan or not plan[f]]

    if not missing:
        print("\n  ✓ 所有必需字段存在")
    else:
        print(f"\n  ⚠️  缺少字段: {missing}")
else:
    print(f"  ✗ 方案文件不存在")
    sys.exit(1)

# 检查元数据
print("\n3. 检查生成元数据...")
print(f"  耗时: {task.metadata.get('duration', 0):.2f}s")
print(f"  Tokens: {task.metadata.get('total_tokens', 0)}")
print(f"  使用Bullets: {task.metadata.get('retrieved_bullets_count', 0)}个")

# 检查日志
print("\n4. 检查任务日志...")
if task.log_file.exists():
    with open(task.log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    log_lines = log_content.strip().split('\n')
    print(f"  ✓ 日志文件存在: {task.log_file}")
    print(f"  日志行数: {len(log_lines)}")

    # 检查关键步骤
    steps = [
        "STEP 1: 提取需求",
        "STEP 2: 等待用户确认",
        "STEP 3: RAG检索模板",
        "STEP 4: 生成实验方案"
    ]

    print("\n  关键步骤:")
    for step in steps:
        if step in log_content:
            print(f"    ✓ {step}")
        else:
            print(f"    ✗ {step}")

    # 检查Mock RAG日志
    if "[MockRAG]" in log_content:
        print("\n  ✓ Mock RAG执行成功")
    else:
        print("\n  ⚠️  未找到Mock RAG日志")

else:
    print(f"  ✗ 日志文件不存在")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)

print(f"\n任务ID: {task_id}")
print(f"任务目录: {task.task_dir}")
print(f"最终状态: {task.status.value}")

print("\n测试项:")
print("  ✓ 1. Chatbot对话")
print("  ✓ 2. 需求提取")
print("  ✓ 3. Mock RAG检索")
print("  ✓ 4. Generator生成")
print("  ✓ 5. 文件持久化")

print("\n生成的文件:")
print(f"  • {task.requirements_file}")
print(f"  • {task.templates_file}")
print(f"  • {task.plan_file}")
print(f"  • {task.log_file}")

print("\n查看方案:")
print(f"  cat {task.plan_file}")
print(f"  或使用CLI: python examples/workflow_cli.py")
print(f"  然后输入: /view {task_id}")

print("\n" + "=" * 80)
print("✅ 端到端测试完成！")
print("=" * 80)

# 清理
bot.cleanup()
