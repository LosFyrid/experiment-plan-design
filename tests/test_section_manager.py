"""
Unit tests for SectionManager.

Tests section loading, validation, and dynamic addition functionality.
"""

import pytest
from pathlib import Path
import tempfile
import yaml
import shutil

from src.utils.section_manager import SectionManager


class TestSectionManager:
    """Test SectionManager functionality."""

    @pytest.fixture
    def temp_config_path(self):
        """Create temporary section config for testing."""
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / "playbook_sections.yaml"

        # Copy original config
        original_path = Path(__file__).parent.parent / "configs" / "playbook_sections.yaml"
        if original_path.exists():
            shutil.copy(str(original_path), str(temp_path))
        else:
            # Create minimal config if original doesn't exist
            minimal_config = {
                'core_sections': {
                    'material_selection': {
                        'id_prefix': 'mat',
                        'description': 'Test description',
                        'examples': []
                    },
                    'procedure_design': {
                        'id_prefix': 'proc',
                        'description': 'Test description',
                        'examples': []
                    }
                },
                'custom_sections': {},
                'settings': {
                    'allow_new_sections': False,
                    'new_section_guidelines': 'Test guidelines'
                }
            }
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(minimal_config, f, allow_unicode=True)

        yield str(temp_path)

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_load_sections(self, temp_config_path):
        """Test loading section configuration."""
        sm = SectionManager(config_path=temp_config_path)

        sections = sm.get_all_sections()
        assert len(sections) >= 2  # At least core sections
        assert 'material_selection' in sections
        assert 'procedure_design' in sections

    def test_get_section_names(self, temp_config_path):
        """Test getting section names list."""
        sm = SectionManager(config_path=temp_config_path)

        names = sm.get_section_names()
        assert isinstance(names, list)
        assert len(names) >= 2
        assert 'material_selection' in names

    def test_get_id_prefixes(self, temp_config_path):
        """Test getting id_prefix mapping."""
        sm = SectionManager(config_path=temp_config_path)

        prefixes = sm.get_id_prefixes()
        assert isinstance(prefixes, dict)
        assert prefixes.get('material_selection') == 'mat'
        assert prefixes.get('procedure_design') == 'proc'

    def test_is_section_valid(self, temp_config_path):
        """Test section validation."""
        sm = SectionManager(config_path=temp_config_path)

        assert sm.is_section_valid('material_selection') is True
        assert sm.is_section_valid('nonexistent_section') is False

    def test_get_section_info(self, temp_config_path):
        """Test getting section information."""
        sm = SectionManager(config_path=temp_config_path)

        info = sm.get_section_info('material_selection')
        assert info is not None
        assert 'id_prefix' in info
        assert info['id_prefix'] == 'mat'

        # Non-existent section
        info = sm.get_section_info('nonexistent')
        assert info is None

    def test_is_new_section_allowed(self, temp_config_path):
        """Test checking if new sections are allowed."""
        sm = SectionManager(config_path=temp_config_path)

        # By default should be False in test config
        allowed = sm.is_new_section_allowed()
        assert isinstance(allowed, bool)

    def test_add_custom_section(self, temp_config_path):
        """Test adding a new custom section."""
        sm = SectionManager(config_path=temp_config_path)

        # Add new section
        success = sm.add_custom_section(
            name="environmental_impact",
            id_prefix="env",
            description="Environmental impact assessment and green chemistry practices",
            creation_reason="Testing custom section addition",
            examples=["Example 1", "Example 2"]
        )

        assert success is True

        # Verify section was added
        assert sm.is_section_valid("environmental_impact") is True

        # Check info
        info = sm.get_section_info("environmental_impact")
        assert info is not None
        assert info['id_prefix'] == 'env'
        assert 'created_at' in info
        assert info['creation_reason'] == "Testing custom section addition"

    def test_prevent_duplicate_section(self, temp_config_path):
        """Test that duplicate sections cannot be added."""
        sm = SectionManager(config_path=temp_config_path)

        # Try to add existing section
        success = sm.add_custom_section(
            name="material_selection",  # Already exists in core
            id_prefix="mat",
            description="Duplicate",
            creation_reason="Test"
        )

        assert success is False

    def test_prevent_duplicate_prefix(self, temp_config_path):
        """Test that duplicate ID prefixes cannot be added."""
        sm = SectionManager(config_path=temp_config_path)

        # Try to add section with existing prefix
        success = sm.add_custom_section(
            name="new_section",
            id_prefix="mat",  # Already used by material_selection
            description="Test",
            creation_reason="Test"
        )

        assert success is False

    def test_format_sections_for_prompt(self, temp_config_path):
        """Test formatting sections for Curator prompt."""
        sm = SectionManager(config_path=temp_config_path)

        formatted = sm.format_sections_for_prompt()

        assert isinstance(formatted, str)
        assert "Available Playbook Sections" in formatted
        assert "material_selection" in formatted
        assert "Valid sections" in formatted

    def test_format_includes_custom_marker(self, temp_config_path):
        """Test that custom sections are marked in prompt."""
        sm = SectionManager(config_path=temp_config_path)

        # Add custom section
        sm.add_custom_section(
            name="test_custom",
            id_prefix="tst",
            description="Test custom section",
            creation_reason="Test"
        )

        formatted = sm.format_sections_for_prompt()

        # Should contain custom marker
        assert "[CUSTOM]" in formatted
        assert "test_custom" in formatted

    def test_format_new_section_guidelines(self, temp_config_path):
        """Test that new section guidelines appear when allowed."""
        # Create config with allow_new_sections=True
        with open(temp_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        config['settings']['allow_new_sections'] = True

        with open(temp_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        sm = SectionManager(config_path=temp_config_path)
        formatted = sm.format_sections_for_prompt()

        assert "Proposing New Sections" in formatted
        assert sm.get_new_section_guidelines() in formatted

    def test_format_restricts_when_not_allowed(self, temp_config_path):
        """Test that restriction message appears when new sections not allowed."""
        # Ensure allow_new_sections=False
        with open(temp_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        config['settings']['allow_new_sections'] = False

        with open(temp_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

        sm = SectionManager(config_path=temp_config_path)
        formatted = sm.format_sections_for_prompt()

        assert "Only use sections listed above" in formatted
        assert "Do not create new sections" in formatted

    def test_get_stats(self, temp_config_path):
        """Test getting section statistics."""
        sm = SectionManager(config_path=temp_config_path)

        stats = sm.get_stats()

        assert 'total_sections' in stats
        assert 'core_sections' in stats
        assert 'custom_sections' in stats
        assert 'allow_new_sections' in stats
        assert 'sections' in stats

        assert stats['total_sections'] >= 2
        assert stats['core_sections'] >= 2
        assert stats['custom_sections'] == 0  # Initially no custom sections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
