"""
ACE Curator - Maintains playbook through incremental delta updates.

Implements ACE paper §3.1-3.2:
- §3.1: Incremental Delta Updates (avoids context collapse)
- §3.2: Grow-and-Refine mechanism (semantic deduplication + pruning)

Key innovations:
1. Delta-based updates (not monolithic rewriting)
2. Semantic deduplication using embeddings
3. Metadata-driven pruning based on helpfulness scores
"""

from typing import List, Dict, Optional, Tuple
import json
import time
from datetime import datetime
from collections import defaultdict

from ace_framework.playbook.schemas import (
    Playbook,
    PlaybookBullet,
    BulletMetadata,
    BulletTag,
    Insight,
    ReflectionResult,
    DeltaOperation,
    PlaybookUpdateResult,
    DeduplicationReport
)
from ace_framework.playbook.playbook_manager import PlaybookManager
from utils.llm_provider import BaseLLMProvider, extract_json_from_text
from utils.config_loader import CuratorConfig
from utils.structured_logger import StructuredLogger, create_curator_logger
from utils.performance_monitor import PerformanceMonitor
from utils.llm_call_tracker import LLMCallTracker
from utils.embedding_utils import (
    EmbeddingManager,
    deduplicate_with_quality_scores
)
from .prompts import (
    CURATOR_SYSTEM_PROMPT,
    build_curation_prompt,
    build_pruning_prompt
)


class PlaybookCurator:
    """
    ACE Curator - Maintains playbook through incremental updates.

    Implements:
    - Incremental delta updates (ACE §3.1)
    - Semantic deduplication (ACE §3.2)
    - Grow-and-refine pruning (ACE §3.2)
    """

    def __init__(
        self,
        playbook_manager: PlaybookManager,
        llm_provider: BaseLLMProvider,
        config: CuratorConfig,
        embedding_manager: Optional[EmbeddingManager] = None,
        logger: Optional[StructuredLogger] = None,
        perf_monitor: Optional[PerformanceMonitor] = None,
        llm_tracker: Optional[LLMCallTracker] = None
    ):
        """
        Args:
            playbook_manager: Manager for playbook operations
            llm_provider: LLM provider for curation decisions
            config: Curator configuration
            embedding_manager: Manager for semantic similarity (deduplication)
            logger: Optional structured logger (created if None)
            perf_monitor: Optional performance monitor
            llm_tracker: Optional LLM call tracker
        """
        self.playbook_manager = playbook_manager
        self.llm = llm_provider
        self.config = config

        # Embedding manager for deduplication
        if embedding_manager is None:
            embedding_manager = EmbeddingManager()
        self.embedding_manager = embedding_manager

        # Observability tools
        self.logger = logger or create_curator_logger()
        self.perf_monitor = perf_monitor
        self.llm_tracker = llm_tracker

    # ========================================================================
    # Main Update Method
    # ========================================================================

    def update(
        self,
        reflection_result: ReflectionResult,
        id_prefixes: Optional[Dict[str, str]] = None
    ) -> PlaybookUpdateResult:
        """
        Update playbook based on reflection insights.

        Implements ACE Curator from paper §3.1-3.2.

        Args:
            reflection_result: Result from Reflector with insights and bullet tags
            id_prefixes: Section name -> ID prefix mapping (from config)

        Returns:
            PlaybookUpdateResult with updated playbook and delta operations

        Raises:
            ValueError: If playbook not loaded
            RuntimeError: If curation fails
        """
        if self.playbook_manager.playbook is None:
            raise ValueError("No playbook loaded")

        curation_start_time = time.time()
        size_before = self.playbook_manager.playbook.size

        # Log curation start
        self.logger.log_curation_started(
            insights_count=len(reflection_result.insights),
            current_playbook_size=size_before
        )

        # Step 1: Update bullet metadata based on tags
        self._update_bullet_metadata(reflection_result.bullet_tags)

        # Step 2: Load id_prefixes from config if not provided
        if id_prefixes is None:
            from utils.config_loader import get_ace_config
            ace_config = get_ace_config()
            id_prefixes = ace_config.playbook.id_prefixes

        # Step 3: Generate delta operations from insights
        if self.perf_monitor:
            with self.perf_monitor.measure("delta_generation", "curator"):
                delta_start = time.time()
                delta_operations = self._generate_delta_operations(
                    insights=reflection_result.insights,
                    id_prefixes=id_prefixes
                )
                delta_duration = time.time() - delta_start
        else:
            delta_start = time.time()
            delta_operations = self._generate_delta_operations(
                insights=reflection_result.insights,
                id_prefixes=id_prefixes
            )
            delta_duration = time.time() - delta_start

        # Log delta operations generated
        op_counts = {"ADD": 0, "UPDATE": 0, "REMOVE": 0}
        for op in delta_operations:
            op_counts[op.operation] = op_counts.get(op.operation, 0) + 1

        self.logger.log_delta_operations_generated(
            duration=delta_duration,
            operations=op_counts
        )

        # Step 4: Apply delta operations
        if self.perf_monitor:
            with self.perf_monitor.measure("operations_apply", "curator"):
                self._apply_delta_operations(delta_operations)
        else:
            self._apply_delta_operations(delta_operations)

        # Step 5: Deduplication (if enabled)
        dedup_report = None
        if self.config.enable_grow_and_refine:
            if self.perf_monitor:
                with self.perf_monitor.measure("deduplication", "curator"):
                    dedup_report = self._perform_deduplication()
            else:
                dedup_report = self._perform_deduplication()

        # Step 6: Pruning (if size exceeded)
        if self.playbook_manager.playbook.size > self.config.max_playbook_size:
            if self.config.prune_harmful_bullets:
                if self.perf_monitor:
                    with self.perf_monitor.measure("pruning", "curator"):
                        self._perform_pruning()
                else:
                    self._perform_pruning()

        # Step 7: Save updated playbook
        if self.perf_monitor:
            with self.perf_monitor.measure("playbook_save", "curator"):
                self.playbook_manager.save()
        else:
            self.playbook_manager.save()

        # Step 8: Create result
        bullets_added = sum(1 for op in delta_operations if op.operation == "ADD")
        bullets_updated = sum(1 for op in delta_operations if op.operation == "UPDATE")
        bullets_removed = sum(1 for op in delta_operations if op.operation == "REMOVE")

        size_after = self.playbook_manager.playbook.size
        total_duration = time.time() - curation_start_time

        result = PlaybookUpdateResult(
            updated_playbook=self.playbook_manager.playbook,
            delta_operations=delta_operations,
            deduplication_report=dedup_report,
            bullets_added=bullets_added,
            bullets_updated=bullets_updated,
            bullets_removed=bullets_removed,
            update_metadata={
                "model": self.llm.model_name if hasattr(self.llm, 'model_name') else "unknown",
                "insights_processed": len(reflection_result.insights),
                "bullet_tags_processed": len(reflection_result.bullet_tags),
                "final_playbook_size": size_after,
                "duration": total_duration
            },
            timestamp=datetime.now()
        )

        # Log playbook update completion
        self.logger.log_playbook_updated(
            total_duration=total_duration,
            size_before=size_before,
            size_after=size_after,
            changes={
                "added": bullets_added,
                "updated": bullets_updated,
                "removed": bullets_removed
            },
            new_version="v_unknown"  # Will be set by version tracker
        )

        return result

    # ========================================================================
    # Metadata Updates
    # ========================================================================

    def _update_bullet_metadata(self, bullet_tags: Dict[str, BulletTag]) -> None:
        """
        Update bullet metadata based on Reflector tags.

        Args:
            bullet_tags: Mapping of bullet_id -> tag
        """
        updated_count = self.playbook_manager.update_bullet_tags(bullet_tags)
        print(f"Updated metadata for {updated_count} bullets")

    # ========================================================================
    # Delta Operations Generation
    # ========================================================================

    def _generate_delta_operations(
        self,
        insights: List[Insight],
        id_prefixes: Dict[str, str]
    ) -> List[DeltaOperation]:
        """
        Generate delta operations from insights using LLM.

        Implements ACE §3.1 incremental updates.

        Args:
            insights: Insights from Reflector
            id_prefixes: Section -> prefix mapping

        Returns:
            List of DeltaOperation objects
        """
        if not insights:
            return []

        # Get current playbook state organized by section
        current_section_bullets = self._get_bullets_by_section()

        # Build prompt
        prompt = build_curation_prompt(
            insights=insights,
            current_section_bullets=current_section_bullets,
            id_prefixes=id_prefixes,
            max_playbook_size=self.config.max_playbook_size,
            current_size=self.playbook_manager.playbook.size
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
                system_prompt=CURATOR_SYSTEM_PROMPT,
                user_prompt=prompt,
                stage="curation"
            )

        # Generate delta operations with LLM
        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=CURATOR_SYSTEM_PROMPT
            )

            # Complete LLM call tracking
            if self.llm_tracker and llm_call_id:
                self.llm_tracker.end_call(
                    response=response.content,
                    input_tokens=getattr(response, 'prompt_tokens', None),
                    output_tokens=getattr(response, 'completion_tokens', None),
                    status="success"
                )

            # Record tokens
            if self.perf_monitor and hasattr(response, 'prompt_tokens'):
                self.perf_monitor.record_tokens(
                    component="curator",
                    input_tokens=response.prompt_tokens,
                    output_tokens=response.completion_tokens,
                    call_id=llm_call_id
                )

        except Exception as e:
            if self.llm_tracker and llm_call_id:
                self.llm_tracker.end_call(response="", status="error", error=str(e))
            raise RuntimeError(f"Delta operation generation failed: {e}")

        # Parse operations
        parsed = self._parse_curator_output(response.content)
        operations_data = parsed.get("delta_operations", [])

        # Convert to DeltaOperation objects
        delta_operations = []
        # Get valid sections from config
        valid_sections = set(id_prefixes.keys())

        for op_data in operations_data:
            try:
                # Parse new_bullet if present
                new_bullet = None
                if op_data.get("new_bullet"):
                    bullet_data = op_data["new_bullet"]
                    section = bullet_data["section"]
                    content = bullet_data["content"]

                    # ✅ FIX: Validate section
                    if section not in valid_sections:
                        # Map invalid sections to closest valid one
                        section_mapping = {
                            "waste_disposal": "safety_protocols",
                            "reaction_conditions": "procedure_design",
                            "cost_optimization": "procedure_design",
                            "equipment": "material_selection"
                        }
                        original_section = section
                        section = section_mapping.get(section, "safety_protocols")  # Default to safety
                        print(f"Warning: Invalid section '{original_section}' mapped to '{section}'")

                    # Generate ID if adding new bullet
                    if op_data["operation"] == "ADD":
                        prefix = id_prefixes.get(section, "unk")
                        bullet_id = self.playbook_manager._generate_bullet_id(section, prefix)
                    else:
                        bullet_id = op_data.get("bullet_id")

                    new_bullet = PlaybookBullet(
                        id=bullet_id,
                        section=section,
                        content=content,
                        metadata=BulletMetadata(source="reflection")
                    )

                operation = DeltaOperation(
                    operation=op_data["operation"],
                    bullet_id=op_data.get("bullet_id"),
                    new_bullet=new_bullet,
                    reason=op_data.get("reason", "")
                )
                delta_operations.append(operation)

            except Exception as e:
                print(f"Warning: Failed to parse delta operation: {e}")
                continue

        return delta_operations

    def _get_bullets_by_section(self) -> Dict[str, List[PlaybookBullet]]:
        """Get current bullets organized by section."""
        bullets_by_section = defaultdict(list)

        for bullet in self.playbook_manager.playbook.bullets:
            bullets_by_section[bullet.section].append(bullet)

        return dict(bullets_by_section)

    # ========================================================================
    # Delta Operations Application
    # ========================================================================

    def _apply_delta_operations(self, operations: List[DeltaOperation]) -> None:
        """
        Apply delta operations to playbook.

        Args:
            operations: List of DeltaOperation objects
        """
        for op in operations:
            try:
                if op.operation == "ADD":
                    self._apply_add_operation(op)
                elif op.operation == "UPDATE":
                    self._apply_update_operation(op)
                elif op.operation == "REMOVE":
                    self._apply_remove_operation(op)
                else:
                    print(f"Warning: Unknown operation type: {op.operation}")

            except Exception as e:
                print(f"Warning: Failed to apply operation {op.operation}: {e}")
                continue

    def _apply_add_operation(self, operation: DeltaOperation) -> None:
        """Add new bullet to playbook."""
        if operation.new_bullet is None:
            print("Warning: ADD operation missing new_bullet")
            return

        # Check for semantic duplicates before adding
        duplicate_info = {"is_duplicate": False}
        if self._is_duplicate(operation.new_bullet):
            print(f"Skipping ADD: Bullet is semantically duplicate")
            duplicate_info["is_duplicate"] = True
            # Log skipped operation
            self.logger.log_operation_applied(
                operation="ADD",
                bullet_id=operation.new_bullet.id,
                section=operation.new_bullet.section,
                reason="Skipped: semantic duplicate",
                duplicate_check=duplicate_info
            )
            return

        # Add bullet using manager (handles embedding)
        self.playbook_manager.playbook.bullets.append(operation.new_bullet)

        # Update embeddings cache
        embedding = self.playbook_manager._get_embedding(operation.new_bullet.content)
        operation.new_bullet.metadata.embedding = embedding.tolist()
        self.playbook_manager._embeddings_cache[operation.new_bullet.id] = embedding

        print(f"Added bullet: {operation.new_bullet.id}")

        # Log successful addition
        self.logger.log_operation_applied(
            operation="ADD",
            bullet_id=operation.new_bullet.id,
            section=operation.new_bullet.section,
            reason=operation.reason,
            duplicate_check=duplicate_info
        )

    def _apply_update_operation(self, operation: DeltaOperation) -> None:
        """Update existing bullet."""
        if operation.bullet_id is None or operation.new_bullet is None:
            print("Warning: UPDATE operation missing bullet_id or new_bullet")
            return

        # Check if bullet exists
        bullet = self.playbook_manager.playbook.get_bullet_by_id(operation.bullet_id)
        if bullet is None:
            print(f"Warning: Bullet {operation.bullet_id} not found for UPDATE")
            return

        # Update content
        self.playbook_manager.update_bullet(
            bullet_id=operation.bullet_id,
            new_content=operation.new_bullet.content
        )

        print(f"Updated bullet: {operation.bullet_id}")

        # Log successful update
        self.logger.log_operation_applied(
            operation="UPDATE",
            bullet_id=operation.bullet_id,
            reason=operation.reason,
            content_changed=True
        )

    def _apply_remove_operation(self, operation: DeltaOperation) -> None:
        """Remove bullet from playbook."""
        if operation.bullet_id is None:
            print("Warning: REMOVE operation missing bullet_id")
            return

        removed = self.playbook_manager.remove_bullet(operation.bullet_id)
        if removed:
            print(f"Removed bullet: {operation.bullet_id}")

            # Log successful removal
            self.logger.log_operation_applied(
                operation="REMOVE",
                bullet_id=operation.bullet_id,
                reason=operation.reason
            )
        else:
            print(f"Warning: Bullet {operation.bullet_id} not found for REMOVE")

    # ========================================================================
    # Deduplication (ACE §3.2)
    # ========================================================================

    def _is_duplicate(self, new_bullet: PlaybookBullet) -> bool:
        """
        Check if new bullet is semantically duplicate of existing bullets.

        Args:
            new_bullet: Candidate bullet

        Returns:
            True if duplicate, False otherwise
        """
        # Get bullets in same section
        section_bullets = self.playbook_manager.playbook.get_bullets_by_section(
            new_bullet.section
        )

        if not section_bullets:
            return False

        # Get embedding for new bullet
        new_embedding = self.embedding_manager.encode([new_bullet.content])[0]

        # Compare with existing bullets
        for existing in section_bullets:
            existing_embedding = self.playbook_manager._embeddings_cache.get(
                existing.id,
                self.embedding_manager.encode([existing.content])[0]
            )

            similarity = self.embedding_manager.compute_similarity(
                new_embedding,
                existing_embedding
            )

            if similarity >= self.config.deduplication_threshold:
                print(f"Duplicate detected: {new_bullet.id} similar to {existing.id} (sim={similarity:.3f})")
                return True

        return False

    def _perform_deduplication(self) -> DeduplicationReport:
        """
        Perform semantic deduplication across all sections.

        Implements Grow-and-Refine from ACE §3.2.

        Returns:
            DeduplicationReport with merge information
        """
        dedup_start_time = time.time()
        merged_pairs = []
        similarity_scores = {}
        total_removed = 0

        # Count total candidate bullets
        total_candidates = sum(
            len(self.playbook_manager.playbook.get_bullets_by_section(section))
            for section in self.playbook_manager.playbook.sections
        )

        # Log deduplication start
        self.logger.log_deduplication_started(
            threshold=self.config.deduplication_threshold,
            candidates_count=total_candidates
        )

        # Deduplicate within each section
        for section in self.playbook_manager.playbook.sections:
            section_bullets = self.playbook_manager.playbook.get_bullets_by_section(section)

            if len(section_bullets) < 2:
                continue

            # Get embeddings
            embeddings = []
            for bullet in section_bullets:
                emb = self.playbook_manager._embeddings_cache.get(
                    bullet.id,
                    self.embedding_manager.encode([bullet.content])[0]
                )
                embeddings.append(emb)

            embeddings_array = self.embedding_manager.encode(
                [b.content for b in section_bullets]
            )

            # Get quality scores (helpfulness)
            quality_scores = [b.metadata.helpfulness_score for b in section_bullets]

            # Find duplicates
            keep_indices, merge_map = deduplicate_with_quality_scores(
                items=[b.content for b in section_bullets],
                embeddings=embeddings_array,
                quality_scores=quality_scores,
                threshold=self.config.deduplication_threshold
            )

            # Apply deduplication
            for kept_idx, removed_indices in merge_map.items():
                kept_bullet = section_bullets[kept_idx]

                for removed_idx in removed_indices:
                    removed_bullet = section_bullets[removed_idx]

                    # Compute similarity for report
                    sim = self.embedding_manager.compute_similarity(
                        embeddings_array[kept_idx],
                        embeddings_array[removed_idx]
                    )

                    merged_pairs.append((kept_bullet.id, removed_bullet.id))
                    similarity_scores[f"{kept_bullet.id}->{removed_bullet.id}"] = sim

                    # Remove duplicate
                    self.playbook_manager.remove_bullet(removed_bullet.id)
                    total_removed += 1

                    print(f"Deduplicated: Kept {kept_bullet.id}, removed {removed_bullet.id} (sim={sim:.3f})")

        # Log deduplication completion
        dedup_duration = time.time() - dedup_start_time
        self.logger.log_deduplication_completed(
            duration=dedup_duration,
            duplicates_found=total_removed,
            merges=[f"{kept}->{removed}" for kept, removed in merged_pairs]
        )

        return DeduplicationReport(
            merged_pairs=merged_pairs,
            similarity_scores=similarity_scores,
            total_deduplicated=total_removed
        )

    # ========================================================================
    # Pruning (ACE §3.2)
    # ========================================================================

    def _perform_pruning(self) -> None:
        """
        Prune low-quality bullets when playbook exceeds max size.

        Implements Grow-and-Refine from ACE §3.2.
        """
        pruning_start_time = time.time()
        current_size = self.playbook_manager.playbook.size
        max_size = self.config.max_playbook_size

        if current_size <= max_size:
            return

        print(f"Playbook size ({current_size}) exceeds max ({max_size}). Pruning...")

        # Log pruning start
        self.logger.log_pruning_started(
            current_size=current_size,
            max_size=max_size,
            threshold=0.3  # Helpfulness threshold used for pruning
        )

        # Find bullets with low helpfulness scores
        low_quality_bullets = [
            b for b in self.playbook_manager.playbook.bullets
            if b.metadata.helpfulness_score < 0.3 and b.metadata.total_uses >= 3
        ]

        # Sort by helpfulness score (lowest first)
        low_quality_bullets.sort(key=lambda b: b.metadata.helpfulness_score)

        # Remove bullets until under size limit
        bullets_to_remove = current_size - max_size
        removed_count = 0

        for bullet in low_quality_bullets:
            if removed_count >= bullets_to_remove:
                break

            self.playbook_manager.remove_bullet(bullet.id)
            print(f"Pruned: {bullet.id} (helpfulness={bullet.metadata.helpfulness_score:.2f})")
            removed_count += 1

        if removed_count < bullets_to_remove:
            print(f"Warning: Only removed {removed_count}/{bullets_to_remove} bullets")

        # Log pruning completion
        pruning_duration = time.time() - pruning_start_time
        self.logger.log_pruning_completed(
            duration=pruning_duration,
            bullets_removed=removed_count
        )

    # ========================================================================
    # Parsing
    # ========================================================================

    def _parse_curator_output(self, content: str) -> Dict:
        """
        Parse Curator LLM output.

        Args:
            content: LLM response content

        Returns:
            Parsed dict with delta_operations

        Raises:
            ValueError: If parsing fails
        """
        # Remove markdown
        content_stripped = content.strip()

        if content_stripped.startswith("```json"):
            content_stripped = content_stripped[7:]
        elif content_stripped.startswith("```"):
            content_stripped = content_stripped[3:]

        if content_stripped.endswith("```"):
            content_stripped = content_stripped[:-3]

        content_stripped = content_stripped.strip()

        # Parse
        try:
            return json.loads(content_stripped)
        except json.JSONDecodeError:
            pass

        # Try extraction
        extracted = extract_json_from_text(content)
        if extracted:
            return extracted

        raise ValueError(f"Failed to parse curator output.\nContent: {content[:500]}...")


# ============================================================================
# Factory Function
# ============================================================================

def create_curator(
    playbook_manager: PlaybookManager,
    llm_provider: BaseLLMProvider,
    config: Optional[CuratorConfig] = None,
    embedding_manager: Optional[EmbeddingManager] = None
) -> PlaybookCurator:
    """
    Factory function to create PlaybookCurator.

    Args:
        playbook_manager: Playbook manager instance
        llm_provider: LLM provider instance
        config: Curator configuration (uses default if None)
        embedding_manager: Embedding manager for deduplication (creates if None)

    Returns:
        Configured PlaybookCurator instance
    """
    from utils.config_loader import get_ace_config

    if config is None:
        config = get_ace_config().curator

    if embedding_manager is None:
        embedding_manager = EmbeddingManager()

    return PlaybookCurator(
        playbook_manager=playbook_manager,
        llm_provider=llm_provider,
        config=config,
        embedding_manager=embedding_manager
    )
