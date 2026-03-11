# Agent: docs_drift_sentry
# Scan Date: 2025-12-28
# Scope: Docs vs Reality Drift

---

## Facts (verifiziert)

### SERVICE_CATALOG.md Status
- **Speicherort**: Working Repo (`governance/SERVICE_CATALOG.md`)
- **Letztes Update**: 2025-12-28
- **Vollstaendigkeit**: KORREKT (alle Services dokumentiert)

### CLAUDE.md Port-Mapping
| Service | CLAUDE.md | Reality (dev.yml) | Status |
|---------|-----------|-------------------|--------|
| ws | 8000 | 8000 | OK |
| signal (cdb_core) | 8001 | 8005 | DRIFT |
| risk | 8002 | 8002 | OK |
| execution | 8003 | 8003 | OK |
| db_writer | - | - | OK |
| paper_runner | 8004 | 8004 | OK |

### CURRENT_STATUS.md
- **Aktualitaet**: 2025-12-28 20:15 CET
- **Inhalt**: Governance Audit Phase 1 dokumentiert
- **Issues**: 6 geschlossen, korrekt referenziert
- **Blocker**: Secrets rotieren (korrekt dokumentiert)

### Compose File Naming
| Datei | Referenziert | Actual Container Name | Status |
|-------|--------------|----------------------|--------|
| prod.yml | cdb_core | (sollte cdb_signal sein) | DRIFT |
| tls.yml | cdb_core | (sollte cdb_signal sein) | DRIFT |
| dev.yml | cdb_signal | cdb_signal | OK |

---

## Assumptions (zu validieren)

1. **PSM Service Nicht-Existenz**: CLAUDE.md erwaehnt "psm" Service, aber dieser existiert nicht als separater Container
   - Paper Runner implementiert PSM-artige Logik

2. **AGENTS.md Autoload**: Referenziert nicht SERVICE_CATALOG.md und ARCHITECTURE_MAP.md
   - Diese Dateien fehlen in der Autoload-Liste

---

## Gaps (identifiziert)

### KRITISCHE DRIFTS

1. **Port Mismatch Signal Service**
   - CLAUDE.md: Port 8001
   - Reality: Port 8005
   - **Action**: CLAUDE.md korrigieren

2. **Naming Mismatch prod.yml/tls.yml**
   - Diese Dateien verwenden `cdb_core`
   - dev.yml verwendet korrekt `cdb_signal`
   - **Action**: prod.yml und tls.yml aktualisieren

3. **ARCHITECTURE_MAP.md fehlt**
   - Im Task gefordert, existiert noch nicht
   - **Action**: Erstellen (Ziel dieses Sprints)

### AUTOLOAD GAPS

4. **AGENTS.md Autoload-Liste unvollstaendig**
   - Fehlt: governance/SERVICE_CATALOG.md
   - Fehlt: knowledge/ARCHITECTURE_MAP.md (sobald erstellt)
   - **Action**: AGENTS.md erweitern

5. **CLAUDE.md Autoload-Liste unvollstaendig**
   - Fehlt: "Service SOLL vs IST" Check-Requirement
   - **Action**: CLAUDE.md erweitern

### DOKUMENTATIONS-GAPS

6. **SERVICE_CATALOG.md im falschen Repo**
   - Liegt im Working Repo unter `governance/`
   - Sollte im Docs Repo unter `knowledge/` oder `governance/` liegen
   - **Status**: Akzeptabel (Governance-Naehe zum Code)

7. **SYSTEM.CONTEXT.md**
   - Erwaehnt Kubernetes als "Zielbild (nicht aktiv)"
   - K8s-Readiness nicht verifiziert

---

## Source Pointers

- `D:\Dev\Workspaces\Repos\Claire_de_Binare\governance\SERVICE_CATALOG.md`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs\knowledge\CURRENT_STATUS.md`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs\agents\AGENTS.md`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs\agents\CLAUDE.md`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\prod.yml`
- `D:\Dev\Workspaces\Repos\Claire_de_Binare\infrastructure\compose\tls.yml`
