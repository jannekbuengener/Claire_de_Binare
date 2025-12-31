# MEXC WebSocket V3 Market Data Contract (Public)

## Ziel

Definition eines minimalen, stabilen Contracts für Public Aggre Deals (Read-Only), der in CDB in ein normalisiertes Event-Schema überführt wird.

## Transport

- Endpoint: `wss://wbs-api.mexc.com/ws`
- Payload: Protobuf Messages (binary)
- Auth: nicht erforderlich (Public Market Data)

## Subscription

MVP (ein Symbol, ein Stream):
- Channel: `spot@public.aggre.deals.v3.api.pb@BTCUSDT`

Nicht MVP (später):
- Multi-symbol subscriptions / dynamische Symbol-Liste
- Weitere Streams (depth, kline, ticker)

## Normalisiertes Event Schema (CDB)

EventType: `TradeAgg`

Felder:
- source: `"mexc"`
- symbol: string (z.B. `"BTCUSDT"`)
- ts_ms: int64 (milliseconds)
- price: decimal/string (kein float rounding)
- qty: decimal/string
- side: enum (`buy` | `sell` | `unknown`)
- raw_ref: optional (Debug: message id/seq/opaque reference)

Hinweis:
- Die exakten Protobuf-Feldnamen werden im D2 Spike final gemappt (proto source of truth).

## Quality Gates (Observability)

- Decode-Rate: Counter `decoded_messages_total`
- Decode-Errors: Counter `decode_errors_total` (inkl. reason label)
- Liveness: Gauge `ws_connected` (0/1)
- Freshness: Gauge `last_message_ts_ms`

Logging:
- Rate-limited sample output (z.B. alle 30s 1 Event) für Debug, ohne Datenflut.

## Error Handling Strategy (MVP)

- Reconnect mit Backoff
- Decode-Fehler: message droppen, Counter erhöhen, Verbindung halten
- Hard-Fail nur bei wiederholtem handshake/connect failure

## Out of Scope (MVP)

- Private/User Streams
- Trading/Orders
- Secrets/Tresor Integration
- Persistenz in DB Writer / Redis / Postgres
- Compose/Infra Änderungen
