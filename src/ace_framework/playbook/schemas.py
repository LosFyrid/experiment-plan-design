"""
Pydantic schemas for ACE Framework.

Implements data models from ACE paper (arXiv:2510.04618v1):
- Playbook structures (§3)
- Experiment plan schemas (domain-specific)
- ACE component results (Generator, Reflector, Curator)
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Playbook Structures (ACE Core)
# ============================================================================

class BulletMetadata(BaseModel):
    """
    Metadata for tracking bullet evolution.

    Implements ACE paper §3.2 (Grow-and-Refine):
    - helpful_count: Times bullet was tagged as helpful
    - harmful_count: Times bullet was tagged as harmful
    - neutral_count: Times bullet was neutral
    """
    helpful_count: int = Field(default=0, ge=0)
    harmful_count: int = Field(default=0, ge=0)
    neutral_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    source: str = Field(default="seed")  # "seed", "reflection", "manual"
    embedding: Optional[List[float]] = Field(default=None)  # For deduplication

    @property
    def total_uses(self) -> int:
        """Total number of times this bullet has been used."""
        return self.helpful_count + self.harmful_count + self.neutral_count

    @property
    def helpfulness_score(self) -> float:
        """
        Helpfulness ratio for pruning decisions.

        Returns value in [0, 1] where:
        - 1.0 = always helpful
        - 0.0 = always harmful
        - 0.5 = neutral or unused
        """
        if self.total_uses == 0:
            return 0.5  # Neutral for unused bullets
        return self.helpful_count / self.total_uses


class PlaybookBullet(BaseModel):
    """
    A single bullet in the ACE playbook.

    Implements structured context from ACE paper §3:
    - Section-based organization
    - Unique IDs with section prefixes
    - Metadata for evolution tracking
    """
    id: str = Field(..., description="Unique ID (e.g., 'mat-00001')")
    section: str = Field(..., description="Section category")
    content: str = Field(..., min_length=10, description="Bullet content")
    metadata: BulletMetadata = Field(default_factory=BulletMetadata)

    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure ID follows 'section-NNNNN' format."""
        if '-' not in v:
            raise ValueError(f"ID must contain section prefix: {v}")
        return v


class Playbook(BaseModel):
    """
    Complete ACE playbook structure.

    Implements evolving context from ACE paper §3:
    - Structured bullets organized by section
    - Version tracking for evolution history
    - Metadata for playbook lifecycle
    """
    bullets: List[PlaybookBullet] = Field(default_factory=list)
    sections: List[str] = Field(
        default_factory=lambda: [
            "material_selection",
            "procedure_design",
            "safety_protocols",
            "quality_control",
            "troubleshooting",
            "common_mistakes"
        ]
    )
    version: str = Field(default="1.0.0")
    last_updated: datetime = Field(default_factory=datetime.now)
    total_generations: int = Field(default=0, ge=0)

    def get_bullets_by_section(self, section: str) -> List[PlaybookBullet]:
        """Retrieve all bullets for a specific section."""
        return [b for b in self.bullets if b.section == section]

    def get_bullet_by_id(self, bullet_id: str) -> Optional[PlaybookBullet]:
        """Retrieve specific bullet by ID."""
        for bullet in self.bullets:
            if bullet.id == bullet_id:
                return bullet
        return None

    @property
    def size(self) -> int:
        """Total number of bullets in playbook."""
        return len(self.bullets)


# ============================================================================
# Experiment Plan Schemas (Domain-Specific for Chemistry)
# ============================================================================

class Material(BaseModel):
    """Material specification for experiment plan."""
    name: str = Field(..., min_length=1)
    cas_number: Optional[str] = Field(default=None, description="CAS Registry Number")
    amount: str = Field(..., description="Quantity with unit (e.g., '10g', '5mL')")
    purity: Optional[str] = Field(default=None, description="Required purity (e.g., '≥99%')")
    supplier: Optional[str] = Field(default=None)
    hazard_info: Optional[str] = Field(default=None, description="Safety warnings")


class ProcedureStep(BaseModel):
    """Single step in experiment procedure."""
    step_number: int = Field(..., ge=1)
    description: str = Field(..., min_length=10, description="Detailed action description")
    duration: Optional[str] = Field(default=None, description="Expected time (e.g., '30 min')")
    temperature: Optional[str] = Field(default=None, description="Temperature (e.g., '25°C', 'reflux')")
    notes: Optional[str] = Field(default=None, description="Additional notes or warnings")
    safety_notes: Optional[List[str]] = Field(default=None, description="Safety warnings for this step")
    critical: bool = Field(default=False, description="Whether this is a critical step")


class QCCheck(BaseModel):
    """Quality control checkpoint."""
    check_point: str = Field(..., description="What to check")
    method: str = Field(..., description="How to check (e.g., 'TLC', 'NMR', 'visual')")
    acceptance_criteria: str = Field(..., description="What indicates success")
    timing: str = Field(..., description="When to check (e.g., 'after step 3')")


class ExperimentPlan(BaseModel):
    """
    Complete experiment plan generated by ACE Generator.

    Domain-specific structure for chemistry experiments.
    """
    title: str = Field(..., min_length=5)
    objective: str = Field(..., min_length=20, description="Clear statement of goal")
    materials: List[Material] = Field(..., min_items=1)
    procedure: List[ProcedureStep] = Field(..., min_items=1)
    safety_notes: List[str] = Field(default_factory=list)
    expected_outcome: str = Field(..., min_length=20)
    quality_control: List[QCCheck] = Field(default_factory=list)
    estimated_duration: Optional[str] = Field(default=None, description="Total time estimate")
    difficulty_level: Optional[str] = Field(default=None, description="beginner/intermediate/advanced")
    references: List[str] = Field(default_factory=list, description="Literature or template references")


# ============================================================================
# ACE Component Results (Generator, Reflector, Curator)
# ============================================================================

class TrajectoryStep(BaseModel):
    """
    Single reasoning step in generation trajectory.

    Used by Reflector to analyze generation process (ACE paper §3).
    """
    step_number: int = Field(..., ge=1)
    thought: str = Field(..., description="LLM's reasoning at this step")
    action: Optional[str] = Field(default=None, description="Action taken")
    observation: Optional[str] = Field(default=None, description="Result of action")


class GenerationResult(BaseModel):
    """
    Output from ACE Generator.

    Includes:
    - Generated plan
    - Reasoning trajectory (for Reflector)
    - Bullets used (for tagging)
    """
    generated_plan: ExperimentPlan
    trajectory: List[TrajectoryStep] = Field(default_factory=list)
    relevant_bullets: List[str] = Field(
        default_factory=list,
        description="IDs of playbook bullets used"
    )
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model name, temperature, tokens, etc."
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class BulletTag(str, Enum):
    """
    Bullet tagging categories from ACE Reflector.

    Implements feedback mechanism from ACE paper §3.
    """
    HELPFUL = "helpful"
    HARMFUL = "harmful"
    NEUTRAL = "neutral"


class Insight(BaseModel):
    """
    Actionable insight extracted by Reflector.

    Follows ACE paper §3 reflection structure:
    - Error identification
    - Root cause analysis
    - Correct approach
    """
    type: str = Field(..., description="error_pattern, best_practice, safety_issue, etc.")
    description: str = Field(..., min_length=20)
    suggested_bullet: Optional[str] = Field(
        default=None,
        description="New bullet content to add to playbook"
    )
    target_section: Optional[str] = Field(
        default=None,
        description="Which playbook section this insight belongs to"
    )
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v: Any) -> str:
        """Convert priority to lowercase for case-insensitive validation."""
        if isinstance(v, str):
            return v.lower().strip()
        return v


class ReflectionResult(BaseModel):
    """
    Output from ACE Reflector.

    Implements iterative refinement from ACE paper §3, Figure 4:
    - Insights for Curator
    - Bullet tags for metadata updates
    - Error analysis
    """
    insights: List[Insight] = Field(default_factory=list)
    bullet_tags: Dict[str, BulletTag] = Field(
        default_factory=dict,
        description="Mapping bullet_id -> tag"
    )
    error_analysis: Optional[str] = Field(
        default=None,
        description="Detailed analysis of what went wrong"
    )
    refinement_rounds: int = Field(default=1, ge=1, le=5)
    reflection_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class DeltaOperation(BaseModel):
    """
    Single delta update operation for Curator.

    Implements incremental updates from ACE paper §3.1:
    - Avoids monolithic rewriting
    - Enables fine-grained tracking
    """
    operation: str = Field(..., pattern="^(ADD|UPDATE|REMOVE)$")
    bullet_id: Optional[str] = Field(default=None, description="For UPDATE/REMOVE")
    new_bullet: Optional[PlaybookBullet] = Field(default=None, description="For ADD/UPDATE")
    old_content: Optional[str] = Field(default=None, description="Original content before UPDATE (for rollback)")
    removed_bullet: Optional[PlaybookBullet] = Field(default=None, description="Complete bullet before REMOVE (for rollback)")
    reason: str = Field(..., description="Why this operation is needed")


class DeduplicationReport(BaseModel):
    """
    Report of semantic deduplication results.

    Implements ACE paper §3.2 grow-and-refine mechanism.
    """
    merged_pairs: List[tuple[str, str]] = Field(
        default_factory=list,
        description="Pairs of (kept_id, removed_id)"
    )
    similarity_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Cosine similarities for merged pairs"
    )
    total_deduplicated: int = Field(default=0, ge=0)


class PlaybookUpdateResult(BaseModel):
    """
    Output from ACE Curator.

    Implements delta updates and deduplication from ACE paper §3.1-3.2.
    """
    updated_playbook: Playbook
    delta_operations: List[DeltaOperation] = Field(default_factory=list)
    deduplication_report: Optional[DeduplicationReport] = Field(default=None)
    bullets_added: int = Field(default=0, ge=0)
    bullets_updated: int = Field(default=0, ge=0)
    bullets_removed: int = Field(default=0, ge=0)
    update_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def total_changes(self) -> int:
        """Total number of modifications made."""
        return self.bullets_added + self.bullets_updated + self.bullets_removed


# ============================================================================
# Feedback Schemas (for Evaluation)
# ============================================================================

class FeedbackScore(BaseModel):
    """
    Feedback for a single evaluation criterion.

    Used by evaluation system to provide feedback to Reflector.
    """
    criterion: str = Field(..., description="completeness, safety, clarity, etc.")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score [0, 1]")
    explanation: Optional[str] = Field(default=None, description="Why this score?")


class Feedback(BaseModel):
    """
    Complete feedback for a generated plan.

    Input to Reflector alongside generated plan.
    """
    plan_id: Optional[str] = Field(default=None)
    scores: List[FeedbackScore] = Field(..., min_items=1)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    feedback_source: str = Field(..., pattern="^(auto|llm_judge|human)$")
    comments: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def is_positive(self) -> bool:
        """Whether feedback indicates success (score ≥ 0.7)."""
        return self.overall_score >= 0.7
