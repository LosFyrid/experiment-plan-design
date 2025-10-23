#!/usr/bin/env python3
"""
深度观测ACE学习内容 - 展示playbook变更和学到的知识

用法：
    python view_ace_learning.py --run-id 203038_ID1FWJ
    python view_ace_learning.py --run-id 203038_ID1FWJ --show-prompts  # 查看LLM prompt
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent


def load_run_logs(run_id: str) -> Dict[str, Any]:
    """加载运行日志"""
    root = get_project_root()

    # 查找run目录
    logs_dir = root / "logs" / "runs"
    run_dirs = list(logs_dir.glob(f"*/run_{run_id}"))

    if not run_dirs:
        print(f"❌ 未找到run_id: {run_id}")
        return {}

    run_dir = run_dirs[0]

    # 加载各组件日志
    logs = {}
    for component in ["generator", "reflector", "curator"]:
        log_file = run_dir / f"{component}.jsonl"
        if log_file.exists():
            events = []
            with open(log_file) as f:
                for line in f:
                    events.append(json.loads(line))
            logs[component] = events

    return logs


def load_llm_calls(run_id: str) -> List[Dict[str, Any]]:
    """加载LLM调用记录"""
    root = get_project_root()
    llm_dir = root / "logs" / "llm_calls"

    calls = []
    for date_dir in llm_dir.iterdir():
        if not date_dir.is_dir():
            continue

        for call_file in date_dir.glob("*.json"):
            # 解析文件名: {timestamp}_{run_id}_{component}.json
            parts = call_file.stem.split('_')
            if len(parts) >= 4:
                file_run_id = f"{parts[1]}_{parts[2]}"
                if file_run_id == run_id:
                    with open(call_file) as f:
                        calls.append(json.load(f))

    return calls


def show_reflector_insights(logs: Dict[str, Any]):
    """展示Reflector发现的insights"""
    print("\n" + "=" * 80)
    print("🔍 REFLECTOR发现的问题和改进建议")
    print("=" * 80)

    # 从reflector日志中找insights_extracted事件
    reflector_logs = logs.get("reflector", [])
    insights_event = None
    for event in reflector_logs:
        if event.get("event_type") == "insights_extracted":
            insights_event = event
            break

    if not insights_event:
        print("未找到insights")
        return

    # 加载reflector的LLM调用查看详细insights
    print("\n从Reflector的迭代过程中提取到的insights：")
    print("（这些是LLM分析实验方案后发现的具体问题）\n")


def show_curator_updates(logs: Dict[str, Any], show_content: bool = False):
    """展示Curator对playbook的更新"""
    print("\n" + "=" * 80)
    print("📝 CURATOR对PLAYBOOK的更新")
    print("=" * 80)

    curator_logs = logs.get("curator", [])

    # 找出所有operation_applied事件
    operations = [e for e in curator_logs if e.get("event_type") == "operation_applied"]

    if not operations:
        print("未找到playbook更新操作")
        return

    print(f"\n本次运行共更新了 {len(operations)} 个playbook条目：\n")

    for i, op in enumerate(operations, 1):
        data = op.get("data", {})
        op_type = data.get("operation")
        bullet_id = data.get("bullet_id")
        section = data.get("section")
        reason = data.get("reason", "无")

        print(f"[{i}] {op_type} - {bullet_id}")
        print(f"    Section: {section}")
        print(f"    原因: {reason}")

        if show_content:
            if op_type == "ADD" and "content" in data:
                print(f"    内容: {data['content']}")
            elif op_type == "UPDATE":
                if "old_content" in data and "new_content" in data:
                    print(f"    旧内容: {data.get('old_content', 'N/A')}")
                    print(f"    新内容: {data.get('new_content', 'N/A')}")
        print()


def show_playbook_comparison(run_id: str):
    """对比playbook更新前后"""
    print("\n" + "=" * 80)
    print("📊 PLAYBOOK更新前后对比")
    print("=" * 80)

    root = get_project_root()
    versions_dir = root / "logs" / "playbook_versions"

    # 查找此次运行相关的版本
    # 文件格式: meta_{timestamp}_{version}.json
    versions = []
    for meta_file in versions_dir.glob("meta_*.json"):
        with open(meta_file) as f:
            meta = json.load(f)
            if meta.get("run_id") == run_id:
                # 找到对应的playbook文件
                playbook_file = meta_file.parent / meta_file.name.replace("meta_", "playbook_")
                versions.append((meta_file, playbook_file, meta))

    if len(versions) < 2:
        print(f"未找到足够的版本进行对比（找到{len(versions)}个版本，需要至少2个）")
        return

    # 按时间排序
    versions.sort(key=lambda x: x[2].get("timestamp", ""))

    before_meta_file, before_playbook_file, before_meta = versions[0]
    after_meta_file, after_playbook_file, after_meta = versions[-1]

    print(f"\n更新前版本: {before_meta.get('version_id', 'unknown')}")
    print(f"  - Bullets数量: {before_meta.get('bullets_count', 0)}")
    print(f"  - 触发原因: {before_meta.get('trigger', 'unknown')}")
    print(f"  - 时间: {before_meta.get('timestamp', 'unknown')}")

    print(f"\n更新后版本: {after_meta.get('version_id', 'unknown')}")
    print(f"  - Bullets数量: {after_meta.get('bullets_count', 0)}")
    print(f"  - 触发原因: {after_meta.get('trigger', 'unknown')}")
    print(f"  - 时间: {after_meta.get('timestamp', 'unknown')}")

    changes = after_meta.get("changes", {})
    print(f"\n变更统计:")
    print(f"  ✅ 新增: {changes.get('added', 0)} bullets")
    print(f"  🔄 更新: {changes.get('updated', 0)} bullets")
    print(f"  ❌ 删除: {changes.get('removed', 0)} bullets")


def show_llm_prompts(llm_calls: List[Dict[str, Any]], component: str = None):
    """展示LLM prompts"""
    print("\n" + "=" * 80)
    print("💬 LLM PROMPTS AND RESPONSES")
    print("=" * 80)

    filtered_calls = llm_calls
    if component:
        filtered_calls = [c for c in llm_calls if component in c.get("call_id", "").lower()]

    for call in filtered_calls:
        call_id = call.get("call_id", "unknown")
        component_name = call_id.split('_')[-1] if '_' in call_id else "unknown"

        print(f"\n[{call_id}]")
        print(f"Component: {component_name}")
        print(f"Model: {call.get('model', 'unknown')}")
        print(f"Duration: {call.get('duration_seconds', 0):.2f}s")
        print(f"Tokens: {call.get('total_tokens', 0)}")

        print("\n--- PROMPT ---")
        prompt = call.get("request", {}).get("prompt", "")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)

        print("\n--- RESPONSE ---")
        response = call.get("response", {}).get("content", "")
        print(response[:500] + "..." if len(response) > 500 else response)
        print("\n" + "-" * 80)


def main():
    parser = argparse.ArgumentParser(description="深度观测ACE学习内容")
    parser.add_argument("--run-id", required=True, help="Run ID")
    parser.add_argument("--show-content", action="store_true", help="显示bullet完整内容")
    parser.add_argument("--show-prompts", action="store_true", help="显示LLM prompts")
    parser.add_argument("--component", help="只看特定组件的prompts (generator/reflector/curator)")

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"ACE学习内容观测 - Run ID: {args.run_id}")
    print(f"{'='*80}")

    # 加载数据
    logs = load_run_logs(args.run_id)
    llm_calls = load_llm_calls(args.run_id)

    if not logs:
        return

    # 展示各部分
    show_reflector_insights(logs)
    show_curator_updates(logs, args.show_content)
    show_playbook_comparison(args.run_id)

    if args.show_prompts:
        show_llm_prompts(llm_calls, args.component)

    print("\n" + "=" * 80)
    print("✅ 观测完成")
    print("=" * 80)
    print("\n提示: 使用 --show-content 查看完整bullet内容")
    print("提示: 使用 --show-prompts 查看LLM对话详情")
    print("提示: 使用 --component curator 只看Curator的LLM调用\n")


if __name__ == "__main__":
    main()
