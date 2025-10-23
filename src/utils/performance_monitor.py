"""
Performance Monitor (A3) - Track timing and resource usage.

Provides:
- Operation timing via context manager
- Token usage tracking
- Performance report generation
- Bottleneck identification
"""

import time
import json
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from collections import defaultdict
from pathlib import Path

from .logs_manager import LogsManager, get_logs_manager


class PerformanceMonitor:
    """
    Monitor and track performance metrics for ACE framework.

    Features:
    - Automatic timing via context manager
    - Hierarchical timing (component -> operation)
    - Token usage tracking
    - JSON export for analysis
    """

    def __init__(
        self,
        run_id: Optional[str] = None,
        logs_manager: Optional[LogsManager] = None
    ):
        """
        Args:
            run_id: Run ID to associate with (uses current from logs_manager if None)
            logs_manager: LogsManager instance (uses default if None)
        """
        self.logs_manager = logs_manager or get_logs_manager()
        self.run_id = run_id or self.logs_manager.current_run_id

        # Timing data: component -> operation -> [durations]
        self.timings: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

        # Token data: component -> call -> {input, output, total}
        self.tokens: Dict[str, List[Dict[str, int]]] = defaultdict(list)

        # Overall metrics
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    # ========================================================================
    # Timing Context Manager
    # ========================================================================

    @contextmanager
    def measure(self, operation: str, component: Optional[str] = None):
        """
        Context manager to measure operation duration.

        Usage:
            with perf.measure("bullet_retrieval", "generator"):
                # code to measure
                pass

        Args:
            operation: Operation name
            component: Optional component name (for grouping)
        """
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            if component:
                self.timings[component][operation].append(elapsed)
            else:
                # Use "global" as component
                self.timings["global"][operation].append(elapsed)

    def record_duration(
        self,
        operation: str,
        duration: float,
        component: Optional[str] = None
    ):
        """
        Manually record a duration.

        Args:
            operation: Operation name
            duration: Duration in seconds
            component: Optional component name
        """
        if component:
            self.timings[component][operation].append(duration)
        else:
            self.timings["global"][operation].append(duration)

    # ========================================================================
    # Token Tracking
    # ========================================================================

    def record_tokens(
        self,
        component: str,
        input_tokens: int,
        output_tokens: int,
        call_id: Optional[str] = None
    ):
        """
        Record token usage for an LLM call.

        Args:
            component: Component name (generator/reflector/curator)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            call_id: Optional call identifier
        """
        self.tokens[component].append({
            "call_id": call_id,
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens
        })

    def get_total_tokens(self) -> Dict[str, int]:
        """
        Get total token usage across all components.

        Returns:
            Dict with total input/output/total tokens
        """
        total_input = 0
        total_output = 0

        for component_tokens in self.tokens.values():
            for call in component_tokens:
                total_input += call["input"]
                total_output += call["output"]

        return {
            "total_input": total_input,
            "total_output": total_output,
            "total": total_input + total_output
        }

    # ========================================================================
    # Run-level Tracking
    # ========================================================================

    def start_run(self):
        """Mark the start of a run."""
        self.start_time = time.time()

    def end_run(self):
        """Mark the end of a run."""
        self.end_time = time.time()

    def get_total_duration(self) -> Optional[float]:
        """Get total run duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    # ========================================================================
    # Report Generation
    # ========================================================================

    def get_timing_summary(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Get timing summary for a component or all components.

        Args:
            component: Optional component to filter by

        Returns:
            Dict with timing statistics
        """
        if component:
            components_to_process = {component: self.timings[component]}
        else:
            components_to_process = dict(self.timings)

        summary = {}

        for comp, operations in components_to_process.items():
            comp_summary = {}
            comp_total = 0

            for operation, durations in operations.items():
                if durations:
                    total = sum(durations)
                    comp_total += total

                    comp_summary[operation] = {
                        "count": len(durations),
                        "total": total,
                        "avg": total / len(durations),
                        "min": min(durations),
                        "max": max(durations)
                    }

            if comp_summary:
                comp_summary["_total"] = comp_total
                summary[comp] = comp_summary

        return summary

    def get_token_summary(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Get token usage summary.

        Args:
            component: Optional component to filter by

        Returns:
            Dict with token statistics
        """
        if component:
            components_to_process = {component: self.tokens[component]}
        else:
            components_to_process = dict(self.tokens)

        summary = {}

        for comp, calls in components_to_process.items():
            if calls:
                total_input = sum(call["input"] for call in calls)
                total_output = sum(call["output"] for call in calls)
                total = total_input + total_output

                summary[comp] = {
                    "num_calls": len(calls),
                    "total_input": total_input,
                    "total_output": total_output,
                    "total": total,
                    "avg_input": total_input / len(calls),
                    "avg_output": total_output / len(calls),
                    "avg_total": total / len(calls)
                }

        return summary

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Complete performance report as dictionary
        """
        report = {
            "run_id": self.run_id,
            "timestamp": time.time(),
            "total_duration": self.get_total_duration(),
            "breakdown": {},
            "llm_stats": {}
        }

        # Timing breakdown by component
        timing_summary = self.get_timing_summary()

        for component, operations in timing_summary.items():
            comp_total = operations.pop("_total", 0)

            report["breakdown"][component] = {
                "total": comp_total,
                **operations
            }

        # Token statistics
        token_summary = self.get_token_summary()

        if token_summary:
            # Per-component breakdown
            report["llm_stats"]["calls_breakdown"] = {
                comp: stats["num_calls"]
                for comp, stats in token_summary.items()
            }

            # Overall token stats
            total_tokens = self.get_total_tokens()
            report["llm_stats"]["tokens"] = total_tokens

            # Total calls
            total_calls = sum(stats["num_calls"] for stats in token_summary.values())
            report["llm_stats"]["total_calls"] = total_calls

            # Average call duration (if available)
            llm_call_durations = []
            for component in ["generator", "reflector", "curator"]:
                if component in self.timings and "llm_call" in self.timings[component]:
                    llm_call_durations.extend(self.timings[component]["llm_call"])

            if llm_call_durations:
                report["llm_stats"]["avg_call_duration"] = sum(llm_call_durations) / len(llm_call_durations)

        return report

    def save_report(self, run_id: Optional[str] = None):
        """
        Save performance report to file.

        Args:
            run_id: Run ID to save for (uses current if None)
        """
        if run_id is None:
            run_id = self.run_id

        if run_id is None:
            raise ValueError("No run_id provided and no current run")

        # Generate report
        report = self.generate_report()

        # Get path from logs_manager
        report_path = self.logs_manager.get_performance_log_path(run_id)

        # Save to file
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

    # ========================================================================
    # Analysis Helpers
    # ========================================================================

    def get_bottlenecks(self, top_n: int = 5) -> List[tuple]:
        """
        Identify the top N slowest operations.

        Args:
            top_n: Number of top bottlenecks to return

        Returns:
            List of (component, operation, total_time) tuples
        """
        all_operations = []

        for component, operations in self.timings.items():
            for operation, durations in operations.items():
                total_time = sum(durations)
                all_operations.append((component, operation, total_time))

        # Sort by total time descending
        all_operations.sort(key=lambda x: x[2], reverse=True)

        return all_operations[:top_n]

    def print_summary(self):
        """Print a human-readable performance summary."""
        report = self.generate_report()

        print("=" * 60)
        print("Performance Report")
        print("=" * 60)

        if report["total_duration"]:
            print(f"Total Duration: {report['total_duration']:.2f}s")
        print()

        # Timing breakdown
        if report["breakdown"]:
            print("Timing Breakdown:")
            for component, metrics in report["breakdown"].items():
                total = metrics.get("total", 0)
                print(f"\n  {component.upper()}: {total:.2f}s")

                for operation, stats in metrics.items():
                    if operation != "total" and isinstance(stats, dict):
                        avg = stats.get("avg", 0)
                        count = stats.get("count", 0)
                        print(f"    - {operation}: {avg:.2f}s (×{count})")

        # Token stats
        if report["llm_stats"]:
            print("\n" + "=" * 60)
            print("LLM Statistics:")

            tokens = report["llm_stats"].get("tokens", {})
            total_calls = report["llm_stats"].get("total_calls", 0)

            print(f"  Total Calls: {total_calls}")
            print(f"  Total Tokens: {tokens.get('total', 0):,}")
            print(f"    - Input: {tokens.get('total_input', 0):,}")
            print(f"    - Output: {tokens.get('total_output', 0):,}")

            if "avg_call_duration" in report["llm_stats"]:
                avg_dur = report["llm_stats"]["avg_call_duration"]
                print(f"  Avg Call Duration: {avg_dur:.2f}s")

        # Bottlenecks
        print("\n" + "=" * 60)
        print("Top Bottlenecks:")
        bottlenecks = self.get_bottlenecks(top_n=5)
        for i, (component, operation, total_time) in enumerate(bottlenecks, 1):
            print(f"  {i}. {component}/{operation}: {total_time:.2f}s")

        print("=" * 60)


# Factory function
def create_performance_monitor(
    run_id: Optional[str] = None,
    logs_manager: Optional[LogsManager] = None
) -> PerformanceMonitor:
    """Create a PerformanceMonitor instance."""
    return PerformanceMonitor(run_id, logs_manager)
