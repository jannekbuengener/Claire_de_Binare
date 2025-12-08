# WORKFLOW_Feature_Implementation

Reference: ../AGENTS.md

Goal: Design and implement a new function safely without live risk.

Roles involved: [Orchestrator](../roles/ORCHESTRATOR_Codex.md), [System Architect](../roles/AGENT_System_Architect.md), [Canonical Governance Officer](../roles/AGENT_Canonical_Governance.md), [Risk Architect](../roles/AGENT_Risk_Architect.md), [Data Architect](../roles/AGENT_Data_Architect.md) (if data changes), [Code Reviewer](../roles/AGENT_Code_Reviewer.md), [Test & Simulation Engineer](../roles/AGENT_Test_Engineer.md), [Refactoring Engineer](../roles/AGENT_Refactoring_Engineer.md), [DevOps Engineer](../roles/AGENT_DevOps_Engineer.md), [Repository Auditor](../roles/AGENT_Repository_Auditor.md) (structure), [Documentation Engineer](../roles/AGENT_Documentation_Engineer.md). Optional intelligence support: [Gemini Research Analyst](../roles/AGENT_Gemini_Research_Analyst.md), [Gemini Data Miner](../roles/AGENT_Gemini_Data_Miner.md), [Gemini Sentiment Scanner](../roles/AGENT_Gemini_Sentiment_Scanner.md).

Phases:
- Analysis (no changes):
  1. Orchestrator: intake with Task Brief, capture goals/scope/KPIs, confirm this workflow.
  2. System Architect: assess design options, service boundaries, event/bus impacts.
  3. Risk Architect: impact analysis; define needed limits/flags/telemetry.
  4. Data Architect (if needed): propose schema/migration/data impacts.
  5. Code Reviewer: identify hotspots and tech debt.
  6. Test & Simulation Engineer: propose test plan, coverage targets, simulations/backtests if applicable.
  7. Repository Auditor (if structural moves): flag layout/naming changes.
  8. Orchestrator: consolidate decision note with options, effort, risks; get user go.
- Delivery (changes allowed):
  1. Orchestrator starts delivery, sets branch/work area.
  2. System Architect validates structural choices during implementation.
  3. Refactoring Engineer implements feature/refactors per plan; Code Reviewer shadows.
  4. Data Architect executes migrations/schema changes (if any) with rollback plan.
  5. Test & Simulation Engineer implements/updates tests and simulations; DevOps Engineer updates CI/CD and feature-flag/rollout plan.
  6. Risk Architect checks limits/flags and monitoring are active.
  7. Repository Auditor applies approved structure/naming adjustments if needed.
  8. Documentation Engineer updates user docs and changelog text.
  9. Orchestrator runs reviews, checks CI, issues final report.

Outputs:
- Analysis reports per role; consolidated decision and implementation plan.
- Implemented feature with tests, green CI, documented rollout strategy.
- Updated documentation and approval status.
