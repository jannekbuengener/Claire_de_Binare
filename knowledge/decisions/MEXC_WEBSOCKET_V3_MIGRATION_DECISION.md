# MEXC WebSocket V3 Protobuf Migration

## Status: 🟡 PROPOSED

Architecture Decision: Migration von Legacy MEXC WebSocket (JSON) zu MEXC V3 WebSocket (Protobuf) für Public Market Data.

## Executive Summary

Decision Driver:
- Legacy Endpoint liefert "Blocked!" und ist faktisch nicht mehr zuverlässig nutzbar.
- MEXC V3 WebSocket verwendet neuen Endpoint und Protobuf-Channels.
- Public Market Data benötigt keine Authentication.
- Governance: D1 ist Documentation-only. Keine Code-/Compose-Mutations.

Success Criteria (D1):
- Decision + Contract sind dokumentiert und reviewbar.
- Scope ist klar begrenzt (Public Read-Only).
- Akzeptanzkriterien für D2 Spike sind eindeutig.

## Kontext

Ausgangslage:
- `cdb_ws` ist aktuell STUB (keine produktive Market-Data Verarbeitung).
- Legacy MEXC WS (`wss://wbs.mexc.com/ws`) liefert "Blocked!" beim Subscribe.
- MEXC hat auf V3 WebSocket umgestellt: `wss://wbs-api.mexc.com/ws`.
- V3 Market Streams nutzen Protobuf-Channels (Suffix `.pb`).

Governance/Compliance:
- Constitution/Policies > User Chat (immer).
- Delivery Gate erforderlich für Code/Infra-Mutations, aber nicht für reine Doku.
- Exchange Credentials = Tresor-Zone. In D1 explizit out-of-scope.

## Entscheidung

Wir migrieren auf MEXC WebSocket V3 mit Protobuf-Decoding für Public Market Data.

Technische Eckpunkte (MVP):
- Endpoint: `wss://wbs-api.mexc.com/ws`
- MVP Channel: `spot@public.aggre.deals.v3.api.pb@BTCUSDT`
- Feature Flag: `WS_SOURCE=mexc_pb` (Default: off/stub)
- Keine Auth/Keys (Public Read-Only). Kein Tresor-Thema in D1.

Lieferplan (high level):
- D1: Decision + Spec (diese Files) ✅
- D2: Spike: Protobuf Tooling + Minimal-Client (decode-stabil)
- D3: Integration in `cdb_ws` mit Metrics + Feature Flag, ohne Secrets

## Alternativen

A) Legacy WS fixen
- Abgelehnt: Deprecation-/Inkompatibilitätsrisiko, unklare Zukunft, Zeitfresser.

B) REST Polling als Ersatz
- Abgelehnt (als Primärlösung): höhere Latenz, höhere API-Last, schlechtere Granularität.

C) Andere Exchange
- Abgelehnt: Scope Drift, keine Priorität gegenüber Stabilisierung der bestehenden Pipeline.

## Konsequenzen

Positiv:
- Stabiler Market-Data Feed für Paper Trading/Observability.
- Saubere Trennung: Public Streams ohne Secrets, Private Streams später (Tresor-konform).

Negativ / Aufwand:
- Protobuf Tooling (proto sources, codegen, decode pipeline) muss eingeführt werden.
- Zusätzliche Komplexität bei Message-Decoding und Fehlertoleranz.

## Akzeptanzkriterien (Gate zu D2)

D2 gilt als erfolgreich, wenn:
- Ein isolierter Client 10 Minuten stabil connected bleibt und Protobuf Messages decodiert (ohne Crashloop).
- Metrics/Logs belegen: decoded_messages_total steigt, ws_connected ist stabil, last_message_ts_ms aktualisiert sich.
- Keine Secrets/Keys in Runtime/Compose für Public Streams.

## Appendix: References

- MEXC Spot V3 WebSocket Market Streams (V3 Protobuf Channels)
- MEXC WebSocket Service Replacement Announcement / Migration Hinweis
