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
except ImportError:
    from base import BaseAgent, AgentOutput


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
        self.api_available = bool(api_key) and not invalid_token and Anthropic is not None
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
                metadata={"skipped": True, "reason": "missing ANTHROPIC_API_KEY"}
            )

        if not proposal.strip():
            raise ValueError("Proposal cannot be empty")

        # Build prompt based on whether this is single-agent or multi-agent
        if len(context) == 0:
            # Single-agent mode: Direct analysis
            prompt = self._build_single_agent_prompt(proposal)
            system_message = "You are a strategic technical analyst. Analyze the proposal and provide structured insights."
        else:
            # Multi-agent mode: Synthesis of previous agent outputs
            prompt = self._build_multi_agent_prompt(proposal, context)
            system_message = "You are a meta-synthesizer. Resolve conflicts, identify gaps, and provide strategic recommendations."

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=[
                    {"role": "user", "content": prompt}
                ]
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
                }
            )

        except Exception as e:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: Claude error encountered, proceeding without Claude output.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "error": str(e)}
            )

    def _build_single_agent_prompt(self, proposal: str) -> str:
        """Build prompt for single-agent mode (no previous context)."""
        return f"""# Proposal Analysis Task

Analyze the following technical proposal and provide structured insights.

## Proposal

{proposal}

## Your Task

Provide your analysis in the following format:

```markdown
---
confidence_scores:
  overall_assessment: 0.8
  feasibility: 0.7
  clarity: 0.9
---

# Executive Summary

[2-3 sentence summary]

## Key Insights

### Strengths
- ...

### Concerns
- ...

### Open Questions
- ...

## Recommendation

**Assessment:** [STRONG_YES / YES / NEUTRAL / CONCERNS / REJECT]

**Confidence:** [0.0-1.0]

**Rationale:** [Why this recommendation?]

**Next Steps:**
1. ...
```

Focus on:
- **Clarity**: Is the problem well-defined?
- **Feasibility**: Is the proposed approach realistic?
- **Gaps**: What critical questions remain?
- **Strategic fit**: Does this align with project goals?
"""

    def _build_multi_agent_prompt(self, proposal: str, context: List[str]) -> str:
        """Build prompt for multi-agent mode (synthesizing previous outputs)."""
        context_section = "\n\n---\n\n".join([
            f"## Agent {i+1} Analysis\n\n{output}"
            for i, output in enumerate(context)
        ])

        return f"""# Meta-Synthesis Task

You are synthesizing multiple AI agent perspectives on a technical proposal.

## Original Proposal

{proposal}

## Previous Agent Analyses

{context_section}

## Your Task: Meta-Synthesis

Provide a synthesis in the following format:

```markdown
---
confidence_scores:
  synthesis_quality: 0.8
  conflict_resolution: 0.7
  completeness: 0.9
---

# Meta-Synthesis

## Agent Alignment Analysis

**Where agents agree:**
- ...

**Where agents disagree:**
- 🔴 **Disagreement #1**: [Describe conflict]
  - Agent A claims: ...
  - Agent B claims: ...
  - **My adjudication**: [Who is more accurate and why]
  - **Confidence**: 0.X

## Blind Spot Detection

**What all agents missed:**
- ...

## Strategic Recommendation

**Gate Decision:** [PROCEED / REVISE / REJECT]

**Confidence:** 0.X

**Rationale:**
...

**If PROCEED:**
- Recommended next steps
- Risks to monitor

**If REVISE:**
- What additional analysis is needed
- Which agent should re-analyze

**If REJECT:**
- Why this proposal is not viable
- What would need to change
```

Critical:
- Be SPECIFIC when identifying disagreements
- Show your reasoning for adjudications
- Identify gaps that NO agent covered
- Provide actionable next steps
"""

    def _extract_confidence_scores(self, content: str) -> Dict[str, float]:
        """Extract confidence scores from YAML frontmatter."""
        frontmatter = self._extract_yaml_frontmatter(content)
        if frontmatter and "confidence_scores" in frontmatter:
            return frontmatter["confidence_scores"]
        return {}
