# WORKFLOW_Risk_Mode_Change

Reference: ../AGENTS.md

Goal: Safely plan, validate, and execute operating-mode or limit changes (e.g., paper -> live, limit adjustments).

Roles involved: [Orchestrator](../roles/ORCHESTRATOR_Codex.md), [System Architect](../roles/AGENT_System_Architect.md) (architecture impact), [Canonical Governance Officer](../roles/AGENT_Canonical_Governance.md) (governance/audit/readiness), [Risk Architect](../roles/AGENT_Risk_Architect.md), [DevOps Engineer](../roles/AGENT_DevOps_Engineer.md), [Test & Simulation Engineer](../roles/AGENT_Test_Engineer.md), [Code Reviewer](../roles/AGENT_Code_Reviewer.md), [Documentation Engineer](../roles/AGENT_Documentation_Engineer.md). Optional intelligence support: [Gemini Research Analyst](../roles/AGENT_Gemini_Research_Analyst.md), [Gemini Data Miner](../roles/AGENT_Gemini_Data_Miner.md), [Gemini Sentiment Scanner](../roles/AGENT_Gemini_Sentiment_Scanner.md) for external market/risk signals.

Phases:
- Analysis (no changes):
  1. Orchestrator documents request (target mode, reason, duration, success criteria, rollback).
  2. System Architect (if needed) assesses architecture or service-boundary impact.
  3. Risk Architect evaluates exposure; defines needed limits/flags/monitoring; sets stop criteria and observations.
  4. DevOps Engineer checks switches (feature flags, config, secrets, deployment guardrails).
  5. Code Reviewer lists risky code paths; Test & Simulation Engineer plans risk-specific tests/probes.
  6. Orchestrator drafts decision note with approval conditions; get user go.
- Delivery (changes allowed):
  1. Risk Architect grants green light for concrete steps; Orchestrator sequences execution.
  2. DevOps Engineer applies config/flag/deployment changes with rollback path; Test & Simulation Engineer runs checks/smokes/probes.
  3. Orchestrator monitors metrics vs stop criteria; trigger immediate rollback if needed.
  4. Documentation Engineer updates ops and incident runbooks; Risk Architect records risk log.

Outputs:
- Approval doc with conditions, active limits/flags, and monitors.
- Evidence of tests/probes and any rollback performed.
- Updated ops docs, including return path and owners.
