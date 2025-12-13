# SYSTEM_CONTEXT – Runtime Facts (v1.0)

## Betriebssystem
- Windows 11
- WSL2 (Linux)

## Runtime
- Docker Desktop
- Docker Compose
- Zielbild: Kubernetes

## Hardware (deklarativ)
- Lokales Entwickler-System
- Ressourcen variabel

## Zweck
Reiner Kontext für Performance- und Infra-Entscheidungen.
Keine Governance.

## WSL2 Global Configuration for Docker Desktop on Windows 10

# CDB stack: Grafana, Prometheus, Loki, Agents
[wsl2]

# Limit RAM usage to avoid Windows slowdown and Docker overload
memory=8GB

# Allocate enough CPU cores for parallel container workloads
processors=8

# Controlled swap size for stable performance without thrashing
swap=4GB

# Allow localhost networking between Windows <-> WSL2
localhostForwarding=true

# Prevent VHDX disk images from growing endlessly
defaultVhdSize=256GB

---

## Runtime-Status & Validierungen

### Post-Migration Check (2025-12-13 01:53 UTC+1)
**Quelle:** Claude - Strukturelle Validierung nach t1/ Migration

**docker-compose.yml Validierung:**
- ✅ FIXED (02:02 UTC+1): Pfade korrigiert
  - Schema-Mount entfernt (Datei existiert nicht)
  - Grafana: `./infrastructure/monitoring/grafana/`
  - Prometheus: `./infrastructure/monitoring/prometheus.yml`
  - Services: `./services/signal/`, `/risk/`, `/execution/`, `/db_writer/`
- ⚠️ Env-Vars fehlen weiterhin: POSTGRES_USER, POSTGRES_DB, GRAFANA_PASSWORD (expected - .env nicht erstellt)

**Service-Import-Check (Stichprobe: services/risk/service.py):**
- ❌ FAIL: Import `from ..common.models import Signal` bricht
- Ursache: `/common/` Verzeichnis existiert nicht
- Erwartung: Shared Models sollten in `/core/domain/` liegen (aktuell leer)

**Tier-Migration Status (2025-12-13 02:10 UTC+1):**
- ✅ t1/ migriert (Essential Core: Services, Infrastructure, Tests)
- ✅ t2/ migriert (Tools: Scripts, GitHub Templates, Migration Archive)
- ✅ t3/ migriert (Research: Portfolio Manager, Paper Trading, Utilities)

**Empfohlene Sofortmaßnahmen:**
1. `.env` Datei erstellen (Template: `.env.example`)
2. Shared Models nach `/core/domain/models.py` migrieren
3. Service-Imports anpassen: `from core.domain.models import Signal`

