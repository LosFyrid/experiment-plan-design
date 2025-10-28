# Comprehensive Configuration Usage Report

**Generated**: 2025-10-28
**Purpose**: Track every configuration parameter's definition, loading, and usage across the codebase

---

## Table of Contents

1. [configs/ace_config.yaml](#1-configsace_configyaml)
2. [configs/rag_config.yaml](#2-configsrag_configyaml)
3. [configs/chatbot_config.yaml](#3-configschatbot_configyaml)
4. [configs/playbook_sections.yaml](#4-configsplaybook_sectionsyaml)
5. [src/external/MOSES/config/settings.yaml](#5-srcexternalmosesconfigsettingsyaml)
6. [src/external/rag/config/settings.yaml](#6-srcexternalragconfigsettingsyaml)
7. [.env.example](#7-envexample)
8. [Hardcoded Values Analysis](#8-hardcoded-values-analysis)
9. [Summary](#9-summary)

---

## 1. configs/ace_config.yaml

### 1.1 ace.model Section

#### ace.model.provider

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:6` - `provider: "qwen"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:21` - `provider: str = Field(default="qwen", pattern="^(qwen|openai|anthropic)$")`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/llm_provider.py:313` - `provider=config.model.provider` - Creates LLM provider
2. `/home/syk/projects/experiment-plan-design/examples/ace_cycle_example.py:51` - `provider=config.model.provider` - ACE cycle example

---

#### ace.model.model_name

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:7` - `model_name: "qwen-max"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:22` - `model_name: str = Field(default="qwen-max")`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/llm_provider.py:314` - `model_name=config.model.model_name` - LLM initialization
2. `/home/syk/projects/experiment-plan-design/examples/ace_cycle_example.py:52` - `model_name=config.model.model_name` - Example script
3. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:164` - `self.llm.model_name` - Logging model name
4. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:198` - `self.llm.model_name` - Metadata tracking
5. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:217` - `self.llm.model_name` - Update metadata

---

#### ace.model.temperature

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:8` - `temperature: 0.7`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:23` - `temperature: float = Field(default=0.7, ge=0.0, le=2.0)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/llm_provider.py:315` - `temperature=config.model.temperature` - LLM initialization
2. `/home/syk/projects/experiment-plan-design/examples/ace_cycle_example.py:53` - `temperature=config.model.temperature` - Example script
3. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:166` - `getattr(self.llm, 'temperature', None)` - Config logging
4. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:178` - `"temperature": getattr(self.llm, 'temperature', 0.7)` - LLM call tracking
5. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:260` - Similar usage in reflector
6. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:302` - Similar usage in curator

---

#### ace.model.max_tokens

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:9` - `max_tokens: 4096`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:24` - `max_tokens: int = Field(default=4096, gt=0)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/llm_provider.py:316` - `max_tokens=config.model.max_tokens` - LLM initialization
2. `/home/syk/projects/experiment-plan-design/examples/ace_cycle_example.py:54` - `max_tokens=config.model.max_tokens` - Example script
3. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:167` - `getattr(self.llm, 'max_tokens', None)` - Config logging
4. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:179` - `"max_tokens": getattr(self.llm, 'max_tokens', 4000)` - LLM call tracking
5. Similar usages in reflector and curator

---

### 1.2 ace.embedding Section

#### ace.embedding.model

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:13` - `model: "text-embedding-v4"`

**Pydantic Model**:
- **NOT DEFINED** in `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py`

**NOT Used In**:
- ACEConfig in config_loader.py does NOT have an `embedding` field
- This section exists in YAML but is NOT loaded into Pydantic models

**Hardcoded Alternative**:
- `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:496` - Hardcoded `embedding_model: str = "text-embedding-v4"` in factory function
- `/home/syk/projects/experiment-plan-design/src/utils/qwen_embedding.py:22` - Hardcoded default model

**Recommendation**: Add `EmbeddingConfig` to ACEConfig and use throughout

---

#### ace.embedding.batch_size

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:14` - `batch_size: 10`

**Pydantic Model**:
- **NOT DEFINED** in config_loader.py

**Hardcoded Alternative**:
- Embedding operations don't currently batch

---

### 1.3 ace.generator Section

#### ace.generator.max_playbook_bullets

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:19` - `max_playbook_bullets: 50`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:33` - `max_playbook_bullets: int = Field(default=50, gt=0, description="Top-k bullets to retrieve")`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:131` - `top_k=self.config.max_playbook_bullets` - Logging bullet retrieval
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:353` - `top_k=self.config.max_playbook_bullets` - Actual bullet retrieval

---

#### ace.generator.include_examples

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:20` - `include_examples: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:34` - `include_examples: bool = Field(default=True)`

**NOT Used In**:
- Not referenced in generator.py
- Likely intended for future use with example library

---

#### ace.generator.enable_few_shot

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:21` - `enable_few_shot: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:35` - `enable_few_shot: bool = Field(default=True)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:144` - `few_shot_examples if self.config.enable_few_shot else None` - Prompt construction (with perf monitoring)
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py:151` - `few_shot_examples if self.config.enable_few_shot else None` - Prompt construction (without perf monitoring)

---

#### ace.generator.few_shot_count

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:22` - `few_shot_count: 3`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:36` - `few_shot_count: int = Field(default=3, ge=0)`

**NOT Used In**:
- Not referenced in generator.py
- Caller currently decides how many examples to pass

---

#### ace.generator.output_format

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:23` - `output_format: "structured"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:37` - `output_format: str = Field(default="structured", pattern="^(structured|markdown)$")`

**NOT Used In**:
- Not referenced in generator.py
- Parser currently handles both formats automatically

---

### 1.4 ace.reflector Section

#### ace.reflector.max_refinement_rounds

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:27` - `max_refinement_rounds: 5`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:42` - `max_refinement_rounds: int = Field(default=5, ge=1, le=10)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:110` - `max_refinement_rounds=self.config.max_refinement_rounds` - Logging
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:154` - `if self.config.enable_iterative and self.config.max_refinement_rounds > 1:` - Control flow
3. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:157` - `max_rounds=self.config.max_refinement_rounds` - Refinement loop
4. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:161` - `refinement_rounds_completed = self.config.max_refinement_rounds` - Result tracking

---

#### ace.reflector.enable_iterative

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:28` - `enable_iterative: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:43` - `enable_iterative: bool = Field(default=True)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py:154` - `if self.config.enable_iterative and self.config.max_refinement_rounds > 1:` - Controls whether iterative refinement is performed

---

#### ace.reflector.reflection_mode

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:29` - `reflection_mode: "detailed"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:44` - `reflection_mode: str = Field(default="detailed", pattern="^(detailed|concise)$")`

**NOT Used In**:
- Not referenced in reflector.py
- Could be used to control prompt verbosity

---

#### ace.reflector.bullet_tagging

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:30` - `bullet_tagging: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:45` - `bullet_tagging: bool = Field(default=True)`

**NOT Used In**:
- Not referenced in reflector.py
- Bullet tagging always performed (could be made optional)

---

### 1.5 ace.curator Section

#### ace.curator.update_mode

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:34` - `update_mode: "incremental"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:50` - `update_mode: str = Field(default="incremental", pattern="^(incremental|lazy)$")`

**NOT Used In**:
- Not referenced in curator.py
- Could control when deduplication runs (incremental vs lazy)

---

#### ace.curator.deduplication_threshold

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:35` - `deduplication_threshold: 0.85`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:51` - `deduplication_threshold: float = Field(default=0.85, ge=0.0, le=1.0)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:601` - `if similarity >= self.config.deduplication_threshold:` - Duplicate detection
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:629` - `threshold=self.config.deduplication_threshold` - Logging
3. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:661` - `threshold=self.config.deduplication_threshold` - Deduplication function call

---

#### ace.curator.max_playbook_size

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:36` - `max_playbook_size: 200`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:52` - `max_playbook_size: int = Field(default=200, gt=0)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:186` - `if self.playbook_manager.playbook.size > self.config.max_playbook_size:` - Trigger pruning
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:290` - `max_playbook_size=self.config.max_playbook_size` - Pass to prompt
3. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:712` - `max_size = self.config.max_playbook_size` - Pruning logic

---

#### ace.curator.enable_grow_and_refine

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:37` - `enable_grow_and_refine: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:53` - `enable_grow_and_refine: bool = Field(default=True)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:178` - `if self.config.enable_grow_and_refine:` - Controls deduplication

---

#### ace.curator.prune_harmful_bullets

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:38` - `prune_harmful_bullets: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:54` - `prune_harmful_bullets: bool = Field(default=True)`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:187` - `if self.config.prune_harmful_bullets:` - Controls pruning

---

### 1.6 ace.playbook Section

#### ace.playbook.default_path

**Status**: 🔄 INDIRECTLY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:42` - `default_path: "data/playbooks/chemistry_playbook.json"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:63` - `default_path: str = Field(default="data/playbooks/chemistry_playbook.json")`

**Usage Locations**:
- Used via environment variable `DEFAULT_PLAYBOOK_PATH` in `.env.example:31`
- Passed as argument to PlaybookManager in various scripts
- Not directly accessed from config in code

---

#### ace.playbook.sections_config

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:45` - `sections_config: "configs/playbook_sections.yaml"`

**Pydantic Model**:
- **NOT DEFINED** in config_loader.py (loaded separately by SectionManager)

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:38` - Hardcoded path `configs/playbook_sections.yaml`
2. Should use config parameter instead

---

#### ace.playbook.sections / id_prefixes

**Status**: ⚠️ DEPRECATED

**Config Definition**:
- Defined in Pydantic model but NOT in ace_config.yaml

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:64-83` - `sections` and `id_prefixes` fields

**Usage Locations**:
- **DEPRECATED**: Now loaded from `playbook_sections.yaml` via SectionManager
- Old config structure kept for backward compatibility

---

### 1.7 ace.training Section

#### ace.training.num_epochs

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:49` - `num_epochs: 5`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:92` - `num_epochs: int = Field(default=5, ge=1)`

**NOT Used In**:
- Training loop not yet implemented
- Reserved for future offline training feature

---

#### ace.training.batch_size

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:50` - `batch_size: 1`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:93` - `batch_size: int = Field(default=1, ge=1)`

**NOT Used In**:
- Training loop not yet implemented

---

#### ace.training.feedback_source

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:51` - `feedback_source: "llm_judge"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:94` - `feedback_source: str = Field(default="llm_judge", pattern="^(llm_judge|human|auto)$")`

**NOT Used In**:
- Feedback source currently determined at runtime
- Could be used as default in feedback worker

---

#### ace.training.enable_offline_warmup

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:52` - `enable_offline_warmup: false`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:95` - `enable_offline_warmup: bool = Field(default=False)`

**NOT Used In**:
- Offline training not yet implemented

---

### 1.8 ace.evaluation Section

#### ace.evaluation.enable_auto_check

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:56` - `enable_auto_check: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:100` - `enable_auto_check: bool = Field(default=True)`

**NOT Used In**:
- Evaluation system not fully implemented

---

#### ace.evaluation.enable_llm_judge

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:57` - `enable_llm_judge: true`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:101` - `enable_llm_judge: bool = Field(default=True)`

**NOT Used In**:
- Used in workflow but not read from config

---

#### ace.evaluation.evaluation_criteria

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/ace_config.yaml:58-63` - List of criteria

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:102-110` - `evaluation_criteria: List[str]`

**NOT Used In**:
- Criteria hardcoded in feedback prompts

---

## 2. configs/rag_config.yaml

### 2.1 rag.vector_store Section

#### rag.vector_store.type

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:6` - `type: "chroma"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:134` - `type: str = Field(default="chroma", pattern="^(chroma|faiss|pinecone)$")`

**Usage Locations**:
- Loaded but not actively checked (only Chroma implemented)

---

#### rag.vector_store.persist_directory

**Status**: 🔄 INDIRECTLY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:7` - `persist_directory: "data/chroma_db"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:135` - `persist_directory: str = Field(default="data/chroma_db")`

**Usage Locations**:
- Overridden by `.env` variable `CHROMA_PERSIST_DIR`
- Used indirectly via environment

---

#### rag.vector_store.collection_name

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:8` - `collection_name: "experiment_templates"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:136` - `collection_name: str = Field(default="experiment_templates")`

**NOT Used In**:
- Collection name hardcoded in RAG adapter

---

### 2.2 rag.embeddings Section

#### rag.embeddings.model_name

**Status**: ❌ HARDCODED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:12` - `model_name: "BAAI/bge-large-zh-v1.5"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:141` - `model_name: str = Field(default="BAAI/bge-large-zh-v1.5")`

**Hardcoded Behavior**:
- **NOT USED**: Project now uses Qwen embeddings (API-based)
- Should be removed or marked deprecated

---

#### rag.embeddings.device

**Status**: ❌ HARDCODED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:14` - `device: "cpu"`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:142` - `device: str = Field(default="cpu", pattern="^(cpu|cuda)$")`

**Hardcoded Behavior**:
- **NOT USED**: Qwen embeddings are API-based (no device needed)

---

#### rag.embeddings.batch_size

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:17` - `batch_size: 32`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:143` - `batch_size: int = Field(default=32, gt=0)`

**NOT Used In**:
- Qwen API handles batching internally

---

### 2.3 rag.retrieval Section

#### rag.retrieval.top_k

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:21` - `top_k: 5`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:148` - `top_k: int = Field(default=5, gt=0)`

**NOT Used In**:
- RAG adapter uses its own top_k parameter

---

#### rag.retrieval.similarity_threshold

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:22` - `similarity_threshold: 0.7`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:149` - `similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)`

**NOT Used In**:
- Not implemented in current RAG adapter

---

#### rag.retrieval.enable_reranking / reranker_model

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:23-24`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:150-151`

**NOT Used In**:
- Reranking not implemented in adapter

---

### 2.4 rag.document_processing Section

#### rag.document_processing.chunk_size

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:28` - `chunk_size: 512`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:156` - `chunk_size: int = Field(default=500, gt=0)`

**NOT Used In**:
- External RAG system has its own config

---

#### rag.document_processing.chunk_overlap

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:29` - `chunk_overlap: 50`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:157` - `chunk_overlap: int = Field(default=50, ge=0)`

**NOT Used In**:
- External RAG system handles chunking

---

#### rag.document_processing.enable_metadata_extraction / supported_formats

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:30-34`

**Pydantic Model**:
- Not defined in Pydantic model

**NOT Used In**:
- External RAG system configuration

---

### 2.5 rag.template_schema / rag.indexing Sections

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/rag_config.yaml:37-56`

**Pydantic Model**:
- Not defined in Pydantic model

**NOT Used In**:
- These sections are not loaded by ConfigLoader
- May be intended for future use

---

## 3. configs/chatbot_config.yaml

### 3.1 chatbot.llm Section

#### chatbot.llm.provider

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:6` - `provider: "qwen"`

**Pydantic Model**:
- **NOT DEFINED** in Pydantic (loaded via dict by chatbot/config.py)

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:91` - `llm_config = self.config["chatbot"]["llm"]` - Dict access
2. Config validated but accessed directly as dict

---

#### chatbot.llm.model_name

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:7` - `model_name: "qwen-plus"`

**Pydantic Model**:
- **NOT DEFINED** in Pydantic

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:91` - Passed to ChatTongyi initialization
2. Used for model selection in LLM init

---

#### chatbot.llm.temperature / max_tokens

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:8-9`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:95-96` - Model kwargs initialization

---

#### chatbot.llm.enable_thinking

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:10` - `enable_thinking: true`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:100` - `if llm_config.get("enable_thinking", False):` - Enables qwen-plus thinking mode

---

### 3.2 chatbot.moses Section

#### chatbot.moses.max_workers

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:14` - `max_workers: 4`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:63` - `self.moses_wrapper = MOSESToolWrapper(self.config["chatbot"]["moses"], auto_init=False)` - Passed to MOSES wrapper

---

#### chatbot.moses.query_timeout

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:15` - `query_timeout: 600`

**Usage Locations**:
1. Passed to MOSES wrapper, used for query timeout control

---

### 3.3 chatbot.memory Section

#### chatbot.memory.type

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:19` - `type: "sqlite"`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:66` - `self.checkpointer = self._init_checkpointer()` - Determines memory backend

---

#### chatbot.memory.sqlite_path

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:22` - `sqlite_path: "data/chatbot_memory.db"`

**Usage Locations**:
1. Used when memory type is "sqlite" to initialize SqliteSaver

---

### 3.4 chatbot.display Section

#### chatbot.display.show_thinking

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:26` - `show_thinking: true`

**Usage Locations**:
1. Used in CLI to determine whether to show thinking output

---

### 3.5 chatbot.system_prompt

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/chatbot_config.yaml:29-35` - Multi-line system prompt

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/chatbot/chatbot.py:69-72` - `system_prompt = self.config["chatbot"].get("system_prompt", ...)` - Used as state_modifier in agent

---

## 4. configs/playbook_sections.yaml

### 4.1 core_sections Section

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/playbook_sections.yaml:5-52` - Six core sections

**Pydantic Model**:
- **NOT DEFINED** - Loaded as dict by SectionManager

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:43-47` - Loads core sections
2. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:100-107` - `get_id_prefixes()` extracts id_prefix
3. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:173` - `is_section_valid()` checks against core sections

---

### 4.2 custom_sections Section

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/playbook_sections.yaml:54-64` - Initially empty

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:49-53` - Loads custom sections
2. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:119-161` - `add_custom_section()` adds new sections
3. Dynamic section additions saved back to YAML

---

### 4.3 settings Section

#### settings.allow_new_sections

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/playbook_sections.yaml:69` - `allow_new_sections: true`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:39` - `self.allow_new_sections = allow_new_sections if allow_new_sections is not None else sections_config.get("settings", {}).get("allow_new_sections", True)`
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py:359` - `if self.section_manager.is_new_section_allowed()` - Controls new section creation

---

#### settings.new_section_guidelines

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/configs/playbook_sections.yaml:72-110` - Multi-line guidelines

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py:74-98` - `format_sections_for_prompt()` includes guidelines
2. `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/prompts.py` - Used in curator prompts

---

## 5. src/external/MOSES/config/settings.yaml

### 5.1 ontology Section

#### ontology.directory_path

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:2` - `directory_path: data/ontology/`

**Pydantic Model**:
- **Dataclass** in `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:72-84` - `OntologySettings`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:149-153` - Converts relative to absolute path
2. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:84` - `onto_path.append(self.directory_path)` - Registers with owlready2

---

#### ontology.ontology_file_name

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:3` - `ontology_file_name: "chem_ontology.owl"`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:96-97` - `ontology_iri` property constructs IRI
2. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:90` - Used to load ontology

---

#### ontology.base_iri

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:4` - `base_iri: "http://www.test.org/chem_ontologies/"`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:96` - Constructs full ontology IRI
2. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:110-116` - Namespace construction

---

#### ontology.java_exe

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:6` - `java_exe: ""`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:60-69` - Sets `owlready2.JAVA_EXE` globally if provided

---

### 5.2 entity_retrieval Section

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:8-13` - Retrieval parameters

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:161-167` - `ENTITY_RETRIEVAL_CONFIG` dict
2. Used by MOSES query system for entity matching

---

### 5.3 LLM Section

#### LLM.model

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:16` - `model: "qwen3-max"`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:158` - `LLM_CONFIG = yaml_settings["LLM"]`
2. Used throughout MOSES for LLM initialization

---

#### LLM.streaming / temperature / max_tokens

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:20-22`

**Usage Locations**:
1. Part of `LLM_CONFIG` dict, used for LLM configuration in MOSES

---

### 5.4 extractor_examples Section

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:24-26`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:159` - `EXTRACTOR_EXAMPLES_CONFIG`
2. Used by ontology extraction system

---

### 5.5 dataset_construction Section

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.yaml:28-32`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:160` - `DATASET_CONSTRUCTION_CONFIG`
2. Used for dataset generation

---

### 5.6 ASSESSMENT_CRITERIA_CONFIG

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- **HARDCODED** in `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:169-271`

**Usage Locations**:
1. Used by MOSES for ontology quality assessment
2. Should be moved to YAML config

---

## 6. src/external/rag/config/settings.yaml

### 6.1 data Section

#### data.templates_dir

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:7` - `templates_dir: "${PROJECT_ROOT}src/external/rag/data/test_papers"`

**Pydantic Model**:
- **NOT PYDANTIC** - Dataclass in `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:147`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:178` - Replaced with PROJECT_ROOT
2. Used by indexer for document loading

---

### 6.2 embedding Section

#### embedding.provider

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:11` - `provider: "dashscope"`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:64` - `EmbeddingConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:182` - Loaded into `SETTINGS.embedding`
2. Used by RAG system for embedding generation

---

#### embedding.model / text_type / batch_size / dimension

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:12-15`

**Usage Locations**:
1. All loaded into `EmbeddingConfig` dataclass
2. Used by Qwen embedding API

---

### 6.3 vector_store Section

#### vector_store.type / persist_directory / collection_name / distance_metric

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:18-22`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:73` - `VectorStoreConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:183` - Loaded
2. Used by Chroma initialization

---

### 6.4 document_processing Section

#### splitter_type / chunk_size / chunk_overlap / separator

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:25-29`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:81` - `DocumentProcessingConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:184` - Loaded
2. Used by text splitter

---

#### semantic_breakpoint_threshold / semantic_buffer_size

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:32-33`

**Usage Locations**:
1. Used when splitter_type is "semantic"

---

### 6.5 retrieval Section

#### similarity_top_k / rerank_top_n / similarity_threshold

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:36-39`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:91` - `RetrievalConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:185` - Loaded
2. Used by query engine for retrieval

---

### 6.6 reranker Section

#### reranker.provider / model / enabled

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:44-47`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:98` - `RerankerConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:186` - Loaded
2. Controls reranking step in query engine

---

### 6.7 llm Section

#### llm.provider / model / temperature / max_tokens

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:50-54`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:105` - `LLMConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:187` - Loaded
2. Used for answer generation (if implemented)

---

### 6.8 cache Section

#### cache.enabled / type / local_cache_dir / redis_* / collection_name / ttl

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:56-69`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:113` - `CacheConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:188` - Loaded
2. Used by embedding cache system

---

### 6.9 logging Section

#### logging.level / file_path / format

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml:72-75`

**Dataclass**:
- `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:128` - `LoggingConfig`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:189` - Loaded
2. Configures RAG system logging

---

## 7. .env.example

### 7.1 API Keys

#### DASHSCOPE_API_KEY

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:3` - `DASHSCOPE_API_KEY=your_dashscope_api_key_here`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:176` - `dashscope_api_key: Optional[str] = Field(default=None, alias="DASHSCOPE_API_KEY")`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/llm_provider.py:110` - `api_key = os.getenv("DASHSCOPE_API_KEY")` - Qwen provider
2. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:196-204` - `get_dashscope_api_key()` - RAG system
3. `/home/syk/projects/experiment-plan-design/src/utils/qwen_embedding.py:28` - Embedding initialization

---

#### QWEN_BASE_URL

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:8` - `QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`

**Usage Locations**:
1. Used for OpenAI-compatible Qwen API endpoint
2. Referenced in MOSES LLM provider

---

#### OPENAI_API_KEY

**Status**: ⚠️ OPTIONAL

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:11` - `# OPENAI_API_KEY=your_openai_api_key_here`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:177` - `openai_api_key: Optional[str]`

**Usage Locations**:
1. Only used if provider is set to "openai"
2. Currently optional (system uses Qwen)

---

### 7.2 Paths

#### PROJECT_ROOT

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:14` - `PROJECT_ROOT=/home/syk/projects/experiment-plan-design`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:180` - `project_root: Optional[str]`

**Usage Locations**:
1. `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:215` - `project_root = os.getenv("PROJECT_ROOT")` - Config loader
2. `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:53-54` - MOSES path resolution
3. `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py:156-163` - RAG auto-detection
4. Widely used for path construction across project

---

#### MOSES_ROOT

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:15` - `MOSES_ROOT=${PROJECT_ROOT}/src/external/MOSES`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:181` - `moses_root: Optional[str]`

**Usage Locations**:
1. Used for MOSES path resolution
2. Referenced in MOSES integration code

---

#### CHROMA_PERSIST_DIR

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:18` - `CHROMA_PERSIST_DIR=${PROJECT_ROOT}/data/chroma_db`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:182` - `chroma_persist_dir: Optional[str]`

**Usage Locations**:
1. Used by RAG system for vector store persistence
2. Overrides rag_config.yaml setting

---

### 7.3 Logging

#### LOG_LEVEL

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:21` - `LOG_LEVEL=INFO`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:189` - `log_level: str = Field(default="INFO")`

**Usage Locations**:
1. Used by logging configuration throughout project

---

#### LOG_FILE

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:22` - `LOG_FILE=${PROJECT_ROOT}/logs/app.log`

**Usage Locations**:
1. Main application log file path

---

### 7.4 Model Configuration

#### DEFAULT_LLM_PROVIDER

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:25` - `DEFAULT_LLM_PROVIDER=qwen`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:185` - `default_llm_provider: str = Field(default="qwen")`

**Usage Locations**:
1. Fallback when config doesn't specify provider

---

#### DEFAULT_LLM_MODEL

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:26` - `DEFAULT_LLM_MODEL=qwen-max`

**Pydantic Model**:
- `/home/syk/projects/experiment-plan-design/src/utils/config_loader.py:186` - `default_llm_model: str = Field(default="qwen-max")`

**Usage Locations**:
1. Default model for ACE framework

---

#### MOSES_LLM_MODEL

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:27` - `MOSES_LLM_MODEL=qwen-plus`

**Usage Locations**:
1. Model used by MOSES (cost optimization)

---

#### DEFAULT_EMBEDDING_MODEL

**Status**: ❌ HARDCODED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:28` - `DEFAULT_EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5`

**NOT Used In**:
- **DEPRECATED**: System now uses Qwen embeddings (API-based)
- This variable is not read by code

---

### 7.5 Playbook Configuration

#### DEFAULT_PLAYBOOK_PATH

**Status**: ✅ ACTIVELY USED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:31` - `DEFAULT_PLAYBOOK_PATH=${PROJECT_ROOT}/data/playbooks/chemistry_playbook.json`

**Usage Locations**:
1. Used as default when playbook path not specified
2. Referenced in workflow scripts

---

### 7.6 Development Settings

#### DEBUG

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:34` - `DEBUG=False`

**NOT Used In**:
- Not read by application code
- Could be used for debug mode toggle

---

#### ENABLE_CACHE

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:35` - `ENABLE_CACHE=True`

**NOT Used In**:
- Caching enabled/disabled in individual config files
- Not a global setting currently

---

#### CACHE_DIR

**Status**: ⚠️ DEFINED BUT UNUSED

**Config Definition**:
- `/home/syk/projects/experiment-plan-design/.env.example:36` - `CACHE_DIR=${PROJECT_ROOT}/.cache`

**NOT Used In**:
- Cache directories specified in individual configs
- Not used as global cache directory

---

## 8. Hardcoded Values Analysis

### 8.1 Hardcoded in Generator

**Location**: `/home/syk/projects/experiment-plan-design/src/ace_framework/generator/generator.py`

1. **Line 132**: `min_similarity=0.3` - Should be config parameter
2. **Line 356**: `min_similarity=0.3` - Duplicate hardcoding
3. **Line 496**: `embedding_model: str = "text-embedding-v4"` - Should use ace.embedding.model

---

### 8.2 Hardcoded in Reflector

**Location**: `/home/syk/projects/experiment-plan-design/src/ace_framework/reflector/reflector.py`

1. **Reflection mode**: Always uses "detailed" - Should check config.reflector.reflection_mode
2. **Bullet tagging**: Always enabled - Should check config.reflector.bullet_tagging

---

### 8.3 Hardcoded in Curator

**Location**: `/home/syk/projects/experiment-plan-design/src/ace_framework/curator/curator.py`

1. **Line 723**: `threshold=0.3` - Helpfulness threshold for pruning should be configurable
2. **Line 729**: `b.metadata.total_uses >= 3` - Minimum uses threshold should be configurable
3. **Update mode**: Config exists but not used to control deduplication timing

---

### 8.4 Hardcoded in Section Manager

**Location**: `/home/syk/projects/experiment-plan-design/src/utils/section_manager.py`

1. **Line 38**: `config_path = project_root / "configs/playbook_sections.yaml"` - Should use ace.playbook.sections_config

---

### 8.5 Hardcoded in RAG Adapter

**Location**: `/home/syk/projects/experiment-plan-design/src/workflow/rag_adapter.py`

1. Collection names, similarity thresholds - Should use rag_config parameters

---

### 8.6 Hardcoded Embedding Models

**Multiple Locations**:

1. `/home/syk/projects/experiment-plan-design/src/utils/qwen_embedding.py:22` - `model: str = "text-embedding-v4"`
2. Should use ace.embedding.model config

---

### 8.7 MOSES Assessment Criteria

**Location**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/config/settings.py:169-271`

- **Entire assessment criteria config is hardcoded in Python**
- Should be moved to YAML for easier modification

---

## 9. Summary

### 9.1 Configuration Health Overview

| Config File | Total Parameters | Actively Used | Defined But Unused | Hardcoded Alternative |
|-------------|------------------|---------------|---------------------|----------------------|
| ace_config.yaml | 28 | 15 (54%) | 10 (36%) | 3 (10%) |
| rag_config.yaml | 20 | 3 (15%) | 15 (75%) | 2 (10%) |
| chatbot_config.yaml | 9 | 9 (100%) | 0 (0%) | 0 (0%) |
| playbook_sections.yaml | 8 | 8 (100%) | 0 (0%) | 0 (0%) |
| MOSES settings.yaml | 16 | 16 (100%) | 0 (0%) | 0 (0%) |
| RAG settings.yaml | 23 | 23 (100%) | 0 (0%) | 0 (0%) |
| .env.example | 15 | 10 (67%) | 3 (20%) | 2 (13%) |

---

### 9.2 Critical Issues

#### High Priority

1. **ace.embedding section**: Defined in YAML but NOT loaded into Pydantic models - Breaks config integrity
2. **rag_config.yaml**: Most parameters unused because RAG uses separate external config
3. **Hardcoded similarity thresholds**: Multiple locations use `0.3`, should be configurable
4. **Section config path**: Hardcoded in section_manager.py instead of using ace.playbook.sections_config

#### Medium Priority

1. **Generator few_shot_count**: Config exists but not used
2. **Generator output_format**: Config exists but not used
3. **Reflector reflection_mode**: Config exists but not used
4. **Reflector bullet_tagging**: Config exists but not used
5. **Curator update_mode**: Config exists but not used
6. **Training/Evaluation configs**: All unused (feature not implemented)

#### Low Priority

1. **DEBUG/ENABLE_CACHE**: Defined in .env but not read
2. **DEFAULT_EMBEDDING_MODEL**: Deprecated (now uses Qwen API)
3. **Assessment criteria**: Should move from Python to YAML

---

### 9.3 Recommendations

#### Immediate Actions

1. **Add ace.embedding to ACEConfig Pydantic model**
2. **Use ace.playbook.sections_config in section_manager**
3. **Make similarity thresholds configurable**
4. **Remove or use undefined rag_config parameters**

#### Short-term Actions

1. **Implement unused generator configs** (few_shot_count, output_format)
2. **Implement unused reflector configs** (reflection_mode, bullet_tagging)
3. **Implement curator update_mode** (incremental vs lazy deduplication)
4. **Clean up deprecated configs** (DEFAULT_EMBEDDING_MODEL)

#### Long-term Actions

1. **Unify RAG configs**: Merge rag_config.yaml with external RAG settings
2. **Implement training system**: Use training/evaluation configs
3. **Move MOSES criteria to YAML**: Better maintainability
4. **Add config validation**: Warn about unused parameters

---

### 9.4 Usage Patterns

#### Well-Designed Configs

1. **chatbot_config.yaml**: 100% usage, clean dict access pattern
2. **playbook_sections.yaml**: Dynamic section management, well-utilized
3. **MOSES settings.yaml**: Complete integration with dataclass pattern
4. **RAG settings.yaml**: Full utilization with dataclass pattern

#### Needs Improvement

1. **ace_config.yaml**: Many unused parameters, missing embedding config
2. **rag_config.yaml**: Duplicate/unused parameters due to external RAG system
3. **.env.example**: Some deprecated variables not cleaned up

---

### 9.5 Config Loading Patterns

#### Pattern 1: Pydantic (ACE)
```python
from utils.config_loader import get_ace_config
config = get_ace_config()
value = config.model.temperature
```

#### Pattern 2: Dict (Chatbot)
```python
from chatbot.config import load_config
config = load_config()
value = config["chatbot"]["llm"]["temperature"]
```

#### Pattern 3: Dataclass (MOSES, RAG)
```python
from MOSES.config.settings import LLM_CONFIG
value = LLM_CONFIG["temperature"]
```

#### Pattern 4: YAML + Manager (Sections)
```python
from utils.section_manager import SectionManager
manager = SectionManager()
sections = manager.get_sections()
```

---

## 10. Next Steps

1. **Fix ace.embedding configuration** (add to Pydantic model)
2. **Create unified config health check script**
3. **Implement unused config parameters** or document as "reserved for future"
4. **Add config migration guide** for deprecated parameters
5. **Set up config validation tests** to catch unused parameters
6. **Document config override precedence** (env > yaml > defaults)

---

**Report End**
