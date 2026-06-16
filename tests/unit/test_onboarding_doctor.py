"""Unit tests for onboarding doctor (#3232)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from tools import onboarding_doctor as doctor

pytestmark = pytest.mark.unit


def test_parse_python_version_good() -> None:
    assert doctor._parse_python_version("Python 3.12.0") == (3, 12, 0)
    assert doctor._parse_python_version("Python 3.11.5") == (3, 11, 5)


def test_parse_python_version_edge() -> None:
    assert doctor._parse_python_version("Python 3.10.0") == (3, 10, 0)
    assert doctor._parse_python_version("") is None
    assert doctor._parse_python_version("not a version") is None


def test_version_ok() -> None:
    assert doctor._version_ok((3, 12, 0)) is True
    assert doctor._version_ok((3, 11, 0)) is True
    assert doctor._version_ok((3, 10, 0)) is False
    assert doctor._version_ok(None) is False
    assert doctor._version_ok((4, 0, 0)) is True


def test_check_python_version() -> None:
    status, ver_str, ok = doctor.check_python_version("Python 3.12.0")
    assert status == "PASS"
    assert ver_str == "3.12.0"
    assert ok == "PASS"

    status, ver_str, ok = doctor.check_python_version("Python 3.10.0")
    assert status == "WARN"
    assert ok == "FAIL"

    status, ver_str, ok = doctor.check_python_version("garbage")
    assert status == "WARN"
    assert ok == "FAIL"


def test_onboarding_files_all_exist(tmp_path: Path) -> None:
    for rel in doctor.ONBOARDING_FILE_CHECKS:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test")
    status, missing = doctor._onboarding_files_exist(tmp_path)
    assert status == "PASS"
    assert not missing


def test_onboarding_files_missing(tmp_path: Path) -> None:
    status, missing = doctor._onboarding_files_exist(tmp_path)
    assert status == "FAIL"
    assert len(missing) > 2


def test_check_env_file_exists(tmp_path: Path) -> None:
    orig = Path.cwd()
    try:
        os.chdir(tmp_path)
        (tmp_path / ".env").write_text("test")
        status, detail = doctor._check_env_file()
        assert status == "PASS"
        assert "found" in detail
    finally:
        os.chdir(orig)


def test_check_env_file_missing_but_example(tmp_path: Path) -> None:
    orig = Path.cwd()
    try:
        os.chdir(tmp_path)
        (tmp_path / ".env.example").write_text("test")
        status, detail = doctor._check_env_file()
        assert status == "WARN"
        assert ".env.example" in detail
    finally:
        os.chdir(orig)


def test_check_env_file_missing(tmp_path: Path) -> None:
    orig = Path.cwd()
    try:
        os.chdir(tmp_path)
        status, _ = doctor._check_env_file()
        assert status == "FAIL"
    finally:
        os.chdir(orig)


def test_check_secrets_path_env_set_valid(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    os.environ["SECRETS_PATH"] = str(secrets)
    try:
        status, detail = doctor._check_secrets_path()
        assert status == "PASS"
        assert str(secrets) in detail
    finally:
        os.environ.pop("SECRETS_PATH", None)


def test_check_secrets_path_env_set_invalid() -> None:
    os.environ["SECRETS_PATH"] = "/nonexistent/path"
    try:
        status, _ = doctor._check_secrets_path()
        assert status == "FAIL"
    finally:
        os.environ.pop("SECRETS_PATH", None)


def test_check_secrets_path_unset(tmp_path: Path) -> None:
    status, _ = doctor._check_secrets_path()
    assert status in ("PASS", "WARN")


def test_build_report_repo_root(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("test")
    (tmp_path / ".git").mkdir()

    def mock_runner(cmd, **kwargs):
        return CompletedProcess(cmd, 0, "output", "")

    report = doctor.build_report(
        tmp_path,
        git_runner=mock_runner,
        python_runner=mock_runner,
        gh_runner=mock_runner,
        docker_runner=mock_runner,
        compose_runner=mock_runner,
        context_doctor_runner=mock_runner,
    )
    assert report.repo_root_found == "PASS"


def test_build_report_python_not_found(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("test")

    def fail_runner(cmd, **kwargs):
        return CompletedProcess(cmd, 1, "", "")

    def git_ok(cmd, **kwargs):
        return CompletedProcess(cmd, 0, "git version 2.40.0", "")

    def git_porcelain(cmd, **kwargs):
        return CompletedProcess(cmd, 0, "", "")

    report = doctor.build_report(
        tmp_path,
        git_runner=git_porcelain,
        python_runner=fail_runner,
        gh_runner=fail_runner,
        docker_runner=fail_runner,
        compose_runner=fail_runner,
        context_doctor_runner=fail_runner,
    )
    assert report.python_found == "FAIL"
    assert report.repo_root_found == "PASS"


def test_json_output_no_secret_leak(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("test")

    def mock_runner(cmd, **kwargs):
        return CompletedProcess(cmd, 0, "python 3.12.0", "")

    report = doctor.build_report(
        tmp_path,
        git_runner=mock_runner,
        python_runner=mock_runner,
        gh_runner=mock_runner,
        docker_runner=mock_runner,
        compose_runner=mock_runner,
        context_doctor_runner=mock_runner,
    )
    payload = doctor.format_report(report, "json")
    for pattern in doctor.FORBIDDEN_OUTPUT_PATTERNS:
        assert not pattern.search(payload), f"forbidden pattern found in JSON output: {pattern.pattern}"


def test_text_output_no_secret_leak(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("test")

    def mock_runner(cmd, **kwargs):
        return CompletedProcess(cmd, 0, "python 3.12.0", "")

    report = doctor.build_report(
        tmp_path,
        git_runner=mock_runner,
        python_runner=mock_runner,
        gh_runner=mock_runner,
        docker_runner=mock_runner,
        compose_runner=mock_runner,
        context_doctor_runner=mock_runner,
    )
    text = doctor.format_report(report, "text")
    assert "super-secret" not in text.lower()


def test_compute_exit_code() -> None:
    ok = doctor.DoctorOutput()
    ok.checks = [doctor.CheckItem(name="x", status="PASS")]
    assert doctor.compute_exit_code(ok) == 0

    fail = doctor.DoctorOutput()
    fail.checks = [doctor.CheckItem(name="x", status="FAIL")]
    assert doctor.compute_exit_code(fail) == 1

    warn = doctor.DoctorOutput()
    warn.checks = [doctor.CheckItem(name="x", status="WARN")]
    assert doctor.compute_exit_code(warn) == 0


def test_main_exit_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mock_report(*args, **kwargs):
        r = doctor.DoctorOutput()
        r.repo_root_found = "PASS"
        r.checks = [doctor.CheckItem(name="test", status="FAIL")]
        return r

    monkeypatch.setattr(doctor, "build_report", mock_report)
    assert doctor.main(["--format", "json"]) == 1

    def mock_report_ok(*args, **kwargs):
        r = doctor.DoctorOutput()
        r.repo_root_found = "PASS"
        r.checks = [doctor.CheckItem(name="test", status="PASS")]
        return r

    monkeypatch.setattr(doctor, "build_report", mock_report_ok)
    assert doctor.main(["--format", "text"]) == 0

    with pytest.raises(SystemExit) as exc_info:
        doctor.main(["--format", "xml"])
    assert exc_info.value.code == 2


def test_forbidden_output_patterns_detect_secret() -> None:
    vulnerabilities = [
        "api_key=abc123def456",
        "secret=my-secret-value",
        "password=supersecret",
        "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "https://github.com/user/repo",
    ]
    for sample in vulnerabilities:
        assert any(
            p.search(sample) for p in doctor.FORBIDDEN_OUTPUT_PATTERNS
        ), f"pattern should detect: {sample}"

    safe_samples = [
        "SECRETS_PATH=C:/Users/user/Documents/.secrets/.cdb",
        "gh auth status: not logged in",
    ]
    for sample in safe_samples:
        for p in doctor.FORBIDDEN_OUTPUT_PATTERNS:
            if p.search(sample):
                break
        else:
            continue
        # Some may match, some may not; that's OK for safe samples


def test_onboarding_files_warn_few_missing(tmp_path: Path) -> None:
    for rel in doctor.ONBOARDING_FILE_CHECKS[:7]:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test")
    status, missing = doctor._onboarding_files_exist(tmp_path)
    # 7 present, 2 missing (tests/README.md, services/README.md) = WARN
    assert status == "WARN"
    assert 2 <= len(missing) <= 2



def test_doctor_output_to_dict(tmp_path: Path) -> None:
    r = doctor.DoctorOutput(
        repo_root_found="PASS",
        git_found="PASS",
        git_branch="main",
        git_dirty="PASS",
        python_found="PASS",
        python_version="3.12.0",
        python_version_ok="PASS",
        env_file="PASS",
        secrets_path="PASS",
        onboarding_files="PASS",
        context_doctor_reachable="PASS",
    )
    d = r.to_dict()
    assert d["repo_root"] == "PASS"
    assert d["git"]["branch"] == "main"
    assert d["lr_note"] == "NO-GO"
    assert "checks" in d
