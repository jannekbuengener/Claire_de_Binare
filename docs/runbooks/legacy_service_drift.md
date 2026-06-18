# Legacy Service Drift — Operator-Prüfpfad

**Erstellt:** 2026-06-18 (Audit #3302)
**Scope:** Erkennung und Klassifikation unerwarteter Legacy-Container im BLUE+RED-Stack
**Referenz:** `knowledge/governance/SERVICE_CATALOG.md` § Entfernte Services (Legacy)

---

## Betroffene Services

| Service | Status | Erwarteter Runtime-Zustand |
|---------|--------|---------------------------|
| `cdb_node_exporter` | LEGACY (entfernt 2026-04-09, #1528/PR #1535) | `absent` — kein Container im BLUE/RED-Stack |
| `cdb_market_eth` | LEGACY (entfernt 2026-06-18, #3303) | `absent` — kein Container im BLUE/RED-Stack |

---

## Read-Only-Prüfung

```powershell
# cdb_node_exporter — Prüfen, ob ein Container läuft
docker ps --filter "name=cdb_node_exporter" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# cdb_node_exporter — Compose-Projekt-Herkunft prüfen
docker inspect cdb_node_exporter --format "{{index .Config.Labels `com.docker.compose.project`}}" 2>$null

# cdb_market_eth — Prüfen, ob ein Container läuft (Port 8011, Image claire_de_binare-cdb_market_eth)
docker ps --filter "name=cdb_market_eth" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"

# cdb_market_eth — V3-Env redacted prüfen (MARKET_V3_SYMBOL, MARKET_V3_CLIENT_ENABLED, MARKET_V3_LIVE_WRITE)
docker inspect cdb_market_eth --format "{{range .Config.Env}}{{println .}}{{end}}" 2>$null | Select-String "MARKET_V3|MARKET_PORT"
```

---

## Klassifikation

| Befund | Klassifikation | Aktion |
|--------|---------------|--------|
| Kein Container | **OK** — erwarteter Zustand | Keine Aktion |
| Container läuft, Compose-Projekt = `claire_de_binare` oder `cdb_*` | **Unerwarteter Runtime-Drift** — Container aus historischem Compose-Projekt (vor #1528-Bereinigung) | Gordon-Gate einholen; keine selbstständige Container-Mutation |
| Container läuft, kein Compose-Projekt-Label | **Unerwarteter Runtime-Drift** — Container manuell oder extern gestartet | Gordon-Gate einholen; keine selbstständige Container-Mutation |

---

## Bereinigung (nur mit Gordon-Gate)

```powershell
# cdb_node_exporter — Container stoppen und entfernen (nur nach explizitem Gordon-Go)
docker stop cdb_node_exporter
docker rm cdb_node_exporter

# cdb_market_eth — Container stoppen und entfernen (nur nach explizitem Gordon-Go)
# Image-Remove erfordert separates Gordon-Go (forensische Nachvollziehbarkeit).
# Keine Reaktivierung ohne eigenes Design-/Evidence-Issue.
docker stop cdb_market_eth
docker rm cdb_market_eth
```

---

## Referenzen

- `knowledge/governance/SERVICE_CATALOG.md` — Entfernte Services (Legacy)
- `infrastructure/compose/SERVICE_MAPPING.md` — Removed Services
- `infrastructure/docs/BLUE_RED_SPLIT.md` — Removed Services
- `infrastructure/monitoring/METRICS_MATRIX.md` — Canon- und Dokudrift (§4)
- Issue #1528 — ursprüngliche Bereinigung `cdb_node_exporter` (CLOSED, PR #1535)
- Issue #3302 — Audit `cdb_node_exporter` (dieses Runbook)
- Issue #3303 — Audit + Decommission `cdb_market_eth`
- Issue #1596 — 503-Bug cdb_market/cdb_market_eth (CLOSED)
- Issue #1206 — ursprünglicher V3-Market-Branch (nicht auf main)
