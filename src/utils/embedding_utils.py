"""
Embedding utilities for ACE Framework.

Provides semantic similarity and deduplication functions for Curator.
Implements ACE paper §3.2 (Grow-and-Refine).
"""

from typing import List, Tuple, Dict, Set, Optional
import numpy as np
from utils.qwen_embedding import QwenEmbeddingProvider, util


class EmbeddingManager:
    """
    Manages embeddings for semantic similarity operations.

    Used by Curator for deduplication (ACE paper §3.2).
    """

    def __init__(
        self,
        model_name: str = "text-embedding-v4",
        api_key: str = None
    ):
        """
        Args:
            model_name: Qwen embedding model (text-embedding-v4推荐)
            api_key: Qwen API密钥（如果不提供，从环境变量读取）
        """
        self.embedding_provider = QwenEmbeddingProvider(model=model_name, api_key=api_key)

    def encode(
        self,
        texts: List[str],
        batch_size: int = 10,  # Qwen限制最多10
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: List of text strings
            batch_size: Batch size for encoding（Qwen最多10）
            show_progress: Show progress bar

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        return self.embedding_provider.encode(
            texts,
            show_progress_bar=show_progress
        )

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity in [0, 1]
        """
        return float(util.cos_sim(embedding1, embedding2)[0, 0])

    def compute_similarity_matrix(
        self,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute pairwise cosine similarity matrix.

        Args:
            embeddings: Array of shape (n, embedding_dim)

        Returns:
            Similarity matrix of shape (n, n)
        """
        return util.cos_sim(embeddings, embeddings)


# ============================================================================
# Deduplication Functions (ACE §3.2)
# ============================================================================

def find_duplicate_pairs(
    embeddings: np.ndarray,
    threshold: float = 0.85,
    exclude_diagonal: bool = True
) -> List[Tuple[int, int, float]]:
    """
    Find pairs of semantically similar items.

    Implements duplicate detection for ACE paper §3.2.

    Args:
        embeddings: Array of shape (n, embedding_dim)
        threshold: Cosine similarity threshold for duplicates
        exclude_diagonal: Don't include self-similarity (i, i)

    Returns:
        List of (idx1, idx2, similarity) tuples where similarity >= threshold
        Sorted by similarity (descending)
    """
    if len(embeddings) == 0:
        return []

    # Compute similarity matrix
    sim_matrix = util.cos_sim(embeddings, embeddings)

    # Find pairs above threshold
    pairs = []
    n = len(embeddings)

    for i in range(n):
        for j in range(i + 1 if exclude_diagonal else i, n):
            similarity = sim_matrix[i, j]
            if similarity >= threshold:
                pairs.append((i, j, float(similarity)))

    # Sort by similarity (descending)
    pairs.sort(key=lambda x: x[2], reverse=True)

    return pairs


def deduplicate_with_quality_scores(
    items: List[str],
    embeddings: np.ndarray,
    quality_scores: List[float],
    threshold: float = 0.85
) -> Tuple[List[int], Dict[int, List[int]]]:
    """
    Deduplicate items, keeping those with highest quality scores.

    Implements Grow-and-Refine deduplication from ACE paper §3.2.

    Args:
        items: List of text items
        embeddings: Embeddings for items (shape: (len(items), embedding_dim))
        quality_scores: Quality score for each item (e.g., helpfulness_score)
        threshold: Similarity threshold for considering items as duplicates

    Returns:
        Tuple of:
        - List of indices to keep
        - Dict mapping kept_idx -> list of removed_idx (duplicates)
    """
    n = len(items)
    if n == 0:
        return [], {}

    # Find duplicate pairs
    duplicate_pairs = find_duplicate_pairs(embeddings, threshold)

    # Build graph of duplicates
    duplicate_groups: Dict[int, Set[int]] = {}  # idx -> set of duplicate indices

    for idx1, idx2, _ in duplicate_pairs:
        # Merge groups if they exist
        group1 = duplicate_groups.get(idx1, {idx1})
        group2 = duplicate_groups.get(idx2, {idx2})
        merged = group1 | group2

        # Update all members to point to merged group
        for idx in merged:
            duplicate_groups[idx] = merged

    # Get unique groups
    seen_groups: Set[frozenset] = set()
    unique_groups: List[Set[int]] = []

    for group in duplicate_groups.values():
        frozen_group = frozenset(group)
        if frozen_group not in seen_groups:
            seen_groups.add(frozen_group)
            unique_groups.append(group)

    # For each group, keep item with highest quality score
    indices_to_keep = set(range(n))  # Start with all indices
    merge_map: Dict[int, List[int]] = {}  # kept_idx -> [removed_idx, ...]

    for group in unique_groups:
        group_list = list(group)

        # Find item with highest quality score in group
        best_idx = max(group_list, key=lambda idx: quality_scores[idx])

        # Remove all others
        for idx in group_list:
            if idx != best_idx:
                indices_to_keep.discard(idx)

                # Record merge
                if best_idx not in merge_map:
                    merge_map[best_idx] = []
                merge_map[best_idx].append(idx)

    return sorted(list(indices_to_keep)), merge_map


def merge_bullet_contents(
    primary_content: str,
    duplicate_contents: List[str],
    embeddings: List[np.ndarray]
) -> str:
    """
    Merge duplicate bullet contents into a single bullet.

    Strategy: Keep primary content (highest quality), optionally
    append unique insights from duplicates.

    Args:
        primary_content: Content of the bullet to keep
        duplicate_contents: Contents of duplicate bullets
        embeddings: Embeddings for [primary] + duplicates

    Returns:
        Merged bullet content
    """
    # For now, simple strategy: just keep primary content
    # More sophisticated merging could extract unique phrases from duplicates
    return primary_content


# ============================================================================
# Semantic Clustering (Optional)
# ============================================================================

def cluster_by_similarity(
    embeddings: np.ndarray,
    threshold: float = 0.7,
    min_cluster_size: int = 2
) -> List[List[int]]:
    """
    Cluster items by semantic similarity using agglomerative approach.

    Args:
        embeddings: Array of shape (n, embedding_dim)
        threshold: Similarity threshold for same cluster
        min_cluster_size: Minimum items in a cluster (smaller -> singleton)

    Returns:
        List of clusters, where each cluster is a list of indices
    """
    if len(embeddings) == 0:
        return []

    from sklearn.cluster import AgglomerativeClustering

    # Compute similarity matrix
    sim_matrix = util.cos_sim(embeddings, embeddings)

    # Convert similarity to distance (1 - similarity)
    distance_matrix = 1 - sim_matrix

    # Perform clustering
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,
        metric='precomputed',
        linkage='average'
    )

    labels = clustering.fit_predict(distance_matrix)

    # Group by label
    clusters: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(idx)

    # Filter by min_cluster_size
    result = [
        cluster for cluster in clusters.values()
        if len(cluster) >= min_cluster_size
    ]

    return result


# ============================================================================
# Utility Functions
# ============================================================================

def get_most_representative(
    embeddings: np.ndarray,
    quality_scores: Optional[List[float]] = None
) -> int:
    """
    Get index of most representative item in a group.

    Representative = closest to centroid (weighted by quality if provided).

    Args:
        embeddings: Array of shape (n, embedding_dim)
        quality_scores: Optional quality scores for weighting

    Returns:
        Index of most representative item
    """
    if len(embeddings) == 0:
        raise ValueError("No embeddings provided")

    if len(embeddings) == 1:
        return 0

    # Compute centroid
    if quality_scores is not None:
        # Weighted centroid
        weights = np.array(quality_scores).reshape(-1, 1)
        centroid = np.average(embeddings, axis=0, weights=weights.flatten())
    else:
        # Simple mean
        centroid = np.mean(embeddings, axis=0)

    # Find closest to centroid
    similarities = util.cos_sim(centroid, embeddings)[0]
    return int(np.argmax(similarities))


def batch_compute_similarities(
    query_embeddings: np.ndarray,
    corpus_embeddings: np.ndarray,
    top_k: int = 5
) -> List[List[Tuple[int, float]]]:
    """
    Compute top-k most similar corpus items for each query.

    Args:
        query_embeddings: Array of shape (n_queries, embedding_dim)
        corpus_embeddings: Array of shape (n_corpus, embedding_dim)
        top_k: Number of top results per query

    Returns:
        List of lists, where each inner list contains (corpus_idx, similarity)
        tuples for one query
    """
    if len(query_embeddings) == 0 or len(corpus_embeddings) == 0:
        return []

    # Compute similarity matrix: (n_queries, n_corpus)
    sim_matrix = util.cos_sim(query_embeddings, corpus_embeddings)

    results = []
    for query_sims in sim_matrix:
        # Get top-k indices
        top_indices = np.argsort(query_sims)[::-1][:top_k]
        top_scores = query_sims[top_indices]

        query_results = [(int(idx), float(score)) for idx, score in zip(top_indices, top_scores)]
        results.append(query_results)

    return results
