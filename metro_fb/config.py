from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.example.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        config_path = EXAMPLE_CONFIG_PATH
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
