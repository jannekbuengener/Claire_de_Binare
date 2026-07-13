# ARVP Diagnostic Telemetry Re-Verify — Preflight (#3973)

Status Class: **PREFLIGHT_READY** — manifests/docs/tooling only; **no runtime executed**
Issue: [#3973](https://github.com/jannekbuengener/Claire_de_Binare/issues/3973)
Hypothesis: `HYP-ARVP-DIAG-TELEMETRY-REVERIFY-01`
Prerequisites: [#3971](https://github.com/jannekbuengener/Claire_de_Binare/pull/3971) @ `251faf59d94f50bd77972c06b3a7cf23d6ecf401`
Failed prior execute: [#3967](https://github.com/jannekbuengener/Claire_de_Binare/issues/3967) (`FAIL_FALSE_ZERO_EVENT_REPRODUCED`)
Regression fix: [#3970](https://github.com/jannekbuengener/Claire_de_Binare/issues/3970) / PR [#3971](https://github.com/jannekbuengener/Claire_de_Binare/pull/3971)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Preflight verdict:** `READY_PENDING_RUNTIME_GO` — re-verify manifests, build-freshness guard,
host-env mapping, and compose preflight complete; execution blocked until Jannek posts
RUNTIME-GO on #3973.

**No-run assertion:** This slice did **not** start any runtime observation.

**#3971 not runtime-verified yet:** Code/tests merged; execute proof remains open.

---

## 1. Why re-verify

#3967 showed Donchian signals in logs but supervisor/ledger **0/0** because all `signal_id`s
collided with pre-#3956 historical ledger rows (likely **stale signal containers**).
#3971 adds collision-safe ID propagation, ledger conflict visibility, and SHA freshness guard.

---

## 2. Expected source SHA (mandatory)

| Field | Value |
|-------|-------|
| `expected_source_sha` | `251faf59d94f50bd77972c06b3a7cf23d6ecf401` |
| `container_build_marker_env` | `CDB_SOURCE_SHA` |
| PR | [#3971](https://github.com/jannekbuengener/Claire_de_Binare/pull/3971) |

**Execute HOLD rule:** If `CDB_SOURCE_SHA` inside running containers cannot be proven equal to
`expected_source_sha` **before** observation → terminal `FAIL_STALE_IMAGE_GUARD` (no supervisor start).

---

## 3. Re-verify campaign manifests

| Lane | Manifest | `campaign_id` | `bot_id` | `strategy_id` |
|------|----------|---------------|----------|---------------|
| PB1 | `manifests/campaign_diag_reverify_pb1.yaml` | `arvp_diag_p0r_pb1_20260710t1600z` | `np-pb1-reverify-01` | `primary_breakout_v1` |
| Donchian | `manifests/campaign_diag_reverify_donchian.yaml` | `arvp_diag_p0r_donchian_20260710t1600z` | `np-donchian-reverify-01` | `donchian_breakout_v1` |

**Not reused:** #3967 IDs (`arvp_diag_p15_*`, `np-*-diag-01`).

Compose override: `manifests/runtime_np_diag_reverify_signal_compose_override.yml`

---

## 4. Host env mapping (set before `docker compose build/up`)

```powershell
$env:CDB_CAMPAIGN_ID_PB1 = "arvp_diag_p0r_pb1_20260710t1600z"
$env:CDB_CAMPAIGN_ID_DONCHIAN = "arvp_diag_p0r_donchian_20260710t1600z"
$env:CDB_SOURCE_SHA = "251faf59d94f50bd77972c06b3a7cf23d6ecf401"
```

```bash
export CDB_CAMPAIGN_ID_PB1="arvp_diag_p0r_pb1_20260710t1600z"
export CDB_CAMPAIGN_ID_DONCHIAN="arvp_diag_p0r_donchian_20260710t1600z"
export CDB_SOURCE_SHA="251faf59d94f50bd77972c06b3a7cf23d6ecf401"
```

Preflight tool: `python -m tools.arvp_diag_reverify_preflight --json`

---

## 5. Execute rebuild requirements (future RUNTIME-GO)

1. Set host env (§4).
2. Rebuild signal images (no cache):

```powershell
docker compose -f infrastructure/compose/compose.red.yml `
  -f manifests/runtime_np_diag_reverify_signal_compose_override.yml `
  build --no-cache cdb_signal_pb1 cdb_signal_donchian
```

3. Verify `CDB_SOURCE_SHA` in container env before observation:

```powershell
docker inspect cdb_signal_pb1 --format "{{range .Config.Env}}{{println .}}{{end}}" | findstr CDB_SOURCE_SHA
docker inspect cdb_signal_donchian --format "{{range .Config.Env}}{{println .}}{{end}}" | findstr CDB_SOURCE_SHA
```

4. Only then start 2h observation window and supervisors.

Safety: `MOCK_TRADING=true`, `DRY_RUN=true`, `MEXC_TESTNET=true`, `USE_REAL_BALANCE=false`.

---

## 6. Future terminal success / fail criteria

| Verdict | Condition |
|---------|-----------|
| `PASS_TELEMETRY_REVERIFIED` | SHA proven; no historical ID reuse; ledger conflicts reported if any; lane counts non-ambiguous |
| `FAIL_STALE_IMAGE_GUARD` | `CDB_SOURCE_SHA` != expected before observation |
| `FAIL_SIGNAL_ID_COLLISION_REPRODUCED` | Runtime IDs match pre-fix historical ledger rows |
| `FAIL_LEDGER_CONFLICT_SILENT` | Signals emitted but conflicts not visible in metrics/logs |
| `FAIL_CAMPAIGN_ID_NOT_PROPAGATED` | Campaign window ledger rows lack diagnostic `campaign_id` |
| `TIMEOUT_NO_SIGNAL_ACTIVITY` | True zero activity both lanes (no false-zero ambiguity) |
| `HOLD_RUNTIME_BLOCKER` | Preflight/infra blocker before window |

**Still unproven until execute:** `campaign_id_propagated_to_ledger`, `lane_campaign_evidence`.

---

## 7. RUNTIME-GO phrase (exact)

```text
RUNTIME-GO #3973: start 2h ARVP telemetry re-verify run after #3971 with rebuilt signal images, expected_source_sha=251faf59d94f50bd77972c06b3a7cf23d6ecf401, PB1 + Donchian, CDB_CAMPAIGN_ID_PB1 and CDB_CAMPAIGN_ID_DONCHIAN set from manifests, CDB_SOURCE_SHA verified in containers before observation, MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false, no Live/Echtgeld.
```

---

## 8. Boundaries

- LR **NO-GO** unchanged
- No Live/Echtgeld; no promotion claim
- No runtime started in this preflight slice
