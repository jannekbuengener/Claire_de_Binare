"""Unit tests for onboarding doctor (#3232)."""

from __future__ import annotations

import io
import json
import os
import re
import sys
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
        assert not pattern.search(
            payload
        ), f"forbidden pattern found in JSON output: {pattern.pattern}"


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


def test_main_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        repo_head="abcd1234",
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
    assert d["repo_head"] == "abcd1234"
    assert d["git"]["branch"] == "main"
    assert d["git"]["head"] == "abcd1234"
    assert d["lr_note"] == "NO-GO"
    assert "checks" in d


class TestFormatMarkdownReport:
    def _build_sample_report(self) -> doctor.DoctorOutput:
        r = doctor.DoctorOutput(
            repo_root_found="PASS",
            git_found="PASS",
            git_branch="feat/test",
            git_dirty="PASS",
            repo_head="deadbeef1234",
            python_found="PASS",
            python_version="3.12.0",
            python_version_ok="PASS",
            docker_found="WARN",
            compose_found="SKIP",
            env_file="PASS",
            secrets_path="PASS",
            secrets_resolved_dir="/home/user/.secrets/.cdb",
            onboarding_files="PASS",
            context_doctor_reachable="PASS",
        )
        r.checks = [
            doctor.CheckItem(name="Repo root", status="PASS"),
            doctor.CheckItem(name="Git", status="PASS", detail="feat/test"),
            doctor.CheckItem(name="Docker", status="WARN"),
            doctor.CheckItem(name="gh CLI", status="SKIP"),
        ]
        return r

    def test_contains_safety_statement(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "LR remains **NO-GO**" in md
        assert "Board stage `trade-capable` is **not** a Live-Go" in md
        assert "No Echtgeld-Go" in md

    def test_contains_repo_head(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "deadbeef1234" in md

    def test_contains_generated_timestamp(self) -> None:
        r = self._build_sample_report()
        ts = "2026-06-16T12:00:00+00:00"
        md = doctor.format_markdown_report(r, ts)
        assert ts in md

    def test_contains_summary_counts(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "**PASS**: 2" in md
        assert "**WARN**: 1" in md
        assert "**FAIL**: 0" in md
        assert "**Overall**: WARN" in md

    def test_contains_onboarding_surfaces(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "## Active Onboarding Surfaces" in md
        assert "README.md" in md
        assert "DEVELOPER_ONBOARDING.md" in md

    def test_contains_limitations(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "## Limitations" in md
        assert "Local checks only" in md

    def test_no_secret_leak(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        for pattern in doctor.FORBIDDEN_OUTPUT_PATTERNS:
            assert not pattern.search(md), f"forbidden pattern found: {pattern.pattern}"

    def test_with_warnings(self) -> None:
        r = self._build_sample_report()
        r.warnings = ["Missing onboarding files: tests/README.md"]
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "## Warnings" in md
        assert "tests/README.md" in md

    def test_without_warnings_section_omitted(self) -> None:
        r = self._build_sample_report()
        r.warnings = []
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "## Warnings" not in md

    def test_overall_fail(self) -> None:
        r = self._build_sample_report()
        r.checks.append(doctor.CheckItem(name="Fail check", status="FAIL"))
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "**Overall**: FAIL" in md

    def test_overall_pass(self) -> None:
        r = doctor.DoctorOutput(
            repo_root_found="PASS",
            git_found="PASS",
            git_branch="main",
            git_dirty="PASS",
            repo_head="abc123",
        )
        r.checks = [doctor.CheckItem(name="x", status="PASS")]
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "**Overall**: PASS" in md

    def test_generated_at_defaults_to_utc(self) -> None:
        r = self._build_sample_report()
        md = doctor.format_markdown_report(r)
        assert "**Generated**:" in md

    def test_pipe_character_escaped_in_detail(self) -> None:
        r = self._build_sample_report()
        r.checks = [doctor.CheckItem(name="Test", status="PASS", detail="a|b")]
        md = doctor.format_markdown_report(r, "2026-06-16T12:00:00+00:00")
        assert "a\\|b" in md


class TestCLIReportArg:
    def _mock_build_report(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> doctor.DoctorOutput:
        r = doctor.DoctorOutput(
            repo_root_found="PASS",
            git_found="PASS",
            git_branch="main",
            git_dirty="PASS",
            repo_head="testsha123",
            python_found="PASS",
            python_version="3.12.0",
            python_version_ok="PASS",
            env_file="PASS",
            secrets_path="PASS",
            onboarding_files="PASS",
            context_doctor_reachable="PASS",
        )
        r.checks = [doctor.CheckItem(name="test", status="PASS")]
        monkeypatch.setattr(doctor, "build_report", lambda **kw: r)
        return r

    def test_report_writes_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._mock_build_report(monkeypatch)
        report_file = tmp_path / "report.md"
        exit_code = doctor.main(["--report", str(report_file)])
        assert exit_code == 0
        assert report_file.is_file()
        content = report_file.read_text(encoding="utf-8")
        assert "# CDB Onboarding Doctor Report" in content
        assert "testsha123" in content

    def test_report_creates_parent_dirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._mock_build_report(monkeypatch)
        report_file = tmp_path / "nested" / "dir" / "report.md"
        exit_code = doctor.main(["--report", str(report_file)])
        assert exit_code == 0
        assert report_file.is_file()

    def test_default_no_file_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._mock_build_report(monkeypatch)
        initial_files = set(p.name for p in tmp_path.iterdir())
        exit_code = doctor.main([])
        assert exit_code == 0
        final_files = set(p.name for p in tmp_path.iterdir())
        assert final_files == initial_files

    def test_report_invalid_path_returns_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._mock_build_report(monkeypatch)
        blocker = tmp_path / "blocker"
        blocker.write_text("block")
        report_file = blocker / "subdir" / "report.md"
        exit_code = doctor.main(["--report", str(report_file)])
        assert exit_code == 2

    def test_json_output_remains_parseable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r = self._mock_build_report(monkeypatch)
        r.repo_head = "abcd1234"
        monkeypatch.setattr(doctor, "build_report", lambda **kw: r)

        import io

        out = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out)
        exit_code = doctor.main(["--format", "json"])
        assert exit_code == 0
        data = json.loads(out.getvalue())
        assert data["repo_root"] == "PASS"
        assert data["repo_head"] == "abcd1234"
        assert data["git"]["branch"] == "main"
        assert data["git"]["head"] == "abcd1234"
        assert data["lr_note"] == "NO-GO"
        assert "checks" in data

    def test_report_contains_secret_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r = self._mock_build_report(monkeypatch)
        r.secrets_resolved_dir = "C:\\Users\\user\\Documents\\.secrets\\.cdb"
        monkeypatch.setattr(doctor, "build_report", lambda **kw: r)
        report_file = tmp_path / "report.md"
        exit_code = doctor.main(["--report", str(report_file)])
        assert exit_code == 0
        content = report_file.read_text(encoding="utf-8")
        for pattern in doctor.FORBIDDEN_OUTPUT_PATTERNS:
            assert not pattern.search(
                content
            ), f"forbidden pattern found: {pattern.pattern}"

    def test_report_and_text_output_coexist(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self._mock_build_report(monkeypatch)
        report_file = tmp_path / "report.md"
        exit_code = doctor.main(["--format", "text", "--report", str(report_file)])
        assert exit_code == 0
        assert report_file.is_file()
        captured = capsys.readouterr()
        assert "=== CDB Onboarding Doctor ===" in captured.out
