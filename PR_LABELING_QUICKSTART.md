# Pull Request Labeling - Schnellstart

## TL;DR

```bash
# Bash-Version (empfohlen)
./label_all_prs.sh

# Oder Python-Version
python3 label_all_prs.py
```

## Was macht das?

Dieses Tool versieht **ALLE** Pull Requests im Repository automatisch mit passenden Labels basierend auf:

- **Titel-Analyse**: Conventional Commit Präfixe (`feat:`, `fix:`, `docs:`, etc.)
- **Keyword-Erkennung**: Betroffene Services (risk-engine, signal-engine, execution, etc.)
- **Beschreibungs-Analyse**: Fallback wenn Titel nicht eindeutig

## Voraussetzungen

### 1. GitHub CLI installieren

**macOS**:
```bash
brew install gh
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install gh
```

**Windows**:
```powershell
winget install GitHub.cli
```

### 2. Authentifizierung

```bash
gh auth login
```

Folge den Anweisungen im Terminal.

## Ausführung

### Option 1: Bash-Skript (Empfohlen)

```bash
# Ausführbar machen (einmalig)
chmod +x label_all_prs.sh

# Ausführen
./label_all_prs.sh
```

**Vorteile**:
- ✅ Schneller
- ✅ Keine zusätzlichen Dependencies
- ✅ Ausführlicher Output

### Option 2: Python-Skript

```bash
# Ausführen
python3 label_all_prs.py
```

**Vorteile**:
- ✅ Plattformunabhängig
- ✅ Leichter erweiterbar
- ✅ JSON-basierte Konfiguration

## Was wird gelabelt?

### Typ-Labels

| Label | Trigger | Beispiel |
|-------|---------|----------|
| `feat` | `feat:`, `feature:` | `feat: add new risk check` |
| `fix` | `fix:`, `bugfix:` | `fix: resolve import error` |
| `docs` | `docs:`, `documentation:` | `docs: update README` |
| `test` | `test:`, `tests:` | `test: add risk engine tests` |
| `refactor` | `refactor:` | `refactor: clean up service code` |
| `chore` | `chore:` | `chore: update dependencies` |
| `ci` | `ci:`, `ci/cd:` | `ci: extend pipeline` |

### Bereichs-Labels

| Label | Keywords | Beispiel |
|-------|----------|----------|
| `risk-engine` | risk, risk-engine | `feat(risk-engine): add circuit breaker` |
| `signal-engine` | signal, signal-engine | `fix(signal): timing issue` |
| `execution` | execution, exec | `test(execution): integration tests` |
| `testing` | test, pytest, coverage | `chore: extend test infrastructure` |
| `infrastructure` | docker, compose, deployment | `feat: dockerized runtime` |
| `security` | security, secrets | `fix(security): env variable leak` |
| `performance` | performance, optimization | `refactor: optimize query performance` |

### Automatisch erkannt

- **Dependabot PRs**: Automatisch `dependencies` + `chore`
- **Breaking Changes**: Bei `!` oder `BREAKING` im Titel
- **Multi-Labels**: Ein PR kann mehrere Labels bekommen (z.B. `feat` + `risk-engine` + `testing`)

## Nach der Ausführung

### Ergebnisse prüfen

```bash
# Alle PRs mit Labels anzeigen
gh pr list --state all --limit 50

# Spezifische Label-Gruppe
gh pr list --label "risk-engine" --state all
gh pr list --label "testing" --state all
```

### Manuelle Nachbearbeitung

PRs die mit ⚠️ markiert wurden, sollten manuell geprüft werden:

```bash
# Label zu PR hinzufügen
gh pr edit <PR_NUMBER> --add-label "label-name"

# Label entfernen
gh pr edit <PR_NUMBER> --remove-label "label-name"

# PR ansehen
gh pr view <PR_NUMBER>
```

## Beispiel-Output

```
🏷️  Label-Bot für Claire de Binare Pull Requests
==================================================

Schritt 1: Prüfe GitHub CLI...
✅ Authentifiziert

Schritt 2: Hole alle Pull Requests...
📊 Gefunden: 7 Pull Requests

Schritt 3: Prüfe verfügbare Labels...
🏷️  Verfügbare Labels: 14

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR #7: test: comprehensive local-only test suite
Status: closed | Merged: true

🏷️  Labels zu vergeben: test testing
  → Füge Label hinzu: test
  → Füge Label hinzu: testing
✅ Labels hinzugefügt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR #6: chore(deps): bump runtime images
Status: closed | Merged: true

🏷️  Labels zu vergeben: chore dependencies infrastructure
  → Füge Label hinzu: chore
  → Füge Label hinzu: dependencies
  → Füge Label hinzu: infrastructure
✅ Labels hinzugefügt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Fertig!

📊 Statistik:
   Gesamt PRs:     7
   Gelabelt:       7
   Nicht gelabelt: 0
```

## Troubleshooting

### "Permission denied"

```bash
chmod +x label_all_prs.sh
# oder
chmod +x label_all_prs.py
```

### "gh: command not found"

GitHub CLI ist nicht installiert:

```bash
# macOS
brew install gh

# Linux
sudo apt install gh

# Windows
winget install GitHub.cli
```

### "Not authenticated"

```bash
gh auth login
```

### Labels werden nicht hinzugefügt

1. Prüfe ob du Schreibrechte auf dem Repository hast:
   ```bash
   gh repo view jannekbuengener/Claire_de_Binare_Cleanroom
   ```

2. Prüfe ob Labels existieren:
   ```bash
   gh label list
   ```

3. Manuelle Label-Erstellung:
   ```bash
   gh label create "feat" --description "Feature" --color "0e8a16"
   ```

## Konfiguration anpassen

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

### Nur bestimmte PRs labeln

**Nur offene PRs**:
```bash
# In label_all_prs.sh, Zeile 45 ändern:
PRS_JSON=$(gh api repos/$REPO/pulls?state=open --paginate)
```

**Nur PRs mit bestimmtem Label**:
```bash
gh pr list --label "needs-labeling" --json number,title,body
```

## Dateien-Übersicht

| Datei | Zweck |
|-------|-------|
| `label_all_prs.sh` | Bash-Skript für automatisches Labeling |
| `label_all_prs.py` | Python-Alternative |
| `pr_labels.json` | Label-Definitionen und Regeln |
| `PR_LABELS.md` | Ausführliche Dokumentation |
| `PR_LABELING_QUICKSTART.md` | Diese Datei |

## Best Practices

### 1. Conventional Commits verwenden

```bash
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
refactor: improve code
chore: update dependencies
ci: extend pipeline
```

### 2. Service-Namen in Titel einbauen

```bash
feat(risk-engine): add circuit breaker
fix(signal): resolve timing issue
test(execution): add integration tests
```

### 3. Keywords in Beschreibung

Wenn Titel nicht ausreicht, Keywords in PR-Beschreibung verwenden:

```markdown
## Summary
This PR adds comprehensive testing infrastructure for the risk-engine.

## Changes
- pytest fixtures
- coverage reports
- integration tests
```

## Weiterführende Links

- [GitHub CLI Dokumentation](https://cli.github.com/manual/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Labels Best Practices](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels)

## Support

Bei Fragen oder Problemen: Jannek Büngener

---

**Version**: 1.0.0
**Letzte Aktualisierung**: 2025-11-22
