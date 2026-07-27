"""Load local CI stage and resource configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml expected via requirements-dev
    yaml = None  # type: ignore[assignment]


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load ci/config/*.yaml")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def profiles_from_config(stages_cfg: dict[str, Any]) -> dict[str, list[str]]:
    profiles = stages_cfg.get("profiles") or {}
    return {str(k): list(v) for k, v in profiles.items()}


def stage_meta(stages_cfg: dict[str, Any], name: str) -> dict[str, Any]:
    stages = stages_cfg.get("stages") or {}
    meta = stages.get(name) or {}
    return dict(meta)
