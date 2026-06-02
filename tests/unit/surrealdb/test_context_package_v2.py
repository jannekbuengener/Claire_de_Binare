"""Unit tests for context_package_v2.py — Context Package v2.

Issues:
    #2798 — [PHASE-2][SURREALDB][SLICE-2] Context Package v2
    Parent: #2778

Scope:
    Fixture-based unit tests. No DB. No MCP. No networking. No writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.surrealdb.context_package_v2 import (
    GUARDRAILS,
    SCHEMA_VERSION,
    ContextPackageV2Error,
    ContextPackageV2Request,
    build_context_package_v2,
)

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "surrealdb"
    / "context_package_v2"
    / "minimal_ingredients.json"
)

REQUIRED_FIELDS = (
    "schema_version",
    "package_id",
    "generated_at_or_as_of",
    "target_scope",
    "source_priority",
    "required_reads",
    "artifacts",
    "ranked_context",
    "evidence_links",
    "decision_replay_links",
    "redaction_summary",
    "limitations",
    "guardrails",
    "determinism",
)


def _sample_artifact(
    artifact_id: str = "docs/surrealdb/context-package-model-v1.md",
    artifact_type: str = "doc",
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "summary": "Baseline package model",
    }
    payload.update(extra)
    return payload


def _base_request(**overrides: Any) -> ContextPackageV2Request:
    defaults: dict[str, Any] = {
        "target_scope": "issue:2798",
        "artifacts": [_sample_artifact()],
        "generated_at_or_as_of": "2026-06-02T12:00:00+00:00",
    }
    defaults.update(overrides)
    return ContextPackageV2Request(**defaults)


@pytest.mark.unit
def test_v2_package_has_required_schema_fields() -> None:
    package = build_context_package_v2(_base_request())
    for field in REQUIRED_FIELDS:
        assert field in package, f"missing required field: {field}"
    assert package["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
def test_package_id_is_deterministic_for_equivalent_inputs() -> None:
    request = _base_request()
    first = build_context_package_v2(request)
    second = build_context_package_v2(request)
    assert first["package_id"] == second["package_id"]
    assert first["determinism"]["content_hash"] == second["determinism"]["content_hash"]


@pytest.mark.unit
def test_generated_at_or_as_of_does_not_change_package_id() -> None:
    base = _base_request(generated_at_or_as_of="2026-06-02T12:00:00+00:00")
    other = _base_request(generated_at_or_as_of="2026-06-03T08:15:00+00:00")
    assert build_context_package_v2(base)["package_id"] == build_context_package_v2(other)[
        "package_id"
    ]


@pytest.mark.unit
def test_artifact_ordering_is_stable() -> None:
    artifacts = [
        _sample_artifact("b-artifact", "doc"),
        _sample_artifact("a-artifact", "doc"),
    ]
    forward = build_context_package_v2(_base_request(artifacts=artifacts))
    reverse = build_context_package_v2(_base_request(artifacts=list(reversed(artifacts))))
    assert forward["package_id"] == reverse["package_id"]
    assert [item["artifact_id"] for item in forward["artifacts"]] == [
        "a-artifact",
        "b-artifact",
    ]


@pytest.mark.unit
def test_sensitive_fields_are_redacted_in_artifacts() -> None:
    package = build_context_package_v2(
        _base_request(
            artifacts=[
                _sample_artifact(
                    metadata={
                        "api_key": "sk-live-secret-value",
                        "password": "hunter2",
                        "token": "Bearer abc.def.ghi",
                    }
                )
            ]
        )
    )
    metadata = package["artifacts"][0]["metadata"]
    assert metadata["api_key"] == "[REDACTED]"
    assert metadata["password"] == "[REDACTED]"
    assert metadata["token"] == "[REDACTED]"


@pytest.mark.unit
def test_redaction_summary_contains_no_raw_secret_values() -> None:
    secret = "sk-live-secret-value"
    package = build_context_package_v2(
        _base_request(
            artifacts=[_sample_artifact(metadata={"api_key": secret})]
        )
    )
    serialized = json.dumps(package["redaction_summary"])
    assert secret not in serialized
    assert package["redaction_summary"]
    for entry in package["redaction_summary"]:
        assert "path" in entry
        assert "field" in entry
        assert "redaction_type" in entry


@pytest.mark.unit
def test_missing_ranked_and_replay_inputs_produce_limitations() -> None:
    package = build_context_package_v2(_base_request())
    assert "ranked_context_not_provided" in package["limitations"]
    assert "decision_replay_links_not_provided" in package["limitations"]
    assert "evidence_links_not_provided" in package["limitations"]
    assert package["ranked_context"] is None


@pytest.mark.unit
def test_refs_only_replay_links_add_limitation_not_fake_verification() -> None:
    package = build_context_package_v2(
        _base_request(
            decision_replay_links=[{"ref": "decision:123", "mode": "replay_by_decision_id"}]
        )
    )
    assert "decision_replay_links_refs_only" in package["limitations"]


@pytest.mark.unit
def test_guardrails_include_no_live_go_and_no_authorization() -> None:
    package = build_context_package_v2(_base_request())
    assert list(package["guardrails"]) == list(GUARDRAILS)
    joined = " ".join(package["guardrails"]).lower()
    assert "no-go" in joined
    assert "orientation" in joined
    assert "authorization" in joined


@pytest.mark.unit
def test_ranked_context_and_replay_links_integrate_when_provided() -> None:
    package = build_context_package_v2(
        _base_request(
            ranked_context={"schema_version": "hybrid-retrieval-ranking/v1", "results": []},
            evidence_links=[{"ref": "evidence:1", "content_hash": "abc123", "verified": True}],
            decision_replay_links=[
                {"replay_id": "replay:1", "content_hash": "def456", "mode": "replay_by_decision_id"}
            ],
        )
    )
    assert package["ranked_context"] is not None
    assert package["evidence_links"]
    assert package["decision_replay_links"]
    assert "ranked_context_not_provided" not in package["limitations"]
    assert "decision_replay_links_not_provided" not in package["limitations"]


@pytest.mark.unit
def test_empty_artifacts_fail_closed() -> None:
    with pytest.raises(ContextPackageV2Error, match="non-empty"):
        build_context_package_v2(_base_request(artifacts=[]))


@pytest.mark.unit
def test_tokenized_url_values_are_redacted() -> None:
    secret_url = "https://example.com/context?token=super-secret-value"
    package = build_context_package_v2(
        _base_request(
            artifacts=[_sample_artifact(source_url=secret_url)],
            evidence_links=[{"ref": secret_url}],
        )
    )
    serialized = json.dumps(package)
    assert "super-secret-value" not in serialized
    assert package["artifacts"][0]["source_url"] == "[REDACTED]"
    assert package["evidence_links"][0]["ref"] == "[REDACTED]"
    assert all(
        "super-secret-value" not in entry.get("path", "")
        for entry in package["redaction_summary"]
    )


@pytest.mark.unit
def test_link_secret_only_differences_do_not_change_package_id() -> None:
    package_a = build_context_package_v2(
        _base_request(
            evidence_links=[
                {"ref": "evidence:shared", "api_key": "sk-one"},
                {"ref": "evidence:other", "content_hash": "abc"},
            ],
        )
    )
    package_b = build_context_package_v2(
        _base_request(
            evidence_links=[
                {"ref": "evidence:shared", "api_key": "sk-two"},
                {"ref": "evidence:other", "content_hash": "abc"},
            ],
        )
    )
    assert package_a["package_id"] == package_b["package_id"]


@pytest.mark.unit
def test_private_rank_field_does_not_change_package_id() -> None:
    artifact_a = _sample_artifact("shared-artifact", _rank=1)
    artifact_b = _sample_artifact("shared-artifact", _rank=99)
    package_a = build_context_package_v2(_base_request(artifacts=[artifact_a]))
    package_b = build_context_package_v2(_base_request(artifacts=[artifact_b]))
    assert package_a["package_id"] == package_b["package_id"]


@pytest.mark.unit
def test_secret_only_differences_do_not_change_package_id_for_same_artifact() -> None:
    artifact_a = _sample_artifact("shared-artifact", metadata={"api_key": "sk-one"})
    artifact_b = _sample_artifact("shared-artifact", metadata={"api_key": "sk-two"})
    package_a = build_context_package_v2(_base_request(artifacts=[artifact_a]))
    package_b = build_context_package_v2(_base_request(artifacts=[artifact_b]))
    assert package_a["package_id"] == package_b["package_id"]


@pytest.mark.unit
def test_required_read_secret_only_differences_do_not_change_package_id() -> None:
    package_a = build_context_package_v2(
        _base_request(
            required_reads=[{"path": "AGENTS.md", "api_key": "sk-one"}],
        )
    )
    package_b = build_context_package_v2(
        _base_request(
            required_reads=[{"path": "AGENTS.md", "api_key": "sk-two"}],
        )
    )
    assert package_a["package_id"] == package_b["package_id"]


@pytest.mark.unit
def test_required_reads_are_redacted() -> None:
    secret = "sk-required-read-secret"
    package = build_context_package_v2(
        _base_request(
            required_reads=[{"path": "AGENTS.md", "api_key": secret}],
        )
    )
    assert secret not in json.dumps(package)
    assert package["required_reads"][0]["api_key"] == "[REDACTED]"


@pytest.mark.unit
def test_evidence_and_replay_links_are_redacted() -> None:
    secret = "Bearer abc.def.ghi"
    package = build_context_package_v2(
        _base_request(
            evidence_links=[{"ref": "evidence:1", "api_key": secret}],
            decision_replay_links=[
                {"ref": "decision:1", "token": "sk-live-secret-value"}
            ],
        )
    )
    serialized = json.dumps(package)
    assert secret not in serialized
    assert "sk-live-secret-value" not in serialized
    assert package["evidence_links"][0]["api_key"] == "[REDACTED]"
    assert package["decision_replay_links"][0]["token"] == "[REDACTED]"


@pytest.mark.unit
def test_fixture_minimal_ingredients_builds_package() -> None:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    package = build_context_package_v2(ContextPackageV2Request(**payload))
    assert package["package_id"].startswith("pkg_")
    assert package["determinism"]["artifact_count"] == len(payload["artifacts"])
