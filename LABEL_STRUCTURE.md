# Label-Struktur für Claire de Binare Pull Requests

## Hierarchie

```
Pull Request Labels (20)
│
├── Typ-Labels (7) ────────── Was wurde gemacht?
│   ├── feat              → Neue Funktionalität
│   ├── fix               → Fehlerbehebung
│   ├── docs              → Dokumentation
│   ├── test              → Tests
│   ├── refactor          → Code-Verbesserung
│   ├── chore             → Wartung/Tooling
│   └── ci                → CI/CD Änderungen
│
├── Bereichs-Labels (7) ────── Wo wurde gearbeitet?
│   ├── risk-engine       → Risk Manager Service
│   ├── signal-engine     → Signal Engine Service
│   ├── execution         → Execution Service
│   ├── testing           → Test-Infrastruktur
│   ├── infrastructure    → Docker/Deployment
│   ├── security          → Sicherheit
│   └── performance       → Performance-Optimierung
│
└── Spezial-Labels (6) ────── Besondere Merkmale?
    ├── dependencies      → Dependency-Updates
    ├── breaking-change   → Breaking Changes
    ├── needs-review      → Wartet auf Review
    ├── work-in-progress  → Noch nicht bereit
    ├── good-first-issue  → Gut für Einsteiger
    └── help-wanted       → Hilfe benötigt
```

## Kombinationen

Ein PR kann mehrere Labels aus verschiedenen Kategorien haben:

### Beispiel 1: Feature mit Risk Engine
```
Titel: feat(risk-engine): add circuit breaker logic
Labels: feat, risk-engine, security
Kombination: Typ + Bereich + Spezial
```

### Beispiel 2: Bugfix mit Testing
```
Titel: fix(tests): resolve pytest fixture issue
Labels: fix, testing
Kombination: Typ + Bereich
```

### Beispiel 3: Dependabot Update
```
Titel: chore(deps): bump pytest from 7.0 to 8.0
Labels: chore, dependencies, testing
Kombination: Typ + Spezial + Bereich
```

### Beispiel 4: Breaking Change mit Refactoring
```
Titel: refactor!: restructure risk engine API
Labels: refactor, risk-engine, breaking-change
Kombination: Typ + Bereich + Spezial
```

## Farb-Schema

| Label | Farbe | Hex-Code | Bedeutung |
|-------|-------|----------|-----------|
| `feat` | 🟢 Grün | `#0e8a16` | Positiv/Neu |
| `fix` | 🔴 Rot | `#d73a4a` | Fehler |
| `docs` | 🔵 Blau | `#0075ca` | Information |
| `test` | 🟡 Gelb | `#ffd700` | Warnung/Wichtig |
| `refactor` | 🟡 Gelb-Hell | `#fbca04` | Neutral |
| `chore` | ⚪ Beige | `#fef2c0` | Wartung |
| `ci` | 🔵 Hellblau | `#1e90ff` | Automation |
| `risk-engine` | 🔴 Rot-Orange | `#ff6347` | Kritisch |
| `signal-engine` | 🔵 Königsblau | `#4169e1` | Service |
| `execution` | 🟢 Grün-Hell | `#32cd32` | Service |
| `testing` | 🟠 Orange | `#ffa500` | Testing |
| `infrastructure` | 🟤 Braun | `#8b4513` | Basis |
| `security` | 🔴 Feuerrot | `#b22222` | Kritisch |
| `performance` | 🟣 Lila | `#9370db` | Optimierung |
| `dependencies` | 🔵 Blau-Mittel | `#0366d6` | Extern |
| `breaking-change` | 🔴 Rot-Hell | `#ff0000` | Achtung! |

## Trigger-Keywords

### Typ-Labels

| Label | Trigger (Titel) | Trigger (Body) |
|-------|----------------|----------------|
| `feat` | `feat:`, `feature:` | feature, new, add |
| `fix` | `fix:`, `bugfix:` | fix, bug, resolve |
| `docs` | `docs:`, `documentation:` | documentation, readme |
| `test` | `test:`, `tests:` | test, pytest, coverage |
| `refactor` | `refactor:` | refactor, clean, improve |
| `chore` | `chore:` | chore, maintenance |
| `ci` | `ci:`, `ci/cd:` | ci, pipeline, workflow |

### Bereichs-Labels

| Label | Keywords |
|-------|----------|
| `risk-engine` | risk, risk-engine, risk_engine, risk manager |
| `signal-engine` | signal, signal-engine, signal_engine, signal engine |
| `execution` | execution, exec, order execution |
| `testing` | test, testing, pytest, coverage, test infrastructure |
| `infrastructure` | infrastructure, docker, compose, deployment |
| `security` | security, secrets, audit, auth, authentication |
| `performance` | performance, optimization, speed, latency |

### Spezial-Labels

| Label | Keywords |
|-------|----------|
| `dependencies` | bump, dependabot, dependencies, dependency |
| `breaking-change` | breaking, breaking change, BREAKING, `!` |

## Label-Regeln

### Regel 1: Typ-Label ist Pflicht
Jeder PR sollte mindestens ein Typ-Label haben (feat, fix, docs, etc.)

### Regel 2: Bereich optional aber empfohlen
Wenn ein PR einen spezifischen Service betrifft, sollte das Bereichs-Label gesetzt werden.

### Regel 3: Max. 5 Labels pro PR
Zu viele Labels sind verwirrend. Maximal 5 Labels pro PR.

### Regel 4: Breaking Changes markieren
Jeder Breaking Change MUSS das Label `breaking-change` haben.

### Regel 5: WIP kennzeichnen
Work-in-Progress PRs MÜSSEN das Label `work-in-progress` haben.

## Automatische Erkennung

### Hohe Priorität (immer erkannt)

1. **Conventional Commit Präfixe** im Titel:
   - `feat:`, `fix:`, `docs:`, etc.

2. **Service-Namen** im Titel oder Body:
   - `risk-engine`, `signal-engine`, `execution`

3. **Dependabot** im Autor oder Titel:
   - Automatisch `dependencies` + `chore`

### Mittlere Priorität (meist erkannt)

1. **Keywords** im Titel:
   - `test`, `security`, `performance`

2. **Keywords** im Body (erste 3 Absätze):
   - Service-Namen, Typen

### Niedrige Priorität (fallback)

1. **Commit-Messages** (bei unklarem Titel)
2. **Datei-Änderungen** (bei unklarem Kontext)

## Best Practices

### ✅ Gute PR-Titel

```
✅ feat(risk-engine): add circuit breaker logic
✅ fix(signal): resolve timing issue in market data
✅ docs: add Paper Trading guide
✅ test(execution): add E2E tests with Docker
✅ chore(deps): bump pytest from 7.0 to 8.0
```

Labels werden automatisch erkannt!

### ❌ Schlechte PR-Titel

```
❌ Update code
❌ Fix bug
❌ Changes
❌ WIP
❌ Refactoring
```

Labels können NICHT automatisch erkannt werden!

### 🔧 Verbesserungs-Tipps

**Vorher**:
```
Update tests
```

**Nachher**:
```
test(risk-engine): add comprehensive unit tests for circuit breaker
```

**Ergebnis**: Labels `test`, `testing`, `risk-engine` automatisch gesetzt!

## Wartung

### Label hinzufügen

```bash
gh label create "new-label" \
  --description "Description" \
  --color "ff6347"
```

### Label bearbeiten

```bash
gh label edit "existing-label" \
  --description "New description" \
  --color "32cd32"
```

### Label löschen

```bash
gh label delete "obsolete-label"
```

### Alle Labels exportieren

```bash
gh label list --json name,description,color > labels_backup.json
```

## Reporting

### PRs nach Label gruppieren

```bash
# Alle Risk-Engine PRs
gh pr list --label "risk-engine" --state all

# Alle Feature-PRs
gh pr list --label "feat" --state all

# Kombinationen
gh pr list --label "feat" --label "risk-engine" --state all
```

### Statistiken generieren

```bash
# Anzahl PRs pro Label
for label in feat fix docs test refactor chore ci; do
  count=$(gh pr list --label "$label" --state all --json number | jq length)
  echo "$label: $count PRs"
done
```

## Timeline

### Initial Setup (2025-11-22)

- ✅ 20 Standard-Labels definiert
- ✅ Automatisches Labeling-System implementiert
- ✅ Bash + Python Skripte erstellt
- ✅ Umfassende Dokumentation

### Zukünftige Erweiterungen

- [ ] GitHub Actions Integration
- [ ] Automatisches Review-Assignment basierend auf Labels
- [ ] Milestone-Zuweisung basierend auf Labels
- [ ] Slack-Benachrichtigung bei bestimmten Labels
- [ ] Automatische PR-Priorisierung

---

**Version**: 1.0.0
**Erstellt**: 2025-11-22
**Repository**: jannekbuengener/Claire_de_Binare_Cleanroom
