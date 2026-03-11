# Multi-LLM Discussion Pipeline: Technical Design Document

**Status**: Design / Prototype Specification
**Created**: 2025-12-17
**Author**: Claude (Sonnet 4.5) in collaboration with Human
**Purpose**: Technical specification for multi-agent AI discussion system

---

## Executive Summary

This document specifies a **file-based, multi-LLM orchestration system** that enables:

1. **Critical multi-perspective analysis** of technical proposals
2. **Explicit conflict detection** between AI agents
3. **Human-in-the-loop gates** for strategic decisions
4. **Traceable knowledge synthesis** from research to GitHub issues

**Key Innovation**: Unlike typical multi-agent systems that aim for consensus, this pipeline **actively encourages disagreement** to prevent echo chambers and surface hidden assumptions.

---

## System Architecture

### High-Level Flow

```
Knowledge Base (Markdown)
    ↓
[Gemini Agent] → Research synthesis, fact extraction
    ↓
[Copilot Agent] → Technical critique, implementation analysis
    ↓
[Claude Agent] → Meta-synthesis, conflict resolution
    ↓
[Human Gate] → Strategic decision
    ↓
GitHub Issue (if approved)
```

### File-Based Orchestration

**Why file-based?**
- ✅ Git-trackable: Full audit trail
- ✅ Pausable: Human can intervene at any point
- ✅ Debuggable: Inspect intermediate states
- ✅ LLM-agnostic: Easy to swap/add agents

**Directory Structure:**
```
discussions/
├── proposals/           # INPUT: Research findings, open questions
├── threads/            # PROCESS: Active discussions
│   └── THREAD_<id>/
│       ├── manifest.json
│       ├── 01_gemini_output.md
│       ├── 02_copilot_output.md
│       ├── 03_claude_output.md
│       └── DIGEST.md
├── gates/              # DECISION: Human review points
└── issues/             # OUTPUT: GitHub-ready specifications
```

---

## Agent Specializations

### 1. Gemini Agent: Research Analyst

**Core Competency**: Fact synthesis, literature review, theoretical frameworks

**Prompt Structure**:
```markdown
You are a research analyst in a multi-agent pipeline.

Your task:
1. Extract factual claims from the proposal
2. Identify theoretical frameworks mentioned
3. Find gaps in current evidence
4. **Highlight points where other agents might disagree**

CRITICAL: Use "## Disagreement Potential" to flag debatable claims.
```

**Output Template**:
```markdown
---
agent: gemini
confidence_scores:
  factual_accuracy: 0.85
  completeness: 0.60
---

# Research Analysis

## Key Findings
1. [Evidence-based claim]

## Open Questions
- [ ] Empirical gap 1

## Disagreement Potential
- Claim X lacks benchmarking data
```

### 2. Copilot Agent: Technical Architect

**Core Competency**: Implementation feasibility, performance analysis, code-level reasoning

**Prompt Structure**:
```markdown
Previous agent (Gemini) claimed: "[QUOTE]"

Your task:
1. Evaluate architectural implications
2. **CRITICALLY CHALLENGE** Gemini's claims if technically infeasible
3. Provide code-level proof/disproof

DO NOT simply rephrase. Your value is TECHNICAL CRITIQUE.
```

**Output Template**:
```markdown
---
agent: copilot
---

# Technical Analysis

## Architectural Implications
[Implementation details]

## 🔴 Disagreement with Gemini
**Gemini's Claim**: "[Quote]"
**My Position**: Disagree. [Evidence: benchmarks, code]
**Resolution Needed**: @human: [Specific experiment]
```

### 3. Claude Agent: Meta-Synthesizer

**Core Competency**: Conflict resolution, strategic evaluation, gap detection

**Prompt Structure**:
```markdown
You are the final arbiter in a multi-agent discussion.

Previous agents disagree on: [CONFLICT]

Your tasks:
1. **Conflict Adjudication**: Who is right and WHY?
2. **Blind Spot Detection**: What did BOTH agents miss?
3. **Gate Recommendation**: PROCEED / REVISE / REJECT

Focus on what humans need to decide, not just technical synthesis.
```

**Output Template**:
```markdown
---
agent: claude
---

# Meta-Synthesis

## Conflict Resolution Table
| Claim | Gemini | Copilot | Adjudication | Confidence |
|-------|--------|---------|--------------|------------|
| [Topic] | ✓ | ✗ | Copilot correct: [reason] | 0.75 |

## Blind Spots
- Organizational: Team lacks BSDE expertise
- Long-term: Maintenance burden underestimated

## Gate Recommendation
- [x] 🔄 REVISE (Missing: empirical benchmark)
```

---

## Orchestration Logic

### Pipeline Selection (Dynamic)

```yaml
pipelines:
  quick:        [claude]                    # Simple topics
  standard:     [gemini, claude]            # Medium complexity
  technical:    [copilot, claude]           # Implementation-focused
  deep:         [gemini, copilot, claude]   # High complexity
  iterative:    [gemini, claude, gemini, claude]  # Research-heavy
```

**Selection Rules**:
```python
if complexity == "high" or "mathematical_modeling" in tags:
    return "deep"
elif "architecture_decision" in tags:
    return "technical"
else:
    return "standard"
```

### Human Gate Triggers

Pipeline pauses automatically if:

1. **Low confidence**: Any agent scores < 0.5
2. **High conflict**: Disagreement count > 2
3. **Strategic keywords**: "breaking change", "migration", "deprecation"
4. **Explicit flag**: `HUMAN_REVIEW_REQUIRED` in output

**Gate Process**:
1. System creates `discussions/gates/GATE_<id>.md`
2. Human reviews and marks decision:
   - ✅ PROCEED → Create GitHub Issue
   - 🔄 REVISE → Specify missing analysis
   - ❌ REJECT → Archive with rationale
3. System resumes or terminates based on decision

---

## Quality Assurance

### Echo Chamber Detection

```python
def validate_discussion_quality(thread_dir):
    metrics = {
        "disagreement_count": count_disagreements(),
        "echo_chamber_score": measure_similarity()  # 0.0 = diverse, 1.0 = repetitive
    }

    if disagreement_count == 0 and num_agents > 1:
        warn("Suspicious: No disagreements in multi-agent discussion")

    if echo_chamber_score > 0.7:
        warn("High similarity - agents may not be critically engaging")
```

### Confidence Calibration

Each agent provides:
```yaml
confidence_scores:
  factual_accuracy: 0.85    # How sure about facts
  completeness: 0.60        # How much is covered
  novelty: 0.40             # How original is the insight
```

**Usage**:
- Low confidence triggers human review
- Confidence < 0.5 on critical claims → automatic gate
- Aggregate scores inform final recommendation

---

## Implementation Pseudocode

### Orchestrator Core

```python
class DiscussionOrchestrator:
    def run_pipeline(self):
        pipeline = ["gemini", "copilot", "claude"]
        context = [proposal_file]

        for agent_name in pipeline:
            # Execute agent
            output = self.run_agent(agent_name, context)
            context.append(output)

            # Check for gates
            if self.should_pause(output):
                self.create_gate()
                return  # Pause for human review

        self.generate_digest()

    def run_agent(self, agent_name, context):
        prompt = self.build_prompt(agent_name, context)
        response = agent.analyze(prompt)
        return response

    def should_pause(self, output):
        # Parse confidence scores
        if extract_confidence(output) < 0.5:
            return True

        # Check for conflicts
        if output.count("🔴 Disagreement") > 2:
            return True

        return False
```

### Agent Interface

```python
class BaseAgent:
    def analyze(self, prompt: str) -> str:
        """
        Args:
            prompt: Full context + instructions

        Returns:
            Structured markdown with:
            - Executive summary
            - Key findings
            - Disagreements (if any)
            - Confidence scores
            - References for next agent
        """
        response = self.call_llm_api(prompt)
        return response
```

---

## Example: Full Discussion Flow

### Input: Proposal
```markdown
# BSDE vs. Stochastic Control

Should we use BSDE or HJB methods for our risk modeling?

## Context
- Current system: NumPy-based forward simulation
- Target: d=50 dimensional problem
- Team: 3 quants, no BSDE expertise
```

### Step 1: Gemini Output
```markdown
## Key Findings
1. BSDE and control are theoretically equivalent
2. BSDE handles non-Markovian cases better

## Disagreement Potential
- "Better" needs quantification - what's the computational cost?
```

### Step 2: Copilot Output
```markdown
## 🔴 Disagreement with Gemini

**Gemini's Claim**: "BSDE handles non-Markovian cases better"

**My Position**: Technically true, but misleading.

**Evidence**:
- BSDE solver: O(n²) memory, 15x slower
- Team has no BSDE expertise → 6-month learning curve

**Resolution**: @human Do we have path-dependent problems that justify this cost?
```

### Step 3: Claude Synthesis
```markdown
## Conflict Resolution

**Adjudication**: Both correct in their domains.
- Gemini: Theoretically sound
- Copilot: Practically sound

**Critical Gap Both Missed**: No discussion of hybrid approaches.

## Gate Recommendation
🔄 REVISE

**Missing**:
1. Empirical benchmark on representative problem
2. Hybrid approach exploration (BSDE for select components)
3. Team training plan or external consultant budget
```

### Step 4: Human Gate Decision
```markdown
Decision: 🔄 REVISE

Additional analysis needed:
- Run prototype with d=10 problem
- Benchmark both methods
- Explore selective BSDE (only for path-dependent components)

Timeline: 2 weeks
```

---

## Advanced Features

### 1. Adaptive Pipeline Extension

If during discussion, gaps emerge:

```python
def should_extend(thread):
    latest_output = read_latest_output()

    # Many open questions → add research pass
    if latest_output.count("## Open Questions") > 5:
        return AgentType.GEMINI

    # Implementation unclear → add technical pass
    if "implementation" in latest_output and code_examples < 2:
        return AgentType.COPILOT
```

### 2. Asynchronous Human Input

```markdown
# HUMAN_INPUT_REQUEST.md (auto-generated)

## Context
Agents disagree on BSDE computational cost.

## Question
Do we have representative path-dependent pricing problems
where BSDE's advantage justifies 15x slowdown?

## Your Answer
[Type here and save → pipeline auto-resumes]
```

### 3. Quality Metrics Dashboard

```
Discussion Quality Report
═══════════════════════════════════════════
✓ Disagreements found: 2 (healthy debate)
✓ Echo chamber score: 0.35 (diverse perspectives)
⚠ Avg confidence: 0.58 (moderate uncertainty)
→ Recommendation: Human review suggested
```

---

## Deployment Considerations

### Minimal Setup

```bash
# 1. Install dependencies
pip install anthropic google-generativeai openai pyyaml

# 2. Configure API keys
export ANTHROPIC_API_KEY="..."
export GOOGLE_API_KEY="..."

# 3. Run discussion
python scripts/run_discussion.py proposals/PROPOSAL_001.md
```

### Production Considerations

**Secrets Management**:
- Never commit `.env` files
- Use secret management service (AWS Secrets Manager, etc.)

**Rate Limiting**:
- Implement backoff for API calls
- Queue discussions to avoid quota exhaustion

**Monitoring**:
- Log all API calls with tokens used
- Track discussion completion rate
- Alert on stuck threads (> 24h without progress)

**Cost Control**:
```python
COST_LIMITS = {
    "per_discussion": 5.00,  # USD
    "daily_total": 100.00
}
```

---

## Success Metrics

### Discussion Quality
- **Disagreement rate**: 20-40% (healthy critical engagement)
- **Echo chamber score**: < 0.5
- **Average confidence**: 0.65-0.85 (not overconfident)

### Outcomes
- **Gate approval rate**: 40-60% (not too easy, not impossible)
- **Revision cycles**: 1-2 average
- **Issue quality**: Measured by downstream eng satisfaction

### Process
- **Time to decision**: < 48h (including human review)
- **Human time investment**: < 30 min per discussion
- **Cost per discussion**: < $3 USD

---

## Open Questions & Future Work

1. **Multi-Round Debates**: Should agents be allowed to respond to each other's critiques iteratively?

2. **Specialized Domain Agents**: Add agents for:
   - **Legal/Compliance** review
   - **Security** analysis
   - **UX/Product** perspective

3. **Automated Benchmarking**: Can we auto-generate code benchmarks when agents disagree on performance?

4. **Learning from History**: Train meta-model on past discussions to improve prompt engineering

5. **Integration with Existing Tools**:
   - Linear/Jira for issue creation
   - Slack for notifications
   - Notion for knowledge base

---

## Related Documents

- [Pipeline Configuration](../../config/pipeline_rules.yaml)
- [Agent Protocol Specification](../agents/protocol.md) (TBD)
- [Evaluation Metrics](../evaluation/metrics.md) (TBD)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Review Cycle**: Quarterly or on major architecture changes
