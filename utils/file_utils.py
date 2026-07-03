"""File and configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from utils.constants import PROJECT_ROOT


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load a YAML configuration file."""
    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def resolve_project_path(relative_path: str | Path) -> Path:
    """Resolve a path relative to the project root."""
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def discover_data_files(
    directories: list[Path],
    extensions: list[str],
    recursive: bool = True,
) -> list[Path]:
    """Discover data files with the given extensions under one or more directories."""
    discovered: list[Path] = []
    normalized_extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}

    for directory in directories:
        if not directory.exists():
            continue

        iterator = directory.rglob("*") if recursive else directory.glob("*")
        for path in iterator:
            if path.is_file() and path.suffix.lower() in normalized_extensions:
                discovered.append(path.resolve())

    return sorted(discovered)


def ensure_parent_directory(path: Path) -> None:
    """Create parent directories for a file path if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
