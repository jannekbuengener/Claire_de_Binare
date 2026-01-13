"""
Gemini Agent - Research synthesis and fact extraction.

Uses Google's Gemini API for comprehensive research analysis,
theoretical framework identification, and evidence extraction.
"""

import os
from typing import List, Dict, Any

try:
    import google.generativeai as genai  # type: ignore
except ImportError:
    genai = None
try:
    from .base import BaseAgent, AgentOutput
    from .prompts import GeminiPrompts
except ImportError:
    from base import BaseAgent, AgentOutput
    from prompts import GeminiPrompts


class GeminiAgent(BaseAgent):
    """
    Gemini agent specializes in:
    - Research synthesis from technical documents
    - Theoretical framework identification
    - Evidence extraction and gap analysis
    - Literature review and fact-checking
    - Open question formulation
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini agent with API configuration."""
        super().__init__(config)

        api_key = os.getenv("GOOGLE_API_KEY")
        invalid_token = api_key and api_key.strip().startswith("#")
        self.api_available = bool(api_key) and not invalid_token and genai is not None
        self.model_name = config.get("model", "gemini-pro")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4000)

        if not self.api_available:
            self.model = None
            return

        genai.configure(api_key=api_key)
        self.model_name = config.get("model", "gemini-pro")
        self.model = genai.GenerativeModel(self.model_name)

    def analyze(self, proposal: str, context: List[str]) -> AgentOutput:
        """
        Analyze proposal with Gemini API.

        Args:
            proposal: Original proposal markdown
            context: Previous agent outputs (should be empty for Gemini - it goes first)

        Returns:
            AgentOutput with Gemini's research synthesis
        """
        if not self.api_available:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: Missing GOOGLE_API_KEY. Proceeded in availability-only mode.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "reason": "missing GOOGLE_API_KEY"},
            )

        if not proposal.strip():
            raise ValueError("Proposal cannot be empty")

        prompt = GeminiPrompts.research_synthesis(proposal)

        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            content = response.text

            # Extract confidence scores from frontmatter
            confidence_scores = self._extract_confidence_scores(content)

            return AgentOutput(
                agent_name=self.agent_name,
                content=content,
                confidence_scores=confidence_scores,
                metadata={
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "prompt_token_count": (
                        response.usage_metadata.prompt_token_count
                        if hasattr(response, "usage_metadata")
                        else None
                    ),
                    "candidates_token_count": (
                        response.usage_metadata.candidates_token_count
                        if hasattr(response, "usage_metadata")
                        else None
                    ),
                },
            )

        except Exception as e:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: Gemini error encountered, proceeding without Gemini output.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "error": str(e)},
            )
