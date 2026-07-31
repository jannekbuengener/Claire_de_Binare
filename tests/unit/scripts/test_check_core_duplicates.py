"""
Unit tests for scripts/check_core_duplicates.py
Tests CI-Guard rules for core duplicates, secrets.py files, and script clones.

test_id: tc_check_core_duplicates_script_surface
test_type: Bauteil-Test / Schutz-Test
cdb_area: scripts
rule_ref: scripts-vs-infrastructure exact clone guard (#4125)
issue_ref: 4125
security_relevant: false
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import tempfile

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "check_core_duplicates.py"
)


def run_check_duplicates(test_dir: Path) -> tuple[int, str, str]:
    """Run check_core_duplicates.py in a test directory."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=test_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _git_init_commit(test_dir: Path, paths: list[str]) -> None:
    subprocess.run(["git", "init"], cwd=test_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=test_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=test_dir,
        check=True,
        capture_output=True,
    )
    if paths:
        subprocess.run(
            ["git", "add", "--"] + paths,
            cwd=test_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "fixture"],
            cwd=test_dir,
            check=True,
            capture_output=True,
        )


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

        assert (
            returncode == 0
        ), f"Expected success, got {returncode}\nStdout: {stdout}\nStderr: {stderr}"
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


def test_identical_script_pair_fails():
    """Identical tracked scripts under both owner surfaces must fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        body = "print('same implementation')\n"
        scripts_file = test_dir / "scripts" / "helper.py"
        infra_file = test_dir / "infrastructure" / "scripts" / "helper.py"
        scripts_file.parent.mkdir(parents=True)
        infra_file.parent.mkdir(parents=True)
        scripts_file.write_text(body)
        infra_file.write_text(body)
        _git_init_commit(
            test_dir,
            ["scripts/helper.py", "infrastructure/scripts/helper.py"],
        )

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 1, f"Expected failure, got {returncode}\nStdout: {stdout}"
        assert "identical script implementation" in stdout
        assert "scripts/helper.py" in stdout
        assert "infrastructure/scripts/helper.py" in stdout


def test_same_name_divergent_content_passes():
    """Same relative name with different content is not an exact-clone violation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        scripts_file = test_dir / "scripts" / "helper.py"
        infra_file = test_dir / "infrastructure" / "scripts" / "helper.py"
        scripts_file.parent.mkdir(parents=True)
        infra_file.parent.mkdir(parents=True)
        scripts_file.write_text("print('owner')\n")
        infra_file.write_text("print('different infra helper')\n")
        _git_init_commit(
            test_dir,
            ["scripts/helper.py", "infrastructure/scripts/helper.py"],
        )

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 0, f"Expected success, got {returncode}\nStdout: {stdout}"
        assert "CI-Guard PASSED" in stdout


def test_explicit_wrapper_accepted():
    """Explicit CDB_SCRIPT_WRAPPER marker exempts a twin path from Rule 3."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        body = "# CDB_SCRIPT_WRAPPER -> scripts/helper.py\nprint('same')\n"
        scripts_file = test_dir / "scripts" / "helper.py"
        infra_file = test_dir / "infrastructure" / "scripts" / "helper.py"
        scripts_file.parent.mkdir(parents=True)
        infra_file.parent.mkdir(parents=True)
        scripts_file.write_text(body)
        infra_file.write_text(body)
        _git_init_commit(
            test_dir,
            ["scripts/helper.py", "infrastructure/scripts/helper.py"],
        )

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 0, f"Expected success, got {returncode}\nStdout: {stdout}"
        assert "CI-Guard PASSED" in stdout


def test_untracked_identical_pair_ignored():
    """Untracked identical twins must not trip the git-tracked Rule 3 guard."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "scripts").mkdir(parents=True)
        (test_dir / "infrastructure" / "scripts").mkdir(parents=True)
        # Seed a tracked unrelated file so the repo has a commit.
        tracked = test_dir / "scripts" / "readme_note.txt"
        tracked.write_text("tracked only\n")
        _git_init_commit(test_dir, ["scripts/readme_note.txt"])

        body = "print('untracked twin')\n"
        (test_dir / "scripts" / "helper.py").write_text(body)
        (test_dir / "infrastructure" / "scripts" / "helper.py").write_text(body)

        returncode, stdout, stderr = run_check_duplicates(test_dir)

        assert returncode == 0, f"Expected success, got {returncode}\nStdout: {stdout}"
        assert "CI-Guard PASSED" in stdout
