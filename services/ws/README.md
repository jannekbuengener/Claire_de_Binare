# WebSocket Service (`cdb_ws`)

MEXC WebSocket Feed (Protobuf v3) — publiziert normalisierte `market_data` auf Redis Pub/Sub.

## Current-main Scope

- RED-Stack-Service; Restart von RED darf BLUE-Core nicht invalidieren.
- Protobuf unter `services/ws/mexc_proto_gen/` (generiert, nicht manuell editieren).
- Health/Metrics auf Port `8000` auch ohne aktive WS-Verbindung importierbar.

## Topics / Streams

- Output Topic: `market_data` (Pub/Sub)

## Runtime Surface

- Endpoint-Port: `8000`
- HTTP: `/health`, `/metrics`

Start im RED-Stack:

```powershell
docker compose -f infrastructure/compose/compose.red.yml up -d cdb_ws
```

## Key Config

- MEXC credentials via Docker secrets / env (siehe `core/secrets`)
- Redis host/port/db wie übrige Services

## Canonical References

- `services/ws/service.py`
- `services/ws/mexc_v3_client.py`
- `services/candles/README.md`
