# RAG Configuration Documentation Index

This directory contains comprehensive documentation about how RAG configuration parameters are used throughout the codebase.

## Documentation Files

### 1. RAG_CONFIG_QUICK_REFERENCE.md
**Quick lookup guide for common RAG configuration tasks**

Covers:
- File locations
- Configuration load chain (component diagram)
- Most important parameters (for indexing and querying)
- Key configuration sections with examples
- Common adjustments (faster indexing, better quality, etc.)
- Parameter dependencies
- Integration with workflow
- Troubleshooting tips

**Use this when:** You need a quick reference or want to understand how a parameter affects performance.

---

### 2. RAG_CONFIG_USAGE_REPORT.md
**Comprehensive mapping of all RAG configuration parameters to their usage locations**

Covers:
- Overview of configuration files and schema
- Detailed parameter usage for all 9 sections:
  - Data configuration (templates_dir)
  - Embedding configuration (model, batch_size, text_type, dimension)
  - Vector store configuration (type, persist_directory, collection_name, distance_metric)
  - Document processing (splitter_type, chunk_size, chunk_overlap, separator, semantic settings)
  - Retrieval (similarity_top_k, rerank_top_n, similarity_threshold)
  - Reranker (provider, model, enabled)
  - LLM (provider, model, temperature, max_tokens)
  - Cache (enabled, type, local_cache_dir, redis settings, collection_name, ttl)
  - Logging (level, file_path, format)
- Integration points with workflow
- Configuration load flow
- Summary table of all parameters
- Key observations about usage

**Use this when:** You need to understand the complete picture of configuration usage.

---

### 3. RAG_CONFIG_CODE_EXAMPLES.md
**Exact code usage examples for each configuration parameter**

Covers:
- Detailed code snippets showing how each parameter is used
- File paths and line numbers
- Effect of each parameter
- Configuration loading and initialization
- Global SETTINGS instance access

**Use this when:** You need to see the exact code that uses a parameter.

---

## Quick Navigation

### By Use Case

**I want to...**

- **Adjust performance**
  - See: `RAG_CONFIG_QUICK_REFERENCE.md` → "Common Adjustments"
  - Examples: Faster indexing, better quality, faster queries, reduce costs

- **Understand a specific parameter**
  - See: `RAG_CONFIG_CODE_EXAMPLES.md` → Search for the parameter name
  - Shows exact code location and effect

- **See where a parameter is used**
  - See: `RAG_CONFIG_USAGE_REPORT.md` → Search for the parameter name
  - Lists all usage locations with line numbers

- **Understand the configuration system**
  - See: `RAG_CONFIG_USAGE_REPORT.md` → "Configuration Load Flow"
  - Or: `RAG_CONFIG_CODE_EXAMPLES.md` → "Configuration Loading & Initialization"

- **Integrate RAG with my code**
  - See: `RAG_CONFIG_QUICK_REFERENCE.md` → "Integration with Workflow"
  - Shows how RAGAdapter wraps LargeRAG

- **Troubleshoot an issue**
  - See: `RAG_CONFIG_QUICK_REFERENCE.md` → "Troubleshooting"
  - Common problems and solutions

### By Parameter Category

**Embedding Parameters** (embedding.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 1
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 2

**Vector Store Parameters** (vector_store.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 2
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 3

**Document Processing Parameters** (document_processing.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 3
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 4

**Retrieval Parameters** (retrieval.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 4
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 5

**Reranker Parameters** (reranker.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 5
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 6

**LLM Parameters** (llm.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 6
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 7

**Cache Parameters** (cache.*)
- See: `RAG_CONFIG_CODE_EXAMPLES.md` → Section 7
- Or: `RAG_CONFIG_USAGE_REPORT.md` → Section 8

**Logging Parameters** (logging.*)
- See: `RAG_CONFIG_USAGE_REPORT.md` → Section 9
- (Not actively used in code)

---

## Configuration File Locations

### Main Configuration
- **YAML**: `/src/external/rag/config/settings.yaml`
- **Python Schema**: `/src/external/rag/config/settings.py`

### RAG Components Using Configuration
- **Indexer**: `/src/external/rag/core/indexer.py`
- **Query Engine**: `/src/external/rag/core/query_engine.py`
- **Main Class**: `/src/external/rag/largerag.py`

### Workflow Integration
- **RAG Adapter**: `/src/workflow/rag_adapter.py`
- **Build Script**: `/build_rag_index.py`
- **Integration Test**: `/test_rag_integration.py`

---

## Key Concepts

### Configuration Load Chain
```
YAML file (settings.yaml)
    ↓ [yaml.safe_load]
YAML dictionary
    ↓ [load_settings() in settings.py]
Pydantic dataclass instances
    ↓ [LargeRAGSettings object]
Global SETTINGS instance
    ↓ [imported as self.settings in components]
Used in LargeRAGIndexer & LargeRAGQueryEngine
```

### Component Responsibilities

**LargeRAGIndexer** uses config for:
- Embedding model and batch size
- Vector store path and collection name
- Document chunking strategy
- Cache setup

**LargeRAGQueryEngine** uses config for:
- LLM model and parameters
- Reranker model and enabled flag
- Retrieval parameters (similarity_top_k, etc.)

---

## Important Parameters by Priority

### Critical (Affect Functionality)
1. **embedding.model** - Which embedding model to use
2. **vector_store.persist_directory** - Where vectors are stored
3. **vector_store.collection_name** - Index namespace
4. **document_processing.splitter_type** - How documents are chunked
5. **retrieval.similarity_top_k** - Vector search candidates
6. **reranker.enabled** - Whether to rerank results
7. **llm.model** - Which LLM for response generation
8. **cache.enabled** - Whether to cache embeddings

### Important (Affect Performance/Quality)
1. **embedding.batch_size** - API batching
2. **document_processing.chunk_size** - Chunk size
3. **retrieval.rerank_top_n** - Final result count
4. **retrieval.similarity_threshold** - Score filtering
5. **llm.max_tokens** - Response length limit
6. **cache.type** - Local vs Redis cache

### Nice-to-Have (Affect Behavior)
1. **llm.temperature** - Output randomness
2. **cache.local_cache_dir** - Cache location
3. **vector_store.distance_metric** - Distance metric

---

## Common Configuration Patterns

### For Development/Testing
```yaml
# Fast indexing, local resources
document_processing:
  splitter_type: "token"
  chunk_size: 512
retrieval:
  similarity_top_k: 20
  rerank_top_n: 5
llm:
  model: "qwen-plus"
cache:
  type: "local"
  enabled: true
```

### For Production Quality
```yaml
# Higher quality, reranking enabled
retrieval:
  similarity_top_k: 50
  rerank_top_n: 10
  similarity_threshold: 0.7
reranker:
  enabled: true
llm:
  model: "qwen-max"
```

### For Cost Optimization
```yaml
# Lower costs with acceptable quality
embedding:
  batch_size: 5  # Avoid rate limits
retrieval:
  similarity_top_k: 20
  rerank_top_n: 5
llm:
  model: "qwen-plus"
cache:
  type: "local"
  enabled: true
```

---

## Testing Configuration Changes

1. **Edit configuration**:
   ```bash
   # Edit the YAML file
   vim src/external/rag/config/settings.yaml
   ```

2. **Rebuild index** (if changing document processing):
   ```bash
   python build_rag_index.py
   ```

3. **Test queries**:
   ```bash
   python src/external/rag/examples/2_query_and_retrieve.py
   ```

4. **Check results** - Look for:
   - Indexing speed (time taken)
   - Retrieval quality (relevance scores)
   - Query latency (time to respond)

---

## Related Documentation

- **Main Project README**: See project root for overview
- **RAG Architecture**: See `/src/external/rag/` for implementation details
- **Workflow Integration**: See `/src/workflow/` for how RAG fits in pipeline
- **ACE Framework**: See project CLAUDE.md for context

---

## Document Statistics

| Document | Size | Sections | Parameters |
|----------|------|----------|------------|
| Quick Reference | 7.0 KB | 10 | All (summarized) |
| Usage Report | 28 KB | 10 | All (detailed) |
| Code Examples | 22 KB | 8 | All (with code) |
| **Total** | **57 KB** | - | - |

---

## Last Updated

Generated: October 28, 2025

These documents comprehensively map all RAG configuration parameters to their usage in the codebase.
