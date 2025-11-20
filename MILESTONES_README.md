# GitHub Milestones für Claire de Binaire

Dieses Verzeichnis enthält zwei Optionen zum Erstellen der 9 Projekt-Milestones bei GitHub.

---

## Option 1: Bash-Script (empfohlen)

**Schnellste Methode** - Erstellt alle Milestones mit einem Befehl:

```bash
bash create_milestones.sh
```

**Voraussetzung**: `gh` CLI muss installiert und authentifiziert sein:
```bash
# gh CLI installieren (falls nicht vorhanden)
# macOS: brew install gh
# Linux: siehe https://cli.github.com/
# Windows: scoop install gh

# Authentifizierung
gh auth login
```

---

## Option 2: Manuelle Erstellung via GitHub Web UI

Falls das Script nicht funktioniert, können Sie die Milestones manuell anlegen:

1. Gehe zu: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones
2. Klicke auf "New milestone"
3. Kopiere Titel und Beschreibung aus `milestones.json`

### Milestone-Übersicht

| Nr | Titel | Beschreibung |
|----|-------|--------------|
| M1 | Foundation & Governance Setup | Projektstruktur, Regeln, Standards |
| M2 | N1 Architektur Finalisierung | Logische Systemarchitektur als Issues |
| M3 | Risk-Layer Hardening & Guards | Risk-Parameter, ENV-Variablen, Konfigs |
| M4 | Event-Driven Core (Redis Pub/Sub) | Vollständiges Event-Gerüst |
| M5 | Persistenz + Analytics Layer | Datenhaltung, Logging, Backtests |
| M6 | Dockerized Runtime (Local Environment) | Produktionsnahe lokale Umgebung |
| M7 | Initial Live-Test (MEXC Testnet) | Expeditionelle Phase |
| M8 | Production Hardening & Security Review | Finale Absicherung |
| M9 | Production Release 1.0 | Abschluss-Meilenstein |

---

## Option 3: GitHub API (für Fortgeschrittene)

Falls Sie die GitHub API direkt verwenden möchten:

```bash
# Authentifizierung mit Personal Access Token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"

# Milestones via API erstellen
cat milestones.json | jq -r '.[] | @json' | while read milestone; do
  curl -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/repos/jannekbuengener/Claire_de_Binare_Cleanroom/milestones \
    -d "$milestone"
done
```

---

## Verifikation

Nach der Erstellung prüfen Sie:

```bash
# Via gh CLI
gh milestone list

# Via Web UI
# Besuche: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones
```

Erwartete Ausgabe: **9 Milestones** (M1-M9), alle im Status "open"

---

## Troubleshooting

### Problem: "gh: command not found"

**Lösung**: `gh` CLI installieren:
- **macOS**: `brew install gh`
- **Linux**: `sudo apt install gh` oder via snap
- **Windows**: `scoop install gh` oder via Installer

### Problem: "gh: not authenticated"

**Lösung**: Authentifizierung durchführen:
```bash
gh auth login
# Folge den Anweisungen im Terminal
```

### Problem: Script-Fehler "permission denied"

**Lösung**: Script ausführbar machen:
```bash
chmod +x create_milestones.sh
bash create_milestones.sh
```

---

**Erstellt**: 2025-11-20
**Für**: Claire de Binaire - Meilenstein-Setup
