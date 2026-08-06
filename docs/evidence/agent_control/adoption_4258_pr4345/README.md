# Cursor Delivery Adoption Evidence Bundle — Issue #4258 / PR #4345

Status: tracked evidence for ACP reconciliation slice  
Issue: [#4258](https://github.com/jannekbuengener/Claire_de_Binare/issues/4258)  
Evidence source PR (unchanged): [#4345](https://github.com/jannekbuengener/Claire_de_Binare/pull/4345)  
Observed: 2026-08-06 (Europe/Berlin)  
LR: **NO-GO**

## Artifacts (this directory)

| File | Role |
| --- | --- |
| `adoption_receipt.json` | Cursor Delivery Verification + Adoption/Reconciliation Receipt |
| `approval_context.json` | PR Approval Context bound to PR #4345 head |
| `approval_handoff.json` | Approval-Agent Handoff (prepared, not executed) |
| `acceptance_matrix.json` | L1/L2/L3 Acceptance Matrix |

## Live verification (read-only)

| Check | Result |
| --- | --- |
| Repository | `jannekbuengener/Claire_de_Binare` |
| Cursor agent id | `bc-1d8c87d1-249a-46ab-a5b0-5734f8fe1519` |
| Branch | `cloud-cursor/dev-env-setup-1519` exists; tip = expected head |
| Head SHA | `01a65ae6e1b55648da1cf62c3de8a4ec2e3a926b` |
| PR | #4345 OPEN, head matches tip |
| Commit author | `cursoragent` / `cursoragent@cursor.com` |
| PR body agent ref | present |
| Phantom branch | none |
| Cursor HTTP POSTs | **0** |
| GitHub writes by verifier | **0** |

## Verdicts

| Gate | Verdict |
| --- | --- |
| Delivery classification | `VERIFIED_CURSOR_CLOUD_GITHUB_DELIVERY` |
| Adoption | `ADOPTABLE_WITH_EXPLICIT_RECONCILIATION_RECEIPT` |
| Approval Context | bound; recommendation `UNKNOWN` (`REQUIRED_CHECK_MISSING` for `cdb-local-ci` — expected; no fake-green) |
| Approval-Agent Handoff | `APPROVAL_HANDOFF_PREPARED_NOT_EXECUTED` / `READY_FOR_APPROVAL_AGENT_HANDOFF` |
| Acceptance | `PARTIAL_4258_ACCEPTANCE_L2_L3_PROVEN` |

## L1 / L2 / L3

- **L1** PARTIAL — two earlier CDB Cursor creates executed and ended `ERROR`; they did **not** produce PR #4345.
- **L2** PROVEN — PR #4345 is a verified Cursor Cloud GitHub delivery.
- **L3** PREPARED — Approval Context + advisory Handoff bound to exact head + adoption digest; Approval Agents remain `MANUAL_BOOTSTRAP_ONLY`.

## Authority limits (all false)

`merge`, `approval`, `live`, `runtime_mutation`, `github_delivery_create`, `cursor_http_posts`, `publish_cdb_local_ci`

## Automations / Self-hosted Go-No-Go

**NO-GO** for Automations and Self-hosted expansion.

Reasons:

- Full E2E chain (same CDB create → delivery → approval) remains unproven.
- `provider_dispatch_proven=false` for this adopted delivery.
- Approval Agents not officially executable (`MANUAL_BOOTSTRAP_ONLY`).
- No Final-CI / `cdb-local-ci` publish / merge authorized in this slice.

## Lessons learned

1. Cursor footer alone is insufficient; bind agent id + commit author + branch tip + PR head together.
2. External successful Cloud delivery can enter ACP only via an explicit reconciliation receipt — never by silently rewriting failed run IDs.
3. Approval Context must bind the adoption digest and exact head without inventing required-check SUCCESS.
4. Hosted Actions SUCCESS on #4345 is a GitHub snapshot only — not Final-Head merge evidence.

## Allowed claims

- PR #4345 is a verified real Cursor Cloud GitHub delivery (live checks passed).
- Delivery was classified into the ACP pilot via an explicit Adoption Receipt.
- Approval Context was bound to the exact PR head and adoption digest.
- No new Cursor run was started; no merge was authorized.

## Forbidden claims

- PR #4345 was produced by a prior CDB pilot run.
- The two failed Cursor runs were successful.
- Full E2E is proven.
- PR #4345 is automatically approved or merge-ready.
- Issue #4258 is closed.
- Automations / Self-hosted are cleared.
- Live / Echtgeld GO.

## Immutable failed runs (unchanged)

- `run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b`
- `run-c2c3898b-af9e-4f73-ad91-830f600561b9`

See also: [`CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md`](../CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md).
