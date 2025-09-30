"""
Unified Configuration System for Amplifier

This module provides a single source of truth for all Amplifier configuration,
reading from .amplifier/config.yaml and providing a clean interface for accessing
configuration values throughout the application.

Usage:
    from amplifier.config.config import config

    # Access configuration values
    data_dir = config.paths.data_dir
    model = config.models.default
    max_chars = config.knowledge_mining.max_chars
"""

import os
from pathlib import Path
from typing import Any
from typing import Union

import yaml
from pydantic import BaseModel
from pydantic import Field


class PathsConfig(BaseModel):
    """Path configuration section."""

    data_dir: str = ".data"
    content_dirs: list[str] = Field(default_factory=lambda: [".data/content"])

    def resolve_path(self, path_str: Union[str, Path], repo_root: Path | None = None) -> Path:
        """Resolve a path string to an absolute Path object.

        Handles:
        - Relative paths (resolved from repo root)
        - Home directory paths (~/...)
        - Absolute paths
        """
        if repo_root is None:
            repo_root = Path.cwd()

        path = Path(path_str)

        # Expand home directory
        path = path.expanduser()

        # If already absolute, return as is
        if path.is_absolute():
            return path

        # Otherwise, resolve relative to repo root
        return (repo_root / path).resolve()


class ModelsConfig(BaseModel):
    """Model configuration section."""

    fast: str = "claude-3-5-haiku-20241022"
    default: str = "claude-sonnet-4-20250514"
    thinking: str = "claude-opus-4-1-20250805"

    # Legacy model configuration (being phased out)
    knowledge_mining: str = "claude-3-5-haiku-20241022"
    knowledge_extraction: str = "claude-sonnet-4-20250514"


class ContentProcessingConfig(BaseModel):
    """Content processing configuration section."""

    max_chars: int = 50000
    classification_chars: int = 1500


class KnowledgeMiningConfig(BaseModel):
    """Knowledge mining configuration section."""

    storage_dir: str = ".data/knowledge_mining"
    default_doc_type: str = "general"
    max_chars: int = 50000
    classification_chars: int = 1500
    model: str = "claude-3-5-haiku-20241022"
    extraction_model: str = "claude-sonnet-4-20250514"


class MemorySystemConfig(BaseModel):
    """Memory system configuration section."""

    enabled: bool = False
    model: str = "claude-3-5-haiku-20241022"
    timeout: int = 120
    max_messages: int = 20
    max_content_length: int = 500
    max_memories: int = 10
    storage_dir: str = ".data/memories"


class SmokeTestConfig(BaseModel):
    """Smoke test configuration section."""

    model_category: str = "fast"
    skip_on_ai_unavailable: bool = True
    ai_timeout: int = 30
    max_output_chars: int = 5000
    test_data_dir: str = ".smoke_test_data"


class OptionalConfig(BaseModel):
    """Optional configuration section."""

    debug: bool = False
    anthropic_api_key: str | None = None


class DirectoryConfig(BaseModel):
    """Directory configuration section (from original .amplifier/config.yaml)."""

    directory: str = "git+microsoft/amplifier/directory"


class AmplifierConfig(BaseModel):
    """Main configuration model."""

    # Core sections
    paths: PathsConfig = Field(default_factory=PathsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    content_processing: ContentProcessingConfig = Field(default_factory=ContentProcessingConfig)
    knowledge_mining: KnowledgeMiningConfig = Field(default_factory=KnowledgeMiningConfig)
    memory_system: MemorySystemConfig = Field(default_factory=MemorySystemConfig)
    smoke_test: SmokeTestConfig = Field(default_factory=SmokeTestConfig)
    optional: OptionalConfig = Field(default_factory=OptionalConfig)

    # Directory configuration (existing)
    directory: DirectoryConfig = Field(default_factory=DirectoryConfig)

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        """Generate default configuration dictionary for creating config.yaml files."""
        return {
            "directory": "git+https://github.com/microsoft/amplifier/directory.git@v0.2.0",
            "paths": {"data_dir": ".data", "content_dirs": [".data/content"]},
            "models": {
                "fast": "claude-3-5-haiku-20241022",
                "default": "claude-sonnet-4-20250514",
                "thinking": "claude-opus-4-1-20250805",
                "knowledge_mining": "claude-3-5-haiku-20241022",
                "knowledge_extraction": "claude-sonnet-4-20250514",
            },
            "content_processing": {"max_chars": 50000, "classification_chars": 1500},
            "knowledge_mining": {
                "storage_dir": ".data/knowledge_mining",
                "default_doc_type": "general",
                "max_chars": 50000,
                "classification_chars": 1500,
                "model": "claude-3-5-haiku-20241022",
                "extraction_model": "claude-sonnet-4-20250514",
            },
            "memory_system": {
                "enabled": False,
                "model": "claude-3-5-haiku-20241022",
                "timeout": 120,
                "max_messages": 20,
                "max_content_length": 500,
                "max_memories": 10,
                "storage_dir": ".data/memories",
            },
            "smoke_test": {
                "model_category": "fast",
                "skip_on_ai_unavailable": True,
                "ai_timeout": 30,
                "max_output_chars": 5000,
                "test_data_dir": ".smoke_test_data",
            },
            "optional": {"debug": False, "anthropic_api_key": None},
        }


class ConfigManager:
    """Configuration manager that reads from .amplifier/config.yaml with environment overrides."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.config_path = self.repo_root / ".amplifier" / "config.yaml"

        self._config = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file with environment variable overrides."""
        # Start with default configuration
        config_data = AmplifierConfig.default_config()

        # Override with YAML file if it exists
        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
                config_data = self._deep_merge(config_data, yaml_data)

        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)

        # Create configuration object
        self._config = AmplifierConfig(**config_data)

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to configuration.

        Environment variables are automatically generated from config keys:
        - All variables are prefixed with AMPLIFIER__
        - Section names and keys are converted to uppercase
        - Nesting is represented by __ (double underscore)
        - Examples: AMPLIFIER__MODELS__DEFAULT, AMPLIFIER__PATHS__DATA_DIR, AMPLIFIER__MEMORY_SYSTEM__ENABLED
        """

        result = config_data.copy()

        # Recursively apply environment overrides
        def apply_overrides(data: dict[str, Any], prefix: str = "AMPLIFIER") -> None:
            for key, value in data.items():
                env_var_name = f"{prefix}__{key}".upper()
                env_value = os.getenv(env_var_name)

                if env_value is not None:
                    # Convert string values to appropriate types based on original value
                    if isinstance(value, bool):
                        data[key] = env_value.lower() in ("true", "1", "yes")
                    elif isinstance(value, int):
                        data[key] = int(env_value)
                    elif isinstance(value, list):
                        data[key] = [item.strip() for item in env_value.split(",")]
                    else:
                        data[key] = env_value
                elif isinstance(value, dict):
                    # Recursively process nested dictionaries
                    apply_overrides(value, env_var_name)

        apply_overrides(result)

        # Handle common shortcut environment variables for backward compatibility
        shortcuts = {
            "DEBUG": ("optional", "debug", bool),
            "ANTHROPIC_API_KEY": ("optional", "anthropic_api_key", str),
            # Legacy compatibility for old AMPLIFIER_ prefixed variables
            "AMPLIFIER_DATA_DIR": ("paths", "data_dir", str),
            "AMPLIFIER_CONTENT_DIRS": ("paths", "content_dirs", list),
            "AMPLIFIER_MODEL_FAST": ("models", "fast", str),
            "AMPLIFIER_MODEL_DEFAULT": ("models", "default", str),
        }

        for env_var, (section, key, var_type) in shortcuts.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if section not in result:
                    result[section] = {}

                if var_type is bool:
                    result[section][key] = env_value.lower() in ("true", "1", "yes")
                elif var_type is int:
                    result[section][key] = int(env_value)
                elif var_type is list:
                    result[section][key] = [item.strip() for item in env_value.split(",")]
                else:
                    result[section][key] = env_value

        # Handle directory configuration (special case for backward compatibility)
        if "directory" in result and isinstance(result["directory"], str):
            result["directory"] = {"directory": result["directory"]}

        return result

    @property
    def config(self) -> AmplifierConfig:
        """Get the configuration object."""
        if self._config is None:
            self._load_config()
        assert self._config is not None  # Should be loaded by _load_config()
        return self._config

    def get_value(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the configuration value (e.g., 'paths.data_dir')
            default: Default value if key is not found

        Returns:
            The configuration value or default
        """
        keys = key_path.split(".")
        value = self.config

        try:
            for key in keys:
                if hasattr(value, key):
                    value = getattr(value, key)
                else:
                    return default
            return value
        except (AttributeError, KeyError):
            return default

    def reload(self) -> None:
        """Reload configuration from file."""
        self._config = None
        self._load_config()


# Global configuration instance
config_manager = ConfigManager()
config = config_manager.config
