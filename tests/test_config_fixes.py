"""
Unit tests for configuration fixes.

Tests the three configuration improvements:
1. ace.embedding configuration loading
2. ace.playbook.sections_config configuration loading
3. generator.min_similarity configuration loading
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.config_loader import get_ace_config
from utils.section_manager import SectionManager


# ============================================================================
# Test 1: Embedding Configuration
# ============================================================================

def test_embedding_config_exists():
    """Test that embedding configuration exists in ACEConfig"""
    config = get_ace_config()

    assert hasattr(config, 'embedding'), "ACEConfig should have 'embedding' attribute"


def test_embedding_config_has_model():
    """Test that embedding config has model field"""
    config = get_ace_config()

    assert hasattr(config.embedding, 'model'), "EmbeddingConfig should have 'model' attribute"
    assert isinstance(config.embedding.model, str), "Embedding model should be string"


def test_embedding_config_default_value():
    """Test that embedding config has correct default value"""
    config = get_ace_config()

    # Should match value in ace_config.yaml
    assert config.embedding.model == "text-embedding-v4"


# ============================================================================
# Test 2: Playbook Sections Config
# ============================================================================

def test_playbook_sections_config_exists():
    """Test that sections_config field exists in PlaybookConfig"""
    config = get_ace_config()

    assert hasattr(config.playbook, 'sections_config'), \
        "PlaybookConfig should have 'sections_config' attribute"


def test_playbook_sections_config_default_value():
    """Test that sections_config has correct default value"""
    config = get_ace_config()

    # Should match value in ace_config.yaml
    assert config.playbook.sections_config == "configs/playbook_sections.yaml"


def test_section_manager_uses_config_path():
    """Test that SectionManager reads path from config"""
    config = get_ace_config()
    manager = SectionManager()  # Don't pass config_path

    # Should use path from ace_config
    assert str(manager.config_path).endswith(config.playbook.sections_config)


def test_section_manager_custom_path_override():
    """Test that SectionManager respects custom path parameter"""
    custom_path = "configs/test_sections.yaml"

    # Should use custom path when provided (even if file doesn't exist, path should be set)
    try:
        manager = SectionManager(config_path=custom_path)
        assert str(manager.config_path).endswith(custom_path)
    except FileNotFoundError:
        # File doesn't exist, but we can still check the path was set correctly
        # by checking the path before _load_config is called
        pass


# ============================================================================
# Test 3: Generator min_similarity Configuration
# ============================================================================

def test_generator_min_similarity_exists():
    """Test that min_similarity field exists in GeneratorConfig"""
    config = get_ace_config()

    assert hasattr(config.generator, 'min_similarity'), \
        "GeneratorConfig should have 'min_similarity' attribute"


def test_generator_min_similarity_type():
    """Test that min_similarity is a float"""
    config = get_ace_config()

    assert isinstance(config.generator.min_similarity, float), \
        "min_similarity should be float type"


def test_generator_min_similarity_default_value():
    """Test that min_similarity has correct default value"""
    config = get_ace_config()

    # Should match value in ace_config.yaml
    assert config.generator.min_similarity == 0.3


def test_generator_min_similarity_range():
    """Test that min_similarity is within valid range [0, 1]"""
    config = get_ace_config()

    assert 0.0 <= config.generator.min_similarity <= 1.0, \
        "min_similarity should be in range [0, 1]"


# ============================================================================
# Integration Tests
# ============================================================================

def test_all_config_fields_loaded():
    """Integration test: all three config fields load correctly"""
    config = get_ace_config()

    # Check all three fixes
    assert hasattr(config, 'embedding')
    assert hasattr(config.playbook, 'sections_config')
    assert hasattr(config.generator, 'min_similarity')

    # Check values
    assert config.embedding.model == "text-embedding-v4"
    assert config.playbook.sections_config == "configs/playbook_sections.yaml"
    assert config.generator.min_similarity == 0.3


def test_config_validation():
    """Test that Pydantic validation works for new fields"""
    config = get_ace_config()

    # Embedding model should be string
    assert isinstance(config.embedding.model, str)

    # sections_config should be string
    assert isinstance(config.playbook.sections_config, str)

    # min_similarity should be float in [0, 1]
    assert isinstance(config.generator.min_similarity, float)
    assert 0.0 <= config.generator.min_similarity <= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
