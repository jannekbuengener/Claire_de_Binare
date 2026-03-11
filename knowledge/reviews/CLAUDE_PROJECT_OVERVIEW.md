---
title: Claude Project Overview
status: draft
date: 2025-12-19
owner: codex
---
# Claude Project Overview

## Purpose
Provide Claude a concise, current snapshot of repo structure, active work, and blockers.

## Repo Topology
- Docs Hub (canonical): `Claire_de_Binare_Docs`
- Working Repo (execution only): `Claire_de_Binare`

## Current Workstreams (high-level)
- Paper Trading M7 planning: sprint plan + testnet plan drafted in Docs Hub.
- Security M8: Trivy scan in CI, non-root hardening for market + db_writer.
- CI stability: gitleaks ignore path, Redis import stub, and CI deps fixes.

## Active Branches / PRs
- Working Repo: `copilot/enhanced-discussion-pipeline`
  - PR #152: https://github.com/jannekbuengener/Claire_de_Binare/pull/152
  - Recent commits:
    - 3903e98 (query_analytics harden)
    - 6cf07a8 (Trivy scan + non-root + local-only tests)
    - acb1d27 (CI deps for tests)
- Docs Hub: `copilot/improve-deep-issues-pipeline`
  - Recent commit: 948fa0f (incident response + pentest stubs + perf baselines)

## Key Files (Claude should scan)
- Docs Hub:
  - `knowledge/systems/PAPER_TRADING_ARCHITECTURE.md`
  - `knowledge/testing/PAPER_TRADING_TEST_REQUIREMENTS.md`
  - `knowledge/tasklists/M7_SPRINT_PLAN.md`
  - `docs/roadmap/M7_TESTNET_PLAN.md`
  - `knowledge/operating_rules/security/INCIDENT_RESPONSE_PLAYBOOK.md`
  - `knowledge/reviews/PENTEST_WEB_REPORT.md`
  - `knowledge/reviews/PENTEST_INFRA_REPORT.md`
  - `knowledge/testing/PERFORMANCE_BASELINES.md`
- Working Repo:
  - `.github/workflows/ci.yaml`
  - `infrastructure/scripts/query_analytics.py`
  - `services/market/Dockerfile`
  - `services/db_writer/Dockerfile`

## Open Blockers / Inputs Needed
- KANBAN_STRUCTURE.md missing (blocks #110/#114).
- SECURITY_ROADMAP.md missing (blocks deeper M8 roadmap items).
- PR #87 diff/logs needed for final resolution in #116 (partially addressed).
- E2E P0 tests (#94/#113) need explicit Working Repo write approval + env.

## CI Status (PR #152)
- Failing: Branch Policy (branch name + PR template), tests missing deps (fixed in acb1d27; rerun needed).
- Passing: Gitleaks, Trivy, Bandit, pip-audit, docs checks.

## Next Steps (suggested)
1. Rerun CI for PR #152 and fix branch-policy naming if required.
2. Decide on KANBAN_STRUCTURE.md and SECURITY_ROADMAP.md location.
3. Approve/assign E2E P0 test implementation (#113).
