# LR-050 Receiver Proof Canon — Operator Receipt Path (#2981)

## Purpose

Define the **canonical** LR-050 operator-receipt proof path for
[#2981](https://github.com/jannekbuengener/Claire_de_Binare/issues/2981), so a
**separate Operator-GO** test slice can execute without re-deciding routing on each
run.

This document is **documentation only**. It does not trigger alerts, read secrets,
start Docker, or close #2981.

Supersedes the channel-declaration gap identified in
[`LR-050-RECEIVER-PROOF-PREFLIGHT-2026-07-03.md`](./LR-050-RECEIVER-PROOF-PREFLIGHT-2026-07-03.md)
(Preflight PR [#3709](https://github.com/jannekbuengener/Claire_de_Binare/pull/3709)).

## Scope

In scope:

- Canonical receiver class, test method, operator inputs, evidence format, redaction,
  and acceptance criteria for #2981.
- Explicit exclusions (Alertmanager internal webhooks, LR-030 synthetic AM proof).

Out of scope:

- No alert firing, SMTP send, Grafana UI mutation, or runtime restart.
- No secret reads by agents; no Live-Go / Echtgeld-Go / LR status change.
- No closure of #2981 (requires committed evidence artifact).

## Control State

| Surface | State |
|---|---|
| LR-050 verdict | **NO-GO** ([`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)) |
| Blocker | Operator Receiver Proof missing — [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md) §3 |
| Refresh matrix | [`LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md`](./LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md) row 2 |
| Gate SSOT | [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §3–§4 |
| Secrets cross-ref | [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983) — SMTP secret **names** only; verification is operator-local |
| Downstream | [#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984) — kill-switch drill depends on receiver proof |
| Canon date | 2026-07-03 |

---

## Canonical Decisions (binding for #2981)

| # | Decision |
|---|---|
| 1 | **LR-050 operator-receipt proof runs through Grafana SMTP Test Notification** to the operator human inbox. |
| 2 | **Alertmanager internal webhook routing** (`default-receiver`, `critical-receiver`, `high-priority-receiver`, `trading-halt-receiver` → `cdb_signal:8005/alerts/*`) **does not** count as operator receipt. |
| 3 | **LR-030 synthetic Alertmanager API proof** (`reports/lr030/.../synthetic_alert_proof_summary.json`) **does not** count as LR-050 operator receipt. |
| 4 | **Real secret values** are verified **only locally by the operator** under `SECRETS_PATH`; agents must not read, echo, or commit SMTP credentials or `ALERT_EMAIL_TO`. |
| 5 | **Prometheus → Alertmanager** remains the documented path for infrastructure alert **rules**; it is **not** the canonical LR-050 **operator paging** proof channel for #2981. |

---

## Receiver Class

| Field | Value |
|---|---|
| **Canonical receiver class** | `grafana-smtp-operator` |
| **Human channel** | Operator email inbox (destination configured via local `ALERT_EMAIL_TO` secret — never committed) |
| **Stack anchor** | Grafana in [`compose.red.yml`](../../infrastructure/compose/compose.red.yml) with `GF_SMTP_*` + Docker secrets `smtp_user`, `smtp_password`, `smtp_from`, `alert_email_to` |
| **Not in scope for proof** | Alertmanager webhook ingest, internal service logs as sole proof |

---

## Operator Inputs (before Operator-GO test)

Operator verifies locally (**agent does not read values**):

| Input | Secret / config name | Required? |
|---|---|---|
| SMTP user | `SMTP_USER` in `SECRETS_PATH` | **Yes** |
| SMTP password | `SMTP_PASSWORD` in `SECRETS_PATH` | **Yes** |
| SMTP from address | `SMTP_FROM` in `SECRETS_PATH` | **Yes** |
| Operator inbox destination | `ALERT_EMAIL_TO` in `SECRETS_PATH` | **Yes** |
| Grafana admin access | `GRAFANA_PASSWORD` in `SECRETS_PATH` | **Yes** (local UI only) |
| Grafana email contact point | UI contact point bound to SMTP; routes to operator inbox | **Yes** — operator confirms configured or configures under GO |

Cross-ref [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983): SMTP/alert credential readiness is a **separate** gate; #2981 proof may proceed when operator attests these four SMTP-related files exist and Grafana contact point works — without publishing values.

---

## Test Method (Operator-GO slice only — not executed by this document)

| Step | Action |
|---|---|
| 1 | Operator-GO: non-destructive RED stack up (`MOCK_TRADING` / `DRY_RUN` unchanged on trading path). |
| 2 | Operator opens Grafana (`http://localhost:3000`, local bind). |
| 3 | Operator uses **Test notification** on the email contact point used for LR-050 proof (preferred — minimal blast radius). |
| 4 | Operator confirms notification received on human inbox. |
| 5 | Operator (or scoped agent under GO) commits **redacted** evidence per format below. |

**Forbidden as sole proof:** Alertmanager API v2 direct POST; webhook delivery to `cdb_signal`; Prometheus alert firing without human-channel receipt.

**Suggested proof labels in evidence:** `alertname`: `CDB-LR050-ReceiverProofTest`; `test_method`: `grafana_test_notification`.

---

## Evidence Format

**Directory:** `reports/lr050/receiver_proof/YYYY-MM-DD/`

| File | Required? | Content |
|---|---|---|
| `manifest.json` | **Yes** | Structured metadata (schema below) |
| `operator_attestation.md` | **Yes** | Redacted operator statement: receipt confirmed, UTC times, channel class |
| `summary.md` | Recommended | Human-readable summary; explicit NO-GO / not Live-Go |
| `redacted_screenshot.sha256` | Optional | Hash only if screenshot stored outside repo |

### `manifest.json` minimum schema

```json
{
  "proof_type": "lr050_operator_receiver_proof",
  "issue": "2981",
  "canon_ref": "docs/live-readiness/LR-050-RECEIVER-PROOF-CANON-2026-07-03.md",
  "receiver_class": "grafana-smtp-operator",
  "test_method": "grafana_test_notification",
  "alertname": "CDB-LR050-ReceiverProofTest",
  "severity": "critical",
  "proof_ts_utc": "2026-07-03T12:00:00Z",
  "receipt_ts_utc": "2026-07-03T12:00:05Z",
  "lr_verdict_at_proof": "NO-GO",
  "live_go": false,
  "echtgeld_go": false,
  "operator_attestation_ref": "operator_attestation.md",
  "redaction_policy": "LR-050-RECEIVER-PROOF-CANON-2026-07-03.md",
  "notes": "LR-050 canary readiness only. Does not clear LR-050 or authorize live capital."
}
```

Aligns with [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §4.4 fields 1–5.

---

## Redaction Rules (mandatory)

| Allowed in repo | Forbidden in repo |
|---|---|
| UTC timestamps (test + receipt) | Email addresses (`ALERT_EMAIL_TO`, from, to, SMTP user) |
| Receiver class `grafana-smtp-operator` | SMTP passwords, API tokens, webhook URLs with secrets |
| `alertname`, `severity`, `test_method` | Full email body with PII or host-specific secrets |
| Operator attestation text (no PII) | Grafana admin password |
| SHA-256 of redacted screenshot (optional) | Raw notification headers with addresses |

Replace forbidden fields with `[REDACTED_OPERATOR_CHANNEL]` or `[REDACTED_SECRET]`.

---

## Acceptance Criteria (Operator-GO test — closes #2981 only when all met)

| # | Criterion |
|---|---|
| 1 | **Timestamp** — `proof_ts_utc` and `receipt_ts_utc` in evidence |
| 2 | **Receiver class name** — `grafana-smtp-operator` in manifest |
| 3 | **Redacted operator attestation** — human receipt confirmed, no PII |
| 4 | **Test method** — `grafana_test_notification` documented |
| 5 | **No Live-Go** — manifest and attestation state LR **NO-GO**; no live-capital authorization |
| 6 | **Evidence on `main`** — under `reports/lr050/receiver_proof/YYYY-MM-DD/` |

Until all six are satisfied, #2981 remains **OPEN**.

---

## Readiness After This Canon

| Question | Answer |
|---|---|
| Is canonical path defined? | **Yes** — this document |
| Is Operator-GO test possible next? | **Yes** — **`READY_FOR_OPERATOR_RECEIVER_TEST`** once operator confirms local SMTP secrets + Grafana contact point (no agent secret read) |
| Does this close #2981? | **No** |
| Does this clear LR-050? | **No** — **NO-GO** unchanged |
| #2984 unblocked? | **Partially** — receiver proof evidence still required before kill-switch drill evidence |

---

## Excluded Paths (explicit)

### Alertmanager internal webhooks

[`alertmanager.yml`](../../infrastructure/monitoring/alertmanager.yml) routes to
`http://cdb_signal:8005/alerts/*`. Per OBSERVABILITY-GATES §3, internal ingest is
**not** operator receipt. Signal service exposes `/health`, `/status`, `/metrics` only.

### LR-030 synthetic Alertmanager proof

`reports/lr030/2026-05-17/synthetic_alert_proof_summary.json` — AM API direct post to
`default-receiver` — shadow/soak scope only; **not** LR-050 canary operator proof.

---

## Cross-References

| Document | Relationship |
|---|---|
| [`LR-050-RECEIVER-PROOF-PREFLIGHT-2026-07-03.md`](./LR-050-RECEIVER-PROOF-PREFLIGHT-2026-07-03.md) | Preflight inventory; channel gap closed by this canon |
| [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) | Proof hierarchy §3; operator receipt definition §4.4 |
| [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) | Alert credential gate matrix (#2530 / #2983) |
| [`ALERTING_DIGEST_FIX.md`](../operations/ALERTING_DIGEST_FIX.md) | Grafana notification policy ops notes |

---

## Document Metadata

| Field | Value |
|---|---|
| Issue | [#2981](https://github.com/jannekbuengener/Claire_de_Binare/issues/2981) |
| Refs | [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983), [#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984), PR [#3709](https://github.com/jannekbuengener/Claire_de_Binare/pull/3709) |
| Status target | `DONE_LR050_RECEIVER_PROOF_CANON` |
| LR verdict | **NO-GO** (unchanged) |
