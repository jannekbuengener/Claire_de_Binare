# hh_hl_continuation_v1 Campaign Preparation Evidence (#4374 / PR #4375)

**Status:** preparation slice hardened with physical dataset proof
**Issue:** #4374 OPEN
**PR:** #4375 DRAFT
**Lineage:** #4372 / PR #4373
**Parent:** #1900
**LR:** NO-GO · `campaign_authorized=false` · no Campaign Execute

## Architecture Verdict

`PROFILE_DRIVEN_EXTENSION_SAFE`

## Dataset Wiring Map

| Need | Canonical place | Reuse |
|---|---|---|
| Root validation | `sensitivity_campaign_dataset_root._pick_window_bank_root` | yes |
| Candle load | `binance_window_bank_adapter.load_window_candles_jsonl` + `load_dataset_spec` | yes |
| Content hash | `core.replay.dataset_identity.content_fingerprint` | yes |
| Window lock | `LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS` + selection SHA | yes |

## Physical local proof

```text
python -m tools.arvp_vacation.hh_hl_campaign_plan prove-dataset \
  --dataset-root <LOCAL_WINDOW_BANK_ROOT> \
  [--receipt-out docs/evidence/arvp_hh_hl_dataset_local_proof_receipt_4374.json]
```

Observed PASS:

- `quality_gate_status=DATASET_BINDING_LOCAL_PROOF_PASS`
- `local_proof_required=false`
- `window_count=39`
- `selection_sha256=3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52`
- `content_fingerprint_digest=10f94c34e32db28a9393c38f944db4968b42e87d9ed223397e3637ff44323af9`
- Receipt: `docs/evidence/arvp_hh_hl_dataset_local_proof_receipt_4374.json`
- Repeat proof digest match: true
- No absolute paths in receipt

## Dry-Plan with receipt

```text
python -m tools.arvp_vacation.hh_hl_campaign_plan plan \
  --dataset-receipt docs/evidence/arvp_hh_hl_dataset_local_proof_receipt_4374.json
```

- `writes=false`, `replays=false`, `execution_sha=null`
- `campaign_execution_authorized=false`
- `manifest_fingerprint=4e5532b33ccbb838f2302f1e0e3592c3d8d12f6929f5feb27cf91071cda5172e`
- `run_plan_fingerprint` binds `planning_sha` of delivery head (see PR head after push)
- Dataset HOLD removed; Grid HOLD remains
- `proof_code_sha=503f6bf6f1ef8e133f1ae24402ba88b258c993175d4ee848141af108af13f26c`
## Remaining Holds

- `HOLD_CAMPAIGN_GRID_OWNER_RATIFICATION_REQUIRED`
- missing `GO_HH_HL_CAMPAIGN_DESIGN` / `GO_HH_HL_CAMPAIGN_EXECUTION`
- `execution_enabled=false`

## Allowed / forbidden claims

Allowed: physical dataset proof PASS · #4153 regression intact · planning-only · no execute.
Forbidden: Campaign authorized · Campaign started · Grid ratified · Design/Execution GO posted · Merge candidate.
