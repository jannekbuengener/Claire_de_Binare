# GitHub Milestones für Claire de Binare

## Übersicht

Dieses Verzeichnis enthält die Definition und Erstellung der 9 Haupt-Milestones für das Claire de Binare Projekt.

## Dateien

- **create_milestones.sh** - Bash-Script zum Erstellen aller Milestones via gh CLI
- **milestones.json** - JSON-Definition aller Milestones (für Referenz/Backup)
- **MILESTONES_README.md** - Diese Datei (Anleitung)

## Voraussetzungen

### 1. GitHub CLI Installation

**macOS:**
```bash
brew install gh
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install gh
```

**Windows:**
```bash
winget install GitHub.cli
```

### 2. Authentifizierung

```bash
# Status prüfen
gh auth status

# Falls nicht eingeloggt
gh auth login
```

## Milestones erstellen

### Schritt 1: Script ausführbar machen (Linux/Mac)

```bash
chmod +x create_milestones.sh
```

### Schritt 2: Script ausführen

```bash
bash create_milestones.sh
```

### Schritt 3: Verifizierung

```bash
gh milestone list
```

**Erwartete Ausgabe:**
```
M1 - Foundation & Governance Setup                    open   0 issues
M2 - N1 Architektur Finalisierung                     open   0 issues
M3 - Risk-Layer Hardening & Guards                    open   0 issues
M4 - Event-Driven Core (Redis Pub/Sub)                open   0 issues
M5 - Persistenz + Analytics Layer                     open   0 issues
M6 - Dockerized Runtime (Local Environment)           open   0 issues
M7 - Initial Live-Test (MEXC Testnet)                 open   0 issues
M8 - Production Hardening & Security Review           open   0 issues
M9 - Production Release 1.0                           open   0 issues
```

## Die 9 Milestones im Detail

### M1 - Foundation & Governance Setup
**Status:** 🟢 In Progress
**Zweck:** Projekt-Grundlage etablieren

- KODEX (Projektphilosophie)
- ADRs (Architecture Decision Records)
- Entwicklungs-Standards
- Repository-Struktur

### M2 - N1 Architektur Finalisierung
**Status:** 🟡 Planned
**Zweck:** Paper-Trading Architektur abschließen

- System-Design finalisieren
- Service-Boundaries definieren
- Event-Flows dokumentieren
- Database-Schema erstellen

### M3 - Risk-Layer Hardening & Guards
**Status:** 🟡 Planned
**Zweck:** Risk-Management implementieren

- 7 Risk-Validierungs-Layer
- 100% Test-Coverage
- ENV-gesteuerte Limits
- Circuit-Breaker

### M4 - Event-Driven Core (Redis Pub/Sub)
**Status:** 🟡 Planned
**Zweck:** Message-Bus aufbauen

- Redis Pub/Sub Integration
- Event-Types definieren
- Routing & Error-Handling
- Message-Serialization

### M5 - Persistenz + Analytics Layer
**Status:** 🟡 Planned
**Zweck:** Datenbank & Analytics

- PostgreSQL Integration
- 5 Core-Tabellen
- Analytics-Queries
- Reporting-Layer

### M6 - Dockerized Runtime (Local Environment)
**Status:** 🟡 Planned
**Zweck:** Containerisierung

- docker-compose Setup
- 8 Services (Redis, PostgreSQL, etc.)
- Health-Checks
- Development-Environment

### M7 - Initial Live-Test (MEXC Testnet)
**Status:** 🔴 Not Started
**Zweck:** Erste Live-Integration

- MEXC Testnet Anbindung
- Paper-Trading mit echten Daten
- Performance-Validierung
- Stability-Testing

### M8 - Production Hardening & Security Review
**Status:** 🔴 Not Started
**Zweck:** Production-Readiness

- Security-Audit
- Penetration-Testing
- Secret-Management
- Load-Testing

### M9 - Production Release 1.0
**Status:** 🔴 Not Started
**Zweck:** Production-Release

- Vollständige Dokumentation
- Deployment-Playbooks
- Monitoring-Dashboards
- 24/7 Operations

## Milestone-Management

### Issues zu Milestone zuordnen

```bash
# Via gh CLI
gh issue edit <issue-number> --milestone "M1 - Foundation & Governance Setup"

# Via Web-UI
https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones
```

### Milestone-Status prüfen

```bash
# Liste aller Milestones
gh milestone list

# Details zu spezifischem Milestone
gh milestone view "M1 - Foundation & Governance Setup"
```

### Milestone abschließen

```bash
gh milestone edit "M1 - Foundation & Governance Setup" --state closed
```

## Troubleshooting

### Problem: gh CLI nicht gefunden

**Lösung:**
```bash
# Installation prüfen
which gh

# Neuinstallation
brew install gh  # macOS
```

### Problem: Nicht authentifiziert

**Lösung:**
```bash
gh auth login
```

### Problem: Milestone existiert bereits

**Fehler:**
```
already exists: milestone with name "M1 - Foundation & Governance Setup" already exists
```

**Lösung:**
1. Prüfen: `gh milestone list`
2. Falls doppelt: Manuell in Web-UI löschen
3. Script erneut ausführen

### Problem: Keine Berechtigung

**Fehler:**
```
HTTP 403: Resource not accessible by integration
```

**Lösung:**
```bash
# Token-Scopes prüfen
gh auth status

# Neu einloggen mit erweiterten Scopes
gh auth login --scopes repo,write:org
```

## Nächste Schritte

Nach erfolgreicher Erstellung der Milestones:

1. **Issues erstellen** - Für jeden Milestone relevante Issues anlegen
2. **Issues zuordnen** - Issues zu passenden Milestones mappen
3. **Projekt-Board** - GitHub Projects Board mit Milestones verknüpfen
4. **Progress-Tracking** - Regelmäßig Milestone-Status aktualisieren

## Ressourcen

- [GitHub Milestones Docs](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones)
- [gh CLI Milestone Commands](https://cli.github.com/manual/gh_milestone)
- [Project Status](../backoffice/PROJECT_STATUS.md)

---

**Erstellt:** 2025-11-20
**Projekt:** Claire de Binare - Autonomous Crypto Trading Bot
**Phase:** N1 - Paper Trading Implementation
