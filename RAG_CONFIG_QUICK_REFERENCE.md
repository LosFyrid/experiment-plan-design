# RAG Configuration Quick Reference

## File Locations

- **Configuration YAML**: `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.yaml`
- **Settings Schema**: `/home/syk/projects/experiment-plan-design/src/external/rag/config/settings.py`
- **Main RAG Class**: `/home/syk/projects/experiment-plan-design/src/external/rag/largerag.py`

## Configuration Load Chain

```
RAG Components                      Configuration Used
────────────────────────────────    ──────────────────────
LargeRAGIndexer.__init__()
  ├─ RetryableDashScopeEmbedding    embedding.model
  │                                  embedding.batch_size
  ├─ ChromaDB PersistentClient      vector_store.persist_directory
  └─ IngestionPipeline._init_pipeline()
      ├─ Chunking Strategy          document_processing.splitter_type
      │                              document_processing.chunk_size
      │                              document_processing.chunk_overlap
      │                              document_processing.semantic_*
      └─ Cache Configuration        cache.enabled
                                     cache.type
                                     cache.local_cache_dir
                                     cache.redis_*
                                     cache.collection_name

LargeRAGQueryEngine.__init__()
  ├─ DashScope LLM                  llm.model
  │                                  llm.temperature
  │                                  llm.max_tokens
  └─ DashScopeRerank                reranker.enabled
                                     reranker.model
                                     retrieval.rerank_top_n

LargeRAGQueryEngine._build_query_engine()
  └─ VectorIndexRetriever           retrieval.similarity_top_k
                                     retrieval.similarity_threshold
```

## Most Important Parameters

### For Indexing (First Run)
1. **embedding.model** - Which Qwen embedding model to use
2. **embedding.batch_size** - Batch size for API calls (reduce if rate limited)
3. **vector_store.persist_directory** - Where to store Chroma database
4. **document_processing.chunk_size** - Document chunk size (tokens)
5. **cache.enabled** - Enable embedding cache (recommended: true)

### For Querying
1. **llm.model** - Which Qwen LLM for response generation
2. **retrieval.similarity_top_k** - Initial vector search recall (30 recommended)
3. **retrieval.rerank_top_n** - Final results after reranking (8 recommended)
4. **reranker.enabled** - Whether to use reranker (true recommended)
5. **retrieval.similarity_threshold** - Score cutoff (0.5-0.8 recommended)

## Key Configuration Sections

### 1. Embedding Config
```yaml
embedding:
  model: "text-embedding-v3"           # Qwen embedding model
  batch_size: 10                       # API batch size (adjust if rate limited)
  dimension: 1024                      # Vector dimension (auto-determined)
```
**Used By**: LargeRAGIndexer (embedding generation)

### 2. Vector Store Config
```yaml
vector_store:
  persist_directory: "data/chroma_db"  # Where vectors are stored
  collection_name: "experiment_plan_templates_v1"  # Namespace ID
  distance_metric: "cosine"            # Distance metric for HNSW
```
**Used By**: LargeRAGIndexer (vector storage), LargeRAGQueryEngine (vector retrieval)

### 3. Document Processing Config
```yaml
document_processing:
  splitter_type: "token"               # token, semantic, or sentence
  chunk_size: 512                      # Chunk size in tokens
  chunk_overlap: 50                    # Overlap between chunks
```
**Used By**: LargeRAGIndexer (document chunking)

### 4. Retrieval Config
```yaml
retrieval:
  similarity_top_k: 30                 # Initial vector search results
  rerank_top_n: 8                      # Final results after reranking
  similarity_threshold: 0.5            # Score cutoff (0 = disabled)
```
**Used By**: LargeRAGQueryEngine (retrieval parameters)

### 5. Reranker Config
```yaml
reranker:
  model: "gte-rerank-v2"               # Reranker model
  enabled: true                        # Enable reranking
```
**Used By**: LargeRAGQueryEngine (result reranking)

### 6. LLM Config
```yaml
llm:
  model: "qwen-plus"                   # qwen-plus or qwen-max
  temperature: 0                       # Deterministic output
  max_tokens: 2000                     # Max response length
```
**Used By**: LargeRAGQueryEngine (LLM response generation)

### 7. Cache Config
```yaml
cache:
  enabled: true                        # Master cache switch
  type: "local"                        # local or redis
  local_cache_dir: "data/cache"        # Cache directory (if local)
  collection_name: "largerag_embedding_cache"  # Cache namespace
```
**Used By**: LargeRAGIndexer (embedding cache)

## Common Adjustments

### Faster Indexing
- Reduce `embedding.batch_size` (but slower)
- Use `document_processing.splitter_type: "token"` (not semantic)
- Reduce `document_processing.chunk_size` (more chunks)

### Better Retrieval Quality
- Increase `retrieval.similarity_top_k` (more candidates)
- Keep `reranker.enabled: true`
- Increase `retrieval.similarity_threshold` (stricter filtering)
- Use `llm.model: "qwen-max"` (better quality but slower/costlier)

### Faster Queries
- Reduce `retrieval.similarity_top_k` (fewer candidates)
- Use `llm.model: "qwen-plus"` (faster but lower quality)
- Disable reranker: `reranker.enabled: false`

### Reduce Costs
- Use `cache.enabled: true` (avoid recalculating embeddings)
- Use `llm.model: "qwen-plus"` instead of `qwen-max`
- Reduce `retrieval.similarity_top_k` (fewer API calls)

## Parameter Dependencies

- **chunk_size** and **chunk_overlap** must be set together
- **similarity_top_k** should be >= **rerank_top_n** (usually 2x)
- **semantic_breakpoint_threshold** only used if `splitter_type: "semantic"`
- **redis_host/port** only used if `cache.type: "redis"`

## Testing Configuration Changes

1. Edit `/src/external/rag/config/settings.yaml`
2. Run indexing with new settings:
   ```bash
   python build_rag_index.py
   ```
3. Test queries:
   ```bash
   python src/external/rag/examples/2_query_and_retrieve.py
   ```

## Integration with Workflow

The RAG is integrated via `RAGAdapter` in the workflow:
- **Location**: `/src/workflow/rag_adapter.py`
- **Entry Point**: `RAGAdapter.retrieve_templates(requirements, top_k=5)`
- **Configuration Usage**: All RAG config is inherited automatically

## Troubleshooting

### "No existing index found"
- Need to run `python build_rag_index.py` first
- Check `vector_store.persist_directory` exists

### Rate limiting on embeddings
- Reduce `embedding.batch_size` (try 5-10)
- Check DASHSCOPE_API_KEY is valid

### Poor retrieval quality
- Increase `retrieval.similarity_top_k` to 50-100
- Increase `retrieval.similarity_threshold` to 0.7-0.8
- Use `llm.model: "qwen-max"`

### Slow queries
- Reduce `retrieval.similarity_top_k`
- Disable reranker: `reranker.enabled: false`
- Use smaller chunks: reduce `document_processing.chunk_size`
