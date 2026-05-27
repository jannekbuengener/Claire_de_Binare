# AGENTS

Status: Root Pointer + Session Compass
Scope: Working Repo

Diese Datei ist der Root-Pointer fuer die lokale Agenten-Registry im Working Repo
und der schnelle Einstiegsanker fuer kanonische Dateien und aktuellen Projektstatus.

Kanonische Agenten-Registry:
[`agents/AGENTS.md`](agents/AGENTS.md)

Verknuepfte Rolle:
[`agents/roles/CODEX.md`](agents/roles/CODEX.md)

Wichtige kanonische Dateien:
- [`docs/meta/WORKING_REPO_CANON.md`](docs/meta/WORKING_REPO_CANON.md)
- [`knowledge/governance/CDB_CONSTITUTION.md`](knowledge/governance/CDB_CONSTITUTION.md)
- [`knowledge/governance/CDB_GOVERNANCE.md`](knowledge/governance/CDB_GOVERNANCE.md)
- [`knowledge/governance/CDB_AGENT_POLICY.md`](knowledge/governance/CDB_AGENT_POLICY.md)
- [`knowledge/CDB_KNOWLEDGE_HUB.md`](knowledge/CDB_KNOWLEDGE_HUB.md)
- [`CURRENT_STATUS.md`](CURRENT_STATUS.md)
- [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- [`docs/runbooks/CONTROL_REGISTER.md`](docs/runbooks/CONTROL_REGISTER.md)
- [`knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md`](knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md)
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- [`agents/OPEN_CODE_AGENTS.md`](agents/OPEN_CODE_AGENTS.md)

Aktueller Projektstand:
- Working Repo ist der produktive Canon fuer Agenten-, Governance-, Knowledge- und Navigationsdoku.
- Repo-/Engineering-Status steht in [`CURRENT_STATUS.md`](CURRENT_STATUS.md); offene PRs, letzte Main-Merges und Arbeitsstatus dort einsehen.
- Operatives Live-Readiness-Verdikt laut [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md): `NO-GO`; reale Trades bleiben durch Human Gate blockiert.
- Board-/Stage-Status laut [`docs/runbooks/CONTROL_REGISTER.md`](docs/runbooks/CONTROL_REGISTER.md): `stage:trade-capable` (ratifiziert 2026-04-08 via Issue `#1492`); dieses Stage-System ist orthogonal zum LR-System und autorisiert weder Live-Kapital noch Strategie-Freigabe.
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) und `knowledge/CURRENT_STATUS.md` sind historische Snapshots und nicht der aktuelle Gesamtstatus.

Status-Regel:
- Fuer Board-/Stage-Status und operativen Fokus zuerst [`docs/runbooks/CONTROL_REGISTER.md`](docs/runbooks/CONTROL_REGISTER.md) lesen; Stage-Mapping und Board-Regeln stehen in [`knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md`](knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md).
- Fuer aktuellen Repo- und Engineering-Stand zuerst [`CURRENT_STATUS.md`](CURRENT_STATUS.md) lesen.
- Fuer operativen Go/No-Go- und Echtgeld-Stand zuerst [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) lesen.
- Stage-Aussagen nie als LR-Go/No-Go lesen und LR-Verdikte nie aus einer Board-Stage ableiten.
- Historische Statusdateien nur als Rueckgriff verwenden und nicht als SSOT behandeln.

Hinweis:
- Das Working Repo ist der produktive Standardpfad fuer Agenten-, Governance- und Navigationsdoku.
- Das lokale Archiv unter `docs/archive/docs_hub_snapshot/` ist nur noch historischer Rueckgriff und nicht mehr Canon.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make test-unit` | Run unit tests (`pytest -v -m unit`) |
| `make test-integration` | Run integration tests with mocks |
| `make test-e2e` | Run E2E tests (requires running stack) |
| `make test-coverage` | Run tests with 80% coverage enforcement |
| `ruff check .` | Lint with Ruff |
| `black .` | Format with Black |
| `mypy core/ services/` | Type check |

---

## Build / Lint / Test Commands

### Running Tests

```bash
# All CI tests (unit + integration)
make test
# or via specific targets:
make test-unit && make test-integration

# Run a single test file
pytest -v tests/unit/risk/test_risk_service.py

# Run a single test function
pytest -v tests/unit/risk/test_risk_service.py::test_exposure_limit_bypassed_for_reduce_only_sell

# Run tests matching a keyword
pytest -v -k "exposure"

# Run with coverage (enforced via make test-coverage)
pytest --cov=core --cov=services --cov=infrastructure/scripts --cov-report=html --cov-report=term --cov-fail-under=80 -m "not e2e and not local_only"

# E2E tests (requires: make docker-up)
pytest -v -m e2e

# Local-only tests (requires running stack)
pytest -v -m local_only
```

### Common Test Markers (pytest.ini - not exhaustive)

- `@pytest.mark.unit` - Fast, isolated unit tests (CI)
- `@pytest.mark.integration` - Tests with mocks (CI)
- `@pytest.mark.contract` - Validate API/service contracts
- `@pytest.mark.external` - Tests requiring external network
- `@pytest.mark.e2e` - End-to-End with real containers
- `@pytest.mark.local_only` - Explicitly local only (not CI)
- `@pytest.mark.slow` - Tests with >10s runtime
- `@pytest.mark.chaos` - Chaos/Resilience tests (DESTRUCTIVE)
- `@pytest.mark.performance` - Performance/Latency tests
- `@pytest.mark.resilience` - Recovery/DR tests
- `@pytest.mark.feature` - Feature-specific tests
- `@pytest.mark.mandatory` - Critical path tests
- `@pytest.mark.load` - Load/Stress tests
- `@pytest.mark.smoke` - Sanity checks

### Linting & Formatting

```bash
# Lint (Ruff)
ruff check .

# Format (Black) - line length 88, target Python 3.12
black .

# Type checking (mypy)
mypy core/ services/

# Security scan
make security-scan
# runs: gitleaks detect, ruff check, bandit -r core/ services/
```

### Docker Operations

```bash
# Start canonical BLUE+RED stack
make docker-up
# or:
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d

# Health check
make docker-health

# Stop
make docker-down
```

---

## Code Style Guidelines

### Formatting
- **Formatter:** Black (line-length=88, target-version=py312)
- **Linter:** Ruff (select=["E", "F"], ignore=["E501", "F401", "F541"])
- No line length enforcement (E501 ignored), soft limit 88 chars

### Imports
```python
from __future__ import annotations

import copy
from decimal import Decimal
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import redis
import psycopg2

from core.utils.redis_client import create_redis_client
from core.utils.uuid_gen import generate_uuid
```

Rules:
1. `from __future__ import annotations` first
2. Standard library (alphabetical)
3. Third-party libraries
4. Local modules (`core.*`, `services.*`, `infrastructure.*`)
5. One import per line; no `import os, sys`

### Type Hints
- Type hints are expected for new or touched production Python APIs.
- Tests, fixtures, scripts and legacy code should follow local style unless the task explicitly hardens typing.
- Use `typing.TYPE_CHECKING` for circular imports.
- Use `Optional[X]` or `X | None` (with future annotations).
- Use `Decimal` for money, order quantities, accounting, risk-/execution-relevant financial values.
- `float` is acceptable for non-financial metrics, indicators, percentages, telemetry, or existing contracts where already established. Do not silently change numeric semantics.

```python
def process_order(order_id: str, quantity: Decimal) -> Optional[dict]:
    ...
```

### Naming Conventions
| Element | Convention | Example |
|---------|-------------|---------|
| Files | `snake_case` | `service.py`, `test_risk_service.py` |
| Classes | `PascalCase` | `RiskManager`, `OrderValidator` |
| Functions/Variables | `snake_case` | `compute_hash`, `order_count` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| Private members | `_leading_underscore` | `_internal_state` |

### Error Handling
- Use explicit exception types, avoid bare `except:`
- Log errors with context before re-raising
- Use `Decimal` exceptions for financial math: `InvalidOperation`
- Fail-closed for security-critical paths

```python
try:
    result = Decimal(raw_value)
except InvalidOperation:
    logger.error("Invalid decimal value", extra={"raw": raw_value})
    raise ValueError(f"Cannot parse decimal: {raw_value}")
```

### Testing Requirements
- **Coverage:** 80% minimum (enforced via `--cov-fail-under=80`)
- **Markers:** Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- **File location:** `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/local/`
- **Naming:** `test_<module>_<description>.py` or `test_<description>.py`
- **Fixtures:** Prefer module-level fixtures in `conftest.py`

### Security Rules
- **No hardcoded secrets** (enforced via gitleaks)
- **No `float` for financial values** (use `Decimal`)
- **Input validation** on all external data (Redis streams, API responses)
- **Secrets via environment:** `SECRETS_PATH` or environment variables
- **No Tresor access** (see `CDB_TRESOR_POLICY.md`)

### Determinism & Auditability
- All system state must be **reproducible** (CDB_CONSTITUTION.md).
- Use `core.utils.uuid_gen` for event-/decision-/audit-relevant IDs where CDB-owned deterministic IDs are required.
- Do not replace external IDs or test fixture IDs without explicit scope.
- Log decision context (Decision Events for governance-critical paths).
- No blackbox decisions; all logic must be traceable.

---

## Selected repo skills (not exhaustive)

Codex skill surface: `.codex/cdb_skills/`

Cursor skill surface: `.cursor/skills/` (repo-versioniert; PR 1: Session-Foundation)

OpenCode skill surface zusaetzlich: `.opencode/skills/` (gezielt laden, nicht pauschal).

| Skill | Purpose | Cursor path |
|-------|---------|-------------|
| `cdb-session-start` | Fail-closed session start (verifies Git truth first) | `.cursor/skills/cdb-session-start/SKILL.md` |
| `cdb-session-close` | Disciplined session close with honest summary | `.cursor/skills/cdb-session-close/SKILL.md` |
| `cdb-issue-to-session-plan` | Convert issue to session plan | `.cursor/skills/cdb-issue-to-session-plan/SKILL.md` |
| `cdb-control-intake` | Control context reading | `.cursor/skills/cdb-control-intake/SKILL.md` |
| `cdb-shadow-validation` | Shadow validation workflows |
| `cdb-backtest-engine` | Backtest engine operations |
| `cdb-ci-cd-guard` | CI/CD guardrails |
| `cdb-contract-evidence-gatekeeper` | Contract evidence gating |
| `cdb-drift-reconcile` | Drift reconciliation |
| `cdb-exchange-adapters` | Exchange adapter operations |
| `cdb-risk-governance` | Risk governance operations |
| `cdb-trading-core` | Trading core operations |
| `cdb-docs-ops` | Documentation and ops-doc maintenance |
| `codex-primary-runtime` | Core runtime operations |
| `ctb-docker-stack` | Docker stack operations |
| `gh-address-comments` | GitHub comment handling |
| `gh-fix-ci` | CI fix operations |

---

## Agent Operating Rules

- Read `knowledge/governance/CDB_AGENT_POLICY.md` section 4 before any write.
- Respect single-writer locks, explicit stop signals, and write gates.
- `DELIVERY_APPROVED.yaml` is human-controlled; agents must not modify it.
- Before planning for strategy/runtime/module/service/contract/context scope, output a `Brain Evidence` block (see `agents/AGENTS.md` § Brain Evidence Gate).
- LR status remains NO-GO for live trading unless explicitly changed by canon/human approval.
