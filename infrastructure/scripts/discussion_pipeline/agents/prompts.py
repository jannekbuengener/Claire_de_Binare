"""
Agent prompt templates for the Discussion Pipeline.

Centralized prompt definitions for all agent types.
Each agent can customize these templates with proposal and context data.
"""

from typing import List


class ClaudePrompts:
    """Prompts for Claude agent (meta-synthesis and strategic evaluation)."""

    @staticmethod
    def single_agent(proposal: str) -> str:
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

    @staticmethod
    def multi_agent(proposal: str, context: List[str]) -> str:
        """Build prompt for multi-agent mode (synthesizing previous outputs)."""
        context_section = "\n\n---\n\n".join(
            [f"## Agent {i+1} Analysis\n\n{output}" for i, output in enumerate(context)]
        )

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
- Point 1: [Specific claim all agents support]
  - Supporting agents: [Agent A, Agent B]
  - Strength of consensus: [STRONG/MODERATE/WEAK]
- Point 2: ...

**Where agents partially align:**
- [Area of partial agreement]
  - Common ground: [What they agree on]
  - Differences: [Where they diverge]

**Where agents disagree:**
- 🔴 **Disagreement #1**: [Describe conflict]
  - Agent A claims: [Specific claim with confidence score]
  - Agent B claims: [Contradictory claim with confidence score]
  - **Nature of conflict**: [Factual/Interpretation/Scope/Methodology]
  - **My adjudication**: [Who is more accurate and why]
  - **Evidence favoring position**: [Concrete reasoning]
  - **Confidence**: 0.X
  - **If wrong**: [Impact if my adjudication is incorrect]

## Quality Assessment of Agent Analyses

**Gemini (Research) Analysis:**
- Strengths: [What Gemini did well]
- Weaknesses: [What Gemini missed or got wrong]
- Confidence in their conclusions: 0.X

**Copilot (Technical) Analysis:**
- Strengths: [What Copilot did well]
- Weaknesses: [What Copilot missed or got wrong]
- Confidence in their conclusions: 0.X

**Cross-validation findings:**
- [Where one agent's claims validate another's]
- [Where one agent's evidence contradicts another's]

## Blind Spot Detection

**What all agents missed:**
1. [Critical gap 1]
   - Why it matters: [Impact on proposal]
   - How to address: [What analysis is needed]

2. [Critical gap 2]
   - ...

**Assumed but not validated:**
- [Assumption 1]: [What agents took for granted]
- [Assumption 2]: ...

**Questions no agent answered:**
1. [Unanswered critical question]
2. ...

## Synthesis of Risks

**Confirmed risks** (multiple agents identified):
- [Risk 1]: Probability: [X], Impact: [Y]
  - Mitigation: [Concrete action]

**Disputed risks** (agents disagree on severity):
- [Risk 2]: Agent A says [X], Agent B says [Y]
  - My assessment: [Resolution]

**Novel risks** (identified through synthesis):
- [Risk 3]: [Emerged from combining agent insights]

## Confidence Meta-Analysis

**Where confidence is misplaced:**
- [Agent X claimed Y with confidence Z, but evidence suggests lower confidence]

**Where uncertainty is appropriate:**
- [Areas where low confidence is justified by evidence gaps]

**Confidence in this synthesis:** 0.X
- Based on: [Quality of input analyses, agreement level, evidence strength]

## Strategic Recommendation

**Gate Decision:** [PROCEED / REVISE / REJECT]

**Confidence:** 0.X

**Rationale:**
[Detailed reasoning incorporating all agent perspectives and synthesis insights]

**Critical assumptions for this recommendation:**
1. [Assumption 1 that if false, would change recommendation]
2. [Assumption 2]

**If PROCEED:**
- **Immediate next steps:**
  1. [Action item with owner]
  2. ...
- **Risks to monitor:**
  - [Risk 1]: [Early warning signal]
  - [Risk 2]: ...
- **Success criteria:**
  - [Measurable indicator 1]
  - [Measurable indicator 2]
- **Timeline assumptions:**
  - [What must happen when]

**If REVISE:**
- **What additional analysis is needed:**
  1. [Specific research question]
  2. [Specific technical validation]
- **Which agent should re-analyze:**
  - Gemini: [Specific research to conduct]
  - Copilot: [Specific technical deep-dive]
- **What would constitute "good enough":**
  - [Criteria for proceeding after revision]

**If REJECT:**
- **Why this proposal is not viable:**
  - [Fundamental blocker 1]
  - [Fundamental blocker 2]
- **What would need to change:**
  - [Specific modification that could make it viable]
  - [Feasibility of that change]
- **Alternative approaches to consider:**
  - [Alternative 1]: [Why it might work better]

## Actionable Insights Summary

**For decision-makers:**
- [Executive summary point 1]
- [Executive summary point 2]

**For implementers:**
- [Technical insight 1]
- [Technical insight 2]

**For researchers:**
- [Research gap 1]
- [Research gap 2]
```

Critical:
- Be SPECIFIC when identifying disagreements - quote exact claims
- Show your reasoning for adjudications with evidence
- Identify gaps that NO agent covered - what's completely missing
- Assess QUALITY of each agent's analysis, not just content
- Provide actionable next steps with owners and criteria
- For each disagreement, state impact if your adjudication is wrong
- Cross-validate claims between agents - do they support or contradict?
- Identify novel risks that emerge from synthesis
- State critical assumptions underlying your recommendation
- Provide specific success criteria and early warning signals
"""

    @staticmethod
    def system_message_single() -> str:
        """System message for single-agent mode."""
        return "You are a strategic technical analyst. Analyze the proposal and provide structured insights."

    @staticmethod
    def system_message_multi() -> str:
        """System message for multi-agent mode."""
        return "You are a meta-synthesizer. Resolve conflicts, identify gaps, and provide strategic recommendations."


class GeminiPrompts:
    """Prompts for Gemini agent (research synthesis and fact extraction)."""

    @staticmethod
    def research_synthesis(proposal: str) -> str:
        """Build research synthesis prompt for Gemini."""
        return f"""# Research Synthesis Task

You are a research analyst specializing in technical knowledge extraction and synthesis.

## Proposal to Analyze

{proposal}

## Your Task: Comprehensive Research Synthesis

Provide your analysis in the following format:

```markdown
---
confidence_scores:
  research_quality: 0.8
  evidence_strength: 0.7
  theoretical_soundness: 0.9
---

# Research Synthesis

## Theoretical Frameworks Identified

**Primary Framework:**
- Name: [Framework name]
- Core principles: ...
- Applicability to this proposal: ...
- Known limitations: [Where this framework breaks down]
- **Confidence**: 0.X

**Alternative Frameworks:**
- [Framework 2]: [Why it might be better/worse]
- [Framework 3]: [Comparative advantage]

**Framework Selection Rationale:**
- Why primary framework was chosen
- Trade-offs compared to alternatives
- Context where alternatives would be superior

## Evidence Base

### Supporting Evidence
1. **Claim**: [What the proposal claims]
   - **Evidence**: [Supporting data/research/precedent]
   - **Source**: [Specific citation or reference]
   - **Source confidence**: [HIGH/MEDIUM/LOW] - [Why this confidence level]
   - **Strength**: 0.X
   - **Caveats**: [What limits this evidence's applicability]

2. ...

### Contradictory Evidence
1. **Counter-evidence**: [Data that contradicts proposal claims]
   - **Source**: ...
   - **Impact**: [How this affects viability]
   - **Resolution**: [How to reconcile this contradiction]

### Gaps in Evidence
- **Missing data point 1**: [What's claimed but not proven]
  - **Impact if wrong**: [What fails if assumption is false]
  - **How to validate**: [Specific test or measurement needed]
- **Missing data point 2**: ...

## Research Gaps & Open Questions

1. **Question**: [Critical unanswered question]
   - **Why critical**: [Concrete impact on proposal viability]
   - **How to answer**: [Specific research approach with timeline]
   - **Workaround if unanswerable**: [Alternative approach]

2. ...

## Literature Review Summary

**Relevant prior work:**
- [Paper/Project 1]: Key findings... | Relevance: [How it applies]
- [Paper/Project 2]: Key findings... | Divergence: [Where it differs]

**What's novel in this proposal:**
- Novel contribution 1: [Why this hasn't been done before]
- Novel contribution 2: ...

**What's derivative:**
- [Clearly state what's adapted from existing work]

## Risk Assessment from Research Perspective

**Theoretical risks:**
- [Risk 1]: Why this framework might not apply
  - **Probability**: [HIGH/MEDIUM/LOW]
  - **Early warning signs**: [What to monitor]
- [Risk 2]: ...

**Empirical risks:**
- [Risk 1]: What real-world data suggests
  - **Historical precedents**: [Cases where similar approaches failed]
  - **Mitigation**: [What can be done]
- [Risk 2]: ...

**Unknown unknowns:**
- [Areas where we lack research entirely]
- [Why these matter]

## Recommendation

**Research Maturity:** [EARLY_STAGE / ESTABLISHED / PROVEN]

**Confidence in viability:** 0.X

**Critical validation needed:**
1. [Experiment/measurement required]
2. [Data collection needed]

**Critical next steps:**
1. ...
2. ...

**Red flags to watch:**
- [Signals that would invalidate this approach]
```

Guidelines:
- Be SPECIFIC about theoretical frameworks (name them explicitly)
- Distinguish CLAIMS from EVIDENCE rigorously
- Include CONTRADICTORY evidence - don't cherry-pick
- Identify gaps ruthlessly - what's assumed but not proven?
- Reference concrete prior work with specific citations
- Provide confidence scores WITH justification
- Focus on RESEARCH perspective, not implementation
- State what's novel vs. derivative clearly
- Identify framework limitations and selection rationale
- Call out unknown unknowns - areas lacking research
- For each gap, explain impact if assumption is wrong
"""


class CopilotPrompts:
    """Prompts for Copilot agent (technical architecture and implementation analysis)."""

    @staticmethod
    def technical_analysis(proposal: str) -> str:
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
- Design pattern(s) identified: [Name specific patterns]

**Architecture style:** [Monolithic/Microservices/Serverless/Event-driven/etc.]

**Feasibility:** [HIGH/MEDIUM/LOW]
**Confidence:** 0.X
**Rationale:** [Why this confidence level]

**Similar implementations:**
- [System 1]: [How it compares]
- [System 2]: [Key differences]

## Implementation Complexity

### Component Breakdown
1. **Component A**
   - Complexity: [LOW/MEDIUM/HIGH] - [Why]
   - Time estimate: [Rough order of magnitude]
   - Dependencies: [Internal and external]
   - Risk factors: [What could go wrong]
   - Testing complexity: [LOW/MEDIUM/HIGH]

2. ...

### Critical Path Analysis
- **Must build first:** [Component X] because [dependency reason]
- **Can parallelize:** [Components Y, Z]
- **Integration points:** [Where components connect]
- **Integration risks:** [What could fail during integration]

### Hidden Complexity
- [Subtle technical challenge 1]: [Why it's harder than it looks]
- [Subtle technical challenge 2]: ...

## Performance & Scalability

**Expected performance characteristics:**
- Latency: [X ms at Y percentile]
- Throughput: [N requests/second]
- Resource usage: [CPU/Memory/Network/Disk]

**Bottleneck analysis:**
- **First bottleneck:** [Component/operation that limits scale]
- **Second bottleneck:** [After first is resolved]
- **Scaling strategy:** [Horizontal/Vertical/Hybrid]

**Scaling concerns:**
- What breaks first when load increases? [Specific component]
- At what load does it break? [Quantitative threshold]
- Mitigation strategies: [Concrete approaches]

**Performance testing needed:**
1. [Specific benchmark to run]
2. [Load test scenario]

## Technical Risks

1. **Risk:** [Technical risk]
   - **Likelihood:** [HIGH/MEDIUM/LOW]
   - **Impact:** [HIGH/MEDIUM/LOW]
   - **Severity:** [CRITICAL/HIGH/MEDIUM/LOW]
   - **Detection:** [How will we know if it happens]
   - **Mitigation**: [Preventive measure]
   - **Fallback**: [What to do if mitigation fails]

2. ...

## Operational Considerations

**Deployment complexity:** [LOW/MEDIUM/HIGH]
- Deployment steps: [Number of manual steps]
- Rollback safety: [How easy to undo]

**Monitoring requirements:**
- Key metrics to track: [Specific metrics]
- Alert conditions: [When to page humans]

**Maintenance burden:**
- Ongoing work required: [What needs regular attention]
- Tribal knowledge risk: [What requires domain expertise]

## Technology Stack Assessment

**Proposed technologies:**
- [Tech 1]: [Maturity, community support, team familiarity]
- [Tech 2]: ...

**Technology risks:**
- [Risk 1]: [Version compatibility, licensing, longevity]
- [Risk 2]: ...

**Alternative stack:**
- [Alternative approach]: [Trade-offs vs. proposed]

## Security Considerations

**Attack surface:**
- [Exposed endpoints/interfaces]

**Security controls needed:**
- [Authentication/Authorization/Encryption/etc.]

**Compliance requirements:**
- [Regulatory considerations]

## Recommendation

**Implementation viability:** 0.X

**Effort estimate:** [S/M/L/XL] - [Rationale]

**Team capability requirement:** [Junior/Mid/Senior/Expert]

**Critical blockers:**
- [What could prevent implementation]
- [How to resolve each blocker]

**Proof of concept needed:**
- [What to validate first]
- [Success criteria for POC]

**Next steps:**
1. [Immediate action]
2. [Follow-up action]

**Decision points:**
- [Key choices that need to be made before proceeding]
```
"""

    @staticmethod
    def critical_analysis(proposal: str, context: List[str]) -> str:
        """Build prompt for critical evaluation of previous analysis."""
        previous_analysis = "\n\n---\n\n".join(
            [
                f"## Previous Agent Analysis {i+1}\n\n{output}"
                for i, output in enumerate(context)
            ]
        )

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

    @staticmethod
    def system_message_single() -> str:
        """System message for single-agent mode."""
        return "You are a technical architect. Analyze implementation feasibility."

    @staticmethod
    def system_message_multi() -> str:
        """System message for multi-agent mode."""
        return "You are a critical technical architect. Challenge assumptions and assess real-world feasibility."
