"""
Configuration loader for ACE Framework.

Loads and validates YAML configuration files using Pydantic.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


# ============================================================================
# Model Configuration
# ============================================================================

class ModelConfig(BaseModel):
    """LLM model configuration."""
    provider: str = Field(default="qwen", pattern="^(qwen|openai|anthropic)$")
    model_name: str = Field(default="qwen-max")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)


# ============================================================================
# ACE Component Configurations
# ============================================================================

class GeneratorConfig(BaseModel):
    """Configuration for ACE Generator."""
    max_playbook_bullets: int = Field(default=50, gt=0, description="Top-k bullets to retrieve")
    include_examples: bool = Field(default=True)
    enable_few_shot: bool = Field(default=True)
    few_shot_count: int = Field(default=3, ge=0)
    output_format: str = Field(default="structured", pattern="^(structured|markdown)$")


class ReflectorConfig(BaseModel):
    """Configuration for ACE Reflector."""
    max_refinement_rounds: int = Field(default=5, ge=1, le=10)
    enable_iterative: bool = Field(default=True)
    reflection_mode: str = Field(default="detailed", pattern="^(detailed|concise)$")
    bullet_tagging: bool = Field(default=True)


class CuratorConfig(BaseModel):
    """Configuration for ACE Curator."""
    update_mode: str = Field(default="incremental", pattern="^(incremental|lazy)$")
    deduplication_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    max_playbook_size: int = Field(default=200, gt=0)
    enable_grow_and_refine: bool = Field(default=True)
    prune_harmful_bullets: bool = Field(default=True)


# ============================================================================
# Playbook Configuration
# ============================================================================

class PlaybookConfig(BaseModel):
    """Playbook structure configuration."""
    default_path: str = Field(default="data/playbooks/chemistry_playbook.json")
    sections: List[str] = Field(
        default_factory=lambda: [
            "material_selection",
            "procedure_design",
            "safety_protocols",
            "quality_control",
            "troubleshooting",
            "common_mistakes"
        ]
    )
    id_prefixes: Dict[str, str] = Field(
        default_factory=lambda: {
            "material_selection": "mat",
            "procedure_design": "proc",
            "safety_protocols": "safe",
            "quality_control": "qc",
            "troubleshooting": "ts",
            "common_mistakes": "err"
        }
    )


# ============================================================================
# Training & Evaluation Configuration
# ============================================================================

class TrainingConfig(BaseModel):
    """Training configuration for offline adaptation."""
    num_epochs: int = Field(default=5, ge=1)
    batch_size: int = Field(default=1, ge=1)
    feedback_source: str = Field(default="llm_judge", pattern="^(llm_judge|human|auto)$")
    enable_offline_warmup: bool = Field(default=False)


class EvaluationConfig(BaseModel):
    """Evaluation configuration."""
    enable_auto_check: bool = Field(default=True)
    enable_llm_judge: bool = Field(default=True)
    evaluation_criteria: List[str] = Field(
        default_factory=lambda: [
            "completeness",
            "safety",
            "clarity",
            "executability",
            "cost_effectiveness"
        ]
    )


# ============================================================================
# Main ACE Configuration
# ============================================================================

class ACEConfig(BaseModel):
    """Complete ACE framework configuration."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)
    reflector: ReflectorConfig = Field(default_factory=ReflectorConfig)
    curator: CuratorConfig = Field(default_factory=CuratorConfig)
    playbook: PlaybookConfig = Field(default_factory=PlaybookConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)


# ============================================================================
# RAG Configuration
# ============================================================================

class VectorStoreConfig(BaseModel):
    """Vector store configuration."""
    type: str = Field(default="chroma", pattern="^(chroma|faiss|pinecone)$")
    persist_directory: str = Field(default="data/chroma_db")
    collection_name: str = Field(default="experiment_templates")


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration."""
    model_name: str = Field(default="BAAI/bge-large-zh-v1.5")
    device: str = Field(default="cpu", pattern="^(cpu|cuda)$")
    batch_size: int = Field(default=32, gt=0)


class RetrievalConfig(BaseModel):
    """Retrieval configuration."""
    top_k: int = Field(default=5, gt=0)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_reranking: bool = Field(default=False)
    reranker_model: Optional[str] = Field(default=None)


class DocumentProcessingConfig(BaseModel):
    """Document processing configuration."""
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)
    separators: List[str] = Field(default_factory=lambda: ["\n\n", "\n", "。", "；"])


class RAGConfig(BaseModel):
    """Complete RAG configuration."""
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    document_processing: DocumentProcessingConfig = Field(default_factory=DocumentProcessingConfig)


# ============================================================================
# Environment Settings
# ============================================================================

class EnvironmentSettings(BaseSettings):
    """Environment variables (from .env file)."""
    # API Keys
    dashscope_api_key: Optional[str] = Field(default=None, alias="DASHSCOPE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # Paths
    project_root: Optional[str] = Field(default=None, alias="PROJECT_ROOT")
    moses_root: Optional[str] = Field(default=None, alias="MOSES_ROOT")
    chroma_persist_dir: Optional[str] = Field(default=None, alias="CHROMA_PERSIST_DIR")

    # LLM Settings
    default_llm_provider: str = Field(default="qwen", alias="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(default="qwen-max", alias="DEFAULT_LLM_MODEL")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# ============================================================================
# Configuration Loader
# ============================================================================

class ConfigLoader:
    """
    Centralized configuration loader.

    Loads configurations from YAML files and environment variables.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Args:
            config_dir: Directory containing config files (default: configs/)
        """
        if config_dir is None:
            # Try to find project root
            project_root = os.getenv("PROJECT_ROOT")
            if project_root:
                config_dir = os.path.join(project_root, "configs")
            else:
                # Assume we're in src/utils/ and go up to project root
                # src/utils/config_loader.py -> src/utils/ -> src/ -> project_root/
                current_file = Path(__file__).resolve()
                config_dir = current_file.parent.parent.parent / "configs"

        self.config_dir = Path(config_dir)

        # Load configurations
        self._ace_config: Optional[ACEConfig] = None
        self._rag_config: Optional[RAGConfig] = None
        self._env_settings: Optional[EnvironmentSettings] = None

    def load_ace_config(self, config_path: Optional[str] = None) -> ACEConfig:
        """
        Load ACE framework configuration.

        Args:
            config_path: Path to ace_config.yaml (default: configs/ace_config.yaml)

        Returns:
            ACEConfig instance
        """
        if self._ace_config is not None:
            return self._ace_config

        if config_path is None:
            config_path = self.config_dir / "ace_config.yaml"
        else:
            config_path = Path(config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Parse nested structure
        if 'ace' in data:
            data = data['ace']

        self._ace_config = ACEConfig(**data)
        return self._ace_config

    def load_rag_config(self, config_path: Optional[str] = None) -> RAGConfig:
        """
        Load RAG configuration.

        Args:
            config_path: Path to rag_config.yaml (default: configs/rag_config.yaml)

        Returns:
            RAGConfig instance
        """
        if self._rag_config is not None:
            return self._rag_config

        if config_path is None:
            config_path = self.config_dir / "rag_config.yaml"
        else:
            config_path = Path(config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Parse nested structure
        if 'rag' in data:
            data = data['rag']

        self._rag_config = RAGConfig(**data)
        return self._rag_config

    def load_env_settings(self) -> EnvironmentSettings:
        """
        Load environment settings from .env file.

        Returns:
            EnvironmentSettings instance
        """
        if self._env_settings is not None:
            return self._env_settings

        self._env_settings = EnvironmentSettings()
        return self._env_settings

    @property
    def ace_config(self) -> ACEConfig:
        """Get ACE config (loads if not already loaded)."""
        if self._ace_config is None:
            return self.load_ace_config()
        return self._ace_config

    @property
    def rag_config(self) -> RAGConfig:
        """Get RAG config (loads if not already loaded)."""
        if self._rag_config is None:
            return self.load_rag_config()
        return self._rag_config

    @property
    def env_settings(self) -> EnvironmentSettings:
        """Get environment settings (loads if not already loaded)."""
        if self._env_settings is None:
            return self.load_env_settings()
        return self._env_settings


# ============================================================================
# Global Singleton Instance
# ============================================================================

_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get global ConfigLoader singleton."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_ace_config() -> ACEConfig:
    """Convenience function to get ACE config."""
    return get_config_loader().ace_config


def get_rag_config() -> RAGConfig:
    """Convenience function to get RAG config."""
    return get_config_loader().rag_config


def get_env_settings() -> EnvironmentSettings:
    """Convenience function to get environment settings."""
    return get_config_loader().env_settings
