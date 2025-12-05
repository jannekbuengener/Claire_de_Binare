# Repository Guidelines

## Project Structure & Module Organization
- Python trading system; runtime modules in `services/` (risk_engine.py, position_sizing.py, execution_simulator.py, mexc_perpetuals.py) plus service wrappers in `backoffice/services/` (signal_engine, risk_manager, execution_service, db_writer, portfolio_manager, execution_simulator).
- Docs live in `backoffice/docs/` (architecture, runbooks, testing, security); ops helpers in `scripts/` and `backoffice/scripts/`; environment templates at `.env.example` and stack wiring in `docker-compose.yml`.
- Tests sit in `tests/` split into `unit/`, `integration/`, `e2e/`, and `local/` with shared fixtures in `tests/conftest.py`.

## Build, Test, and Development Commands
- Setup: `python -m pip install -r requirements-dev.txt` (use a venv). Copy `.env.example` to `.env` before running services.
- Lint/format: `ruff .` then `black .` or `pre-commit run --all-files` (runs Ruff + Black + basic hygiene).
- Local stack for E2E: `docker compose up -d`; stop with `docker compose down`.
- Tests:
  - CI-fast: `pytest -v -m "not e2e and not local_only"` or `make test` / `./run-tests.ps1 test`.
  - Unit only: `pytest -v -m unit`.
  - Integration (mocked services): `pytest -v -m "integration and not e2e and not local_only"`.
  - E2E: `pytest -v -m e2e` (requires running Docker stack).
  - Coverage: `pytest --cov=services --cov=backoffice/services --cov-report=term`.
  - Full local suite: `make test-full-system` or `./run-tests.ps1 test-full-system`.

## Coding Style & Naming Conventions
- Python 3.11, Black-formatted (88 chars, 4-space indent, LF, final newline per `.editorconfig`); Ruff enforces lint rules. Keep type hints and docstrings on service boundaries.
- Files/modules use `snake_case`; classes `PascalCase`; functions/vars `snake_case` (constants upper snake). Avoid emojis in source for Windows compatibility.

## Testing Guidelines
- Markers: `unit`, `integration`, `e2e`, `local_only`, `slow`, `chaos` (see `pytest.ini`). Only `unit`/`integration` run in CI; `local_only`/`chaos` are destructive and must stay local.
- Name tests `test_*.py`; prefer shared fixtures from `tests/conftest.py` and keep new fixtures isolated.
- E2E/local tests expect Docker health; wait ~10s after `docker compose up -d`. Keep coverage artifacts (`htmlcov/`, `.coverage`) out of commits.

## Commit & Pull Request Guidelines
- Use conventional commits as in history (e.g., `fix(env): complete ENV validation`). Keep scope small and message imperative.
- Before PRs: run Ruff + Black and the CI-fast pytest target; note whether E2E/local suites were executed.
- PR description should include: goal/approach, linked issue, configs touched (`.env`, compose), and test commands/results. For behavioral changes, attach logs/metrics from tests rather than screenshots.

## Security & Configuration Tips
- Never commit secrets. Populate `.env` from `.env.example`; MEXC keys are IP-bound—rotate if the host changes. Prefer local Docker networks and shut stacks down after tests (`docker compose down`) to avoid stale state.
