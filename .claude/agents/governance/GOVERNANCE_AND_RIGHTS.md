# GOVERNANCE_AND_RIGHTS

Reference: ../AGENTS.md

## Decision Rights
- User: final go/no-go for delivery, releases, risk-mode changes, and any live-trading action.
- Codex Orchestrator: runs workflows, assigns roles, blocks on rule violations, requests approvals.
- Sub-agents: advise within their remit; may change artifacts only in Delivery phase when Orchestrator permits.

## Safety Rules
- No live trades or production deployments without the Risk Mode workflow and user approval.
- Secrets/keys only through approved paths; never in logs or repository.
- Feature flags/configs need rollback paths; prefer blue-green or canary.
- Enable logging/monitoring for new changes; alerts for critical KPIs.

## Documentation Duties
- Every phase uses `prompts/PROMPT_Analysis_Report_Format.md`.
- Orchestrator keeps task chronology; Documentation Engineer maintains user docs and release notes.
- Record key decisions: what, why, who, date, rollback strategy.

## Risk/Mode Changes
- Always use WORKFLOW_Risk_Mode_Change.
- Require: risk assessment by Risk Architect; test plan by Test Engineer; flag/config design by DevOps Engineer; approval by user and Orchestrator.
- Define stop criteria and monitoring before activation.

## Live-Trading Guardrails
- Default mode is safe/staging/paper.
- Live activation only after dual approval (user + Orchestrator) and successful probe test.
- Provide kill switch, rollback plan, and monitoring for the initial phase.
