"""
Claude Agent - Meta-synthesis and strategic evaluation.

Uses Anthropic's Claude API for high-level strategic analysis,
conflict resolution, and recommendation generation.
"""

import os
from typing import List, Dict, Any

try:
    from anthropic import Anthropic  # type: ignore
except ImportError:
    Anthropic = None
try:
    from .base import BaseAgent, AgentOutput
    from .prompts import ClaudePrompts
except ImportError:
    from base import BaseAgent, AgentOutput
    from prompts import ClaudePrompts


class ClaudeAgent(BaseAgent):
    """
    Claude agent specializes in:
    - Meta-synthesis across multiple perspectives
    - Conflict resolution between agents
    - Gap analysis (what other agents missed)
    - Gate recommendations (PROCEED/REVISE/REJECT)
    - Strategic framing and decision support
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Claude agent with API configuration."""
        super().__init__(config)

        api_key = os.getenv("ANTHROPIC_API_KEY")
        invalid_token = api_key and api_key.strip().startswith("#")
        self.api_available = (
            bool(api_key) and not invalid_token and Anthropic is not None
        )
        self.client = Anthropic(api_key=api_key) if self.api_available else None
        self.model = config.get("model", "claude-sonnet-4-5-20250929")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4000)

    def analyze(self, proposal: str, context: List[str]) -> AgentOutput:
        """
        Analyze proposal with Claude API.

        Args:
            proposal: Original proposal markdown
            context: Previous agent outputs (empty for single-agent mode)

        Returns:
            AgentOutput with Claude's analysis
        """
        if not self.api_available:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: Missing ANTHROPIC_API_KEY. Proceeded in availability-only mode.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "reason": "missing ANTHROPIC_API_KEY"},
            )

        if not proposal.strip():
            raise ValueError("Proposal cannot be empty")

        # Build prompt based on whether this is single-agent or multi-agent
        if len(context) == 0:
            # Single-agent mode: Direct analysis
            prompt = ClaudePrompts.single_agent(proposal)
            system_message = ClaudePrompts.system_message_single()
        else:
            # Multi-agent mode: Synthesis of previous agent outputs
            prompt = ClaudePrompts.multi_agent(proposal, context)
            system_message = ClaudePrompts.system_message_multi()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text

            # Extract confidence scores from frontmatter
            confidence_scores = self._extract_confidence_scores(content)

            return AgentOutput(
                agent_name=self.agent_name,
                content=content,
                confidence_scores=confidence_scores,
                metadata={
                    "model": self.model,
                    "temperature": self.temperature,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )

        except Exception as e:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: Claude error encountered, proceeding without Claude output.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "error": str(e)},
            )

    def _extract_confidence_scores(self, content: str) -> Dict[str, float]:
        """Extract confidence scores from YAML frontmatter."""
        frontmatter = self._extract_yaml_frontmatter(content)
        if frontmatter and "confidence_scores" in frontmatter:
            return frontmatter["confidence_scores"]
        return {}
