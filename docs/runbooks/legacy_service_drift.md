# Legacy Service Drift — Operator-Prüfpfad

**Erstellt:** 2026-06-18 (Audit #3302)
**Scope:** Erkennung und Klassifikation unerwarteter Legacy-Container im BLUE+RED-Stack
**Referenz:** `knowledge/governance/SERVICE_CATALOG.md` § Entfernte Services (Legacy)

---

## Betroffener Service

| Service | Status | Erwarteter Runtime-Zustand |
|---------|--------|---------------------------|
| `cdb_node_exporter` | LEGACY (entfernt 2026-04-09, #1528/PR #1535) | `absent` — kein Container im BLUE/RED-Stack |

---

## Read-Only-Prüfung

```powershell
# Prüfen, ob ein cdb_node_exporter-Container läuft
docker ps --filter "name=cdb_node_exporter" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# Prüfen, ob der Container aus einem bestimmten Compose-Projekt stammt
docker inspect cdb_node_exporter --format "{{index .Config.Labels `com.docker.compose.project`}}" 2>$null
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
# Container stoppen und entfernen (nur nach explizitem Gordon-Go)
docker stop cdb_node_exporter
docker rm cdb_node_exporter
```

---

## Referenzen

- `knowledge/governance/SERVICE_CATALOG.md` — Entfernte Services (Legacy)
- `infrastructure/compose/SERVICE_MAPPING.md` — Removed Services
- `infrastructure/docs/BLUE_RED_SPLIT.md` — Removed Services
- `infrastructure/monitoring/METRICS_MATRIX.md` — Canon- und Dokudrift (§4)
- Issue #1528 — ursprüngliche Bereinigung (CLOSED, PR #1535)
- Issue #3302 — aktuelles Audit (dieses Runbook)
