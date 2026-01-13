"""
Copilot Agent - Technical architecture and implementation analysis.

Uses OpenAI GPT-4 as fallback for GitHub Copilot-style technical analysis.
Focuses on implementation feasibility, code-level reasoning, and critical evaluation.
"""

import os
from typing import List, Dict, Any

try:
    from openai import OpenAI  # type: ignore
except ImportError:
    OpenAI = None
try:
    from .base import BaseAgent, AgentOutput
    from .prompts import CopilotPrompts
except ImportError:
    from base import BaseAgent, AgentOutput
    from prompts import CopilotPrompts


class CopilotAgent(BaseAgent):
    """
    Copilot agent specializes in:
    - Technical architecture analysis
    - Implementation feasibility assessment
    - Code-level reasoning and design patterns
    - Performance and scalability analysis
    - CRITICAL evaluation of other agents' claims
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Copilot agent with API configuration."""
        super().__init__(config)

        api_key = os.getenv("OPENAI_API_KEY")
        invalid_token = api_key and api_key.strip().startswith("#")
        self.api_available = bool(api_key) and not invalid_token and OpenAI is not None
        self.client = OpenAI(api_key=api_key) if self.api_available else None
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get(
            "temperature", 0.5
        )  # Lower for technical precision
        self.max_tokens = config.get("max_tokens", 4000)

    def analyze(self, proposal: str, context: List[str]) -> AgentOutput:
        """
        Analyze proposal with GPT-4 (Copilot fallback).

        Args:
            proposal: Original proposal markdown
            context: Previous agent outputs (typically Gemini's analysis)

        Returns:
            AgentOutput with technical analysis
        """
        if not self.api_available:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: Missing OPENAI_API_KEY. Proceeded in availability-only mode.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "reason": "missing OPENAI_API_KEY"},
            )

        if not proposal.strip():
            raise ValueError("Proposal cannot be empty")

        # Build prompt with previous context
        if len(context) == 0:
            # Single-agent mode (unlikely for Copilot)
            prompt = CopilotPrompts.technical_analysis(proposal)
            system_message = CopilotPrompts.system_message_single()
        else:
            # Multi-agent mode: Challenge previous analysis
            prompt = CopilotPrompts.critical_analysis(proposal, context)
            system_message = CopilotPrompts.system_message_multi()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content

            # Extract confidence scores from frontmatter
            confidence_scores = self._extract_confidence_scores(content)

            return AgentOutput(
                agent_name=self.agent_name,
                content=content,
                confidence_scores=confidence_scores,
                metadata={
                    "model": self.model,
                    "temperature": self.temperature,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )

        except Exception as e:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: OpenAI error encountered, proceeding without Copilot output.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "error": str(e)},
            )
