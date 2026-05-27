---
name: cdb-docs-ops
description: 'Create or update CDB operational documentation from the working-repo canon. Use when Codex needs to capture system state, derive a health/status digest, write a tactical runbook, or build a crisis playbook. Keep the current SSOT split explicit: `CURRENT_STATUS.md` for repo state, `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` for Echtgeld Go/No-Go, and `docs/runbooks/CONTROL_REGISTER.md` for Board stage and operating focus.'
disable-model-invocation: true
---

# CDB Ops Docs

## Canon first
- Working repo only. Do not default to retired external docs repos.
- Start control-first:
  1. GitHub control issue `#1445`
  2. newest weekly comment on `#1445`
  3. stage-ratification issue `#1492` as Board context only
  4. `docs/runbooks/CONTROL_REGISTER.md`
  5. `CURRENT_STATUS.md`
  6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  7. only then supporting issues, PRs, or repo artifacts
- Keep status classes separate:
  - `CURRENT_STATUS.md` = repo and engineering state
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` = live-readiness verdict
  - `docs/runbooks/CONTROL_REGISTER.md` = Board stage and operating focus
- Never restate `trade-capable` as live authorization. LR is still `NO-GO`.
- Treat `#1492` strictly as ratified stage context, never as LR clearance.

## Modes
1. Create a source doc from raw operational knowledge.
2. Derive exactly one artifact from source docs or canon docs:
   - status digest
   - runbook
   - playbook

## Source doc rules
- Use deterministic wording only.
- Capture facts, constraints, dependencies, downstream impact, and invalidation triggers.
- If the request mixes repo state, LR verdict, and Board stage, split them explicitly instead of collapsing them into one status claim.
- If evidence is missing, stop and ask targeted questions rather than filling gaps with assumptions.

## Artifact rules
- Status digest for health or "where do we stand?"
- Runbook for tactical recovery steps
- Playbook for multi-step incidents or human-gated crisis handling
- Use semantic colors only for gates, verdicts, triggers, and expected results.

## Safety
- No real trades.
- No irreversible action without explicit human approval.
- For any live-trading topic, treat `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` as procedure shape only and `LR-AUDIT-STATUS` as the verdict authority.
