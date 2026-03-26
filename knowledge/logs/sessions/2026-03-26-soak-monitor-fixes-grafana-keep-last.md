# Session Log — 2026-03-26: Soak-Monitor-Fixes (#1282/#1283) + Grafana KeepLast (#1266/#1267)

**Branch**: `fix/1281-db-check-pg-env-resolution`
**Commits**: `08f7e7b` (soak-monitor), `216d0eb` (grafana)

---

## Kontext

72h-Soak-Run LR-040 (gestartet 2026-03-25 12:12 UTC, Artefaktpfad `artifacts/soak_test_20260325_121250`) war zum Zeitpunkt der Soak-Monitor-Änderungen noch aktiv. Alle Änderungen waren non-destructive (keine Cron-Eingriffe, keine Artefakt-Löschung).

---

## Issue #1283 — Generischer Pointer in `_write_active_run_path()`

**Root Cause**: `_write_active_run_path()` schrieb nur den intent-spezifischen Pointer (`soak_active_run_path_lr040.txt`). Der generische Pointer `soak_active_run_path.txt` fehlte für lr040-Runs, obwohl Runbook und CURRENT_STATUS.md ihn als vorhanden dokumentierten.

**Fix** (`infrastructure/scripts/soak_monitor.sh`):
- In `_write_active_run_path()` nach dem intent-spezifischen Write: `if [ "$SOAK_RUN_INTENT" = "lr040" ]; then printf '%s\n' "$artifact_path" > "$ARTIFACT_ROOT/soak_active_run_path.txt"; fi`
- Validation-Runs berühren den generischen Pointer nicht

**Tests** (`tests/unit/scripts/test_soak_monitor_timeline.py`):
- `_simulate_write_active_run_path()` als Python-Mirror der Bash-Funktion
- `TestGenericPointerSync` (4 Tests): lr040 schreibt beide Pointer, validation schreibt nur intent-spezifisch, unbekannter Intent schreibt keinen generischen Pointer

---

## Issue #1282 — Disk-Check DISK_UNAVAILABLE Robustheit

**Root Cause**: `df /repo 2>/dev/null | awk ...` — stderr unterdrückt, kein Exit-Code, keine Unterscheidung zwischen Command-Failure (exit != 0) und Parse-Failure (exit 0, kein parsebarer Output). disk_evidence und disk_alerts.log enthielten keinen Diagnose-Grund.

**Fix** (`infrastructure/scripts/soak_monitor.sh`, Check 5):
- Raw-Output einmal capturen: `DF_REPO_RAW=$(df -h /repo 2>&1) || DF_REPO_RC=$?`
- `DISK_UNAVAILABLE_REASON` für Command-Failure vs. Parse-Failure gesetzt
- disk_evidence: Reason + Raw-Output (Newlines normalisiert mit `tr '\n' ' '`)
- disk_alerts.log: konkreter Reason statt generischer String
- Semantik von `ARTIFACT_DISK_PCT` unverändert (Zahl oder leer)

**Tests** (`tests/unit/scripts/test_soak_monitor_timeline.py`):
- Fixture `_DF_COMMAND_FAILED`
- 2 neue Tests in `TestDiskSpaceCheck` dokumentieren die zwei Failure-Modi

---

## Issues #1266/#1267 — Grafana execErrState DatasourceError-Spam

**Root Cause (gemeinsam)**:
- `orders_rejected.yml` + `high_error_rate.yml` hatten `execErrState: Error`
- Bei transienten Docker-DNS-Ausfällen (Container-Neustart entfernt kurz den DNS-Eintrag für `cdb_prometheus`) → Grafana bekommt `no such host` → sofort Error-State-Alert + Mail

**Warum erster Versuch (PR #1273) scheiterte**:
- `KeepLastState` ist im Unified Alerting kein gültiger Wert (war Legacy-Classic-Alerting-String)
- Grafana lieferte: `unknown Error state option KeepLastState` → Restart-Loop

**Echter Fix** (`216d0eb`):
- Korrekter String: `KeepLast` (Enum `models.KeepLastErrState` in `pkg/services/ngalert/models/alert_rule.go`)
- Unterstützt seit Grafana 10.4/11.0, funktioniert mit aktuellem 11.4.7-ubuntu-Image
- Kein Image-Upgrade nötig

**Geändert**:
- `orders_rejected.yml`: `execErrState: Error` → `execErrState: KeepLast`
- `high_error_rate.yml`: `execErrState: Error` → `execErrState: KeepLast`
- `test_grafana_alerting_provisioning.py`:
  - `VALID_EXEC_ERR_STATES`: `"KeepLastState"` entfernt, `"KeepLast"` ergänzt
  - `KEEP_LAST_STATE_RULES`: `set()` → `{"cdb-orders-rejected", "cdb_error_rate_high"}`
  - Placeholder-Asserts durch aktive Regression-Guards ersetzt
  - Docstrings auf korrekte Root-Cause korrigiert

**Verifikation**: 21/21 Grafana-Provisioning-Tests grün

**Bewusst nicht geändert**: Datasource-URL, Grafana-Image-Version, Alertmanager-Routing, Fachschwellen

---

## Gesamt-Teststand

```
test_soak_monitor_timeline.py:         110 passed
test_grafana_alerting_provisioning.py:  21 passed
```

---

## Offen nach dieser Session

- **#1266/#1267 Runtime-Wirksamkeit**: Grafana muss einmal mit der aktualisierten Provisioning-Konfiguration neu geladen / neu gestartet werden, damit `KeepLast` runtime-wirksam wird. In dieser Session wurde kein RED-/Grafana-Restart durchgeführt.
- **#1269** (midnight-rollover): Bewusst offen bis Live-Evidence vorliegt
- **LR-040 Soak-Run**: Läuft bis 2026-03-28 12:12 UTC; Gate-Evaluierung danach
