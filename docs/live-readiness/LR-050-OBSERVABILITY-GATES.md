# LR-050 Observability Gates — Live-Canary Monitoring and Alert Gates

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531)
- **Document role:** Repo-backed SSOT for Prometheus/Alertmanager/receiver **readiness**, abort vs investigate **policy classes**, receiver proof requirements, and canary verification matrix (**gate definition only — not activation**)
- **Last updated:** 2026-06-04
- **Companion:** [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md), [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md), [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md), [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md), [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md)
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit Human Approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Merge of PR that adds this document | **Documentation only** — ersetzt **niemals** Human Approval |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Runtime / receiver actions via this document | **None** — no stack commands, no test alerts, no orders |

---

## 1. Scope and non-goals

### In scope

- Define monitoring readiness layers: Prometheus, Alertmanager, receiver routes, operator receiver proof.
- Classify canary alert gates: **abort** (policy halt class), **investigate** (observe/escalate, no live GO), **blocker_before_live** (missing LR-050 proof or mechanism).
- Map repo-present rules/config to gates without claiming LR-050 canary delivery proof.
- Hand off proof obligations to [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) (Canary Plan) and [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (Dry-run Proof).

### Non-goals

- No change to [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md), `ROADMAP.yaml`, services, compose, or monitoring config files.
- No Prometheus/Alertmanager/Grafana runtime validation, receiver test messages, or ServiceDown simulation.
- No receiver URLs, webhook targets, SMTP hosts, tokens, or operator contact addresses in this document.
- No replacement of [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) (kill-switch runbook) or [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) (secrets).

---

## 2. Related documents and dependencies

| Document / issue | Relationship |
|------------------|--------------|
| [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) | §7 Monitoring — this SSOT |
| [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) | Outage / fill-rate policy pointers |
| [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) | Manual halt when alerts unevaluable |
| [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) | Venue/exchange path inventory ([#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527)) |
| [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) | Alert credential names; receiver proof |
| [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | Canary Plan — SSOT: [LR-050-CANARY-PLAN.md](./LR-050-CANARY-PLAN.md) (`plan_only`, not executable) |
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | Dry-run — non-destructive gate checks only |
| [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | Final LR reconcile after child SSOTs |
| [`infrastructure/monitoring/alerts.yml`](../../infrastructure/monitoring/alerts.yml) | Prometheus alert rules (read-only reference) |
| [`infrastructure/monitoring/alertmanager.yml`](../../infrastructure/monitoring/alertmanager.yml) | Route/receiver names (read-only reference) |
| [`infrastructure/monitoring/METRICS_MATRIX.md`](../../infrastructure/monitoring/METRICS_MATRIX.md) | Metric inventory |
| [`knowledge/operations/ALERTING_RUNBOOK.md`](../../knowledge/operations/ALERTING_RUNBOOK.md) | Ops procedures — **not** executed by this issue |

---

## 3. Proof hierarchy (mandatory — do not conflate)

| Observation | Counts as LR-050 receiver proof? |
|-------------|----------------------------------|
| Grafana dashboard panel visible | **No** |
| Prometheus target `up` / scrape success | **No** |
| Prometheus alert `firing` in UI/API | **No** — not Alertmanager delivery proof |
| Alertmanager route/receiver config present | **No** — not operator receipt proof |
| Grafana Unified Alerting rule fires | **No** — not Alertmanager delivery proof |
| Internal receiver (e.g. service ingest webhook) delivers to app | **No** — signal ingest only, not operator receipt |
| Repo-backed **operator receipt evidence** (redacted attestation artifact) | **Yes** — only this class clears `receiver proof required: yes` rows |

**Rule:** No alert route is **live-ready** for LR-050 canary until a **repo-backed operator receipt proof** exists for that route class (separate from this gate-definition PR).

---

## 4. Readiness layers

### 4.1 Prometheus readiness

| Check | Repo anchor | LR-050 status |
|-------|-------------|---------------|
| Alert rules file committed | [`infrastructure/monitoring/alerts.yml`](../../infrastructure/monitoring/alerts.yml) | `config_present` |
| Critical canary alertnames defined | `ServiceDown`, `DatabaseConnectionLost`, `CircuitBreakerTriggered`, `PrometheusTargetDown`, … | `config_present` (subset) |
| Scrape/target health at runtime | Prometheus TSDB/targets API | `blocker_before_live` — requires runtime GO, not this issue |
| Canary-specific alerts (fills, mode drift, stale-data alert rules) | Not in `alerts.yml` | `blocker_before_live` |

**Fail-closed:** If Prometheus cannot attest targets/alerts during a canary window, treat as **unevaluable monitoring** → operator manual halt, no new live-capital orders, global **NO-GO** unchanged.

### 4.2 Alertmanager readiness

| Check | Repo anchor | LR-050 status |
|-------|-------------|---------------|
| Route tree + receivers defined | [`infrastructure/monitoring/alertmanager.yml`](../../infrastructure/monitoring/alertmanager.yml) | `config_present` |
| Named receivers | `default-receiver`, `critical-receiver`, `high-priority-receiver`, `trading-halt-receiver` | `config_present` (names only) |
| Operator external channel (email/pager/SMS) | SMTP block commented; no production operator receiver in repo | `blocker_before_live` |
| Delivery to operator at runtime | Alertmanager notification log / receipt | `blocker_before_live` |

**Fail-closed:** Alertmanager unavailable or delivery unverified → **no** live-capital GO; halt new risk-on orders per [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md).

### 4.3 Receiver route readiness

| Route class | Match / alert | Purpose (repo intent) | Operator receipt proof |
|-------------|---------------|----------------------|-------------------------|
| `critical-receiver` | `severity: critical` | Critical path notification | **Required** — `blocker_before_live` |
| `trading-halt-receiver` | `alertname: CircuitBreakerTriggered` | Trading halt signal ingest | **Required** — `blocker_before_live` |
| `high-priority-receiver` | `severity: high` | Elevated notifications | **Required** for canary |
| `default-receiver` | default route | Fallback notifications | **Required** for canary |
| Internal ingest webhooks | All above receivers use in-cluster webhook configs | Application alert ingest | **Not** operator proof |

Crosslink: credential names → [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md); halt actions → [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md).

### 4.4 Receiver proof requirement (definition)

A valid **LR-050 operator receipt proof** MUST document (in a future evidence file under `reports/` or `docs/evidence/`, not in this PR):

1. **UTC timestamp** of test or real incident notification.
2. **Alertname** and **severity** (or Grafana rule title if explicitly in canary plan).
3. **Receiver class** (e.g. `critical-receiver`) — name only, no secrets.
4. **Operator attestation** that the notification was received on the human channel (redacted screenshot hash, ticket ID, or signed operator note).
5. Explicit statement: this proof is for **LR-050 canary readiness**, not P5 prestart-only shadow.

Until such an artifact exists on `main`, all rows with `receiver proof required: yes` remain **`blocker_before_live`**.

Historical shadow digest material under `reports/shadow_mode/` is **not** LR-050 live-capital canary proof.

---

## 5. Alert policy classes (abort vs investigate)

| Class | Meaning for LR-050 canary | Grants live GO? |
|-------|---------------------------|-----------------|
| **abort** | Operator policy: **halt new live-capital orders**, invoke kill-switch/runbook, consider REVOKED path. Does **not** assert automated halt is wired or receiver-delivered unless separately proven. | **No** |
| **investigate** | Observe, triage, escalate; may continue only under explicit Human Approval and canary plan constraints. | **No** |
| **blocker_before_live** | Gate not satisfied for live-capital canary (missing rule, threshold, proof, or runtime verification). | **No** |

**Soak-test labels** in `alerts.yml` (`soak_test: abort` / `investigate`) inform shadow/soak policy; they do **not** auto-clear `LR-050` without canary-specific operator proof.

---

## 6. Monitoring stack duality (Grafana vs Alertmanager)

| Channel | Repo anchor | Canary note |
|---------|-------------|-------------|
| Prometheus → Alertmanager | `alerts.yml` + `alertmanager.yml` | Primary **documented** path for `ServiceDown`, `DatabaseConnectionLost`, `CircuitBreakerTriggered` |
| Grafana Unified Alerting | `infrastructure/monitoring/grafana/provisioning/alerting/*.yml` | e.g. high rejection rate, orders rejected, circuit breaker — **parallel** path |
| Operator notification | Grafana notification policies (see shadow reports) vs Alertmanager receivers | **blocker_before_live** until #2532 names canonical operator channel |

Canary Plan ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532)) MUST declare which channel is authoritative for operator paging during live-capital canary.

---

## 7. Gate topics (summary)

### 7.1 Infrastructure and trading halt signals

| Gate | Repo mechanism | Policy class | Notes |
|------|----------------|--------------|-------|
| **ServiceDown** | `alerts.yml` → `severity: critical` | **abort** (policy) | `config_present`; route to `critical-receiver`; proof `blocker_before_live` |
| **DatabaseConnectionLost** | `alerts.yml` → `severity: critical` | **abort** (policy) | Same |
| **PrometheusTargetDown** | `alerts.yml` → `severity: warning` | **investigate** | If sole visibility → fail-closed escalate to abort policy |
| **CircuitBreakerTriggered** | `alerts.yml` + `trading-halt-receiver` | **abort** (policy) | In-memory CB metric; not file Kill Switch — see kill-switch runbook |
| **RedisConnectionLost** | `alerts.yml` critical | **abort** (policy) | Order-flow risk |

### 7.2 Trading / execution anomalies

| Gate | Repo mechanism | Policy class | Notes |
|------|----------------|--------------|-------|
| **Unexpected fills** | No dedicated Prometheus alert; execution fill metrics in METRICS_MATRIX | **blocker_before_live** | Policy **abort** once canary thresholds + alert exist ([#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532)) |
| **Rejected order spike** | Grafana: `high_error_rate`, `orders_rejected`; counters in metrics | **investigate** default; canary threshold TBD | Spike definition → #2532; not live-ready without proof |
| **Shadow/live mode drift** | Runtime mode contract (P5); `execution_shadow_blocked_total` metric | **blocker_before_live** | No `shadow/live drift` alert in `alerts.yml` |
| **Latency** | No LR-050 alert rule in monitoring config | **blocker_before_live** | Generic app paths may exist; canary SLO TBD |
| **Slippage** | Risk `DECISION_THRESHOLDS` / `decide_trade` block path — not Prometheus alert | **blocker_before_live** (canary alert); enforceable in app | See risk limits |
| **Stale market data** | Risk staleness/silence thresholds in `services/risk/service.py` — not stale-data Prometheus alert | **blocker_before_live** (canary-specific alerting) | App **enforceable_now** for generic block; canary alert proof missing |

### 7.3 Kill-switch alert route

| Gate | Repo mechanism | Policy class | Notes |
|------|----------------|--------------|-------|
| **Kill-switch alert route** | `trading-halt-receiver` for `CircuitBreakerTriggered`; **no** alert on `risk_kill_switch_active` | **abort** (policy) + **blocker_before_live** (file KS + operator proof) | Manual halt: kill-switch runbook; metric gap documented there |

---

## 8. Behavior when monitoring is impaired

| Condition | Operator policy (fail-closed) | Receiver proof |
|-----------|--------------------------------|----------------|
| **Prometheus unavailable** | Halt new live-capital orders; manual kill-switch; stay **NO-GO** | n/a — cannot fire/attest |
| **Alertmanager unavailable** | Same; do not assume Grafana alone satisfies canary | n/a |
| **Receiver unverified** | Treat as **blocker_before_live**; no live-capital GO | Missing |
| **Dashboard-only visibility** | **Investigate** at best; **not** sufficient for canary; escalate to manual halt if trading | **No** proof |

Align with [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) (Alertmanager/Prometheus outage row) and [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) (unevaluable monitoring).

---

## 9. Prüfbarkeits-Matrix (canary gates)

Legend — **blocker status:** `docs_only` | `config_present` | `blocker_before_live` | `enforceable_now` (app/runtime mechanism only; does **not** imply operator delivery or live-ready).

| Gate | Source / mechanism | Expected signal | Alert class | Receiver proof required | Verification method | Runtime action required | Blocker status | Fail-closed behavior |
|------|-------------------|-----------------|-------------|-------------------------|---------------------|-------------------------|----------------|----------------------|
| Prometheus rules committed | `infrastructure/monitoring/alerts.yml` | Alertnames evaluable when Prometheus up | investigate | no | Repo file review | no | `config_present` | Unevaluable → halt, NO-GO |
| Prometheus scrape health | Prometheus targets API | `up==1` for canary jobs | investigate | no | Runtime target check (#2533 / separate GO) | yes | `blocker_before_live` | Missing targets → treat as outage |
| Alertmanager config | `alertmanager.yml` | Routes/receivers loaded | investigate | no | Repo file review | no | `config_present` | AM down → halt policy |
| Operator receiver proof | Evidence artifact (future) | Human receipt for test alert | abort | yes | Redacted attestation on `main` | yes | `blocker_before_live` | No proof → no live GO |
| **ServiceDown** | Prometheus rule + `critical-receiver` | `up==0` for `cdb_*` job | abort | yes | Rule review + delivery proof | yes (drill) | `config_present` + proof blocker | Policy halt; proof required |
| **DatabaseConnectionLost** | Prometheus `pg_up==0` | DB exporter down | abort | yes | Rule review + delivery proof | yes (drill) | `config_present` + proof blocker | Policy halt |
| **PrometheusTargetDown** | Prometheus rule | Scrape failure | investigate | no | Rule review; runtime scrape | yes | `config_present` | Escalate if sole signal |
| **CircuitBreakerTriggered** | Prometheus + `trading-halt-receiver` | `circuit_breaker_active==1` | abort | yes | Rule + AM route review + proof | yes (drill) | `config_present` + proof blocker | Policy halt; not file KS |
| **RedisConnectionLost** | Prometheus critical | `redis_up==0` | abort | yes | Rule review + proof | yes (drill) | `config_present` + proof blocker | Policy halt |
| **Unexpected fills** | No canary alert rule | Fill rate vs plan | abort | yes | #2532 thresholds + future rule | yes | `blocker_before_live` | Halt + REVOKED path |
| **Rejected order spike** | Grafana `high_error_rate`, `orders_rejected` | Reject rate / count | investigate | yes | Grafana provisioning review + proof | yes | `config_present` + proof blocker | Escalate; threshold in #2532 |
| **Shadow/live mode drift** | P5 mode contract; metrics | Mode != approved | abort | yes | #2532 plan + runtime check | yes | `blocker_before_live` | Halt if drift |
| **Latency (canary SLO)** | Not in alert rules | Latency over cap | investigate | yes | #2532 defines SLO | yes | `blocker_before_live` | Escalate / halt per plan |
| **Slippage (canary)** | Risk `decide_trade` thresholds | BLOCK on slippage RC | abort | no | Unit tests; dry-run #2533 | no (unit) / yes (e2e) | `enforceable_now` (app); alert `blocker_before_live` | Block in app; alert TBD |
| **Stale market data (canary alert)** | Risk staleness/silence | BLOCK or missing ts | abort | yes | Unit tests; canary alert TBD | partial | `enforceable_now` (app); alert `blocker_before_live` | Block in app |
| **Kill-switch alert route** | `trading-halt-receiver` | CB alert to ingest | abort | yes | Route name review + proof | yes | `config_present` + proof blocker | Manual KS always available |
| **File Kill Switch metric alert** | `risk_kill_switch_active` gauge; no matching alert | Gauge `==1` | abort | yes | METRICS_MATRIX; no alert in alerts.yml | yes | `blocker_before_live` | Use manual KS + CB alert gap |
| Grafana circuit breaker alert | `grafana/.../circuit_breaker.yml` | Grafana firing | investigate | yes | Repo provisioning | yes | `config_present` + proof blocker | Not AM delivery proof |
| TradePipelineStalled | `alerts.yml` warning | Pipeline stall | investigate | no | Rule review | yes | `config_present` | Investigate; may halt per #2532 |
| Monitoring outage | Policy (this §8) | AM/Prom down | abort | no | Operator attestation | yes | `docs_only` | Halt new orders, NO-GO |
| Dashboard-only ops | Policy | Visual only | investigate | no | N/A | no | `docs_only` | Insufficient for GO |

---

## 10. Handoff — [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) Canary Plan

The Canary Plan **MUST** include:

1. Authoritative operator notification channel (Alertmanager vs Grafana).
2. Every **abort**-class gate above as a **stop criterion** with numeric thresholds where applicable (fills, reject spike, mode drift, slippage, stale data).
3. Explicit listing of receivers requiring **operator receipt proof** before live-capital window starts.
4. Escalation from **investigate** to manual halt (no auto-live).
5. Reference to [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) — plan does not grant GO.

---

## 11. Handoff — [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) Dry-run Proof

SSOT: [`LR-050-DRY-RUN-PROOF.md`](./LR-050-DRY-RUN-PROOF.md) (`dry_run_proof_contract`, `docs_only`; **runtime evidence not executed**).

**May** prove without real money or receiver tests (repo/CI bounded):

- Config resolution references correct alert files.
- Metric endpoints expose expected series names (read-only scrape in test env).
- Risk/execution gates block with `real_money=false` / shadow mode.

**Must NOT** be claimed in #2533 alone:

- Alertmanager delivery to operator.
- ServiceDown simulation on production stack.
- Receiver test messages or webhook/SMTP drills.

Those require **separate Runtime-GO** after Human Approval path is clear.

---

## 12. Handoff — runtime-only (explicit non-goals for #2531)

| Action | Allowed in #2531? |
|--------|-------------------|
| `docker exec` / Prometheus API queries on live stack | **No** |
| Alertmanager UI test fire / `TestAlert` POST | **No** |
| Stop `cdb_*` for ServiceDown drill | **No** |
| Webhook/SMTP/pager test | **No** |
| Live or canary orders | **No** |

---

## 13. Restunsicherheiten

1. **Dual notification stack:** Grafana vs Alertmanager operator path not canonically chosen for LR-050 canary.
2. **Internal webhooks:** Receivers deliver to in-cluster ingest; operator paging not repo-proven.
3. **File Kill Switch vs CB alert:** `CircuitBreakerTriggered` does not cover `risk_kill_switch_active` / file state.
4. **Historical shadow alerting evidence** (`reports/shadow_mode/`) — informative only, not LR-050 canary proof.
5. **Canary numeric thresholds** for reject spike, fills, latency — TBD in #2532.

---

## 14. Closing statement

Delivery of this document closes **gate definition** for [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) only. It does **not**:

- Change global `LR-050` verdict (**NO-GO** remains).
- Grant live-capital GO or Echtgeld-Go.
- Replace Human Approval ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534)).
- Mark any alert route live-ready without operator receipt proof.
