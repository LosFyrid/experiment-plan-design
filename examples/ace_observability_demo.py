#!/usr/bin/env python3
"""
ACE Framework Observability System - Example Usage

This script demonstrates how to use the observability tools integrated
into the ACE framework (Generator, Reflector, Curator).

It shows:
1. How to initialize observability tools
2. How to run a complete ACE cycle with logging
3. How to query and analyze the generated logs

Usage:
    python ace_observability_demo.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from datetime import datetime
from typing import Dict, Any

# ACE Framework imports
from ace_framework.playbook.playbook_manager import PlaybookManager
from ace_framework.playbook.schemas import (
    PlaybookBullet,
    BulletMetadata,
    ExperimentPlan,
    Material,
    ProcedureStep,
    QCCheck,
    Feedback,
    Insight
)
from ace_framework.generator.generator import PlanGenerator
from ace_framework.reflector.reflector import PlanReflector
from ace_framework.curator.curator import PlaybookCurator

# Observability imports
from utils.logs_manager import LogsManager, get_logs_manager
from utils.structured_logger import (
    StructuredLogger,
    create_generator_logger,
    create_reflector_logger,
    create_curator_logger
)
from utils.performance_monitor import PerformanceMonitor, create_performance_monitor
from utils.llm_call_tracker import LLMCallTracker, create_llm_call_tracker
from utils.playbook_version_tracker import PlaybookVersionTracker

# LLM provider (mock for demo)
from utils.llm_provider import BaseLLMProvider, LLMResponse
from utils.config_loader import GeneratorConfig, ReflectorConfig, CuratorConfig


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for demonstration purposes."""

    def __init__(self):
        self.provider = "mock"
        self.model_name = "mock-model"
        self.temperature = 0.7
        self.max_tokens = 4000

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Generate a mock response."""
        # Mock response based on which component is calling
        if "experiment plan" in prompt.lower():
            # Generator mock response
            content = """{
                "plan": {
                    "title": "Synthesis of Aspirin",
                    "objective": "Synthesize aspirin from salicylic acid",
                    "materials": [
                        {
                            "name": "Salicylic acid",
                            "amount": "2.0 g",
                            "purity": "≥99%",
                            "cas_number": "69-72-7"
                        },
                        {
                            "name": "Acetic anhydride",
                            "amount": "5.0 mL",
                            "purity": "≥99%",
                            "cas_number": "108-24-7"
                        }
                    ],
                    "procedure": [
                        {
                            "step_number": 1,
                            "description": "Weigh 2.0 g salicylic acid into a dry flask",
                            "duration": "5 min",
                            "temperature": "room temperature",
                            "safety_notes": ["Wear gloves and safety glasses"]
                        },
                        {
                            "step_number": 2,
                            "description": "Add 5.0 mL acetic anhydride and 3 drops H2SO4",
                            "duration": "2 min",
                            "temperature": "room temperature",
                            "safety_notes": ["Add acetic anhydride slowly", "Use fume hood"]
                        }
                    ],
                    "safety_notes": [
                        "Work in fume hood - acetic anhydride is corrosive",
                        "Wear protective equipment at all times"
                    ],
                    "expected_outcome": "White crystalline aspirin product, yield ~80%",
                    "quality_control": [
                        {
                            "check_type": "melting_point",
                            "acceptance_criteria": "135-138°C",
                            "method": "Melting point apparatus"
                        }
                    ]
                },
                "reasoning": {
                    "trajectory": [
                        {
                            "step_number": 1,
                            "thought": "Need to identify suitable starting materials",
                            "action": "Retrieved playbook bullet mat-00015 about reagent selection"
                        }
                    ],
                    "bullets_used": ["mat-00015", "proc-00023", "safe-00008"]
                }
            }"""
        elif "reflect" in prompt.lower() or "analyze" in prompt.lower():
            # Reflector mock response
            content = """{
                "insights": [
                    {
                        "insight_id": "ins-001",
                        "category": "material_selection",
                        "content": "Always specify reagent purity for reproducibility",
                        "priority": "high",
                        "generalizability": "high",
                        "source_reference": "Step 1 material specification"
                    }
                ],
                "bullet_tags": {
                    "mat-00015": "helpful",
                    "proc-00023": "helpful",
                    "safe-00008": "neutral"
                }
            }"""
        else:
            # Curator mock response
            content = """{
                "delta_operations": [
                    {
                        "operation": "ADD",
                        "new_bullet": {
                            "section": "material_selection",
                            "content": "Always specify reagent purity for reproducibility",
                            "metadata": {}
                        },
                        "reason": "Extracted from high-priority insight"
                    }
                ]
            }"""

        return LLMResponse(
            content=content,
            model="mock-model",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300
        )


def create_mock_playbook(playbook_path: str) -> PlaybookManager:
    """Create a mock playbook for demonstration."""
    playbook_manager = PlaybookManager(playbook_path=playbook_path)

    # Create a new playbook
    playbook_manager.get_or_create()

    # Add some initial bullets
    initial_bullets = [
        PlaybookBullet(
            id="mat-00015",
            section="material_selection",
            content="Always verify reagent purity before use",
            metadata=BulletMetadata(
                helpful_count=5,
                harmful_count=0,
                created_at=datetime.now().isoformat(),
                source="manual"
            )
        ),
        PlaybookBullet(
            id="proc-00023",
            section="procedure_design",
            content="Use fume hood for volatile reagents",
            metadata=BulletMetadata(
                helpful_count=8,
                harmful_count=0,
                created_at=datetime.now().isoformat(),
                source="manual"
            )
        ),
        PlaybookBullet(
            id="safe-00008",
            section="safety_protocols",
            content="Wear protective equipment at all times",
            metadata=BulletMetadata(
                helpful_count=10,
                harmful_count=0,
                created_at=datetime.now().isoformat(),
                source="manual"
            )
        )
    ]

    for bullet in initial_bullets:
        playbook_manager.add_bullet(bullet)

    playbook_manager.save()

    return playbook_manager


def run_ace_cycle_with_observability():
    """Run a complete ACE cycle with observability enabled."""

    print("=" * 80)
    print("ACE Framework Observability System - Demo")
    print("=" * 80)

    # Step 1: Initialize observability infrastructure
    print("\n[1/7] Initializing observability infrastructure...")

    logs_manager = get_logs_manager()
    run_id = logs_manager.start_run()

    print(f"  ✓ Started new run: {run_id}")
    print(f"  ✓ Logs directory: {logs_manager.get_run_dir(run_id)}")

    # Create observability tools
    perf_monitor = create_performance_monitor(run_id=run_id)
    perf_monitor.start_run()

    generator_logger = create_generator_logger(run_id=run_id)
    reflector_logger = create_reflector_logger(run_id=run_id)
    curator_logger = create_curator_logger(run_id=run_id)

    generator_llm_tracker = create_llm_call_tracker("generator", run_id=run_id)
    reflector_llm_tracker = create_llm_call_tracker("reflector", run_id=run_id)
    curator_llm_tracker = create_llm_call_tracker("curator", run_id=run_id)

    version_tracker = PlaybookVersionTracker(run_id=run_id)

    print("  ✓ Created all observability tools")

    # Step 2: Initialize ACE components
    print("\n[2/7] Initializing ACE components...")

    # Create mock playbook
    playbook_path = str(project_root / "data" / "playbooks" / "demo_playbook.json")
    playbook_manager = create_mock_playbook(playbook_path)

    print(f"  ✓ Created playbook with {playbook_manager.playbook.size} bullets")

    # Save initial version
    version_tracker.save_version(
        playbook=playbook_manager.playbook,
        trigger="initialization",
        run_id=run_id
    )

    # Initialize components with observability
    llm_provider = MockLLMProvider()

    generator = PlanGenerator(
        playbook_manager=playbook_manager,
        llm_provider=llm_provider,
        config=GeneratorConfig(),
        logger=generator_logger,
        perf_monitor=perf_monitor,
        llm_tracker=generator_llm_tracker
    )

    reflector = PlanReflector(
        llm_provider=llm_provider,
        config=ReflectorConfig(),
        playbook_manager=playbook_manager,
        logger=reflector_logger,
        perf_monitor=perf_monitor,
        llm_tracker=reflector_llm_tracker
    )

    curator = PlaybookCurator(
        playbook_manager=playbook_manager,
        llm_provider=llm_provider,
        config=CuratorConfig(),
        logger=curator_logger,
        perf_monitor=perf_monitor,
        llm_tracker=curator_llm_tracker
    )

    print("  ✓ Initialized Generator, Reflector, Curator with observability")

    # Step 3: Run Generator
    print("\n[3/7] Running Generator...")

    requirements = {
        "objective": "Synthesize aspirin from salicylic acid",
        "target_compound": "Aspirin (acetylsalicylic acid)",
        "constraints": ["Use common lab equipment", "Complete in 2 hours"]
    }

    generation_result = generator.generate(requirements=requirements)

    print(f"  ✓ Generated plan: {generation_result.generated_plan.title}")
    print(f"  ✓ Used {len(generation_result.relevant_bullets)} playbook bullets")
    print(f"  ✓ Trajectory: {len(generation_result.trajectory)} steps")

    # Step 4: Run Reflector
    print("\n[4/7] Running Reflector...")

    # Create mock feedback
    feedback = Feedback(
        overall_score=0.85,
        completeness=0.9,
        safety=0.95,
        clarity=0.8,
        executability=0.85,
        cost_effectiveness=0.7,
        comments="Good plan but could improve cost efficiency"
    )

    reflection_result = reflector.reflect(
        generated_plan=generation_result.generated_plan,
        feedback=feedback,
        trajectory=generation_result.trajectory,
        playbook_bullets_used=generation_result.relevant_bullets
    )

    print(f"  ✓ Extracted {len(reflection_result.insights)} insights")
    print(f"  ✓ Tagged {len(reflection_result.bullet_tags)} bullets")

    # Step 5: Run Curator
    print("\n[5/7] Running Curator...")

    size_before = playbook_manager.playbook.size

    curation_result = curator.update(reflection_result=reflection_result)

    size_after = playbook_manager.playbook.size

    print(f"  ✓ Playbook updated: {size_before} → {size_after} bullets")
    print(f"  ✓ Operations: +{curation_result.bullets_added} "
          f"-{curation_result.bullets_removed} ~{curation_result.bullets_updated}")

    # Save updated version
    version_tracker.save_version(
        playbook=playbook_manager.playbook,
        trigger="curation",
        run_id=run_id,
        changes={
            "added": curation_result.bullets_added,
            "updated": curation_result.bullets_updated,
            "removed": curation_result.bullets_removed
        }
    )

    # Step 6: Finalize observability
    print("\n[6/7] Finalizing observability...")

    perf_monitor.end_run()
    perf_monitor.save_report(run_id=run_id)

    logs_manager.end_run()

    print("  ✓ Saved performance report")
    print("  ✓ Saved playbook version")
    print("  ✓ Finalized all logs")

    # Step 7: Demonstrate querying
    print("\n[7/7] Demonstrating log querying...")

    # Show what was logged
    print("\n  Logged events:")
    print(f"    - Generator: {logs_manager.get_run_dir(run_id) / 'generator.jsonl'}")
    print(f"    - Reflector: {logs_manager.get_run_dir(run_id) / 'reflector.jsonl'}")
    print(f"    - Curator: {logs_manager.get_run_dir(run_id) / 'curator.jsonl'}")
    print(f"    - Performance: {logs_manager.get_performance_log_path(run_id)}")

    # Show LLM calls
    llm_calls_dir = logs_manager.llm_calls_dir / datetime.now().strftime("%Y%m%d")
    generator_calls = list((llm_calls_dir / "generator").glob("*.json"))
    reflector_calls = list((llm_calls_dir / "reflector").glob("*.json"))
    curator_calls = list((llm_calls_dir / "curator").glob("*.json"))

    print(f"\n  LLM calls tracked:")
    print(f"    - Generator: {len(generator_calls)} calls")
    print(f"    - Reflector: {len(reflector_calls)} calls")
    print(f"    - Curator: {len(curator_calls)} calls")

    # Show performance summary
    print("\n  Performance summary:")
    perf_monitor.print_summary()

    # Step 8: Show how to use analysis scripts
    print("\n" + "=" * 80)
    print("Next Steps: Analyze the logs")
    print("=" * 80)

    print(f"""
You can now use the analysis scripts to query the logs:

1. Query this run:
   python scripts/analysis/query_runs.py --run-id {run_id}

2. Query LLM calls:
   python scripts/analysis/query_llm_calls.py --run-id {run_id}

3. Analyze performance:
   python scripts/analysis/analyze_performance.py --run-id {run_id}

4. Check playbook evolution:
   python scripts/analysis/analyze_playbook_evolution.py --list-versions

5. Export a prompt for inspection:
   python scripts/analysis/query_llm_calls.py --run-id {run_id} --details

See scripts/analysis/README.md for full documentation.
    """)

    print("=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_ace_cycle_with_observability()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
