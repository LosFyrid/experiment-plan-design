"""
Prompt templates for ACE Reflector.

Implements reflection prompts inspired by ACE paper §3 and Appendix D.
Reflector performs iterative refinement to extract high-quality insights.
"""

from typing import List, Dict, Optional
from ..playbook.schemas import TrajectoryStep, ExperimentPlan, Feedback


def format_experiment_plan(plan: ExperimentPlan) -> str:
    """
    Format experiment plan for reflection analysis.

    Args:
        plan: ExperimentPlan object

    Returns:
        Formatted plan string
    """
    lines = []

    lines.append(f"# {plan.title}")
    lines.append(f"\n**Objective**: {plan.objective}")

    # Materials
    lines.append("\n## Materials")
    for mat in plan.materials:
        mat_line = f"- {mat.name} ({mat.amount})"
        if mat.purity:
            mat_line += f" - Purity: {mat.purity}"
        if mat.hazard_info:
            mat_line += f" - ⚠️ {mat.hazard_info}"
        lines.append(mat_line)

    # Procedure
    lines.append("\n## Procedure")
    for step in plan.procedure:
        step_line = f"{step.step_number}. {step.description}"
        if step.duration:
            step_line += f" ({step.duration})"
        if step.temperature:
            step_line += f" [Temp: {step.temperature}]"
        if step.critical:
            step_line = f"🔴 {step_line}"
        lines.append(step_line)
        if step.notes:
            lines.append(f"   Note: {step.notes}")

    # Safety
    if plan.safety_notes:
        lines.append("\n## Safety Notes")
        for note in plan.safety_notes:
            lines.append(f"- ⚠️ {note}")

    # Quality Control
    if plan.quality_control:
        lines.append("\n## Quality Control")
        for qc in plan.quality_control:
            lines.append(f"- **{qc.check_point}** ({qc.timing})")
            lines.append(f"  - Method: {qc.method}")
            lines.append(f"  - Criteria: {qc.acceptance_criteria}")

    # Expected outcome
    lines.append(f"\n## Expected Outcome")
    lines.append(plan.expected_outcome)

    return "\n".join(lines)


def format_feedback(feedback: Feedback) -> str:
    """
    Format feedback for reflection.

    Args:
        feedback: Feedback object

    Returns:
        Formatted feedback string
    """
    lines = []

    lines.append(f"**Overall Score**: {feedback.overall_score:.2f}/1.0")
    lines.append(f"**Source**: {feedback.feedback_source}")

    lines.append("\n**Criteria Scores**:")
    for score in feedback.scores:
        lines.append(f"- {score.criterion}: {score.score:.2f}")
        if score.explanation:
            lines.append(f"  → {score.explanation}")

    if feedback.comments:
        lines.append(f"\n**Comments**: {feedback.comments}")

    return "\n".join(lines)


def format_trajectory(trajectory: List[TrajectoryStep]) -> str:
    """
    Format reasoning trajectory for analysis.

    Args:
        trajectory: List of TrajectoryStep objects

    Returns:
        Formatted trajectory string
    """
    if not trajectory:
        return "No reasoning trajectory available."

    lines = []
    for step in trajectory:
        lines.append(f"\n### Step {step.step_number}")
        lines.append(f"**Thought**: {step.thought}")
        if step.action:
            lines.append(f"**Action**: {step.action}")
        if step.observation:
            lines.append(f"**Observation**: {step.observation}")

    return "\n".join(lines)


# ============================================================================
# Initial Reflection Prompt (Round 1)
# ============================================================================

INITIAL_REFLECTION_SYSTEM_PROMPT = """You are an expert chemistry experiment reviewer with deep knowledge of:
- Experimental design and methodology
- Chemical safety and best practices
- Common pitfalls and error patterns
- Quality control and reproducibility

Your role is to analyze generated experiment plans and extract actionable insights that can improve future generations.

You will receive:
1. A generated experiment plan
2. Feedback scores indicating quality issues
3. The reasoning trajectory used during generation
4. Playbook bullets that were referenced

Your task is to perform **error analysis** and extract **improvement insights**:

**Error Analysis**:
- What went wrong in the generated plan?
- Why did it happen? (root cause)
- Which aspects of feedback scores are low?
- Are there safety issues, clarity problems, or completeness gaps?

**Insight Extraction**:
- What should be done differently next time?
- Which specific practices should be added to the playbook?
- How can we prevent this type of error in future?
- What patterns can be generalized?

**Bullet Tagging**:
- Which playbook bullets were helpful (led to good decisions)?
- Which were harmful (led to errors or omissions)?
- Which were neutral (not impactful)?

Focus on **actionable** and **specific** insights, not generic advice.
"""


def build_initial_reflection_prompt(
    plan: ExperimentPlan,
    feedback: Feedback,
    trajectory: List[TrajectoryStep],
    bullets_used: List[str],
    bullet_contents: Dict[str, str]
) -> str:
    """
    Build initial reflection prompt (Round 1).

    Args:
        plan: Generated experiment plan
        feedback: Evaluation feedback
        trajectory: Reasoning trajectory
        bullets_used: List of bullet IDs used
        bullet_contents: Mapping of bullet_id -> content

    Returns:
        Prompt string for initial reflection
    """
    sections = []

    # Generated plan
    sections.append("## Generated Experiment Plan")
    sections.append(format_experiment_plan(plan))

    # Feedback
    sections.append("\n## Evaluation Feedback")
    sections.append(format_feedback(feedback))

    # Trajectory
    sections.append("\n## Generation Reasoning Trajectory")
    sections.append(format_trajectory(trajectory))

    # Bullets used
    sections.append("\n## Playbook Bullets Referenced")
    if bullets_used:
        for bullet_id in bullets_used:
            content = bullet_contents.get(bullet_id, "Content not found")
            sections.append(f"- **[{bullet_id}]**: {content}")
    else:
        sections.append("No playbook bullets were explicitly referenced.")

    # Task instruction
    sections.append("\n## Your Task")
    sections.append("""
Analyze the above information and provide:

1. **Error Identification**: What specific problems exist in the plan?
2. **Root Cause Analysis**: Why did these errors occur?
3. **Correct Approach**: What should have been done instead?
4. **Key Insights**: What generalizable lessons can be extracted?
5. **Bullet Tagging**: For each bullet referenced, was it helpful, harmful, or neutral?

Output as JSON:
```json
{
  "error_identification": "Detailed description of errors...",
  "root_cause_analysis": "Why these errors occurred...",
  "correct_approach": "What should be done instead...",
  "insights": [
    {
      "type": "safety_issue",
      "description": "Specific insight...",
      "suggested_bullet": "Proposed playbook bullet content...",
      "target_section": "safety_protocols",
      "priority": "high"
    }
  ],
  "bullet_tags": {
    "mat-00001": "helpful",
    "proc-00003": "harmful"
  }
}
```
""")

    return "\n\n".join(sections)


# ============================================================================
# Refinement Prompt (Rounds 2-5)
# ============================================================================

REFINEMENT_SYSTEM_PROMPT = """You are refining your previous reflection to improve insight quality.

In each refinement round, you should:
1. **Deepen Analysis**: Go beyond surface-level observations
2. **Increase Specificity**: Replace vague advice with concrete actions
3. **Add Context**: Explain why certain practices matter
4. **Generalize Patterns**: Extract broader lessons from specific errors
5. **Ensure Actionability**: Make sure insights can be directly applied

Focus on improving the **quality** and **usefulness** of insights, not just adding more.
"""


def build_refinement_prompt(
    previous_insights: List[Dict],
    previous_analysis: str,
    round_number: int,
    max_rounds: int
) -> str:
    """
    Build refinement prompt for iterative improvement.

    Implements iterative refinement from ACE paper §3, Figure 4.

    Args:
        previous_insights: Insights from previous round
        previous_analysis: Error analysis from previous round
        round_number: Current round (2-5)
        max_rounds: Maximum refinement rounds

    Returns:
        Refinement prompt string
    """
    sections = []

    sections.append(f"## Refinement Round {round_number}/{max_rounds}")

    sections.append("\n### Previous Analysis")
    sections.append(previous_analysis)

    sections.append("\n### Previous Insights")
    for i, insight in enumerate(previous_insights, 1):
        sections.append(f"\n**Insight {i}**:")
        sections.append(f"- Type: {insight.get('type', 'unknown')}")
        sections.append(f"- Description: {insight.get('description', '')}")
        if "suggested_bullet" in insight:
            sections.append(f"- Suggested Bullet: {insight['suggested_bullet']}")

    sections.append("\n### Your Task")
    sections.append("""
Refine the above analysis and insights by:
1. Making insights more specific and actionable
2. Adding important details that were missed
3. Improving the clarity and usefulness of suggested bullets
4. Ensuring root causes are correctly identified
5. Removing redundant or low-value insights

Output the **improved** analysis and insights in the same JSON format:
```json
{
  "error_identification": "Refined error description...",
  "root_cause_analysis": "Deeper root cause...",
  "correct_approach": "More specific approach...",
  "insights": [
    {
      "type": "...",
      "description": "Improved insight...",
      "suggested_bullet": "Better bullet content...",
      "target_section": "...",
      "priority": "..."
    }
  ],
  "bullet_tags": {
    "...": "..."
  }
}
```
""")

    return "\n\n".join(sections)


# ============================================================================
# Bullet Tagging Prompt (if not included in reflection)
# ============================================================================

def build_bullet_tagging_prompt(
    plan: ExperimentPlan,
    feedback: Feedback,
    bullets_used: List[str],
    bullet_contents: Dict[str, str]
) -> str:
    """
    Build prompt specifically for bullet tagging.

    Used if bullet tagging needs to be done separately.

    Args:
        plan: Generated experiment plan
        feedback: Evaluation feedback
        bullets_used: List of bullet IDs
        bullet_contents: Mapping of bullet_id -> content

    Returns:
        Bullet tagging prompt
    """
    sections = []

    sections.append("## Experiment Plan Summary")
    sections.append(f"**Title**: {plan.title}")
    sections.append(f"**Overall Quality Score**: {feedback.overall_score:.2f}")

    sections.append("\n## Playbook Bullets Used")
    for bullet_id in bullets_used:
        content = bullet_contents.get(bullet_id, "Unknown")
        sections.append(f"\n**[{bullet_id}]**: {content}")

    sections.append("\n## Your Task")
    sections.append("""
For each playbook bullet above, determine if it was:
- **helpful**: Led to a good decision or prevented an error
- **harmful**: Led to an error, omission, or suboptimal choice
- **neutral**: Was referenced but didn't significantly impact quality

Consider the feedback scores when making your assessment.

Output as JSON:
```json
{
  "bullet_tags": {
    "mat-00001": "helpful",
    "proc-00003": "harmful",
    "safe-00002": "neutral"
  },
  "explanations": {
    "mat-00001": "Why this bullet was helpful...",
    "proc-00003": "Why this bullet was harmful..."
  }
}
```
""")

    return "\n\n".join(sections)
