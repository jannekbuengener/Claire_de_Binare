"""
Unit tests for scripts/check_core_duplicates.py
Tests CI-Guard rules for core duplicates and secrets.py files.
"""

import subprocess
import sys
from pathlib import Path
import pytest
import tempfile
import shutil


def run_check_duplicates(test_dir: Path) -> tuple[int, str, str]:
    """Run check_core_duplicates.py in a test directory."""
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "check_core_duplicates.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=test_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_clean_repo_passes():
    """Test that a clean repository passes the check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create valid structure
        (test_dir / "core" / "domain").mkdir(parents=True)
        (test_dir / "core" / "domain" / "secrets.py").write_text("# allowed secrets.py")
        (test_dir / "services" / "signal").mkdir(parents=True)
        (test_dir / "services" / "signal" / "service.py").write_text("# service")

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 0, f"Expected success, got {returncode}\nStdout: {stdout}\nStderr: {stderr}"
        assert "CI-Guard PASSED" in stdout


def test_services_core_duplicate_fails():
    """Test that services/*/core/** directories are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create forbidden core duplicate
        core_dup_path = test_dir / "services" / "signal" / "core"
        core_dup_path.mkdir(parents=True)
        (core_dup_path / "utils.py").write_text("# duplicate core")

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 1, f"Expected failure, got {returncode}\nStdout: {stdout}"
        assert "CI-Guard FAILED" in stdout
        assert "FORBIDDEN: core duplicate" in stdout
        assert "services/signal/core" in stdout


def test_secrets_py_duplicate_fails():
    """Test that additional secrets.py files are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create allowed secrets.py
        (test_dir / "core" / "domain").mkdir(parents=True)
        (test_dir / "core" / "domain" / "secrets.py").write_text("# allowed")

        # Create forbidden secrets.py
        (test_dir / "services" / "risk").mkdir(parents=True)
        (test_dir / "services" / "risk" / "secrets.py").write_text("# forbidden")

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 1, f"Expected failure, got {returncode}\nStdout: {stdout}"
        assert "CI-Guard FAILED" in stdout
        assert "FORBIDDEN: secrets.py" in stdout
        assert "services/risk/secrets.py" in stdout


def test_multiple_violations_all_reported():
    """Test that all violations are reported together."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create multiple violations
        (test_dir / "services" / "signal" / "core").mkdir(parents=True)
        (test_dir / "services" / "risk" / "core").mkdir(parents=True)
        (test_dir / "services" / "risk" / "secrets.py").write_text("# bad")

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 1
        assert "CI-Guard FAILED" in stdout
        # Should report all 3 violations
        assert stdout.count("FORBIDDEN") == 3


def test_gitignore_and_pycache_ignored():
    """Test that .git and __pycache__ directories are ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create secrets.py in ignored locations
        (test_dir / ".git" / "hooks").mkdir(parents=True)
        (test_dir / ".git" / "hooks" / "secrets.py").write_text("# ignored")
        (test_dir / "__pycache__").mkdir()
        (test_dir / "__pycache__" / "secrets.py").write_text("# ignored")

        # Create allowed location
        (test_dir / "core" / "domain").mkdir(parents=True)
        (test_dir / "core" / "domain" / "secrets.py").write_text("# allowed")

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 0
        assert "CI-Guard PASSED" in stdout
