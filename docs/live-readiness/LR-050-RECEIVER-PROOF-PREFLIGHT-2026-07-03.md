# LR-050 Receiver Proof Preflight — Operator Receipt (#2981)

## Purpose

Read-only preflight for [#2981](https://github.com/jannekbuengener/Claire_de_Binare/issues/2981):
identify how Alertmanager / monitoring receiver proof can be executed **safely** and
**redacted**, without Live-Go, trading, or secret exposure in repo artifacts.

This document does **not** trigger alerts, start Docker, or close #2981.

## Scope

In scope:

- Repo-backed inventory of alert/receiver paths relevant to LR-050 operator receipt.
- Safe test design, redaction rules, and evidence format for a future Operator-GO slice.
- Preflight decision for #2981.

Out of scope:

- No alert firing, no Docker, no runtime restart.
- No secret reads or values in repo/chat/PR.
- No Live-Go, Echtgeld-Go, LR status change, or #2981 closure.

## Control State

| Surface | State |
|---|---|
| LR-050 verdict | **NO-GO** ([`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)) |
| Blocker row | Operator Receiver Proof missing — [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md) §3 |
| Refresh matrix | [`LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md`](./LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md) row 2 → #2981 **OPEN** |
| Gate SSOT | [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §3–§4 |
| Downstream | [#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984) kill-switch drill **depends on** receiver proof |
| Preflight date | 2026-07-03 |
| Repo anchor | `origin/main` @ preflight session |

---

## Preflight Decision

| Field | Value |
|---|---|
| **Decision** | **`BLOCKED_NEEDS_CONFIG`** |
| Secondary gate | **`BLOCKED_NEEDS_SECRET_CONTEXT`** (for execution only — operator verifies SMTP secrets locally) |
| Operator-GO required for test? | **Yes** — stack interaction + human receipt attestation |
| #2981 status after preflight | **Stays OPEN** — no evidence artifact on `main` |

### Why not `READY_FOR_OPERATOR_RECEIVER_TEST`

Repo config is **not** ready for a clean LR-050 operator-receipt run without prior
operator decisions and small config fixes:

1. **Alertmanager not in default RED stack** — `compose.red.yml` runs Prometheus +
   Grafana but **not** `cdb_alertmanager`. Alertmanager lives in
   [`logging.yml`](../../infrastructure/compose/logging.yml) overlay only.
   Prometheus [`prometheus.yml`](../../infrastructure/monitoring/prometheus.yml) targets
   `cdb_alertmanager:9093`, which is unreachable when AM container is absent.
2. **Alertmanager receivers have no external operator channel** —
   [`alertmanager.yml`](../../infrastructure/monitoring/alertmanager.yml): SMTP block
   commented; all named receivers use **internal webhooks only**.
3. **Webhook targets appear unwired** — receivers POST to
   `http://cdb_signal:8005/alerts{,/critical,/high,/trading-halt}`, but
   [`services/signal/service.py`](../../services/signal/service.py) exposes only
   `/health`, `/status`, `/metrics` (no `/alerts` routes). Internal ingest ≠ operator
   receipt per [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §3.
4. **Canonical LR-050 operator channel undeclared** — OBSERVABILITY-GATES §6: Grafana
   vs Alertmanager duality; canary plan must name authoritative paging path ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) /
   #2976 context).
5. **Grafana notification policies not fully repo-provisioned** — alert rules exist under
   `infrastructure/monitoring/grafana/provisioning/alerting/`, but contact points /
   notification routing are partly UI-managed ([`ALERTING_DIGEST_FIX.md`](../operations/ALERTING_DIGEST_FIX.md)).

### Why not `INCONCLUSIVE`

Repo evidence is sufficient to name blockers and a recommended proof path. Gaps are
specific and actionable.

### Why `BLOCKED_NEEDS_SECRET_CONTEXT` (execution prerequisite)

Grafana SMTP delivery (recommended path below) requires operator-local secrets via
`SECRETS_PATH`: `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `ALERT_EMAIL_TO`
([`compose.red.yml`](../../infrastructure/compose/compose.red.yml)). Agent must not
read or commit these values.

---

## Receiver Inventory (repo read-only)

### A. Alertmanager path (Prometheus → Alertmanager)

| Item | Repo state | LR-050 operator receipt? |
|---|---|---|
| Config | [`alertmanager.yml`](../../infrastructure/monitoring/alertmanager.yml) | Config present only |
| Named receivers | `default-receiver`, `critical-receiver`, `high-priority-receiver`, `trading-halt-receiver` | Names only |
| Delivery mechanism | Webhooks → `cdb_signal:8005/alerts/*` | **Not** operator proof |
| External email/SMS | Commented placeholders | **Not configured** |
| Runtime in RED | Not in `compose.red.yml` | **Gap** — overlay or stack change needed |
| Historical proof | LR-030 synthetic AM API post (`reports/lr030/.../synthetic_alert_proof_summary.json`) | **Not** LR-050 operator receipt (internal route only) |

### B. Grafana Unified Alerting path (recommended for #2981 slice)

| Item | Repo state | LR-050 operator receipt? |
|---|---|---|
| Alert rules (provisioned) | `circuit_breaker.yml`, `high_error_rate.yml`, `orders_rejected.yml` | Rules present; not proof |
| SMTP in RED compose | `GF_SMTP_*` + secrets `smtp_user`, `smtp_password`, `smtp_from`, `alert_email_to` | **Candidate human channel** when secrets valid |
| Notification contact points | UI-managed per ops docs | Operator must verify/configure under GO |
| Operator inbox delivery | Requires runtime + secrets | **Valid proof class** if attested redacted |

### C. Harvester local alerts (not in scope for #2981)

Harvester `alerts.py` produces local gap reports (`manual_escalation_only`) — does
**not** satisfy Alertmanager/operator receipt per evidence mapping (#3680).

---

## Proof Hierarchy (mandatory)

From [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §3:

| Observation | Counts for #2981? |
|---|---|
| Prometheus alert firing | **No** |
| Alertmanager UI shows alert | **No** |
| Webhook delivered to `cdb_signal` | **No** — ingest only |
| Operator receives notification on **human channel** + redacted attestation on `main` | **Yes** |

---

## Recommended Path (after config unblock)

### Step 0 — Operator planning (before Runtime-GO)

1. **Declare canonical channel for this proof:** Grafana SMTP → operator inbox
   (receiver class name in evidence: `grafana-smtp-operator`).
2. Confirm Grafana contact point routes **critical** test alerts to email (UI check;
   no repo commit of addresses).
3. Decide whether Alertmanager path will be fixed in a **separate** follow-up (webhook
   wiring + AM in stack + external receiver) — not required to defer #2981 if Grafana
   path is declared canonical for LR-050 canary readiness.

### Step 1 — Operator-GO preconditions

- Explicit Operator-GO for non-destructive RED stack use (`MOCK_TRADING=true`,
  `DRY_RUN=true` on trading path unchanged).
- `SECRETS_PATH` populated; operator confirms SMTP + `ALERT_EMAIL_TO` locally (**agent
  does not read files**).
- BLUE + RED running; Grafana reachable at `http://localhost:3000` (local bind).
- No live-capital flags; LR remains **NO-GO**.

### Step 2 — Safe synthetic test (Operator executes)

**Preferred:** Grafana **Test notification** on the email contact point tied to a
**paused** or dedicated LR-050 proof alert rule — avoids production spam.

**Alternative (higher blast radius):** Short-lived firing of provisioned rule
`CDB - Circuit Breaker Activated` with `for:` window and immediate resolve — only with
Operator-GO and digest policy understood ([`ALERTING_DIGEST_FIX.md`](../operations/ALERTING_DIGEST_FIX.md)).

**Do not use alone:** LR-030-style Alertmanager API v2 direct POST to `default-receiver`
— does not prove human operator receipt for LR-050.

### Step 3 — Operator receipt capture

Operator confirms notification received on human channel (email client / mobile — not
repo). Record UTC receipt time independently of mail headers in evidence if headers
contain PII.

### Step 4 — Commit redacted evidence

See Evidence Format below. Post summary comment on #2981; close #2981 only when artifact
is on `main` and acceptance criteria met.

---

## Redaction Rules (mandatory)

| Field | In repo evidence? |
|---|---|
| UTC timestamp of test / receipt | **Yes** |
| `alertname` / Grafana rule title | **Yes** |
| `severity` label | **Yes** |
| Receiver class name (e.g. `grafana-smtp-operator`, `critical-receiver`) | **Yes** — name only |
| Run ID / proof slice label (e.g. `lr050-receiver-proof-20260703`) | **Yes** |
| Operator attestation text (no PII) | **Yes** |
| SHA-256 of redacted screenshot | **Yes** (optional) |
| Email addresses (`ALERT_EMAIL_TO`, from, to, SMTP user) | **No** — replace with `[REDACTED_OPERATOR_CHANNEL]` |
| SMTP passwords, API tokens, webhook URLs with secrets | **No** |
| Full email body / screenshot with addresses or host-specific secrets | **No** — hash or paraphrase only |
| Grafana admin password | **No** |
| Instance hostnames if sensitive | Paraphrase or redact |

---

## Evidence Format (target)

**Directory:** `reports/lr050/receiver_proof/YYYY-MM-DD/`

**Files:**

| File | Content |
|---|---|
| `manifest.json` | Structured proof metadata (see schema below) |
| `operator_attestation.md` | Short operator-signed note: receipt confirmed, channel class, UTC time |
| `redacted_screenshot.sha256` | Optional hash of redacted screenshot stored **outside** repo if needed |
| `summary.md` | Human-readable summary + explicit NO-GO / not Live-Go statement |

**`manifest.json` schema (minimum):**

```json
{
  "proof_type": "lr050_operator_receiver_proof",
  "issue": "2981",
  "lr_verdict_at_proof": "NO-GO",
  "live_go": false,
  "echtgeld_go": false,
  "channel_class": "grafana-smtp-operator",
  "alertname": "CDB-LR050-ReceiverProofTest",
  "severity": "critical",
  "test_method": "grafana_test_notification",
  "proof_ts_utc": "2026-07-03T12:00:00Z",
  "receipt_ts_utc": "2026-07-03T12:00:05Z",
  "operator_attestation_ref": "operator_attestation.md",
  "redaction_policy": "LR-050-OBSERVABILITY-GATES.md §4.4 + LR-050-RECEIVER-PROOF-PREFLIGHT-2026-07-03.md",
  "notes": "LR-050 canary readiness only. Does not clear LR-050 or authorize live capital."
}
```

Must satisfy [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) §4.4
fields 1–5.

---

## Config Unblock Checklist (before Operator-GO test)

| # | Action | Owner |
|---|---|---|
| 1 | Declare Grafana SMTP as canonical LR-050 operator channel for this proof (document in #2981 comment or canary plan) | Operator |
| 2 | Verify Grafana email contact point + test notification works locally | Operator |
| 3 | Confirm `SECRETS_PATH` SMTP secrets present (no values in repo) | Operator |
| 4 | (Optional follow-up) Add Alertmanager to stack or fix AM→signal webhook wiring + external receiver | Separate issue / scope |
| 5 | Execute Operator-GO test slice; commit redacted evidence | Operator + scoped agent docs commit |

When items 1–3 are done and Operator-GO granted → decision upgrades to
**`READY_FOR_OPERATOR_RECEIVER_TEST`**.

---

## Relationship to #2984

[#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984) requires
kill-switch drill with **alerting observed** (kill-switch event reaches receiver).
That drill **depends on** #2981-style operator receipt proof. Completing #2981 via
Grafana operator channel does not automatically prove Alertmanager `trading-halt-receiver`
— #2984 may need correlated alert observation on the same or declared canonical channel.

---

## Validation (this preflight slice)

```powershell
git fetch origin --prune
git status -sb
git rev-parse origin/main
gh issue view 2981 2984 2977
rg "Alertmanager|receiver|alert|operator receipt|2981|2984|LR-050" docs infrastructure services .github
```

Content review:

- No alert triggered in this slice.
- No secrets read or written.
- No Live-Go / Echtgeld-Go language.

---

## Document Metadata

| Field | Value |
|---|---|
| Issue | [#2981](https://github.com/jannekbuengener/Claire_de_Binare/issues/2981) |
| Refs | [#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984), [#2977](https://github.com/jannekbuengener/Claire_de_Binare/issues/2977) (CLOSED) |
| Status target | `DONE_LR050_RECEIVER_PROOF_PREFLIGHT` |
| LR verdict | **NO-GO** (unchanged) |
