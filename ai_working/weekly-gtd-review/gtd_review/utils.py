"""
Simple utilities for GTD review tool.

Simplified versions of amplifier utilities for standalone operation.
"""

import json
from pathlib import Path
from typing import Any


def get_data_dir() -> Path:
    """Get the data directory for storing session files."""
    # Use ~/.amplifier/gtd-review for session data
    data_dir = Path.home() / ".amplifier" / "gtd-review"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def read_json(filepath: Path | str) -> Any:
    """Read JSON from file."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Any, filepath: Path | str, indent: int = 2) -> None:
    """Write JSON to file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
