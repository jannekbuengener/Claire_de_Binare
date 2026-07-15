# ARVP Diagnostic Telemetry Verification — Preflight (#3965)

Status Class: **PREFLIGHT_READY** — config/arvp/docs/tooling only; **no runtime executed**
Issue: [#3965](https://github.com/jannekbuengener/Claire_de_Binare/issues/3965)
Hypothesis: `HYP-ARVP-DIAG-TELEMETRY-01`
Prerequisites: [#3956](https://github.com/jannekbuengener/Claire_de_Binare/pull/3956), [#3961](https://github.com/jannekbuengener/Claire_de_Binare/pull/3961), [#3964](https://github.com/jannekbuengener/Claire_de_Binare/pull/3964)
Root observation: [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912) (`TIMEOUT_NO_CHAIN`)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Preflight verdict:** `READY_PENDING_RUNTIME_GO` — diagnostic manifests, host-env mapping,
and compose preflight complete; execution blocked until Jannek posts RUNTIME-GO on #3965.

**No-run assertion:** This slice did **not** start any runtime observation.

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

## 2. What the future run will prove

After RUNTIME-GO on #3965, a **2h** parallel natural-paper diagnostic run (PB1 + Donchian,
`BTCUSDT`) should demonstrate post-#3964 telemetry repairs:

| Proof target | Source slice | Runtime signal |
|--------------|--------------|----------------|
| Collision-safe `signal_id` | #3955 / #3956 | No duplicate runtime signal IDs across lanes |
| Global + lane-scoped Supervisor counts | #3955 / #3956 | Supervisor reports both scopes |
| `campaign_id` per parallel lane | #3963 / #3964 | Container `CDB_CAMPAIGN_ID` matches manifest |
| `lane_campaign_evidence` | #3960 / #3961 | Probe/supervisor payload per lane |
| `blocks_by_reason` | #3960 / #3961 | Visible when Risk blocks |
| `campaign_id_propagated_to_ledger` | #3960 / #3961 | **Not proven until runtime** |

**Not claimed in this preflight:** `campaign_id_propagated_to_ledger` — requires runtime evidence.

---

## 3. Diagnostic campaign manifests

| Lane | Manifest | `campaign_id` | `bot_id` | `strategy_id` |
|------|----------|---------------|----------|---------------|
| PB1 | `config/arvp/campaign_diag_telemetry_pb1.yaml` | `arvp_diag_p15_pb1_20260710t1100z` | `np-pb1-diag-01` | `primary_breakout_v1` |
| Donchian | `config/arvp/campaign_diag_telemetry_donchian.yaml` | `arvp_diag_p15_donchian_20260710t1100z` | `np-donchian-diag-01` | `donchian_breakout_v1` |

Distinct from #3912 (`np-pb1-parallel-01`, `np-donchian-parallel-01`, `arvp_3912_*` IDs).

Compose override: `config/arvp/runtime_np_diag_telemetry_signal_compose_override.yml`
Allocation override: `config/arvp/runtime_np_parallel_allocation_compose_override.yml` (unchanged)

---

## 4. Host env mapping (set before `docker compose up`)

Export from manifests via `tools.arvp_diag_telemetry_preflight`:

```powershell
$env:CDB_CAMPAIGN_ID_PB1 = "arvp_diag_p15_pb1_20260710t1100z"
$env:CDB_CAMPAIGN_ID_DONCHIAN = "arvp_diag_p15_donchian_20260710t1100z"
```

```bash
export CDB_CAMPAIGN_ID_PB1="arvp_diag_p15_pb1_20260710t1100z"
export CDB_CAMPAIGN_ID_DONCHIAN="arvp_diag_p15_donchian_20260710t1100z"
```

Helper:

```powershell
python -m tools.arvp_diag_telemetry_preflight
python -m tools.arvp_diag_telemetry_preflight --json
```

At RUNTIME-GO execute: rewrite `start_utc` and `timeout_utc` in both manifests
(replace `RUNTIME_GO_SET`).

---

## 5. Static validation (2026-07-10)

```powershell
pytest -q tests/unit/arvp tests/unit/tools -k "diag_telemetry or p15_campaign"
ruff check tools services core tests
$env:CDB_CAMPAIGN_ID_PB1 = "arvp_diag_p15_pb1_20260710t1100z"
$env:CDB_CAMPAIGN_ID_DONCHIAN = "arvp_diag_p15_donchian_20260710t1100z"
docker compose `
  -f infrastructure/compose/compose.blue.yml `
  -f infrastructure/compose/compose.red.yml `
  -f config/arvp/runtime_np_diag_telemetry_signal_compose_override.yml `
  -f config/arvp/runtime_np_parallel_allocation_compose_override.yml `
  config
```

`docker compose config` only — no `up`, `restart`, or container start.

---

## 6. Execute parameters (at RUNTIME-GO)

| Parameter | Value |
|-----------|-------|
| Window | 2h (recommended) |
| Symbol | BTCUSDT |
| PB1 `strategy_id` / `bot_id` | `primary_breakout_v1` / `np-pb1-diag-01` |
| Donchian `strategy_id` / `bot_id` | `donchian_breakout_v1` / `np-donchian-diag-01` |
| Supervisors | 2× `tools.arvp_campaign_supervisor` (one per manifest) |
| Terminal evidence | `docs/evidence/arvp_diag_telemetry_verification_run.md` (opened at execute) |
| Safety | `MOCK_TRADING=true`, `DRY_RUN=true`, `MEXC_TESTNET=true`, `USE_REAL_BALANCE=false` |

---

## 7. RUNTIME-GO phrase (Jannek — copy/paste on #3965)

```text
RUNTIME-GO #3965: start 2h ARVP telemetry diagnostic run with PB1 + Donchian, CDB_CAMPAIGN_ID_PB1 and CDB_CAMPAIGN_ID_DONCHIAN set from manifests, MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false, no Live/Echtgeld.
```

---

## 8. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld authorization from this preflight
- No runtime started in this slice
- `campaign_id_propagated_to_ledger` unproven until runtime execute

---

*Preflight recorded 2026-07-10 on `main` @ `0eb19e46` (#3964).*
