# TEST RUNBOOK – Re-Run Required

> Ergebnisse zählen erst nach vollständiger Durchführung und lückenloser Evidence-Ablage laut `backoffice/docs/TEST_RERUN_EVIDENCE_<RUN_DATE>.md`.

## Vorbedingungen
- `.env` vorhanden, Secrets plausibel und nicht eingecheckt.
- Python 3.11 Umgebung aktiv; `pip install -r requirements.txt`.
- Docker & Docker Compose laufen (inkl. Desktop-WSL Integration).
- `export RUN_DATE=$(date +%F)` gesetzt.
- Vorlauf bereinigt: `docker compose down -v || true`.

## Ablauf (lokal)
1. **Repo aktualisieren**
   ```bash
   git pull --rebase
   pip install -r requirements.txt
   ```
2. **.env-Validierung & Hash**
   ```bash
   REQUIRED_KEYS="MEXC_API_KEY MEXC_API_SECRET REDIS_PASSWORD POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD"
   for key in $REQUIRED_KEYS; do grep -q "^${key}=" .env || echo "MISSING ${key}"; done
   sha256sum .env | awk '{print $1}' > backoffice/artifacts/${RUN_DATE}/integration/env_sha256.txt
   ```
3. **Unit-Scope**
   ```bash
   pytest -q -m "not integration" \
     --junitxml backoffice/artifacts/${RUN_DATE}/unit/junit.xml \
     --cov=src \
     --cov-report=xml:backoffice/artifacts/${RUN_DATE}/unit/coverage.xml \
     --log-file backoffice/artifacts/${RUN_DATE}/unit/pytest_unit.log
   ```
4. **Lint & Types**
   ```bash
   black --check .
   ruff check .
   mypy --strict --ignore-missing-imports src tests
   ```
5. **Security-Scope**
   ```bash
   mkdir -p backoffice/artifacts/${RUN_DATE}/security
   gitleaks detect --redact --exit-code 1 \
     --report-format json \
     --report-path backoffice/artifacts/${RUN_DATE}/security/gitleaks.json
   trivy fs --severity HIGH,CRITICAL --exit-code 1 \
     --format json \
     --output backoffice/artifacts/${RUN_DATE}/security/trivy_fs.json .
   bandit -r . -q -o backoffice/artifacts/${RUN_DATE}/security/bandit.log -f txt || true
   sudo ss -tulpen | grep LISTEN > backoffice/artifacts/${RUN_DATE}/security/open_ports.txt || true
   ```
6. **Integration (inkl. Runtime-Security & Logs)**
   ```bash
   export COMPOSE_FILE=compose.yml
   docker compose build cdb_test
   docker compose up -d cdb_core cdb_risk cdb_execution
   docker compose ps > backoffice/artifacts/${RUN_DATE}/integration/compose_ps.log
   docker compose logs --since 5m --no-color > backoffice/artifacts/${RUN_DATE}/integration/compose_pre.log || true
   docker compose run --rm cdb_test -m integration -q \
     --junitxml backoffice/artifacts/${RUN_DATE}/integration/junit.xml
   docker compose logs --since 5m --no-color > backoffice/artifacts/${RUN_DATE}/integration/compose_post.log || true
   docker inspect cdb_core cdb_risk cdb_execution \
     > backoffice/artifacts/${RUN_DATE}/security/runtime_security_check.txt
   docker compose down
   ```
7. **Log-Analyse**
   ```bash
   grep -R --color=never -nE "ERROR|CRITICAL|Traceback" logs/ \
     > backoffice/artifacts/${RUN_DATE}/integration/log_analysis.txt || true
   ```
8. **Open-Ports (best effort, ohne sudo, Timeout ≤10 s)**
   ```bash
   mkdir -p backoffice/artifacts/${RUN_DATE}/security
   (timeout 10 ss -tulpen 2>/dev/null || timeout 10 lsof -iTCP -sTCP:LISTEN 2>/dev/null || timeout 10 netstat -tulpen 2>/dev/null || echo "Open-Ports optional; Tool nicht verfügbar oder Timeout") \
     > backoffice/artifacts/${RUN_DATE}/security/open_ports.txt
   ```

## CI-Lauf (GitHub Actions)
- Workflow `QA Hardening CI` führt identische Scopes (`secrets`, `lint_types`, `unit`, `security`, `integration`) aus.
- Artefakte werden automatisch nach `backoffice/artifacts/${RUN_DATE}/…` geschrieben und als Workflow-Artefakte veröffentlicht.

## Artefaktpfade (Pflicht)

| Scope        | Pfade                                                                 |
|--------------|----------------------------------------------------------------------|
| Unit         | `backoffice/artifacts/${RUN_DATE}/unit/{junit.xml,coverage.xml,pytest_unit.log}` |
| Lint/Types   | `backoffice/artifacts/${RUN_DATE}/lint/*`, `backoffice/artifacts/${RUN_DATE}/types/mypy.log` |
| Security     | `backoffice/artifacts/${RUN_DATE}/security/{gitleaks.json,bandit.log,trivy_fs.json,open_ports.txt,runtime_security_check.txt}` |
| Integration  | `backoffice/artifacts/${RUN_DATE}/integration/{compose_pre.log,compose_post.log,compose_ps.log,junit.xml,env_sha256.txt,metrics.txt?,health_checks.json,env_missing.txt?}` |

## Akzeptanzkriterien
- `gitleaks` & `trivy` melden **keine** Secrets bzw. HIGH/CRITICAL Vulnerabilities (sonst Security-FAIL + Finding).
- Lint (`black`, `ruff`) und Types (`mypy --strict`) ohne Fehler.
- Unit-Tests sammlen >0 Tests, `coverage.xml` vorhanden.
- Integration liefert JUnit, Health-Checks `<500`, Redis-Bus Smoke erfolgreich.
- Runtime-Security-Check bestätigt non-root, `cap_drop=ALL`, `no-new-privileges`.
- Evidence `TEST_RERUN_EVIDENCE_<RUN_DATE>.md` vollständig inkl. Appendix „Infrastruktur & Controls“, Reviewer-Zeile `⛔ <RUN_DATE> / <REVIEWER>`.
