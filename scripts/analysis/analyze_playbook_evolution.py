#!/usr/bin/env python3
"""
Analyze playbook evolution over time.

Usage:
    python analyze_playbook_evolution.py --list-versions
    python analyze_playbook_evolution.py --compare v1 v2
    python analyze_playbook_evolution.py --growth-stats
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "logs"


def list_playbook_versions() -> List[Dict[str, Any]]:
    """
    List all playbook versions.

    Returns:
        List of version metadata dictionaries
    """
    logs_dir = get_logs_dir()
    versions_dir = logs_dir / "playbook_versions"

    if not versions_dir.exists():
        print(f"No playbook versions directory found at {versions_dir}")
        return []

    versions = []

    for version_file in sorted(versions_dir.glob("*.json")):
        with open(version_file) as f:
            data = json.load(f)

        # Determine file type and extract appropriate data
        # Type 1: playbook_*.json - full snapshot with bullets
        # Type 2: meta_*.json - metadata only

        if "bullets" in data:
            # Full playbook snapshot
            version_info = {
                "version_id": version_file.stem,
                "timestamp": data.get("last_updated", ""),
                "trigger": None,  # Not in snapshot format
                "run_id": None,
                "size": len(data.get("bullets", [])),
                "bullets_count": len(data.get("bullets", [])),
                "path": str(version_file),
                "file_type": "snapshot"
            }
        else:
            # Metadata file
            version_info = {
                "version_id": data.get("version", version_file.stem),
                "timestamp": data.get("timestamp", ""),
                "trigger": data.get("trigger"),
                "run_id": data.get("run_id"),
                "size": data.get("size", 0),
                "bullets_count": data.get("size", 0),
                "path": str(version_file),
                "file_type": "metadata"
            }

        versions.append(version_info)

    return versions


def load_playbook_version(version_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a specific playbook version.

    Args:
        version_id: Version identifier (filename without .json extension)

    Returns:
        Playbook version data or None
    """
    logs_dir = get_logs_dir()
    versions_dir = logs_dir / "playbook_versions"

    version_file = versions_dir / f"{version_id}.json"
    if version_file.exists():
        with open(version_file) as f:
            data = json.load(f)

        # Wrap metadata files to provide consistent interface
        if "bullets" not in data:
            # Metadata file - convert to playbook-like structure
            return {
                "playbook": {
                    "bullets": [],  # Metadata files don't have full bullets
                    "size": data.get("size", 0)
                },
                "metadata": data
            }
        else:
            # Full snapshot - wrap it
            return {
                "playbook": data,
                "metadata": {
                    "version_id": version_id,
                    "timestamp": data.get("last_updated", ""),
                    "trigger": "snapshot"
                }
            }

    return None


def print_versions_list(versions: List[Dict[str, Any]]):
    """Print a list of playbook versions."""
    if not versions:
        print("No playbook versions found.")
        return

    print("\n" + "=" * 110)
    print("PLAYBOOK VERSIONS")
    print("=" * 110)

    print(f"\n{'Version ID':<30} {'Timestamp':<20} {'Trigger':<15} {'Size':<8} {'Type':<10} {'Run ID':<15}")
    print("-" * 110)

    for v in versions:
        version_id = v["version_id"][:29]
        timestamp = v["timestamp"][:19] if v["timestamp"] else "N/A"
        trigger = (v.get("trigger") or "N/A")[:14]
        size = v["bullets_count"]
        file_type = v.get("file_type", "unknown")[:9]
        run_id = (v.get("run_id") or "N/A")[:14]

        print(f"{version_id:<30} {timestamp:<20} {trigger:<15} {size:<8} {file_type:<10} {run_id:<15}")

    # Summary statistics
    meta_count = sum(1 for v in versions if v.get("file_type") == "metadata")
    snapshot_count = sum(1 for v in versions if v.get("file_type") == "snapshot")

    print(f"\nTotal versions: {len(versions)} (metadata: {meta_count}, snapshots: {snapshot_count})")
    print("=" * 110)


def compare_versions(version1_id: str, version2_id: str):
    """
    Compare two playbook versions.

    Args:
        version1_id: First version ID
        version2_id: Second version ID
    """
    v1 = load_playbook_version(version1_id)
    v2 = load_playbook_version(version2_id)

    if not v1:
        print(f"Version {version1_id} not found.")
        return
    if not v2:
        print(f"Version {version2_id} not found.")
        return

    playbook1 = v1.get("playbook", {})
    playbook2 = v2.get("playbook", {})

    bullets1 = {b["id"]: b for b in playbook1.get("bullets", [])}
    bullets2 = {b["id"]: b for b in playbook2.get("bullets", [])}

    # Find differences
    added = set(bullets2.keys()) - set(bullets1.keys())
    removed = set(bullets1.keys()) - set(bullets2.keys())
    common = set(bullets1.keys()) & set(bullets2.keys())

    # Check for content changes in common bullets
    modified = []
    for bullet_id in common:
        if bullets1[bullet_id]["content"] != bullets2[bullet_id]["content"]:
            modified.append(bullet_id)

    # Print comparison
    print("\n" + "=" * 80)
    print("PLAYBOOK VERSION COMPARISON")
    print("=" * 80)

    print(f"\nVersion 1: {version1_id}")
    print(f"  Timestamp: {v1.get('metadata', {}).get('timestamp')}")
    print(f"  Size: {len(bullets1)} bullets")

    print(f"\nVersion 2: {version2_id}")
    print(f"  Timestamp: {v2.get('metadata', {}).get('timestamp')}")
    print(f"  Size: {len(bullets2)} bullets")

    print("\n" + "-" * 80)
    print("CHANGES")
    print("-" * 80)

    print(f"\nAdded: {len(added)} bullets")
    if added:
        for bullet_id in sorted(added)[:10]:  # Show first 10
            content = bullets2[bullet_id]["content"][:60]
            print(f"  + {bullet_id}: {content}...")

        if len(added) > 10:
            print(f"  ... and {len(added) - 10} more")

    print(f"\nRemoved: {len(removed)} bullets")
    if removed:
        for bullet_id in sorted(removed)[:10]:
            content = bullets1[bullet_id]["content"][:60]
            print(f"  - {bullet_id}: {content}...")

        if len(removed) > 10:
            print(f"  ... and {len(removed) - 10} more")

    print(f"\nModified: {len(modified)} bullets")
    if modified:
        for bullet_id in sorted(modified)[:10]:
            print(f"  ~ {bullet_id}")

        if len(modified) > 10:
            print(f"  ... and {len(modified) - 10} more")

    print("\n" + "=" * 80)


def analyze_growth_stats(versions: List[Dict[str, Any]]):
    """Analyze playbook growth statistics."""
    if not versions:
        print("No versions to analyze.")
        return

    print("\n" + "=" * 80)
    print("PLAYBOOK GROWTH STATISTICS")
    print("=" * 80)

    # Sort by timestamp (handle None values)
    sorted_versions = sorted(versions, key=lambda v: v.get("timestamp") or "")

    # Calculate growth
    sizes = [v["bullets_count"] for v in sorted_versions]

    print(f"\nTotal Versions: {len(versions)}")
    print(f"Initial Size: {sizes[0]} bullets")
    print(f"Current Size: {sizes[-1]} bullets")

    # Calculate growth percentage (handle zero initial size)
    net_growth = sizes[-1] - sizes[0]
    if sizes[0] > 0:
        growth_pct = (net_growth / sizes[0]) * 100
        print(f"Net Growth: {net_growth} bullets ({growth_pct:.1f}%)")
    else:
        print(f"Net Growth: {net_growth} bullets (from empty playbook)")

    # Growth by trigger
    trigger_counts = defaultdict(int)
    for v in versions:
        trigger = v.get("trigger") or "snapshot"
        trigger_counts[trigger] += 1

    print("\nVersions by Trigger:")
    for trigger, count in sorted(trigger_counts.items()):
        print(f"  - {trigger}: {count}")

    # Find the most recent full snapshot for detailed analysis
    snapshot_versions = [v for v in sorted_versions if v.get("file_type") == "snapshot"]

    if snapshot_versions:
        latest_snapshot = snapshot_versions[-1]
        latest = load_playbook_version(latest_snapshot["version_id"])

        if latest:
            playbook = latest.get("playbook", {})
            bullets = playbook.get("bullets", [])

            if bullets:
                section_counts = defaultdict(int)
                for bullet in bullets:
                    section = bullet.get("section", "unknown")
                    section_counts[section] += 1

                print(f"\nCurrent Section Distribution (from latest snapshot {latest_snapshot['version_id']}):")
                for section, count in sorted(section_counts.items()):
                    pct = count / len(bullets) * 100 if bullets else 0
                    print(f"  - {section}: {count} bullets ({pct:.1f}%)")

                # Quality statistics
                helpful_scores = [b.get("metadata", {}).get("helpful_count", 0) for b in bullets]
                harmful_scores = [b.get("metadata", {}).get("harmful_count", 0) for b in bullets]

                print("\nQuality Metrics:")
                if helpful_scores:
                    print(f"  - Avg Helpful Count: {sum(helpful_scores) / len(helpful_scores):.2f}")
                    print(f"  - Avg Harmful Count: {sum(harmful_scores) / len(harmful_scores):.2f}")

                    # High-quality bullets
                    high_quality = [b for b in bullets if b.get("metadata", {}).get("helpful_count", 0) >= 3]
                    pct = len(high_quality) / len(bullets) * 100 if bullets else 0
                    print(f"  - High Quality Bullets (helpful_count >= 3): {len(high_quality)} ({pct:.1f}%)")
            else:
                print("\nNo bullets found in latest snapshot.")
    else:
        print("\nNo full snapshots available for detailed analysis.")
        print("Note: Only metadata files exist, which don't contain full bullet information.")

    print("\n" + "=" * 80)


def track_bullet_evolution(bullet_id: str):
    """
    Track how a specific bullet evolved across versions.

    Args:
        bullet_id: Bullet ID to track
    """
    versions = list_playbook_versions()

    if not versions:
        print("No versions found.")
        return

    print("\n" + "=" * 80)
    print(f"EVOLUTION OF BULLET: {bullet_id}")
    print("=" * 80)

    found_count = 0

    for v in sorted(versions, key=lambda x: x.get("timestamp", "")):
        version_data = load_playbook_version(v["version_id"])
        if not version_data:
            continue

        playbook = version_data.get("playbook", {})
        bullets = {b["id"]: b for b in playbook.get("bullets", [])}

        if bullet_id in bullets:
            bullet = bullets[bullet_id]
            found_count += 1

            print(f"\nVersion: {v['version_id']}")
            print(f"Timestamp: {v['timestamp']}")
            print(f"Content: {bullet['content']}")

            metadata = bullet.get("metadata", {})
            print(f"Helpful: {metadata.get('helpful_count', 0)}, Harmful: {metadata.get('harmful_count', 0)}")
            print(f"Uses: {metadata.get('total_uses', 0)}")

            print("-" * 80)

    if found_count == 0:
        print(f"\nBullet {bullet_id} not found in any version.")
    else:
        print(f"\nFound in {found_count} versions.")

    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Analyze playbook evolution")
    parser.add_argument("--list-versions", action="store_true",
                       help="List all playbook versions")
    parser.add_argument("--compare", nargs=2, metavar=("V1", "V2"),
                       help="Compare two versions")
    parser.add_argument("--growth-stats", action="store_true",
                       help="Show growth statistics")
    parser.add_argument("--track-bullet", metavar="BULLET_ID",
                       help="Track evolution of a specific bullet")

    args = parser.parse_args()

    if args.list_versions:
        versions = list_playbook_versions()
        print_versions_list(versions)
    elif args.compare:
        compare_versions(args.compare[0], args.compare[1])
    elif args.growth_stats:
        versions = list_playbook_versions()
        analyze_growth_stats(versions)
    elif args.track_bullet:
        track_bullet_evolution(args.track_bullet)
    else:
        # Default: show versions list
        versions = list_playbook_versions()
        print_versions_list(versions)


if __name__ == "__main__":
    main()
