#!/usr/bin/env python3
"""
Analyze performance metrics from ACE framework runs.

Usage:
    python analyze_performance.py --run-id 143052_abc123
    python analyze_performance.py --date 20251022 --compare
    python analyze_performance.py --bottlenecks --top 10
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "logs"


def load_performance_report(run_id: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load performance report for a specific run.

    Args:
        run_id: Run ID
        date: Optional date filter

    Returns:
        Performance report data or None
    """
    logs_dir = get_logs_dir()
    runs_dir = logs_dir / "runs"

    # Search for run
    if date:
        perf_file = runs_dir / date / f"run_{run_id}" / "performance.json"
        if perf_file.exists():
            with open(perf_file) as f:
                return json.load(f)
    else:
        # Search all dates
        for date_dir in runs_dir.iterdir():
            if date_dir.is_dir():
                perf_file = date_dir / f"run_{run_id}" / "performance.json"
                if perf_file.exists():
                    with open(perf_file) as f:
                        return json.load(f)

    return None


def load_all_performance_reports(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load all performance reports, optionally filtered by date.

    Args:
        date: Optional date filter

    Returns:
        List of performance reports
    """
    logs_dir = get_logs_dir()
    runs_dir = logs_dir / "runs"

    reports = []

    if date:
        date_dirs = [runs_dir / date]
    else:
        date_dirs = sorted(runs_dir.iterdir(), reverse=True)

    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue

        for run_dir in date_dir.iterdir():
            if not run_dir.is_dir() or not run_dir.name.startswith("run_"):
                continue

            perf_file = run_dir / "performance.json"
            if perf_file.exists():
                with open(perf_file) as f:
                    report = json.load(f)
                    report["_run_id"] = run_dir.name.replace("run_", "")
                    report["_date"] = date_dir.name
                    reports.append(report)

    return reports


def print_performance_summary(report: Dict[str, Any]):
    """Print a summary of a performance report."""
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    run_id = report.get("_run_id", report.get("run_id", "unknown"))
    print(f"\nRun ID: {run_id}")

    total_duration = report.get("total_duration")
    if total_duration:
        print(f"Total Duration: {total_duration:.2f}s")

    # Timing breakdown
    breakdown = report.get("breakdown", {})
    if breakdown:
        print("\n" + "-" * 80)
        print("TIMING BREAKDOWN")
        print("-" * 80)

        for component, metrics in breakdown.items():
            total = metrics.get("total", 0)
            print(f"\n{component.upper()}: {total:.2f}s")

            for operation, stats in metrics.items():
                if operation == "total" or not isinstance(stats, dict):
                    continue

                avg = stats.get("avg", 0)
                count = stats.get("count", 0)
                min_time = stats.get("min", 0)
                max_time = stats.get("max", 0)

                print(f"  - {operation}:")
                print(f"      Count: {count}")
                print(f"      Avg: {avg:.2f}s")
                print(f"      Min: {min_time:.2f}s")
                print(f"      Max: {max_time:.2f}s")

    # LLM statistics
    llm_stats = report.get("llm_stats", {})
    if llm_stats:
        print("\n" + "-" * 80)
        print("LLM STATISTICS")
        print("-" * 80)

        total_calls = llm_stats.get("total_calls", 0)
        print(f"\nTotal Calls: {total_calls}")

        tokens = llm_stats.get("tokens", {})
        if tokens:
            print(f"Total Tokens: {tokens.get('total', 0):,}")
            print(f"  - Input: {tokens.get('total_input', 0):,}")
            print(f"  - Output: {tokens.get('total_output', 0):,}")

        avg_duration = llm_stats.get("avg_call_duration")
        if avg_duration:
            print(f"Avg Call Duration: {avg_duration:.2f}s")

        # Breakdown by component
        calls_breakdown = llm_stats.get("calls_breakdown", {})
        if calls_breakdown:
            print("\nCalls by Component:")
            for comp, count in calls_breakdown.items():
                print(f"  - {comp}: {count}")

    print("\n" + "=" * 80)


def compare_performance(reports: List[Dict[str, Any]]):
    """Compare performance across multiple runs."""
    if not reports:
        print("No reports to compare.")
        return

    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)

    # Extract key metrics
    metrics = []
    for report in reports:
        run_id = report.get("_run_id", "unknown")[:15]
        total_duration = report.get("total_duration", 0)
        llm_stats = report.get("llm_stats", {})
        total_calls = llm_stats.get("total_calls", 0)
        total_tokens = llm_stats.get("tokens", {}).get("total", 0)

        metrics.append({
            "run_id": run_id,
            "duration": total_duration,
            "calls": total_calls,
            "tokens": total_tokens
        })

    # Print comparison table
    print(f"\n{'Run ID':<17} {'Duration':<12} {'LLM Calls':<12} {'Total Tokens':<15}")
    print("-" * 60)

    for m in metrics:
        duration_str = f"{m['duration']:.2f}s" if m['duration'] else "N/A"
        print(f"{m['run_id']:<17} {duration_str:<12} {m['calls']:<12} {m['tokens']:,}")

    # Calculate averages
    if metrics:
        avg_duration = sum(m["duration"] for m in metrics if m["duration"]) / len(metrics)
        avg_calls = sum(m["calls"] for m in metrics) / len(metrics)
        avg_tokens = sum(m["tokens"] for m in metrics) / len(metrics)

        print("-" * 60)
        print(f"{'AVERAGE':<17} {avg_duration:.2f}s{' '*6} {avg_calls:.1f}{' '*7} {avg_tokens:,.0f}")

    print("=" * 80)


def identify_bottlenecks(reports: List[Dict[str, Any]], top_n: int = 5):
    """
    Identify performance bottlenecks across runs.

    Args:
        reports: List of performance reports
        top_n: Number of top bottlenecks to show
    """
    # Aggregate timing data across all runs
    aggregated = defaultdict(lambda: {"total_time": 0, "count": 0, "max_time": 0})

    for report in reports:
        breakdown = report.get("breakdown", {})

        for component, metrics in breakdown.items():
            for operation, stats in metrics.items():
                if operation == "total" or not isinstance(stats, dict):
                    continue

                key = f"{component}/{operation}"
                total = stats.get("total", 0)
                max_time = stats.get("max", 0)

                aggregated[key]["total_time"] += total
                aggregated[key]["count"] += stats.get("count", 0)
                aggregated[key]["max_time"] = max(aggregated[key]["max_time"], max_time)

    # Sort by total time
    bottlenecks = sorted(
        aggregated.items(),
        key=lambda x: x[1]["total_time"],
        reverse=True
    )[:top_n]

    print("\n" + "=" * 80)
    print(f"TOP {top_n} BOTTLENECKS (across {len(reports)} runs)")
    print("=" * 80)

    print(f"\n{'Operation':<40} {'Total Time':<15} {'Calls':<10} {'Max Time':<10}")
    print("-" * 80)

    for operation, stats in bottlenecks:
        total_time = stats["total_time"]
        count = stats["count"]
        max_time = stats["max_time"]

        print(f"{operation:<40} {total_time:.2f}s{' '*9} {count:<10} {max_time:.2f}s")

    print("=" * 80)


def analyze_llm_efficiency(reports: List[Dict[str, Any]]):
    """Analyze LLM call efficiency across runs."""
    print("\n" + "=" * 80)
    print("LLM EFFICIENCY ANALYSIS")
    print("=" * 80)

    total_calls = 0
    total_tokens = 0
    total_duration = 0
    component_stats = defaultdict(lambda: {"calls": 0, "tokens": 0})

    for report in reports:
        llm_stats = report.get("llm_stats", {})

        total_calls += llm_stats.get("total_calls", 0)
        tokens = llm_stats.get("tokens", {})
        total_tokens += tokens.get("total", 0)

        # Extract LLM call durations
        breakdown = report.get("breakdown", {})
        for component, metrics in breakdown.items():
            llm_call = metrics.get("llm_call", {})
            if isinstance(llm_call, dict):
                total_duration += llm_call.get("total", 0)

        # Component breakdown
        calls_breakdown = llm_stats.get("calls_breakdown", {})
        for comp, count in calls_breakdown.items():
            component_stats[comp]["calls"] += count

    if total_calls == 0:
        print("\nNo LLM calls found in reports.")
        return

    print(f"\nTotal LLM Calls: {total_calls}")
    print(f"Total Tokens: {total_tokens:,}")
    print(f"Average Tokens per Call: {total_tokens / total_calls:,.0f}")

    if total_duration > 0:
        print(f"Total LLM Time: {total_duration:.2f}s")
        print(f"Average Call Duration: {total_duration / total_calls:.2f}s")
        print(f"Tokens per Second: {total_tokens / total_duration:,.0f}")

    print("\nBy Component:")
    for comp, stats in sorted(component_stats.items()):
        calls = stats["calls"]
        pct = (calls / total_calls * 100) if total_calls > 0 else 0
        print(f"  - {comp}: {calls} calls ({pct:.1f}%)")

    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Analyze ACE framework performance")
    parser.add_argument("--run-id", help="Analyze specific run")
    parser.add_argument("--date", help="Filter by date (YYYYMMDD format)")
    parser.add_argument("--compare", action="store_true",
                       help="Compare multiple runs")
    parser.add_argument("--bottlenecks", action="store_true",
                       help="Identify performance bottlenecks")
    parser.add_argument("--top", type=int, default=5,
                       help="Number of top bottlenecks to show (default: 5)")
    parser.add_argument("--llm-efficiency", action="store_true",
                       help="Analyze LLM call efficiency")

    args = parser.parse_args()

    if args.run_id:
        # Analyze specific run
        report = load_performance_report(args.run_id, date=args.date)
        if report:
            print_performance_summary(report)
        else:
            print(f"Performance report not found for run {args.run_id}")
    else:
        # Analyze multiple runs
        reports = load_all_performance_reports(date=args.date)

        if not reports:
            print("No performance reports found.")
            return

        if args.compare:
            compare_performance(reports)
        elif args.bottlenecks:
            identify_bottlenecks(reports, top_n=args.top)
        elif args.llm_efficiency:
            analyze_llm_efficiency(reports)
        else:
            # Default: show summary of latest run
            if reports:
                print_performance_summary(reports[0])


if __name__ == "__main__":
    main()
