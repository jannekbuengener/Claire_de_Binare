# Legacy Service Drift — Operator-Prüfpfad

**Erstellt:** 2026-06-18 (Audit #3302, #3304, #3305)
**Scope:** Erkennung und Klassifikation unerwarteter Legacy-/Referenz-Container im BLUE+RED-Stack inkl. Soak-Monitore, Scheduler-Tasks und MockX Valkey
**Referenz:** `knowledge/governance/SERVICE_CATALOG.md` § Entfernte Services (Legacy) und § Referenz-/Dev-Test-Infrastruktur

---

## Betroffene Services

| Service | Status | Erwarteter Runtime-Zustand |
|---------|--------|---------------------------|
| `cdb_node_exporter` | LEGACY (entfernt 2026-04-09, #1528/PR #1535) | `absent` — kein Container im BLUE/RED-Stack |
| `cdb_market_eth` | LEGACY (entfernt 2026-06-18, #3303) | `absent` — kein Container im BLUE/RED-Stack |
| `lr030_soak_monitor` | LEGACY (decommissioned 2026-06-18, #3304) | `absent` — kein Container; Windows-Task `CDB_Soak_Sidecar` deaktiviert |
| `lr040_soak_monitor` | LEGACY (decommissioned 2026-06-18, #3304) | `absent` — kein Container; Windows-Task `CDB_LR040_SoakMonitor` deaktiviert |
| `mockx-valkey` | Non-canonical dev/test reference infra (#3305, #1648) | `absent by default` — nur waehrend expliziter MockX test-pack Session |

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

# lr030_soak_monitor — Prüfen, ob ein Container läuft (Image ubuntu:22.04, kein Compose)
docker ps --filter "name=lr030_soak_monitor" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# lr040_soak_monitor — Prüfen, ob ein Container läuft (Image ubuntu:22.04, kein Compose)
docker ps --filter "name=lr040_soak_monitor" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# Soak Scheduler-Tasks — Prüfen, ob Windows-Tasks noch aktiv sind
Get-ScheduledTask -TaskName "CDB_LR040_SoakMonitor", "CDB_Soak_Sidecar" -ErrorAction SilentlyContinue | Format-Table TaskName, State

# mockx-valkey — Pruefen, ob ein Container laeuft (MockX reference/dev-test only)
docker ps --filter "name=mockx-valkey" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker ps -a --filter "name=mockx-valkey" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

# mockx-valkey — Herkunft redacted pruefen (keine Env-/Passwort-Ausgabe)
docker inspect mockx-valkey --format "Name={{.Name}}{{println}}Image={{.Config.Image}}{{println}}Status={{.State.Status}}{{println}}RestartPolicy={{.HostConfig.RestartPolicy.Name}}{{println}}Ports={{json .NetworkSettings.Ports}}{{println}}Mounts={{range .Mounts}}{{.Name}}:{{.Destination}}:{{.Type}};{{end}}{{println}}ComposeProject={{index .Config.Labels `"com.docker.compose.project"`}}{{println}}ComposeService={{index .Config.Labels `"com.docker.compose.service"`}}{{println}}ComposeWorkingDir={{index .Config.Labels `"com.docker.compose.project.working_dir"`}}{{println}}ComposeConfigFiles={{index .Config.Labels `"com.docker.compose.project.config_files"`}}" 2>$null
```

---

## Klassifikation

| Befund | Klassifikation | Aktion |
|--------|---------------|--------|
| Kein Container | **OK** — erwarteter Zustand | Keine Aktion |
| Container läuft, Compose-Projekt = `claire_de_binare` oder `cdb_*` | **Unerwarteter Runtime-Drift** — Container aus historischem Compose-Projekt (vor #1528-Bereinigung) | Jannek-Ops-GO einholen; keine selbstständige Container-Mutation |
| Container läuft, kein Compose-Projekt-Label | **Unerwarteter Runtime-Drift** — Container manuell oder extern gestartet | Jannek-Ops-GO einholen; keine selbstständige Container-Mutation |
| `mockx-valkey` läuft ausserhalb einer expliziten MockX test-pack Session | **Unerwarteter Reference-Infra-Drift** — non-canonical MockX Valkey ist nicht `cdb_redis` | Jannek-Ops-GO einholen; keine selbststaendige Container-Mutation; Volume/Image separat gate-pflichtig |

---

## Bereinigung (nur mit Jannek-Ops-GO)

```powershell
# cdb_node_exporter — Container stoppen und entfernen (nur nach explizitem Jannek-Ops-GO)
docker stop cdb_node_exporter
docker rm cdb_node_exporter

# cdb_market_eth — Container stoppen und entfernen (nur nach explizitem Jannek-Ops-GO)
# Image-Remove erfordert separates Jannek-Ops-GO (forensische Nachvollziehbarkeit).
# Keine Reaktivierung ohne eigenes Design-/Evidence-Issue.
docker stop cdb_market_eth
docker rm cdb_market_eth

# mockx-valkey — Container stoppen und entfernen (nur nach explizitem Jannek-Ops-GO)
# Volume/Image bleiben erhalten, ausser ein separates Jannek-Ops-GO erlaubt deren Cleanup.
docker stop mockx-valkey
docker rm mockx-valkey
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
- Issue #3304 — Audit + Decommission `lr030_soak_monitor` / `lr040_soak_monitor` + Scheduler `CDB_LR040_SoakMonitor` / `CDB_Soak_Sidecar`
- Issue #3305 — Audit + Cleanup `mockx-valkey` reference-infra drift
- Issue #1648 — Formalized `tools/test_pack/mock_exchange/` as local reference copy, not active CDB integration
