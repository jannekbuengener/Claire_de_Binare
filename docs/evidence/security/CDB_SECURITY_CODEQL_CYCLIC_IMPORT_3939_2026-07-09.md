# CodeQL Cyclic-Import Fix — Issue #3939

**Date:** 2026-07-09 (UTC+2)  
**Scope:** Break `py/cyclic-import` between context harness and evidence JSON  
**Issue:** [#3939](https://github.com/jannekbuengener/Claire_de_Binare/issues/3939)  
**Parent:** [#3924](https://github.com/jannekbuengener/Claire_de_Binare/issues/3924) quality batch  
**LR:** NO-GO (unchanged)

---

## Brain Evidence

| Feld | Wert |
|------|------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| repo_fallback_used | true |
| repo_fallback_reason | insufficient_evidence |
| tools_or_queries | `gh api code-scanning/alerts`, repo import graph, targeted pytest |
| records_or_results | Alerts #4616, #4617 (`py/cyclic-import`) on harness ↔ evidence_json |
| impact_on_plan | Module split at shared types; no CodeQL suppression |

---

## Root Cause

- `context_invocation_evidence_json` imported `context_live_invocation_harness` at module level for `HarnessReport` / `MatrixRow`.
- `context_live_invocation_harness.format_report()` lazy-imported `serialize_invocation_evidence` from evidence_json for `--format json`.
- CodeQL `py/cyclic-import` flags the module-level cycle (#4616, #4617).

## Fix

Extracted shared dataclasses and constants to `tools/surrealdb/context_invocation_harness_types.py`:

- `MatrixRow`, `HarnessReport`, `MatrixStatus`, `FinalVerdict`, `InvocationProfile`
- `ISSUE_REF`, `RATIFICATION_DOC`

Import graph after fix:

```
context_invocation_harness_types  (no surrealdb siblings)
        ↑                ↑
        |                |
evidence_json      live_invocation_harness ──lazy──► evidence_json (json format only)
```

No top-level cycle: evidence_json no longer imports harness.

## Validation

```bash
ruff check tools/surrealdb/context_invocation_harness_types.py \
  tools/surrealdb/context_invocation_evidence_json.py \
  tools/surrealdb/context_live_invocation_harness.py
pytest -q tests/unit/surrealdb/test_context_invocation_evidence_json.py \
  tests/unit/surrealdb/test_context_live_invocation_harness.py
```

## Restunsicherheit

GitHub CodeQL alert closure (#4616, #4617) is measurable only after Default Setup rescan on `main`. No alert dismissals performed.

## Safety Boundaries

- No alert dismissals
- #3755 Grafana HOLD untouched
- #3936 libcurl residual untouched
- No Trivy/image/runtime changes
- LR remains NO-GO
