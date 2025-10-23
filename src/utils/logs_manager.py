"""
Logs Manager - Central manager for all logging operations.

Responsibilities:
- Generate unique run_ids
- Create and manage log directory structure
- Maintain index files
- Provide log path resolution
"""

import os
import json
import random
import string
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


class LogsManager:
    """
    Central manager for ACE framework logging.

    Manages:
    - Run ID generation and tracking
    - Log directory creation
    - Index file maintenance
    - Path resolution for all log types
    """

    def __init__(self, logs_root: str = "logs"):
        """
        Args:
            logs_root: Root directory for all logs (default: "logs")
        """
        self.logs_root = Path(logs_root)
        self.logs_root.mkdir(exist_ok=True)

        # Create subdirectories
        self.runs_dir = self.logs_root / "runs"
        self.llm_calls_dir = self.logs_root / "llm_calls"
        self.playbook_versions_dir = self.logs_root / "playbook_versions"
        self.components_dir = self.logs_root / "components"
        self.performance_dir = self.logs_root / "performance"
        self.errors_dir = self.logs_root / "errors"
        self.prompts_dir = self.logs_root / "prompts"

        for dir_path in [
            self.runs_dir,
            self.llm_calls_dir,
            self.playbook_versions_dir,
            self.components_dir,
            self.performance_dir,
            self.errors_dir,
            self.prompts_dir
        ]:
            dir_path.mkdir(exist_ok=True)

        # Index files
        self.runs_index_file = self.runs_dir / "runs_index.jsonl"
        self.versions_index_file = self.playbook_versions_dir / "versions_index.jsonl"

        # Current run context
        self.current_run_id: Optional[str] = None
        self.current_run_dir: Optional[Path] = None

    # ========================================================================
    # Run ID Management
    # ========================================================================

    def generate_run_id(self) -> str:
        """
        Generate unique run ID: {HHMMSS}_{random6chars}

        Example: "143015_aBc123"

        Returns:
            Unique run ID string
        """
        timestamp = datetime.now().strftime("%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        return f"{timestamp}_{random_suffix}"

    def start_run(
        self,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new run and create its directory structure.

        Args:
            run_id: Optional custom run ID (auto-generated if None)
            metadata: Optional metadata for the run

        Returns:
            The run ID
        """
        if run_id is None:
            run_id = self.generate_run_id()

        self.current_run_id = run_id

        # Create run directory: logs/runs/{date}/run_{run_id}/
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.runs_dir / date_str
        date_dir.mkdir(exist_ok=True)

        run_dir = date_dir / f"run_{run_id}"
        run_dir.mkdir(exist_ok=True)
        self.current_run_dir = run_dir

        # Create metadata file
        default_metadata = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "date": date_str,
            "status": "running",
            "components": [],
        }

        if metadata:
            default_metadata.update(metadata)

        metadata_file = run_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(default_metadata, f, indent=2)

        # Update runs index
        self._update_runs_index({
            "run_id": run_id,
            "timestamp": default_metadata["timestamp"],
            "date": date_str,
            "status": "running",
            "components": []
        })

        return run_id

    def end_run(
        self,
        run_id: Optional[str] = None,
        status: str = "completed",
        summary: Optional[Dict[str, Any]] = None
    ):
        """
        Mark a run as completed and save summary.

        Args:
            run_id: Run ID to end (uses current if None)
            status: Final status ("completed", "failed", "cancelled")
            summary: Optional summary data
        """
        if run_id is None:
            run_id = self.current_run_id

        if run_id is None:
            return

        # Update metadata
        run_dir = self._get_run_dir(run_id)
        if run_dir:
            metadata_file = run_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                metadata["status"] = status
                metadata["ended_at"] = datetime.now().isoformat()

                # Calculate duration
                start_time = datetime.fromisoformat(metadata["timestamp"])
                end_time = datetime.fromisoformat(metadata["ended_at"])
                metadata["duration"] = (end_time - start_time).total_seconds()

                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)

            # Save summary if provided
            if summary:
                summary_file = run_dir / "summary.json"
                with open(summary_file, "w") as f:
                    json.dump(summary, f, indent=2)

        # Update runs index
        self._update_runs_index({
            "run_id": run_id,
            "status": status
        }, update_existing=True)

        # Clear current run
        if run_id == self.current_run_id:
            self.current_run_id = None
            self.current_run_dir = None

    # ========================================================================
    # Path Resolution
    # ========================================================================

    def get_run_dir(self, run_id: Optional[str] = None) -> Path:
        """Get run directory path."""
        if run_id is None:
            if self.current_run_dir:
                return self.current_run_dir
            raise ValueError("No current run and no run_id provided")

        return self._get_run_dir(run_id)

    def get_component_log_path(
        self,
        component: str,
        run_id: Optional[str] = None
    ) -> Path:
        """Get path to component log file within run directory."""
        run_dir = self.get_run_dir(run_id)
        return run_dir / f"{component}.jsonl"

    def get_performance_log_path(self, run_id: Optional[str] = None) -> Path:
        """Get path to performance log within run directory."""
        run_dir = self.get_run_dir(run_id)
        return run_dir / "performance.json"

    def get_llm_call_path(
        self,
        component: str,
        detail: str = "",
        run_id: Optional[str] = None
    ) -> Path:
        """
        Get path to LLM call log file.

        Args:
            component: Component name (generator/reflector/curator)
            detail: Optional detail (e.g., "round1", "round2")
            run_id: Run ID (uses current if None)

        Returns:
            Path to LLM call log file
        """
        if run_id is None:
            run_id = self.current_run_id

        if run_id is None:
            raise ValueError("No current run and no run_id provided")

        # Create date directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.llm_calls_dir / date_str
        date_dir.mkdir(exist_ok=True)

        # Construct filename
        timestamp = datetime.now().strftime("%H%M%S")
        if detail:
            filename = f"{timestamp}_{run_id}_{component}_{detail}.json"
        else:
            filename = f"{timestamp}_{run_id}_{component}.json"

        return date_dir / filename

    def get_playbook_version_path(self, version: str) -> tuple[Path, Path]:
        """
        Get paths to playbook version file and its metadata.

        Args:
            version: Version identifier (e.g., "v001")

        Returns:
            Tuple of (playbook_path, meta_path)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        playbook_file = self.playbook_versions_dir / f"playbook_{timestamp}_{version}.json"
        meta_file = self.playbook_versions_dir / f"meta_{timestamp}_{version}.json"
        return playbook_file, meta_file

    # ========================================================================
    # Index Management
    # ========================================================================

    def _update_runs_index(
        self,
        entry: Dict[str, Any],
        update_existing: bool = False
    ):
        """Update runs index file."""
        if update_existing:
            # Read existing entries and update matching run_id
            entries = []
            if self.runs_index_file.exists():
                with open(self.runs_index_file, "r") as f:
                    for line in f:
                        if line.strip():
                            existing = json.loads(line)
                            if existing["run_id"] == entry["run_id"]:
                                existing.update(entry)
                            entries.append(existing)

            # Write back all entries
            with open(self.runs_index_file, "w") as f:
                for e in entries:
                    f.write(json.dumps(e) + "\n")
        else:
            # Append new entry
            with open(self.runs_index_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def update_versions_index(self, entry: Dict[str, Any]):
        """Update playbook versions index file."""
        with open(self.versions_index_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def register_component(self, component: str, run_id: Optional[str] = None):
        """Register that a component has been used in this run."""
        if run_id is None:
            run_id = self.current_run_id

        if run_id is None:
            return

        run_dir = self._get_run_dir(run_id)
        if run_dir:
            metadata_file = run_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                if "components" not in metadata:
                    metadata["components"] = []

                if component not in metadata["components"]:
                    metadata["components"].append(component)

                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _get_run_dir(self, run_id: str) -> Optional[Path]:
        """Find run directory by run_id."""
        # Search in all date directories
        for date_dir in self.runs_dir.glob("*"):
            if date_dir.is_dir() and date_dir.name != "runs_index.jsonl":
                run_dir = date_dir / f"run_{run_id}"
                if run_dir.exists():
                    return run_dir
        return None

    def list_runs(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all runs, optionally filtered by date and status.

        Args:
            date: Optional date filter (YYYY-MM-DD)
            status: Optional status filter ("running", "completed", "failed")

        Returns:
            List of run metadata dictionaries
        """
        runs = []

        if self.runs_index_file.exists():
            with open(self.runs_index_file, "r") as f:
                for line in f:
                    if line.strip():
                        run = json.loads(line)

                        # Apply filters
                        if date and run.get("date") != date:
                            continue
                        if status and run.get("status") != status:
                            continue

                        runs.append(run)

        return runs

    def get_run_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific run."""
        run_dir = self._get_run_dir(run_id)
        if run_dir:
            metadata_file = run_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    return json.load(f)
        return None


# Global instance (can be overridden)
_default_logs_manager = None


def get_logs_manager(logs_root: str = "logs") -> LogsManager:
    """Get or create the default LogsManager instance."""
    global _default_logs_manager
    if _default_logs_manager is None:
        _default_logs_manager = LogsManager(logs_root)
    return _default_logs_manager
