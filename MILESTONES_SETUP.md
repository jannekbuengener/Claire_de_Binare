# GitHub Milestones Setup - Alternativen ohne gh CLI

Da `gh` CLI in dieser Umgebung nicht verfügbar ist, hier die Alternativen:

## Option 1: Python-Script (empfohlen für diese Umgebung)

### Schritt 1: GitHub Token erstellen

1. Gehe zu: https://github.com/settings/tokens/new
2. Name: `Claire Milestones`
3. Expiration: `90 days` (oder länger)
4. Scopes auswählen:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `repo:status` (Access commit status)
   - ✅ `public_repo` (Access public repositories)
5. Klicke **Generate token**
6. Kopiere den Token (wird nur einmal angezeigt!)

### Schritt 2: Token setzen

```bash
# Linux/Mac
export GITHUB_TOKEN=your_github_token_here

# Windows PowerShell
$env:GITHUB_TOKEN="your_github_token_here"

# Windows CMD
set GITHUB_TOKEN=your_github_token_here
```

### Schritt 3: Python-Script ausführen

```bash
# Im Projekt-Root
python create_milestones.py
```

**Erwartete Ausgabe:**
```
🚀 Creating GitHub Milestones for Claire de Binaire...

✅ Created: M1 - Foundation & Governance Setup
✅ Created: M2 - N1 Architektur Finalisierung
✅ Created: M3 - Risk-Layer Hardening & Guards
✅ Created: M4 - Event-Driven Core (Redis Pub/Sub)
✅ Created: M5 - Persistenz + Analytics Layer
✅ Created: M6 - Dockerized Runtime (Local Environment)
✅ Created: M7 - Initial Live-Test (MEXC Testnet)
✅ Created: M8 - Production Hardening & Security Review
✅ Created: M9 - Production Release 1.0

✅ Successfully created/verified 9/9 milestones!
```

### Schritt 4: Verifizierung

Prüfe in GitHub Web-UI:
```
https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones
```

---

## Option 2: gh CLI auf lokalem System

Falls du gh CLI auf deinem Windows/Mac System hast:

```bash
# Navigiere zum Repo
cd C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Cleanroom

# Authentifizieren (falls noch nicht)
gh auth login

# Script ausführen
bash create_milestones.sh
```

---

## Option 3: Manuell in GitHub Web-UI

1. Gehe zu: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones/new
2. Erstelle jeden Milestone manuell:

**M1 - Foundation & Governance Setup**
- Title: `M1 - Foundation & Governance Setup`
- Description: `Establish project foundation with documentation, governance structures, and development standards. Includes KODEX, ADRs, and initial architecture decisions.`

**M2 - N1 Architektur Finalisierung**
- Title: `M2 - N1 Architektur Finalisierung`
- Description: `Finalize N1 (Paper Trading) architecture. Complete system design, service boundaries, event flows, and database schema. Ready for implementation phase.`

... (siehe `milestones.json` für vollständige Liste)

---

## Troubleshooting

### Problem: `gh: command not found`

**Ursache:** gh CLI nicht installiert

**Lösung:** Nutze Python-Script (Option 1) oder installiere gh CLI:

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

### Problem: `GITHUB_TOKEN not set`

**Ursache:** Environment-Variable fehlt

**Lösung:**
1. Token erstellen (siehe oben)
2. Token exportieren:
   ```bash
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   ```

### Problem: `HTTP 422: Validation Failed (already_exists)`

**Ursache:** Milestone existiert bereits

**Lösung:** Das ist OK! Das Script überspringt existierende Milestones automatisch.

### Problem: `HTTP 401: Bad credentials`

**Ursache:** Ungültiger oder abgelaufener Token

**Lösung:**
1. Neuen Token erstellen
2. Token neu exportieren
3. Script erneut ausführen

---

## Nächste Schritte nach Erstellung

1. **Issues erstellen** - Für jeden Milestone relevante Issues anlegen
2. **Issues zuordnen** - Issues zu passenden Milestones mappen
3. **Projekt-Board** - GitHub Projects Board mit Milestones verknüpfen
4. **Progress-Tracking** - Regelmäßig Milestone-Status aktualisieren

---

**Erstellt:** 2025-11-20
**Projekt:** Claire de Binaire
**Status:** Ready for execution
