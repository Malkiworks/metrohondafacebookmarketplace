from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config.yaml")


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        example = Path("config.example.yaml")
        raise FileNotFoundError(
            f"Missing {config_path}. Copy {example} to config.yaml and edit it."
        )
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
