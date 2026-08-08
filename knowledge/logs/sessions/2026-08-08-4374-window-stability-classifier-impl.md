# Session — #4374 window_stability + durable classifier implementation

Date: 2026-08-08
Surface: Cursor worktree `batch-validation-research-issue-4374-exec-prep`
Branch: `batch/validation-research-issue-4374`
Result: delivery slice for contracts + library + tests + Owner-GO prep
Issue: #4374 (OPEN; Refs only — not closed)

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- context_brain_attempted: true
- context_available: false
- repo_fallback_reason: insufficient_evidence

## Delivered

### Slice 1
- `docs/contracts/cdb_hh_hl_window_stability.v1.schema.json`
- `tools/arvp_vacation/hh_hl_window_stability.py`
- `tests/unit/arvp/test_hh_hl_window_stability.py`
- example artifact under `docs/contracts/examples/`

### Slice 2
- `docs/contracts/cdb_hh_hl_analyzer_classification.v1.schema.json`
- `docs/contracts/cdb_hh_hl_classifier_threshold_policy.v1.schema.json`
- durable `classify_hh_hl_campaign` in `hh_hl_campaign_analyzer.py`
- `tests/unit/arvp/test_hh_hl_campaign_analyzer_classification.py`

### Owner threshold policy prep
- DRAFT `uniform_negative_sign_reject_v1` example (PROMISING rules empty)
- Owner GO package + comment draft for ratification

### Future execute window prep
- Execute prompt + Owner GO package/comment draft
- No live stability build / no analyzer re-execute against primary

## Validation

```bash
python -m pytest tests/unit/arvp/test_hh_hl_window_stability.py \
  tests/unit/arvp/test_hh_hl_campaign_analyzer_classification.py -q
```

All targeted tests PASS (Windows pytest tmp cleanup PermissionError is infra noise).

## Safety

- LR NO-GO
- Primary immutable
- No Stage B / Paper / Live
- PROMISING remains research follow-up only
- No #4153 matrix assumptions

## Next step

1. Merge batch PR (separate merge session).
2. Owner ratify threshold policy (optional for REJECTED path).
3. Owner post Execute-GO; then run execute prompt sequence and STOP.
