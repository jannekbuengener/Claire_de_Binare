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
except ImportError:
    from base import BaseAgent, AgentOutput


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
        self.temperature = config.get("temperature", 0.5)  # Lower for technical precision
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
                metadata={"skipped": True, "reason": "missing OPENAI_API_KEY"}
            )

        if not proposal.strip():
            raise ValueError("Proposal cannot be empty")

        # Build prompt with previous context
        if len(context) == 0:
            # Single-agent mode (unlikely for Copilot)
            prompt = self._build_technical_prompt(proposal)
            system_message = "You are a technical architect. Analyze implementation feasibility."
        else:
            # Multi-agent mode: Challenge previous analysis
            prompt = self._build_critical_analysis_prompt(proposal, context)
            system_message = "You are a critical technical architect. Challenge assumptions and assess real-world feasibility."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
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
                }
            )

        except Exception as e:
            return AgentOutput(
                agent_name=self.agent_name,
                content="---\nconfidence_scores:\n  availability: 0.7\n---\n\n# Agent Skipped\n\nReason: OpenAI error encountered, proceeding without Copilot output.\n",
                confidence_scores={"availability": 0.7},
                metadata={"skipped": True, "error": str(e)}
            )

    def _build_technical_prompt(self, proposal: str) -> str:
        """Build standalone technical analysis prompt."""
        return f"""# Technical Architecture Analysis

Analyze the following proposal from an implementation perspective.

## Proposal

{proposal}

## Your Task

Provide technical analysis in this format:

```markdown
---
confidence_scores:
  implementation_feasibility: 0.7
  scalability: 0.8
  maintainability: 0.9
---

# Technical Analysis

## Architecture Assessment

**Proposed approach:**
- Summary of technical approach
- Key design decisions

**Feasibility:** [HIGH/MEDIUM/LOW]
**Confidence:** 0.X

## Implementation Complexity

### Component Breakdown
1. **Component A**
   - Complexity: [LOW/MEDIUM/HIGH]
   - Time estimate: [Rough order of magnitude]
   - Dependencies: ...

### Critical Path
- What must be built first?
- What are the integration points?

## Performance & Scalability

**Expected performance characteristics:**
- Latency: ...
- Throughput: ...
- Resource usage: ...

**Scaling concerns:**
- What breaks first when load increases?
- Mitigation strategies: ...

## Technical Risks

1. **Risk:** [Technical risk]
   - **Likelihood:** [HIGH/MEDIUM/LOW]
   - **Impact:** [HIGH/MEDIUM/LOW]
   - **Mitigation**: ...

## Recommendation

**Implementation viability:** 0.X

**Critical blockers:**
- [What could prevent implementation]

**Next steps:**
1. ...
```
"""

    def _build_critical_analysis_prompt(self, proposal: str, context: List[str]) -> str:
        """Build prompt for critical evaluation of previous analysis."""
        previous_analysis = "\n\n---\n\n".join([
            f"## Previous Agent Analysis {i+1}\n\n{output}"
            for i, output in enumerate(context)
        ])

        return f"""# Critical Technical Analysis

You are reviewing a proposal AND previous agent analysis.
Your job: Challenge assumptions, find implementation gaps, assess real-world feasibility.

## Original Proposal

{proposal}

## Previous Analysis

{previous_analysis}

## Your Task: Critical Evaluation

```markdown
---
confidence_scores:
  implementation_feasibility: 0.6
  previous_analysis_accuracy: 0.7
  risk_assessment: 0.8
---

# Technical Critique

## Agreement with Previous Analysis

**Where I agree:**
- Point 1: [What previous agent got right]
- Point 2: ...

## 🔴 Disagreements

### Disagreement #1: [Topic]

**Previous claim:** [What other agent(s) said]

**My position:** [Why I disagree]

**Evidence:**
- Benchmark data: ...
- Real-world precedent: ...
- Technical constraint: ...

**Confidence in my position:** 0.X

**Resolution needed:** [What would settle this dispute]

### Disagreement #2: ...

## Implementation Reality Check

**What previous analysis overlooked:**
1. **Overlooked issue 1**
   - Why it matters: ...
   - Impact on feasibility: ...

2. ...

## Code-Level Concerns

**Design patterns applicable:**
- [Pattern 1]: Why it fits
- [Pattern 2]: Alternative approach

**Anti-patterns to avoid:**
- [Anti-pattern 1]: Why it would fail here

## Performance Analysis

**Theoretical vs. Practical:**
- Theory says: [From previous analysis]
- Reality is: [What actually happens at scale]
- Gap explanation: [Why they differ]

**Benchmarks needed:**
- Test case 1: ...
- Test case 2: ...

## Technical Debt Assessment

**If we build this:**
- Maintenance burden: [LOW/MEDIUM/HIGH]
- Refactoring likelihood: ...
- Long-term viability: ...

## Final Recommendation

**Implementation verdict:** [GO / PROTOTYPE_FIRST / RECONSIDER / NO_GO]

**Confidence:** 0.X

**Critical next steps:**
1. ...

**Blockers:**
- [What must be resolved before proceeding]
```

Critical:
- Use 🔴 markers for disagreements
- Be SPECIFIC about technical constraints
- Reference real-world data when challenging claims
- Provide concrete alternatives, not just criticism
"""
