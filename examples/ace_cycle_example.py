"""
ACE Framework - End-to-End Example

Demonstrates complete ACE cycle:
1. Generator: Create experiment plan using playbook
2. Evaluation: Get feedback on plan quality
3. Reflector: Analyze and extract insights
4. Curator: Update playbook with delta operations

This example uses mock feedback for demonstration.
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ace_framework.playbook.schemas import Feedback, FeedbackScore
from ace_framework.generator.generator import create_generator
from ace_framework.reflector.reflector import create_reflector
from ace_framework.curator.curator import create_curator
from ace_framework.playbook.playbook_manager import PlaybookManager
from utils.llm_provider import create_llm_provider
from utils.config_loader import get_ace_config, get_env_settings
from utils.embedding_utils import EmbeddingManager


def main():
    """Run complete ACE cycle example."""

    print("=" * 80)
    print("ACE Framework - Complete Cycle Example")
    print("=" * 80)

    # Load configuration
    print("\n[1/7] Loading configuration...")
    config = get_ace_config()
    env = get_env_settings()

    # Check API key
    if not env.dashscope_api_key:
        print("ERROR: DASHSCOPE_API_KEY not set. Please configure .env file.")
        return

    # Create LLM provider
    print("[2/7] Initializing LLM provider...")
    llm_provider = create_llm_provider(
        provider=config.model.provider,
        model_name=config.model.model_name,
        temperature=config.model.temperature,
        max_tokens=config.model.max_tokens
    )
    print(f"  Using: {config.model.provider}/{config.model.model_name}")

    # Create playbook manager
    print("[3/7] Loading playbook...")
    playbook_path = project_root / config.playbook.default_path
    playbook_manager = PlaybookManager(
        playbook_path=str(playbook_path),
        embedding_model="BAAI/bge-small-zh-v1.5"
    )

    try:
        playbook = playbook_manager.load()
        print(f"  Loaded playbook: {playbook.size} bullets, version {playbook.version}")
    except FileNotFoundError:
        print("  Playbook not found. Creating new playbook...")
        playbook = playbook_manager.get_or_create(sections=config.playbook.sections)

    # Create ACE components
    print("[4/7] Creating ACE components...")

    # Generator
    generator = create_generator(
        playbook_path=str(playbook_path),
        llm_provider=llm_provider,
        config=config.generator
    )

    # Reflector
    reflector = create_reflector(
        llm_provider=llm_provider,
        config=config.reflector,
        playbook_manager=playbook_manager
    )

    # Curator
    embedding_manager = EmbeddingManager(model_name="BAAI/bge-small-zh-v1.5")
    curator = create_curator(
        playbook_manager=playbook_manager,
        llm_provider=llm_provider,
        config=config.curator,
        embedding_manager=embedding_manager
    )

    print("  ✓ Generator ready")
    print("  ✓ Reflector ready")
    print("  ✓ Curator ready")

    # Example requirements
    print("\n[5/7] Generating experiment plan...")
    requirements = {
        "target_compound": "Aspirin (Acetylsalicylic acid)",
        "objective": "Synthesize aspirin from salicylic acid via acetylation",
        "materials": ["salicylic acid", "acetic anhydride", "sulfuric acid (catalyst)"],
        "constraints": [
            "Room temperature reaction",
            "Use minimal amount of catalyst",
            "Purify by recrystallization"
        ]
    }

    print(f"  Target: {requirements['target_compound']}")
    print(f"  Objective: {requirements['objective']}")

    # Generate plan
    try:
        generation_result = generator.generate(
            requirements=requirements,
            templates=[],  # No templates for this example
            few_shot_examples=None
        )

        plan = generation_result.generated_plan
        print(f"  ✓ Plan generated: {plan.title}")
        print(f"  - Materials: {len(plan.materials)} items")
        print(f"  - Procedure: {len(plan.procedure)} steps")
        print(f"  - Safety notes: {len(plan.safety_notes)}")
        print(f"  - Bullets used: {len(generation_result.relevant_bullets)}")

    except Exception as e:
        print(f"  ✗ Generation failed: {e}")
        return

    # Mock feedback (in real system, this would come from evaluation)
    print("\n[6/7] Creating mock feedback...")
    feedback = Feedback(
        scores=[
            FeedbackScore(criterion="completeness", score=0.8, explanation="All required sections present"),
            FeedbackScore(criterion="safety", score=0.7, explanation="Safety notes present but could be more specific"),
            FeedbackScore(criterion="clarity", score=0.9, explanation="Procedure is clear and well-structured"),
            FeedbackScore(criterion="executability", score=0.85, explanation="Steps are detailed and actionable"),
        ],
        overall_score=0.81,
        feedback_source="auto"
    )
    print(f"  Overall score: {feedback.overall_score:.2f}")

    # Reflect on plan
    print("\n[7/7] Running Reflector...")
    try:
        reflection_result = reflector.reflect(
            generated_plan=plan,
            feedback=feedback,
            trajectory=generation_result.trajectory,
            playbook_bullets_used=generation_result.relevant_bullets
        )

        print(f"  ✓ Reflection complete: {len(reflection_result.insights)} insights extracted")
        print(f"  - Bullet tags: {len(reflection_result.bullet_tags)}")
        print(f"  - Refinement rounds: {reflection_result.refinement_rounds}")

        # Print insights
        if reflection_result.insights:
            print("\n  Key Insights:")
            for i, insight in enumerate(reflection_result.insights[:3], 1):
                print(f"    {i}. [{insight.priority}] {insight.type}: {insight.description[:100]}...")

    except Exception as e:
        print(f"  ✗ Reflection failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Update playbook with Curator
    print("\n[8/7] Running Curator...")
    try:
        update_result = curator.update(
            reflection_result=reflection_result,
            id_prefixes=config.playbook.id_prefixes
        )

        print(f"  ✓ Playbook updated")
        print(f"  - Bullets added: {update_result.bullets_added}")
        print(f"  - Bullets updated: {update_result.bullets_updated}")
        print(f"  - Bullets removed: {update_result.bullets_removed}")
        print(f"  - Total changes: {update_result.total_changes}")

        if update_result.deduplication_report:
            print(f"  - Deduplicated: {update_result.deduplication_report.total_deduplicated}")

        print(f"  - Final playbook size: {update_result.updated_playbook.size}")

    except Exception as e:
        print(f"  ✗ Curation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print("\n" + "=" * 80)
    print("ACE Cycle Complete!")
    print("=" * 80)
    print(f"Generated plan: {plan.title}")
    print(f"Feedback score: {feedback.overall_score:.2f}")
    print(f"Insights extracted: {len(reflection_result.insights)}")
    print(f"Playbook updates: {update_result.total_changes} changes")
    print(f"New playbook size: {update_result.updated_playbook.size} bullets")
    print("\nPlaybook will continue to evolve with each generation cycle.")
    print("=" * 80)


if __name__ == "__main__":
    main()
