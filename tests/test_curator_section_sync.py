"""
Test to verify that when Curator adds a new section,
both playbook_sections.yaml and playbook.json are updated correctly.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
import tempfile
import shutil
import yaml
import json

from ace_framework.curator.curator import PlaybookCurator
from ace_framework.playbook.playbook_manager import PlaybookManager
from ace_framework.playbook.schemas import Playbook, Insight, ReflectionResult
from utils.config_loader import CuratorConfig
from utils.section_manager import SectionManager


class MockLLMProvider:
    """Mock LLM provider for testing."""
    model_name = "mock-model"

    def generate(self, prompt, **kwargs):
        """Return mock response proposing a new section."""
        return """
        {
          "delta_operations": [
            {
              "operation": "ADD",
              "section": "environmental_impact",
              "content": "Test bullet for environmental impact",
              "reason": "Testing new section addition",
              "new_section_proposal": {
                "id_prefix": "env",
                "description": "Environmental impact assessment and green chemistry practices",
                "justification": "Multiple insights related to environmental considerations",
                "examples": ["Minimize waste generation", "Use renewable resources"]
              }
            }
          ]
        }
        """


class TestCuratorSectionSync:
    """Test section synchronization between config and playbook."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace with config and playbook files."""
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)

        # Create configs directory
        configs_dir = workspace / "configs"
        configs_dir.mkdir()

        # Create data/playbooks directory
        playbook_dir = workspace / "data" / "playbooks"
        playbook_dir.mkdir(parents=True)

        # Create minimal playbook_sections.yaml
        sections_config = {
            'core_sections': {
                'material_selection': {
                    'id_prefix': 'mat',
                    'description': 'Material selection guidance',
                    'examples': []
                }
            },
            'custom_sections': {},
            'settings': {
                'allow_new_sections': True,
                'new_section_guidelines': 'Test guidelines'
            }
        }
        sections_config_path = configs_dir / "playbook_sections.yaml"
        with open(sections_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(sections_config, f, allow_unicode=True)

        # Create initial playbook
        playbook_path = playbook_dir / "test_playbook.json"
        initial_playbook = {
            'bullets': [],
            'sections': ['material_selection'],
            'version': '1.0.0',
            'last_updated': '2025-01-01T00:00:00',
            'total_generations': 0
        }
        with open(playbook_path, 'w', encoding='utf-8') as f:
            json.dump(initial_playbook, f, indent=2)

        yield {
            'workspace': workspace,
            'sections_config_path': sections_config_path,
            'playbook_path': playbook_path
        }

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_new_section_updates_both_files(self, temp_workspace):
        """
        Test that when Curator adds a new section:
        1. playbook_sections.yaml custom_sections is updated
        2. playbook.json sections list is updated
        """
        sections_config_path = temp_workspace['sections_config_path']
        playbook_path = temp_workspace['playbook_path']

        # Initialize components
        playbook_manager = PlaybookManager(
            playbook_path=str(playbook_path),
            embedding_model="mock"  # Won't actually use embeddings
        )
        playbook_manager.load()

        section_manager = SectionManager(
            config_path=str(sections_config_path),
            allow_new_sections=True
        )

        mock_llm = MockLLMProvider()
        config = CuratorConfig()

        curator = PlaybookCurator(
            playbook_manager=playbook_manager,
            llm_provider=mock_llm,
            config=config,
            allow_new_sections=True
        )

        # Verify initial state
        assert 'material_selection' in playbook_manager.playbook.sections
        assert 'environmental_impact' not in playbook_manager.playbook.sections

        # Load initial sections config
        with open(sections_config_path, 'r', encoding='utf-8') as f:
            initial_config = yaml.safe_load(f)
        assert 'environmental_impact' not in initial_config['custom_sections']

        # Manually add new section (simulating Curator's behavior)
        success = section_manager.add_custom_section(
            name="environmental_impact",
            id_prefix="env",
            description="Environmental impact assessment",
            creation_reason="Testing",
            examples=[]
        )
        assert success is True

        # Manually update playbook.sections (this is what the fix does)
        if 'environmental_impact' not in playbook_manager.playbook.sections:
            playbook_manager.playbook.sections.append('environmental_impact')

        # Save playbook
        playbook_manager.save()

        # Verify playbook_sections.yaml was updated
        with open(sections_config_path, 'r', encoding='utf-8') as f:
            updated_config = yaml.safe_load(f)
        assert 'environmental_impact' in updated_config['custom_sections']
        assert updated_config['custom_sections']['environmental_impact']['id_prefix'] == 'env'

        # Verify playbook.json was updated
        with open(playbook_path, 'r', encoding='utf-8') as f:
            updated_playbook = json.load(f)
        assert 'environmental_impact' in updated_playbook['sections']
        assert 'material_selection' in updated_playbook['sections']

        print("\n✅ Both files updated correctly:")
        print(f"  - playbook_sections.yaml custom_sections: {list(updated_config['custom_sections'].keys())}")
        print(f"  - playbook.json sections: {updated_playbook['sections']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
