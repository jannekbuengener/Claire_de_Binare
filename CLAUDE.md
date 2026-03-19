# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claire de Binare (CDB) is a Python 3.12 crypto trading system with signal processing, risk management, order execution, and market regime detection. It runs on Docker Compose (PostgreSQL, Redis, service containers) and is developed on Windows 11 with Git Bash (MINGW64).

## Commands

### Install dependencies
```bash
pip install -r requirements.txt -r requirements-dev.txt -r requirements-mcp.txt
pip install ruff black
```

### Run all CI tests (unit + integration)
```bash
make test
# or directly:
pytest -q -k "not test_mcp_time_server_runtime"
```

### Run specific test categories
```bash
pytest -v -m unit                          # Unit tests only
pytest -v -m "integration and not e2e"     # Integration tests (mocked)
pytest -v -m e2e                           # E2E (requires running containers)
pytest tests/unit/test_foo.py              # Single file
pytest tests/unit/test_foo.py::test_bar    # Single test
```

### Linting (must pass in CI)
```bash
ruff check .                               # Lint
black --config pyproject.toml --check .    # Formatting check
```

### Docker stack
```bash
make docker-up       # Start the canonical BLUE+RED local runtime
make docker-down     # Stop containers
make docker-health   # Check container health
```

`base.yml + dev.yml` remain only for CI/test and explicit legacy/debug
flows; they are not the normal operator/runtime path.

### Coverage (not enforced in CI by default)
```bash
make test-coverage   # 80% minimum for core/ and services/
```

## Architecture

### Core (`core/`)
Domain models (`domain/models.py`), event types (`domain/event.py`), configuration (`config/`), indicators, replay logic, safety guards, and auth/secrets handling. Central types: `Signal`, `Order`, `OrderResult`.

### Services (`services/`)
Each subdirectory is a microservice: `signal/` (signal generation), `risk/` (risk assessment), `execution/` (order execution), `allocation/` (portfolio allocation), `regime/` (market regime detection), `market/` (market data), `candles/` (candlestick data), `ws/` (WebSocket/MEXC), `reports/`, `validation/`, `db_writer/`.

### Infrastructure (`infrastructure/`)
- `compose/` — Docker Compose fragments: canonical runtime is
  `compose.blue.yml` + `compose.red.yml`; legacy fragments such as
  `base.yml`/`dev.yml` remain for CI/test or explicit compatibility flows.
- `actions-runner/` — Self-hosted GitHub Actions runner (labels: `cdb, docker`)
- `scripts/` — Operational scripts (systemcheck, daily_check, evidence generation)

### Tests (`tests/`)
Organized by type: `unit/`, `integration/`, `e2e/`, `contract/`, `smoke/`, `replay/`, `chaos/`, `performance/`, `load/`, `resilience/`. Markers defined in `pytest.ini`. Shared fixtures in `tests/conftest.py`.

### Governance (`governance/`)
Delivery approval gates, secrets policy, canary readiness configs.

### CDB Agent SDK (`cdb_agent_sdk/`)
Separate Python package with its own `pyproject.toml` and `uv.lock`.

## CI & Branch Protection

Two required checks on `main`:
1. **`ci (Unit/Integration + Lint gesammelt)`** — runs on self-hosted runner (`[self-hosted, cdb]`): ruff, black (diff-only), pytest (excluding `test_mcp_time_server_runtime`), MCP config validation
2. **`policy-gate`** — categorizes PRs by scope:
   - `docs-only`: only `docs/**` or `*.md` files
   - `workflows-only`: only `.github/workflows/**`
   - `infra-only`: only `infrastructure/**`
   - `core/service`: everything else — requires label `allow-core-change` or `manual-approval`

Branch must be up-to-date with `main` before merge (`strict: true`). Bot review threads must be resolved before merge.

## Linting Configuration (`pyproject.toml`)

- **black**: line-length 88, target py312, excludes `services/ws/mexc_proto_gen/`
- **ruff**: select E+F rules, ignores E501/F401/F541. Tests additionally ignore F811/F841/E402

## Platform Caveats (Windows / Git Bash)

- Git Bash (MINGW64) converts Unix paths in arguments. Use `MSYS_NO_PATHCONV=1` before Docker commands that contain Linux paths (e.g., `/var/run/docker.sock`)
- Another AI agent (Kodex/OpenAI) may switch branches — always verify current branch with `git rev-parse --abbrev-ref HEAD` before committing
- Docker Compose resolves paths correctly (uses Docker API directly)
