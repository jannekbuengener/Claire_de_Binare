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

## Canonical References

- `services/signal/service.py`
- `services/signal/config.py`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1.md`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md`
