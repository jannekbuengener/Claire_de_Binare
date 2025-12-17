"""
Configuration loader for the Discussion Pipeline.

Handles loading pipeline_rules.yaml from the Docs Hub workspace
with automatic path resolution.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """
    Loads and validates pipeline configuration from Docs Hub.

    Path resolution strategy:
    1. DOCS_HUB_PATH environment variable
    2. --docs-hub CLI argument
    3. Sibling directory auto-detection (../Claire_de_Binare_Docs)
    4. Interactive prompt (fallback)
    """

    def __init__(self, docs_hub_path: Optional[str] = None):
        """
        Initialize config loader.

        Args:
            docs_hub_path: Optional explicit path to Docs Hub workspace
        """
        self.docs_hub_path = self._resolve_docs_hub_path(docs_hub_path)
        self.config_file = self.docs_hub_path / "config" / "pipeline_rules.yaml"

        if not self.config_file.exists():
            raise FileNotFoundError(
                f"Pipeline configuration not found at: {self.config_file}\n"
                f"Expected Docs Hub at: {self.docs_hub_path}"
            )

    def _resolve_docs_hub_path(self, explicit_path: Optional[str] = None) -> Path:
        """
        Resolve the path to the Docs Hub workspace.

        Args:
            explicit_path: Optional explicit path (from CLI or constructor)

        Returns:
            Resolved Path to Docs Hub

        Raises:
            FileNotFoundError: If Docs Hub cannot be located
        """
        # Strategy 1: Explicit path (CLI argument or constructor)
        if explicit_path:
            path = Path(explicit_path).resolve()
            if self._validate_docs_hub(path):
                return path
            raise FileNotFoundError(f"Invalid Docs Hub path: {explicit_path}")

        # Strategy 2: Environment variable
        env_path = os.getenv("DOCS_HUB_PATH")
        if env_path:
            path = Path(env_path).resolve()
            if self._validate_docs_hub(path):
                return path

        # Strategy 3: Sibling directory auto-detection
        # Assume script is in Claire_de_Binare/scripts/discussion_pipeline/utils/
        # So Docs Hub is at ../../../../Claire_de_Binare_Docs/
        current_file = Path(__file__).resolve()
        working_repo = current_file.parents[3]  # Go up to Claire_de_Binare/
        sibling_docs = working_repo.parent / "Claire_de_Binare_Docs"

        if self._validate_docs_hub(sibling_docs):
            return sibling_docs.resolve()

        # Strategy 4: Fallback - show helpful error
        raise FileNotFoundError(
            "Could not locate Docs Hub workspace.\n\n"
            "Tried:\n"
            f"1. DOCS_HUB_PATH env var: {env_path or 'not set'}\n"
            f"2. Sibling directory: {sibling_docs} (not found)\n\n"
            "Please either:\n"
            "- Set DOCS_HUB_PATH environment variable\n"
            "- Use --docs-hub CLI argument\n"
            "- Ensure Docs Hub is at ../Claire_de_Binare_Docs relative to Working Repo"
        )

    def _validate_docs_hub(self, path: Path) -> bool:
        """
        Validate that a path is a valid Docs Hub workspace.

        Args:
            path: Path to check

        Returns:
            True if valid Docs Hub, False otherwise
        """
        if not path.exists():
            return False

        # Check for expected Docs Hub structure
        required_paths = [
            path / "config" / "pipeline_rules.yaml",
            path / "discussions",
            path / "docs"
        ]

        return all(p.exists() for p in required_paths)

    def load_config(self) -> Dict[str, Any]:
        """
        Load and parse pipeline configuration.

        Returns:
            Dict with pipeline configuration

        Raises:
            yaml.YAMLError: If configuration is invalid
        """
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Validate required sections
        required_sections = ["pipelines", "gates", "agents"]
        missing = [s for s in required_sections if s not in config]
        if missing:
            raise ValueError(
                f"Invalid pipeline configuration. Missing sections: {missing}"
            )

        return config

    def get_pipeline_preset(self, preset_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific pipeline preset.

        Args:
            preset_name: Name of preset (quick, standard, deep, etc.)

        Returns:
            Dict with preset configuration

        Raises:
            KeyError: If preset doesn't exist
        """
        config = self.load_config()
        if preset_name not in config["pipelines"]:
            available = list(config["pipelines"].keys())
            raise KeyError(
                f"Unknown preset: {preset_name}. Available: {available}"
            )

        return config["pipelines"][preset_name]

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.

        Args:
            agent_name: Name of agent (gemini, copilot, claude)

        Returns:
            Dict with agent configuration

        Raises:
            KeyError: If agent doesn't exist
        """
        config = self.load_config()
        if agent_name not in config["agents"]:
            available = list(config["agents"].keys())
            raise KeyError(
                f"Unknown agent: {agent_name}. Available: {available}"
            )

        return config["agents"][agent_name]

    def get_gate_config(self) -> Dict[str, Any]:
        """
        Get gate trigger configuration.

        Returns:
            Dict with gate configuration
        """
        config = self.load_config()
        return config["gates"]

    def get_quality_config(self) -> Dict[str, Any]:
        """
        Get quality metrics configuration.

        Returns:
            Dict with quality configuration
        """
        config = self.load_config()
        return config.get("quality", {})
