from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.evidence_harvester.boot import (
    BOOT_READINESS_SCHEMA,
    BootReadinessError,
    main,
)


@pytest.mark.unit
def test_default_command_is_status(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "status"
    assert payload["schema_version"] == BOOT_READINESS_SCHEMA


@pytest.mark.unit
def test_status_reports_full_readiness(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["status", "--pretty", "--evaluated-at-utc", "2026-06-19T16:00:00Z"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "status"
    assert payload["verdict"]["verdict"] in ("PASS", "WARN", "FAIL")

    flags = [
        "repo_root_valid",
        "harvester_modules_importable",
        "artifact_dirs_available",
        "scheduler_script_present",
        "command_plan_available",
        "safety_boundaries_ok",
    ]
    for flag in flags:
        assert flag in payload, f"Missing flag: {flag}"
        assert isinstance(payload[flag], bool), f"{flag} must be bool"

    assert payload["verdict"]["total_checks"] >= 1
    assert len(payload["findings"]) >= 1


@pytest.mark.unit
def test_status_readiness_flags_expected_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["repo_root_valid"] is True
    assert payload["harvester_modules_importable"] is True
    assert payload["command_plan_available"] is True


@pytest.mark.unit
def test_preflight_checks_modules_and_paths(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["preflight", "--pretty", "--evaluated-at-utc", "2026-06-19T16:00:00Z"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "preflight"

    b001_findings = [f for f in payload["findings"] if f["check_id"] == "B001"]
    assert len(b001_findings) >= 1

    b002_findings = [f for f in payload["findings"] if f["check_id"] == "B002"]
    assert len(b002_findings) >= 1


@pytest.mark.unit
def test_preflight_includes_status_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["preflight", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_root_valid"] is True
    assert payload["harvester_modules_importable"] is True


@pytest.mark.unit
def test_install_plan_prints_plan_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["install-plan", "--pretty", "--evaluated-at-utc", "2026-06-19T16:00:00Z"]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)

    assert plan.get("mode") == "install-plan"
    assert plan.get("plan_only") is True
    assert len(plan.get("available_steps", [])) >= 1
    for step in plan.get("available_steps", []):
        assert "step" in step
        assert "command" in step


@pytest.mark.unit
def test_install_plan_steps_require_go(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["install-plan", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)

    for step in plan.get("available_steps", []):
        if "install-windows-task" in step["step"]:
            assert step.get("requires_go") != ""
        if "start-docker-stack" in step["step"]:
            assert step.get("requires_go") != ""


@pytest.mark.unit
def test_render_operator_handoff_renders_markdown(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "render-operator-handoff",
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# Evidence Harvester Boot" in output
    assert "## Operator Steps to Enable Reboot-Resilient Always-On Mode" in output
    assert "python -m tools.evidence_harvester.boot status" in output
    assert "## Safety" in output


@pytest.mark.unit
def test_render_operator_handoff_includes_install_instructions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "render-operator-handoff",
            "--pretty",
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Windows Task Scheduler" in output
    assert "Docker-based background runner" in output
    assert "Infra-Mutation-Gate" in output
    assert "3733" in output
    assert "No LR-Go" in output


@pytest.mark.unit
def test_status_modules_importable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["harvester_modules_importable"] is True


@pytest.mark.unit
def test_status_docker_detected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["docker_available"], bool)
    docker_finding = [f for f in payload["findings"] if f["check_id"] == "B005"]
    assert len(docker_finding) >= 1
    msg = docker_finding[-1]["message"]
    assert "Not started" in msg or "Docker not found" in msg


@pytest.mark.unit
def test_status_findings_have_no_docker_start(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)

    for finding in payload["findings"]:
        msg = finding["message"].lower()
        assert (
            "docker start" not in msg
        ), f"Finding {finding['check_id']} mentions 'docker start': {msg}"


@pytest.mark.unit
def test_status_artifact_dirs_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["artifact_dirs_available"], bool)


@pytest.mark.unit
def test_status_scheduler_script_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["scheduler_script_present"], bool)


@pytest.mark.unit
def test_status_safety_boundaries_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["safety_boundaries_ok"], bool)


@pytest.mark.unit
def test_status_command_plan_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command_plan_available"] is True


@pytest.mark.unit
def test_status_repo_root_valid(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--evaluated-at-utc", "2026-06-19T16:00:00Z"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_root_valid"] is True


@pytest.mark.unit
def test_status_rejects_unknown_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["status", "--unknown-flag"])


@pytest.mark.unit
def test_json_output_writes_file(tmp_path: Path) -> None:
    json_path = tmp_path / "boot_readiness.json"
    exit_code = main(
        [
            "status",
            "--json-output",
            str(json_path),
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )

    assert exit_code == 0
    assert json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "status"
    assert payload["schema_version"] == BOOT_READINESS_SCHEMA


@pytest.mark.unit
def test_markdown_output_writes_file(tmp_path: Path) -> None:
    md_path = tmp_path / "boot_readiness.md"
    exit_code = main(
        [
            "status",
            "--markdown-output",
            str(md_path),
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )

    assert exit_code == 0
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "# Evidence Harvester Boot Readiness Report" in content
    assert "## Readiness Flags" in content
    assert "## Findings" in content
    assert "## Safety" in content
    assert "No LR-Go" in content


@pytest.mark.unit
def test_safety_emitted_for_all_modes(capsys: pytest.CaptureFixture[str]) -> None:
    for mode in ("status", "preflight"):
        capsys.readouterr()
        exit_code = main(
            [mode, "--pretty", "--evaluated-at-utc", "2026-06-19T16:00:00Z"]
        )
        assert exit_code == 0
        output = capsys.readouterr().out
        assert "safety" in output.lower() or "No LR-Go" in output


@pytest.mark.unit
def test_main_reads_sys_argv_when_called_with_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    import sys

    saved_argv = sys.argv
    try:
        sys.argv = [
            "boot.py",
            "status",
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
        exit_code = main()
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["mode"] == "status"
    finally:
        sys.argv = saved_argv
