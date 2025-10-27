"""
Playbook Manager for ACE Framework.

Implements playbook operations:
- Load/save from JSON
- Semantic bullet retrieval (top-k similarity)
- Metadata updates (helpful/harmful counts)
- ID generation with section prefixes
- Embedding cache management (独立文件，支持增量更新)
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import numpy as np

# 使用Qwen embedding替代sentence-transformers
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.qwen_embedding import QwenEmbeddingProvider, util

from .schemas import Playbook, PlaybookBullet, BulletMetadata, BulletTag

# Embedding cache 配置
CACHE_VERSION = "1.0"
CACHE_EMBEDDING_DIM = 1024  # Qwen text-embedding-v4 的维度


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
        # Cache 文件路径：在同目录下，文件名前加点（隐藏文件）
        self.cache_path = self.playbook_path.parent / f".{self.playbook_path.stem}.embeddings"
        self.embedding_model = embedding_model
        self.embedding_provider = QwenEmbeddingProvider(model=embedding_model, api_key=api_key)
        self._playbook: Optional[Playbook] = None
        self._embeddings_cache: Dict[str, np.ndarray] = {}  # bullet_id -> embedding

    # ========================================================================
    # Load / Save
    # ========================================================================

    def load(self) -> Playbook:
        """
        Load playbook from JSON file with embedding cache support.

        流程：
        1. 加载 playbook.json
        2. 尝试加载 cache 文件
        3. 检测同步状态
        4. 增量更新（只计算变化的部分）
        5. 保存更新后的 cache

        Returns:
            Playbook object

        Raises:
            FileNotFoundError: If playbook file doesn't exist
        """
        if not self.playbook_path.exists():
            raise FileNotFoundError(f"Playbook not found: {self.playbook_path}")

        # Step 1: 加载主文件
        with open(self.playbook_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse with Pydantic for validation
        self._playbook = Playbook(**data)

        # Step 2: 加载缓存
        cache_data = self._load_cache_file()

        if cache_data is None:
            print("  ℹ️  缓存文件不存在，将创建新缓存")
            cache_data = self._create_empty_cache()

        # Step 3: 检测同步状态
        sync_status = self._detect_sync_status(self._playbook, cache_data)

        needs_compute = sync_status["needs_create"] + sync_status["needs_update"]

        if needs_compute:
            print(f"  🔄 需要更新 {len(needs_compute)} 个 embedding")
            if sync_status['needs_create']:
                print(f"     新增: {len(sync_status['needs_create'])}")
            if sync_status['needs_update']:
                print(f"     更新: {len(sync_status['needs_update'])}")
            if sync_status['needs_delete']:
                print(f"     删除: {len(sync_status['needs_delete'])}")

            # Step 4: 批量计算
            self._compute_and_update_embeddings(self._playbook, needs_compute, cache_data)
        else:
            print(f"  ✅ 缓存完全同步，加载 {len(sync_status['up_to_date'])} 个 embedding")

        # Step 5: 删除过期的缓存
        for bullet_id in sync_status["needs_delete"]:
            if bullet_id in cache_data["embeddings"]:
                del cache_data["embeddings"][bullet_id]

        # Step 6: 加载到内存
        self._load_embeddings_to_memory(self._playbook, cache_data)

        # Step 7: 保存更新后的缓存
        if needs_compute or sync_status["needs_delete"]:
            self._save_cache_file(cache_data)

        return self._playbook

    def save(self, playbook: Optional[Playbook] = None) -> None:
        """
        Save playbook to JSON file (不含 embedding，保持文件简洁).

        注意：
        - 只保存主文件，不更新缓存
        - 缓存会在下次加载时自动同步
        - 这样避免保存时的额外计算开销

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

        # Remove embeddings from metadata before saving (保持文件简洁)
        for bullet in data.get('bullets', []):
            if 'metadata' in bullet and 'embedding' in bullet['metadata']:
                bullet['metadata']['embedding'] = None

        with open(self.playbook_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        # 不主动更新缓存，延迟到下次加载时
        # 理由：
        # 1. 避免每次保存都触发embedding计算
        # 2. 如果保存后不立即使用，无需浪费计算
        # 3. 下次加载时会自动检测并同步

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

    # ========================================================================
    # Embedding Cache 管理
    # ========================================================================

    def _compute_content_hash(self, content: str) -> str:
        """计算 bullet content 的 SHA256 hash（前16字符）

        Args:
            content: Bullet 内容

        Returns:
            Hash 字符串（16字符）
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _create_empty_cache(self) -> dict:
        """创建空的 cache 数据结构"""
        return {
            "version": CACHE_VERSION,
            "embedding_model": self.embedding_model,
            "embedding_dim": CACHE_EMBEDDING_DIM,
            "last_sync": datetime.now().isoformat(),
            "bullet_count": 0,
            "embeddings": {}
        }

    def _load_cache_file(self) -> Optional[dict]:
        """加载 embedding cache 文件

        Returns:
            Cache 数据，如果文件不存在或损坏返回 None
        """
        if not self.cache_path.exists():
            return None

        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 验证版本兼容性
            if not self._validate_cache_version(cache_data):
                print(f"  ⚠️  缓存版本不兼容，将重新创建")
                return None

            return cache_data
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"  ⚠️  缓存文件损坏: {e}")
            return None

    def _validate_cache_version(self, cache_data: dict) -> bool:
        """检查缓存版本是否兼容

        Args:
            cache_data: Cache 数据

        Returns:
            是否兼容
        """
        if cache_data.get("version") != CACHE_VERSION:
            print(f"  ⚠️  缓存版本不匹配: {cache_data.get('version')} != {CACHE_VERSION}")
            return False

        if cache_data.get("embedding_model") != self.embedding_model:
            print(f"  ⚠️  Embedding 模型不匹配: {cache_data.get('embedding_model')} != {self.embedding_model}")
            return False

        return True

    def _save_cache_file(self, cache_data: dict) -> None:
        """原子写入 cache 文件

        Args:
            cache_data: Cache 数据
        """
        temp_file = self.cache_path.with_suffix('.tmp')

        try:
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # 原子替换
            temp_file.replace(self.cache_path)
        except Exception as e:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
            raise RuntimeError(f"Failed to save cache file: {e}")

    def _detect_sync_status(self, playbook: Playbook, cache_data: dict) -> dict:
        """检测 playbook 和 cache 的同步状态

        Args:
            playbook: 当前 playbook
            cache_data: Cache 数据

        Returns:
            同步状态字典:
            {
                "needs_create": ["mat-00005"],     # 新增的bullets
                "needs_update": ["mat-00001"],     # 内容变化的bullets
                "needs_delete": ["mat-00002"],     # 删除的bullets
                "up_to_date": ["mat-00003", ...]   # 无需更新的bullets
            }
        """
        cached_embeddings = cache_data.get("embeddings", {})
        current_bullets = {b.id: b for b in playbook.bullets}

        result = {
            "needs_create": [],
            "needs_update": [],
            "needs_delete": [],
            "up_to_date": []
        }

        # 检查现有bullets
        for bullet_id, bullet in current_bullets.items():
            current_hash = self._compute_content_hash(bullet.content)

            if bullet_id not in cached_embeddings:
                # 新增
                result["needs_create"].append(bullet_id)
            elif cached_embeddings[bullet_id].get("content_hash") != current_hash:
                # 内容变化
                result["needs_update"].append(bullet_id)
            else:
                # 无需更新
                result["up_to_date"].append(bullet_id)

        # 检查删除的bullets
        for bullet_id in cached_embeddings:
            if bullet_id not in current_bullets:
                result["needs_delete"].append(bullet_id)

        return result

    def _compute_and_update_embeddings(
        self,
        playbook: Playbook,
        bullet_ids: List[str],
        cache_data: dict
    ) -> None:
        """批量计算并更新 embedding

        Args:
            playbook: 当前 playbook
            bullet_ids: 需要计算的 bullet IDs
            cache_data: Cache 数据（会被直接修改）
        """
        bullets_to_compute = [
            b for b in playbook.bullets if b.id in bullet_ids
        ]

        if not bullets_to_compute:
            return

        # 批量计算（减少API调用）
        contents = [b.content for b in bullets_to_compute]
        print(f"  🔄 正在计算 {len(contents)} 个 embedding...")

        embeddings = self.embedding_provider.encode(
            contents,
            show_progress_bar=False
        )

        # 更新缓存
        for bullet, embedding in zip(bullets_to_compute, embeddings):
            content_hash = self._compute_content_hash(bullet.content)
            cache_data["embeddings"][bullet.id] = {
                "content_hash": content_hash,
                "embedding": embedding.tolist()
            }

        # 更新元数据
        cache_data["last_sync"] = datetime.now().isoformat()
        cache_data["bullet_count"] = len(playbook.bullets)

        print(f"  ✅ 已更新 {len(bullets_to_compute)} 个 embedding")

    def _load_embeddings_to_memory(self, playbook: Playbook, cache_data: dict) -> None:
        """从 cache 加载 embedding 到内存

        Args:
            playbook: 当前 playbook
            cache_data: Cache 数据
        """
        cached_embeddings = cache_data.get("embeddings", {})

        for bullet in playbook.bullets:
            if bullet.id in cached_embeddings:
                embedding_list = cached_embeddings[bullet.id]["embedding"]
                self._embeddings_cache[bullet.id] = np.array(embedding_list)

    def _build_embeddings_cache(self) -> None:
        """Build embeddings for all bullets in current playbook.

        【已废弃】此方法已被新的缓存机制替代，保留用于向后兼容。
        现在使用独立的 cache 文件和增量更新机制。

        Optimized for incremental loading:
        - Reuses existing embeddings from metadata if available
        - Only computes missing embeddings via API
        """
        if self._playbook is None:
            return

        if not self._playbook.bullets:
            return

        # Separate bullets into: has_embedding vs needs_embedding
        bullets_with_embedding = []
        bullets_needing_embedding = []

        for bullet in self._playbook.bullets:
            if bullet.metadata.embedding is not None and len(bullet.metadata.embedding) > 0:
                # Load from persisted metadata
                bullets_with_embedding.append(bullet)
                self._embeddings_cache[bullet.id] = np.array(bullet.metadata.embedding)
            else:
                # Needs computation
                bullets_needing_embedding.append(bullet)

        # Batch compute missing embeddings
        if bullets_needing_embedding:
            contents = [b.content for b in bullets_needing_embedding]
            embeddings = self.embedding_provider.encode(
                contents,
                show_progress_bar=False
            )

            # Store newly computed embeddings
            for bullet, embedding in zip(bullets_needing_embedding, embeddings):
                self._embeddings_cache[bullet.id] = embedding
                bullet.metadata.embedding = embedding.tolist()

            print(f"  ℹ️  Computed {len(bullets_needing_embedding)} new embeddings, "
                  f"loaded {len(bullets_with_embedding)} from cache")

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
