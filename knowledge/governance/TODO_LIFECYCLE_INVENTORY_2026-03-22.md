---
relations:
  role: audit-artifact
  domain: governance
  upstream:
    - knowledge/governance/CDB_REPO_GUIDELINES.md
  status: active
  tags: [todo-lifecycle, audit, governance, inventory]
---
# TODO/Placeholder Lifecycle Inventory — 2026-03-22

**Issue:** #1236
**Policy:** `knowledge/governance/CDB_REPO_GUIDELINES.md § 6 (Open Marker Lifecycle)`
**Scan tool:** `scripts/todo_lifecycle_audit.sh`
**Audit date:** 2026-03-22

---

## 1. Classification Summary

| Class | Count | Description |
|---|---|---|
| tracked backlog | 18 | TODO/PLACEHOLDER with valid `(#<issue>)` reference |
| temporary technical note | 4 | PR/implementation comments with real PR ref |
| stale leftover (resolved) | 10 | bare TODO/TBD/`#TBD` — fixed in this pass |
| archive candidate | ~20 | bare TODO in old roadmaps, session logs, analysis docs |
| residual (needs issue) | 0 | all skipped tests resolved |

---

## 2. Active-Path Violations — Resolved in This Pass

### Code / Scripts

| File | Change | Policy Rule |
|---|---|---|
| `tests/unit/execution/test_service.py` | `# TODO:` → `# TODO(#308):` (4×) | Rule 1 |
| `scripts/dimensionality_audit/measure_dimensionality.py` | `# TODO:` → `# TODO(#128):` (9×) | Rule 1 |
| `infrastructure/scripts/dimensionality_audit/measure_dimensionality.py` | same as above (identical file) | Rule 1 |
| `services/risk/models.py` | `PR #XXX` → `PR #617` | Rule 1 |
| `services/risk/service.py` | `PR #XXX` → `PR #617` (2×) | Rule 1 |
| `infrastructure/compose/dev.yml` | removed `(TODO: fix field mapping)` — replaced with doc pointer | Rule 1 |

### Dashboards / Monitoring

| File | Change | Policy Rule |
|---|---|---|
| `infrastructure/monitoring/grafana/dashboards/cdb_money_result_owner_v1.json` | `TODO (missing KPIs)` → `PLACEHOLDER(#203)` in description + panel content | Rule 3 |
| `infrastructure/monitoring/grafana/dashboards/cdb_system_health_owner_v1.json` | `TODO (missing KPIs)` → `PLACEHOLDER(#203)` in description, content, and 4 panel titles | Rule 3 |

### Governance / Knowledge Docs

| File | Change | Policy Rule |
|---|---|---|
| `knowledge/contracts/CONTRACTS.md` | `# TODO:` → `# TODO(#154):` in code block; `**TODO:**` → `**TODO(#154):**` (2×) | Rule 3 |
| `knowledge/governance/SECRET_ROTATION_POLICY.md` | `Issue: #TBD` → explicit pending note | Rule 2 |
| `knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md` | `Issue #TBD` → explicit pending note | Rule 2 |
| `knowledge/decisions/MEXC_WEBSOCKET_V3_MIGRATION_DECISION.md` | `Issue #TBD` removed from title | Rule 2 |

### Policy Infrastructure

| File | Change |
|---|---|
| `knowledge/governance/CDB_REPO_GUIDELINES.md § 6` | Already written in PR #1239 / commit c5fb1f9 — not re-touched |
| `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` | Already converted to `Open gate:` form in PR #1239 — not re-touched |
| `scripts/todo_lifecycle_audit.sh` | **NEW** — repeatable scan (see §4) |

---

## 3. Residual / Deliberately Not Resolved

### Residual violation — cleared

The `@pytest.mark.skip` in `tests/performance/verlosung/test_analytics_performance.py:312` was
removed in a subsequent commit within this PR. Root cause: the bug referenced in the skip reason
was already fixed in `3903e98` (Dec 2025); the path `backoffice/scripts/` never existed in the
working repo. The skip was stale Verlosung-migration ballast, not a real open blocker.
`scripts/todo_lifecycle_audit.sh` confirms 0 violations (Rule 4: OK).

### Archive-candidate TODOs (deliberately not touched)

The following paths carry bare `TODO`/`TBD` markers in content that is primarily historical, analytical, or draft-quality. These are NOT in active operator-facing or code paths and do not create operational risk:

- `knowledge/reviews/CONSISTENCY_AUDIT.md` — stale status table
- `knowledge/roadmap/M7_TESTNET_PLAN.md`, `M8_SECURITY_PLAN.md`, `M9_RELEASE_PLAN.md` — old milestone roadmaps
- `knowledge/analysis/PROJECT_ANALYTICS.md` — research analysis
- `knowledge/decisions/K8S_BUDGET_DECISION.md` — decision doc with TBD gate values
- `knowledge/content/ONBOARDING_LINKS.md`, `ONBOARDING_QUICK_START.md` — content docs
- `knowledge/operations/disaster_recovery/README.md` — backup TODO (Issue #1175 separately tracked)
- `knowledge/operations/MCP_CENTRAL_CONFIG.md` — agent config note
- `knowledge/security/SECURITY_HARDENING.md` — hardening checklist note
- `knowledge/logs/sessions/` — historical session logs (never cleaned per policy)
- `docs/contracts/blocked_decisions.schema.yaml`, `correlation.schema.yaml` — TBD code_lines
- `docs/governance/evidence/ISSUE-741-postgres-least-privilege-rls.md` — evidence artifact

**Rationale:** Cleaning all historical knowledge docs would violate the "minimal-invasive" and "no large-scale reorganisation" guardrails. These paths are not operator-facing and do not cause Scheinsicherheit.

---

## 4. Repeatable Audit Scan

```bash
# Run from repo root
bash scripts/todo_lifecycle_audit.sh

# Verbose (shows all hits):
bash scripts/todo_lifecycle_audit.sh --verbose
```

**Exit codes:**
- `0` = PASS (no violations)
- `1` = FAIL (violations found)

**Rules checked:**
1. Unreferenced `# TODO:` / `# FIXME:` in code/scripts (must use `TODO(#issue):`)
2. Bare `Issue #TBD` / `#TBD` in active governance/runbook docs
3. Bare `TODO` in active dashboards and canonical docs
4. `@pytest.mark.skip` without an issue reference in the reason string

**False-positive exclusions built into the script:**
- `scripts/todo_lifecycle_audit.sh` itself
- `knowledge/governance/CDB_REPO_GUIDELINES.md` (the policy document lists forbidden markers as examples)
- `.orchestrator_*` files
- Archive trees: `knowledge/archive/**`, `docs/archive/**`
- Historical paths: `knowledge/logs/sessions/**`, `knowledge/reviews/**`, `knowledge/roadmap/**`, `knowledge/analysis/**`, `knowledge/decisions/**`

---

## 5. Policy Decisions

| Decision | Rationale |
|---|---|
| `TODO(#<issue>):` is the required form in code | Unambiguous, machine-readable, links directly to tracker |
| `PLACEHOLDER(#<issue>):` for dashboard/doc shells | Signals deliberate incompleteness; issue provides timeline |
| Archive/snapshot trees are excluded from cleanup | Editing evidence or session logs retroactively damages audit trail |
| `PR #617` preferred over `# NOTE:` for existing code | Keeps author attribution and traceability; no open work implied |
| `TODO(#154)` used in CONTRACTS.md | Issue #154 (code audit) was the closest relevant umbrella; noting it is better than leaving bare TODO even though #154 is closed — the reference is informational |
| `#TBD` in governance docs replaced with explicit prose | Governance docs with `#TBD` give false impression of tracked work; explicit "pending / no issue created" is more honest |
