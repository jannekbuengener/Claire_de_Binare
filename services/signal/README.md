# Signal Service (`cdb_signal`)

Event-getriebene Signal-Erzeugung aus `market_data` mit statischer Adapter-Grenze.

## Current-main Scope

- Erzeugt Signale fuer den Risk Service (`cdb_risk`).
- Default-Strategiepfad ist `primary_breakout_v1`.
- Runtime-Pfad `donchian_breakout_v1` nutzt bar-basierte Donchian-Kanaele (Pack-A §7.2, frozen defaults via `SIGNAL_ENTRY_CHANNEL_BARS` / `SIGNAL_EXIT_CHANNEL_BARS`).
- Adapter-Auswahl bleibt fail-closed und statisch (kein dynamisches Runtime-Routing).
- Kein Live-Authorization-Gate: Stage/LR-Gates bleiben ausserhalb dieses Service.

## Topics / Streams

- Input Topic: `market_data`
- Output Topic: `signals`
- Output Stream: `stream.signals` (konfigurierbar via `SIGNAL_OUTPUT_STREAM`)

## Runtime Surface

- Endpoint-Port: `SIGNAL_PORT` (Config-Default `8001`; RED-Runtime `8005` via `compose.red.yml`)
- HTTP Endpoints: `/health`, `/status`, `/metrics`

Start im RED-Stack:

```powershell
docker compose -f infrastructure/compose/compose.red.yml up -d cdb_signal
```

Parallel natural-paper (campaign-scoped, **not** canonical default; requires separate
RUNTIME-GO; #3912 remains NOT READY):

```powershell
# Static validation only in CI/docs — do not run up without RUNTIME-GO
docker compose `
  -f infrastructure/compose/compose.red.yml `
  -f config/arvp/runtime_np_parallel_signal_compose_override.yml `
  config
```

See `config/arvp/README.md` for `cdb_signal_pb1` / `cdb_signal_donchian` bot-id
convention, allocation override pairing, and risk-side filter contract (#3911).
LR remains **NO-GO**.

## Key Config

- `SIGNAL_STRATEGY_ID`
- `SIGNAL_SYMBOL`
- `SIGNAL_ENTRY_LOOKBACK_MIN`
- `SIGNAL_EXIT_LOOKBACK_MIN`
- `SIGNAL_BREAKOUT_BUFFER`
- `SIGNAL_MIN_MINUTES_BETWEEN_ENTRIES`
- `SIGNAL_ENTRY_CHANNEL_BARS` (donchian_breakout_v1, default `20`)
- `SIGNAL_EXIT_CHANNEL_BARS` (donchian_breakout_v1, default `10`)
- `SIGNAL_OUTPUT_STREAM`
- `SIGNAL_BOT_ID` (experiment audit identity; compose-wired)
- `CDB_CAMPAIGN_ID` (campaign-scoped overlays; lane-specific via `CDB_CAMPAIGN_ID_PB1` / `CDB_CAMPAIGN_ID_DONCHIAN`)
- `CDB_SOURCE_SHA` (image build marker; set at `docker build --build-arg`; verified before ARVP observation)

## ARVP Telemetry (measurement chain only)

After PRs #3956, #3961, #3971, #3974 the signal service participates in a
**measurement chain** for bounded natural-paper/diagnostic runs:

1. **Runtime signal IDs** — `format_runtime_signal_id()` assigns collision-safe
   `sig-…` UUID4-hex IDs for natural-paper paths (not the deterministic replay
   counter).
2. **Ledger write** — each published signal persists to `correlation_ledger`
   via `build_signal_ledger_payload()`; `campaign_id` comes from `CDB_CAMPAIGN_ID`.
3. **Insert conflicts** — `ON CONFLICT DO NOTHING` suppressions increment
   `correlation_ledger_insert_conflicts_total` (Prometheus on `/metrics`).
   Non-zero conflicts with zero lane ledger rows indicate **false-zero risk**.
4. **Supervisor evidence** — `tools/arvp_campaign_supervisor` reads lane metrics
   and Postgres for `lane_campaign_evidence` and `blocks_by_reason`.

**Telemetry PASS proves the measurement chain, not trading readiness.** LR remains
**NO-GO**; no promotion claim.

### Image freshness (`CDB_SOURCE_SHA`)

Campaign overlays require rebuilt signal images. The Dockerfile exposes
`ARG/ENV CDB_SOURCE_SHA`. Before any RUNTIME-GO observation:

```powershell
docker inspect cdb_signal_pb1 --format "{{range .Config.Env}}{{println .}}{{end}}" | findstr CDB_SOURCE_SHA
```

If the container SHA ≠ expected `origin/main` (or manifest pin) → **HOLD**.

Rebuild/recreate review (docs-only): `docs/evidence/arvp_signal_runtime_rebuild_recreate_review_3976.md`.

Preflight helpers:

```powershell
python -m tools.arvp_diag_reverify_preflight --json
python -m tools.arvp_np_telemetry_pass_preflight --json
```

## Canonical References

- `services/signal/service.py`
- `services/signal/config.py`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1.md`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md`
