# CI/CD Troubleshooting Guide – Claire de Binaire

Systematischer Leitfaden zum Beheben von fehlgeschlagenen GitHub Actions Checks.

---

## 📋 Inhaltsverzeichnis

1. [Allgemeiner Workflow](#allgemeiner-workflow)
2. [ci/test - Pytest & Coverage](#1-citest---pytest--coverage)
3. [ci/lint - Code Quality](#2-cilint---code-quality)
4. [ci/docker-build - Container Build](#3-cidocker-build---container-build)
5. [ci/secrets - Secret Scanning](#4-cisecrets---secret-scanning)
6. [ci/security - Dependency Security](#5-cisecurity---dependency-security)
7. [Quick Fix Checkliste](#quick-fix-checkliste)
8. [Häufige Fehlerquellen](#häufige-fehlerquellen)

---

## Allgemeiner Workflow

### 0. Reihenfolge beim Troubleshooting

```bash
# 1. GitHub Actions Logs öffnen
# In GitHub bei jedem roten Job auf „Details" klicken
# → Genaue Fehlermeldung notieren (Screenshot/Copy)

# 2. Lokal reproduzieren
# Dieselben Commands ausführen wie im Workflow

# 3. Fixen & Testen
# Problem beheben, lokal verifizieren

# 4. Commit & Push
# Änderungen committen, neuen Push → Checks neu laufen lassen

# 5. Verify
# Alle Checks grün? → Merge
```

### Tools & Shortcuts

```bash
# Makefile nutzen (empfohlen)
make help              # Alle verfügbaren Commands
make test-fast         # Schnelle lokale Tests
make coverage          # Coverage wie in CI
make lint              # Linting wie in CI
make clean             # Cleanup vor Troubleshooting

# Oder direkt pytest
pytest --maxfail=1 -q  # Stoppt bei erstem Fehler
pytest -vv --tb=short  # Verbose mit kurzen Tracebacks
```

---

## 1. ci/test - Pytest & Coverage

### Ziel
✅ Alle Tests grün
✅ Coverage-Threshold erfüllt (95%+)

### Workflow-Kommandos
```yaml
# Aus .github/workflows/pytest.yml
python -m pytest --cov=services --cov-report=xml --cov-report=term -v
python -m pytest --cov=services --cov-fail-under=95 --cov-report=term -q
```

### Lokal reproduzieren

```bash
# Schritt 1: Schneller Check
make test-fast

# Schritt 2: Mit Coverage
make coverage

# Schritt 3: Coverage Threshold
pytest --cov=services --cov-fail-under=95 -q

# Schritt 4: Nur fehlgeschlagene Tests
pytest --lf -vv
```

### Typische Fehlerquellen

#### A. Tests schlagen fehl

**Symptom**: `FAILED tests/test_xyz.py::test_abc`

**Diagnose**:
```bash
# Einzelnen Test debuggen
pytest -vv -s tests/test_xyz.py::test_abc

# Mit pdb bei Fehler
pytest --pdb tests/test_xyz.py::test_abc
```

**Häufige Ursachen**:
1. **API-Änderungen** - Funktions-Signaturen geändert
   ```python
   # Fix: Parameter in Tests anpassen
   # Alt: risk_engine.evaluate_signal(signal, state)
   # Neu: risk_engine.evaluate_signal(signal, state, config)
   ```

2. **Geänderte Grenzwerte**
   ```python
   # Fix: Test-Erwartungen aktualisieren
   # Alt: assert decision.approved is True  # Bei 20% Exposure
   # Neu: assert decision.approved is False  # Limit auf 19% gesenkt
   ```

3. **Hypothesis-Flakiness** - Nicht-deterministisch
   ```bash
   # Reproduzierbar machen
   pytest tests/test_risk_engine_hypothesis.py --hypothesis-seed=12345

   # Weniger Beispiele für CI
   pytest --hypothesis-max-examples=50
   ```

#### B. Coverage zu niedrig

**Symptom**: `FAILED: coverage: 93% < 95%`

**Diagnose**:
```bash
# Fehlende Lines anzeigen
pytest --cov=services --cov-report=term-missing

# HTML-Report für Details
make coverage-html
open htmlcov/index.html
```

**Lösungen**:
1. **Tests ergänzen** für fehlende Pfade
2. **Tote Code-Pfade** entfernen (wenn sicher)
3. **Coverage-Threshold anpassen** (nur als letzter Ausweg)

#### C. Import-Errors

**Symptom**: `ModuleNotFoundError: No module named 'services'`

**Fix**:
```bash
# PYTHONPATH setzen
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Oder in pytest.ini:
# [pytest]
# pythonpath = .
```

---

## 2. ci/lint - Code Quality

### Ziel
✅ Code-Style konsistent
✅ Type-Hints korrekt
✅ Keine Linting-Errors

### Workflow-Tools
Typischerweise: `ruff`, `black`, `mypy`, `flake8`

### Lokal reproduzieren

```bash
# Schritt 1: Makefile nutzen
make lint              # Wenn implementiert

# Schritt 2: Einzeln prüfen
ruff check .           # Fast linter
black . --check        # Formatierung
mypy services/         # Type checking
flake8 services/       # Classic linter

# Schritt 3: Auto-Fix
black .                # Automatisch formatieren
ruff check . --fix     # Auto-fixbare Probleme
```

### Typische Fehlerquellen

#### A. Formatierungsfehler

**Symptom**: `black` meldet nicht-formatierte Dateien

**Fix**:
```bash
# Automatisch formatieren
black .

# Nur bestimmte Dateien
black services/risk_engine.py
```

#### B. Unused Imports

**Symptom**: `F401: 'module' imported but unused`

**Fix**:
```bash
# Automatisch entfernen (ruff)
ruff check . --fix

# Oder manuell
# services/risk_engine.py:5 - import os (unused) → löschen
```

#### C. Type-Errors

**Symptom**: `mypy` meldet Type-Inkonsistenzen

**Fix**:
```python
# Beispiel: Fehlende Type-Hints
# Alt:
def process(data):
    return data * 2

# Neu:
def process(data: float) -> float:
    return data * 2
```

#### D. Line Length

**Symptom**: `E501: line too long (95 > 88 characters)`

**Fix**:
```python
# Alt:
decision = risk_engine.evaluate_signal(signal_event, risk_state, risk_config, additional_param)

# Neu (Multi-Line):
decision = risk_engine.evaluate_signal(
    signal_event,
    risk_state,
    risk_config,
    additional_param
)
```

---

## 3. ci/docker-build - Container Build

### Ziel
✅ Alle Docker Images bauen erfolgreich
✅ docker-compose.yml valide

### Lokal reproduzieren

```bash
# Schritt 1: Compose Validation
docker compose config --quiet

# Schritt 2: Unsere Compose-Tests (NEU!)
pytest tests/test_docker_compose_validation.py -v

# Schritt 3: Einzelne Services bauen
docker compose build cdb_redis
docker compose build cdb_postgres

# Schritt 4: Alle Services bauen
docker compose build

# Schritt 5: Health-Check
make docker-up
make docker-health
```

### Typische Fehlerquellen

#### A. Basisimage nicht verfügbar

**Symptom**: `ERROR: pull access denied for python:3.14-slim`

**Fix**:
```dockerfile
# Alt (Dockerfile):
FROM python:3.14-slim

# Neu (existierendes Tag):
FROM python:3.11-slim
```

**Verfügbare Tags prüfen**:
```bash
# Docker Hub API
curl https://registry.hub.docker.com/v2/repositories/library/python/tags\?page_size\=100 | grep name
```

#### B. COPY-Pfade falsch

**Symptom**: `COPY failed: file not found in build context`

**Fix**:
```dockerfile
# Alt:
COPY services/cdb_risk/requirements.txt /app/

# Neu (wenn Projektstruktur geändert):
COPY requirements.txt /app/
```

#### C. Fehlende Dependencies

**Symptom**: Build läuft durch, aber Container startet nicht

**Diagnose**:
```bash
# Container Logs anschauen
docker compose logs cdb_risk

# Interaktiv troubleshooten
docker compose run --rm cdb_risk bash
pip list
```

**Fix**: Dependencies in `requirements.txt` ergänzen

---

## 4. ci/secrets - Secret Scanning

### Ziel
✅ Keine Secrets im Repository
✅ Alle Secrets in `.env` oder Vault

### Tools
Meist: `gitleaks`, `trufflehog`, `detect-secrets`

### Lokal reproduzieren

```bash
# Wenn gitleaks installiert:
gitleaks detect --source . --verbose

# Oder GitHub Action lokal mit act:
act -j secrets
```

### Typische Fehlerquellen

#### A. Echte Secrets committed

**Symptom**: `gitleaks` findet `POSTGRES_PASSWORD=MySecretPass123`

**KRITISCH - Sofortmaßnahmen**:
```bash
# 1. Secret rotieren (neue generieren)
# → In PostgreSQL/Service neues Passwort setzen

# 2. Aus Repo entfernen
# Git History bereinigen (VORSICHT!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# 3. In .gitignore sicherstellen
echo ".env" >> .gitignore
echo "*.secret" >> .gitignore
```

**Besser: Platzhalter nutzen**:
```bash
# In .env.example (für Doku):
POSTGRES_PASSWORD=your_secure_password_here

# Echte .env nie committen!
```

#### B. Test-Daten / Dummy-Secrets

**Symptom**: `gitleaks` findet `API_KEY=test_12345_not_real`

**Fix**: Format entschärfen
```python
# Alt (wird als Secret erkannt):
API_KEY = "sk_test_4eC39HqLyjWDarjtT1zdp7dc"

# Neu (kein Secret-Pattern):
API_KEY = "EXAMPLE_KEY_NOT_REAL_FOR_TESTING"
```

#### C. False Positives

**Symptom**: Legitime Strings als Secrets erkannt

**Fix**: Whitelist in `.gitleaks.toml`
```toml
[[rules]]
id = "postgres-password-example"
description = "Example password in documentation"
regex = '''password.*example'''
path = '''docs/.*\.md'''

[allowlist]
paths = [
  '''^\.env\.example$''',
  '''^docs/examples/'''
]
```

---

## 5. ci/security - Dependency Security

### Ziel
✅ Keine bekannten Vulnerabilities
✅ Dependencies aktuell

### Tools
`pip-audit`, `safety`, `bandit`, Snyk, Trivy

### Lokal reproduzieren

```bash
# Schritt 1: Python Dependencies scannen
pip-audit

# Schritt 2: Safety Check
safety check

# Schritt 3: Code-Scan mit bandit
bandit -r services/

# Schritt 4: Docker-Image scannen
trivy image python:3.11-slim
```

### Typische Fehlerquellen

#### A. Vulnerable Dependencies

**Symptom**: `pip-audit` meldet CVE in Package

**Beispiel**:
```
cryptography 40.0.0 has vulnerability CVE-2023-xxxxx
```

**Fix**:
```bash
# 1. Version prüfen
pip show cryptography

# 2. Auf sichere Version upgraden
pip install --upgrade cryptography>=41.0.0

# 3. requirements.txt aktualisieren
pip freeze | grep cryptography >> requirements.txt

# 4. Testen
make test
```

#### B. Indirect Dependencies

**Symptom**: Vulnerability in Dependency einer Dependency

**Diagnose**:
```bash
# Dependency-Tree anzeigen
pip install pipdeptree
pipdeptree -p vulnerable-package
```

**Fix**:
```bash
# Option 1: Hauptpackage upgraden (zieht neuere Deps nach)
pip install --upgrade parent-package

# Option 2: Explizit pinnen
echo "sub-dependency>=safe-version" >> requirements.txt
```

#### C. Docker Base Image Vulns

**Symptom**: Trivy findet CVEs im Basisimage

**Fix**:
```dockerfile
# Alt:
FROM python:3.11-slim

# Neu (neuestes Patch-Release):
FROM python:3.11.7-slim

# Oder: Distroless für minimale Attack-Surface
FROM gcr.io/distroless/python3-debian11
```

#### D. Bandit False Positives

**Symptom**: Bandit meldet `B601: paramiko_calls` aber ist Test-Code

**Fix**: `# nosec` Kommentar (sparsam nutzen!)
```python
# In Tests OK:
ssh_client = paramiko.SSHClient()  # nosec B601 - Test-Code only
```

**Oder**: `.bandit` Config
```yaml
# .bandit
skips: ['B601']  # Skip paramiko checks
```

---

## Quick Fix Checkliste

### Vor jedem Push

```bash
☐ make clean                    # Alte Artifacts weg
☐ make test-fast                # Unit-Tests grün
☐ make coverage                 # Coverage ≥ 95%
☐ make lint                     # Linting clean
☐ git status                    # Keine .env/.secret Dateien staged
☐ Pre-Commit Hook läuft durch   # Automatisch bei git commit
```

### Bei roten Checks

```bash
☐ GitHub Actions Log kopieren
☐ Lokal reproduzieren
☐ Fix implementieren
☐ Lokal testen
☐ Commit + Push
☐ Checks beobachten
```

### Vor Merge

```bash
☐ Alle CI Checks grün
☐ Code Review approved
☐ Branch up-to-date mit main
☐ Keine Merge-Konflikte
☐ PR-Beschreibung vollständig
```

---

## Häufige Fehlerquellen

### 1. **Hypothesis-Flakiness**

**Problem**: Tests manchmal grün, manchmal rot

**Lösung**:
```python
# In Test-Datei:
from hypothesis import settings

@settings(max_examples=100, deadline=None)
@given(...)
def test_with_hypothesis(...):
    ...
```

**Oder in `pytest.ini`**:
```ini
[pytest]
hypothesis_profile = ci

[hypothesis:ci]
max_examples = 50
deadline = None
```

### 2. **Timing-Issues in Tests**

**Problem**: Integration-Tests manchmal timeout

**Lösung**:
```python
import time

# Statt:
assert redis.ping()

# Besser (mit Retry):
for _ in range(5):
    try:
        assert redis.ping()
        break
    except:
        time.sleep(0.1)
else:
    pytest.fail("Redis not available")
```

### 3. **ENV-Variablen fehlen**

**Problem**: Tests lokal grün, in CI rot

**Diagnose**: CI hat keine .env-Datei!

**Fix**: `.github/workflows/pytest.yml`
```yaml
- name: Create test .env
  run: |
    cat > .env <<EOF
    POSTGRES_PASSWORD=test_password
    REDIS_PASSWORD=test_password
    EOF
```

### 4. **Python-Version-Unterschiede**

**Problem**: Lokal Python 3.11, CI nutzt 3.12

**Fix**: Matrix-Testing oder Version pinnen
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```

---

## Abschluss-Kommentar für PR

Template für GitHub PR-Kommentar nach Fixes:

```markdown
## ✅ CI/CD Checks behoben

Alle roten Checks analysiert und adressiert:

- **ci/test**: Tests lokal grün (73/73 passed), Coverage 100%
- **ci/lint**: Linting/Formatierung angepasst (black + ruff)
- **ci/docker-build**: Docker-Build lokal erfolgreich
- **ci/secrets**: Secret-Scan bereinigt (keine Findings)
- **ci/security**: Dependencies aktualisiert (pip-audit clean)

Lokale Verifikation:
```bash
make test           # ✅ All tests passed
make lint           # ✅ No issues
make docker-build   # ✅ Build successful
```

Warte auf erneuten Lauf der GitHub-Checks.
Merge erst nach grünen Pipelines.
```

---

## Hilfreiche Ressourcen

- [Testing Guide](./testing/TESTING_GUIDE.md) - Detaillierte Test-Dokumentation
- [Makefile](../Makefile) - Alle verfügbaren Commands
- [GitHub Actions Workflows](../.github/workflows/) - Workflow-Definitionen
- [Pre-Commit Hook](../scripts/hooks/pre-commit) - Lokale Validierung

---

**Version**: 1.0
**Letzte Aktualisierung**: 2025-11-19
**Maintainer**: Claire de Binaire Team

---

**Bei Fragen oder unklaren Fehlermeldungen:**
1. Log-Auszug in PR-Kommentar posten
2. Lokale Reproduktion dokumentieren
3. Team-Review anfragen
