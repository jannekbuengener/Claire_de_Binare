# Campaign manifests

Campaign-scoped runtime overlays for bounded ARVP natural-paper observations.
These files are **not** canonical defaults. LR remains **NO-GO**; no Live/Echtgeld
authorization from manifest presence alone.

## Parallel natural-paper (2-strategy)

| Artifact | Purpose |
|----------|---------|
| `runtime_np_parallel_signal_compose_override.yml` | Two `cdb_signal` instances: `cdb_signal_pb1` (`primary_breakout_v1`) and `cdb_signal_donchian` (`donchian_breakout_v1`) with distinct ports and non-empty `SIGNAL_BOT_ID` values (#3909) |
| `runtime_np_parallel_allocation_compose_override.yml` | Conservative per-strategy allocation caps for shared capital pool (#3910 / #3915) |

Hypothesis: `HYP-NP-PARALLEL-2S-01`.

### Static validation (no `up` / `down` / `restart`)

```powershell
$env:SECRETS_PATH = "<path-to-secrets>"
docker compose `
  -f infrastructure/compose/compose.red.yml `
  -f manifests/runtime_np_parallel_signal_compose_override.yml `
  config
```

Full parallel stack (signal + allocation overrides):

```powershell
docker compose `
  -f infrastructure/compose/compose.blue.yml `
  -f infrastructure/compose/compose.red.yml `
  -f manifests/runtime_np_parallel_signal_compose_override.yml `
  -f manifests/runtime_np_parallel_allocation_compose_override.yml `
  config
```

### Application gates

- **Separate RUNTIME-GO required** before any `docker compose up`.
- **#3912** (parallel pilot execute): prerequisites #3909–#3911 + gearbox alignment
  review landed; **pending Jannek RUNTIME-GO** on #3912. Preflight:
  `docs/evidence/arvp_parallel_natural_paper_3912_preflight.md`.
- **#3893** (single-strategy Donchian 24h) **CLOSED** (`TIMEOUT_NO_CHAIN`) — stack
  returned to canonical `cdb_signal` baseline before #3912 scheduling.

### Campaign manifests (#3912)

| Artifact | Lane |
|----------|------|
| `campaign_3912_np_parallel_pb1.yaml` | `primary_breakout_v1` / `np-pb1-parallel-01` |
| `campaign_3912_np_parallel_donchian.yaml` | `donchian_breakout_v1` / `np-donchian-parallel-01` |

Rewrite `campaign_id`, `start_utc`, and `timeout_utc` at RUNTIME-GO execute (templates
use `*_TEMPLATE` / `RUNTIME_GO_SET` placeholders).

At RUNTIME-GO, export lane-specific host env from rewritten manifests before `docker compose up`:

```text
CDB_CAMPAIGN_ID_PB1=<pb1 manifest campaign_id>
CDB_CAMPAIGN_ID_DONCHIAN=<donchian manifest campaign_id>
```

Helper: `tools.arvp_parallel_lane_compose_contract.build_parallel_compose_host_env()`.
Each parallel signal service receives `CDB_CAMPAIGN_ID` via compose substitution (P1.5 / #3963).
Values must be distinct.

### Risk-side filter contract (topic/stream isolation)

Both parallel signal instances publish to the **shared** Redis pub/sub topic `signals`
and stream `stream.signals` (default `SIGNAL_OUTPUT_STREAM`). `cdb_risk` subscribes
to the shared bus and routes decisions using payload `strategy_id` and `bot_id`.

Per-publisher topic partitioning is **not** implemented in this slice. Runtime
ledger/evidence isolation is guarded by contract tests in
`tests/unit/arvp/test_arvp_parallel_ledger_evidence_isolation_contract_3911.py`
(mixed PB1 + Donchian fixture; export qualifiers: `strategy_id`, `bot_id`,
`config_hash`). Unqualified mixed-window export fails closed (`mixed bot_id`).

Gearbox alignment: `docs/evidence/arvp_parallel_pilot_gearbox_alignment_3912.md`.
**#3912** still requires explicit **RUNTIME-GO** before execute.

### Diagnostic telemetry verification (#3965)

Short 2h parallel run to prove post-#3964 telemetry (collision-safe `signal_id`,
lane-scoped counts, `campaign_id` propagation, block-reason evidence).

| Artifact | Lane |
|----------|------|
| `campaign_diag_telemetry_pb1.yaml` | `primary_breakout_v1` / `np-pb1-diag-01` |
| `campaign_diag_telemetry_donchian.yaml` | `donchian_breakout_v1` / `np-donchian-diag-01` |
| `runtime_np_diag_telemetry_signal_compose_override.yml` | Diagnostic bot IDs + P1.5 `CDB_CAMPAIGN_ID` wiring |

Preflight: `docs/evidence/arvp_diag_telemetry_verification_preflight.md`.
Helper: `python -m tools.arvp_diag_telemetry_preflight`.
**Pending Jannek RUNTIME-GO on #3965.**

## Single-strategy prior art

| Artifact | Purpose |
|----------|---------|
| `runtime_3792_signal_compose_override.yml` | Swap canonical `cdb_signal` to `donchian_breakout_v1` for #3792 |
| `campaign_3792_donchian_np_01.yaml` | Campaign manifest referencing the #3792 signal override |
