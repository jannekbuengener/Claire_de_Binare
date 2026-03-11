"""
Configuration loader for the Discussion Pipeline.

Loads pipeline configuration from the local working-repo canon and falls back
to the local Docs-Hub snapshot when needed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigLoader:
    """
    Loads and validates pipeline configuration from the docs workspace.

    Resolution strategy:
    1. Explicit path / CLI argument
    2. DOCS_HUB_PATH environment variable
    3. Local working repo canon
    4. Local archive snapshot (docs/archive/docs_hub_snapshot)
    """

    def __init__(self, docs_hub_path: Optional[str] = None):
        self.workspace_path = self._resolve_workspace_path(docs_hub_path)
        self.docs_hub_path = self.workspace_path
        self.config_file = self._resolve_config_file(self.workspace_path)
        self.discussions_path = self._resolve_discussions_path(self.workspace_path)
        self.issue_template_path = self._resolve_issue_template_path(
            self.workspace_path
        )

        if not self.config_file.exists():
            raise FileNotFoundError(
                f"Pipeline configuration not found at: {self.config_file}"
            )

    def _resolve_workspace_path(self, explicit_path: Optional[str] = None) -> Path:
        if explicit_path:
            path = Path(explicit_path).resolve()
            if self._validate_workspace(path):
                return path
            raise FileNotFoundError(f"Invalid docs workspace path: {explicit_path}")

        env_path = os.getenv("DOCS_HUB_PATH")
        if env_path:
            path = Path(env_path).resolve()
            if self._validate_workspace(path):
                return path

        working_repo = Path(__file__).resolve().parents[4]
        if self._validate_workspace(working_repo):
            return working_repo

        snapshot_docs = working_repo / "docs" / "archive" / "docs_hub_snapshot"
        if self._validate_workspace(snapshot_docs):
            return snapshot_docs.resolve()

        raise FileNotFoundError(
            "Could not locate docs workspace.\n\n"
            "Tried:\n"
            f"1. DOCS_HUB_PATH env var: {env_path or 'not set'}\n"
            f"2. Working repo root: {working_repo}\n"
            f"3. Local archive snapshot: {snapshot_docs}\n\n"
            "Provide --docs-hub / DOCS_HUB_PATH or restore the local canon paths."
        )

    def _resolve_config_file(self, workspace_path: Path) -> Path:
        candidates = [
            workspace_path
            / "knowledge"
            / "discussions"
            / "config"
            / "pipeline_rules.yaml",
            workspace_path / "config" / "pipeline_rules.yaml",
            workspace_path
            / "_archive"
            / "discussion_pipeline"
            / "config"
            / "pipeline_rules.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _resolve_discussions_path(self, workspace_path: Path) -> Path:
        candidates = [
            workspace_path / "knowledge" / "discussions",
            workspace_path / "discussions",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _resolve_issue_template_path(self, workspace_path: Path) -> Path:
        candidates = [
            workspace_path / "docs" / "templates" / "github_issue.md",
            workspace_path / "knowledge" / "templates" / "github_issue.md",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _validate_workspace(self, path: Path) -> bool:
        if not path.exists():
            return False
        return (
            self._resolve_config_file(path).exists()
            and self._resolve_discussions_path(path).exists()
        )

    def load_config(self) -> Dict[str, Any]:
        with open(self.config_file, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)

        required_sections = ["pipelines", "gates", "agents"]
        missing = [section for section in required_sections if section not in config]
        if missing:
            raise ValueError(
                f"Invalid pipeline configuration. Missing sections: {missing}"
            )

        return config

    def get_pipeline_preset(self, preset_name: str) -> Dict[str, Any]:
        config = self.load_config()
        if preset_name not in config["pipelines"]:
            available = list(config["pipelines"].keys())
            raise KeyError(f"Unknown preset: {preset_name}. Available: {available}")
        return config["pipelines"][preset_name]

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        config = self.load_config()
        if agent_name not in config["agents"]:
            available = list(config["agents"].keys())
            raise KeyError(f"Unknown agent: {agent_name}. Available: {available}")
        return config["agents"][agent_name]

    def get_gate_config(self) -> Dict[str, Any]:
        config = self.load_config()
        return config["gates"]

    def get_quality_config(self) -> Dict[str, Any]:
        config = self.load_config()
        return config.get("quality", {})
