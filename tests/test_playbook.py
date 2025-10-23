"""
Unit tests for ACE Playbook schemas and manager.

Tests core functionality without requiring LLM API calls.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from src.ace_framework.playbook.schemas import (
    BulletMetadata,
    PlaybookBullet,
    Playbook,
    BulletTag
)
from src.ace_framework.playbook.playbook_manager import PlaybookManager


class TestBulletMetadata:
    """Test BulletMetadata functionality."""

    def test_default_values(self):
        """Test default metadata values."""
        metadata = BulletMetadata()

        assert metadata.helpful_count == 0
        assert metadata.harmful_count == 0
        assert metadata.neutral_count == 0
        assert metadata.source == "seed"
        assert metadata.total_uses == 0
        assert metadata.helpfulness_score == 0.5  # Neutral for unused

    def test_helpfulness_score_calculation(self):
        """Test helpfulness score computation."""
        # All helpful
        metadata = BulletMetadata(helpful_count=10, harmful_count=0, neutral_count=0)
        assert metadata.helpfulness_score == 1.0

        # All harmful
        metadata = BulletMetadata(helpful_count=0, harmful_count=10, neutral_count=0)
        assert metadata.helpfulness_score == 0.0

        # Mixed
        metadata = BulletMetadata(helpful_count=7, harmful_count=3, neutral_count=0)
        assert metadata.helpfulness_score == 0.7

        # With neutral
        metadata = BulletMetadata(helpful_count=5, harmful_count=2, neutral_count=3)
        assert metadata.helpfulness_score == 0.5  # 5 / 10


class TestPlaybookBullet:
    """Test PlaybookBullet functionality."""

    def test_bullet_creation(self):
        """Test creating a bullet."""
        bullet = PlaybookBullet(
            id="mat-00001",
            section="material_selection",
            content="Always verify reagent purity before use."
        )

        assert bullet.id == "mat-00001"
        assert bullet.section == "material_selection"
        assert len(bullet.content) > 0
        assert isinstance(bullet.metadata, BulletMetadata)

    def test_bullet_id_validation(self):
        """Test bullet ID format validation."""
        # Valid ID
        bullet = PlaybookBullet(
            id="proc-00005",
            section="procedure_design",
            content="Test content"
        )
        assert bullet.id == "proc-00005"

        # Invalid ID (no hyphen)
        with pytest.raises(ValueError):
            PlaybookBullet(
                id="invalid",
                section="test",
                content="Test"
            )


class TestPlaybook:
    """Test Playbook functionality."""

    def test_playbook_creation(self):
        """Test creating an empty playbook."""
        playbook = Playbook()

        assert len(playbook.bullets) == 0
        assert len(playbook.sections) == 6  # Default sections
        assert playbook.version == "1.0.0"
        assert playbook.total_generations == 0

    def test_get_bullets_by_section(self):
        """Test retrieving bullets by section."""
        bullet1 = PlaybookBullet(id="mat-00001", section="material_selection", content="Test 1")
        bullet2 = PlaybookBullet(id="mat-00002", section="material_selection", content="Test 2")
        bullet3 = PlaybookBullet(id="proc-00001", section="procedure_design", content="Test 3")

        playbook = Playbook(bullets=[bullet1, bullet2, bullet3])

        mat_bullets = playbook.get_bullets_by_section("material_selection")
        assert len(mat_bullets) == 2

        proc_bullets = playbook.get_bullets_by_section("procedure_design")
        assert len(proc_bullets) == 1

    def test_get_bullet_by_id(self):
        """Test retrieving bullet by ID."""
        bullet = PlaybookBullet(id="safe-00001", section="safety_protocols", content="Safety first")
        playbook = Playbook(bullets=[bullet])

        found = playbook.get_bullet_by_id("safe-00001")
        assert found is not None
        assert found.id == "safe-00001"

        not_found = playbook.get_bullet_by_id("nonexistent")
        assert not_found is None

    def test_playbook_size(self):
        """Test playbook size property."""
        playbook = Playbook()
        assert playbook.size == 0

        playbook.bullets.append(PlaybookBullet(id="test-00001", section="test", content="Test"))
        assert playbook.size == 1


class TestPlaybookManager:
    """Test PlaybookManager functionality."""

    @pytest.fixture
    def temp_playbook_path(self):
        """Create temporary playbook path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = Path(f.name)
        yield path
        # Cleanup
        if path.exists():
            path.unlink()

    def test_save_and_load(self, temp_playbook_path):
        """Test saving and loading playbook."""
        manager = PlaybookManager(
            playbook_path=str(temp_playbook_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"  # Small model for testing
        )

        # Create playbook
        playbook = Playbook()
        playbook.bullets.append(
            PlaybookBullet(id="test-00001", section="test", content="Test bullet")
        )

        # Save
        manager._playbook = playbook
        manager.save()

        assert temp_playbook_path.exists()

        # Load
        manager2 = PlaybookManager(
            playbook_path=str(temp_playbook_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        loaded = manager2.load()

        assert loaded.size == 1
        assert loaded.bullets[0].id == "test-00001"

    def test_add_bullet(self, temp_playbook_path):
        """Test adding bullet to playbook."""
        manager = PlaybookManager(
            playbook_path=str(temp_playbook_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )

        playbook = manager.get_or_create()
        initial_size = playbook.size

        # Add bullet
        new_bullet = manager.add_bullet(
            content="New test bullet",
            section="material_selection",
            id_prefix="mat",
            source="test"
        )

        assert new_bullet.id.startswith("mat-")
        assert manager.playbook.size == initial_size + 1

    def test_update_bullet_tags(self, temp_playbook_path):
        """Test updating bullet metadata from tags."""
        manager = PlaybookManager(
            playbook_path=str(temp_playbook_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Create playbook with bullet
        playbook = Playbook()
        bullet = PlaybookBullet(id="test-00001", section="test", content="Test")
        playbook.bullets.append(bullet)
        manager._playbook = playbook

        # Update tags
        tags = {
            "test-00001": BulletTag.HELPFUL
        }
        updated = manager.update_bullet_tags(tags)

        assert updated == 1
        assert bullet.metadata.helpful_count == 1
        assert bullet.metadata.helpfulness_score > 0.5

    def test_remove_bullet(self, temp_playbook_path):
        """Test removing bullet."""
        manager = PlaybookManager(
            playbook_path=str(temp_playbook_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Create playbook
        playbook = Playbook()
        playbook.bullets.append(PlaybookBullet(id="test-00001", section="test", content="Test 1"))
        playbook.bullets.append(PlaybookBullet(id="test-00002", section="test", content="Test 2"))
        manager._playbook = playbook

        initial_size = playbook.size

        # Remove bullet
        removed = manager.remove_bullet("test-00001")

        assert removed is True
        assert manager.playbook.size == initial_size - 1
        assert manager.playbook.get_bullet_by_id("test-00001") is None

    def test_generate_bullet_id(self, temp_playbook_path):
        """Test bullet ID generation."""
        manager = PlaybookManager(
            playbook_path=str(temp_playbook_path),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )

        playbook = manager.get_or_create()

        # Generate first ID
        id1 = manager._generate_bullet_id("material_selection", "mat")
        assert id1 == "mat-00001"

        # Add bullet with that ID
        playbook.bullets.append(
            PlaybookBullet(id=id1, section="material_selection", content="Test")
        )

        # Generate second ID
        id2 = manager._generate_bullet_id("material_selection", "mat")
        assert id2 == "mat-00002"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
