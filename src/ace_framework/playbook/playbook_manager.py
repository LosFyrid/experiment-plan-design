"""
Playbook Manager for ACE Framework.

Implements playbook operations:
- Load/save from JSON
- Semantic bullet retrieval (top-k similarity)
- Metadata updates (helpful/harmful counts)
- ID generation with section prefixes
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import numpy as np

# 使用Qwen embedding替代sentence-transformers
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.qwen_embedding import QwenEmbeddingProvider, util

from .schemas import Playbook, PlaybookBullet, BulletMetadata, BulletTag


class PlaybookManager:
    """
    Manages ACE playbook lifecycle.

    Key features:
    - Semantic search using embeddings (for Generator bullet retrieval)
    - Incremental updates (for Curator)
    - Metadata tracking (for Grow-and-Refine)
    """

    def __init__(
        self,
        playbook_path: str,
        embedding_model: str = "text-embedding-v4",  # Qwen embedding v4
        api_key: str = None
    ):
        """
        Args:
            playbook_path: Path to playbook JSON file
            embedding_model: Qwen embedding model name (text-embedding-v4推荐)
            api_key: Qwen API密钥（如果不提供，从环境变量读取）
        """
        self.playbook_path = Path(playbook_path)
        self.embedding_provider = QwenEmbeddingProvider(model=embedding_model, api_key=api_key)
        self._playbook: Optional[Playbook] = None
        self._embeddings_cache: Dict[str, np.ndarray] = {}  # bullet_id -> embedding

    # ========================================================================
    # Load / Save
    # ========================================================================

    def load(self) -> Playbook:
        """
        Load playbook from JSON file.

        Returns:
            Playbook object

        Raises:
            FileNotFoundError: If playbook file doesn't exist
        """
        if not self.playbook_path.exists():
            raise FileNotFoundError(f"Playbook not found: {self.playbook_path}")

        with open(self.playbook_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse with Pydantic for validation
        self._playbook = Playbook(**data)

        # Build embeddings cache
        self._build_embeddings_cache()

        return self._playbook

    def save(self, playbook: Optional[Playbook] = None) -> None:
        """
        Save playbook to JSON file.

        Args:
            playbook: Playbook to save (uses self._playbook if None)
        """
        if playbook is None:
            playbook = self._playbook

        if playbook is None:
            raise ValueError("No playbook to save")

        # Update timestamp
        playbook.last_updated = datetime.now()

        # Ensure directory exists
        self.playbook_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save (exclude embeddings from serialization)
        data = playbook.model_dump(mode='json')

        # Remove embeddings from metadata before saving
        for bullet in data.get('bullets', []):
            if 'metadata' in bullet and 'embedding' in bullet['metadata']:
                bullet['metadata']['embedding'] = None

        with open(self.playbook_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def get_or_create(self, sections: Optional[List[str]] = None) -> Playbook:
        """
        Load existing playbook or create empty one.

        Args:
            sections: Section names for new playbook (if creating)

        Returns:
            Loaded or created Playbook
        """
        if self.playbook_path.exists():
            return self.load()
        else:
            # Create empty playbook
            playbook = Playbook(sections=sections or [])
            self._playbook = playbook
            self.save(playbook)
            return playbook

    # ========================================================================
    # Embeddings
    # ========================================================================

    def _build_embeddings_cache(self) -> None:
        """Build embeddings for all bullets in current playbook."""
        if self._playbook is None:
            return

        contents = [bullet.content for bullet in self._playbook.bullets]
        if not contents:
            return

        # Batch encode for efficiency (Qwen支持批量，最多25个/次)
        embeddings = self.embedding_provider.encode(
            contents,
            show_progress_bar=False
        )

        # Store in cache
        for bullet, embedding in zip(self._playbook.bullets, embeddings):
            self._embeddings_cache[bullet.id] = embedding
            # Also store in bullet metadata for persistence
            bullet.metadata.embedding = embedding.tolist()

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text string."""
        embeddings = self.embedding_provider.encode(
            text,  # 传入单个字符串
            show_progress_bar=False
        )
        # encode返回的是(1, dim)的数组，取第一个
        if embeddings.ndim == 2 and embeddings.shape[0] == 1:
            return embeddings[0]
        return embeddings

    # ========================================================================
    # Retrieval (for Generator)
    # ========================================================================

    def retrieve_relevant_bullets(
        self,
        query: str,
        top_k: int = 50,
        section_filter: Optional[List[str]] = None,
        min_similarity: float = 0.3
    ) -> List[Tuple[PlaybookBullet, float]]:
        """
        Retrieve top-k most relevant bullets using semantic similarity.

        Implements bullet retrieval for ACE Generator (ACE paper §3).

        Args:
            query: Query text (e.g., experiment requirements)
            top_k: Number of bullets to retrieve
            section_filter: Only return bullets from these sections
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of (bullet, similarity_score) tuples, sorted by score (desc)
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        if not self._playbook.bullets:
            return []

        # Get query embedding
        query_embedding = self._get_embedding(query)

        # Filter bullets by section if specified
        bullets = self._playbook.bullets
        if section_filter:
            bullets = [b for b in bullets if b.section in section_filter]

        if not bullets:
            return []

        # Get embeddings for candidates
        bullet_embeddings = np.array([
            self._embeddings_cache.get(b.id, self._get_embedding(b.content))
            for b in bullets
        ])

        # Compute cosine similarities
        similarities = util.cos_sim(query_embedding, bullet_embeddings)[0]

        # Create (bullet, score) pairs
        results = [
            (bullet, float(score))
            for bullet, score in zip(bullets, similarities)
            if score >= min_similarity
        ]

        # Sort by similarity (descending) and take top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def retrieve_by_section(
        self,
        section: str,
        top_k: Optional[int] = None
    ) -> List[PlaybookBullet]:
        """
        Retrieve all bullets from a specific section.

        Args:
            section: Section name
            top_k: Limit number of results (None = all)

        Returns:
            List of bullets, sorted by helpfulness score (desc)
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        bullets = self._playbook.get_bullets_by_section(section)

        # Sort by helpfulness score
        bullets.sort(
            key=lambda b: b.metadata.helpfulness_score,
            reverse=True
        )

        if top_k is not None:
            bullets = bullets[:top_k]

        return bullets

    # ========================================================================
    # Updates (for Curator)
    # ========================================================================

    def add_bullet(
        self,
        content: str,
        section: str,
        id_prefix: str,
        source: str = "reflection"
    ) -> PlaybookBullet:
        """
        Add a new bullet to playbook.

        Args:
            content: Bullet text
            section: Section name
            id_prefix: Section prefix (e.g., "mat", "proc")
            source: "seed", "reflection", "manual"

        Returns:
            Created PlaybookBullet
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        # Generate unique ID
        bullet_id = self._generate_bullet_id(section, id_prefix)

        # Create bullet
        bullet = PlaybookBullet(
            id=bullet_id,
            section=section,
            content=content,
            metadata=BulletMetadata(source=source)
        )

        # Compute embedding
        embedding = self._get_embedding(content)
        bullet.metadata.embedding = embedding.tolist()
        self._embeddings_cache[bullet_id] = embedding

        # Add to playbook
        self._playbook.bullets.append(bullet)

        return bullet

    def update_bullet(
        self,
        bullet_id: str,
        new_content: Optional[str] = None,
        metadata_updates: Optional[Dict] = None
    ) -> PlaybookBullet:
        """
        Update existing bullet.

        Args:
            bullet_id: ID of bullet to update
            new_content: New content (None = keep existing)
            metadata_updates: Dict of metadata fields to update

        Returns:
            Updated PlaybookBullet

        Raises:
            ValueError: If bullet not found
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        bullet = self._playbook.get_bullet_by_id(bullet_id)
        if bullet is None:
            raise ValueError(f"Bullet not found: {bullet_id}")

        # Update content
        if new_content is not None:
            bullet.content = new_content
            # Recompute embedding
            embedding = self._get_embedding(new_content)
            bullet.metadata.embedding = embedding.tolist()
            self._embeddings_cache[bullet_id] = embedding

        # Update metadata
        if metadata_updates:
            for key, value in metadata_updates.items():
                if hasattr(bullet.metadata, key):
                    setattr(bullet.metadata, key, value)

        bullet.metadata.last_updated = datetime.now()

        return bullet

    def remove_bullet(self, bullet_id: str) -> bool:
        """
        Remove bullet from playbook.

        Args:
            bullet_id: ID of bullet to remove

        Returns:
            True if removed, False if not found
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        original_size = len(self._playbook.bullets)
        self._playbook.bullets = [
            b for b in self._playbook.bullets if b.id != bullet_id
        ]

        # Clean up cache
        if bullet_id in self._embeddings_cache:
            del self._embeddings_cache[bullet_id]

        return len(self._playbook.bullets) < original_size

    def update_bullet_tags(
        self,
        bullet_tags: Dict[str, BulletTag]
    ) -> int:
        """
        Update bullet metadata based on Reflector tags.

        Implements metadata updates for ACE paper §3.2 Grow-and-Refine.

        Args:
            bullet_tags: Mapping of bullet_id -> tag

        Returns:
            Number of bullets updated
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        updated_count = 0

        for bullet_id, tag in bullet_tags.items():
            bullet = self._playbook.get_bullet_by_id(bullet_id)
            if bullet is None:
                continue

            # Increment appropriate counter
            if tag == BulletTag.HELPFUL:
                bullet.metadata.helpful_count += 1
            elif tag == BulletTag.HARMFUL:
                bullet.metadata.harmful_count += 1
            elif tag == BulletTag.NEUTRAL:
                bullet.metadata.neutral_count += 1

            bullet.metadata.last_updated = datetime.now()
            updated_count += 1

        return updated_count

    # ========================================================================
    # Utilities
    # ========================================================================

    def _generate_bullet_id(self, section: str, prefix: str) -> str:
        """
        Generate unique bullet ID with section prefix.

        Format: {prefix}-{NNNNN} (e.g., "mat-00001")

        Args:
            section: Section name
            prefix: Section prefix (e.g., "mat")

        Returns:
            Unique bullet ID
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        # Find highest existing number for this prefix
        max_num = 0
        for bullet in self._playbook.bullets:
            if bullet.id.startswith(f"{prefix}-"):
                try:
                    num = int(bullet.id.split('-')[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    continue

        # Generate new ID
        new_num = max_num + 1
        return f"{prefix}-{new_num:05d}"

    def get_statistics(self) -> Dict:
        """
        Get playbook statistics.

        Returns:
            Dict with size, section distribution, metadata stats, etc.
        """
        if self._playbook is None:
            raise ValueError("No playbook loaded")

        section_counts = {}
        total_helpful = 0
        total_harmful = 0
        total_neutral = 0

        for bullet in self._playbook.bullets:
            # Section distribution
            section_counts[bullet.section] = section_counts.get(bullet.section, 0) + 1

            # Metadata aggregation
            total_helpful += bullet.metadata.helpful_count
            total_harmful += bullet.metadata.harmful_count
            total_neutral += bullet.metadata.neutral_count

        return {
            "total_bullets": self._playbook.size,
            "sections": section_counts,
            "total_helpful_tags": total_helpful,
            "total_harmful_tags": total_harmful,
            "total_neutral_tags": total_neutral,
            "version": self._playbook.version,
            "last_updated": self._playbook.last_updated.isoformat(),
            "total_generations": self._playbook.total_generations
        }

    @property
    def playbook(self) -> Optional[Playbook]:
        """Get current playbook instance."""
        return self._playbook
