"""PostgreSQL Database Fixtures for E2E Tests.

Provides deterministic DB state management:
- reset_db: Truncate all tables
- seed_db: Load test seed data
- clean_db: Reset + Seed in one step (most common)
"""

import os
import pytest
import psycopg2
from pathlib import Path


def get_db_connection():
    """Get PostgreSQL connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "claire_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.getenv("POSTGRES_DB", "claire_de_binare"),
    )


def execute_sql_file(conn, sql_file_path: Path):
    """Execute SQL file against database connection."""
    with conn.cursor() as cur:
        sql_content = sql_file_path.read_text(encoding="utf-8")
        cur.execute(sql_content)
    conn.commit()


@pytest.fixture(scope="function")
def reset_db():
    """Fixture: Reset database by truncating all tables.

    Usage:
        def test_something(reset_db):
            # DB is now clean (all tables truncated)
            pass
    """
    conn = get_db_connection()
    try:
        fixtures_dir = Path(__file__).parent / "sql"
        reset_script = fixtures_dir / "00_reset.sql"
        execute_sql_file(conn, reset_script)
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="function")
def seed_db(reset_db):
    """Fixture: Reset DB and load seed data.

    Usage:
        def test_with_data(seed_db):
            # DB has deterministic seed data loaded
            pass

    Seed Data:
        - 1 portfolio snapshot (100k USDT)
        - 3 signals (BTC/ETH/BNB)
        - 3 orders (1 filled, 1 rejected, 1 pending)
        - 1 trade (BTC buy)
        - 1 position (BTC long)
    """
    conn = reset_db  # reset_db fixture provides connection
    fixtures_dir = Path(__file__).parent / "sql"
    seed_script = fixtures_dir / "01_seed_data.sql"
    execute_sql_file(conn, seed_script)
    yield conn


@pytest.fixture(scope="function")
def clean_db(seed_db):
    """Fixture: Alias for seed_db (reset + seed).

    Most common fixture for E2E tests.

    Usage:
        def test_order_flow(clean_db):
            # DB is reset and seeded with test data
            pass
    """
    return seed_db


# Module-level function for manual DB management (non-fixture usage)
def reset_database():
    """Reset database manually (non-pytest usage)."""
    conn = get_db_connection()
    try:
        fixtures_dir = Path(__file__).parent / "sql"
        reset_script = fixtures_dir / "00_reset.sql"
        execute_sql_file(conn, reset_script)
    finally:
        conn.close()


def seed_database():
    """Seed database manually (non-pytest usage)."""
    conn = get_db_connection()
    try:
        fixtures_dir = Path(__file__).parent / "sql"
        reset_script = fixtures_dir / "00_reset.sql"
        seed_script = fixtures_dir / "01_seed_data.sql"
        execute_sql_file(conn, reset_script)
        execute_sql_file(conn, seed_script)
    finally:
        conn.close()


if __name__ == "__main__":
    # Allow running as script for manual DB reset/seed
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "reset":
            reset_database()
            print("[OK] Database reset complete")
        elif command == "seed":
            seed_database()
            print("[OK] Database reset and seeded")
        else:
            print(f"Unknown command: {command}")
            print("Usage: python db_fixtures.py [reset|seed]")
            sys.exit(1)
    else:
        seed_database()
        print("[OK] Database reset and seeded (default action)")
