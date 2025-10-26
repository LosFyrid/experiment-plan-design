"""
ACE Generator - Generates experiment plans using playbook context.

Implements ACE paper §3 Generator role with:
- Playbook bullet retrieval
- Context-aware plan generation
- Trajectory tracking for Reflector
"""

from typing import List, Dict, Optional, Any
import json
import time
from datetime import datetime

from ace_framework.playbook.schemas import (
    Playbook,
    PlaybookBullet,
    ExperimentPlan,
    GenerationResult,
    TrajectoryStep
)
from ace_framework.playbook.playbook_manager import PlaybookManager
from utils.llm_provider import BaseLLMProvider, parse_json_response, extract_json_from_text
from utils.config_loader import GeneratorConfig
from utils.structured_logger import StructuredLogger, create_generator_logger
from utils.performance_monitor import PerformanceMonitor
from utils.llm_call_tracker import LLMCallTracker
from .prompts import (
    SYSTEM_PROMPT,
    build_generation_prompt,
    extract_bullet_references,
    format_playbook_bullets
)


class PlanGenerator:
    """
    ACE Generator - Creates experiment plans using evolving playbook context.

    Implements the Generator role from ACE paper §3:
    - Retrieves relevant playbook bullets using semantic search
    - Generates structured plans with LLM
    - Tracks reasoning trajectory for Reflector analysis
    """

    def __init__(
        self,
        playbook_manager: PlaybookManager,
        llm_provider: BaseLLMProvider,
        config: GeneratorConfig,
        logger: Optional[StructuredLogger] = None,
        perf_monitor: Optional[PerformanceMonitor] = None,
        llm_tracker: Optional[LLMCallTracker] = None
    ):
        """
        Args:
            playbook_manager: Manager for playbook operations
            llm_provider: LLM provider for generation
            config: Generator configuration
            logger: Optional structured logger (created if None)
            perf_monitor: Optional performance monitor
            llm_tracker: Optional LLM call tracker
        """
        self.playbook_manager = playbook_manager
        self.llm = llm_provider
        self.config = config

        # Observability tools
        self.logger = logger or create_generator_logger()
        self.perf_monitor = perf_monitor
        self.llm_tracker = llm_tracker

    # ========================================================================
    # Main Generation Method
    # ========================================================================

    def generate(
        self,
        requirements: Dict[str, Any],
        templates: Optional[List[Dict]] = None,
        few_shot_examples: Optional[List[Dict]] = None,
        section_filter: Optional[List[str]] = None
    ) -> GenerationResult:
        """
        Generate experiment plan using playbook context.

        Implements ACE Generator from paper §3.

        Args:
            requirements: Structured requirements (from MOSES chatbot)
            templates: Retrieved templates from RAG (optional)
            few_shot_examples: Few-shot examples for in-context learning (optional)
            section_filter: Only retrieve bullets from these sections (optional)

        Returns:
            GenerationResult with plan, trajectory, and bullets used

        Raises:
            ValueError: If playbook not loaded
            RuntimeError: If generation fails
        """
        generation_start_time = time.time()

        # Step 1: Retrieve relevant playbook bullets
        if self.perf_monitor:
            with self.perf_monitor.measure("bullet_retrieval", "generator"):
                relevant_bullets = self._retrieve_bullets(
                    requirements,
                    section_filter=section_filter
                )
        else:
            relevant_bullets = self._retrieve_bullets(
                requirements,
                section_filter=section_filter
            )

        # Log bullet retrieval
        if relevant_bullets:
            similarities = [score for _, score in self.playbook_manager.retrieve_relevant_bullets(
                query=" ".join([requirements.get("objective", ""), requirements.get("target_compound", "")]),
                top_k=len(relevant_bullets)
            )][:5]  # Top 5 similarities

            section_counts = {}
            for bullet in relevant_bullets:
                section_counts[bullet.section] = section_counts.get(bullet.section, 0) + 1

            self.logger.log_bullet_retrieval(
                query=requirements.get("objective", ""),
                bullets_retrieved=len(relevant_bullets),
                top_k=self.config.max_playbook_bullets,
                min_similarity=0.3,
                top_similarities=similarities,
                sections=section_counts
            )

        # Step 2: Build prompt
        if self.perf_monitor:
            with self.perf_monitor.measure("prompt_construction", "generator"):
                user_prompt = build_generation_prompt(
                    requirements=requirements,
                    playbook_bullets=relevant_bullets,
                    templates=templates or [],
                    few_shot_examples=few_shot_examples if self.config.enable_few_shot else None
                )
        else:
            user_prompt = build_generation_prompt(
                requirements=requirements,
                playbook_bullets=relevant_bullets,
                templates=templates or [],
                few_shot_examples=few_shot_examples if self.config.enable_few_shot else None
            )

        # Log prompt construction
        self.logger.log_prompt_constructed(
            prompt_length=len(user_prompt),
            num_bullets=len(relevant_bullets),
            num_templates=len(templates) if templates else 0,
            num_examples=len(few_shot_examples) if few_shot_examples else 0
        )

        # Step 3: Generate with LLM
        self.logger.log_llm_call_started(
            model=self.llm.model_name if hasattr(self.llm, 'model_name') else "unknown",
            config={
                "temperature": getattr(self.llm, 'temperature', None),
                "max_tokens": getattr(self.llm, 'max_tokens', None)
            }
        )

        # Track LLM call
        llm_call_id = None
        if self.llm_tracker:
            llm_call_id = self.llm_tracker.start_call(
                model_provider=getattr(self.llm, 'provider', 'unknown'),
                model_name=getattr(self.llm, 'model_name', 'unknown'),
                config={
                    "temperature": getattr(self.llm, 'temperature', 0.7),
                    "max_tokens": getattr(self.llm, 'max_tokens', 4000)
                },
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                stage="generation"
            )

        try:
            if self.perf_monitor:
                with self.perf_monitor.measure("llm_call", "generator"):
                    response = self.llm.generate(
                        prompt=user_prompt,
                        system_prompt=SYSTEM_PROMPT
                    )
            else:
                response = self.llm.generate(
                    prompt=user_prompt,
                    system_prompt=SYSTEM_PROMPT
                )

            # Complete LLM call tracking
            if self.llm_tracker and llm_call_id:
                self.llm_tracker.end_call(
                    response=response.content,
                    input_tokens=response.prompt_tokens,
                    output_tokens=response.completion_tokens,
                    status="success"
                )

            # Record tokens in perf monitor
            if self.perf_monitor:
                self.perf_monitor.record_tokens(
                    component="generator",
                    input_tokens=response.prompt_tokens,
                    output_tokens=response.completion_tokens,
                    call_id=llm_call_id
                )

            # Log LLM call completion
            llm_duration = time.time() - generation_start_time
            self.logger.log_llm_call_completed(
                duration=llm_duration,
                tokens={
                    "input": response.prompt_tokens,
                    "output": response.completion_tokens,
                    "total": response.total_tokens
                },
                llm_call_id=llm_call_id or "unknown"
            )

        except Exception as e:
            # Log error
            if self.llm_tracker and llm_call_id:
                self.llm_tracker.end_call(
                    response="",
                    status="error",
                    error=str(e)
                )
            raise RuntimeError(f"LLM generation failed: {e}")

        # Step 4: Parse response
        if self.perf_monitor:
            with self.perf_monitor.measure("output_parsing", "generator"):
                parsed_output = self._parse_generation_output(response.content)
        else:
            parsed_output = self._parse_generation_output(response.content)

        # Step 5: Extract components
        plan_data = parsed_output.get("plan", {})
        reasoning_data = parsed_output.get("reasoning", {})

        # Step 6: Create ExperimentPlan
        try:
            experiment_plan = ExperimentPlan(**plan_data)

            # Log successful parsing
            self.logger.log_output_parsed(
                success=True,
                plan_title=experiment_plan.title,
                materials_count=len(experiment_plan.materials),
                procedure_steps=len(experiment_plan.procedure)
            )

        except Exception as e:
            # Log parsing failure
            self.logger.log_output_parsed(
                success=False,
                error=str(e)
            )
            raise ValueError(f"Failed to parse experiment plan: {e}\nPlan data: {plan_data}")

        # Step 7: Extract trajectory
        trajectory = self._parse_trajectory(reasoning_data.get("trajectory", []))

        # Step 8: Extract bullet references
        bullets_used_from_output = reasoning_data.get("bullets_used", [])
        bullets_used_from_text = extract_bullet_references(response.content)
        bullets_used = list(set(bullets_used_from_output + bullets_used_from_text))

        # Step 9: Create result
        total_duration = time.time() - generation_start_time

        generation_result = GenerationResult(
            generated_plan=experiment_plan,
            trajectory=trajectory,
            relevant_bullets=bullets_used,
            generation_metadata={
                "model": response.model,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
                "retrieved_bullets_count": len(relevant_bullets),
                "retrieved_bullet_ids": [b.id for b in relevant_bullets],
                "templates_retrieved": [
                    {
                        "title": t.get("title", ""),
                        "score": t.get("score", 0),
                        "content_preview": t.get("content", "")[:100]
                    }
                    for t in templates
                ] if templates else [],
                "duration": total_duration
            },
            timestamp=datetime.now()
        )

        # Log plan generation completion
        self.logger.log_plan_generated(
            total_duration=total_duration,
            bullets_used=bullets_used
        )

        # Step 10: Update playbook statistics
        if self.playbook_manager.playbook:
            self.playbook_manager.playbook.total_generations += 1

        return generation_result

    # ========================================================================
    # Bullet Retrieval
    # ========================================================================

    def _retrieve_bullets(
        self,
        requirements: Dict[str, Any],
        section_filter: Optional[List[str]] = None
    ) -> List[PlaybookBullet]:
        """
        Retrieve relevant playbook bullets using semantic search.

        Args:
            requirements: Structured requirements
            section_filter: Only retrieve from these sections

        Returns:
            List of relevant PlaybookBullet objects
        """
        # Build query from requirements
        query_parts = []

        if "objective" in requirements:
            query_parts.append(requirements["objective"])

        if "target_compound" in requirements:
            query_parts.append(f"Target: {requirements['target_compound']}")

        if "constraints" in requirements and requirements["constraints"]:
            query_parts.append("Constraints: " + ", ".join(requirements["constraints"]))

        query = " ".join(query_parts)

        # Retrieve bullets
        retrieved = self.playbook_manager.retrieve_relevant_bullets(
            query=query,
            top_k=self.config.max_playbook_bullets,
            section_filter=section_filter,
            min_similarity=0.3
        )

        # Extract bullets (discard scores)
        return [bullet for bullet, _ in retrieved]

    # ========================================================================
    # Output Parsing
    # ========================================================================

    def _parse_generation_output(self, content: str) -> Dict:
        """
        Parse LLM output to extract plan and reasoning.

        Handles both direct JSON and JSON embedded in text.

        Args:
            content: LLM response content

        Returns:
            Dict with "plan" and "reasoning" keys

        Raises:
            ValueError: If parsing fails
        """
        # Try direct JSON parse first
        content_stripped = content.strip()

        # Remove markdown code blocks
        if content_stripped.startswith("```json"):
            content_stripped = content_stripped[7:]
        elif content_stripped.startswith("```"):
            content_stripped = content_stripped[3:]

        if content_stripped.endswith("```"):
            content_stripped = content_stripped[:-3]

        content_stripped = content_stripped.strip()

        # Try parsing
        try:
            parsed = json.loads(content_stripped)
            return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from mixed text
        extracted = extract_json_from_text(content)
        if extracted:
            return extracted

        raise ValueError(f"Failed to parse generation output as JSON.\nContent: {content[:500]}...")

    def _parse_trajectory(self, trajectory_data: List[Dict]) -> List[TrajectoryStep]:
        """
        Parse trajectory data into TrajectoryStep objects.

        Args:
            trajectory_data: List of trajectory step dicts

        Returns:
            List of TrajectoryStep objects
        """
        trajectory = []

        for i, step_data in enumerate(trajectory_data, 1):
            try:
                step = TrajectoryStep(
                    step_number=step_data.get("step_number", i),
                    thought=step_data.get("thought", ""),
                    action=step_data.get("action"),
                    observation=step_data.get("observation")
                )
                trajectory.append(step)
            except Exception as e:
                # Skip invalid steps
                print(f"Warning: Failed to parse trajectory step {i}: {e}")
                continue

        return trajectory

    # ========================================================================
    # Utilities
    # ========================================================================

    def get_playbook_summary(self) -> Dict[str, Any]:
        """
        Get summary of current playbook state.

        Returns:
            Dict with playbook statistics
        """
        return self.playbook_manager.get_statistics()

    def preview_retrieved_bullets(
        self,
        requirements: Dict[str, Any],
        top_k: int = 10
    ) -> List[tuple[str, str, float]]:
        """
        Preview which bullets would be retrieved for given requirements.

        Useful for debugging and understanding retrieval.

        Args:
            requirements: Structured requirements
            top_k: Number of bullets to show

        Returns:
            List of (bullet_id, content, similarity_score) tuples
        """
        # Build query
        query_parts = []
        if "objective" in requirements:
            query_parts.append(requirements["objective"])
        if "target_compound" in requirements:
            query_parts.append(requirements["target_compound"])

        query = " ".join(query_parts)

        # Retrieve
        retrieved = self.playbook_manager.retrieve_relevant_bullets(
            query=query,
            top_k=top_k
        )

        # Format results
        return [
            (bullet.id, bullet.content, score)
            for bullet, score in retrieved
        ]


# ============================================================================
# Factory Function
# ============================================================================

def create_generator(
    playbook_path: str,
    llm_provider: BaseLLMProvider,
    config: Optional[GeneratorConfig] = None,
    embedding_model: str = "text-embedding-v4"
) -> PlanGenerator:
    """
    Factory function to create PlanGenerator.

    Args:
        playbook_path: Path to playbook JSON
        llm_provider: LLM provider instance
        config: Generator configuration (uses default if None)
        embedding_model: Model for bullet retrieval

    Returns:
        Configured PlanGenerator instance
    """
    from utils.config_loader import get_ace_config

    if config is None:
        config = get_ace_config().generator

    playbook_manager = PlaybookManager(
        playbook_path=playbook_path,
        embedding_model=embedding_model
    )

    # Try to load existing playbook, or create empty one
    try:
        playbook_manager.load()
    except FileNotFoundError:
        playbook_manager.get_or_create()

    return PlanGenerator(
        playbook_manager=playbook_manager,
        llm_provider=llm_provider,
        config=config
    )
