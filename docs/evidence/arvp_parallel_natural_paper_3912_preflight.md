# ARVP Parallel Natural-Paper Pilot — Preflight (#3912)

Status Class: **PREFLIGHT_READY** — docs/manifests only; **no runtime executed**
Issue: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)
Hypothesis: `HYP-NP-PARALLEL-2S-01`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Gearbox alignment: [`arvp_parallel_pilot_gearbox_alignment_3912.md`](arvp_parallel_pilot_gearbox_alignment_3912.md)
Prior single-strategy lane: [#3893](https://github.com/jannekbuengener/Claire_de_Binare/issues/3893) (CLOSED `TIMEOUT_NO_CHAIN`)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Preflight verdict:** `READY_PENDING_RUNTIME_GO` — technical prerequisites and
alignment review complete; execution blocked until Jannek posts RUNTIME-GO on #3912.

**No-run assertion:** This slice did **not** start parallel pilot observation.

---

## 1. Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

---

## 2. Prerequisites checklist

| Gate | Status | Evidence |
|------|--------|----------|
| #3909 parallel compose | PASS | `config/arvp/runtime_np_parallel_signal_compose_override.yml` |
| #3910 Donchian allocation | PASS | `config/arvp/runtime_np_parallel_allocation_compose_override.yml` |
| #3911 ledger isolation | PASS | PR #3941 @ `0f273b15` |
| #3913 gearbox contracts | PASS | `docs/design/arvp_gearbox_design_contracts_3913.md` |
| Gearbox alignment review | PASS | `docs/evidence/arvp_parallel_pilot_gearbox_alignment_3912.md` |
| #3893 scheduling / stack | PASS | #3893 CLOSED; `cdb_signal` → `primary_breakout_v1` baseline |
| Campaign manifests | PASS | `config/arvp/campaign_3912_np_parallel_pb1.yaml`, `..._donchian.yaml` |
| RUNTIME-GO on #3912 | **PENDING** | Human gate |

---

## 3. Static validation (2026-07-09)

```text
pytest -q tests/unit/arvp/test_arvp_parallel_ledger_evidence_isolation_contract_3911.py
pytest -q tests/unit/arvp/test_arvp_np_parallel_signal_compose_contract_3909.py
pytest -q tests/unit/arvp/test_arvp_gearbox_design_contracts_3913.py
docker compose -f infrastructure/compose/compose.blue.yml
  -f infrastructure/compose/compose.red.yml
  -f config/arvp/runtime_np_parallel_signal_compose_override.yml
  -f config/arvp/runtime_np_parallel_allocation_compose_override.yml config
```

---

## 4. Execute parameters (at RUNTIME-GO)

| Parameter | Value |
|-----------|-------|
| Window | 12h (recommended) |
| Symbol | BTCUSDT |
| PB1 `strategy_id` / `bot_id` | `primary_breakout_v1` / `np-pb1-parallel-01` |
| Donchian `strategy_id` / `bot_id` | `donchian_breakout_v1` / `np-donchian-parallel-01` |
| Supervisors | 2× `tools.arvp_campaign_supervisor` (one per manifest) |
| Terminal evidence | `docs/evidence/arvp_parallel_natural_paper_3912.md` (opened at execute) |

**Before supervisor start:** rewrite `campaign_id`, `start_utc`, `timeout_utc` in both
manifests (replace `*_TEMPLATE` / `RUNTIME_GO_SET` placeholders).

---

## 5. RUNTIME-GO phrase (Jannek — copy/paste on #3912)

```text
RUNTIME-GO 2-Strategy Parallel Natural-Paper Pilot — HYP-NP-PARALLEL-2S-01 — strategies=primary_breakout_v1+donchian_breakout_v1 — symbol=BTCUSDT — window=12h — bot_ids=np-pb1-parallel-01,np-donchian-parallel-01 — MOCK_TRADING=true DRY_RUN=true USE_REAL_BALANCE=false MEXC_TESTNET=true — No Live-Go No Echtgeld-Go No Risk bypass No parameter tuning LR remains NO-GO — Expected outcome: per-strategy evidence only, not promotion
```

---

## 6. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld authorization from this preflight
- Shared risk/execution — conservative per-strategy allocation caps required

---

*Preflight recorded 2026-07-09 on `main`.*
