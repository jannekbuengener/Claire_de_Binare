# ARVP Parallel Natural-Paper After Telemetry PASS — Preflight (#3980)

Status Class: **PREFLIGHT_READY** — docs/manifests only; **no runtime executed**
Issue: [#3980](https://github.com/jannekbuengener/Claire_de_Binare/issues/3980)
Hypothesis: `HYP-NP-PARALLEL-2S-01`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Telemetry chain: [#3977](https://github.com/jannekbuengener/Claire_de_Binare/issues/3977) `PASS_TELEMETRY_REVERIFIED` / PR [#3978](https://github.com/jannekbuengener/Claire_de_Binare/pull/3978) / PR [#3979](https://github.com/jannekbuengener/Claire_de_Binare/pull/3979)
Prior pilot: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912) (CLOSED `TIMEOUT_NO_CHAIN`)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Preflight verdict:** `READY_PENDING_RUNTIME_GO` — strategy validation run prepared;
execution blocked until Jannek posts RUNTIME-GO on #3980.

**No-run assertion:** This slice did **not** start parallel natural-paper observation.

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
| #3977 telemetry re-verify | PASS | `PASS_TELEMETRY_REVERIFIED`; `docs/evidence/arvp_diag_telemetry_reverify_run.md` |
| #3971 collision-safe signal IDs | PASS | merged @ `251faf59` |
| #3911 ledger isolation | PASS | PR #3941 @ `0f273b15` |
| Fresh campaign manifests | PASS | `manifests/campaign_np_telemetry_pass_pb1.yaml`, `..._donchian.yaml` |
| Compose lane wiring | PASS | `manifests/runtime_np_telemetry_pass_signal_compose_override.yml` |
| `CDB_SOURCE_SHA` pinned | PASS | `441fb9d6d0731f2111142899a1b8be828a4a046a` (`origin/main` @ #3979) |
| RUNTIME-GO on #3980 | **PENDING** | Human gate |

---

## 3. Prepared run

| Lane | `strategy_id` | `bot_id` | `campaign_id` |
|------|---------------|----------|---------------|
| PB1 | `primary_breakout_v1` | `np-pb1-telemetry-pass-01` | `arvp_np_pb1_after_telemetry_pass_20260710t1700z` |
| Donchian | `donchian_breakout_v1` | `np-donchian-telemetry-pass-01` | `arvp_np_donchian_after_telemetry_pass_20260710t1700z` |

| Parameter | Value |
|-----------|-------|
| Window | **4h first** (not 12h) |
| Symbol | BTCUSDT |
| Supervisors | 2× `tools.arvp_campaign_supervisor` (one per manifest) |
| Execute evidence doc | `docs/evidence/arvp_np_parallel_after_telemetry_pass_run.md` (opened at execute) |

**Not reused:** #3912 pilot IDs, #3967 diagnostic IDs, #3977 re-verify IDs.

---

## 4. Host env mapping

Preflight tool: `python -m tools.arvp_np_telemetry_pass_preflight --json`

```powershell
$env:CDB_CAMPAIGN_ID_PB1 = "arvp_np_pb1_after_telemetry_pass_20260710t1700z"
$env:CDB_CAMPAIGN_ID_DONCHIAN = "arvp_np_donchian_after_telemetry_pass_20260710t1700z"
$env:CDB_SOURCE_SHA = "441fb9d6d0731f2111142899a1b8be828a4a046a"
```

```bash
export CDB_CAMPAIGN_ID_PB1="arvp_np_pb1_after_telemetry_pass_20260710t1700z"
export CDB_CAMPAIGN_ID_DONCHIAN="arvp_np_donchian_after_telemetry_pass_20260710t1700z"
export CDB_SOURCE_SHA="441fb9d6d0731f2111142899a1b8be828a4a046a"
```

---

## 5. Telemetry gates (mandatory at execute)

| Gate | Observable via |
|------|----------------|
| `lane_campaign_evidence` | `tools.arvp_campaign_supervisor` / probe layer |
| `correlation_ledger_insert_conflicts_total` | `:8015` / `:8016` metrics |
| `campaign_id` propagation | lane ledger rows + supervisor evidence |
| No false-zero | container log signal count == supervisor ledger count |

Execute **must HOLD** if `CDB_SOURCE_SHA` in running containers ≠ expected SHA.

---

## 6. Static validation (2026-07-10)

```text
pytest -q tests/unit/arvp tests/unit/tools tests/unit/replay -k "np_telemetry_pass or arvp"
ruff check core services tools tests
python -m tools.arvp_np_telemetry_pass_preflight --json
docker compose -f infrastructure/compose/compose.blue.yml
  -f infrastructure/compose/compose.red.yml
  -f manifests/runtime_np_telemetry_pass_signal_compose_override.yml
  -f manifests/runtime_np_parallel_allocation_compose_override.yml config
```

Note: `infrastructure/compose/docker-compose.yml` is not present in this repo;
canonical static validation uses `compose.blue.yml` + `compose.red.yml` + overrides.

---

## 7. RUNTIME-GO phrase (Jannek — copy/paste on #3980)

```text
RUNTIME-GO #3980: start 4h ARVP PB1 + Donchian parallel natural-paper run after telemetry PASS, CDB_CAMPAIGN_ID_PB1 and CDB_CAMPAIGN_ID_DONCHIAN set from manifests, CDB_SOURCE_SHA verified in containers before observation, MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false, no Live/Echtgeld.
```

Before supervisor start: rewrite `start_utc` and `timeout_utc` in both manifests
(replace `RUNTIME_GO_SET` placeholders).

---

## 8. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld authorization from this preflight
- No strategy parameter tuning
- No promotion claim
- Shared risk/execution — conservative per-strategy allocation caps apply

---

*Preflight recorded 2026-07-10 on `docs/arvp-parallel-after-telemetry-pass-preflight`.*
