---
relations:
  role: historical_reference
  domain: knowledge
  status: historical
  mandatory_read: false
  superseded_by:
    - docs/meta/REPOSITORY_CANON.md
    - CURRENT_STATUS.md
    - docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
    - docs/runbooks/CONTROL_REGISTER.md
---
# CDB Knowledge Hub

**Status:** HISTORICAL / REFERENCE ONLY  
**Mandatory read:** No  
**Historical baseline:** December 2025  
**Reclassified:** 2026-07-17 via issue #4117

## Practical meaning

This file preserves the former shared decision and agent-handoff hub from the
December 2025 repository phase. It is retained for audit provenance and
historical comparison.

It is **not** a current status source, governance source, task tracker, runtime
canon, agent registry, or live handoff queue.

## Current authoritative entry points

Use these files instead:

- [Repository canon](../docs/meta/REPOSITORY_CANON.md)
- [Current repository and engineering status](../CURRENT_STATUS.md)
- [Live-readiness verdict](../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- [Board and control status](../docs/runbooks/CONTROL_REGISTER.md)
- [Governance](governance/CDB_GOVERNANCE.md)
- [Agent policy](governance/CDB_AGENT_POLICY.md)
- [Canonical agent registry](../agents/AGENTS.md)
- [Agent root surface matrix](../docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md)

These sources win whenever they conflict with historical content described
below.

## Historical boundary

The following statements are historical and must not be read as present-day
runtime or repository truth:

- GitLab CI as an active secondary path
- the old `base / dev / prod` Compose model as current runtime canon
- December 2025 test and infrastructure baselines
- multi-person Claude/Gemini/Codex write-role assignments
- external-only agent definitions
- December 2025 handoff and delivery queues

The active repository uses the current repo-backed Canon, BLUE/RED runtime
surfaces, GitHub workflows, and versioned agent-root adapters documented by the
entry points above.

## Historical handoffs

| Historical handoff | Original state | Current classification |
|---|---|---|
| Codex → Claude: P1 developer tools | DONE, 2025-12-14 | HISTORICAL COMPLETE |
| Claude → Services: `get_secret()` migration | OPEN, December 2025 | CLOSED / HISTORICAL — no active tracking evidence |
| Gemini → Claude: governance review | OPEN, December 2025 | CLOSED / HISTORICAL — no active tracking evidence |

No item in this table is an active assignment. Current work must be represented
by a live GitHub issue, pull request, or current status/control surface.

## Historical decisions

### Repository-local canon — retained principle

The repository-local Canon principle remains valid only through the current
[repository canon](../docs/meta/REPOSITORY_CANON.md), not through the old wording
in this file.

### External-only agents — superseded

**Original decision:** 2025-12-19, agent definitions outside the repository.  
**Current state:** SUPERSEDED.

The repository now contains versioned agent surfaces under `.claude/`,
`.codex/`, `.cursor/`, `.gemini/`, `.opencode/`, `.vscode/`, and `agents/`.
Their current roles and authority boundaries are defined by
[AGENTS.md](../AGENTS.md), [agents/AGENTS.md](../agents/AGENTS.md), the
[agent policy](governance/CDB_AGENT_POLICY.md), and the
[root surface matrix](../docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md).

### December 2025 roadmap and delivery plans — historical

M7–M9 roadmap refinements, PR-01 through PR-06, session summaries, delegation
notes, and the former Claude tasklist are historical records. They do not create
current work, approval, or operational authority.

The complete pre-reclassification text remains available through Git history up
to commit `191b926a1a5543a094bcd2bc1a74c67b25229eb9`.

## Maintenance rule

This file is append-only for historical clarification. Do not add live status,
new handoffs, current decisions, runtime instructions, or governance rules here.

A current claim belongs in its existing authoritative surface. A current task
belongs in GitHub. A historical correction may be added only with a dated source
reference.
