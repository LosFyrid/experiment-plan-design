# Quick Start Guide

## Repository Initialization Complete ✅

The Experiment Plan Design System repository has been successfully initialized with the following structure:

### Created Files

**Documentation**:
- `README.md` - Project overview and usage guide
- `ARCHITECTURE.md` - Detailed system architecture and design decisions
- `CLAUDE.md` - Guidance for Claude Code when working with this codebase

**Configuration**:
- `configs/ace_config.yaml` - ACE framework configuration
- `configs/rag_config.yaml` - RAG template library configuration
- `src/external/MOSES/config/settings.yaml` - MOSES configuration (直接修改)
- `.env.example` - Environment variables template
- `requirements.txt` - Python dependencies

**Project Structure**:
```
src/
├── ace_framework/          # ACE core (Generator, Reflector, Curator, Playbook)
├── chatbot/                # MOSES wrapper for dialogue management
├── rag/                    # Template library and vector search
├── evaluation/             # Plan evaluation and feedback
└── utils/                  # Common utilities

data/
├── templates/              # Experiment plan templates (TBD from partners)
├── examples/               # Training/test examples
└── playbooks/              # ACE playbooks (evolving knowledge base)

configs/                    # YAML configuration files
tests/                      # Unit and integration tests
docs/                       # Additional documentation
notebooks/                  # Jupyter notebooks for experiments
logs/                       # Application logs
```

## Next Steps

### 1. Set Up Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your DASHSCOPE_API_KEY (for Qwen)
```

### 2. Development Priorities (From README.md)

- [ ] **ACE Framework Core Implementation** ← Current priority
  - [ ] Implement Playbook data structures (`src/ace_framework/playbook/`)
  - [ ] Implement Generator (`src/ace_framework/generator/`)
  - [ ] Implement Reflector with iterative refinement (`src/ace_framework/reflector/`)
  - [ ] Implement Curator with delta updates (`src/ace_framework/curator/`)

- [ ] **MOSES Chatbot Wrapper** (`src/chatbot/`)
  - [ ] Create wrapper interface for MOSES query workflow
  - [ ] Implement dialogue state management
  - [ ] Implement requirements extraction

- [ ] **RAG Template Library** (`src/rag/`)
  - [ ] Set up Chroma vector store
  - [ ] Implement template indexing with LlamaIndex
  - [ ] Implement retrieval with semantic search

- [ ] **Evaluation System** (`src/evaluation/`)
  - [ ] Implement automated completeness checks
  - [ ] Implement LLM-as-a-judge evaluator
  - [ ] Implement human feedback collection interface

- [ ] **End-to-End Integration**
  - [ ] Connect all three stages (MOSES → RAG → ACE)
  - [ ] Create example workflows
  - [ ] Add integration tests

## Key Implementation Guidelines

### ACE Framework (Follow Paper Strictly)

Reference: `2510.04618v1.pdf` in repository root

1. **Generator** (§3, Figure 4):
   - Use prompt templates from Appendix D (pages 15-18)
   - Retrieve top-K bullets from playbook (default: 50)
   - Track reasoning trajectory for Reflector

2. **Reflector** (§3, Figure 10):
   - Implement iterative refinement (max 5 rounds)
   - Tag bullets as helpful/harmful/neutral
   - Extract structured insights (error_identification, root_cause, correct_approach)

3. **Curator** (§3.1, §3.2, Figure 11):
   - **Critical**: Use incremental delta updates (NOT monolithic rewriting)
   - Implement grow-and-refine mechanism
   - Semantic deduplication with cosine similarity threshold 0.85

### Model Consistency

**Important**: All three ACE roles MUST use the **same LLM model** (paper §4.2) to prevent knowledge transfer bias.

Default: `qwen-max` for Generator, Reflector, and Curator

### Pydantic Schemas

Implement data models in `src/ace_framework/playbook/schemas.py`:

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BulletMetadata(BaseModel):
    helpful_count: int = 0
    harmful_count: int = 0
    created_at: datetime
    last_updated: datetime
    source: str  # "reflection" | "manual" | "seed"

class PlaybookBullet(BaseModel):
    id: str  # e.g., "mat-00001"
    section: str
    content: str
    metadata: BulletMetadata

class Playbook(BaseModel):
    bullets: List[PlaybookBullet]
    sections: List[str]
    version: str
    last_updated: datetime

# See ARCHITECTURE.md §6 for ExperimentPlan and other schemas
```

## Testing

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/ace_framework/
pytest tests/rag/
pytest tests/chatbot/

# With coverage
pytest --cov=src tests/

# Format and lint before committing
black src/ tests/
mypy src/
flake8 src/ tests/
```

## Configuration Files

### `configs/ace_config.yaml`
- Controls ACE behavior: model selection, playbook settings, training parameters
- Modify `ace.generator.max_playbook_bullets` to change retrieval size
- Modify `ace.reflector.max_refinement_rounds` to change iteration count

### `configs/rag_config.yaml`
- Controls template retrieval: vector store, embeddings, search parameters
- Modify `retrieval.top_k` to change number of retrieved templates

### `src/external/MOSES/config/settings.yaml` (MOSES自己的配置)
- **直接修改MOSES配置，不要新建配置文件**
- 修改LLM部分改为Qwen：
  ```yaml
  LLM:
    model: "qwen-plus"  # 改为qwen模型
    temperature: 0
    max_tokens: 5000
  ```

## Working with MOSES

MOSES is located at `src/external/MOSES/` (git subtree).

**DO NOT modify MOSES code directly.** Instead:

1. Create wrapper in `src/chatbot/moses_wrapper.py`
2. Import MOSES components:
   ```python
   from src.external.MOSES.autology_constructor.idea.query_team import query_workflow
   ```
3. Wrap MOSES query workflow with dialogue management

## References

- ACE Paper: `2510.04618v1.pdf` (in repository root)
- MOSES Documentation: `src/external/MOSES/README.md`
- LlamaIndex Docs: https://docs.llamaindex.ai/
- Dynamic Cheatsheet: https://github.com/suzgunmirac/dynamic-cheatsheet

## Questions or Issues?

Refer to:
1. `CLAUDE.md` - Detailed guidance for Claude Code
2. `ARCHITECTURE.md` - System architecture and design decisions
3. `README.md` - Project overview and usage examples

---

**Repository Status**: Initialized and ready for development
**Next Action**: Implement ACE Framework core components
