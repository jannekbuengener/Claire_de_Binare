# #4374 Execute — window_stability build + durable re-classify

Status: PLANNING_ONLY until Owner posts `GO_HH_HL_WINDOW_STABILITY_CLASSIFIER_EXECUTE`.
LR: NO-GO. No Stage B / Paper / Live / Echtgeld / Promotion / Primary mutation.

## Preconditions

1. Slice contracts merged on `main` (or this batch branch after merge):
   - `cdb.hh_hl_window_stability.v1`
   - `cdb.hh_hl_analyzer_classification.v1`
   - `cdb.hh_hl_classifier_threshold_policy.v1`
2. Live Owner-GO comment on #4374 with fence
   `cdb.hh_hl_window_stability_classifier_authorization.v1`
   and status `GO_HH_HL_WINDOW_STABILITY_CLASSIFIER_EXECUTE`.
3. Bound Primary unchanged:
   - `campaign_phase=PRIMARY_COMPLETE` 39/39
   - param FP `9067cd6aa48ad2cc2a7932af50e990888048b8f912b8f3e3ad0dd5b318d1c0a4`
   - summary FP `e5faae11041706e8668252387808f3bd193bdb24c8505d6ba1a7e162413adf28`
   - Owner Primary GO `5222204496` (do not reuse as this execute GO)
4. Reproduction evidence from GO `5223567140` remains PASS (read-only bind).
5. Optional: Owner-ratified threshold policy
   (`uniform_negative_sign_reject_v1`, `policy_status=OWNER_RATIFIED`).
   Without it, max verdict is `INCONCLUSIVE` /
   `ANALYZER_INCONCLUSIVE_THRESHOLD_POLICY_ABSENT`.

## Sequence (STOP after step 8)

1. **Owner-/Contract-Gate** — verify GO fence live via `gh api`; verify schemas present.
2. **Primary read-only bind** — recompute sha256 of `campaign_summary.json` + envelope; abort if drift.
3. **Stability Artifact erzeugen**

```bash
python -m tools.arvp_vacation.hh_hl_window_stability build \
  --evidence-root "<PRIMARY_ROOT>" \
  --bindings-json "<bindings.json>" \
  --run-keys-json "<expected_run_keys.json>" \
  --write
```

4. **Stability Artifact validieren**

```bash
python -m tools.arvp_vacation.hh_hl_window_stability validate \
  --artifact "<PRIMARY_ROOT>/window_stability.json"
```

5. **Analyzer mit Stability erneut ausführen** — call
   `classify_hh_hl_campaign(...)` with bound stability (+ ratified policy if present).
6. **durable Classification Artifact schreiben** — new file only; do **not**
   overwrite `docs/evidence/arvp_hh_hl_analyzer_classification_4374_5223567140.json`.
7. **Ergebnis berichten** on #4374 (classification, reason_code, fingerprints).
8. **STOP** — no Stage B, no Paper, no Live, no automatic follow-up execute.

## Hard non-goals

- No new replay runs
- No reproduction re-run
- No primary run-tree mutation
- No inventing PROMISING thresholds
- No #4153 21/19 matrix assumptions
- Do not close #4374 unless Owner explicitly asks

## Expected statuses

| Condition | Verdict |
|---|---|
| Stability missing/invalid | `INCONCLUSIVE` / `ANALYZER_INCONCLUSIVE_WINDOW_STABILITY_ABSENT` |
| Stability OK, policy absent/draft | `INCONCLUSIVE` / `…_THRESHOLD_POLICY_ABSENT` or `…_NOT_RATIFIED` |
| Stability OK + ratified uniform-negative rule fires | `REJECTED` / `ANALYZER_REJECTED_UNIFORM_NEGATIVE_SIGN` |
| PROMISING | only if Owner-ratified promising rule exists and fires (v1 draft has none) |
