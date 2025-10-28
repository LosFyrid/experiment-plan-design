# RAG Configuration Parameters Usage Report

## Overview
This document provides a comprehensive mapping of all RAG configuration parameters from `src/external/rag/config/settings.yaml` to their actual usage locations in the codebase.

## Configuration Files

### 1. RAG Settings YAML
**Location:** `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml`

This is the main configuration file with the following structure:
- `data` - Data paths
- `embedding` - Embedding model configuration
- `vector_store` - Vector database configuration
- `document_processing` - Document chunking strategy
- `retrieval` - Retrieval parameters
- `reranker` - Reranker model configuration
- `llm` - LLM model configuration
- `cache` - Caching mechanism configuration
- `logging` - Logging configuration

### 2. Settings Schema Definition
**Location:** `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py`

Defines Python dataclasses for type-safe configuration:
- `EmbeddingConfig`
- `VectorStoreConfig`
- `DocumentProcessingConfig`
- `RetrievalConfig`
- `RerankerConfig`
- `LLMConfig`
- `CacheConfig`
- `LoggingConfig`
- `LargeRAGSettings`

---

## Detailed Parameter Usage

### 1. DATA CONFIGURATION

#### Parameter: `templates_dir`
**YAML Definition:**
```yaml
data:
  templates_dir: "${PROJECT_ROOT}src/external/rag/data/test_papers"
```

**Usage Locations:**
- **Not directly used** in core RAG components
- Used in build scripts and examples for file path resolution
- Referenced in build_rag_index.py and examples/1_build_index.py

**Files:**
- `/home/syk/projects/experiment-plan-design/build_rag_index.py` (line 25)
- `/home/syk/projects/experiment-plan-design/src/external/rag/examples/1_build_index.py` (line 66)

---

### 2. EMBEDDING CONFIGURATION

#### Parameter: `provider`
**YAML Definition:**
```yaml
embedding:
  provider: "dashscope"  # Fixed value
```

**Usage:** Defined in schema but not actively used in code (fixed to "dashscope")

#### Parameter: `model`
**YAML Definition:**
```yaml
embedding:
  model: "text-embedding-v3"  # Qwen embedding model
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 80)
   ```python
   self.embed_model = RetryableDashScopeEmbedding(
       model_name=self.settings.embedding.model,  # LINE 80
       text_type=DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT,
       api_key=self.api_key,
       embed_batch_size=self.settings.embedding.batch_size,
   )
   ```

#### Parameter: `text_type`
**YAML Definition:**
```yaml
embedding:
  text_type: "document"  # document or query
```

**Usage:** Schema-defined but hardcoded in indexer.py (line 81)
```python
text_type=DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT,
```

#### Parameter: `batch_size`
**YAML Definition:**
```yaml
embedding:
  batch_size: 10  # Reduce to avoid API rate limiting
```

**Usage Locations:**

1. **LargeRAGIndexer.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 83)
   ```python
   embed_batch_size=self.settings.embedding.batch_size,  # LINE 83
   ```
   - Controls batch size for embedding API calls
   - Smaller values (10) reduce rate limiting issues
   - Used with `RetryableDashScopeEmbedding` wrapper

2. **Comment in example** - `/home/syk/projects/experiment-plan-design/src/external/rag/examples/1_build_index.py` (line 96)
   ```python
   print("  [3] Embedding     - DashScope text-embedding-v3 (1024维)")
   ```

#### Parameter: `dimension`
**YAML Definition:**
```yaml
embedding:
  dimension: 1024  # Vector dimension
```

**Usage:** Schema-defined but not actively used (DashScope determines this)

---

### 3. VECTOR STORE CONFIGURATION

#### Parameter: `type`
**YAML Definition:**
```yaml
vector_store:
  type: "chroma"  # Fixed value
```

**Usage:** Hardcoded in implementation (not configurable)

#### Parameter: `persist_directory`
**YAML Definition:**
```yaml
vector_store:
  persist_directory: "${PROJECT_ROOT}src/external/rag/data/chroma_db"
```

**Usage Locations:**

1. **LargeRAGIndexer.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 89-91)
   ```python
   self.chroma_client = chromadb.PersistentClient(
       path=self.settings.vector_store.persist_directory  # LINE 90
   )
   ```
   - Creates persistent Chroma database client
   - Determines where vector indices are stored on disk
   - Survives restart (persistent storage)

2. **LargeRAGIndexer.get_index_stats()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 250)
   ```python
   "persist_directory": self.settings.vector_store.persist_directory,
   ```

3. **Examples** - `/home/syk/projects/experiment-plan-design/src/external/rag/examples/1_build_index.py` (line 227)
   ```python
   print(f"  {index_stats.get('persist_directory', 'N/A')}")
   ```

#### Parameter: `collection_name`
**YAML Definition:**
```yaml
vector_store:
  collection_name: "experiment_plan_templates_v1"
```

**Usage Locations:**

1. **LargeRAGIndexer.build_index()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 197-200)
   ```python
   collection = self.chroma_client.get_or_create_collection(
       name=self.settings.vector_store.collection_name,  # LINE 198
       metadata={"hnsw:space": self.settings.vector_store.distance_metric}
   )
   ```
   - Creates or retrieves Chroma collection
   - Must be unique within persist directory
   - Used as namespace for related documents

2. **LargeRAGIndexer.load_index()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 220-221)
   ```python
   collection = self.chroma_client.get_collection(
       name=self.settings.vector_store.collection_name
   )
   ```

3. **LargeRAGIndexer.get_index_stats()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 248)
   ```python
   "collection_name": self.settings.vector_store.collection_name,
   ```

4. **Examples** - `/home/syk/projects/experiment-plan-design/src/external/rag/examples/1_build_index.py` (line 131)
   ```python
   print(f"  Collection 名称: {index_stats.get('collection_name', 'N/A')}")
   ```

#### Parameter: `distance_metric`
**YAML Definition:**
```yaml
vector_store:
  distance_metric: "cosine"  # cosine, l2, ip
```

**Usage Locations:**

1. **LargeRAGIndexer.build_index()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 199)
   ```python
   metadata={"hnsw:space": self.settings.vector_store.distance_metric}
   ```
   - Passed to Chroma as HNSW space (distance metric)
   - "cosine" = cosine similarity
   - "l2" = Euclidean distance
   - "ip" = inner product

---

### 4. DOCUMENT PROCESSING CONFIGURATION

#### Parameter: `splitter_type`
**YAML Definition:**
```yaml
document_processing:
  splitter_type: "token"  # token / semantic / sentence
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 99-125)
   ```python
   splitter_type = self.settings.document_processing.splitter_type  # LINE 99
   
   if splitter_type == "semantic":
       # semantic splitting
   elif splitter_type == "sentence":
       # sentence splitting
   else:  # "token" (default)
       # token splitting
   ```
   - Determines chunking strategy
   - "semantic" = breaks at semantic boundaries (expensive)
   - "sentence" = preserves sentence integrity
   - "token" = breaks at token boundaries (default)

#### Parameter: `chunk_size`
**YAML Definition:**
```yaml
document_processing:
  chunk_size: 512  # In tokens
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - Used in all three splitter types:

   - Semantic splitter (line 106): Not directly used
   - Sentence splitter (line 114):
     ```python
     splitter = SentenceSplitter(
         chunk_size=self.settings.document_processing.chunk_size,  # LINE 114
         chunk_overlap=self.settings.document_processing.chunk_overlap,
     )
     ```
   - Token splitter (line 122):
     ```python
     splitter = SentenceSplitter(
         chunk_size=self.settings.document_processing.chunk_size,  # LINE 122
         chunk_overlap=self.settings.document_processing.chunk_overlap,
     )
     ```

2. **Logging in _init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 117, 125)
   ```python
   logger.info(f"Using sentence splitter (size={self.settings.document_processing.chunk_size})")
   logger.info(f"Using token-based splitter (size={self.settings.document_processing.chunk_size}, overlap={...})")
   ```

3. **Example documentation** - `/home/syk/projects/experiment-plan-design/src/external/rag/examples/1_build_index.py` (line 95)
   ```python
   print("  [2] 文档分块      - SentenceSplitter (chunk_size=512, overlap=50)")
   ```

#### Parameter: `chunk_overlap`
**YAML Definition:**
```yaml
document_processing:
  chunk_overlap: 50  # In tokens
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 115, 123)
   ```python
   chunk_overlap=self.settings.document_processing.chunk_overlap,
   ```
   - Used in both SentenceSplitter initializations
   - Provides context overlap between chunks

2. **Logging** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 125)
   ```python
   logger.info(f"Using token-based splitter (size={...}, overlap={self.settings.document_processing.chunk_overlap})")
   ```

#### Parameter: `separator`
**YAML Definition:**
```yaml
document_processing:
  separator: "\n\n"  # Chunking separator
```

**Usage:** Schema-defined in `DocumentProcessingConfig` but not actively used in code

#### Parameter: `semantic_breakpoint_threshold`
**YAML Definition:**
```yaml
document_processing:
  semantic_breakpoint_threshold: 0.5  # Semantic breakpoint threshold (0-1)
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 106-109)
   ```python
   if splitter_type == "semantic":
       from llama_index.core.node_parser import SemanticSplitterNodeParser
       splitter = SemanticSplitterNodeParser(
           embed_model=self.embed_model,
           breakpoint_percentile_threshold=self.settings.document_processing.semantic_breakpoint_threshold,  # LINE 106
           buffer_size=self.settings.document_processing.semantic_buffer_size,
       )
       logger.info(f"Using semantic splitter (threshold={self.settings.document_processing.semantic_breakpoint_threshold})")
   ```
   - Only used when `splitter_type == "semantic"`
   - Controls sensitivity of semantic boundaries
   - Higher values = stricter boundaries

#### Parameter: `semantic_buffer_size`
**YAML Definition:**
```yaml
document_processing:
  semantic_buffer_size: 1  # Buffer size for semantic splitting
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 107-108)
   ```python
   buffer_size=self.settings.document_processing.semantic_buffer_size,  # LINE 107
   ```
   - Only used when `splitter_type == "semantic"`
   - Controls context buffer around breakpoints

---

### 5. RETRIEVAL CONFIGURATION

#### Parameter: `similarity_top_k`
**YAML Definition:**
```yaml
retrieval:
  similarity_top_k: 30  # Vector retrieval recall count
```

**Usage Locations:**

1. **LargeRAGQueryEngine._build_query_engine()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 59-61)
   ```python
   retriever_kwargs = {
       "index": self.index,
       "similarity_top_k": self.settings.retrieval.similarity_top_k,  # LINE 61
   }
   ```
   - Number of candidates retrieved from vector search
   - Larger value = better recall, slower retrieval
   - Used in VectorIndexRetriever

2. **LargeRAGQueryEngine.get_similar_documents()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 121-122, 131, 134)
   ```python
   required_candidates = max(
       final_top_k * 2,  # candidate pool should be 2x final output
       self.settings.retrieval.similarity_top_k  # LINE 121
   )
   
   if required_candidates > self.settings.retrieval.similarity_top_k:  # LINE 131
       logger.info(
           f"Auto-adjusted similarity_top_k from {self.settings.retrieval.similarity_top_k} "  # LINE 134
           f"to {required_candidates} to satisfy top_k={final_top_k}"
       )
   ```
   - Automatically adjusted upward if user requests more results
   - Ensures reranker has enough candidates

#### Parameter: `rerank_top_n`
**YAML Definition:**
```yaml
retrieval:
  rerank_top_n: 8  # Reranker final return count
```

**Usage Locations:**

1. **LargeRAGQueryEngine.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 47-51)
   ```python
   if self.settings.reranker.enabled:
       self.reranker = DashScopeRerank(
           model=self.settings.reranker.model,
           api_key=self.api_key,
           top_n=self.settings.retrieval.rerank_top_n,  # LINE 50
       )
   ```
   - Number of results returned after reranking
   - Passed to DashScopeRerank

2. **LargeRAGQueryEngine.get_similar_documents()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 115, 151)
   ```python
   final_top_k = top_k or self.settings.retrieval.rerank_top_n  # LINE 115
   
   reranker = DashScopeRerank(
       model=self.settings.reranker.model,
       api_key=self.api_key,
       top_n=max(final_top_k, self.settings.retrieval.rerank_top_n),  # LINE 151
   )
   ```
   - Used as default when no explicit top_k provided
   - Dynamically adjusted upward if needed

#### Parameter: `similarity_threshold`
**YAML Definition:**
```yaml
retrieval:
  similarity_threshold: 0.5  # Similarity threshold (filter low-quality docs)
```

**Usage Locations:**

1. **LargeRAGQueryEngine._build_query_engine()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 65-67)
   ```python
   if self.settings.retrieval.similarity_threshold > 0:
       retriever_kwargs["similarity_cutoff"] = self.settings.retrieval.similarity_threshold  # LINE 66
       logger.info(f"Similarity threshold enabled: {self.settings.retrieval.similarity_threshold}")
   ```

2. **LargeRAGQueryEngine.get_similar_documents()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 138-139)
   ```python
   if self.settings.retrieval.similarity_threshold > 0:
       retriever_kwargs["similarity_cutoff"] = self.settings.retrieval.similarity_threshold  # LINE 139
   ```
   - Filters results to only include scores above threshold
   - Only applied when > 0
   - Recommended: 0.6-0.8 (conservative filtering)

---

### 6. RERANKER CONFIGURATION

#### Parameter: `provider`
**YAML Definition:**
```yaml
reranker:
  provider: "dashscope"  # Fixed value
```

**Usage:** Schema-defined but not actively used (fixed to "dashscope")

#### Parameter: `model`
**YAML Definition:**
```yaml
reranker:
  model: "gte-rerank-v2"  # Qwen reranker model
```

**Usage Locations:**

1. **LargeRAGQueryEngine.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 47-48)
   ```python
   if self.settings.reranker.enabled:
       self.reranker = DashScopeRerank(
           model=self.settings.reranker.model,  # LINE 48
   ```

2. **LargeRAGQueryEngine.get_similar_documents()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (line 149)
   ```python
   reranker = DashScopeRerank(
       model=self.settings.reranker.model,  # LINE 149
   ```

#### Parameter: `enabled`
**YAML Definition:**
```yaml
reranker:
  enabled: true  # Whether to enable reranker
```

**Usage Locations:**

1. **LargeRAGQueryEngine.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 46-51)
   ```python
   self.reranker = None
   if self.settings.reranker.enabled:  # LINE 46
       self.reranker = DashScopeRerank(...)
   ```

2. **LargeRAGQueryEngine._build_query_engine()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (line 72)
   ```python
   postprocessors = [self.reranker] if self.reranker else []
   ```

3. **Test** - `/home/syk/projects/experiment-plan-design/src/external/rag/tests/test_query_engine.py` (line 53)
   ```python
   if query_engine.settings.reranker.enabled:
       assert query_engine.reranker is not None
   ```

---

### 7. LLM CONFIGURATION

#### Parameter: `provider`
**YAML Definition:**
```yaml
llm:
  provider: "dashscope"  # Fixed value
```

**Usage:** Schema-defined but not actively used (fixed to "dashscope")

#### Parameter: `model`
**YAML Definition:**
```yaml
llm:
  model: "qwen-plus"  # qwen-plus or qwen-max
```

**Usage Locations:**

1. **LargeRAGQueryEngine.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (lines 37-42)
   ```python
   self.llm = DashScope(
       model_name=self.settings.llm.model,  # LINE 38
       api_key=self.api_key,
       temperature=self.settings.llm.temperature,
       max_tokens=self.settings.llm.max_tokens,
   )
   ```
   - Model used for RAG query response generation
   - "qwen-plus" = cost-optimized
   - "qwen-max" = higher quality but more expensive

#### Parameter: `temperature`
**YAML Definition:**
```yaml
llm:
  temperature: 0  # Deterministic output
```

**Usage Locations:**

1. **LargeRAGQueryEngine.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (line 40)
   ```python
   temperature=self.settings.llm.temperature,  # LINE 40
   ```
   - Passed to DashScope LLM
   - 0 = deterministic output
   - Higher values = more creative

#### Parameter: `max_tokens`
**YAML Definition:**
```yaml
llm:
  max_tokens: 2000  # Maximum response length
```

**Usage Locations:**

1. **LargeRAGQueryEngine.__init__()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/query_engine.py` (line 41)
   ```python
   max_tokens=self.settings.llm.max_tokens,  # LINE 41
   ```
   - Maximum length of LLM response
   - Limits generation length

---

### 8. CACHE CONFIGURATION

#### Parameter: `enabled`
**YAML Definition:**
```yaml
cache:
  enabled: true  # Whether to enable caching
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 134)
   ```python
   if self.settings.cache.enabled:  # LINE 134
       if self.settings.cache.type == "local":
           # configure local cache
       elif self.settings.cache.type == "redis":
           # configure redis cache
   ```
   - Master switch for caching
   - When disabled, proceeds without cache

#### Parameter: `type`
**YAML Definition:**
```yaml
cache:
  type: "local"  # local (recommended) or redis
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 135-169)
   ```python
   if self.settings.cache.type == "local":  # LINE 135
       # local cache implementation
       try:
           local_cache = LlamaIndexLocalCache(
               cache_dir=self.settings.cache.local_cache_dir,
               collection_name=self.settings.cache.collection_name,
           )
           cache = IngestionCache(
               cache=local_cache,
               collection=self.settings.cache.collection_name,
           )
   
   elif self.settings.cache.type == "redis":  # LINE 151
       # redis cache implementation
       cache = IngestionCache(
           cache=RedisKVStore.from_host_and_port(
               host=self.settings.cache.redis_host,
               port=self.settings.cache.redis_port,
           ),
           collection=self.settings.cache.collection_name,
       )
   else:
       logger.warning(f"Unknown cache type: {self.settings.cache.type}")
   ```

#### Parameter: `local_cache_dir`
**YAML Definition:**
```yaml
cache:
  local_cache_dir: "${PROJECT_ROOT}src/external/rag/data/cache"
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 139-140)
   ```python
   local_cache = LlamaIndexLocalCache(
       cache_dir=self.settings.cache.local_cache_dir,  # LINE 139
       collection_name=self.settings.cache.collection_name,
   )
   logger.info(f"Local file cache initialized at: {self.settings.cache.local_cache_dir}")
   ```
   - Directory where embedding cache is stored
   - Uses pickle files (pickle format)
   - No additional server required

2. **Example documentation** - `/home/syk/projects/experiment-plan-design/src/external/rag/examples/1_build_index.py` (line 198)
   ```python
   print("  ✓ 缓存位置: src/tools/largerag/data/cache/")
   ```

#### Parameter: `redis_host`
**YAML Definition:**
```yaml
cache:
  redis_host: "localhost"
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 159)
   ```python
   cache=RedisKVStore.from_host_and_port(
       host=self.settings.cache.redis_host,  # LINE 159
       port=self.settings.cache.redis_port,
   )
   ```
   - Only used when `cache.type == "redis"`
   - Redis server hostname/IP

#### Parameter: `redis_port`
**YAML Definition:**
```yaml
cache:
  redis_port: 6379
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (line 160)
   ```python
   port=self.settings.cache.redis_port,
   ```
   - Only used when `cache.type == "redis"`
   - Redis server port

#### Parameter: `collection_name`
**YAML Definition:**
```yaml
cache:
  collection_name: "largerag_embedding_cache"
```

**Usage Locations:**

1. **LargeRAGIndexer._init_pipeline()** - `/home/syk/projects/experiment-plan-design/src/external/rag/core/indexer.py` (lines 140, 144, 162)
   ```python
   local_cache = LlamaIndexLocalCache(
       cache_dir=self.settings.cache.local_cache_dir,
       collection_name=self.settings.cache.collection_name,  # LINE 140
   )
   cache = IngestionCache(
       cache=local_cache,
       collection=self.settings.cache.collection_name,  # LINE 144
   )
   ```
   - Namespace for cached embeddings
   - Same name used for both local and Redis cache

#### Parameter: `ttl`
**YAML Definition:**
```yaml
cache:
  ttl: 86400  # Cache expiration time (seconds, Redis only)
```

**Usage:** Schema-defined but not actively used in code (Redis TTL would be set elsewhere)

---

### 9. LOGGING CONFIGURATION

#### Parameter: `level`
**YAML Definition:**
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

**Usage:** Schema-defined in `LoggingConfig` but logging setup in module uses built-in logging config

#### Parameter: `file_path`
**YAML Definition:**
```yaml
logging:
  file_path: "${PROJECT_ROOT}logs/largerag.log"
```

**Usage:** Schema-defined but not actively used (logging to module-level loggers)

#### Parameter: `format`
**YAML Definition:**
```yaml
logging:
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Usage:** Schema-defined in `LoggingConfig` but not actively applied

---

## Integration Points

### 1. Workflow Integration
**Location:** `/home/syk/projects/experiment-plan-design/src/workflow/rag_adapter.py`

The `RAGAdapter` class wraps LargeRAG for the experiment plan generation workflow:

```python
class RAGAdapter:
    def retrieve_templates(self, requirements: Dict[str, Any], top_k: int = 5) -> List[Dict]:
        """Retrieves templates using LargeRAG"""
        docs = self._rag.get_similar_docs(query_text=query, top_k=top_k)
        templates = self._convert_to_template_format(docs)
        return templates
```

**Configuration Usage:**
- Indirectly uses all RAG config through LargeRAG
- Adapts RAG output format for Generator compatibility
- Does not directly access settings

### 2. Build Script
**Location:** `/home/syk/projects/experiment-plan-design/build_rag_index.py`

Simple script to build RAG index:

```python
from external.rag.largerag import LargeRAG

rag = LargeRAG()  # Uses default config
success = rag.index_from_folders(data_path)
```

### 3. Integration Test
**Location:** `/home/syk/projects/experiment-plan-design/test_rag_integration.py`

Tests RAG integration with the workflow:

```python
adapter = RAGAdapter()
templates = adapter.retrieve_templates(requirements={...}, top_k=3)
```

---

## Configuration Load Flow

```
settings.yaml (YAML file)
    ↓
settings.py: load_settings()
    ↓
SETTINGS (global LargeRAGSettings instance)
    ↓
LargeRAGIndexer.__init__()  ← Uses for embedding, vector store, cache, document processing
LargeRAGQueryEngine.__init__()  ← Uses for LLM, reranker, retrieval
```

---

## Summary Table

| Category | Parameter | Location | Usage | Critical |
|----------|-----------|----------|-------|----------|
| **Embedding** | model | indexer.py:80 | DashScope model name | Yes |
| | batch_size | indexer.py:83 | API batch size | Yes |
| **Vector Store** | persist_directory | indexer.py:90 | Chroma storage path | Yes |
| | collection_name | indexer.py:198 | Chroma collection ID | Yes |
| | distance_metric | indexer.py:199 | HNSW space metric | Yes |
| **Document Processing** | splitter_type | indexer.py:99 | Chunking strategy | Yes |
| | chunk_size | indexer.py:114,122 | Chunk token size | Yes |
| | chunk_overlap | indexer.py:115,123 | Chunk overlap tokens | Yes |
| | semantic_threshold | indexer.py:106 | Semantic boundary sensitivity | No (conditional) |
| **Retrieval** | similarity_top_k | query_engine.py:61 | Vector recall count | Yes |
| | rerank_top_n | query_engine.py:50 | Final return count | Yes |
| | similarity_threshold | query_engine.py:66 | Score cutoff | Yes |
| **Reranker** | model | query_engine.py:48 | Reranker model name | Yes |
| | enabled | query_engine.py:46 | Enable/disable | Yes |
| **LLM** | model | query_engine.py:38 | LLM model name | Yes |
| | temperature | query_engine.py:40 | Output determinism | No |
| | max_tokens | query_engine.py:41 | Response limit | Yes |
| **Cache** | enabled | indexer.py:134 | Cache on/off | Yes |
| | type | indexer.py:135 | Cache backend | Yes |
| | local_cache_dir | indexer.py:139 | Local cache path | Yes |
| | redis_host | indexer.py:159 | Redis hostname | No (conditional) |
| | redis_port | indexer.py:160 | Redis port | No (conditional) |
| | collection_name | indexer.py:140 | Cache namespace | Yes |

---

## Key Observations

1. **Actively Used Parameters:**
   - Embedding: model, batch_size
   - Vector Store: persist_directory, collection_name, distance_metric
   - Document Processing: splitter_type, chunk_size, chunk_overlap
   - Retrieval: similarity_top_k, rerank_top_n, similarity_threshold
   - Reranker: model, enabled
   - LLM: model, max_tokens, temperature
   - Cache: enabled, type, local_cache_dir, collection_name

2. **Conditionally Used:**
   - Semantic breakpoint threshold (only for semantic splitter)
   - Redis parameters (only when cache type is redis)

3. **Schema-Only (Not Used):**
   - data.templates_dir
   - embedding.provider, text_type, dimension
   - vector_store.type
   - document_processing.separator
   - reranker.provider
   - llm.provider
   - logging parameters

4. **Configuration Entry Points:**
   - `LargeRAGIndexer.__init__()` - Loads for embedding, vector store, cache, document processing
   - `LargeRAGQueryEngine.__init__()` - Loads for LLM, reranker, retrieval
   - Both inherit from `SETTINGS` global instance (initialized in settings.py)

