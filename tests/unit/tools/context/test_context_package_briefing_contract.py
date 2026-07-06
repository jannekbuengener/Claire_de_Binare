"""Context Package / Agent Briefing contract tests (#3775).

Refs #3771. Consolidates fail-closed contracts for context.package,
context.briefing / cdb_context_briefing, Context Package v2 builder,
and validate_context_package. Covers required reads, stop conditions,
guardrails, limitations, redaction, LOW-trust degradation, and
deterministic fixture outputs. In-memory/fixture only — no live SurrealDB.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tools.context.validate_context_package import validate_package
from tools.mcp.context_bridge import (
    READINESS_MINIMUM_READS,
    cdb_context_briefing_handler,
    context_briefing_handler,
    context_package_handler,
    create_bridge,
)
from tools.surrealdb.context_package_v2 import (
    GUARDRAILS as PACKAGE_V2_GUARDRAILS,
    ContextPackageV2Request,
    build_context_package_v2,
)
from tools.surrealdb.context_required_reads import MINIMUM_READS as RESOLVER_MINIMUM_READS
from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_V2_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "surrealdb" / "context_package_v2" / "minimal_ingredients.json"
)

BRIEFING_OK_TOP_LEVEL = frozenset({"tool", "status", "briefing"})
CDB_BRIEFING_TOOL = "cdb_context_briefing"
CONTEXT_BRIEFING_TOOL = "context.briefing"

BRIEFING_ENVELOPE_REQUIRED = frozenset(
    {
        "briefing_id",
        "scope_summary",
        "human_go_required",
        "guardrails",
        "stop_conditions",
        "required_reads",
        "operator_trust_level",
        "trust_limitations",
        "approval_semantics",
    }
)

PACKAGE_HANDLER_OK_TOP = frozenset({"tool", "status", "package"})
PACKAGE_HANDLER_ERROR_TOP = frozenset({"tool", "status", "error"})
PACKAGE_HANDLER_PACKAGE_FIELDS = frozenset(
    {
        "format",
        "items",
        "package_id",
        "warnings",
        "missing_context",
        "stop_conditions",
        "source_refs",
        "created_at",
    }
)

BRIEFING_BASELINE_STOP_PREFIXES = ("S1:", "S3:", "S10:")
BRIEFING_BASELINE_GUARDRAILS = (
    "Briefing is context, not authorisation.",
    "No Runtime write.",
    "No MCP live action.",
    "No DB/migration write.",
    "No Trading/Risk/Execution decision.",
    "No Live/Echtgeld Go.",
    "LR remains NO-GO (SSOT: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md).",
)

_VALID_RECORD = {
    "record_id": "rec_contract_001",
    "record_type": "doc_record",
    "repo": "Claire_de_Binare",
    "source_path": "docs/example.md",
    "source_commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492",
    "source_hash": "abc123def456",
    "observed_at": "2026-06-17T12:00:00Z",
    "confidence": "high",
    "supersedes": None,
    "tags": ["contract"],
    "summary": "Contract test record",
    "evidence_refs": [{"ref": "docs/example.md", "source": "repo"}],
}

_VALID_CONTEXT_PACKAGE = {
    "package": {
        "package_id": "cdb-context-package-contract-001",
        "package_type": "context_package",
        "created_at": "2026-06-17T12:00:00Z",
        "source_commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492",
        "source_repo": "Claire_de_Binare",
        "records": [_VALID_RECORD],
    },
    "meta": {
        "version": "1.0",
        "validator_ref": "tools/context/validate_context_package.py",
        "schema_ref": "tools/context/schemas/context_package.schema.json",
        "safety_boundaries": {
            "lr_status": "NO-GO",
            "board_stage_is_live_go": False,
            "real_money_go": False,
            "productive_db_writes_allowed": False,
            "secrets_in_outputs_allowed": False,
            "trading_state_ingestion_allowed": False,
        },
    },
}

_SECRET_FIXTURE = "sk-contract-redaction-negative-control"


def _briefing_kwargs(**extra: object) -> dict[str, Any]:
    base: dict[str, Any] = {
        "task_id": "contract-3775",
        "task_scope": "RED_ONLY issue #3775 Context Package / Agent Briefing contract tests",
        "target_issue": "#3775",
        "requested_depth": "standard",
        "operation_mode": "read_only",
    }
    base.update(extra)
    return base


def _briefing(**extra: object) -> dict[str, Any]:
    result = context_briefing_handler(**_briefing_kwargs(**extra))
    assert result["status"] == "ok", result
    return result["briefing"]


def _sample_v2_artifact(**extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "artifact_id": "docs/surrealdb/context-package-model-v1.md",
        "artifact_type": "doc",
        "summary": "Contract baseline artifact",
    }
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# context_package_schema_fail_closed
# ---------------------------------------------------------------------------


def test_context_package_schema_fail_closed_rejects_invalid_record_type() -> None:
    """Invalid Context Package JSON schema violations fail closed with BLOCKED."""
    pkg = json.loads(json.dumps(_VALID_CONTEXT_PACKAGE))
    pkg["package"]["records"][0]["record_type"] = "order_record"
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    assert report["exit_code"] == 1
    assert report["error_count"] >= 1
    codes = {e["code"] for e in report["errors"]}
    assert "invalid_enum" in codes


def test_context_package_schema_fail_closed_rejects_empty_source_hash() -> None:
    """Missing source_hash on records is blocked fail-closed."""
    pkg = json.loads(json.dumps(_VALID_CONTEXT_PACKAGE))
    pkg["package"]["records"][0]["source_hash"] = ""
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    assert report["exit_code"] == 1


# ---------------------------------------------------------------------------
# required_reads_stable
# ---------------------------------------------------------------------------


def test_required_reads_stable_readiness_minimum_matches_resolver_baseline() -> None:
    """READINESS_MINIMUM_READS and resolver MINIMUM_READS stay contract-aligned."""
    resolver_paths = {entry["path"] for entry in RESOLVER_MINIMUM_READS}
    assert set(READINESS_MINIMUM_READS) == resolver_paths


def test_required_reads_stable_in_briefing_envelope() -> None:
    """Briefing required_reads always include the canonical minimum set."""
    briefing = _briefing()
    required_reads = briefing["required_reads"]
    assert isinstance(required_reads, list)
    for path in READINESS_MINIMUM_READS:
        assert path in required_reads, f"missing canonical required read: {path}"


# ---------------------------------------------------------------------------
# stop_conditions_stable
# ---------------------------------------------------------------------------


def test_stop_conditions_stable_baseline_prefixes_in_briefing() -> None:
    """Briefing stop_conditions include stable S1/S3/S10 baseline entries."""
    stop_conditions = _briefing()["stop_conditions"]
    assert isinstance(stop_conditions, list)
    assert len(stop_conditions) >= len(BRIEFING_BASELINE_STOP_PREFIXES)
    for prefix in BRIEFING_BASELINE_STOP_PREFIXES:
        assert any(sc.startswith(prefix) for sc in stop_conditions), (
            f"missing baseline stop condition prefix {prefix!r}"
        )


def test_stop_conditions_stable_resolver_is_deterministic() -> None:
    """Stop resolver output is deterministic for equivalent inputs."""
    inputs = [
        "S1: briefing scope ambiguous",
        "S3: required canon reads unavailable",
        "S10: STOP if LR/Stage/Live claims surface",
    ]
    first = resolve_stop_conditions(stop_conditions=inputs, operation_mode="read_only")
    second = resolve_stop_conditions(stop_conditions=inputs, operation_mode="read_only")
    assert first == second
    assert all("type" in item and "severity" in item for item in first)


# ---------------------------------------------------------------------------
# guardrails_limitations_present
# ---------------------------------------------------------------------------


def test_guardrails_limitations_present_in_briefing_envelope() -> None:
    """Briefing guardrails and trust_limitations are always present."""
    briefing = _briefing()
    guardrails = briefing["guardrails"]
    assert isinstance(guardrails, list)
    assert len(guardrails) >= len(BRIEFING_BASELINE_GUARDRAILS)
    for expected in BRIEFING_BASELINE_GUARDRAILS:
        assert expected in guardrails
    limitations = briefing["trust_limitations"]
    assert isinstance(limitations, list)
    assert len(limitations) >= 1


def test_guardrails_limitations_present_in_context_package_v2() -> None:
    """Context Package v2 includes guardrails and limitations fields."""
    package = build_context_package_v2(
        ContextPackageV2Request(
            target_scope="issue:3775",
            artifacts=[_sample_v2_artifact()],
            generated_at_or_as_of="2026-06-02T12:00:00+00:00",
        )
    )
    assert list(package["guardrails"]) == list(PACKAGE_V2_GUARDRAILS)
    assert isinstance(package["limitations"], list)
    assert len(package["limitations"]) >= 1


# ---------------------------------------------------------------------------
# redaction_negative_controls
# ---------------------------------------------------------------------------


def test_redaction_negative_controls_validate_package_hides_secret_values() -> None:
    """Validator report must not echo secret-like values from blocked input."""
    pkg = json.loads(json.dumps(_VALID_CONTEXT_PACKAGE))
    pkg["package"]["records"][0]["summary"] = f"Contains api_key={_SECRET_FIXTURE}"
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    report_str = json.dumps(report)
    assert _SECRET_FIXTURE not in report_str


def test_redaction_negative_controls_v2_package_redacts_sensitive_metadata() -> None:
    """Context Package v2 redacts secret-like artifact metadata."""
    package = build_context_package_v2(
        ContextPackageV2Request(
            target_scope="issue:3775",
            artifacts=[
                _sample_v2_artifact(
                    metadata={
                        "api_key": _SECRET_FIXTURE,
                        "password": "hunter2-contract",
                    }
                )
            ],
            generated_at_or_as_of="2026-06-02T12:00:00+00:00",
        )
    )
    serialized = json.dumps(package)
    assert _SECRET_FIXTURE not in serialized
    assert "hunter2-contract" not in serialized
    metadata = package["artifacts"][0]["metadata"]
    assert metadata["api_key"] == "[REDACTED]"
    assert metadata["password"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# low_trust_degrades
# ---------------------------------------------------------------------------


def test_low_trust_degrades_without_false_high_operator_trust() -> None:
    """Default briefing path without enrichment records degrades to LOW, not HIGH."""
    briefing = _briefing(requested_depth="quick")
    assert briefing["operator_trust_level"] == "LOW"
    assert briefing["operator_trust_level"] != "HIGH"
    assert briefing["approval_semantics"]["no_echtgeld_go"] is True
    assert any(
        "LOW" in item or "low" in item.lower()
        for item in briefing["trust_limitations"]
    )


# ---------------------------------------------------------------------------
# deterministic_fixture_output
# ---------------------------------------------------------------------------


def test_deterministic_fixture_output_briefing_id_stable() -> None:
    """Equivalent briefing inputs produce identical briefing_id (no wall-clock drift)."""
    kwargs = _briefing_kwargs()
    first = context_briefing_handler(**kwargs)
    second = context_briefing_handler(**kwargs)
    assert first["status"] == "ok" and second["status"] == "ok"
    assert first["briefing"]["briefing_id"] == second["briefing"]["briefing_id"]


def test_deterministic_fixture_output_v2_fixture_package_id_stable() -> None:
    """Fixture-backed v2 package_id and content_hash are stable across builds."""
    payload = json.loads(FIXTURE_V2_PATH.read_text(encoding="utf-8"))
    request = ContextPackageV2Request(**payload)
    first = build_context_package_v2(request)
    second = build_context_package_v2(request)
    assert first["package_id"] == second["package_id"]
    assert first["determinism"]["content_hash"] == second["determinism"]["content_hash"]


def test_deterministic_fixture_output_package_handler_id_stable() -> None:
    """context.package package_id is deterministic for identical artifact lists."""
    bridge = create_bridge()
    args = {"artifacts": ["context.readiness", "AGENTS.md"]}
    first = bridge.execute_tool("context.package", args)
    second = bridge.execute_tool("context.package", args)
    assert first["package"]["package_id"] == second["package"]["package_id"]
    assert first["package"]["created_at"] is None


# ---------------------------------------------------------------------------
# no_live_surrealdb_required
# ---------------------------------------------------------------------------


def test_no_live_surrealdb_required_module_imports_are_side_effect_free() -> None:
    """Contract tests use repo-local builders/handlers only (no live DB client)."""
    module_paths = (
        "tools.context.validate_context_package",
        "tools.mcp.context_bridge",
        "tools.surrealdb.context_package_v2",
        "tools.surrealdb.context_required_reads",
        "tools.surrealdb.context_stop_resolver",
    )
    for module_path in module_paths:
        mod = __import__(module_path, fromlist=["__name__"])
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "surrealdb.connect" not in source
        assert "Surreal(" not in source


# ---------------------------------------------------------------------------
# briefing_envelope_shape
# ---------------------------------------------------------------------------


def test_briefing_envelope_shape_context_briefing_top_level() -> None:
    """context.briefing ok response has stable top-level fields."""
    result = context_briefing_handler(**_briefing_kwargs())
    assert result["tool"] == CONTEXT_BRIEFING_TOOL
    assert result["status"] == "ok"
    assert BRIEFING_OK_TOP_LEVEL.issubset(result.keys())
    briefing = result["briefing"]
    missing = BRIEFING_ENVELOPE_REQUIRED - set(briefing.keys())
    assert not missing, f"missing briefing envelope fields: {sorted(missing)}"


def test_briefing_envelope_shape_cdb_context_briefing_alias() -> None:
    """cdb_context_briefing alias preserves briefing envelope and tool name."""
    result = cdb_context_briefing_handler(**_briefing_kwargs())
    assert result["status"] == "ok"
    assert result["tool"] == CDB_BRIEFING_TOOL
    assert "briefing" in result
    briefing = result["briefing"]
    assert BRIEFING_ENVELOPE_REQUIRED.issubset(briefing.keys())


def test_briefing_envelope_shape_no_iso_timestamp_in_briefing_id() -> None:
    """briefing_id is a fixed-width hash fragment, not a wall-clock timestamp."""
    briefing_id = _briefing()["briefing_id"]
    assert isinstance(briefing_id, str)
    assert re.fullmatch(r"[0-9a-f]{16}", briefing_id)


# ---------------------------------------------------------------------------
# context_package_handler_shape
# ---------------------------------------------------------------------------


def test_context_package_handler_shape_ok_response() -> None:
    """context.package ok response exposes stable package schema fields."""
    result = context_package_handler(artifacts=["context.readiness"])
    assert result["tool"] == "context.package"
    assert result["status"] == "ok"
    assert PACKAGE_HANDLER_OK_TOP.issubset(result.keys())
    package = result["package"]
    missing = PACKAGE_HANDLER_PACKAGE_FIELDS - set(package.keys())
    assert not missing, f"missing package fields: {sorted(missing)}"


def test_context_package_handler_shape_error_response() -> None:
    """context.package error response exposes stable error schema fields."""
    result = context_package_handler()
    assert result["tool"] == "context.package"
    assert result["status"] == "error"
    assert PACKAGE_HANDLER_ERROR_TOP.issubset(result.keys())
    error = result["error"]
    assert "code" in error and "message" in error
    assert error["code"] == "invalid_artifacts"
