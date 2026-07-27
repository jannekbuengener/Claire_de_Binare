"""Redaction tests for the local CI status publisher."""

from __future__ import annotations

import pytest

from ci.publisher.redaction import redact_mapping, redact_text

pytestmark = pytest.mark.unit


def test_token_like_strings_are_redacted():
    text = "using ghp_abcdefghijklmnopqrstuvwxyz012345 and gho_ABCDEFGHIJKLMNOPQRSTUV"
    out = redact_text(text)
    assert "ghp_" not in out
    assert "gho_" not in out
    assert "[REDACTED]" in out


def test_authorization_headers_are_never_logged():
    text = "Authorization: Bearer ghs_abcdefghijklmnopqrstuvwxyz012345"
    out = redact_text(text)
    assert "ghs_" not in out
    assert "Bearer ghs_" not in out
    assert "[REDACTED]" in out


def test_github_api_errors_do_not_leak_credentials():
    payload = {
        "message": "Bad credentials",
        "authorization": "Bearer ghp_leakleakleakleakleak",
        "documentation_url": "https://docs.github.com",
    }
    out = redact_mapping(payload)
    assert out["authorization"] == "[REDACTED]"
    assert "ghp_" not in str(out)


def test_evidence_summaries_contain_no_secrets():
    summary = {
        "run_id": "abc12345",
        "commit_sha": "deadbeef",
        "token": "github_pat_should_not_appear",
        "description": "ok with token=github_pat_ABCDEFGH12345678",
    }
    out = redact_mapping(summary)
    assert out["token"] == "[REDACTED]"
    assert "github_pat_" not in out["description"]
