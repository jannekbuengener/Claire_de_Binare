"""
Base agent interface for the Discussion Pipeline.

All agent implementations must inherit from BaseAgent and implement
the analyze() method.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class AgentOutput:
    """
    Standardized output format for all agents.

    Attributes:
        agent_name: Name of the agent (gemini, copilot, claude)
        content: Full markdown output with YAML frontmatter
        confidence_scores: Dict of metric -> score (0.0-1.0)
        timestamp: ISO 8601 timestamp
        metadata: Additional agent-specific data
    """

    agent_name: str
    content: str
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent": self.agent_name,
            "content_preview": (
                self.content[:200] + "..." if len(self.content) > 200 else self.content
            ),
            "confidence_scores": self.confidence_scores,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all pipeline agents.

    Each agent receives:
    - The original proposal text
    - Context from previous agents in the pipeline

    And produces:
    - Markdown analysis with YAML frontmatter
    - Confidence scores for key claims
    - Metadata for quality assessment
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agent with configuration.

        Args:
            config: Agent configuration from pipeline_rules.yaml
        """
        self.config = config
        self.agent_name = self.__class__.__name__.replace("Agent", "").lower()

    @abstractmethod
    def analyze(self, proposal: str, context: List[str]) -> AgentOutput:
        """
        Analyze the proposal and produce structured output.

        Args:
            proposal: The original proposal markdown text
            context: List of previous agent outputs (for multi-agent pipelines)

        Returns:
            AgentOutput with analysis, scores, and metadata

        Raises:
            ValueError: If proposal is empty or invalid
            RuntimeError: If API call fails
        """
        pass

    def _extract_yaml_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract YAML frontmatter from markdown content.

        Args:
            content: Markdown with optional YAML frontmatter

        Returns:
            Dict of frontmatter data, or None if not present
        """
        if not content.startswith("---"):
            return None

        try:
            end_marker = content.find("---", 3)
            if end_marker == -1:
                return None

            import yaml

            frontmatter = content[3:end_marker].strip()
            return yaml.safe_load(frontmatter)
        except Exception:
            return None

    def _build_prompt(self, proposal: str, context: List[str]) -> str:
        """
        Build agent-specific prompt with proposal and context.

        Args:
            proposal: Original proposal
            context: Previous agent outputs

        Returns:
            Formatted prompt string
        """
        # Prompts are built inline in each agent for now
        # TODO: Extract to prompts.py in Phase 2
        return f"Proposal:\n{proposal}\n\nContext:\n" + "\n".join(context)
