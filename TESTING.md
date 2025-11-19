# Testing Strategy

This project uses `pytest` as the primary test runner. Tests live under the
`tests/` directory (configured via `testpaths = tests`) and are grouped by
marker:

- `@pytest.mark.unit` — fast, isolated unit tests
- `@pytest.mark.integration` — tests that rely on external services like Docker,
  Redis, or Postgres

## Running Tests

- Run the full suite: `pytest`
- Only unit tests: `pytest -m unit`
- Only integration tests (requires services): `pytest -m integration`

Current integration scaffolds are marked with `@pytest.mark.skip` because Docker
and data services are not wired in this cleanroom environment. Remove the skip
markers once the services are available.

Coverage can be enabled when `pytest-cov` is installed:

```bash
pytest --cov=services --cov-report=term-missing --cov-report=html
```

## Environment Validation

A helper script, `tests/validate_setup.ps1`, checks the local environment for
Python 3.12, required testing packages, and the presence of core test files. It
does **not** run pytest automatically. Execute it from the project root:

```powershell
pwsh tests/validate_setup.ps1
```

After the script reports green, run tests manually (for example `pytest -q`).

## Risk Engine Tests

The initial risk engine tests use lightweight fixtures from `tests/conftest.py`
covering configuration defaults, portfolio state, and basic signal events.
Future iterations should extend these fixtures as business rules mature.
