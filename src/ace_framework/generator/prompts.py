"""
Prompt templates for ACE Generator.

Implements prompts inspired by ACE paper §3 and Appendix D.
"""

from typing import List, Dict, Optional
from ..playbook.schemas import PlaybookBullet


def format_playbook_bullets(bullets: List[PlaybookBullet]) -> str:
    """
    Format playbook bullets for inclusion in prompt.

    Args:
        bullets: List of PlaybookBullet objects

    Returns:
        Formatted string with section-organized bullets
    """
    if not bullets:
        return "No playbook guidance available."

    # Group by section
    sections: Dict[str, List[PlaybookBullet]] = {}
    for bullet in bullets:
        if bullet.section not in sections:
            sections[bullet.section] = []
        sections[bullet.section].append(bullet)

    # Format output
    lines = []
    for section, section_bullets in sections.items():
        lines.append(f"\n### {section.replace('_', ' ').title()}")
        for bullet in section_bullets:
            lines.append(f"- [{bullet.id}] {bullet.content}")

    return "\n".join(lines)


def format_requirements(requirements: Dict) -> str:
    """
    Format structured requirements into readable text.

    Args:
        requirements: Dict with target_compound, materials, constraints, etc.

    Returns:
        Formatted requirements string
    """
    lines = []

    if "target_compound" in requirements:
        lines.append(f"**Target Compound**: {requirements['target_compound']}")

    if "objective" in requirements:
        lines.append(f"**Objective**: {requirements['objective']}")

    if "materials" in requirements and requirements["materials"]:
        lines.append("\n**Available Materials**:")
        for mat in requirements["materials"]:
            if isinstance(mat, dict):
                lines.append(f"  - {mat.get('name', 'Unknown')}")
            else:
                lines.append(f"  - {mat}")

    if "constraints" in requirements and requirements["constraints"]:
        lines.append("\n**Constraints**:")
        for constraint in requirements["constraints"]:
            lines.append(f"  - {constraint}")

    if "special_requirements" in requirements:
        lines.append(f"\n**Special Requirements**: {requirements['special_requirements']}")

    return "\n".join(lines)


def format_templates(templates: List[Dict]) -> str:
    """
    Format retrieved templates for prompt.

    Supports both Mock RAG format and Real RAG format:
    - Mock RAG: {title, procedure_summary, key_points}
    - Real RAG: {title, content, score}

    Args:
        templates: List of template dicts from RAG

    Returns:
        Formatted templates string
    """
    if not templates:
        return "No relevant templates found."

    lines = []
    for i, template in enumerate(templates, 1):
        lines.append(f"\n### Template {i}")

        # Title（通用）
        if "title" in template:
            lines.append(f"**Title**: {template['title']}")

        # Mock RAG 格式（向后兼容）
        if "procedure_summary" in template:
            lines.append(f"**Procedure**: {template['procedure_summary']}")

        if "key_points" in template:
            lines.append("**Key Points**:")
            for point in template["key_points"]:
                lines.append(f"  - {point}")

        # Real RAG 格式（新增）
        if "content" in template:
            # 截取前500字符作为预览（避免过长）
            content = template["content"]
            max_length = 500
            if len(content) > max_length:
                content_preview = content[:max_length] + "... (内容已截断)"
            else:
                content_preview = content

            lines.append(f"**Content**:\n{content_preview}")

        # 相关度分数（可选）
        if "score" in template:
            lines.append(f"**Relevance Score**: {template['score']:.3f}")

    return "\n".join(lines)


# ============================================================================
# Main Generation Prompt
# ============================================================================

SYSTEM_PROMPT = """You are an expert chemistry experiment planner with extensive knowledge in organic synthesis, materials science, and laboratory best practices.

Your task is to generate detailed, safe, and executable experiment plans based on:
1. **User Requirements**: The specific goals and constraints
2. **Playbook Guidance**: Accumulated best practices and lessons learned
3. **Template References**: Relevant example procedures

You must produce a structured experiment plan that includes:
- Clear objective statement
- Complete materials list with specifications
- Detailed step-by-step procedure
- Safety protocols and warnings
- Quality control checkpoints
- Expected outcomes

**Critical Guidelines**:
- Always prioritize safety - include all relevant warnings
- Be specific with quantities, temperatures, and durations
- Reference playbook bullets that inform your decisions (use bullet IDs like [mat-00001])
- Explain your reasoning for key choices
- Ensure the procedure is executable by a trained chemist

Output your response as a JSON object with the following structure:
```json
{
  "plan": {
    "title": "Experiment title",
    "objective": "Clear statement of what this experiment aims to achieve",
    "materials": [
      {
        "name": "Material name",
        "amount": "Quantity with unit",
        "purity": "Required purity (optional)",
        "cas_number": "CAS number (optional)",
        "hazard_info": "Safety information (optional)"
      }
    ],
    "procedure": [
      {
        "step_number": 1,
        "description": "Detailed description of this step",
        "duration": "Expected time (optional)",
        "temperature": "Temperature condition (optional)",
        "notes": "Additional notes or warnings (optional)",
        "critical": false
      }
    ],
    "safety_notes": [
      "Safety warning 1",
      "Safety warning 2"
    ],
    "expected_outcome": "What should be observed if experiment succeeds",
    "quality_control": [
      {
        "check_point": "What to verify",
        "method": "How to check",
        "acceptance_criteria": "What indicates success",
        "timing": "When to check"
      }
    ],
    "estimated_duration": "Total time estimate (optional)",
    "difficulty_level": "beginner/intermediate/advanced (optional)"
  },
  "reasoning": {
    "trajectory": [
      {
        "step_number": 1,
        "thought": "Your reasoning for a major decision",
        "action": "What you decided",
        "observation": "Expected result"
      }
    ],
    "bullets_used": ["mat-00001", "proc-00005"]
  }
}
```
"""


def build_generation_prompt(
    requirements: Dict,
    playbook_bullets: List[PlaybookBullet],
    templates: List[Dict],
    few_shot_examples: Optional[List[Dict]] = None
) -> str:
    """
    Build complete generation prompt for ACE Generator.

    Args:
        requirements: Structured requirements from MOSES
        playbook_bullets: Retrieved bullets from playbook
        templates: Retrieved templates from RAG
        few_shot_examples: Optional few-shot examples

    Returns:
        Complete user prompt string
    """
    sections = []

    # Requirements
    sections.append("## User Requirements")
    sections.append(format_requirements(requirements))

    # Playbook guidance
    sections.append("\n## Playbook Guidance")
    sections.append("The following best practices have been learned from past experiments:")
    sections.append(format_playbook_bullets(playbook_bullets))

    # Templates
    sections.append("\n## Reference Templates")
    sections.append("Here are relevant experiment templates for reference:")
    sections.append(format_templates(templates))

    # Few-shot examples (if provided)
    if few_shot_examples:
        sections.append("\n## Example Plans")
        sections.append("Here are examples of well-structured experiment plans:")
        for i, example in enumerate(few_shot_examples, 1):
            sections.append(f"\n### Example {i}")
            if "input" in example:
                sections.append(f"**Input**: {example['input']}")
            if "output" in example:
                sections.append(f"**Output**: {example['output']}")

    # Final instruction
    sections.append("\n## Your Task")
    sections.append(
        "Based on the above information, generate a complete experiment plan. "
        "Think step-by-step, reference relevant playbook bullets using their IDs, "
        "and ensure your plan is safe, complete, and executable."
    )

    return "\n\n".join(sections)


# ============================================================================
# Trajectory Extraction Prompt
# ============================================================================

TRAJECTORY_EXTRACTION_PROMPT = """You are analyzing an experiment plan generation process.

Given the generated plan and the context used, identify the key reasoning steps that led to important decisions.

For each major decision (e.g., material selection, procedure choice, safety measure), extract:
1. **Thought**: What was the reasoning?
2. **Action**: What was decided?
3. **Observation**: What was the expected result or justification?

Focus on decisions that:
- Impact safety
- Affect experiment success
- Involve tradeoffs
- Apply playbook guidance

Output as JSON array:
```json
{
  "trajectory": [
    {
      "step_number": 1,
      "thought": "Need to select appropriate solvent for reaction",
      "action": "Chose dichloromethane based on polarity requirements",
      "observation": "DCM provides optimal solubility and reaction rate"
    }
  ]
}
```
"""


# ============================================================================
# Bullet Reference Extraction
# ============================================================================

def extract_bullet_references(text: str) -> List[str]:
    """
    Extract playbook bullet IDs referenced in generated text.

    Looks for patterns like [mat-00001] or (mat-00001).

    Args:
        text: Generated plan text

    Returns:
        List of unique bullet IDs
    """
    import re

    # Pattern: [section-NNNNN] or (section-NNNNN)
    pattern = r'[\[\(]([a-z]+-\d{5})[\]\)]'

    matches = re.findall(pattern, text)

    # Return unique IDs
    return list(set(matches))
