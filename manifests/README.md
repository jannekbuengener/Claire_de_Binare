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
- **#3912** (parallel pilot execute) remains **NOT READY** until:
  - #3911 ledger/evidence isolation guards land
  - alignment review against gearbox design contracts (#3913)
  - explicit RUNTIME-GO
- **#3893** (single-strategy Donchian 24h observation) is a **separate lane** — do not conflate or schedule against without coordination.

### Risk-side filter contract (topic/stream isolation)

Both parallel signal instances publish to the **shared** Redis pub/sub topic `signals`
and stream `stream.signals` (default `SIGNAL_OUTPUT_STREAM`). `cdb_risk` subscribes
to the shared bus and routes decisions using payload `strategy_id` and `bot_id`.

Per-publisher topic partitioning is **not** implemented in this slice. Runtime
ledger/evidence isolation guards are tracked in **#3911**.

## Single-strategy prior art

| Artifact | Purpose |
|----------|---------|
| `runtime_3792_signal_compose_override.yml` | Swap canonical `cdb_signal` to `donchian_breakout_v1` for #3792 |
| `campaign_3792_donchian_np_01.yaml` | Campaign manifest referencing the #3792 signal override |
