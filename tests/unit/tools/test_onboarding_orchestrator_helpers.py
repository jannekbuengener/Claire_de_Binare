from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from tools import onboarding_orchestrator

pytestmark = pytest.mark.unit


def _iter_input(values: list[str]) -> Iterator[str]:
    return iter(values)


def test_get_setup_prompt_text_is_exact() -> None:
    assert onboarding_orchestrator.get_setup_prompt_text() == (
        "Moechtest du das Onboarding-Setup jetzt ausfuehren?\n\n" "1. Ja\n" "2. Abbruch"
    )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1", onboarding_orchestrator.SETUP_APPROVED),
        ("ja", onboarding_orchestrator.SETUP_APPROVED),
        (" yes ", onboarding_orchestrator.SETUP_APPROVED),
        ("2", onboarding_orchestrator.SETUP_ABORTED),
        ("nein", onboarding_orchestrator.SETUP_ABORTED),
        ("NO", onboarding_orchestrator.SETUP_ABORTED),
        ("abbruch", onboarding_orchestrator.SETUP_ABORTED),
        ("cancel", onboarding_orchestrator.SETUP_ABORTED),
    ],
)
def test_normalize_setup_prompt_input_maps_expected_values(
    raw_value: str, expected: str
) -> None:
    assert onboarding_orchestrator.normalize_setup_prompt_input(raw_value) == expected


@pytest.mark.parametrize("raw_value", ["", "0", "maybe", "setup-plan"])
def test_normalize_setup_prompt_input_rejects_invalid_values(raw_value: str) -> None:
    assert onboarding_orchestrator.normalize_setup_prompt_input(raw_value) is None


def test_prompt_for_setup_confirmation_repeats_after_invalid_input() -> None:
    responses = _iter_input(["vielleicht", "yes"])
    prompts: list[str] = []

    result = onboarding_orchestrator.prompt_for_setup_confirmation(
        input_fn=lambda _prompt: next(responses),
        output_fn=prompts.append,
    )

    assert result == onboarding_orchestrator.SETUP_APPROVED
    assert prompts == [
        onboarding_orchestrator.get_setup_prompt_text(),
        onboarding_orchestrator.get_setup_prompt_text(),
    ]


def test_prompt_for_setup_confirmation_accepts_abort_synonym() -> None:
    prompts: list[str] = []

    result = onboarding_orchestrator.prompt_for_setup_confirmation(
        input_fn=lambda _prompt: "abbruch",
        output_fn=prompts.append,
    )

    assert result == onboarding_orchestrator.SETUP_ABORTED
    assert prompts == [onboarding_orchestrator.get_setup_prompt_text()]


def _prepare_root(tmp_path: Path) -> Path:
    for rel_path in onboarding_orchestrator.CANONICAL_BOOTLOADER_FILES:
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    scenario_path = tmp_path / onboarding_orchestrator.SCENARIO_FILE
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    scenario_path.write_text(
        "\n".join(onboarding_orchestrator.REQUIRED_SCENARIO_TERMS),
        encoding="utf-8",
    )

    lr_path = tmp_path / "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"
    lr_path.parent.mkdir(parents=True, exist_ok=True)
    lr_path.write_text("NO-GO", encoding="utf-8")

    (tmp_path / ".env.example").write_text("EXAMPLE=1\n", encoding="utf-8")
    return tmp_path


def _runner_ok(*_args, **_kwargs) -> CompletedProcess:
    return CompletedProcess(
        [],
        0,
        '{"warnings": [], "check_scope": "partial_context_onboarding", "skipped_checks": ["mcp_server", "surrealdb_schema"]}',
        "",
    )


def test_build_verdict_default_mode_enters_confirmation_pending(tmp_path: Path) -> None:
    root = _prepare_root(tmp_path)
    report = onboarding_orchestrator.build_verdict(
        root,
        mode="default",
        doctor_runner=_runner_ok,
        context_doctor_runner=_runner_ok,
    )

    assert report.status == "SETUP_WARN"
    assert report.state == onboarding_orchestrator.SETUP_CONFIRMATION_PENDING
    assert report.requires_explicit_setup_go is True
    assert report.setup_prompt_visible is True
    assert report.allowed_next_actions == [
        onboarding_orchestrator.ACTION_APPROVE_SETUP,
        onboarding_orchestrator.ACTION_ABORT,
    ]


def test_build_verdict_check_only_mode_hides_prompt(tmp_path: Path) -> None:
    root = _prepare_root(tmp_path)
    report = onboarding_orchestrator.build_verdict(
        root,
        mode="check-only",
        doctor_runner=_runner_ok,
        context_doctor_runner=_runner_ok,
    )

    assert report.status == "SETUP_WARN"
    assert report.state == onboarding_orchestrator.SETUP_REQUIRED
    assert report.requires_explicit_setup_go is True
    assert report.setup_prompt_visible is False
    assert report.allowed_next_actions == [
        onboarding_orchestrator.ACTION_REQUEST_SETUP_GO,
        onboarding_orchestrator.ACTION_ABORT,
    ]


def test_format_output_check_only_does_not_show_setup_prompt(tmp_path: Path) -> None:
    root = _prepare_root(tmp_path)
    report = onboarding_orchestrator.build_verdict(
        root,
        mode="check-only",
        doctor_runner=_runner_ok,
        context_doctor_runner=_runner_ok,
    )

    output = onboarding_orchestrator.format_output(report, "text")
    assert "Moechtest du das Onboarding-Setup jetzt ausfuehren?" not in output
    assert "check-only mode is dry-run only." in output
    assert "Would only run setup after explicit setup GO." in output
