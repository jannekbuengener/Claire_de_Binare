# Prompt für Claude Code (Terminal)

> **Copy & Paste diesen Prompt in dein Terminal mit Claude Code**

---

## 🎯 Aufgabe

Erstelle die 9 GitHub Milestones für das Claire de Binaire Projekt.

## 📋 Kontext

Du findest im aktuellen Verzeichnis:
- `create_milestones.sh` - Bash-Script mit allen gh-Befehlen
- `milestones.json` - JSON-Daten für die Milestones
- `MILESTONES_README.md` - Detaillierte Anleitung

## ✅ Deine Aufgabe

1. **Prüfe ob `gh` CLI installiert ist**:
   ```bash
   gh --version
   ```
   - Falls NICHT installiert: Installiere `gh` CLI für dein OS
   - Falls installiert: Gehe zu Schritt 2

2. **Prüfe ob `gh` authentifiziert ist**:
   ```bash
   gh auth status
   ```
   - Falls NICHT authentifiziert: Führe `gh auth login` aus und folge den Anweisungen
   - Falls authentifiziert: Gehe zu Schritt 3

3. **Führe das Milestone-Script aus**:
   ```bash
   bash create_milestones.sh
   ```

4. **Verifiziere das Ergebnis**:
   ```bash
   gh milestone list
   ```
   - Erwartete Ausgabe: 9 Milestones (M1 - M9)

## 🔧 Troubleshooting

### Falls `gh` nicht installiert ist:

**macOS**:
```bash
brew install gh
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install gh
```

**Linux (andere Distros)**:
```bash
# Siehe: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
```

**Windows**:
```powershell
scoop install gh
# oder via winget:
winget install --id GitHub.cli
```

### Falls Authentifizierung fehlschlägt:

```bash
gh auth login
# Wähle:
# - GitHub.com
# - HTTPS
# - Login with a web browser (empfohlen)
# Folge dem Link und authorisiere
```

### Falls Script-Fehler:

```bash
# Mache Script ausführbar
chmod +x create_milestones.sh

# Führe erneut aus
bash create_milestones.sh
```

## 📊 Erwartetes Ergebnis

Nach erfolgreicher Ausführung solltest du sehen:

```
🎯 Erstelle GitHub Milestones für Claire de Binaire...

📋 Erstelle M1 - Foundation & Governance Setup...
✓ Created milestone M1 - Foundation & Governance Setup

🏗️ Erstelle M2 - N1 Architektur Finalisierung...
✓ Created milestone M2 - N1 Architektur Finalisierung

🛡️ Erstelle M3 - Risk-Layer Hardening & Guards...
✓ Created milestone M3 - Risk-Layer Hardening & Guards

📡 Erstelle M4 - Event-Driven Core (Redis Pub/Sub)...
✓ Created milestone M4 - Event-Driven Core (Redis Pub/Sub)

💾 Erstelle M5 - Persistenz + Analytics Layer...
✓ Created milestone M5 - Persistenz + Analytics Layer

🐳 Erstelle M6 - Dockerized Runtime (Local Environment)...
✓ Created milestone M6 - Dockerized Runtime (Local Environment)

🧪 Erstelle M7 - Initial Live-Test (MEXC Testnet)...
✓ Created milestone M7 - Initial Live-Test (MEXC Testnet)

🔒 Erstelle M8 - Production Hardening & Security Review...
✓ Created milestone M8 - Production Hardening & Security Review

🚀 Erstelle M9 - Production Release 1.0...
✓ Created milestone M9 - Production Release 1.0

✅ Alle 9 Milestones erstellt!
```

## 🌐 Web-Verifikation

Nach dem Erstellen kannst du die Milestones auch im Browser prüfen:

https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones

---

**Hinweis**: Falls du weiterhin Probleme hast, kannst du die Milestones auch manuell über die GitHub Web UI erstellen (siehe `MILESTONES_README.md`).
