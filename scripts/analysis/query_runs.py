#!/usr/bin/env python3
"""
Query and filter ACE framework runs.

Usage:
    python query_runs.py --date 20251022
    python query_runs.py --run-id 143052_abc123
    python query_runs.py --component generator --latest 5
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "logs"


def list_all_runs(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all runs, optionally filtered by date.

    Args:
        date: Date string in YYYYMMDD format (e.g., "20251022")

    Returns:
        List of run metadata dictionaries
    """
    logs_dir = get_logs_dir()
    runs_dir = logs_dir / "runs"

    if not runs_dir.exists():
        print(f"No runs directory found at {runs_dir}")
        return []

    runs = []

    if date:
        # Search in specific date directory
        date_dir = runs_dir / date
        if date_dir.exists():
            for run_dir in sorted(date_dir.iterdir()):
                if run_dir.is_dir() and run_dir.name.startswith("run_"):
                    runs.append(_load_run_metadata(run_dir))
    else:
        # Search all dates
        for date_dir in sorted(runs_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                for run_dir in sorted(date_dir.iterdir(), reverse=True):
                    if run_dir.is_dir() and run_dir.name.startswith("run_"):
                        runs.append(_load_run_metadata(run_dir))

    return runs


def _load_run_metadata(run_dir: Path) -> Dict[str, Any]:
    """Load metadata for a run directory."""
    run_id = run_dir.name.replace("run_", "")
    date = run_dir.parent.name

    metadata = {
        "run_id": run_id,
        "date": date,
        "path": str(run_dir),
        "components": [],
        "log_files": []
    }

    # Check which components have logs
    for component in ["generator", "reflector", "curator"]:
        component_log = run_dir / f"{component}.jsonl"
        if component_log.exists():
            metadata["components"].append(component)
            metadata["log_files"].append(str(component_log))

    # Check for performance log
    perf_log = run_dir / "performance.json"
    if perf_log.exists():
        metadata["has_performance"] = True
        with open(perf_log) as f:
            perf_data = json.load(f)
            metadata["total_duration"] = perf_data.get("total_duration")
            metadata["llm_stats"] = perf_data.get("llm_stats", {})
    else:
        metadata["has_performance"] = False

    return metadata


def query_runs_by_component(component: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Query runs that have logs for a specific component.

    Args:
        component: Component name (generator/reflector/curator)
        date: Optional date filter

    Returns:
        List of run metadata dictionaries
    """
    all_runs = list_all_runs(date=date)
    return [run for run in all_runs if component in run["components"]]


def get_run_details(run_id: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific run.

    Args:
        run_id: Run ID (e.g., "143052_abc123")
        date: Optional date (YYYYMMDD format)

    Returns:
        Detailed run information or None if not found
    """
    logs_dir = get_logs_dir()
    runs_dir = logs_dir / "runs"

    # Search for run
    if date:
        run_path = runs_dir / date / f"run_{run_id}"
        if run_path.exists():
            return _load_run_details(run_path)
    else:
        # Search all dates
        for date_dir in runs_dir.iterdir():
            if date_dir.is_dir():
                run_path = date_dir / f"run_{run_id}"
                if run_path.exists():
                    return _load_run_details(run_path)

    return None


def _load_run_details(run_path: Path) -> Dict[str, Any]:
    """Load detailed information about a run."""
    metadata = _load_run_metadata(run_path)

    # Load component logs
    metadata["logs"] = {}

    for component in metadata["components"]:
        log_file = run_path / f"{component}.jsonl"
        events = []

        with open(log_file) as f:
            for line in f:
                events.append(json.loads(line))

        metadata["logs"][component] = {
            "event_count": len(events),
            "events": events
        }

    return metadata


def print_run_summary(runs: List[Dict[str, Any]]):
    """Print a summary table of runs."""
    if not runs:
        print("No runs found.")
        return

    print(f"\n{'Run ID':<20} {'Date':<10} {'Components':<30} {'Duration':<10} {'LLM Calls':<10}")
    print("=" * 90)

    for run in runs:
        run_id = run["run_id"]
        date = run["date"]
        components = ", ".join(run["components"])
        duration = f"{run.get('total_duration', 0):.2f}s" if run.get("total_duration") else "N/A"
        llm_calls = run.get("llm_stats", {}).get("total_calls", "N/A")

        print(f"{run_id:<20} {date:<10} {components:<30} {duration:<10} {llm_calls:<10}")

    print(f"\nTotal runs: {len(runs)}")


def main():
    parser = argparse.ArgumentParser(description="Query ACE framework runs")
    parser.add_argument("--date", help="Filter by date (YYYYMMDD format)")
    parser.add_argument("--run-id", help="Get details for specific run ID")
    parser.add_argument("--component", choices=["generator", "reflector", "curator"],
                       help="Filter by component")
    parser.add_argument("--latest", type=int, help="Show only N latest runs")
    parser.add_argument("--details", action="store_true", help="Show detailed information")

    args = parser.parse_args()

    if args.run_id:
        # Query specific run
        run_details = get_run_details(args.run_id, date=args.date)
        if run_details:
            print(json.dumps(run_details, indent=2))
        else:
            print(f"Run {args.run_id} not found.")
    else:
        # Query multiple runs
        if args.component:
            runs = query_runs_by_component(args.component, date=args.date)
        else:
            runs = list_all_runs(date=args.date)

        # Apply latest filter
        if args.latest and runs:
            runs = runs[:args.latest]

        # Print results
        if args.details:
            print(json.dumps(runs, indent=2))
        else:
            print_run_summary(runs)


if __name__ == "__main__":
    main()
