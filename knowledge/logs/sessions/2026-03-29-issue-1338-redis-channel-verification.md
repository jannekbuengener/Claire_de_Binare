# Session Log — 2026-03-29 — Issue #1338 Redis Channel Verification

## Ziel
Vollständige Verifikation der Redis-Channel-Tabelle in `knowledge/ARCHITECTURE_MAP.md` gegen aktuelle Code-Callsites.

## Ergebnis
- **Pub/Sub Channels:** 5/6 verified-current, 1 korrigiert (`alerts`: "(Monitoring)" → "kein Code-Subscriber (publish-only)")
- **Redis Streams:** 8 Streams neu dokumentiert mit Verified-Spalte
  - 5 mit aktiven xread-Consumern
  - 3 ohne (stream.signals, stream.orders, stream.orders_blocked — write-only / Audit-Artefakte)

## Änderungen
- `knowledge/ARCHITECTURE_MAP.md` — Pub/Sub-Tabelle qualifiziert, neue Streams-Sektion
- Commit: `e88c523` auf `fix/1302-inventory-reconcile-blue-red`

## Issues
- #1338: kommentiert + geschlossen
- #1335: als Teilmenge von #1338 kommentiert + geschlossen

## Restunsicherheiten
- `alerts` ist publish-only; externe Subscriber (Grafana/Alertmanager) außerhalb Repo-Scope möglich
- `cdb.envelopes.v1` / `cdb:envelopes:v1` (Replay-Infrastruktur) bewusst nicht in Service-Tabelle aufgenommen
- 3 reader-lose Streams könnten als Cleanup-Issue getracked werden (nicht angelegt)
