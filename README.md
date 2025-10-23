# Experiment Plan Design System

An intelligent system for generating chemistry experiment plans using ACE (Agentic Context Engineering) framework.

## Project Overview

This project implements a three-stage pipeline for automated experiment plan generation:

1. **Knowledge-based Chatbot**: Interactive dialogue system built on MOSES (Multi-Ontology Semantic Extraction and Synthesis) to extract experimental requirements and domain knowledge
2. **RAG-based Template Library**: Retrieval system for finding relevant experiment plan templates using vector search
3. **ACE-powered Plan Generator**: Context engineering framework that synthesizes user requirements and templates into executable experiment plans

## System Architecture

```
=== 实验方案生成流程 (实时) ===
User Input (Experimental Idea)
         ↓
[MOSES Chatbot] → Structured Requirements (JSON)
         ↓
[RAG Template Library] → Relevant Templates
         ↓
[Generator + Playbook] → Experiment Plan ✅
         ↓
Final Experiment Plan (Structured Document)

=== Playbook进化流程 (离线/在线学习) ===
Experiment Plan → Feedback (LLM-judge/Human)
         ↓
[Reflector] → Analyze errors → Insights
         ↓
[Curator] → Incremental delta updates
         ↓
Updated Playbook (用于下次生成)
```

## Key Components

### 1. ACE Framework (Playbook Evolution System)
Based on the paper "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" (arXiv:2510.04618v1).

**核心理解**：ACE不是生成流程，而是**让系统自我改进的学习机制**。

- **Generator**: 使用当前playbook生成实验方案（这是唯一直接面向用户的组件）
- **Reflector**: 分析生成的方案+反馈，提取改进策略（离线/在线学习）
- **Curator**: 将insights增量更新到playbook（离线/在线学习）
- **Playbook**: 持续进化的知识库，指导Generator生成更好的方案

**生产环境使用**：用户只需 Generator + Playbook
**训练/改进环境**：使用完整ACE循环（Generator → Feedback → Reflector → Curator → Update Playbook）

Key Features:
- **Incremental Delta Updates**: Avoids context collapse through localized edits
- **Grow-and-Refine**: Balances context expansion with redundancy control
- **Self-Improving**: Playbook continuously evolves from execution feedback

### 2. MOSES Integration
- Ontology-based knowledge retrieval for chemistry domain
- Multi-agent workflow for query processing
- Wrapper interface for dialogue management

### 3. RAG Template Library
- Vector-based similarity search (Chroma)
- Template indexing and retrieval
- LlamaIndex for efficient processing

## Directory Structure

```
experiment-plan-design/
├── src/
│   ├── ace_framework/          # ACE core implementation
│   │   ├── generator/          # Plan generation with playbook
│   │   ├── reflector/          # Analysis and insight extraction
│   │   ├── curator/            # Playbook update logic
│   │   └── playbook/           # Playbook data structures
│   ├── chatbot/                # MOSES wrapper and dialogue management
│   ├── evaluation/             # Scoring and feedback systems
│   ├── utils/                  # Common utilities
│   └── external/               # External dependencies
│       ├── MOSES/              # MOSES codebase (git subtree)
│       └── rag/                # RAG template library
├── data/
│   ├── templates/              # Experiment plan templates
│   └── examples/               # Example inputs/outputs
├── configs/                    # Configuration files
├── tests/                      # Unit and integration tests
├── docs/                       # Documentation
└── notebooks/                  # Jupyter notebooks for experiments
```

## Installation

```bash
# Clone repository
git clone <repo-url>
cd experiment-plan-design

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Key configuration files:
- `configs/ace_config.yaml`: ACE framework settings (model selection, playbook parameters)
- `configs/rag_config.yaml`: RAG template library settings
- `src/external/MOSES/config/settings.yaml`: MOSES ontology and LLM settings (直接修改MOSES配置)
- `.env`: API keys and sensitive credentials

## Usage

### Basic Usage

```python
from src.ace_framework import ExperimentPlanGenerator

# Initialize generator
generator = ExperimentPlanGenerator(
    config_path="configs/ace_config.yaml"
)

# Generate plan from user requirements
requirements = {
    "objective": "Synthesize aspirin from salicylic acid",
    "constraints": ["Lab safety level 2", "Budget < $500"],
    "expected_outcome": "Pure acetylsalicylic acid crystals"
}

plan = generator.generate(requirements)
print(plan.to_markdown())
```

### Training ACE Playbook (Offline Adaptation)

```python
from src.ace_framework import ACETrainer

trainer = ACETrainer(config_path="configs/ace_config.yaml")

# Train on example dataset
trainer.train(
    examples_path="data/examples/training_set.json",
    num_epochs=5,
    feedback_source="llm_judge"  # or "human"
)

# Save trained playbook
trainer.save_playbook("data/playbooks/chemistry_v1.json")
```

## Development Status

- [x] Project initialization
- [x] Architecture design
- [ ] ACE framework core implementation
- [ ] MOSES chatbot wrapper
- [ ] RAG template library
- [ ] Evaluation system
- [ ] End-to-end integration
- [ ] Documentation and examples

## References

1. Zhang, Q., et al. (2025). "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models." arXiv:2510.04618v1
2. MOSES: Multi-Ontology Semantic Extraction and Synthesis (local implementation)
3. LlamaIndex Documentation: https://docs.llamaindex.ai/

## License

[To be determined]

## Contact

[To be filled]
