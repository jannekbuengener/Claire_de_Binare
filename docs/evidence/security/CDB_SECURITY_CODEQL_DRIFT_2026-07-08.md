# CodeQL Drift Triage — 63 Open Alerts (HIGH Fix Slice)

**Date:** 2026-07-08 (UTC+2)  
**Scope:** `CODEQL_DRIFT_SLICE` — triage + minimal HIGH security fix  
**Repo @ probe:** `4d095de9` (`origin/main` pre-slice)  
**LR:** NO-GO (unchanged)

---

## Brain Evidence

| Feld | Wert |
|------|------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| context_brain_used | false |
| repo_fallback_used | true |
| repo_fallback_reason | insufficient_evidence |
| tools_or_queries | `gh api code-scanning/alerts` (paginate), repo reads, targeted pytest |
| records_or_results | CodeQL open **63** (4 HIGH, 59 quality) at slice start |
| impact_on_plan | GitHub API authoritative for alert inventory; fixes scoped to 4 HIGH only |

---

## Ledger Drift (#2513)

| Source | CodeQL open |
|--------|-------------|
| Epic #2289 Slice 1 / #2513 body | **0** |
| Live GitHub Code Scanning (2026-07-08) | **63** |

**Root cause (documented):** Post [#3673](https://github.com/jannekbuengener/Claire_de_Binare/pull/3673) GitHub **CodeQL Default Setup** is authoritative for Code Scanning alerts. Advanced [`codeql-python.yml`](../../.github/workflows/codeql-python.yml) runs `security-and-quality` with `upload: false` — validation only. The historical “CodeQL 0” claim reflected the advanced-workflow reduction, not the Default Setup surface now visible in GitHub Security.

**Boundary:** Alert closure is measurable only after the next Default Setup scan on `main`. No GitHub alert dismissals in this slice.

---

## CodeQL Inventory (open @ slice start)

| Category | Count | Notes |
|----------|-------|-------|
| **Total open** | **63** | GitHub API |
| HIGH security | 4 | `clear-text-*` in `tools/surrealdb/` |
| Quality | 59 | unused-import, ineffectual-statement, empty-except, … |

### HIGH security alerts

| Alert | Rule | File | Classification | Action |
|-------|------|------|----------------|--------|
| [#4535](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4535) | `py/clear-text-storage-sensitive-data` | `audit_trail_t3_common.py` | Taint on env `write_text` despite sidecar pattern (#2918) | Refactor: metadata write isolated from `surreal_pass` scope |
| [#4612](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4612) | `py/clear-text-storage-sensitive-data` | `audit_trail_t3_common.py` | Compose env writes username only | Neutral `_write_operator_env_file` helper |
| [#4611](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4611) | `py/clear-text-logging-sensitive-data` | `context_importer.py` | True-positive: `_emit_error` lacked redaction | `redact_sensitive_json` in `_emit_error` |
| [#4533](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4533) | `py/clear-text-logging-sensitive-data` | `context_onboarding_doctor.py` | Sanitizer-blind stdout path | `format_report` uses `redact_sensitive_json` / `redact_sensitive_text` |

### Quality clusters (not fixed in this slice)

| Rule | Count | Primary paths |
|------|-------|---------------|
| `py/unused-import` | 16 | `tools/surrealdb/*`, tests, `.codex/*` |
| `py/ineffectual-statement` | 16 | `memory_write_path_*`, `memory_db_*` |
| `py/empty-except` | 10 | audit_trail, onboarding, `.codex/imagegen` |
| Other | 17 | cyclic-import, unused vars, … |

**Follow-up:** separate engineering batch for 59 quality alerts (dedupe vs #2513).

---

## Delivered (this slice)

| File | Change |
|------|--------|
| `tools/surrealdb/context_importer.py` | `_emit_error` → `redact_sensitive_json` |
| `tools/surrealdb/audit_trail_t3_common.py` | Split metadata/sidecar writes; `_write_operator_env_file` |
| `tools/surrealdb/context_onboarding_doctor.py` | Redacted `format_report`; epilog wording |
| `tests/unit/surrealdb/test_context_importer_sensitive_output.py` | `ContextImporterError` redaction test |
| `tests/unit/surrealdb/test_context_onboarding_doctor.py` | `main()` stdout redaction test |

---

## Validation

```bash
pytest -q tests/unit/surrealdb/test_sensitive_output.py \
         tests/unit/surrealdb/test_context_importer_sensitive_output.py \
         tests/unit/surrealdb/test_context_onboarding_doctor.py
# 36 passed
git diff --check
```

Local CodeQL CLI: not run (optional). Post-merge recount via `gh api … code-scanning/alerts` required.

---

## Safety Boundaries

- No alert dismissals
- No Trivy/image/Grafana (#3755 HOLD)
- No BLUE/RED runtime changes
- No MCP/DB mutations
- LR remains NO-GO

---

## References

- Meta tracker: [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)
- Prior retriage: `knowledge/logs/sessions/2026-07-08-security-retriage-readonly-report.md`
- Sensitive output helpers: `tools/surrealdb/sensitive_output.py` (#2918–#2920)
- Control register CodeQL posture: `docs/runbooks/CONTROL_REGISTER.md` (#3673)
