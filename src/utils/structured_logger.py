"""
Structured Logger (A1) - Unified structured logging for ACE framework.

Provides:
- JSONL-based event logging
- Component-specific logging (Generator, Reflector, Curator)
- Automatic timestamp and run_id tracking
- Support for both per-run and global logs
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Literal
from pathlib import Path

from .logs_manager import LogsManager, get_logs_manager


LogLevel = Literal["debug", "info", "warning", "error"]
Component = Literal["generator", "reflector", "curator"]


class StructuredLogger:
    """
    Structured logger for ACE framework components.

    Logs events in JSONL format with unified structure:
    {
        "timestamp": "ISO 8601",
        "run_id": "143015_aBc123",
        "component": "generator",
        "event_type": "bullet_retrieval",
        "level": "info",
        "data": { ... }
    }
    """

    def __init__(
        self,
        component: Component,
        logs_manager: Optional[LogsManager] = None,
        enable_global_log: bool = True
    ):
        """
        Args:
            component: Component name (generator/reflector/curator)
            logs_manager: LogsManager instance (uses default if None)
            enable_global_log: Whether to also write to global component log
        """
        self.component = component
        self.logs_manager = logs_manager or get_logs_manager()
        self.enable_global_log = enable_global_log

        # Global component log path
        self.global_log_path = self.logs_manager.components_dir / f"{component}.jsonl"

    # ========================================================================
    # Main Logging Methods
    # ========================================================================

    def log(
        self,
        event_type: str,
        data: Dict[str, Any],
        level: LogLevel = "info",
        run_id: Optional[str] = None
    ):
        """
        Log an event.

        Args:
            event_type: Type of event (e.g., "bullet_retrieval")
            data: Event-specific data
            level: Log level (debug/info/warning/error)
            run_id: Optional run ID (uses current from logs_manager if None)
        """
        # Get run_id
        if run_id is None:
            run_id = self.logs_manager.current_run_id

        # Construct log entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "run_id": run_id,
            "component": self.component,
            "event_type": event_type,
            "level": level,
            "data": data
        }

        # Write to run-specific log
        if run_id:
            try:
                log_path = self.logs_manager.get_component_log_path(
                    self.component,
                    run_id
                )
                self._write_log_entry(log_path, entry)

                # Register component usage
                self.logs_manager.register_component(self.component, run_id)
            except (ValueError, FileNotFoundError) as e:
                # Run directory doesn't exist yet
                print(f"Warning: Could not write to run log: {e}")

        # Write to global component log
        if self.enable_global_log:
            self._write_log_entry(self.global_log_path, entry)

    def debug(
        self,
        event_type: str,
        data: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        """Log a debug-level event."""
        self.log(event_type, data, level="debug", run_id=run_id)

    def info(
        self,
        event_type: str,
        data: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        """Log an info-level event."""
        self.log(event_type, data, level="info", run_id=run_id)

    def warning(
        self,
        event_type: str,
        data: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        """Log a warning-level event."""
        self.log(event_type, data, level="warning", run_id=run_id)

    def error(
        self,
        event_type: str,
        data: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        """Log an error-level event."""
        self.log(event_type, data, level="error", run_id=run_id)

    # ========================================================================
    # Component-Specific Convenience Methods
    # ========================================================================

    # Generator Events
    def log_bullet_retrieval(
        self,
        query: str,
        bullets_retrieved: int,
        top_k: int,
        min_similarity: float,
        top_similarities: list,
        sections: Dict[str, int],
        run_id: Optional[str] = None
    ):
        """Log bullet retrieval event."""
        self.info("bullet_retrieval", {
            "query": query,
            "bullets_retrieved": bullets_retrieved,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "top_similarities": top_similarities,
            "sections": sections
        }, run_id=run_id)

    def log_prompt_constructed(
        self,
        prompt_length: int,
        num_bullets: int,
        num_templates: int,
        num_examples: int,
        run_id: Optional[str] = None
    ):
        """Log prompt construction event."""
        self.info("prompt_constructed", {
            "prompt_length": prompt_length,
            "num_bullets": num_bullets,
            "num_templates": num_templates,
            "num_examples": num_examples
        }, run_id=run_id)

    def log_llm_call_started(
        self,
        model: str,
        config: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        """Log LLM call start event."""
        self.info("llm_call_started", {
            "model": model,
            "config": config
        }, run_id=run_id)

    def log_llm_call_completed(
        self,
        duration: float,
        tokens: Dict[str, int],
        llm_call_id: str,
        run_id: Optional[str] = None
    ):
        """Log LLM call completion event."""
        self.info("llm_call_completed", {
            "duration": duration,
            "tokens": tokens,
            "llm_call_id": llm_call_id
        }, run_id=run_id)

    def log_output_parsed(
        self,
        success: bool,
        plan_title: Optional[str] = None,
        materials_count: Optional[int] = None,
        procedure_steps: Optional[int] = None,
        error: Optional[str] = None,
        run_id: Optional[str] = None
    ):
        """Log output parsing event."""
        data = {"success": success}
        if success:
            data.update({
                "plan_title": plan_title,
                "materials_count": materials_count,
                "procedure_steps": procedure_steps
            })
        else:
            data["error"] = error

        level = "info" if success else "error"
        self.log("output_parsed", data, level=level, run_id=run_id)

    def log_plan_generated(
        self,
        total_duration: float,
        bullets_used: list,
        run_id: Optional[str] = None
    ):
        """Log plan generation completion event."""
        self.info("plan_generated", {
            "total_duration": total_duration,
            "bullets_used": bullets_used
        }, run_id=run_id)

    # Reflector Events
    def log_reflection_started(
        self,
        plan_title: str,
        feedback_score: float,
        max_refinement_rounds: int,
        run_id: Optional[str] = None
    ):
        """Log reflection start event."""
        self.info("reflection_started", {
            "plan_title": plan_title,
            "feedback_score": feedback_score,
            "max_refinement_rounds": max_refinement_rounds
        }, run_id=run_id)

    def log_initial_reflection_done(
        self,
        duration: float,
        insights_count: int,
        priority_distribution: Dict[str, int],
        run_id: Optional[str] = None
    ):
        """Log initial reflection completion event."""
        self.info("initial_reflection_done", {
            "duration": duration,
            "insights_count": insights_count,
            "priority_distribution": priority_distribution
        }, run_id=run_id)

    def log_refinement_round_started(
        self,
        round_num: int,
        run_id: Optional[str] = None
    ):
        """Log refinement round start event."""
        self.info("refinement_round_started", {
            "round": round_num
        }, run_id=run_id)

    def log_refinement_round_completed(
        self,
        round_num: int,
        duration: float,
        insights_count: int,
        quality_improved: bool,
        run_id: Optional[str] = None
    ):
        """Log refinement round completion event."""
        self.info("refinement_round_completed", {
            "round": round_num,
            "duration": duration,
            "insights_count": insights_count,
            "quality_improved": quality_improved
        }, run_id=run_id)

    def log_bullet_tagging_done(
        self,
        tags: Dict[str, str],
        helpful: int,
        harmful: int,
        neutral: int,
        run_id: Optional[str] = None
    ):
        """Log bullet tagging completion event."""
        self.info("bullet_tagging_done", {
            "tags": tags,
            "helpful": helpful,
            "harmful": harmful,
            "neutral": neutral
        }, run_id=run_id)

    def log_insights_extracted(
        self,
        total_duration: float,
        final_insights_count: int,
        refinement_rounds_completed: int,
        run_id: Optional[str] = None
    ):
        """Log insights extraction completion event."""
        self.info("insights_extracted", {
            "total_duration": total_duration,
            "final_insights_count": final_insights_count,
            "refinement_rounds_completed": refinement_rounds_completed
        }, run_id=run_id)

    # Curator Events
    def log_curation_started(
        self,
        insights_count: int,
        current_playbook_size: int,
        run_id: Optional[str] = None
    ):
        """Log curation start event."""
        self.info("curation_started", {
            "insights_count": insights_count,
            "current_playbook_size": current_playbook_size
        }, run_id=run_id)

    def log_delta_operations_generated(
        self,
        duration: float,
        operations: Dict[str, int],
        run_id: Optional[str] = None
    ):
        """Log delta operations generation event."""
        self.info("delta_operations_generated", {
            "duration": duration,
            "operations": operations
        }, run_id=run_id)

    def log_operation_applied(
        self,
        operation: str,
        bullet_id: str,
        section: Optional[str] = None,
        reason: Optional[str] = None,
        duplicate_check: Optional[Dict[str, Any]] = None,
        content_changed: Optional[bool] = None,
        run_id: Optional[str] = None
    ):
        """Log individual operation application event."""
        data = {
            "operation": operation,
            "bullet_id": bullet_id
        }
        if section:
            data["section"] = section
        if reason:
            data["reason"] = reason
        if duplicate_check:
            data["duplicate_check"] = duplicate_check
        if content_changed is not None:
            data["content_changed"] = content_changed

        self.info("operation_applied", data, run_id=run_id)

    def log_deduplication_started(
        self,
        threshold: float,
        candidates_count: int,
        run_id: Optional[str] = None
    ):
        """Log deduplication start event."""
        self.info("deduplication_started", {
            "threshold": threshold,
            "candidates_count": candidates_count
        }, run_id=run_id)

    def log_deduplication_completed(
        self,
        duration: float,
        duplicates_found: int,
        merges: list,
        run_id: Optional[str] = None
    ):
        """Log deduplication completion event."""
        self.info("deduplication_completed", {
            "duration": duration,
            "duplicates_found": duplicates_found,
            "merges": merges
        }, run_id=run_id)

    def log_pruning_started(
        self,
        current_size: int,
        max_size: int,
        threshold: float,
        run_id: Optional[str] = None
    ):
        """Log pruning start event."""
        self.info("pruning_started", {
            "current_size": current_size,
            "max_size": max_size,
            "threshold": threshold
        }, run_id=run_id)

    def log_pruning_completed(
        self,
        duration: float,
        bullets_removed: int,
        run_id: Optional[str] = None
    ):
        """Log pruning completion event."""
        self.info("pruning_completed", {
            "duration": duration,
            "bullets_removed": bullets_removed
        }, run_id=run_id)

    def log_playbook_updated(
        self,
        total_duration: float,
        size_before: int,
        size_after: int,
        changes: Dict[str, int],
        new_version: str,
        run_id: Optional[str] = None
    ):
        """Log playbook update completion event."""
        self.info("playbook_updated", {
            "total_duration": total_duration,
            "size_before": size_before,
            "size_after": size_after,
            "changes": changes,
            "new_version": new_version
        }, run_id=run_id)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _write_log_entry(self, log_path: Path, entry: Dict[str, Any]):
        """Write a log entry to file in JSONL format."""
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


# Factory functions for convenience
def create_generator_logger(
    logs_manager: Optional[LogsManager] = None
) -> StructuredLogger:
    """Create a logger for Generator component."""
    return StructuredLogger("generator", logs_manager)


def create_reflector_logger(
    logs_manager: Optional[LogsManager] = None
) -> StructuredLogger:
    """Create a logger for Reflector component."""
    return StructuredLogger("reflector", logs_manager)


def create_curator_logger(
    logs_manager: Optional[LogsManager] = None
) -> StructuredLogger:
    """Create a logger for Curator component."""
    return StructuredLogger("curator", logs_manager)
