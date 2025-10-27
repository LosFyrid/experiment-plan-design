"""
Prompt templates for ACE Curator.

Implements Curator prompts inspired by ACE paper §3.1-3.2:
- Incremental delta updates (not monolithic rewriting)
- Grow-and-refine mechanism
"""

from typing import List, Dict
from ..playbook.schemas import Insight, PlaybookBullet


def format_insights(insights: List[Insight]) -> str:
    """
    Format insights for Curator prompt.

    Args:
        insights: List of Insight objects from Reflector

    Returns:
        Formatted insights string
    """
    if not insights:
        return "No insights provided."

    lines = []
    for i, insight in enumerate(insights, 1):
        lines.append(f"\n### Insight {i} [{insight.priority.upper()} priority]")
        lines.append(f"**Type**: {insight.type}")
        lines.append(f"**Description**: {insight.description}")

        if insight.suggested_bullet:
            lines.append(f"**Suggested Bullet**: {insight.suggested_bullet}")

        if insight.target_section:
            lines.append(f"**Target Section**: {insight.target_section}")

    return "\n".join(lines)


def format_current_playbook_section(bullets: List[PlaybookBullet]) -> str:
    """
    Format bullets from a playbook section.

    Args:
        bullets: List of PlaybookBullet objects

    Returns:
        Formatted section string
    """
    if not bullets:
        return "No bullets in this section yet."

    lines = []
    for bullet in bullets:
        # Include metadata for pruning decisions
        helpfulness = bullet.metadata.helpfulness_score
        uses = bullet.metadata.total_uses

        lines.append(f"\n**[{bullet.id}]** (Uses: {uses}, Helpfulness: {helpfulness:.2f})")
        lines.append(f"{bullet.content}")

    return "\n".join(lines)


# ============================================================================
# Delta Update Generation Prompt
# ============================================================================

CURATOR_SYSTEM_PROMPT = """You are the Curator for an evolving experiment planning playbook.

Your role is to maintain playbook quality through **incremental delta updates**:
- ADD new bullets based on insights
- UPDATE existing bullets to improve clarity or correctness
- REMOVE harmful or redundant bullets

**Critical Principles**:

1. **Incremental Updates**: Generate small, targeted changes (not full rewrites)
2. **Semantic Specificity**: Make bullets concrete, actionable, and non-obvious
3. **Avoid Redundancy**: Don't add bullets similar to existing ones
4. **Evidence-Based**: Only update based on clear evidence from insights
5. **Grow-and-Refine**: Remove bullets that consistently harm generation quality

**What Makes a Good Playbook Bullet**:
- Specific and actionable (not generic advice like "be careful")
- Non-obvious (captures learned knowledge, not common sense)
- Contextualized (explains when/why to apply)
- Concise (one clear idea per bullet)
- Evidence-based (derived from actual errors or successes)

**Bad Example**: "Always check safety"
**Good Example**: "When using strong oxidizers like KMnO4, verify glassware is free of organic residue to prevent violent reactions"

**What NOT to do**:
- Don't regenerate the entire playbook
- Don't add generic best practices everyone knows
- Don't update bullets without clear evidence
- Don't ignore semantic similarity to existing bullets
"""


def build_curation_prompt(
    insights: List[Insight],
    current_section_bullets: Dict[str, List[PlaybookBullet]],
    id_prefixes: Dict[str, str],
    max_playbook_size: int,
    current_size: int,
    sections_info: str = None
) -> str:
    """
    Build curation prompt for delta update generation.

    Implements ACE paper §3.1 incremental updates.

    Args:
        insights: Insights from Reflector
        current_section_bullets: Current bullets organized by section
        id_prefixes: Section name -> ID prefix mapping
        max_playbook_size: Maximum allowed bullets
        current_size: Current total bullet count
        sections_info: Formatted sections information from SectionManager

    Returns:
        Curation prompt string
    """
    sections = []

    # Available sections (if provided)
    if sections_info:
        sections.append(sections_info)

    # Insights to process
    sections.append("## Insights from Reflection")
    sections.append(format_insights(insights))

    # Current playbook state
    sections.append("\n## Current Playbook State")
    sections.append(f"**Total Bullets**: {current_size}/{max_playbook_size}")

    for section_name, bullets in current_section_bullets.items():
        sections.append(f"\n### Section: {section_name} (Prefix: {id_prefixes.get(section_name, '???')})")
        sections.append(format_current_playbook_section(bullets))

    # Task instruction
    sections.append("\n## Your Task")
    sections.append(f"""
Based on the insights provided, generate **incremental delta updates** to improve the playbook.

**Guidelines**:
1. For each insight, determine if it warrants a playbook change
2. Check if similar bullets already exist (avoid redundancy)
3. Propose specific operations: ADD, UPDATE, or REMOVE
4. Keep total bullets under {max_playbook_size}
5. Focus on high-priority insights first

**Output Format** (JSON):
```json
{{
  "delta_operations": [
    {{
      "operation": "ADD",
      "bullet_id": null,
      "new_bullet": {{
        "section": "safety_protocols",
        "content": "When using strong oxidizers like KMnO4, verify glassware is free of organic residue to prevent violent reactions"
      }},
      "reason": "Addresses safety insight #1 about oxidizer handling"
    }},
    {{
      "operation": "UPDATE",
      "bullet_id": "proc-00003",
      "new_bullet": {{
        "section": "procedure_design",
        "content": "Updated content with improved clarity..."
      }},
      "reason": "Clarifies ambiguous instruction based on insight #2"
    }},
    {{
      "operation": "REMOVE",
      "bullet_id": "err-00001",
      "new_bullet": null,
      "reason": "Bullet has been consistently harmful (low helpfulness score)"
    }}
  ]
}}
```

**Important**:
- Limit to **3-5 operations** per curation cycle (incremental updates)
- Only propose operations with clear justification
- If no changes are needed, return empty delta_operations list
""")

    return "\n\n".join(sections)


# ============================================================================
# Deduplication Prompt (Optional)
# ============================================================================

def build_deduplication_check_prompt(
    new_bullet_content: str,
    existing_bullets: List[PlaybookBullet],
    similarity_threshold: float = 0.85
) -> str:
    """
    Build prompt to check if new bullet is redundant.

    This is a fallback LLM-based check in addition to embedding similarity.

    Args:
        new_bullet_content: Proposed new bullet
        existing_bullets: Current bullets in same section
        similarity_threshold: Cosine similarity threshold

    Returns:
        Deduplication check prompt
    """
    sections = []

    sections.append("## Proposed New Bullet")
    sections.append(new_bullet_content)

    sections.append("\n## Existing Bullets in Section")
    for bullet in existing_bullets:
        sections.append(f"\n**[{bullet.id}]**: {bullet.content}")

    sections.append("\n## Your Task")
    sections.append(f"""
Determine if the proposed bullet is semantically redundant with any existing bullet.

Two bullets are redundant if they convey essentially the same information, even if worded differently.

**Output as JSON**:
```json
{{
  "is_redundant": true,
  "similar_bullet_id": "mat-00005",
  "explanation": "Both bullets address solvent selection for polarity, though wording differs"
}}
```

Or if not redundant:
```json
{{
  "is_redundant": false,
  "similar_bullet_id": null,
  "explanation": "Addresses unique aspect not covered by existing bullets"
}}
```
""")

    return "\n\n".join(sections)


# ============================================================================
# Pruning Decision Prompt
# ============================================================================

def build_pruning_prompt(
    low_quality_bullets: List[PlaybookBullet],
    playbook_size: int,
    max_size: int
) -> str:
    """
    Build prompt for pruning decisions when playbook exceeds max size.

    Implements Grow-and-Refine from ACE paper §3.2.

    Args:
        low_quality_bullets: Bullets with low helpfulness scores
        playbook_size: Current size
        max_size: Maximum size

    Returns:
        Pruning prompt
    """
    sections = []

    sections.append(f"## Playbook Size Limit Exceeded")
    sections.append(f"Current size: {playbook_size}")
    sections.append(f"Maximum size: {max_size}")
    sections.append(f"Need to remove: {playbook_size - max_size} bullets")

    sections.append("\n## Candidate Bullets for Removal")
    sections.append("These bullets have low helpfulness scores or have caused errors:")

    for bullet in low_quality_bullets:
        sections.append(f"\n**[{bullet.id}]** (Score: {bullet.metadata.helpfulness_score:.2f})")
        sections.append(f"- Content: {bullet.content}")
        sections.append(f"- Uses: {bullet.metadata.total_uses}")
        sections.append(f"- Helpful: {bullet.metadata.helpful_count}, Harmful: {bullet.metadata.harmful_count}")

    sections.append("\n## Your Task")
    sections.append("""
Decide which bullets to remove to bring playbook back under size limit.

**Criteria**:
1. Remove bullets with helpfulness_score < 0.3 (more harmful than helpful)
2. Among low-score bullets, prioritize removing those with most uses (clear evidence)
3. Keep bullets that address critical safety or quality issues
4. Avoid removing all bullets from a section

**Output as JSON**:
```json
{
  "bullets_to_remove": ["err-00001", "proc-00007"],
  "reasoning": "Removed bullets that consistently led to errors (score < 0.3 with 5+ uses)"
}
```
""")

    return "\n\n".join(sections)
