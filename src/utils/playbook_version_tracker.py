"""
Playbook Version Tracker (A2) - Track Playbook evolution over time.

Provides:
- Automatic version snapshots after each update
- Version metadata and change tracking
- Version comparison and diff
- Version history queries
"""

import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ace_framework.playbook.schemas import Playbook
from utils.logs_manager import LogsManager, get_logs_manager


class PlaybookVersionTracker:
    """
    Tracks Playbook versions and changes over time.

    Features:
    - Automatic snapshot creation
    - Metadata tracking (reason, changes, statistics)
    - Version indexing for fast lookup
    - Diff and comparison utilities
    """

    def __init__(
        self,
        playbook_path: str,
        logs_manager: Optional[LogsManager] = None
    ):
        """
        Args:
            playbook_path: Path to the current playbook file
            logs_manager: LogsManager instance (uses default if None)
        """
        self.playbook_path = Path(playbook_path)
        self.logs_manager = logs_manager or get_logs_manager()
        self.versions_dir = self.logs_manager.playbook_versions_dir

        # Version counter (read from index)
        self.version_counter = self._get_latest_version_number() + 1

    # ========================================================================
    # Version Creation
    # ========================================================================

    def save_version(
        self,
        reason: str,
        trigger: str = "manual",
        run_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        generation_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Path, Path]:
        """
        Save current Playbook as a new version.

        Args:
            reason: Human-readable reason for this version
            trigger: What triggered this save ("curator_update", "manual", etc.)
            run_id: Associated run ID (if applicable)
            changes: Dict with "added", "updated", "removed" bullet lists
            generation_metadata: Metadata from the generation that led to this update

        Returns:
            Tuple of (version_id, playbook_path, meta_path)
        """
        # Read current playbook
        if not self.playbook_path.exists():
            raise FileNotFoundError(f"Playbook not found: {self.playbook_path}")

        with open(self.playbook_path, "r") as f:
            playbook_data = json.load(f)

        # Generate version ID
        version_id = f"v{self.version_counter:03d}"
        self.version_counter += 1

        # Get paths for version files
        playbook_path, meta_path = self.logs_manager.get_playbook_version_path(version_id)

        # Save playbook snapshot
        with open(playbook_path, "w") as f:
            json.dump(playbook_data, f, indent=2)

        # Compute statistics
        bullets = playbook_data.get("bullets", [])
        size = len(bullets)

        section_distribution = {}
        helpfulness_scores = []
        for bullet in bullets:
            section = bullet.get("section", "unknown")
            section_distribution[section] = section_distribution.get(section, 0) + 1

            metadata = bullet.get("metadata", {})
            helpful = metadata.get("helpful_count", 0)
            harmful = metadata.get("harmful_count", 0)
            neutral = metadata.get("neutral_count", 0)
            total_uses = helpful + harmful + neutral

            if total_uses > 0:
                helpfulness_scores.append(helpful / total_uses)
            else:
                helpfulness_scores.append(0.5)  # Default

        avg_helpfulness = sum(helpfulness_scores) / len(helpfulness_scores) if helpfulness_scores else 0.0

        # Create metadata
        metadata = {
            "version": version_id,
            "timestamp": datetime.now().isoformat(),
            "run_id": run_id or self.logs_manager.current_run_id,
            "playbook_path": str(self.playbook_path),
            "reason": reason,
            "trigger": trigger,
            "changes": changes or {
                "added": 0,
                "updated": 0,
                "removed": 0,
                "added_bullets": [],
                "updated_bullets": [],
                "removed_bullets": []
            },
            "size": size,
            "section_distribution": section_distribution,
            "avg_helpfulness_score": avg_helpfulness,
            "generation_metadata": generation_metadata or {}
        }

        # Save metadata
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Update version index
        self._update_version_index({
            "version": version_id,
            "timestamp": metadata["timestamp"],
            "run_id": run_id,
            "size": size,
            "reason": reason,
            "changes": {
                "added": metadata["changes"]["added"],
                "updated": metadata["changes"]["updated"],
                "removed": metadata["changes"]["removed"]
            }
        })

        return version_id, playbook_path, meta_path

    def save_version_with_changes_info(
        self,
        reason: str,
        playbook_before: Playbook,
        playbook_after: Playbook,
        trigger: str = "curator_update",
        run_id: Optional[str] = None,
        generation_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Path, Path]:
        """
        Save version with automatically computed changes.

        Args:
            reason: Reason for this version
            playbook_before: Playbook state before changes
            playbook_after: Playbook state after changes
            trigger: What triggered this save
            run_id: Associated run ID
            generation_metadata: Generation metadata

        Returns:
            Tuple of (version_id, playbook_path, meta_path)
        """
        # Compute changes
        bullets_before = {b.id: b for b in playbook_before.bullets}
        bullets_after = {b.id: b for b in playbook_after.bullets}

        added_ids = set(bullets_after.keys()) - set(bullets_before.keys())
        removed_ids = set(bullets_before.keys()) - set(bullets_after.keys())

        updated_ids = []
        for bid in bullets_before.keys() & bullets_after.keys():
            if bullets_before[bid].content != bullets_after[bid].content:
                updated_ids.append(bid)

        changes = {
            "added": len(added_ids),
            "updated": len(updated_ids),
            "removed": len(removed_ids),
            "added_bullets": list(added_ids),
            "updated_bullets": updated_ids,
            "removed_bullets": list(removed_ids)
        }

        # Add size_before for metadata
        if generation_metadata is None:
            generation_metadata = {}
        generation_metadata["size_before"] = playbook_before.size

        return self.save_version(
            reason=reason,
            trigger=trigger,
            run_id=run_id,
            changes=changes,
            generation_metadata=generation_metadata
        )

    # ========================================================================
    # Version Queries
    # ========================================================================

    def list_versions(self) -> List[Dict[str, Any]]:
        """
        List all versions.

        Returns:
            List of version index entries
        """
        versions = []
        index_file = self.logs_manager.versions_index_file

        if index_file.exists():
            with open(index_file, "r") as f:
                for line in f:
                    if line.strip():
                        versions.append(json.loads(line))

        return versions

    def get_version_metadata(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific version.

        Args:
            version: Version ID (e.g., "v001")

        Returns:
            Metadata dictionary or None if not found
        """
        # Find meta file for this version
        meta_files = list(self.versions_dir.glob(f"meta_*_{version}.json"))

        if meta_files:
            with open(meta_files[0], "r") as f:
                return json.load(f)

        return None

    def get_version_playbook_path(self, version: str) -> Optional[Path]:
        """
        Get path to playbook file for a specific version.

        Args:
            version: Version ID (e.g., "v001")

        Returns:
            Path to playbook file or None if not found
        """
        playbook_files = list(self.versions_dir.glob(f"playbook_*_{version}.json"))
        return playbook_files[0] if playbook_files else None

    # ========================================================================
    # Version Comparison
    # ========================================================================

    def diff_versions(
        self,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two Playbook versions.

        Args:
            version1: Earlier version ID
            version2: Later version ID

        Returns:
            Diff dictionary with added/removed/modified bullets
        """
        # Load both versions
        path1 = self.get_version_playbook_path(version1)
        path2 = self.get_version_playbook_path(version2)

        if not path1 or not path2:
            raise ValueError(f"Version not found: {version1} or {version2}")

        with open(path1, "r") as f:
            pb1 = json.load(f)
        with open(path2, "r") as f:
            pb2 = json.load(f)

        bullets1 = {b["id"]: b for b in pb1.get("bullets", [])}
        bullets2 = {b["id"]: b for b in pb2.get("bullets", [])}

        added = set(bullets2.keys()) - set(bullets1.keys())
        removed = set(bullets1.keys()) - set(bullets2.keys())

        modified = []
        for bid in bullets1.keys() & bullets2.keys():
            if bullets1[bid]["content"] != bullets2[bid]["content"]:
                modified.append({
                    "bullet_id": bid,
                    "old_content": bullets1[bid]["content"],
                    "new_content": bullets2[bid]["content"]
                })

        return {
            "version1": version1,
            "version2": version2,
            "added": list(added),
            "removed": list(removed),
            "modified": modified,
            "size_change": len(bullets2) - len(bullets1),
            "size_before": len(bullets1),
            "size_after": len(bullets2)
        }

    def get_bullet_history(self, bullet_id: str) -> List[Dict[str, Any]]:
        """
        Track the history of a specific bullet across all versions.

        Args:
            bullet_id: Bullet ID to track

        Returns:
            List of version info where this bullet appears/changes
        """
        history = []

        for version_entry in self.list_versions():
            version = version_entry["version"]
            playbook_path = self.get_version_playbook_path(version)

            if playbook_path:
                with open(playbook_path, "r") as f:
                    playbook = json.load(f)

                bullet = next(
                    (b for b in playbook.get("bullets", []) if b["id"] == bullet_id),
                    None
                )

                if bullet:
                    history.append({
                        "version": version,
                        "timestamp": version_entry["timestamp"],
                        "content": bullet["content"],
                        "metadata": bullet.get("metadata", {})
                    })

        return history

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _get_latest_version_number(self) -> int:
        """Get the latest version number from index."""
        versions = self.list_versions()
        if not versions:
            return 0

        # Extract version numbers (e.g., "v001" -> 1)
        version_numbers = [
            int(v["version"][1:]) for v in versions if v["version"].startswith("v")
        ]

        return max(version_numbers) if version_numbers else 0

    def _update_version_index(self, entry: Dict[str, Any]):
        """Update versions index file."""
        self.logs_manager.update_versions_index(entry)

    # ========================================================================
    # Restore and Export
    # ========================================================================

    def restore_version(self, version: str, backup_current: bool = True):
        """
        Restore a specific version to become the current playbook.

        Args:
            version: Version ID to restore
            backup_current: Whether to backup current playbook first
        """
        # Backup current if requested
        if backup_current and self.playbook_path.exists():
            self.save_version(
                reason=f"Backup before restoring {version}",
                trigger="restore"
            )

        # Get version file
        version_path = self.get_version_playbook_path(version)
        if not version_path:
            raise ValueError(f"Version not found: {version}")

        # Copy version to current playbook
        shutil.copy(version_path, self.playbook_path)

    def export_evolution_data(self, output_path: str):
        """
        Export Playbook evolution data for visualization.

        Args:
            output_path: Path to save JSON data
        """
        versions = self.list_versions()

        evolution_data = []
        for version_entry in versions:
            version = version_entry["version"]
            metadata = self.get_version_metadata(version)

            if metadata:
                evolution_data.append({
                    "version": version,
                    "timestamp": metadata["timestamp"],
                    "size": metadata["size"],
                    "avg_helpfulness": metadata["avg_helpfulness_score"],
                    "section_distribution": metadata["section_distribution"],
                    "changes": metadata["changes"]
                })

        with open(output_path, "w") as f:
            json.dump(evolution_data, f, indent=2)
