# Session: CDB-052 Rankability / Warmup-Provenance fail-closed (#4336)

Date: 2026-08-04  
Branch: `batch/validation-research-issue-4336-cdb052`  
Base: `origin/main` @ `d9da71b0` (CDB-051 merged via #4340)

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
context_tool_status: available
context_trust_level: none
records_found: none
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
```

## Delivered (CDB-052-only)

- Shared `assert_rankability_provenance` / `enforce_rankability_provenance`
- Batch-A missing manifest → `manifest_missing` (no silent skip)
- Stale manifest warmup fill remains blocked
- `record_is_rankable` requires `rankable is True` + bound provenance
- Extraction emits `rankability_blocking_flags`
- Sensitivity preflight gate `cdb052_rankability_provenance`
- Parameter-control CDB-052 → `CORRECTNESS_FIX_ONLY`, `blocked_by_issues: [4336]`
  - `RESEARCH_ALLOWED` retained with explicit non-promotion note
- Deterministic register / YAML / sensitivity fixture fingerprint updates

## Validation

- Targeted unit matrix: 72 passed / 3 skipped (rankability, scorers, preflight, closure, extraction, PC)
- Broader keyword regression: 137 passed (incl. CDB-049/050/051 integrity/provider paths)
- ruff PASS; black PASS; gitleaks protect --staged: no leaks
- `python -m tools.validate_parameter_control_policy` PASS
  - `register_fingerprint=bfbfc042…`
  - `canonical_json_sha256=fe1c6f1d…`

## Router

- `CREATE_NEW_BATCH_PR` / lane `validation-research` / `NO_COMPATIBLE_OPEN_PR`
- Branch kept as `…-cdb052` (anti-repush vs deleted `…-4336`)

## Non-goals held

No merge, no `cdb-local-ci`, no Issue close, no sensitivity campaign, LR NO-GO.
CDB-049..051 not regressively redesigned.

## Status

`DONE_CDB052_RANKABILITY_PROVENANCE_ADDED_TO_BATCH_PR` (after PR open)
