# Repository Guidelines

## Project Structure & Module Organization
- `/core`: shared domain models, typed config loaders, and utilities that multiple services consume; keep generic helpers here and avoid embedding service-specific logic.
- `/services`: stateless runtime components (execution, risk, signal, psm, db_writer, etc.), with each service in its own directory containing the service module, config, Dockerfile, and requirements.
- `/infrastructure`: deployment scaffolding (compose fragments, IaC, monitoring, database schema and migration scripts) organized under `/infrastructure/compose`, `/infrastructure/k8s`, `/infrastructure/monitoring`, and `/infrastructure/database`.
- `/tests`: structured as `unit/`, `integration/`, and `replay/` suites aligned with the corresponding service names.
- `/governance`: canonical policies (read-only) live here; follow them before changing other zones and rely on `CDB_KNOWLEDGE_HUB.md` for writable notes.

## Build, Test, and Development Commands
- `make test`: runs `make test-unit` and `make test-integration` (CI-friendly pytest markers).
- `make test-unit`: runs `pytest -v -m unit` for deterministic unit coverage.
- `make test-integration`: runs `pytest -v -m "integration and not e2e and not local_only"`.
- `make test-e2e` and `make test-local*`: execute E2E/local suites and assume `docker compose up -d` is running; use these only in controlled local environments.
- `make docker-up`, `make docker-down`, `make docker-health`: manage the Compose stack and inspect container status.
- `make install-dev`: installs dev dependencies via `pip install -r requirements-dev.txt`.

## Coding Style & Naming Conventions
- Python files use `snake_case` for functions/variables and `CamelCase` for classes, with four spaces per indent to keep formatting consistent.
- Favor pure helpers and deterministic utilities; avoid hidden randomness or current timestamps unless explicitly passed as config (`seed`, `timestamp`).
- Configuration lives in env files and passed variables, never hardcoded secrets inline.
- Run the formatting/linting tools referenced in `requirements-dev.txt` before commits to keep style deterministic.

## Testing Guidelines
- Use `pytest` markers (`unit`, `integration`, `e2e`, `local_only`, `slow`, etc.) so the intentions of each suite stay explicit and deterministic.
- Name test files `test_<area>.py` and mirror the service directory structure under `/tests`.
- Replay tests live under `/tests/replay/` to satisfy the PSM policy; they must rehydrate deterministic event sequences.
- Run `make test` for core coverage and `make test-coverage` to generate `htmlcov` reports before merging changes to services or core logic.

## Commit & Pull Request Guidelines
- Follow the conventional-style history: `type(scope): short description` (e.g., `fix(execution): handle zero trades`).
- Mention the relevant issue (if any), describe the change, list affected commands/tests, and attach logs/screenshots for user-facing or operational updates.
- Ensure the touched services’ suites pass (`make test` or the targeted marker) and note any deviations directly in the PR description.
