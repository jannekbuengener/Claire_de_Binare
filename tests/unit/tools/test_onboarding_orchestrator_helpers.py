from __future__ import annotations

from collections.abc import Iterator

import pytest

from tools import onboarding_orchestrator

pytestmark = pytest.mark.unit


def _iter_input(values: list[str]) -> Iterator[str]:
    return iter(values)


def test_get_setup_prompt_text_is_exact() -> None:
    assert onboarding_orchestrator.get_setup_prompt_text() == (
        "Möchtest du das Onboarding-Setup jetzt ausführen?\n\n" "1. Ja\n" "2. Abbruch"
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
