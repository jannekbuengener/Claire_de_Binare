# Pull Request Auto-Labeling System

## 📋 Übersicht

Dieses Verzeichnis enthält ein vollautomatisches Label-System für alle Pull Requests im Claire de Binaire Cleanroom Repository.

## 🚀 Schnellstart

```bash
# Option 1: Bash (empfohlen)
./label_all_prs.sh

# Option 2: Python
python3 label_all_prs.py
```

## 📁 Dateien

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `label_all_prs.sh` | 213 | Bash-Skript für automatisches Labeling |
| `label_all_prs.py` | 300 | Python-Alternative mit JSON-Config |
| `pr_labels.json` | 135 | Label-Definitionen und Regeln |
| `PR_LABELING_QUICKSTART.md` | 322 | Schnellstart-Anleitung |
| `PR_LABELS.md` | 203 | Ausführliche Dokumentation |
| `README_PR_LABELING.md` | - | Diese Datei |

**Gesamt**: 1.173 Zeilen Code & Dokumentation

## 🎯 Was macht das System?

### Automatische Label-Zuweisung

Das System analysiert:

1. **PR-Titel**: Conventional Commit Präfixe (`feat:`, `fix:`, `docs:`, etc.)
2. **PR-Beschreibung**: Keywords für Service-Zuordnung
3. **Commit-Messages**: Zusätzlicher Kontext

### Unterstützte Labels

#### Typ-Labels (7)
- `feat` - Neue Funktionalität
- `fix` - Fehlerbehebung
- `docs` - Dokumentation
- `test` - Tests
- `refactor` - Code-Verbesserung
- `chore` - Wartung/Tooling
- `ci` - CI/CD Änderungen

#### Bereichs-Labels (7)
- `risk-engine` - Risk Manager Service
- `signal-engine` - Signal Engine Service
- `execution` - Execution Service
- `testing` - Test-Infrastruktur
- `infrastructure` - Docker/Deployment
- `security` - Sicherheit
- `performance` - Performance-Optimierung

#### Spezial-Labels (6)
- `dependencies` - Dependency-Updates
- `breaking-change` - Breaking Changes
- `needs-review` - Wartet auf Review
- `work-in-progress` - Noch nicht bereit
- `good-first-issue` - Gut für Einsteiger
- `help-wanted` - Hilfe benötigt

**Gesamt**: 20 Standard-Labels

## 🔧 Voraussetzungen

### GitHub CLI

**Installation**:
```bash
# macOS
brew install gh

# Linux (Ubuntu/Debian)
sudo apt install gh

# Windows
winget install GitHub.cli
```

**Authentifizierung**:
```bash
gh auth login
```

## 📊 Beispiel-Output

```
🏷️  Label-Bot für Claire de Binaire Pull Requests
==================================================

Schritt 1: Prüfe GitHub CLI...
✅ Authentifiziert

Schritt 2: Hole alle Pull Requests...
📊 Gefunden: 7 Pull Requests

Schritt 3: Prüfe verfügbare Labels...
🏷️  Verfügbare Labels: 14

Schritt 4: Analysiere Pull Requests...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR #7: test: comprehensive local-only test suite
Status: closed | Merged: true

🏷️  Labels: test, testing
✅ Labels hinzugefügt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR #6: chore(deps): bump runtime images
Status: closed | Merged: true

🏷️  Labels: chore, dependencies, infrastructure
✅ Labels hinzugefügt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Fertig!

📊 Statistik:
   Gesamt PRs:     7
   Gelabelt:       7
   Übersprungen:   0
```

## 🎨 Label-Beispiele

### Beispiel 1: Feature PR
```
Titel: feat(risk-engine): add circuit breaker
Labels: feat, risk-engine, security
```

### Beispiel 2: Bugfix PR
```
Titel: fix(signal): resolve timing issue in market data processing
Labels: fix, signal-engine
```

### Beispiel 3: Test PR
```
Titel: test: comprehensive E2E test suite with Docker
Labels: test, testing, infrastructure
```

### Beispiel 4: Documentation PR
```
Titel: docs: add Paper Trading guide and local E2E tests documentation
Labels: docs, testing
```

## 🔍 Verifikation

Nach Ausführung:

```bash
# Alle PRs mit Labels anzeigen
gh pr list --state all --limit 50

# Spezifische Label-Gruppe
gh pr list --label "risk-engine" --state all
gh pr list --label "testing" --state all

# Einzelnen PR ansehen
gh pr view <PR_NUMBER>
```

## 🛠️ Troubleshooting

### Problem: "Permission denied"

**Lösung**:
```bash
chmod +x label_all_prs.sh
chmod +x label_all_prs.py
```

### Problem: "gh: command not found"

**Lösung**: GitHub CLI installieren (siehe Voraussetzungen)

### Problem: "Not authenticated"

**Lösung**:
```bash
gh auth login
```

### Problem: Labels werden nicht hinzugefügt

**Ursachen**:
1. Keine Schreibrechte auf Repository
2. Labels existieren nicht (werden automatisch erstellt)
3. PR ist locked

**Debugging**:
```bash
# Prüfe Berechtigungen
gh repo view jannekbuengener/Claire_de_Binare_Cleanroom

# Prüfe vorhandene Labels
gh label list

# Manuelle Label-Erstellung
gh label create "feat" --description "Feature" --color "0e8a16"
```

## 📝 Konfiguration

### Eigene Label-Regeln

Editiere `pr_labels.json`:

```json
{
  "label_rules": {
    "type_labels": {
      "feat": ["feat:", "feature:"],
      "custom": ["custom:"]
    },
    "area_labels": {
      "my-service": ["my-service", "myservice"]
    }
  }
}
```

### Bash-Skript anpassen

Editiere `label_all_prs.sh`:

```bash
# Nur offene PRs labeln
PRS_JSON=$(gh api repos/$REPO/pulls?state=open --paginate)

# Nur PRs ab einer bestimmten Nummer
PRS_JSON=$(gh api repos/$REPO/pulls?state=all --paginate | jq '[.[] | select(.number >= 10)]')
```

## 🔗 Integration

### Pre-Commit Hook (optional)

```bash
# .git/hooks/pre-push
#!/bin/bash
python3 label_all_prs.py
```

### GitHub Actions (optional)

```yaml
# .github/workflows/label-prs.yml
name: Auto-label PRs
on:
  pull_request:
    types: [opened, edited]

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Label PR
        run: |
          python3 label_all_prs.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 📚 Weiterführende Dokumentation

- **Schnellstart**: `PR_LABELING_QUICKSTART.md` (7KB, 322 Zeilen)
- **Ausführlich**: `PR_LABELS.md` (4.6KB, 203 Zeilen)
- **JSON-Config**: `pr_labels.json` (3.7KB, 135 Zeilen)

## 🎯 Best Practices

### 1. Conventional Commits

Verwende standardisierte Commit-Präfixe:

```bash
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
refactor: improve code
chore: update dependencies
ci: extend pipeline
```

### 2. Service-Namen im Titel

```bash
feat(risk-engine): add circuit breaker
fix(signal): resolve timing issue
test(execution): add integration tests
docs(infrastructure): Docker setup guide
```

### 3. Keywords in Beschreibung

Wenn Titel nicht ausreicht:

```markdown
## Summary
This PR adds comprehensive testing infrastructure for the **risk-engine**.

## Changes
- pytest fixtures for **testing**
- coverage reports
- **integration** tests with Docker
```

## 📊 Statistik

| Metrik | Wert |
|--------|------|
| Unterstützte Labels | 20 |
| Typ-Labels | 7 |
| Bereichs-Labels | 7 |
| Spezial-Labels | 6 |
| Code-Zeilen (Bash) | 213 |
| Code-Zeilen (Python) | 300 |
| Dokumentation | 660 Zeilen |
| Gesamt | 1.173 Zeilen |

## 🤝 Contribution

Bei Verbesserungsvorschlägen:

1. Neue Label-Regel in `pr_labels.json` hinzufügen
2. Logik in `label_all_prs.sh` oder `label_all_prs.py` anpassen
3. Dokumentation in `PR_LABELS.md` ergänzen
4. Pull Request erstellen (wird automatisch gelabelt! 😄)

## 📞 Support

Bei Fragen oder Problemen: **Jannek Büngener**

---

**Version**: 1.0.0
**Erstellt**: 2025-11-22
**Repository**: jannekbuengener/Claire_de_Binare_Cleanroom
