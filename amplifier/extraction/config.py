#!/usr/bin/env python3
"""
Configuration for Memory Extraction system.
Uses the main configuration system for consistency.
"""

from pathlib import Path


class MemoryExtractionConfig:
    """Configuration for Memory Extraction system using main config"""

    def __init__(self):
        """Initialize configuration from main system"""
        from amplifier.config.config import config

        self._config = config

    @property
    def memory_system_enabled(self) -> bool:
        """Enable memory extraction system (must be explicitly set to true)"""
        return self._config.memory_system.enabled

    @property
    def memory_extraction_model(self) -> str:
        """Model for memory extraction (fast, efficient, cost-effective)"""
        return self._config.memory_system.model

    @property
    def memory_extraction_timeout(self) -> int:
        """Timeout in seconds for Claude Code SDK extraction operations"""
        return self._config.memory_system.timeout

    @property
    def memory_extraction_max_messages(self) -> int:
        """Maximum number of recent messages to process for extraction"""
        return self._config.memory_system.max_messages

    @property
    def memory_extraction_max_content_length(self) -> int:
        """Maximum characters per message to process"""
        return self._config.memory_system.max_content_length

    @property
    def memory_extraction_max_memories(self) -> int:
        """Maximum number of memories to extract per session"""
        return self._config.memory_system.max_memories

    @property
    def memory_storage_dir(self) -> Path:
        """Directory for storing extracted memories"""
        return Path(self._config.memory_system.storage_dir)

    @property
    def anthropic_api_key(self) -> str | None:
        """Anthropic API key (optional, Claude Code SDK may provide)"""
        return self._config.optional.anthropic_api_key

    def ensure_storage_dir(self) -> Path:
        """Ensure storage directory exists and return it"""
        self.memory_storage_dir.mkdir(parents=True, exist_ok=True)
        return self.memory_storage_dir


# Singleton instance
_config: MemoryExtractionConfig | None = None


def get_config() -> MemoryExtractionConfig:
    """Get or create the configuration singleton"""
    global _config
    if _config is None:
        _config = MemoryExtractionConfig()
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)"""
    global _config
    _config = None
