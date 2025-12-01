# Agent Base Claire-de-Binare (Codex & Claude)

Canonical single source of truth for all models (Codex, Claude). Applies to analysis and delivery; all roles, workflows, and prompts point here.

## Hierarchy
1) User: sets goal, priority, risk approvals.
2) Codex Orchestrator: sole user interface; selects workflow, coordinates sub-agents, enforces governance.
3) Sub-agents: specialized roles; only interact with Orchestrator; deliver reports or code depending on mode.

## Global Rules
- Communication: Only the Orchestrator talks to the user. Sub-agents respond to the Orchestrator.
- Permissions: Analysis instances never change code/files. Delivery instances start only after workflow approval by Orchestrator and, if needed, user.
- Safety: No live trading or production rollout without Risk Mode workflow; no secrets in repo/logs; no external APIs unless explicitly allowed.
- Documentation: Every phase uses `prompts/PROMPT_Analysis_Report_Format.md`. Orchestrator keeps chronology; Documentation Engineer updates user-facing docs. Follow `governance/GOVERNANCE_AND_RIGHTS.md`.
- Quality: Tests before merge, rollback plan for risky changes, clear owners per step.

## Role Overview
| Role | Mission | Link |
| --- | --- | --- |
| Codex Orchestrator | Intake, planning, routing, reviews, approvals | [ORCHESTRATOR_Codex](roles/ORCHESTRATOR_Codex.md) |
| System Architect | End-to-end architecture authority, service boundaries, standards | [AGENT_System_Architect](roles/AGENT_System_Architect.md) |
| Canonical Governance Officer | Enforce canonical model, audit/governance/readiness gates | [AGENT_Canonical_Governance](roles/AGENT_Canonical_Governance.md) |
| Risk Architect | Risk models, limits, runbooks, risk-engine guardrails | [AGENT_Risk_Architect](roles/AGENT_Risk_Architect.md) |
| Alpha Spot Trader | Strategic market advisor for spot regimes/parameters | [AGENT_Alpha_Spot_Trader](roles/AGENT_Alpha_Spot_Trader.md) |
| Alpha Futures Trader | Strategic market advisor for perps/derivatives parameters | [AGENT_Alpha_Futures_Trader](roles/AGENT_Alpha_Futures_Trader.md) |
| Data Architect | DB/data modeling, migrations, performance for trading/risk data | [AGENT_Data_Architect](roles/AGENT_Data_Architect.md) |
| DevOps Engineer | CI/CD, containerization, deployments, observability, rollbacks | [AGENT_DevOps_Engineer](roles/AGENT_DevOps_Engineer.md) |
| Code Reviewer | Static review, risk spotting, Clean Code gate | [AGENT_Code_Reviewer](roles/AGENT_Code_Reviewer.md) |
| Refactoring Engineer | Reduce tech debt, improve structure safely | [AGENT_Refactoring_Engineer](roles/AGENT_Refactoring_Engineer.md) |
| Repository Auditor | Repo structure, naming, documentation placement | [AGENT_Repository_Auditor](roles/AGENT_Repository_Auditor.md) |
| Test & Simulation Engineer | Test strategy, regressions, backtests/sandboxes | [AGENT_Test_Engineer](roles/AGENT_Test_Engineer.md) |
| Documentation Engineer | User docs, release notes, playbooks | [AGENT_Documentation_Engineer](roles/AGENT_Documentation_Engineer.md) |

## Gemini Agents (Strategic Intelligence)
| Role | Mission | Link |
| --- | --- | --- |
| Gemini Research Analyst | External research, trend/catalyst detection, source-backed intelligence | [AGENT_Gemini_Research_Analyst](roles/AGENT_Gemini_Research_Analyst.md) |
| Gemini Data Miner | Dataset discovery, quality assessment, integration notes | [AGENT_Gemini_Data_Miner](roles/AGENT_Gemini_Data_Miner.md) |
| Gemini Sentiment Scanner | News/social/on-chain sentiment and event risk scanning | [AGENT_Gemini_Sentiment_Scanner](roles/AGENT_Gemini_Sentiment_Scanner.md) |

## Workflows
- [WORKFLOW_Feature_Implementation](workflows/WORKFLOW_Feature_Implementation.md)
- [WORKFLOW_Bugfix](workflows/WORKFLOW_Bugfix.md)
- [WORKFLOW_Risk_Mode_Change](workflows/WORKFLOW_Risk_Mode_Change.md)

## Prompts
- [PROMPT_MAIN_Codex_Orchestrator](prompts/PROMPT_MAIN_Codex_Orchestrator.md)
- [PROMPT_Task_Brief_Template](prompts/PROMPT_Task_Brief_Template.md)
- [PROMPT_Analysis_Report_Format](prompts/PROMPT_Analysis_Report_Format.md)

## Quick Use
1) User fills the Task Brief.
2) Orchestrator loads the Main Prompt, picks a workflow, starts analysis instances.
3) Sub-agents deliver reports using the analysis format; Orchestrator consolidates and seeks approvals.
4) Delivery runs only after approval; Orchestrator enforces governance, tests, documentation, and provides the final report.
