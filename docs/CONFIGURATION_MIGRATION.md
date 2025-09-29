# Configuration Migration Guide

## Overview

Amplifier configuration has been unified under `.amplifier/config.yaml` to provide a single, consistent source of truth for all configuration. This replaces the previous dual system of `.env` files and `.amplifier/config.yaml`.

## What Changed

### Before: Dual Configuration System
- **`.env`**: Used for environment variables (paths, models, processing limits)
- **`.amplifier/config.yaml`**: Used only for directory configuration

### After: Unified Configuration System
- **`.amplifier/config.yaml`**: Single source for all configuration with comprehensive defaults
- **Environment variables**: Now used as overrides rather than fallbacks
- **Default configuration factory**: Provides complete default values for all settings

## Migration Steps

### 1. Update Your Configuration File

Your `.amplifier/config.yaml` should now include all configuration sections:

```yaml
# Directory configuration (existing)
directory: git+microsoft/amplifier/directory

# Path configuration
paths:
  data_dir: .data
  content_dirs:
    - .data/content

# Model configuration
models:
  fast: claude-3-5-haiku-20241022
  default: claude-sonnet-4-20250514
  thinking: claude-opus-4-1-20250805
  # Legacy model configuration (being phased out)
  knowledge_mining: claude-3-5-haiku-20241022
  knowledge_extraction: claude-sonnet-4-20250514

# Content processing configuration
content_processing:
  max_chars: 50000
  classification_chars: 1500

# Knowledge mining configuration
knowledge_mining:
  storage_dir: .data/knowledge_mining
  default_doc_type: general
  max_chars: 50000
  classification_chars: 1500
  model: claude-3-5-haiku-20241022
  extraction_model: claude-sonnet-4-20250514

# Memory system configuration
memory_system:
  enabled: false
  model: claude-3-5-haiku-20241022
  timeout: 120
  max_messages: 20
  max_content_length: 500
  max_memories: 10
  storage_dir: .data/memories

# Smoke test configuration
smoke_test:
  model_category: fast
  skip_on_ai_unavailable: true
  ai_timeout: 30
  max_output_chars: 5000
  test_data_dir: .smoke_test_data

# Optional configuration
optional:
  debug: false
  # API keys are optional - Claude Code SDK may provide these
  # anthropic_api_key: your_api_key_here
```

### 2. Environment Variable Naming

Environment variables are automatically generated from configuration paths:

**Format**: All variables are prefixed with `AMPLIFIER__`, then section and keys are converted to uppercase, with nesting represented by `__` (double underscore)

**Examples**:
- `AMPLIFIER__MODELS__DEFAULT` → `models.default`
- `AMPLIFIER__PATHS__DATA_DIR` → `paths.data_dir`
- `AMPLIFIER__MEMORY_SYSTEM__ENABLED` → `memory_system.enabled`
- `AMPLIFIER__SMOKE_TEST__AI_TIMEOUT` → `smoke_test.ai_timeout`

**Backward Compatibility Shortcuts**:
- `DEBUG` → `optional.debug`
- `ANTHROPIC_API_KEY` → `optional.anthropic_api_key`
- `AMPLIFIER_DATA_DIR` → `paths.data_dir` (legacy)
- `AMPLIFIER_CONTENT_DIRS` → `paths.content_dirs` (legacy)
- `AMPLIFIER_MODEL_DEFAULT` → `models.default` (legacy)

### 3. Environment Variable Overrides

The new system uses environment variables as overrides:
- Configuration starts with comprehensive defaults
- Values from `.amplifier/config.yaml` override defaults
- Environment variables override both defaults and YAML values
- Environment variable names are automatically mapped from config keys

## Benefits

### 1. Centralized Configuration
- Single file to manage all Amplifier settings
- Clear structure and organization
- Better documentation through YAML comments

### 2. Version Control Friendly
- YAML format is more readable in diffs
- Easy to track configuration changes
- Better for sharing configurations across teams

### 3. Hierarchical Organization
- Logical grouping of related settings
- Clear separation between different subsystems
- Easier to understand relationships between settings

### 4. Type Safety and Defaults
- Configuration is validated using Pydantic models
- Clear error messages for invalid configurations
- Auto-completion support in IDEs
- Comprehensive defaults ensure no missing configuration

## Accessing Configuration in Code

### New Unified API
```python
from amplifier.config.config import config

# Access configuration values
data_dir = config.paths.data_dir
model = config.models.default
max_chars = config.knowledge_mining.max_chars
```

### Default Configuration Factory
```python
from amplifier.config.config import AmplifierConfig

# Generate complete default configuration
defaults = AmplifierConfig.default_config()
```

### Existing APIs Still Work
```python
# These continue to work unchanged
from amplifier.config.paths import paths
from amplifier.smoke_tests.config import config as smoke_config
```

## Troubleshooting

### Configuration Not Loading
1. Check that `.amplifier/config.yaml` exists and is valid YAML
2. Verify file permissions are readable
3. Check for syntax errors in the YAML file

### Values Not Taking Effect
1. Configuration is loaded at startup - restart the application
2. Check for typos in section names or field names
3. Verify data types match expected types (string, number, boolean, list)

### Environment Variables Not Working
Environment variables now work as overrides and will always take precedence when set:
1. Verify the environment variable name matches the expected format
2. Check that the value type is correct (strings for text, "true"/"false" for booleans, numbers for integers)
3. Environment variables override both defaults and YAML values

## Examples

### Minimal Configuration
```yaml
directory: git+microsoft/amplifier/directory
```
(All other values use defaults or environment variable fallbacks)

### Development Configuration
```yaml
directory: git+microsoft/amplifier/directory
paths:
  data_dir: .dev-data
  content_dirs:
    - ./docs
    - ./examples
models:
  default: claude-sonnet-4-20250514
optional:
  debug: true
```

### Production Configuration
```yaml
directory: git+microsoft/amplifier/directory
paths:
  data_dir: /app/data
  content_dirs:
    - /app/content
    - /shared/docs
models:
  default: claude-opus-4-1-20250805
memory_system:
  enabled: true
  timeout: 300
optional:
  debug: false
```