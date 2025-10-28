# RAG Configuration Usage - Code Examples

This document shows exactly how each configuration parameter is used in the actual code.

## 1. Embedding Configuration Usage

### embedding.model

**Configuration:**
```yaml
embedding:
  model: "text-embedding-v3"
```

**Code Usage** - `/src/external/rag/core/indexer.py` line 80:
```python
self.embed_model = RetryableDashScopeEmbedding(
    model_name=self.settings.embedding.model,  # <- Uses config value
    text_type=DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT,
    api_key=self.api_key,
    embed_batch_size=self.settings.embedding.batch_size,
    max_retries=3,
    retry_delay=2.0,
)
```

**Effect:** Determines which DashScope embedding model to use for converting documents to vectors

---

### embedding.batch_size

**Configuration:**
```yaml
embedding:
  batch_size: 10
```

**Code Usage** - `/src/external/rag/core/indexer.py` line 83:
```python
self.embed_model = RetryableDashScopeEmbedding(
    model_name=self.settings.embedding.model,
    text_type=DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT,
    api_key=self.api_key,
    embed_batch_size=self.settings.embedding.batch_size,  # <- Uses config value
)
```

**Effect:** Controls how many documents are embedded in parallel. Smaller values reduce API rate limiting.

---

## 2. Vector Store Configuration Usage

### vector_store.persist_directory

**Configuration:**
```yaml
vector_store:
  persist_directory: "${PROJECT_ROOT}src/external/rag/data/chroma_db"
```

**Code Usage** - `/src/external/rag/core/indexer.py` lines 89-91:
```python
def __init__(self):
    self.settings = SETTINGS
    self.api_key = DASHSCOPE_API_KEY
    
    # ... embedding setup ...
    
    self.chroma_client = chromadb.PersistentClient(
        path=self.settings.vector_store.persist_directory  # <- Uses config value
    )
```

**Effect:** Creates Chroma database at specified directory. Survives process restart.

**Also used in** - `/src/external/rag/core/indexer.py` line 250:
```python
def get_index_stats(self) -> Dict[str, Any]:
    return {
        "collection_name": self.settings.vector_store.collection_name,
        "document_count": collection.count(),
        "persist_directory": self.settings.vector_store.persist_directory,  # <- Returns in stats
    }
```

---

### vector_store.collection_name

**Configuration:**
```yaml
vector_store:
  collection_name: "experiment_plan_templates_v1"
```

**Code Usage #1** - Creating collection in `/src/external/rag/core/indexer.py` lines 197-200:
```python
def build_index(self, documents: List[Document]) -> VectorStoreIndex:
    nodes = self.pipeline.run(documents=documents, show_progress=True)
    
    # Create Chroma collection
    collection = self.chroma_client.get_or_create_collection(
        name=self.settings.vector_store.collection_name,  # <- Uses config value
        metadata={"hnsw:space": self.settings.vector_store.distance_metric}
    )
    vector_store = ChromaVectorStore(chroma_collection=collection)
```

**Code Usage #2** - Loading collection in `/src/external/rag/core/indexer.py` lines 220-221:
```python
def load_index(self) -> Optional[VectorStoreIndex]:
    try:
        collection = self.chroma_client.get_collection(
            name=self.settings.vector_store.collection_name  # <- Uses config value
        )
```

**Effect:** Namespaces vectors so multiple experiments can store indices separately.

---

### vector_store.distance_metric

**Configuration:**
```yaml
vector_store:
  distance_metric: "cosine"
```

**Code Usage** - `/src/external/rag/core/indexer.py` line 199:
```python
collection = self.chroma_client.get_or_create_collection(
    name=self.settings.vector_store.collection_name,
    metadata={"hnsw:space": self.settings.vector_store.distance_metric}  # <- Uses config value
)
```

**Effect:** Sets distance metric for HNSW (Hierarchical Navigable Small World) index
- "cosine" = cosine similarity (recommended for embeddings)
- "l2" = Euclidean distance
- "ip" = inner product

---

## 3. Document Processing Configuration Usage

### document_processing.splitter_type

**Configuration:**
```yaml
document_processing:
  splitter_type: "token"
```

**Code Usage** - `/src/external/rag/core/indexer.py` lines 99-125:
```python
def _init_pipeline(self):
    """Initialize Ingestion Pipeline (with caching)"""
    splitter_type = self.settings.document_processing.splitter_type  # <- Gets config value
    
    if splitter_type == "semantic":
        # Semantic splitting (requires extra embedding computation)
        from llama_index.core.node_parser import SemanticSplitterNodeParser
        splitter = SemanticSplitterNodeParser(
            embed_model=self.embed_model,
            breakpoint_percentile_threshold=self.settings.document_processing.semantic_breakpoint_threshold,
            buffer_size=self.settings.document_processing.semantic_buffer_size,
        )
        logger.info(f"Using semantic splitter (threshold={...})")
    
    elif splitter_type == "sentence":
        # Sentence splitting (preserves sentence integrity)
        from llama_index.core.node_parser import SentenceSplitter
        splitter = SentenceSplitter(
            chunk_size=self.settings.document_processing.chunk_size,
            chunk_overlap=self.settings.document_processing.chunk_overlap,
        )
        logger.info(f"Using sentence splitter (size={...})")
    
    else:  # "token" (default)
        # Token splitting (breaks at token boundaries)
        splitter = SentenceSplitter(
            chunk_size=self.settings.document_processing.chunk_size,  # <- Conditional usage
            chunk_overlap=self.settings.document_processing.chunk_overlap,
        )
        logger.info(f"Using token-based splitter (size={...})")
```

**Effect:** Determines how documents are split into chunks
- "token": Fast, breaks at token boundaries
- "sentence": Preserves sentence integrity
- "semantic": Slow but breaks at semantic boundaries

---

### document_processing.chunk_size & chunk_overlap

**Configuration:**
```yaml
document_processing:
  chunk_size: 512
  chunk_overlap: 50
```

**Code Usage** - `/src/external/rag/core/indexer.py` lines 114-115, 122-123:
```python
elif splitter_type == "sentence":
    splitter = SentenceSplitter(
        chunk_size=self.settings.document_processing.chunk_size,      # <- Uses config
        chunk_overlap=self.settings.document_processing.chunk_overlap,  # <- Uses config
    )

else:  # "token" (default)
    splitter = SentenceSplitter(
        chunk_size=self.settings.document_processing.chunk_size,      # <- Uses config
        chunk_overlap=self.settings.document_processing.chunk_overlap,  # <- Uses config
    )
```

**Effect:**
- `chunk_size`: Controls how many tokens per chunk (larger = fewer chunks)
- `chunk_overlap`: Overlap between consecutive chunks (provides context)

---

### document_processing.semantic_breakpoint_threshold

**Configuration:**
```yaml
document_processing:
  semantic_breakpoint_threshold: 0.5
```

**Code Usage** - `/src/external/rag/core/indexer.py` lines 106-109 (only if splitter_type == "semantic"):
```python
if splitter_type == "semantic":
    from llama_index.core.node_parser import SemanticSplitterNodeParser
    splitter = SemanticSplitterNodeParser(
        embed_model=self.embed_model,
        breakpoint_percentile_threshold=self.settings.document_processing.semantic_breakpoint_threshold,  # <- Conditional
        buffer_size=self.settings.document_processing.semantic_buffer_size,
    )
    logger.info(f"Using semantic splitter (threshold={self.settings.document_processing.semantic_breakpoint_threshold})")
```

**Effect:** Controls sensitivity of semantic boundaries (0-1)
- Higher = stricter boundaries
- Only used when splitter_type = "semantic"

---

## 4. Retrieval Configuration Usage

### retrieval.similarity_top_k

**Configuration:**
```yaml
retrieval:
  similarity_top_k: 30
```

**Code Usage #1** - In `_build_query_engine()` at `/src/external/rag/core/query_engine.py` lines 59-61:
```python
def _build_query_engine(self):
    """Build query engine (with Reranker)"""
    retriever_kwargs = {
        "index": self.index,
        "similarity_top_k": self.settings.retrieval.similarity_top_k,  # <- Uses config
    }
```

**Code Usage #2** - In `get_similar_documents()` at `/src/external/rag/core/query_engine.py` lines 121-134:
```python
def get_similar_documents(self, query_text: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    # Determine final return count
    final_top_k = top_k or self.settings.retrieval.rerank_top_n
    
    # Dynamic adjustment of candidate pool size
    required_candidates = max(
        final_top_k * 2,  # Candidate pool should be 2x final output
        self.settings.retrieval.similarity_top_k  # <- Uses config as baseline
    )
    
    # Log if auto-adjusted
    if required_candidates > self.settings.retrieval.similarity_top_k:  # <- Checks against config
        logger.info(
            f"Auto-adjusted similarity_top_k from {self.settings.retrieval.similarity_top_k} "
            f"to {required_candidates} to satisfy top_k={final_top_k}"
        )
```

**Effect:** Number of candidates retrieved from vector search before reranking
- Larger = better recall, slower
- Smaller = faster, may miss relevant documents

---

### retrieval.rerank_top_n

**Configuration:**
```yaml
retrieval:
  rerank_top_n: 8
```

**Code Usage #1** - Passed to reranker in `__init__()` at `/src/external/rag/core/query_engine.py` lines 47-51:
```python
if self.settings.reranker.enabled:
    self.reranker = DashScopeRerank(
        model=self.settings.reranker.model,
        api_key=self.api_key,
        top_n=self.settings.retrieval.rerank_top_n,  # <- Uses config
    )
```

**Code Usage #2** - Used as default in `get_similar_documents()` at line 115:
```python
final_top_k = top_k or self.settings.retrieval.rerank_top_n  # <- Default if no explicit top_k
```

**Code Usage #3** - Dynamically adjusted at line 151:
```python
reranker = DashScopeRerank(
    model=self.settings.reranker.model,
    api_key=self.api_key,
    top_n=max(final_top_k, self.settings.retrieval.rerank_top_n),  # <- Uses larger of two values
)
```

**Effect:** Number of results returned after reranking
- Smaller = faster, fewer results
- Larger = slower, more results

---

### retrieval.similarity_threshold

**Configuration:**
```yaml
retrieval:
  similarity_threshold: 0.5
```

**Code Usage #1** - In `_build_query_engine()` at `/src/external/rag/core/query_engine.py` lines 65-67:
```python
if self.settings.retrieval.similarity_threshold > 0:  # <- Checks if enabled
    retriever_kwargs["similarity_cutoff"] = self.settings.retrieval.similarity_threshold  # <- Uses config
    logger.info(f"Similarity threshold enabled: {self.settings.retrieval.similarity_threshold}")
```

**Code Usage #2** - In `get_similar_documents()` at lines 138-139:
```python
if self.settings.retrieval.similarity_threshold > 0:  # <- Checks if enabled
    retriever_kwargs["similarity_cutoff"] = self.settings.retrieval.similarity_threshold  # <- Uses config
```

**Effect:** Filters results to only include scores >= threshold
- 0 = disabled (returns all)
- 0.5-0.8 = conservative filtering
- Higher = stricter filtering

---

## 5. Reranker Configuration Usage

### reranker.enabled

**Configuration:**
```yaml
reranker:
  enabled: true
```

**Code Usage #1** - In `__init__()` at `/src/external/rag/core/query_engine.py` lines 46-51:
```python
self.reranker = None
if self.settings.reranker.enabled:  # <- Checks config
    self.reranker = DashScopeRerank(
        model=self.settings.reranker.model,
        api_key=self.api_key,
        top_n=self.settings.retrieval.rerank_top_n,
    )
```

**Code Usage #2** - In `_build_query_engine()` at line 72:
```python
postprocessors = [self.reranker] if self.reranker else []  # <- Uses only if initialized
self.query_engine = RetrieverQueryEngine.from_args(
    retriever=retriever,
    node_postprocessors=postprocessors,  # <- Reranker added if enabled
    llm=self.llm,
)
```

**Effect:**
- true = uses DashScope reranker (slower but better quality)
- false = skips reranking (faster but lower quality)

---

### reranker.model

**Configuration:**
```yaml
reranker:
  model: "gte-rerank-v2"
```

**Code Usage #1** - In `__init__()` at `/src/external/rag/core/query_engine.py` line 48:
```python
if self.settings.reranker.enabled:
    self.reranker = DashScopeRerank(
        model=self.settings.reranker.model,  # <- Uses config
        api_key=self.api_key,
        top_n=self.settings.retrieval.rerank_top_n,
    )
```

**Code Usage #2** - In `get_similar_documents()` at line 149:
```python
reranker = DashScopeRerank(
    model=self.settings.reranker.model,  # <- Uses config
    api_key=self.api_key,
    top_n=max(final_top_k, self.settings.retrieval.rerank_top_n),
)
```

**Effect:** Which DashScope reranker model to use for re-ranking results

---

## 6. LLM Configuration Usage

### llm.model

**Configuration:**
```yaml
llm:
  model: "qwen-plus"
```

**Code Usage** - In `__init__()` at `/src/external/rag/core/query_engine.py` lines 37-42:
```python
def __init__(self, index: VectorStoreIndex):
    self.index = index
    self.settings = SETTINGS
    self.api_key = DASHSCOPE_API_KEY
    
    # Initialize LLM (use model from config)
    self.llm = DashScope(
        model_name=self.settings.llm.model,  # <- Uses config
        api_key=self.api_key,
        temperature=self.settings.llm.temperature,
        max_tokens=self.settings.llm.max_tokens,
    )
```

**Effect:** Which Qwen LLM to use for generating responses
- "qwen-plus" = faster, cheaper
- "qwen-max" = higher quality, slower, more expensive

---

### llm.temperature

**Configuration:**
```yaml
llm:
  temperature: 0
```

**Code Usage** - At `/src/external/rag/core/query_engine.py` line 40:
```python
self.llm = DashScope(
    model_name=self.settings.llm.model,
    api_key=self.api_key,
    temperature=self.settings.llm.temperature,  # <- Uses config
    max_tokens=self.settings.llm.max_tokens,
)
```

**Effect:** Controls output randomness
- 0 = deterministic
- Higher = more creative/random

---

### llm.max_tokens

**Configuration:**
```yaml
llm:
  max_tokens: 2000
```

**Code Usage** - At `/src/external/rag/core/query_engine.py` line 41:
```python
self.llm = DashScope(
    model_name=self.settings.llm.model,
    api_key=self.api_key,
    temperature=self.settings.llm.temperature,
    max_tokens=self.settings.llm.max_tokens,  # <- Uses config
)
```

**Effect:** Maximum length of LLM response in tokens

---

## 7. Cache Configuration Usage

### cache.enabled

**Configuration:**
```yaml
cache:
  enabled: true
```

**Code Usage** - In `_init_pipeline()` at `/src/external/rag/core/indexer.py` line 134:
```python
def _init_pipeline(self):
    """Initialize Ingestion Pipeline (with caching)"""
    # ... transformations setup ...
    
    # Configure cache
    cache = None
    if self.settings.cache.enabled:  # <- Checks config
        if self.settings.cache.type == "local":
            # local cache logic
        elif self.settings.cache.type == "redis":
            # redis cache logic
    
    self.pipeline = IngestionPipeline(
        transformations=transformations,
        cache=cache,  # <- Will be None if disabled
    )
```

**Effect:**
- true = enables embedding cache (avoids recomputing)
- false = disables cache (slower re-indexing)

---

### cache.type

**Configuration:**
```yaml
cache:
  type: "local"
```

**Code Usage** - At `/src/external/rag/core/indexer.py` lines 135-169:
```python
if self.settings.cache.enabled:
    if self.settings.cache.type == "local":  # <- Checks config
        # Use local file cache
        try:
            local_cache = LlamaIndexLocalCache(
                cache_dir=self.settings.cache.local_cache_dir,
                collection_name=self.settings.cache.collection_name,
            )
            cache = IngestionCache(cache=local_cache, collection=self.settings.cache.collection_name)
            logger.info(f"Local file cache initialized at: {self.settings.cache.local_cache_dir}")
        except Exception as e:
            logger.warning(f"Failed to initialize local cache: {e}. Proceeding without cache.")
    
    elif self.settings.cache.type == "redis":  # <- Checks config
        # Use Redis cache
        if not REDIS_AVAILABLE:
            logger.warning("Redis cache requested but not available.")
        else:
            try:
                cache = IngestionCache(
                    cache=RedisKVStore.from_host_and_port(
                        host=self.settings.cache.redis_host,
                        port=self.settings.cache.redis_port,
                    ),
                    collection=self.settings.cache.collection_name,
                )
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}. Proceeding without cache.")
    else:
        logger.warning(f"Unknown cache type: {self.settings.cache.type}. Using no cache.")
```

**Effect:**
- "local" = file-based cache (no extra services needed)
- "redis" = Redis cache (requires Redis server)

---

### cache.local_cache_dir

**Configuration:**
```yaml
cache:
  local_cache_dir: "${PROJECT_ROOT}src/external/rag/data/cache"
```

**Code Usage** - At `/src/external/rag/core/indexer.py` lines 139-140:
```python
if self.settings.cache.type == "local":
    try:
        local_cache = LlamaIndexLocalCache(
            cache_dir=self.settings.cache.local_cache_dir,  # <- Uses config
            collection_name=self.settings.cache.collection_name,
        )
        cache = IngestionCache(
            cache=local_cache,
            collection=self.settings.cache.collection_name,
        )
        logger.info(f"Local file cache initialized at: {self.settings.cache.local_cache_dir}")
```

**Effect:** Directory where embedding cache files (pickle) are stored

---

### cache.redis_host & cache.redis_port

**Configuration:**
```yaml
cache:
  redis_host: "localhost"
  redis_port: 6379
```

**Code Usage** - At `/src/external/rag/core/indexer.py` lines 158-162:
```python
elif self.settings.cache.type == "redis":
    try:
        cache = IngestionCache(
            cache=RedisKVStore.from_host_and_port(
                host=self.settings.cache.redis_host,    # <- Uses config
                port=self.settings.cache.redis_port,    # <- Uses config
            ),
            collection=self.settings.cache.collection_name,
        )
```

**Effect:** Redis server connection details (only used if cache.type = "redis")

---

### cache.collection_name

**Configuration:**
```yaml
cache:
  collection_name: "largerag_embedding_cache"
```

**Code Usage #1** - With local cache at `/src/external/rag/core/indexer.py` lines 140, 144:
```python
local_cache = LlamaIndexLocalCache(
    cache_dir=self.settings.cache.local_cache_dir,
    collection_name=self.settings.cache.collection_name,  # <- Uses config
)
cache = IngestionCache(
    cache=local_cache,
    collection=self.settings.cache.collection_name,  # <- Uses config
)
```

**Code Usage #2** - With Redis cache at line 162:
```python
cache = IngestionCache(
    cache=RedisKVStore.from_host_and_port(...),
    collection=self.settings.cache.collection_name,  # <- Uses config
)
```

**Effect:** Namespace for cached embeddings (allows multiple caches)

---

## Configuration Loading & Initialization

### How Configuration Gets Loaded

**File**: `/src/external/rag/config/settings.py`

```python
def load_settings(config_path: Optional[str] = None) -> LargeRAGSettings:
    """Load configuration file"""
    if config_path is None:
        config_path = Path(__file__).parent / "settings.yaml"  # <- Loads YAML
    
    with open(config_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    # ... variable substitution for ${PROJECT_ROOT} ...
    
    # Build configuration objects
    settings = LargeRAGSettings(
        embedding=EmbeddingConfig(**resolved['embedding']),           # <- Creates embedding config
        vector_store=VectorStoreConfig(**resolved['vector_store']),   # <- Creates vector store config
        document_processing=DocumentProcessingConfig(**resolved['document_processing']),  # <- etc
        retrieval=RetrievalConfig(**resolved['retrieval']),
        reranker=RerankerConfig(**resolved['reranker']),
        llm=LLMConfig(**resolved['llm']),
        cache=CacheConfig(**resolved['cache']),
        logging=LoggingConfig(**resolved['logging']),
    )
    
    return settings

# Global instance created on module import
SETTINGS = load_settings()
```

### How Components Access Configuration

**In LargeRAGIndexer** (`/src/external/rag/core/indexer.py`):
```python
def __init__(self):
    self.settings = SETTINGS  # <- Gets global SETTINGS instance
    self.api_key = DASHSCOPE_API_KEY
    
    # Use self.settings throughout:
    self.embed_model = RetryableDashScopeEmbedding(
        model_name=self.settings.embedding.model,  # <- Accesses from loaded config
        ...
    )
```

**In LargeRAGQueryEngine** (`/src/external/rag/core/query_engine.py`):
```python
def __init__(self, index: VectorStoreIndex):
    self.index = index
    self.settings = SETTINGS  # <- Gets global SETTINGS instance
    self.api_key = DASHSCOPE_API_KEY
    
    # Use self.settings throughout:
    self.llm = DashScope(
        model_name=self.settings.llm.model,  # <- Accesses from loaded config
        ...
    )
```

---

## Summary

Each configuration parameter flows through this chain:

```
YAML file (settings.yaml)
    ↓
settings.py: load_settings() → SETTINGS (global instance)
    ↓
LargeRAGIndexer.__init__() or LargeRAGQueryEngine.__init__()
    ↓
self.settings = SETTINGS
    ↓
self.settings.[section].[parameter]  ← Accessed in code
```

All parameters are type-safe due to Pydantic dataclasses.
