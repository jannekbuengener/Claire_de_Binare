# LR-050 Live-Capital Readiness Decision Pack

- **Control:** `LR-050` (P5 Canary Echtgeld)
- **GitHub plan issue:** [#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526)
- **Document role:** Human-reviewable decision pack for a future controlled live-capital / crypto canary
- **Last updated:** 2026-06-03
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit human live approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Secrets in this document | **None** |
| Orders / runtime mutation via this document | **None** |

Human Gate **GRANTED 2026-04-04** applies to the **P5 prestart / shadow-stability pack only**, not to live-capital canary. Repo anchor: [`reports/p5_canary/2026-04-04/decision_record.yaml`](../../reports/p5_canary/2026-04-04/decision_record.yaml), Issue [#1445](https://github.com/jannekbuengener/Claire_de_Binare/issues/1445).

---

## 1. Aktuelles LR-Verdikt

| Field | Value |
|-------|-------|
| **Operational verdict** | **NO-GO** |
| **Blocking phase (roadmap)** | None (`P0` blocking phase is `DONE`) |
| **Global live-readiness blocker** | `P5` / `LR-050` — gated; requires explicit human approval before any live-capital exposure |
| **SSOT** | [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) |
| **Phase mirror** | [`GO_NO_GO.md`](./GO_NO_GO.md) — P5 row `NO-GO` |

**Interpretation:** P0–P4 prerequisites are `DONE`. Committed P5 prestart artifacts under `reports/p5_canary/2026-04-04/` (`manifest.json`, `prestart_evidence_lock.yaml`, `decision_record.yaml`, `lean_shadow_evidence_handoff.yaml`) are **prestart-only** evidence. They do **not** clear `LR-050` and do **not** authorize live capital.

---

## 2. Erfüllte Evidence (referenziert, nicht neu bewertet)

Phasenstatus gemäß [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md) (nicht `P5_CANARY_EXECUTION_CHECKLIST.md` §5, falls dort ältere P1-Formulierung).

| Phase / Task | Status | Primary evidence |
|--------------|--------|------------------|
| P0 `LR-001`–`LR-003` | DONE | [`LR-001-EVIDENCE.md`](./LR-001-EVIDENCE.md), [`LR-002-EVIDENCE.md`](./LR-002-EVIDENCE.md), [`LR-003-EVIDENCE.md`](./LR-003-EVIDENCE.md) |
| P1 `LR-012` (scope-narrowed) | DONE | PR #1107, [`docs/evidence/LR-012.md`](../evidence/LR-012.md), [`LR-012-STATE.yaml`](./LR-012-STATE.yaml) |
| P2 `LR-020`, `LR-021` | DONE | [`LR-020-STATE.yaml`](./LR-020-STATE.yaml), LR-021 closed |
| P3 `LR-030` | DONE | [`docs/evidence/LR-030.md`](../evidence/LR-030.md), [`LR-030-STATE.yaml`](./LR-030-STATE.yaml), `reports/lr030/2026-05-17/` |
| P3 `LR-031` | PASS-evidenced | [`docs/evidence/LR-031.md`](../evidence/LR-031.md) |
| P3 soak run | PASS | [#2440](https://github.com/jannekbuengener/Claire_de_Binare/issues/2440) **CLOSED** — >24h shadow/soak (`lr030-shadow-soak-20260516_204415`) |
| P4 `LR-040`–`LR-042` | DONE / PASS | `reports/p5_canary/2026-04-04/lr040/lr040_soak_gate_eval.json`, [`docs/evidence/LR-041.md`](../evidence/LR-041.md), [`docs/evidence/LR-042.md`](../evidence/LR-042.md) |
| P5 prestart pack | Committed GO (prestart only) | `reports/p5_canary/2026-04-04/` — **does not** clear `LR-050` |

Control map (detail): [`docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`](../operations/P5_CANARY_EXECUTION_CHECKLIST.md).

---

## 3. Offene P5-Risiken und Planungs-Gates

Diese Risiken bleiben offen, bis die zugehörigen Kind-Issues repo-backed erfüllt sind. **Dieses Pack schließt sie nicht.**

| Risk / gate | Owner issue | State | Note |
|-------------|-------------|-------|------|
| Venue / broker / exchange path audit | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) | OPEN | No preferred canary venue documented yet |
| Hard capital, order, and loss limits | [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) | OPEN | SSOT: [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) — structure + enforceability; canary values `TBD_BLOCKER_BEFORE_LIVE` |
| Kill-switch and stop controls verified | [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) | OPEN | SSOT: [LR-050-KILL-SWITCH-RUNBOOK.md](./LR-050-KILL-SWITCH-RUNBOOK.md) |
| Secret handling readiness (no key exposure) | [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) | OPEN | SSOT: [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) — gate definition only; venue permissions `TBD_BLOCKER_BEFORE_LIVE` until #2527 |
| Live-canary monitoring / alert gates | [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) | OPEN | Prometheus / Alertmanager readiness |
| First real-money canary **plan** (not activation) | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | OPEN | Depends on #2527–#2531 |
| Live-path dry-run without orders | [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | OPEN | `real_money=false` / dry_run proof |
| Exact human approval wording and checklist | [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) | OPEN | **Child gate** — no GO wording in this pack |
| Final LR verdict reconcile | [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | OPEN | After #2527–#2534; may set `ready-for-human-live-approval` only if evidence supports it |

Residual policy risks (audit canon): no staged live-capital rollout plan approved; explicit human gate for real trades remains mandatory ([`ROADMAP.yaml`](./ROADMAP.yaml) — `requires: explicit_human_approval`).

---

## 4. Entscheidungsvorlage (GO / NO-GO / ready-for-human-live-approval)

**Aktiver Zustand:** `NO-GO`

| State | Meaning | Current |
|-------|---------|---------|
| `NO-GO` | Live-capital canary not authorized; fail-closed | **Active** |
| `ready-for-human-live-approval` | Planning/evidence complete enough for Jannek to review and issue **separate** exact approval per [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md); reconcile via [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | **Not reached** |
| `GO` | Live-capital canary may proceed only after **explicit** human approval matching [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md); never via issue/PR merge alone | **Not granted** |

**Operator decision log (template — do not pre-fill GO):**

```text
Date (UTC):
Operator:
Decision: NO-GO | ready-for-human-live-approval | GO
Evidence reviewed: LR-050-DECISION-PACK.md + LR-AUDIT-STATUS + child issues #2527–#2534
If GO: exact approval text (must match [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md) — [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534)):
Venue:
Symbols:
Max notional:
Max daily loss:
Duration:
Revocation / halt trigger:
```

---

## 5. Canary-Parameter (TBD — nicht freigebend)

Alle Felder sind **TBD** bis die Kind-Issues liefern. Werte hier sind Platzhalter, keine Freigabe.

**Risk-limit detail (enforceability, fail-closed, proof hooks):** [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)).

| Parameter | Value | Source issue |
|-----------|-------|--------------|
| **Venue** | TBD | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) |
| **Symbols** | TBD | [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528), [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) |
| **Max notional (per order / session)** | TBD (`TBD_BLOCKER_BEFORE_LIVE`) | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 |
| **Max daily loss** | TBD (`TBD_BLOCKER_BEFORE_LIVE`) | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 |
| **Laufzeit (canary window)** | TBD | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) |
| Order types | TBD | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) |
| Trading window / cooldown | TBD (`TBD_BLOCKER_BEFORE_LIVE`) | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) §4 |

Procedure shape (not verdict): [`knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md`](../../knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md).

---

## 6. Stop- / Kill-Regeln und Rollback

| Topic | Reference |
|-------|-----------|
| **Kill-switch / stop SSOT** | [LR-050-KILL-SWITCH-RUNBOOK.md](./LR-050-KILL-SWITCH-RUNBOOK.md) ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)) |
| Kill-switch operator checklist | [`docs/operations/KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md) |
| P5 governance baseline | [`governance/p5_canary_readiness.yaml`](../../governance/p5_canary_readiness.yaml) |
| Kill-switch verification in soak gate | `infrastructure/scripts/soak_gate_eval.py` — `kill_switch_precheck_inactive` (see runbook §9 precheck gap) |

**Rollback (fail-closed default):**

1. Halt new orders (manual kill-switch / trading disable / allocation 0 per runbook).
2. Restore canonical shadow/prestart path: `execution_status.mode` = `mock` (see P5 runtime-mode contract).
3. Do not set `MOCK_TRADING="false"` or enable live execution without separate human GO per [LR-050-HUMAN-APPROVAL.md](./LR-050-HUMAN-APPROVAL.md).
4. Document incident and keep global verdict **NO-GO** until [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) reconcile.

---

## 7. Monitoring

| Topic | Reference |
|-------|-----------|
| Canary alert matrix / abort vs investigate | [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) (OPEN) |
| P5 control map (alert-related controls) | [`P5_CANARY_EXECUTION_CHECKLIST.md`](../operations/P5_CANARY_EXECUTION_CHECKLIST.md) |
| Prestart endpoint captures (historical) | `reports/p5_canary/2026-04-04/endpoints/` |

**Gate:** No live-capital approval without documented Alertmanager/Prometheus readiness and stop rules ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531), [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)).

---

## 8. Verantwortlicher Operator

| Role | Identity |
|------|----------|
| **Accountable operator** | `jannekbuengener` (consistent with [`GO_NO_GO.md`](./GO_NO_GO.md) owner column) |
| **Responsibilities** | Review this pack, child-issue evidence, and LR-AUDIT-STATUS before any state change; execute halt/rollback; never infer GO from automation, PR merge, or Board stage |

No credentials, API keys, or secret values belong in this document.

---

## 9. Human Approval Boundary

| Rule | Detail |
|------|--------|
| Who may grant live-capital GO | [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534)) — only `jannekbuengener` (or explicit handoff) |
| What PR #2526 / this pack grants | **Nothing** toward live or real-money trading |
| Implicit approval | **Invalid** — ambiguous statements do not count as GO |
| Issue / PR closure | Does **not** replace human approval |
| Prestart Human Gate (2026-04-04) | P5 shadow/prestart continuity only |
| Final verdict upgrade | [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) after #2527–#2534 complete |

---

## 10. Kind-Issue-Gate-Matrix

| Issue | Title (short) | Required for `ready-for-human-live-approval` |
|-------|---------------|-----------------------------------------------|
| [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) | Venue audit | Yes |
| [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) | Risk limits | Yes |
| [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) | Kill-switch | Yes |
| [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) | Secrets handling — [LR-050-SECRETS-READINESS.md](./LR-050-SECRETS-READINESS.md) | Yes |
| [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) | Observability | Yes |
| [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | Canary plan | Yes |
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | Dry-run proof | Yes |
| [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) | Approval wording | Yes |
| [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) | Final LR reconcile | Yes (after above) |

---

## Related documents (no duplication)

- [`README.md`](./README.md) — live-readiness index
- [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) — hard capital/order/loss gate parameters ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528))
- [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) — stop/halt paths and verification matrix ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529))
- [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) — exact live-capital GO/REVOKE wording ([#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534))
- [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) — credential handling and readiness ([#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530))
- [`ISSUES.md`](./ISSUES.md) — LR task list
- [`docs/operations/P5_PRESTART_PACK.md`](../operations/P5_PRESTART_PACK.md) — prestart template
- [`docs/runbooks/CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md) — Board stage vs LR
