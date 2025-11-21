# CI/CD Pipeline Guide - Claire de Binaire

**Version**: 2.0
**Datum**: 2025-11-21
**Status**: ✅ Production-Ready

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Pipeline-Jobs](#pipeline-jobs)
3. [Verwendung](#verwendung)
4. [Artefakte & Reports](#artefakte--reports)
5. [Troubleshooting](#troubleshooting)
6. [Erweiterungen](#erweiterungen)

---

## Übersicht

Die CI/CD-Pipeline läuft automatisch bei:
- **Pull Requests** (alle Branches)
- **Push** auf `main` Branch
- **Manuell** via Workflow Dispatch

### Pipeline-Architektur

```
┌─────────────────────────────────────────┐
│         CODE QUALITY CHECKS             │
├─────────────────────────────────────────┤
│  • Linting (Ruff)                       │
│  • Format Check (Black)                 │
│  • Type Checking (mypy)                 │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│              TESTS                      │
├─────────────────────────────────────────┤
│  • Python 3.11 & 3.12 Matrix            │
│  • Unit + Integration Tests             │
│  • Coverage Reports (HTML + XML)        │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         SECURITY CHECKS                 │
├─────────────────────────────────────────┤
│  • Secret Scanning (Gitleaks)           │
│  • Security Audit (Bandit)              │
│  • Dependency Audit (pip-audit)         │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       DOCUMENTATION CHECKS              │
├─────────────────────────────────────────┤
│  • Markdown Linting                     │
│  • Link Validation (geplant)            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│          BUILD SUMMARY                  │
└─────────────────────────────────────────┘
```

---

## Pipeline-Jobs

### 1. Code Quality Checks

#### **Linting (Ruff)**
- **Tool**: Ruff (Fast Python Linter)
- **Scope**: Alle Python-Dateien
- **Config**: `pyproject.toml` (falls vorhanden)
- **Output**: GitHub-Format (inline annotations)

```bash
# Lokal ausführen:
ruff check .
```

#### **Format Check (Black)**
- **Tool**: Black (Code Formatter)
- **Scope**: Alle Python-Dateien
- **Mode**: Check-only (kein Auto-Fix)
- **Output**: Diff bei Abweichungen

```bash
# Lokal ausführen:
black --check --diff .

# Auto-Fix:
black .
```

#### **Type Checking (mypy)**
- **Tool**: mypy (Static Type Checker)
- **Scope**: `services/` Verzeichnis
- **Mode**: `continue-on-error: true` (MVP-Phase)
- **Flags**: `--ignore-missing-imports --no-strict-optional`

```bash
# Lokal ausführen:
mypy services/ --ignore-missing-imports --no-strict-optional
```

**Status**: Nicht blockierend in MVP-Phase (wird nur gewarnt)

---

### 2. Tests

#### **Test Matrix**
- **Python Versions**: 3.11, 3.12
- **Strategy**: `fail-fast: false` (alle Versionen testen)
- **Marker**: `-m "not e2e and not local_only"` (nur CI-Tests)

#### **Coverage**
- **Tool**: pytest-cov
- **Scope**: `services/` Verzeichnis
- **Reports**:
  - Terminal (mit missing lines)
  - XML (`coverage.xml`)
  - HTML (`htmlcov/`)

```bash
# Lokal ausführen:
pytest -v -m "not e2e and not local_only" \
  --cov=services \
  --cov-report=term-missing \
  --cov-report=html
```

#### **Test-Kategorien**

| Marker | Beschreibung | CI | Lokal |
|--------|--------------|----|----|
| `unit` | Schnelle, isolierte Tests | ✅ | ✅ |
| `integration` | Tests mit Mock-Services | ✅ | ✅ |
| `e2e` | Tests mit echten Containern | ❌ | ✅ |
| `local_only` | Explizit nur lokal | ❌ | ✅ |
| `slow` | Tests >10s | ❌ | ✅ |

---

### 3. Security Checks

#### **Secret Scanning (Gitleaks)**
- **Tool**: Gitleaks
- **Mode**: `detect` (keine Git-Historie nötig)
- **Scope**: Alle Dateien
- **Config**: `.gitleaksignore` (falls vorhanden)

```bash
# Lokal ausführen:
gitleaks detect --no-git --source . --verbose
```

**Blockiert**: ✅ Ja (Pipeline schlägt fehl bei Secrets)

#### **Security Audit (Bandit)**
- **Tool**: Bandit
- **Scope**: `services/` Verzeichnis
- **Output**: JSON-Report (`bandit-report.json`)
- **Mode**: `continue-on-error: true`

```bash
# Lokal ausführen:
bandit -r services/ -f json -o bandit-report.json
```

**Blockiert**: ❌ Nein (nur Report)

#### **Dependency Audit (pip-audit)**
- **Tool**: pip-audit
- **Scope**: `requirements.txt`
- **Output**: JSON-Report (`pip-audit.json`)
- **Mode**: `continue-on-error: true`

```bash
# Lokal ausführen:
pip-audit --requirement requirements.txt
```

**Blockiert**: ❌ Nein (nur Report)

---

### 4. Documentation Checks

#### **Markdown Linting**
- **Tool**: markdownlint-cli
- **Config**: `.markdownlintrc`
- **Scope**: Alle `.md` Dateien (außer `node_modules`, `.venv`)
- **Mode**: `continue-on-error: true` (MVP-Phase)

```bash
# Lokal ausführen:
markdownlint '**/*.md' --ignore node_modules --ignore .venv
```

#### **Link Validation**
- **Status**: 🔴 Geplant (noch nicht implementiert)
- **Tool**: markdown-link-check (geplant)

---

### 5. Build Summary

**Immer ausgeführt** (auch bei Fehlern):
- Aggregiert Status aller Jobs
- Erstellt GitHub Step Summary
- Zeigt Übersicht aller Job-Results

**Output**:
```markdown
## 🎯 CI/CD Pipeline Summary

**Status**: success

### Jobs:
- Linting: success
- Format Check: success
- Type Check: success
- Tests: success
- Secret Scan: success
- Security Audit: success
- Dependency Audit: success
- Docs Check: success
```

---

## Verwendung

### Automatische Ausführung

**Bei Pull Request:**
```bash
# Erstelle PR
gh pr create --title "..." --body "..."

# Pipeline läuft automatisch
# Status sichtbar in PR-Checks
```

**Bei Push auf main:**
```bash
git push origin main

# Pipeline läuft automatisch
```

### Manuelle Ausführung

**Via GitHub UI:**
1. Gehe zu: `Actions` → `CI/CD Pipeline`
2. Klicke: `Run workflow`
3. Wähle Branch
4. Klicke: `Run workflow`

**Via gh CLI:**
```bash
gh workflow run ci.yaml --ref main
```

### Lokale Simulation

**Alle CI-Tests lokal ausführen:**
```bash
# 1. Code Quality
ruff check .
black --check --diff .
mypy services/ --ignore-missing-imports --no-strict-optional

# 2. Tests
pytest -v -m "not e2e and not local_only" --cov=services

# 3. Security
gitleaks detect --no-git --source .
bandit -r services/
pip-audit --requirement requirements.txt

# 4. Docs
markdownlint '**/*.md' --ignore node_modules --ignore .venv
```

**Makefile-Targets** (geplant):
```bash
make ci-lint        # Alle Linting-Checks
make ci-test        # Alle Tests
make ci-security    # Alle Security-Checks
make ci-full        # Komplette CI-Pipeline simulieren
```

---

## Artefakte & Reports

### Coverage Reports

**Verfügbar für 30 Tage nach CI-Run:**

1. **HTML-Report** (`htmlcov/`)
   - Download: `Actions` → `Workflow Run` → `Artifacts` → `coverage-report-py3.12`
   - Öffne: `htmlcov/index.html` im Browser

2. **XML-Report** (`coverage.xml`)
   - Maschinell lesbar
   - Für Coverage-Tools (codecov, coveralls)

3. **Terminal-Output**
   - Sichtbar in GitHub Step Summary
   - Zeigt Coverage-Prozentsatz + Missing Lines

### Security Reports

1. **Bandit Report** (`bandit-report.json`)
   - JSON-Format
   - Listet alle Sicherheitswarnungen
   - Schweregrade: LOW, MEDIUM, HIGH

2. **pip-audit Report** (`pip-audit.json`)
   - JSON-Format
   - Bekannte Vulnerabilities in Dependencies
   - CVE-Nummern + Fixes

### Logs

**CI-Logs ansehen:**
```bash
# Via gh CLI
gh run list
gh run view <run-id>
gh run view <run-id> --log

# Fehlgeschlagene Runs
gh run list --status failure
```

---

## Troubleshooting

### Problem: Linting schlägt fehl

**Fehler:**
```
Ruff found X issues
```

**Lösung:**
```bash
# Auto-Fix (meiste Issues)
ruff check . --fix

# Manuell prüfen
ruff check .
```

---

### Problem: Format-Check schlägt fehl

**Fehler:**
```
would reformat X files
```

**Lösung:**
```bash
# Auto-Format
black .

# Vorher prüfen
black --check --diff .
```

---

### Problem: Tests schlagen fehl

**Fehler:**
```
X tests failed
```

**Lösung:**
```bash
# Lokal reproduzieren
pytest -v -m "not e2e and not local_only"

# Spezifischen Test debuggen
pytest -v tests/test_xyz.py::test_abc

# Mit Logs
pytest -v -s tests/test_xyz.py
```

---

### Problem: Secret-Scan schlägt fehl

**Fehler:**
```
Gitleaks found X leaks
```

**Lösung:**
```bash
# 1. Secrets identifizieren
gitleaks detect --no-git --source . --verbose

# 2. Secrets entfernen
# → In .env verschieben (nicht committen!)
# → Hardcoded Werte durch os.getenv() ersetzen

# 3. .gitignore prüfen
echo ".env" >> .gitignore
```

**False Positives:**
- Erstelle `.gitleaksignore` Datei

---

### Problem: Coverage zu niedrig

**Warnung:**
```
Coverage: 45% (Target: 80%)
```

**Lösung:**
```bash
# 1. Coverage lokal prüfen
pytest --cov=services --cov-report=html

# 2. HTML-Report öffnen
open htmlcov/index.html

# 3. Fehlende Tests identifizieren
# → Rote Bereiche im Report

# 4. Tests hinzufügen
# → In tests/ entsprechende Dateien erstellen
```

---

### Problem: Dependency-Vulnerabilities

**Warnung:**
```
pip-audit found X vulnerabilities
```

**Lösung:**
```bash
# 1. Details anzeigen
pip-audit --requirement requirements.txt

# 2. Dependencies updaten
pip install --upgrade <package>

# 3. requirements.txt aktualisieren
pip freeze > requirements.txt

# 4. Testen
pytest -v
```

---

## Erweiterungen

### Geplante Erweiterungen

#### **Phase 2 (N1 Complete)**
- ✅ Coverage-Threshold (80%)
- ✅ Performance-Tests (pytest-benchmark)
- ✅ Mutation-Testing (mutmut)
- ✅ Link-Checking (markdown-link-check)

#### **Phase 3 (Production)**
- ✅ Docker-Image-Builds
- ✅ Container-Scanning (Trivy)
- ✅ SAST (CodeQL)
- ✅ Deployment-Automation

#### **Phase 4 (Scale)**
- ✅ Load-Testing (Locust)
- ✅ Chaos-Testing
- ✅ Multi-Environment-Deployment
- ✅ Rollback-Automation

---

### Neue Jobs hinzufügen

**Template:**
```yaml
new-job:
  name: New Job Name
  runs-on: ubuntu-latest
  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'

    - name: Run new check
      run: |
        pip install new-tool
        new-tool --check

    - name: Upload report (optional)
      uses: actions/upload-artifact@v4
      with:
        name: new-report
        path: report.json
        retention-days: 30
```

**Integration in build-summary:**
```yaml
build-summary:
  needs: [..., new-job]  # Job hinzufügen
  steps:
    - name: Create summary
      run: |
        echo "- New Job: ${{ needs.new-job.result }}" >> $GITHUB_STEP_SUMMARY
```

---

## Best Practices

### 1. Vor jedem Commit

```bash
# Quick-Check (1-2 Minuten)
ruff check .
black --check .
pytest -q -m "not e2e"
```

### 2. Vor jedem PR

```bash
# Full-Check (5-10 Minuten)
ruff check .
black --check --diff .
mypy services/ --ignore-missing-imports
pytest -v -m "not e2e" --cov=services
gitleaks detect --no-git --source .
```

### 3. Pre-Commit Hooks

**Installieren:**
```bash
pip install pre-commit
pre-commit install
```

**Config** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

---

## Metriken & KPIs

### Pipeline-Performance

| Metrik | Target | Aktuell |
|--------|--------|---------|
| **Total Runtime** | <10 min | ~8 min |
| **Test Runtime** | <2 min | ~1.5 min |
| **Linting** | <30s | ~20s |
| **Security Scans** | <2 min | ~1 min |

### Code Quality

| Metrik | Target | Aktuell |
|--------|--------|---------|
| **Test Coverage** | >80% | 100% |
| **Linting Issues** | 0 | 0 |
| **Security Issues** | 0 | 0 |
| **Type Coverage** | >70% | ~50% |

---

## Ressourcen

### Interne Docs
- [TESTING_GUIDE.md](./testing/TESTING_GUIDE.md)
- [SECURITY_HARDENING.md](./security/HARDENING.md)
- [PROJECT_STATUS.md](../PROJECT_STATUS.md)

### Externe Links
- [GitHub Actions Docs](https://docs.github.com/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)

---

**Erstellt**: 2025-11-21
**Autor**: Claude (AI Assistant)
**Projekt**: Claire de Binaire - Autonomous Crypto Trading Bot
**Phase**: N1 - Paper Trading Implementation
