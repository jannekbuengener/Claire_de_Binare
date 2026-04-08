---
issue: 1315
date: 2026-03-29
topic: Signal README Port-Drift Fix
status: CLOSED
---

## Befund

- `services/signal/README.md` dokumentierte 4× Port `8001` (Architektur-Übersicht, curl-Beispiel, Health-Endpoint, Metrics-Endpoint)
- Tatsächlicher Runtime-Port: `8005` (via `SIGNAL_PORT=8005` in `compose.red.yml:67`, Port-Binding `8005:8005` in `compose.red.yml:72`)
- `config.py:17` Default ist `8001`, aber in allen Deploy-Szenarien durch Env-Var überschrieben → kein Fix nötig
- Fehler im Issue-Text: Issue nennt `compose.blue.yml`, cdb_signal ist in `compose.red.yml`

## Fix

- Branch: `fix/1315-signal-readme-port`
- Commit: `825f992` — 4 Stellen in README korrigiert
- PR: #1318 (squash-merged, Branch gelöscht)

## Validierung

- Alle CI-Checks grün (ci, policy-gate, replay-smoke)
- `grep -n "8001" services/signal/README.md` → kein Treffer nach Fix
- Issue #1315 auto-closed durch PR-Merge
