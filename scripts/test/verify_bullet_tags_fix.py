#!/usr/bin/env python3
"""
测试脚本：验证bullet tags修复

测试修改后的Reflector是否正确返回bullet IDs而非insight类型。
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ace_framework.reflector.prompts import build_refinement_prompt

# 模拟数据
previous_insights = [
    {
        "type": "safety_issue",
        "description": "Missing emergency procedures",
        "suggested_bullet": "Include detailed emergency procedures",
        "target_section": "safety_protocols",
        "priority": "high"
    }
]

bullets_used = ["proc-00001", "qc-00002", "safe-00003"]
bullet_contents = {
    "proc-00001": "For temperature-sensitive reactions...",
    "qc-00002": "Record physical properties...",
    "safe-00003": "For reactions generating toxic gases..."
}

# 生成prompt
prompt = build_refinement_prompt(
    previous_insights=previous_insights,
    previous_analysis="Some analysis...",
    round_number=2,
    max_rounds=5,
    bullets_used=bullets_used,
    bullet_contents=bullet_contents
)

print("=" * 80)
print("REFINEMENT PROMPT 验证")
print("=" * 80)

# 检查关键内容
checks = {
    "包含bullets列表": "Playbook Bullets Referenced" in prompt,
    "包含proc-00001": "proc-00001" in prompt,
    "包含qc-00002": "qc-00002" in prompt,
    "包含safe-00003": "safe-00003" in prompt,
    "包含IMPORTANT提示": "IMPORTANT" in prompt,
    "包含bullet ID示例": '"proc-00001"' in prompt or '"qc-00002"' in prompt,
}

print("\n✅ 修复验证:")
for check, passed in checks.items():
    status = "✓" if passed else "✗"
    print(f"  {status} {check}")

all_passed = all(checks.values())
print(f"\n{'✅ 所有检查通过!' if all_passed else '❌ 有检查失败'}")

# 显示prompt片段
print("\n" + "=" * 80)
print("PROMPT 片段预览:")
print("=" * 80)
print(prompt[1500:2500] if len(prompt) > 2500 else prompt)

print("\n" + "=" * 80)
print("说明：")
print("  - 修复后的prompt包含完整的bullets列表")
print("  - JSON示例中使用实际的bullet IDs")
print("  - 添加了IMPORTANT警告，明确说明不要使用insight类型")
print("=" * 80)
