# Session: #4036 Scanner README-only Architecture Suppression

**Date:** 2026-07-13  
**Issue:** [#4036](https://github.com/jannekbuengener/Claire_de_Binare/issues/4036)  
**Branch:** `fix/4036-architecture-scanner-readme-precision`  
**Base:** `origin/main` @ `740fc11d16c3976679af06171cf3b871da1f127d`

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
records_found: none
```

## Scope

Suppress README-only false positives for `architecture_service_catalog_drift` while
preserving fingerprint/dedupe compatibility for mixed README + structural PRs.

## Delivered

- `normalize_repo_path()` / `is_services_or_core_readme()` in scanner
- Architecture trigger decision on `architecture_structural_files` (README-filtered)
- Digest-only evaluation on structural subset only
- Fingerprint/trigger_files remain on full `service_runtime_files` shortlist
- Unit tests + runbook update

## Validation

Recorded in PR body after CI.

## Boundaries

- LR NO-GO; no runtime/trading/DB/MCP changes
- PR #3755 untouched; work in dedicated worktree
