# Flaky Test Log (Issue #276)

Tracking-Dokument für flaky Tests und deren Behebung.

## Status

| Metrik | Wert | Ziel |
|--------|------|------|
| Critical Flaky | 0 | 0 |
| Known Flaky | 0 | 0 |
| Pass Rate (3x) | TBD | ≥95% |

## Flaky Detection Workflow

### 1. Lokal testen

```bash
# Alle E2E-Tests 3x wiederholen
pytest -m e2e --count=3 -v

# Nur bei Fehler stoppen
pytest -m e2e --count=3 -x

# Mit Timing-Info
pytest -m e2e --count=3 -v --durations=10
```

### 2. CI Integration

```yaml
# .github/workflows/test.yml
- name: Flaky Detection
  run: pytest -m e2e --count=3 --tb=short
  continue-on-error: true

- name: Upload Flaky Report
  uses: actions/upload-artifact@v4
  with:
    name: flaky-report
    path: flaky_results.xml
```

## Flaky Test Inventory

| Test | Status | Root Cause | Fix Plan | Fixed In |
|------|--------|------------|----------|----------|
| - | - | - | - | - |

### Template für neue Einträge

```markdown
| test_example::test_case | 🔴 Critical | Race condition in Redis pub/sub | Add explicit wait | #xxx |
```

## Root Cause Kategorien

| Kategorie | Beschreibung | Typische Lösung |
|-----------|--------------|-----------------|
| TIMING | Timing/Race Condition | Explicit waits, Retry |
| ORDER | Test-Reihenfolge-Abhängigkeit | Isolation, Fixtures |
| STATE | Shared State | Cleanup, Fresh State |
| NETWORK | Netzwerk-Abhängigkeit | Mocking, Retry |
| RESOURCE | Resource Exhaustion | Limits, Cleanup |

## Behebungs-Checkliste

Für jeden flaky Test:

- [ ] 3x Reproduktion bestätigt
- [ ] Root Cause identifiziert
- [ ] Fix implementiert
- [ ] 10x grün nach Fix
- [ ] In dieser Log aktualisiert

## Priorität

1. **Critical (🔴)**: Blockiert CI/CD → Sofort fixen
2. **High (🟠)**: Regelmäßig flaky → Diese Woche
3. **Low (🟡)**: Selten flaky → Backlog

## Metriken-History

| Datum | Total Tests | Flaky | Pass Rate |
|-------|-------------|-------|-----------|
| 2025-12-28 | TBD | 0 | TBD |

## Verifizierung

```bash
# Nach Fixes: 10x Run ohne Fehler
pytest -m e2e --count=10 -x
```
