#!/usr/bin/env python3
"""
调试脚本：检查bullet tags问题

分析：
1. Generator返回的bullets_used
2. Reflector收到的参数
3. Reflector返回的bullet_tags
4. Curator实际更新的bullets
"""

import json
from pathlib import Path

# 最近一次运行的日志
run_dir = Path("logs/runs/2025-10-24/run_125836_QkXKJx")

print("=" * 80)
print("BULLET TAGS 问题分析")
print("=" * 80)

# 1. Generator输出
print("\n[1] Generator输出的bullets_used:")
with open(run_dir / "generator.jsonl") as f:
    for line in f:
        event = json.loads(line)
        if event.get("event_type") == "plan_generated":
            bullets_used = event["data"]["bullets_used"]
            print(f"  ✓ {len(bullets_used)}个bullets: {bullets_used}")
            break

# 2. Reflector输出
print("\n[2] Reflector返回的bullet_tags:")
with open(run_dir / "reflector.jsonl") as f:
    for line in f:
        event = json.loads(line)
        if event.get("event_type") == "bullet_tagging_done":
            tags = event["data"]["tags"]
            print(f"  ❌ 返回了 {len(tags)} 个tags:")
            for key, value in tags.items():
                print(f"     - {key}: {value}")
            print(f"\n  问题：这些key不是bullet IDs，而是insight类型名称！")
            break

# 3. 预期的正确格式
print("\n[3] 预期的正确bullet_tags格式应该是:")
print("  {")
for bullet_id in bullets_used[:3]:
    print(f'    "{bullet_id}": "helpful/harmful/neutral",')
print("    ...")
print("  }")

# 4. 问题分析
print("\n[4] 问题根源分析:")
print("  原因1: LLM在生成JSON时，把insight的type字段值误用为bullet_tags的key")
print("  原因2: Prompt中可能没有明确强调bullet_tags必须使用bullet ID作为key")
print("  原因3: Reflector的refinement轮次中，可能丢失了bullets_used的上下文")

print("\n[5] 修复建议:")
print("  方案1: 在Reflector prompt中更明确地要求使用bullet ID")
print("  方案2: 在prompt中列出所有bullet IDs的列表，让LLM从中选择")
print("  方案3: 在Reflector解析时，检测到错误格式后回退或警告")

print("\n" + "=" * 80)
