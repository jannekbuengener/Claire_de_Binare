"""
E2E Happy Path Test - Deterministic Pipeline Validation
Sprint 2 Part 2: Issue #620

Tests complete signal → risk → execution → order_results → DB flow.

Assertions (run_id-based, deterministic):
- orders_executed >= 1 (filtered by run_id)
- trades_in_db >= 1 (filtered by bot_id == run_id)
- Optional: exactly N trades if deterministic
"""

import os
import sys
import time
import json
import uuid
import redis
import psycopg2
import pytest
from pathlib import Path
from typing import Dict, Any

# Add repo root to path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from tests.e2e.replay_runner import ReplayRunner

pytestmark = pytest.mark.e2e


class TestHappyPath:
    """E2E Happy Path Test Suite - Sprint 2 Part 2 #620"""

    # Mismatch Budget (Governance Gate) - Sprint 2 Part 2 #620
    # Maximum acceptable missing trades due to async DB writer lag
    # Default: 5 (production-grade baseline)
    # Override: E2E_MISMATCH_BUDGET env var (must be positive integer)
    MISMATCH_BUDGET_DEFAULT = 5

    @classmethod
    def get_mismatch_budget(cls) -> tuple[int, str]:
        """
        Get mismatch budget from env or default.

        Returns:
            tuple[int, str]: (budget_value, source)
                - budget_value: Integer budget (> 0)
                - source: "default" or "env"

        Raises:
            ValueError: If E2E_MISMATCH_BUDGET is invalid (not int or <= 0)
        """
        env_budget = os.getenv("E2E_MISMATCH_BUDGET")

        if env_budget is None:
            return cls.MISMATCH_BUDGET_DEFAULT, "default"

        # Validate env var
        try:
            budget_value = int(env_budget)
        except ValueError as e:
            raise ValueError(
                f"E2E_MISMATCH_BUDGET must be a valid integer, got: '{env_budget}'. "
                f"Example: E2E_MISMATCH_BUDGET=10"
            ) from e

        if budget_value <= 0:
            raise ValueError(
                f"E2E_MISMATCH_BUDGET must be positive (> 0), got: {budget_value}. "
                f"Use default (5) or set a positive value like E2E_MISMATCH_BUDGET=10"
            )

        return budget_value, "env"

    @pytest.fixture(scope="class")
    def redis_client(self):
        """Redis client for stream verification."""
        redis_password = os.getenv("REDIS_PASSWORD")
        if not redis_password:
            secrets_path = os.getenv("SECRETS_PATH", os.path.expanduser("~/.secrets/.cdb"))
            password_file = Path(secrets_path) / "REDIS_PASSWORD"
            if password_file.exists():
                redis_password = password_file.read_text().strip()

        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=redis_password,
            db=0,
            decode_responses=True,
        )

        client.ping()
        yield client
        client.close()

    @pytest.fixture(scope="class")
    def postgres_client(self):
        """Postgres client for order_results verification."""
        # Read Postgres password from secrets
        secrets_path = os.getenv("SECRETS_PATH", os.path.expanduser("~/.secrets/.cdb"))
        password_file = Path(secrets_path) / "POSTGRES_PASSWORD_DSN"

        if password_file.exists():
            dsn = password_file.read_text().strip()
            # Replace cdb_postgres with localhost (we're outside Docker)
            dsn = dsn.replace("cdb_postgres", "localhost")
            conn = psycopg2.connect(dsn)
        else:
            # Fallback to environment variables
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "cdb"),
                user=os.getenv("POSTGRES_USER", "cdb_user"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )

        yield conn
        conn.close()

    @pytest.fixture(scope="function")
    def run_id(self):
        """Generate unique run_id for E2E determinism tracking (Sprint 2 Part 2 #620)."""
        return f"e2e-{uuid.uuid4().hex[:12]}"

    @pytest.fixture(scope="function")
    def replay_runner(self, run_id):
        """Replay runner with deterministic fixture and run_id."""
        fixture_path = repo_root / "tests" / "e2e" / "fixtures" / "mexc_btcusdt_replay.json"

        redis_password = os.getenv("REDIS_PASSWORD")
        if not redis_password:
            secrets_path = os.getenv("SECRETS_PATH", os.path.expanduser("~/.secrets/.cdb"))
            password_file = Path(secrets_path) / "REDIS_PASSWORD"
            if password_file.exists():
                redis_password = password_file.read_text().strip()

        runner = ReplayRunner(
            fixture_path=str(fixture_path),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=redis_password,
            run_id=run_id,  # Sprint 2 Part 2 #620: E2E determinism tracking
        )

        runner.load_fixture()
        runner.connect_redis()

        yield runner

        runner.cleanup()

    def get_order_results_for_run(
        self, redis_client: redis.Redis, run_id: str, count: int = 1000
    ) -> list:
        """
        Get order_results from stream filtered by bot_id == run_id.

        Sprint 2 Part 2 #620: run_id-based filtering for deterministic E2E.
        """
        all_results = redis_client.xrevrange("stream.order_results", "+", "-", count=count)

        filtered_results = []
        for result_id, result_data in all_results:
            if result_data.get("bot_id") == run_id:
                filtered_results.append((result_id, result_data))

        return filtered_results

    def get_trades_for_run(self, postgres_client, run_id: str) -> list:
        """
        Query trades from Postgres filtered by bot_id == run_id.

        Sprint 2 Part 2 #620: run_id-based filtering for deterministic E2E.
        """
        cursor = postgres_client.cursor()

        # Check if bot_id column exists first
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'trades' AND column_name = 'bot_id'
            """
        )
        has_bot_id = cursor.fetchone() is not None

        if has_bot_id:
            cursor.execute(
                """
                SELECT id, order_id, symbol, side, status, timestamp
                FROM trades
                WHERE metadata->>'bot_id' = %s OR metadata::text LIKE %s
                ORDER BY timestamp DESC
                """,
                (run_id, f'%"bot_id": "{run_id}"%'),
            )
        else:
            # Fallback: filter by metadata JSON field
            cursor.execute(
                """
                SELECT id, order_id, symbol, side, status, timestamp
                FROM trades
                WHERE metadata::text LIKE %s
                ORDER BY timestamp DESC
                """,
                (f'%{run_id}%',),
            )

        results = cursor.fetchall()
        cursor.close()
        return results

    @pytest.mark.e2e
    def test_happy_path_deterministic_pipeline(
        self, replay_runner, redis_client, postgres_client, run_id
    ):
        """
        Test: Complete pipeline signal → risk → execution → order_results → DB.

        Sprint 2 Part 2 #620: E2E Harness with Hard Assertions (run_id-based)

        Expected (deterministic, run_id-filtered):
            - Order results in stream: >= 1 (filtered by bot_id == run_id)
            - Trades in DB: >= 1 (filtered by metadata bot_id == run_id)
        """
        # Get mismatch budget (with fail-fast validation)
        mismatch_budget, budget_source = self.get_mismatch_budget()

        print("\n" + "=" * 60)
        print("E2E HAPPY PATH TEST: Deterministic Pipeline")
        print(f"Run ID: {run_id}")
        print(f"Mismatch Budget: {mismatch_budget} (source: {budget_source})")
        print("=" * 60)

        # Run replay with run_id tagging
        print(f"\n[Running replay (40 ticks, run_id={run_id})]")
        stats = replay_runner.run(tick_delay_ms=0)

        print(f"  Ticks published: {stats['ticks_published']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Duration: {stats['duration_ms']}ms")

        assert stats["errors"] == 0, "Replay should complete without errors"

        # Wait for pipeline processing
        print(f"\n[Waiting for pipeline processing (5s)]")
        time.sleep(5)

        # Get order_results filtered by run_id
        print(f"\n[Fetching order_results for run_id={run_id}]")
        order_results = self.get_order_results_for_run(redis_client, run_id, count=1000)
        print(f"  Found {len(order_results)} order_results with bot_id={run_id}")

        if order_results:
            print(f"\n[Sample Order Results (first 5)]")
            for result_id, result_data in order_results[:5]:
                symbol = result_data.get("symbol", "N/A")
                side = result_data.get("side", "N/A")
                status = result_data.get("status", "N/A")
                print(f"  {result_id}: {symbol} {side} {status}")

        # Get trades from DB filtered by run_id
        print(f"\n[Fetching trades for run_id={run_id}]")
        trades = self.get_trades_for_run(postgres_client, run_id)
        print(f"  Found {len(trades)} trades with bot_id={run_id}")

        if trades:
            print(f"\n[Sample Trades (first 5)]")
            for row in trades[:5]:
                trade_id, order_id, symbol, side, status, timestamp = row
                print(f"  Trade #{trade_id} (order_id={order_id}): {symbol} {side} {status} @ {timestamp}")

        # ====================================================================
        # HARD ASSERTIONS (Sprint 2 Part 2 #620 - run_id-based)
        # ====================================================================

        print(f"\n[Running Hard Assertions]")

        # Assertion 1: Order results in stream >= 1
        print(f"\n[1] Order results in stream >= 1 (filtered by run_id)")
        print(f"   Count: {len(order_results)} (expected: >= 1)")
        assert (
            len(order_results) >= 1
        ), f"Expected >= 1 order result with bot_id={run_id}, got {len(order_results)}"

        # Assertion 2: Trades in DB >= 1
        print(f"\n[2] Trades in DB >= 1 (filtered by run_id)")
        print(f"   Count: {len(trades)} (expected: >= 1)")
        assert (
            len(trades) >= 1
        ), f"Expected >= 1 trade with bot_id={run_id}, got {len(trades)}"

        # Mismatch Policy Check (Sprint 2 Part 2 #620)
        print(f"\n[3] Mismatch Policy Check (Budget: {mismatch_budget}, source: {budget_source})")
        mismatch = len(order_results) - len(trades)

        if mismatch > 0:
            # More order_results than trades (expected: async lag or rejected orders)
            print(f"   Missing Trades: {mismatch} (order_results > trades)")
            print(f"   Budget: {mismatch}/{mismatch_budget} ({'WITHIN' if mismatch <= mismatch_budget else 'EXCEEDED'})")

            # Governance Gate: Check against budget
            if mismatch > mismatch_budget:
                print(f"   ERROR: Mismatch exceeds budget!")
                print(f"   Likely causes: DB writer overloaded, excessive rejected orders, or stream corruption")
                assert False, (
                    f"Mismatch budget exceeded: {mismatch} missing trades (budget: {mismatch_budget}, source: {budget_source}). "
                    f"This indicates excessive async lag or data loss. "
                    f"Run ID: {run_id}"
                )
            else:
                print(f"   WARN: {mismatch} order_results missing from DB (within budget)")
                print(f"   Likely cause: Async DB writer lag or non-execution statuses")
                print(f"   Policy: Acceptable as long as within budget")
        elif mismatch < 0:
            # More trades than order_results (unexpected: possible duplicates)
            duplicate_count = abs(mismatch)
            print(f"   WARN: {duplicate_count} more trades than order_results")
            print(f"   Possible cause: DB duplicates or multiple executions")

            # Check for actual duplicates in DB
            order_ids_in_trades = [t[1] for t in trades if t[1]]  # Extract order_id from trades
            unique_order_ids = set(order_ids_in_trades)
            actual_duplicates = len(order_ids_in_trades) - len(unique_order_ids)

            if actual_duplicates > 0:
                print(f"   ERROR: Detected {actual_duplicates} duplicate order_ids in DB")
                assert False, (
                    f"DB integrity violation: {actual_duplicates} duplicate trades "
                    f"with bot_id={run_id}"
                )
            else:
                print(f"   No duplicates detected - may be legitimate multiple fills")
        else:
            # Perfect match
            print(f"   OK: order_results == trades ({len(order_results)})")

        print(f"\n" + "=" * 60)
        print("SUCCESS: ALL ASSERTIONS PASSED")
        print(f"Run ID: {run_id}")
        print(f"  Order Results: {len(order_results)}")
        print(f"  Trades in DB: {len(trades)}")
        print(f"  Mismatch: {mismatch:+d} (order_results - trades)")
        print(f"  Budget Status: {abs(mismatch)}/{mismatch_budget} ({'WITHIN' if abs(mismatch) <= mismatch_budget else 'EXCEEDED'})")
        print(f"  Budget Source: {budget_source}")
        print("=" * 60)


if __name__ == "__main__":
    """Run test standalone for debugging."""
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
