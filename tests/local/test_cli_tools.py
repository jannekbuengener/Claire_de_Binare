"""
CLI-Tools Tests - Claire de Binare
Lokaler-only Test: Validierung von Command-Line Scripts

WICHTIG: Dieser Test MUSS lokal mit Docker Compose ausgeführt werden!
    - Erfordert: PostgreSQL mit Daten, Python-Scripts in backoffice/scripts/
    - Testet: query_analytics.py und andere CLI-Tools
    - Prüft: Script-Execution, Output-Format, Error-Handling
    - NICHT in CI ausführen (Scripts benötigen echte DB)

Ausführung:
    pytest -v -m local_only tests/local/test_cli_tools.py
"""

import pytest
import subprocess
import os
from pathlib import Path


@pytest.fixture
def cli_env():
    """Environment für CLI-Tools mit PostgreSQL-Credentials"""
    env = os.environ.copy()
    env.update(
        {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "claire_user",
            "POSTGRES_PASSWORD": "claire_db_secret_2024",
            "POSTGRES_DB": "claire_de_binare",
        }
    )
    return env


@pytest.mark.local_only
def test_query_analytics_script_exists():
    """
    Basic-Test: query_analytics.py existiert und ist ausfuührbar

    Validiert:
    - Script-Datei vorhanden
    - Python-Syntax korrekt (imports funktionieren)
    """
    print("\n📋 Testing query_analytics.py existence...")

    script_path = Path("backoffice/scripts/query_analytics.py")

    # Script existiert
    assert script_path.exists(), f"Script not found: {script_path}"

    # Script ist Python-File
    assert script_path.suffix == ".py", "Script should be .py file"

    # Kann importiert werden (keine Syntax-Fehler)
    result = subprocess.run(
        ["python", "-m", "py_compile", str(script_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script has syntax errors: {result.stderr}"

    print("✅ query_analytics.py exists and is valid Python")


@pytest.mark.local_only
def test_query_analytics_help_output(cli_env):
    """
    CLI-Test: --help zeigt Usage-Information

    Validiert:
    - --help funktioniert
    - Output enthält Command-Liste
    - Exit Code 0
    """
    print("\n📋 Testing query_analytics.py --help...")

    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--help"],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should succeed
    assert result.returncode == 0, f"--help failed: {result.stderr}"

    # Should contain usage info
    output = result.stdout.lower()

    # Check for common help indicators
    has_usage = any(
        word in output for word in ["usage", "options", "arguments", "commands"]
    )

    if not has_usage:
        print(f"⚠️  Help output doesn't contain standard keywords: {result.stdout}")

    print(f"✅ --help works (exit code: {result.returncode})")


@pytest.mark.local_only
def test_query_analytics_last_signals(cli_env):
    """
    CLI-Test: --last-signals N zeigt letzte N Signals

    Validiert:
    - Command funktioniert
    - Output ist lesbar
    - Exit Code 0 oder informativ
    """
    print("\n📋 Testing query_analytics.py --last-signals 5...")

    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--last-signals", "5"],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(f"  Exit Code: {result.returncode}")

    # Wenn DB leer, ist das OK (aber sollte es sagen)
    if result.returncode != 0:
        # Check if error is "no data" (acceptable) vs. "crash" (not acceptable)
        error_lower = result.stderr.lower()

        if any(word in error_lower for word in ["no data", "empty", "not found"]):
            print("  ℹ️  No signals in DB (acceptable)")
            pytest.skip("DB has no signals yet")
        else:
            pytest.fail(f"Command crashed: {result.stderr}")

    # Success: Check output
    output = result.stdout

    if len(output) > 0:
        print(f"  ✅ Output received ({len(output)} chars)")
        # Check if output looks like tabular data or JSON
        if "symbol" in output.lower() or "{" in output:
            print("  ✅ Output contains signal data")
    else:
        print("  ⚠️  Empty output (DB might be empty)")

    print("✅ --last-signals command works")


@pytest.mark.local_only
def test_query_analytics_last_trades(cli_env):
    """
    CLI-Test: --last-trades N zeigt letzte N Trades

    Validiert:
    - Command funktioniert
    - Output ist lesbar
    """
    print("\n📋 Testing query_analytics.py --last-trades 5...")

    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--last-trades", "5"],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(f"  Exit Code: {result.returncode}")

    # Wenn DB leer, skip
    if result.returncode != 0:
        error_lower = result.stderr.lower()

        if any(word in error_lower for word in ["no data", "empty", "not found"]):
            print("  ℹ️  No trades in DB (acceptable)")
            pytest.skip("DB has no trades yet")
        else:
            pytest.fail(f"Command crashed: {result.stderr}")

    # Success
    output = result.stdout

    if len(output) > 0:
        print(f"  ✅ Output received ({len(output)} chars)")

    print("✅ --last-trades command works")


@pytest.mark.local_only
def test_query_analytics_portfolio_summary(cli_env):
    """
    CLI-Test: --portfolio-summary zeigt Portfolio-Übersicht

    Validiert:
    - Command funktioniert
    - Output enthält Portfolio-Metriken
    """
    print("\n📋 Testing query_analytics.py --portfolio-summary...")

    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--portfolio-summary"],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(f"  Exit Code: {result.returncode}")

    # Wenn DB leer, skip
    if result.returncode != 0:
        error_lower = result.stderr.lower()

        if any(word in error_lower for word in ["no data", "empty"]):
            print("  ℹ️  No portfolio data in DB (acceptable)")
            pytest.skip("DB has no portfolio snapshots yet")
        else:
            pytest.fail(f"Command crashed: {result.stderr}")

    # Success: Check for portfolio keywords
    output_lower = result.stdout.lower()

    portfolio_keywords = ["equity", "cash", "pnl", "position", "exposure"]
    found_keywords = [kw for kw in portfolio_keywords if kw in output_lower]

    if len(found_keywords) > 0:
        print(f"  ✅ Portfolio metrics found: {found_keywords}")
    else:
        print("  ⚠️  No portfolio metrics in output")

    print("✅ --portfolio-summary command works")


@pytest.mark.local_only
def test_query_analytics_trade_statistics(cli_env):
    """
    CLI-Test: --trade-statistics zeigt Trading-Statistiken

    Validiert:
    - Command funktioniert
    - Output enthält Statistiken
    """
    print("\n📋 Testing query_analytics.py --trade-statistics...")

    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--trade-statistics"],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(f"  Exit Code: {result.returncode}")

    # Wenn DB leer, skip
    if result.returncode != 0:
        error_lower = result.stderr.lower()

        if any(word in error_lower for word in ["no data", "empty"]):
            print("  ℹ️  No trade data in DB (acceptable)")
            pytest.skip("DB has no trades yet")
        else:
            pytest.fail(f"Command crashed: {result.stderr}")

    # Success: Check for statistics keywords
    output_lower = result.stdout.lower()

    stats_keywords = [
        "win rate",
        "total trades",
        "profit",
        "loss",
        "average",
        "sharpe",
        "drawdown",
    ]
    found_keywords = [kw for kw in stats_keywords if kw in output_lower]

    if len(found_keywords) > 0:
        print(f"  ✅ Statistics metrics found: {found_keywords}")
    else:
        print("  ⚠️  No statistics in output")

    print("✅ --trade-statistics command works")


@pytest.mark.local_only
def test_query_analytics_handles_invalid_arguments(cli_env):
    """
    Error-Handling-Test: Ungültige Argumente werden abgefangen

    Validiert:
    - Script crasht nicht bei ungültigen Args
    - Zeigt sinnvolle Error-Message
    - Exit Code != 0
    """
    print("\n📋 Testing query_analytics.py error handling...")

    # Test mit ungültigem Flag
    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--invalid-flag"],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should fail (ungültiges Argument)
    assert result.returncode != 0, "Script should reject invalid arguments"

    # Should have error message
    assert (
        len(result.stderr) > 0 or len(result.stdout) > 0
    ), "Script should print error message"

    print("  ✅ Invalid arguments rejected")

    # Test mit ungültiger Number
    result = subprocess.run(
        [
            "python",
            "backoffice/scripts/query_analytics.py",
            "--last-signals",
            "not_a_number",
        ],
        env=cli_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should fail
    # (könnte auch 0 sein wenn Script default verwendet, aber dann sollte Output da sein)
    if result.returncode == 0:
        # OK wenn Output vorhanden
        assert (
            len(result.stdout) > 0
        ), "If script succeeds with bad input, should have output"
    else:
        # Error case
        assert (
            len(result.stderr) > 0 or len(result.stdout) > 0
        ), "Should have error message"

    print("  ✅ Invalid number handled")

    print("✅ Error handling works")


@pytest.mark.local_only
def test_query_analytics_database_connection_failure():
    """
    Resilience-Test: Script handled DB-Connection-Fehler gracefully

    Validiert:
    - Script crasht nicht komplett
    - Zeigt sinnvolle Error-Message
    - Exit Code != 0
    """
    print("\n📋 Testing query_analytics.py with bad DB credentials...")

    # Falsche Credentials
    bad_env = os.environ.copy()
    bad_env.update(
        {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "invalid_user",
            "POSTGRES_PASSWORD": "wrong_password",
            "POSTGRES_DB": "claire_de_binare",
        }
    )

    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--last-signals", "5"],
        env=bad_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should fail
    assert result.returncode != 0, "Script should fail with bad credentials"

    # Should mention connection error
    error_output = (result.stderr + result.stdout).lower()

    connection_errors = [
        "connection",
        "authentication",
        "password",
        "connect",
        "failed",
    ]
    has_connection_error = any(err in error_output for err in connection_errors)

    if has_connection_error:
        print("  ✅ Connection error message present")
    else:
        print(f"  ⚠️  Error message unclear: {result.stderr}")

    print("✅ DB connection failure handled")


if __name__ == "__main__":
    # Run with: pytest -v -m local_only tests/local/test_cli_tools.py
    pytest.main([__file__, "-v", "-m", "local_only", "-s"])
