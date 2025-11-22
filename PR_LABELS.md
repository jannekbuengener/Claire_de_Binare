# Pull Request Labels - Anleitung

## Übersicht

Dieses Dokument beschreibt das automatische Label-System für alle Pull Requests im Claire de Binaire Cleanroom Repository.

## Ausführung

### Voraussetzungen

1. **GitHub CLI installiert**:
   ```bash
   # macOS
   brew install gh

   # Linux
   sudo apt install gh

   # Windows
   winget install GitHub.cli
   ```

2. **Authentifizierung**:
   ```bash
   gh auth login
   ```

### Skript ausführen

```bash
# Ausführbar machen
chmod +x label_all_prs.sh

# Ausführen
./label_all_prs.sh
```

## Label-Kategorien

### Typ-Labels (basierend auf Conventional Commits)

| Label | Beschreibung | Trigger-Keywords |
|-------|--------------|------------------|
| `feat` | Neue Funktionalität | `feat:`, `feature:` |
| `fix` | Fehlerbehebung | `fix:`, `bugfix:` |
| `docs` | Dokumentation | `docs:`, `documentation:` |
| `test` | Tests | `test:`, `tests:` |
| `refactor` | Code-Refactoring | `refactor:` |
| `chore` | Wartung/Tooling | `chore:` |
| `ci` | CI/CD Änderungen | `ci:`, `ci/cd:` |

### Bereichs-Labels

| Label | Beschreibung | Trigger-Keywords |
|-------|--------------|------------------|
| `risk-engine` | Risk Manager Service | `risk`, `risk-engine`, `risk_engine` |
| `signal-engine` | Signal Engine Service | `signal`, `signal-engine` |
| `execution` | Execution Service | `execution`, `exec` |
| `testing` | Test-Infrastruktur | `test`, `testing`, `pytest`, `coverage` |
| `infrastructure` | Docker/Deployment | `infrastructure`, `docker`, `compose` |
| `security` | Sicherheit | `security`, `secrets`, `audit` |
| `performance` | Performance | `performance`, `optimization`, `speed` |

### Spezial-Labels

| Label | Beschreibung | Trigger |
|-------|--------------|---------|
| `dependencies` | Dependency-Updates | `bump`, `dependabot`, `dependencies` |

## Label-Logik

Das Skript analysiert:

1. **PR-Titel** (primär):
   - Conventional Commit Präfixe (`feat:`, `fix:`, etc.)
   - Keywords im Titel

2. **PR-Beschreibung** (fallback):
   - Wenn keine Labels aus Titel, suche in Description

3. **Automatische Erstellung**:
   - Falls keine Labels im Repo existieren, werden Standard-Labels erstellt

## Manuelle Nachbearbeitung

Nach Skript-Ausführung solltest du folgende PRs manuell prüfen:

1. PRs ohne Labels (⚠️ im Output)
2. PRs mit mehrdeutigen Titeln
3. Dependabot-PRs (ggf. zusätzliche Bereichs-Labels)

## Verifikation

Nach Ausführung prüfen:

```bash
# Alle PRs mit Labels anzeigen
gh pr list --repo jannekbuengener/Claire_de_Binare_Cleanroom --state all --limit 50

# Spezifische Label-Gruppe anzeigen
gh pr list --label "testing" --state all
gh pr list --label "risk-engine" --state all
```

## Beispiele

### Beispiel 1: Feature PR
```
Titel: feat: add daily drawdown test
Labels: feat, testing, risk-engine
```

### Beispiel 2: Bugfix PR
```
Titel: fix: resolve Python import conflicts in services
Labels: fix, infrastructure
```

### Beispiel 3: Dokumentation PR
```
Titel: docs: add comprehensive Paper Trading test requirements
Labels: docs, testing
```

### Beispiel 4: CI/CD PR
```
Titel: ci: extend pipeline with comprehensive checks
Labels: ci, infrastructure
```

## Troubleshooting

### Problem: "Permission denied"

**Lösung**: Skript ausführbar machen:
```bash
chmod +x label_all_prs.sh
```

### Problem: "Not authenticated"

**Lösung**: GitHub CLI authentifizieren:
```bash
gh auth login
```

### Problem: "No labels found"

**Ursache**: Repository hat noch keine Labels

**Lösung**: Das Skript erstellt automatisch Standard-Labels beim ersten Durchlauf.

### Problem: Skript findet keine passenden Labels

**Lösung**:
1. Prüfe ob PR-Titel Conventional Commit Format verwendet
2. Ergänze Keywords in PR-Beschreibung
3. Manuelle Label-Zuweisung:
   ```bash
   gh pr edit <PR_NUMBER> --add-label "label-name"
   ```

## Best Practices

1. **Conventional Commits verwenden**:
   ```
   feat: add new feature
   fix: resolve bug in service
   docs: update README
   test: add risk engine tests
   ```

2. **Keywords in Titel einbauen**:
   ```
   feat(risk-engine): add circuit breaker
   fix(signal): resolve timing issue
   test(execution): add integration tests
   ```

3. **PR-Beschreibungen aussagekräftig gestalten**:
   - Erwähne betroffene Services
   - Beschreibe was getestet wurde
   - Verlinke verwandte Issues

## Weitere Kommandos

```bash
# Labels eines PR anzeigen
gh pr view <PR_NUMBER> --json labels

# Label zu PR hinzufügen
gh pr edit <PR_NUMBER> --add-label "label-name"

# Label von PR entfernen
gh pr edit <PR_NUMBER> --remove-label "label-name"

# Alle verfügbaren Labels anzeigen
gh label list
```

## Kontakt

Bei Fragen oder Problemen: Jannek Büngener
