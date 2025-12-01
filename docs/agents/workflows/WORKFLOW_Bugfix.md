# WORKFLOW_Bugfix

Reference: ../AGENTS.md

Goal: Reproduce the bug, find root cause, fix safely, and prevent regression.

Roles involved: [Orchestrator](../roles/ORCHESTRATOR_Codex.md), [System Architect](../roles/AGENT_System_Architect.md) (if architectural), [Canonical Governance Officer](../roles/AGENT_Canonical_Governance.md) (governance/audit), [Code Reviewer](../roles/AGENT_Code_Reviewer.md), [Test & Simulation Engineer](../roles/AGENT_Test_Engineer.md), [Refactoring Engineer](../roles/AGENT_Refactoring_Engineer.md), [Risk Architect](../roles/AGENT_Risk_Architect.md) (if risk), [Data Architect](../roles/AGENT_Data_Architect.md) (if schema/data), [DevOps Engineer](../roles/AGENT_DevOps_Engineer.md) (if pipeline/infra), [Repository Auditor](../roles/AGENT_Repository_Auditor.md) (if layout), [Documentation Engineer](../roles/AGENT_Documentation_Engineer.md). Optional intelligence support: [Gemini Research Analyst](../roles/AGENT_Gemini_Research_Analyst.md), [Gemini Data Miner](../roles/AGENT_Gemini_Data_Miner.md), [Gemini Sentiment Scanner](../roles/AGENT_Gemini_Sentiment_Scanner.md) for external context/datasets/sentiment.

Phases:
- Analysis (no changes):
  1. Orchestrator gathers bug description (logs, steps to reproduce), ranks severity.
  2. System Architect (if relevant) checks for structural/architecture implications.
  3. Test & Simulation Engineer reproduces and isolates with test cases/fixtures/simulations.
  4. Code Reviewer analyzes root-cause hypotheses, marks sensitive areas.
  5. Risk Architect evaluates business/live impact; sets blocks or safe modes if needed.
  6. Data Architect (if data issue) assesses schema/data impacts.
  7. Repository Auditor (if layout issue) flags structural fixes.
  8. Orchestrator summarizes fix plan, scope, success criteria; get user go.
- Delivery (changes allowed):
  1. Refactoring Engineer or responsible dev fixes cause and hardens code; pairs with Code Reviewer.
  2. Data Architect executes schema/migration changes if required with rollback.
  3. Test & Simulation Engineer adds regression tests/simulations to CI; verifies reproduction disappears.
  4. DevOps Engineer adjusts deployment/config if relevant; sets feature flags/kill switches for rollout.
  5. Repository Auditor applies approved layout/naming fixes if needed.
  6. Orchestrator checks CI, runs review, plans release with Risk Architect if live risk.
  7. Documentation Engineer records fix, runbook, and release notes.

Outputs:
- Reproducible tests, root-cause note, fix commit/PR.
- Green CI, temporary protections or flags if needed.
- Documented lessons learned and release note.
