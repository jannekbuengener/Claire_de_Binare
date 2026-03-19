#!/usr/bin/env python3
"""
Compatibility smoke for the repo's PostgreSQL driver usage.

This keeps Issue #520 small and explicit:
- verify the runtime import path works on the active Python interpreter
- verify repo pins no longer drift back to older psycopg2-binary versions
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXPECTED_PSYCOPG2_BINARY = "2.9.11"
EXPECTED_SPEC = f"psycopg2-binary=={EXPECTED_PSYCOPG2_BINARY}"

PINNED_FILES = [
    Path("requirements.txt"),
    Path("requirements-dev.txt"),
    Path("tools/paper_trading/requirements.txt"),
    Path("services/execution/requirements.txt"),
    Path("services/risk/requirements.txt"),
    Path("services/market/requirements.txt"),
    Path("services/reports/requirements.txt"),
    Path("services/signal/requirements.txt"),
    Path("infrastructure/compose/Dockerfile.test"),
    Path("services/db_writer/Dockerfile"),
    Path(".github/workflows/contracts.yml"),
    Path(".github/workflows/ci.yaml"),
    Path(".github/workflows/e2e.yml"),
    Path(".github/workflows/e2e-tests.yml"),
]


def require_text(path: Path, needle: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    if needle in text:
        return None
    return f"{path.as_posix()}: missing '{needle}'"


def forbid_text(path: Path, needle: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    if needle in text:
        return f"{path.as_posix()}: still contains '{needle}'"
    return None


def main() -> int:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions

    from core.utils.postgres_client import get_postgres_dsn

    failures: list[str] = []

    version = psycopg2.__version__.split()[0]
    if version != EXPECTED_PSYCOPG2_BINARY:
        failures.append(
            "runtime psycopg2 version mismatch: "
            f"expected {EXPECTED_PSYCOPG2_BINARY}, got {version}"
        )

    dsn = get_postgres_dsn(
        host="localhost",
        port=5432,
        database="claire_de_binare",
        user="claire_user",
        password="test-password",
        sslmode="disable",
    )
    if (
        "postgresql://claire_user:test-password@localhost:5432/claire_de_binare"
        not in dsn
    ):
        failures.append(f"unexpected DSN format from core.utils.postgres_client: {dsn}")

    for path in PINNED_FILES:
        if not path.exists():
            failures.append(f"{path.as_posix()}: file missing")
            continue
        missing = require_text(path, EXPECTED_SPEC)
        if missing:
            failures.append(missing)
        stale = forbid_text(path, "psycopg2-binary==2.9.9")
        if stale:
            failures.append(stale)

    print(f"Python: {sys.version.split()[0]}")
    print(f"psycopg2: {psycopg2.__version__}")
    print(f"DSN sample: {dsn}")

    if failures:
        print("Postgres driver compatibility check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        "Postgres driver compatibility check passed: "
        f"runtime import OK, repo pins aligned on {EXPECTED_SPEC}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
