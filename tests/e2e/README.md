# E2E Tests — Deterministic Test Path

**Issue anchor:** `#354` (historical) · **Marker:** `@pytest.mark.e2e`
**Boundary:** Shadow/Paper-first; LR **NO-GO** — kein Live-Kapital (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)

## Übersicht

End-to-End Tests für die Claire de Binare Trading Pipeline mit deterministischen Fixtures.

**Ziel:** Reproduzierbare, stabile E2E-Tests mit niedriger Flake-Rate.

---

## Test Structure

```
tests/e2e/
├── README.md
├── test_smoke_pipeline.py       # Smoke: market_data → signals
├── test_paper_trading_p0.py     # Paper-trading P0 flows
├── fixtures/
│   └── market_data.json
└── __init__.py
```

---

## Test Scenarios

### 1. Smoke Test: Market Data → Signal Generation

**File:** `test_smoke_pipeline.py::test_smoke_market_data_to_signal`

**Pipeline:**

```
1. market_data fixture → Redis Pub/Sub (market_data topic)
2. cdb_signal → consumes market_data → generates signals
3. signals → Redis Stream (stream.signals)
4. Validation: signals_generated_total > 0
```

**Determinismus:**

- Fixture: `fixtures/market_data.json` (fixed prices, timestamps)
- Expected Output: mindestens 1 Signal generiert
- Metrics: Prometheus `signals_generated_total` Counter

---

## Running Tests

### Local (kanonischer Einstieg)

```powershell
# Kanonischer lokaler E2E-Lauf (Stack-Start + Tests + Teardown)
.\infrastructure\scripts\run_e2e.ps1

# Nur Tests, Stack bereits manuell gestartet
.\infrastructure\scripts\run_e2e.ps1 -SkipStackStart -SkipTeardown
```

Alternativ über Makefile (BLUE+RED muss laufen):

```bash
make docker-up
make test-e2e
```

### Local (manueller Debug-/Fallback-Pfad)

**431B CI lab** (isoliert, nicht der Operator-BLUE+RED-Runtime):

```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up -d
pytest -m e2e -v --tb=short
```

**Operator runtime** (BLUE+RED, wenn E2E gegen laufenden Stack):

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
pytest -m e2e -v --tb=short
```

Legacy `base.yml + dev.yml + logging.yml` ist **nicht** der kanonische Operator- oder E2E-Einstieg.

### CI (GitHub Actions)

**Offizieller Workflow:** `.github/workflows/e2e.yml`

Automatisch bei Push auf `main` (path-filtered), `workflow_dispatch`, und wöchentlich (So 06:30 UTC).

---

## Debugging

### Service Health

```powershell
docker ps --filter name=cdb_ --format "table {{.Names}}\t{{.Status}}"
make docker-health
```

### Logs

```powershell
docker logs cdb_signal --tail 50
docker logs cdb_ws --tail 50
```

### Common Issues

**`signals_generated_total = 0`:** Signal-Health, Redis Pub/Sub auf `market_data`, Fixture prüfen.

**Flaky results:** Wartezeiten/Race Conditions, Stack-Clean-State vor Run sicherstellen.

---

## CI vs Local

| Surface | Stack canon | Pytest |
|---|---|---|
| `run_e2e.ps1` | Script-gesteuert | `tests/e2e/` |
| `make test-e2e` | BLUE+RED (manuell vorher `make docker-up`) | `-m e2e` |
| CI `e2e.yml` | Workflow-definiert | `-m e2e` |

Unit/Integration ohne Container: `make test` (exkl. `e2e`, `local_only`).

---

## Contact / References

- Compose canon: `infrastructure/compose/README.md`
- Signal stream: `stream.signals` (`services/signal/README.md`)
- Engineering ledger: `CURRENT_STATUS.md`
