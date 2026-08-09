"""Contract tests for the Gemini branch of the AI Review Router."""

from __future__ import annotations

from pathlib import Path

import pytest

WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "ai-review-router.yml"
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_gemini_uses_live_confirmed_reviewer_model() -> None:
    workflow = _workflow_text()

    assert "gemini-3.1-pro-preview:generateContent" in workflow
    assert "gemini-1.5-pro" not in workflow
    assert "maxOutputTokens:4096" in workflow


def test_gemini_provider_errors_are_structured_and_fail_closed() -> None:
    workflow = _workflow_text()

    assert "http_status=$(curl" in workflow
    assert ".error.code" in workflow
    assert ".error.status" in workflow
    assert ".error.message" in workflow
    assert "Gemini provider error: HTTP" in workflow
    assert 'post_or_patch_comment "$comment_body"' in workflow
    assert "exit 1" in workflow


def test_gemini_empty_success_response_is_explicitly_failed() -> None:
    workflow = _workflow_text()

    assert "status=EMPTY_SUCCESS_RESPONSE" in workflow
    assert "message=no candidate content" in workflow


def test_gemini_incomplete_or_schema_invalid_response_is_failed() -> None:
    workflow = _workflow_text()

    assert ".candidates[0].finishReason" in workflow
    assert '!= "STOP"' in workflow
    assert "INVALID_OR_INCOMPLETE_REVIEW_RESPONSE" in workflow
    assert "finishReason=$finish_reason" in workflow
    assert "^Reviewer:[[:space:]]*GEMINI$" in workflow
    assert "^5\\. .+$" in workflow


def test_gemini_key_is_header_only_and_never_in_the_endpoint() -> None:
    workflow = _workflow_text()

    assert '"x-goog-api-key: $secret_value"' in workflow
    assert ":generateContent?key=" not in workflow


def test_missing_secret_and_review_verdict_paths_remain_fail_closed() -> None:
    workflow = _workflow_text()

    assert "missing secret $secret_name" in workflow
    assert 'if [ "$verdict" = "PASS" ]; then' in workflow
    assert 'verdict="FAIL"' in workflow
