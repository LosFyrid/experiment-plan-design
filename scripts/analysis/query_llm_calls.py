#!/usr/bin/env python3
"""
Query and analyze LLM calls in ACE framework.

Usage:
    python query_llm_calls.py --date 20251022
    python query_llm_calls.py --component generator
    python query_llm_calls.py --run-id 143052_abc123
    python query_llm_calls.py --export-prompt <call_id> --output prompt.txt
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "logs"


def list_llm_calls(
    date: Optional[str] = None,
    component: Optional[str] = None,
    run_id: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List LLM calls with optional filters.

    Args:
        date: Date filter (YYYYMMDD format)
        component: Component filter (generator/reflector/curator)
        run_id: Run ID filter
        status: Status filter (success/error/in_progress)

    Returns:
        List of LLM call data dictionaries
    """
    logs_dir = get_logs_dir()
    llm_calls_dir = logs_dir / "llm_calls"

    if not llm_calls_dir.exists():
        print(f"No LLM calls directory found at {llm_calls_dir}")
        return []

    calls = []

    # Determine search paths
    if date:
        date_dirs = [llm_calls_dir / date]
    else:
        date_dirs = sorted(llm_calls_dir.iterdir(), reverse=True)

    # Search for call files
    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue

        # Search for JSON files directly in date directory
        for call_file in date_dir.glob("*.json"):
            # Parse filename: {timestamp}_{run_id}_{component}.json
            # run_id format: HHMMSS_randomchars
            # So filename is: {timestamp}_{HHMMSS}_{randomchars}_{component}.json
            filename = call_file.stem
            parts = filename.split('_')

            if len(parts) < 4:
                continue

            # Reconstruct run_id from parts[1] and parts[2]
            file_run_id = f"{parts[1]}_{parts[2]}"
            file_component = '_'.join(parts[3:])  # Handle component names with underscores

            # Apply filters
            if run_id and file_run_id != run_id:
                continue
            if component and not file_component.startswith(component):
                continue

            with open(call_file) as f:
                call_data = json.load(f)

            if status and call_data.get("status") != status:
                continue

            calls.append(call_data)

    return calls


def get_call_details(call_id: str) -> Optional[Dict[str, Any]]:
    """
    Get details for a specific LLM call.

    Args:
        call_id: LLM call ID

    Returns:
        Call data or None if not found
    """
    logs_dir = get_logs_dir()
    llm_calls_dir = logs_dir / "llm_calls"

    # Search for call file
    for call_file in llm_calls_dir.glob(f"**/{call_id}.json"):
        with open(call_file) as f:
            return json.load(f)

    return None


def print_calls_summary(calls: List[Dict[str, Any]]):
    """Print a summary table of LLM calls."""
    if not calls:
        print("No LLM calls found.")
        return

    print(f"\n{'Call ID':<25} {'Component':<12} {'Model':<15} {'Status':<10} {'Tokens':<10} {'Duration':<10}")
    print("=" * 90)

    for call in calls:
        call_id = call["llm_call_id"][:24]
        component = call.get("component", "unknown")
        model = call.get("model", {}).get("name", "unknown")[:14]
        status = call.get("status", "unknown")

        tokens = call.get("tokens")
        if tokens:
            token_str = f"{tokens.get('total', 0):,}"
        else:
            token_str = "N/A"

        timing = call.get("timing", {})
        duration = timing.get("duration")
        if duration is not None:
            duration_str = f"{duration:.2f}s"
        else:
            duration_str = "N/A"

        print(f"{call_id:<25} {component:<12} {model:<15} {status:<10} {token_str:<10} {duration_str:<10}")

    print(f"\nTotal calls: {len(calls)}")


def export_prompt(call_id: str, output_path: str):
    """
    Export prompts from an LLM call to a text file.

    Args:
        call_id: LLM call ID
        output_path: Output file path
    """
    call_data = get_call_details(call_id)

    if not call_data:
        print(f"Call {call_id} not found.")
        return

    request = call_data.get("request", {})
    system_prompt = request.get("system_prompt", "")
    user_prompt = request.get("user_prompt", "")

    with open(output_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("SYSTEM PROMPT\n")
        f.write("=" * 80 + "\n\n")
        f.write(system_prompt)
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("USER PROMPT\n")
        f.write("=" * 80 + "\n\n")
        f.write(user_prompt)
        f.write("\n")

    print(f"Prompts exported to {output_path}")


def analyze_token_usage(calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze token usage across LLM calls.

    Args:
        calls: List of LLM call data

    Returns:
        Token usage statistics
    """
    stats = {
        "total_calls": len(calls),
        "successful_calls": 0,
        "total_tokens": 0,
        "total_input": 0,
        "total_output": 0,
        "by_component": {},
        "by_model": {}
    }

    for call in calls:
        if call.get("status") == "success":
            stats["successful_calls"] += 1

        tokens = call.get("tokens")
        if not tokens:
            continue

        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)
        total = tokens.get("total", input_tokens + output_tokens)

        stats["total_tokens"] += total
        stats["total_input"] += input_tokens
        stats["total_output"] += output_tokens

        # By component
        component = call.get("component", "unknown")
        if component not in stats["by_component"]:
            stats["by_component"][component] = {
                "calls": 0,
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0
            }

        stats["by_component"][component]["calls"] += 1
        stats["by_component"][component]["total_tokens"] += total
        stats["by_component"][component]["input_tokens"] += input_tokens
        stats["by_component"][component]["output_tokens"] += output_tokens

        # By model
        model = call.get("model", {}).get("name", "unknown")
        if model not in stats["by_model"]:
            stats["by_model"][model] = {
                "calls": 0,
                "total_tokens": 0
            }

        stats["by_model"][model]["calls"] += 1
        stats["by_model"][model]["total_tokens"] += total

    return stats


def main():
    parser = argparse.ArgumentParser(description="Query LLM calls in ACE framework")
    parser.add_argument("--date", help="Filter by date (YYYYMMDD format)")
    parser.add_argument("--component", choices=["generator", "reflector", "curator"],
                       help="Filter by component")
    parser.add_argument("--run-id", help="Filter by run ID")
    parser.add_argument("--status", choices=["success", "error", "in_progress"],
                       help="Filter by status")
    parser.add_argument("--call-id", help="Get details for specific call ID")
    parser.add_argument("--export-prompt", metavar="CALL_ID",
                       help="Export prompts from specific call")
    parser.add_argument("--output", help="Output file for --export-prompt")
    parser.add_argument("--analyze-tokens", action="store_true",
                       help="Analyze token usage")
    parser.add_argument("--details", action="store_true",
                       help="Show detailed information")

    args = parser.parse_args()

    if args.export_prompt:
        output = args.output or f"{args.export_prompt}_prompt.txt"
        export_prompt(args.export_prompt, output)
    elif args.call_id:
        call_details = get_call_details(args.call_id)
        if call_details:
            print(json.dumps(call_details, indent=2))
        else:
            print(f"Call {args.call_id} not found.")
    else:
        calls = list_llm_calls(
            date=args.date,
            component=args.component,
            run_id=args.run_id,
            status=args.status
        )

        if args.analyze_tokens:
            stats = analyze_token_usage(calls)
            print(json.dumps(stats, indent=2))
        elif args.details:
            print(json.dumps(calls, indent=2))
        else:
            print_calls_summary(calls)


if __name__ == "__main__":
    main()
