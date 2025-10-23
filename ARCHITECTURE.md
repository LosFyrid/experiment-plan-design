# System Architecture Document

## 1. Overview

This document records the architectural decisions, technical stack, and design principles for the Experiment Plan Design System.

## 2. Architecture Decisions

### 2.1 Core Decisions

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| ACE Implementation | From-scratch (reference paper) | Full customization for chemistry domain; cleaner codebase | 2025-10-23 |
| LLM Provider | Qwen (primary) | Cost-effective; good Chinese support; domain adaptability | 2025-10-23 |
| Vector Database | Chroma | Lightweight; easy integration with LlamaIndex | 2025-10-23 |
| Chatbot Framework | LangChain/LangGraph | Continuity with MOSES; mature ecosystem | 2025-10-23 |
| Cold Start Strategy | Deferred | ACE can bootstrap from execution feedback (paper §4.3) | 2025-10-23 |

### 2.2 ACE Framework Design

Following the paper's architecture (Figure 4, page 5), we implement:

#### **Three-Role Architecture**

```python
┌─────────────────────────────────────────────────────────────┐
│                     ACE Workflow                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Query + Context Playbook                                    │
│         ↓                                                     │
│  ┌──────────────┐                                            │
│  │  Generator   │ → Trajectory (Experiment Plan Draft)       │
│  └──────────────┘                                            │
│         ↓                                                     │
│  ┌──────────────┐    ┌─────────────────────┐                │
│  │  Reflector   │ ←──│ Iterative Refinement│                │
│  └──────────────┘    └─────────────────────┘                │
│         ↓                                                     │
│     Insights (JSON: error_identification, correct_approach)  │
│         ↓                                                     │
│  ┌──────────────┐                                            │
│  │   Curator    │ → Delta Context Items                      │
│  └──────────────┘                                            │
│         ↓                                                     │
│  Playbook Update (Incremental Merge)                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### **Key Innovations (vs. Dynamic Cheatsheet)**

| Feature | Dynamic Cheatsheet | ACE (Our Implementation) |
|---------|-------------------|--------------------------|
| Update Mechanism | Monolithic rewriting | **Incremental delta updates** (§3.1) |
| Reflector | Integrated in curator | **Dedicated component** with iterative refinement (§3) |
| Context Structure | Flat memory entries | **Structured bullets** with metadata (id, counters) |
| Collapse Prevention | Not addressed | **Grow-and-refine** mechanism (§3.2) |
| Multi-epoch | Not mentioned | **Supported** for offline training (§4.5) |

#### **Playbook Structure (§3.1)**

```python
{
  "bullets": [
    {
      "id": "chem-00001",
      "section": "material_selection",
      "content": "Always verify reagent purity before synthesis...",
      "metadata": {
        "helpful_count": 5,
        "harmful_count": 0,
        "created_at": "2025-10-23T14:00:00Z",
        "last_updated": "2025-10-23T15:30:00Z"
      }
    },
    // More bullets...
  ],
  "sections": [
    "material_selection",
    "procedure_design",
    "safety_protocols",
    "quality_control",
    "troubleshooting"
  ]
}
```

### 2.3 Data Flow

#### **实时生成流程（生产环境）**

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Knowledge Extraction (MOSES Chatbot)               │
├─────────────────────────────────────────────────────────────┤
│ User Input: "我想合成阿司匹林，要求纯度>98%"                   │
│      ↓                                                        │
│ MOSES Ontology Query (LangGraph workflow)                    │
│      ↓                                                        │
│ Structured Requirements:                                      │
│ {                                                             │
│   "target_compound": "acetylsalicylic_acid",                 │
│   "starting_materials": ["salicylic_acid", "acetic_anhydride"],│
│   "purity_requirement": ">98%",                              │
│   "safety_constraints": ["avoid moisture", "fume hood required"]│
│ }                                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Template Retrieval (RAG)                            │
├─────────────────────────────────────────────────────────────┤
│ Query Embedding: embed(requirements)                         │
│      ↓                                                        │
│ Chroma Vector Search                                         │
│      ↓                                                        │
│ Top-K Templates:                                              │
│ [                                                             │
│   {                                                           │
│     "template_id": "aspirin_synthesis_v3",                   │
│     "similarity": 0.92,                                      │
│     "structure": { ... }                                     │
│   },                                                          │
│   ...                                                         │
│ ]                                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Plan Generation (Generator + Playbook)              │
├─────────────────────────────────────────────────────────────┤
│ Input:                                                        │
│   - Requirements (from Stage 1)                              │
│   - Templates (from Stage 2)                                 │
│   - Current Playbook (evolved knowledge base)                │
│      ↓                                                        │
│ Generator → Final Plan ✅                                     │
│      ↓                                                        │
│ Output Plan:                                                  │
│ {                                                             │
│   "title": "High-Purity Aspirin Synthesis Protocol",        │
│   "materials": [...],                                        │
│   "procedure": [...],                                        │
│   "safety_notes": [...],                                     │
│   "expected_yield": "85-90%",                                │
│   "quality_control": [...]                                   │
│ }                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### **Playbook进化流程（训练/改进环境）**

```
┌─────────────────────────────────────────────────────────────┐
│ Feedback Collection                                          │
├─────────────────────────────────────────────────────────────┤
│ Generated Plan + Feedback (LLM-judge / Human / Auto-check)  │
│      ↓                                                        │
│ {                                                             │
│   "plan": { ... },                                           │
│   "feedback": {                                              │
│     "completeness_score": 8/10,                             │
│     "safety_score": 9/10,                                    │
│     "issues": ["Missing recrystallization details"]         │
│   }                                                           │
│ }                                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Reflector: Analysis & Insight Extraction                     │
├─────────────────────────────────────────────────────────────┤
│ Iterative Refinement (max 5 rounds)                         │
│      ↓                                                        │
│ Insights:                                                     │
│ {                                                             │
│   "error_identification": "Missed purification step",       │
│   "root_cause": "Playbook lacks crystallization strategies",│
│   "correct_approach": "Always include purification...",     │
│   "bullet_tags": {"proc-00012": "helpful", ...}             │
│ }                                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Curator: Playbook Update (Incremental Delta)                 │
├─────────────────────────────────────────────────────────────┤
│ Delta Operations:                                             │
│   - ADD: "proc-00025: Include recrystallization..."         │
│   - UPDATE: "proc-00012.helpful_count += 1"                 │
│   - REMOVE: (semantic deduplication)                         │
│      ↓                                                        │
│ Updated Playbook → Used in next generation                   │
└─────────────────────────────────────────────────────────────┘
```

## 3. Technical Stack

### 3.1 Core Dependencies

```yaml
LLM Framework:
  - langchain: 0.3.7+
  - langchain-community: latest
  - openai: 1.0+ (for API compatibility)

ACE & RAG:
  - llama-index: 0.10+
  - chromadb: 0.4+
  - sentence-transformers: 2.2+

MOSES Integration:
  - owlready2: 0.47 (OWL ontology interface)
  - rank-bm25: 0.2.2 (entity matching)

Data Processing:
  - pydantic: 2.11+
  - pyyaml: 6.0+

Development:
  - pytest: 7.0+
  - black: 23.0+
  - mypy: 1.0+
```

### 3.2 Model Selection

| Component | Model | Justification |
|-----------|-------|---------------|
| **ACE (Generator/Reflector/Curator)** | Qwen-Max | 统一使用同一模型避免知识迁移偏差 (paper §4.2) |
| **MOSES Agents** | Qwen-Plus (配置在MOSES的settings.yaml) | 对话任务使用较便宜的模型 |
| **Embeddings** | bge-large-zh-v1.5 | SOTA Chinese embeddings |

## 4. Module Design

### 4.1 ACE Framework (`src/ace_framework/`)

#### **Generator** (`generator/generator.py`)

```python
class ExperimentPlanGenerator:
    """
    Generates experiment plans using current playbook context.

    Based on ACE paper §3, implements:
    - Playbook-aware prompt construction
    - Structured output generation (Pydantic models)
    - Trajectory tracking for reflection
    """

    def generate(
        self,
        requirements: dict,
        templates: List[dict],
        playbook: Playbook,
        config: GeneratorConfig
    ) -> GenerationResult:
        """
        Args:
            requirements: Structured requirements from chatbot
            templates: Retrieved templates from RAG
            playbook: Current ACE playbook
            config: Generation parameters

        Returns:
            GenerationResult with:
              - generated_plan: Experiment plan (structured)
              - trajectory: Reasoning trace
              - relevant_bullets: Bullets used from playbook
        """
        pass
```

#### **Reflector** (`reflector/reflector.py`)

```python
class PlanReflector:
    """
    Analyzes generated plans and extracts actionable insights.

    Implements ACE paper §3 with iterative refinement (§3, Figure 4).

    Key capabilities:
    - Error identification (what went wrong?)
    - Root cause analysis (why did it happen?)
    - Correct approach extraction (what should be done?)
    - Bullet tagging (helpful/harmful/neutral)
    """

    def reflect(
        self,
        generated_plan: dict,
        ground_truth: Optional[dict],
        feedback: dict,  # From LLM-as-judge or human
        trajectory: List[dict],
        playbook_bullets_used: List[str],
        max_refinement_rounds: int = 5
    ) -> ReflectionResult:
        """
        Returns:
            ReflectionResult with:
              - insights: List of actionable insights
              - bullet_tags: {bullet_id: "helpful"|"harmful"|"neutral"}
              - error_analysis: Structured error breakdown
        """
        pass
```

#### **Curator** (`curator/curator.py`)

```python
class PlaybookCurator:
    """
    Maintains playbook through incremental delta updates.

    Implements ACE paper §3.1 (Incremental Delta Updates) and
    §3.2 (Grow-and-Refine).

    Avoids context collapse through:
    - Delta-based updates (not monolithic rewriting)
    - Semantic deduplication
    - Metadata-driven pruning
    """

    def update(
        self,
        current_playbook: Playbook,
        insights: List[Insight],
        bullet_tags: dict,
        mode: str = "incremental"  # "incremental" or "lazy"
    ) -> PlaybookUpdateResult:
        """
        Returns:
            PlaybookUpdateResult with:
              - updated_playbook: New playbook state
              - delta_operations: List of ADD/UPDATE/REMOVE ops
              - deduplication_report: Items merged
        """
        pass
```

### 4.2 MOSES Integration (`src/chatbot/`)

MOSES配置位于 `src/external/MOSES/config/settings.yaml`，**直接修改该文件**而非新建配置。

修改LLM配置为Qwen：
```yaml
# src/external/MOSES/config/settings.yaml
LLM:
  model: "qwen-plus"  # 使用qwen-plus节省成本
  streaming: false
  temperature: 0
  max_tokens: 5000
```

封装器实现：
```python
class MOSESChatbotWrapper:
    """
    Wraps MOSES query system as conversational chatbot.

    注意：不修改MOSES代码，仅封装调用
    """

    def chat(self, user_input: str) -> ChatResponse:
        """Interactive chat interface"""
        pass

    def extract_requirements(self, dialogue_history: List[dict]) -> dict:
        """Convert dialogue to structured requirements"""
        pass
```

### 4.3 RAG Template Library (`src/external/rag/`)

```python
class TemplateLibrary:
    """
    Vector-based template retrieval system.

    Uses:
    - Chroma for vector storage
    - LlamaIndex for document processing
    - Hybrid search (semantic + keyword)
    """

    def index_templates(self, template_dir: str):
        """Build vector index from template files"""
        pass

    def retrieve(
        self,
        requirements: dict,
        top_k: int = 5
    ) -> List[Template]:
        """Retrieve relevant templates"""
        pass
```

### 4.4 Evaluation (`src/evaluation/`)

```python
class ExperimentPlanEvaluator:
    """
    Multi-dimensional plan evaluation.

    Supports:
    - Automated checks (completeness, safety)
    - LLM-as-a-judge (quality assessment)
    - Human feedback collection
    """

    def evaluate(
        self,
        plan: dict,
        mode: str = "auto"  # "auto", "llm_judge", "human"
    ) -> EvaluationResult:
        pass
```

## 5. Configuration Management

### 5.1 Config File Structure

```yaml
# configs/ace_config.yaml
ace:
  model:
    provider: "qwen"
    model_name: "qwen-max"
    temperature: 0.7
    max_tokens: 4096

  generator:
    max_playbook_bullets: 50  # Retrieve top-k bullets
    include_examples: true

  reflector:
    max_refinement_rounds: 5
    enable_iterative: true

  curator:
    deduplication_threshold: 0.85  # Cosine similarity
    update_mode: "incremental"  # or "lazy"
    max_playbook_size: 200  # bullets

  playbook:
    sections:
      - material_selection
      - procedure_design
      - safety_protocols
      - quality_control
      - troubleshooting
```

## 6. Data Schemas

### 6.1 Playbook Bullet

```python
from pydantic import BaseModel
from datetime import datetime

class PlaybookBullet(BaseModel):
    id: str  # e.g., "chem-00001"
    section: str  # From predefined sections
    content: str  # Actionable insight/strategy
    metadata: BulletMetadata

class BulletMetadata(BaseModel):
    helpful_count: int = 0
    harmful_count: int = 0
    created_at: datetime
    last_updated: datetime
    source: str  # "reflection" | "manual" | "seed"
```

### 6.2 Experiment Plan

```python
class ExperimentPlan(BaseModel):
    title: str
    objective: str
    materials: List[Material]
    procedure: List[ProcedureStep]
    safety_notes: List[str]
    expected_outcome: str
    quality_control: List[QCCheck]
    references: Optional[List[str]]

class Material(BaseModel):
    name: str
    cas_number: Optional[str]
    quantity: str
    purity: Optional[str]
    supplier: Optional[str]

class ProcedureStep(BaseModel):
    step_number: int
    description: str
    duration: Optional[str]
    temperature: Optional[str]
    safety_notes: Optional[List[str]]
```

## 7. Testing Strategy

### 7.1 Unit Tests
- Generator: Prompt construction, output parsing
- Reflector: Insight extraction, bullet tagging logic
- Curator: Delta update logic, deduplication

### 7.2 Integration Tests
- End-to-end plan generation
- Playbook evolution over multiple iterations
- MOSES → RAG → ACE pipeline

### 7.3 Evaluation Metrics
- **Completeness**: % of required sections present
- **Safety**: Presence of safety warnings
- **Clarity**: Readability score (human eval)
- **Executability**: Can a chemist follow the plan? (human eval)

## 8. Deployment Considerations

### 8.1 Scaling
- **Offline Training**: Batch process on training set
- **Online Deployment**: API endpoint for real-time generation
- **Playbook Versioning**: Git-based tracking of playbook evolution

### 8.2 Monitoring
- Generation success rate
- Playbook growth rate
- Average feedback scores
- Context length trends (to detect potential collapse)

## 9. Future Extensions

### 9.1 Short-term (1-3 months)
- [ ] Multi-language support (English + Chinese)
- [ ] Template authoring interface
- [ ] Automated safety validation (rule-based)

### 9.2 Long-term (6+ months)
- [ ] Multi-domain adaptation (biology, physics)
- [ ] Collaborative playbook curation
- [ ] Experiment execution tracking integration

## 10. References

- Paper: Zhang et al. (2025). "Agentic Context Engineering" ([2510.04618v1.pdf](./2510.04618v1.pdf))
- Dynamic Cheatsheet: https://github.com/suzgunmirac/dynamic-cheatsheet
- LlamaIndex Docs: https://docs.llamaindex.ai/
- MOSES: `src/external/MOSES/README.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Maintained by**: Project Team
