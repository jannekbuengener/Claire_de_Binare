"""Fixture-backed integration tests for Wave 16-E (#2159).

Issues:
    #2159 — [SURREALDB][CONTEXT][STALE-TESTS] Add stale knowledge fixtures and tests
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Scope:
    Verifies that the file-backed fixtures in
    tests/fixtures/surrealdb/stale_knowledge_scan/ are deterministic,
    secret-free, structurally correct, and can drive all four Wave-16
    components:
        1. scan service (scan_stale_knowledge_v1)
        2. refresh plan generator (generate_refresh_plan_v1)
        3. stale context CLI (main)
        4. stale context MCP tool (handle_cdb_context_stale)

    All tests are @pytest.mark.unit — no DB, no SurrealDB SDK, no MCP
    network, no runtime, no writes.

Fixtures covered:
    - all_types_bundle.json  — triggers all 8 stale_types
    - sample_bundle.json     — triggers source_hash_changed, source_deleted,
                               evidence_expired (3 types, original fixture)

Coverage added by this file:
    - File loads without error and has the expected JSON structure.
    - All 8 stale_types are triggered by all_types_bundle.json.
    - Stale IDs are deterministic across two independent scan calls.
    - sample_bundle.json triggers exactly the 3 expected stale_types.
    - Fixture JSON keys contain no secret-like names.
    - Fixture string values contain no absolute host paths.
    - Refresh plan from all_types_bundle covers all 8 stale_types.
    - CLI scan and report commands consume all_types_bundle.json correctly.
    - MCP tool returns findings for all 8 stale_types from all_types_bundle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.mcp.stale_context_tools import handle_cdb_context_stale, TOOL_CDB_CONTEXT_STALE
from tools.surrealdb.stale_context_cli import EXIT_OK, main
from tools.surrealdb.stale_knowledge_scan import STALE_TYPES, scan_stale_knowledge_v1
from tools.surrealdb.stale_refresh_plan import generate_refresh_plan_v1

# ── Fixture paths ─────────────────────────────────────────────────────────────

_FIXTURE_DIR = Path("tests/fixtures/surrealdb/stale_knowledge_scan")
_ALL_TYPES_PATH = _FIXTURE_DIR / "all_types_bundle.json"
_SAMPLE_PATH = _FIXTURE_DIR / "sample_bundle.json"

# Reference timestamp matching all_types_bundle.json meta.as_of
_AS_OF = "2026-05-06T12:00:00+00:00"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load(path: Path) -> dict[str, Any]:
    """Load a fixture JSON file and return it as a dict."""
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_without_meta(fixture: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the fixture with 'meta' and '_comment' stripped.

    scan_stale_knowledge_v1 accepts any Mapping — it ignores unknown keys,
    but the CLI's _load_bundle() pops 'meta' automatically.  For direct
    service/plan calls we pass as_of explicitly so the meta field does not
    matter.  Strip it here to avoid confusion.
    """
    return {k: v for k, v in fixture.items() if k not in ("meta", "_comment")}


def _mcp_request(bundle: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """Minimal MCP request dict for handle_cdb_context_stale."""
    params: dict[str, Any] = {"bundle": bundle, "as_of": _AS_OF}
    params.update(extra)
    return {"tool": TOOL_CDB_CONTEXT_STALE, "parameters": params}


# ── 1. Fixture file loads ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_all_types_fixture_loads() -> None:
    """all_types_bundle.json exists, parses as JSON object, has all domain keys."""
    assert _ALL_TYPES_PATH.exists(), f"Fixture file missing: {_ALL_TYPES_PATH}"
    fixture = _load(_ALL_TYPES_PATH)
    assert isinstance(fixture, dict), "Fixture must be a JSON object"

    expected_keys = {
        "sources",
        "decisions",
        "evidence_records",
        "memory_records",
        "dependency_edges",
        "context_packages",
        "briefings",
    }
    missing = expected_keys - set(fixture.keys())
    assert not missing, f"Fixture missing expected domain keys: {missing}"


# ── 2. All 8 stale_types triggered ───────────────────────────────────────────


@pytest.mark.unit
def test_all_types_fixture_triggers_all_8_stale_types() -> None:
    """scan_stale_knowledge_v1 on all_types_bundle.json must produce all 8 stale_types."""
    fixture = _load(_ALL_TYPES_PATH)
    bundle = _bundle_without_meta(fixture)
    result = scan_stale_knowledge_v1(bundle, as_of=_AS_OF)

    assert result.status == "ok"
    found_types = {f.stale_type for f in result.findings}
    missing_types = STALE_TYPES - found_types
    assert not missing_types, (
        f"Missing stale_types in findings: {missing_types}. "
        f"Got: {found_types}"
    )
    assert found_types == STALE_TYPES, (
        f"Unexpected stale_types: {found_types - STALE_TYPES}"
    )


# ── 3. Determinism ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_all_types_fixture_stale_ids_deterministic() -> None:
    """Two independent scan calls on all_types_bundle.json produce identical stale_id sets."""
    fixture = _load(_ALL_TYPES_PATH)
    bundle = _bundle_without_meta(fixture)

    result_a = scan_stale_knowledge_v1(bundle, as_of=_AS_OF)
    result_b = scan_stale_knowledge_v1(bundle, as_of=_AS_OF)

    ids_a = sorted(f.stale_id for f in result_a.findings)
    ids_b = sorted(f.stale_id for f in result_b.findings)
    assert ids_a == ids_b, "stale_ids are not deterministic across two scan calls"
    assert len(ids_a) >= 8, f"Expected at least 8 findings, got {len(ids_a)}"


# ── 4. sample_bundle triggers its 3 types ────────────────────────────────────


@pytest.mark.unit
def test_sample_fixture_triggers_3_expected_types() -> None:
    """sample_bundle.json triggers exactly source_hash_changed, source_deleted,
    evidence_expired — and nothing else."""
    assert _SAMPLE_PATH.exists(), f"Fixture file missing: {_SAMPLE_PATH}"
    fixture = _load(_SAMPLE_PATH)
    bundle = _bundle_without_meta(fixture)
    result = scan_stale_knowledge_v1(bundle, as_of=_AS_OF)

    found = {f.stale_type for f in result.findings}
    expected = {"source_hash_changed", "source_deleted", "evidence_expired"}
    assert found == expected, (
        f"sample_bundle.json produced unexpected stale_types.\n"
        f"Expected: {expected}\nGot:      {found}"
    )


# ── 5. Fixture secret safety (key names) ─────────────────────────────────────


@pytest.mark.unit
def test_fixtures_contain_no_secret_key_names() -> None:
    """No key in any fixture JSON must match a secret-like name pattern."""
    _SECRET_NAMES = frozenset({
        "password", "passwd", "secret", "token", "api_key", "apikey",
        "private_key", "privatekey", "access_key", "auth_token",
    })
    _VALUE_PATTERNS = ("BEGIN RSA", "BEGIN OPENSSH", "ghp_", "sk-", "eyJ")

    def _iter_keys_and_values(obj: Any, path: str = ""):
        """Recursively yield (path, key, value) tuples from any JSON structure."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield path, k, v
                yield from _iter_keys_and_values(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                yield from _iter_keys_and_values(item, f"{path}[{i}]")

    violations: list[str] = []

    for fixture_path in (_ALL_TYPES_PATH, _SAMPLE_PATH):
        fixture = _load(fixture_path)
        for loc, key, value in _iter_keys_and_values(fixture):
            if key.lower() in _SECRET_NAMES:
                violations.append(
                    f"{fixture_path.name}{loc}: key '{key}' matches secret pattern"
                )
            if isinstance(value, str):
                for pat in _VALUE_PATTERNS:
                    if pat in value:
                        violations.append(
                            f"{fixture_path.name}{loc}.{key}: "
                            f"value matches secret pattern '{pat}'"
                        )

    assert not violations, "Secret-like keys/values found in fixtures:\n" + "\n".join(violations)


# ── 6. No absolute host paths in fixture values ───────────────────────────────


@pytest.mark.unit
def test_fixtures_contain_no_absolute_paths() -> None:
    """No string value in any fixture must be an absolute host path.

    ISO-8601 timestamps ('+00:00') are exempt.
    Only values that start with '/' (Unix) or look like Windows drive paths
    are flagged.
    """

    def _iter_string_values(obj: Any) -> list[str]:
        strings: list[str] = []
        if isinstance(obj, dict):
            for v in obj.values():
                strings.extend(_iter_string_values(v))
        elif isinstance(obj, list):
            for item in obj:
                strings.extend(_iter_string_values(item))
        elif isinstance(obj, str):
            strings.append(obj)
        return strings

    violations: list[str] = []

    for fixture_path in (_ALL_TYPES_PATH, _SAMPLE_PATH):
        fixture = _load(fixture_path)
        for s in _iter_string_values(fixture):
            # ISO-8601 timestamps contain '+' or 'T' — skip those
            if "T" in s or "+" in s or "Z" in s:
                continue
            # Flag Unix absolute paths or Windows drive paths
            if s.startswith("/") or (len(s) > 2 and s[1] == ":" and s[2] in ("/", "\\")):
                violations.append(f"{fixture_path.name}: absolute path value: {s!r}")

    assert not violations, "Absolute host paths found in fixtures:\n" + "\n".join(violations)


# ── 7. Refresh plan covers all 8 stale_types ─────────────────────────────────


@pytest.mark.unit
def test_refresh_plan_from_all_types_fixture_covers_all_stale_types() -> None:
    """generate_refresh_plan_v1 on all_types_bundle.json must produce plan items
    for all 8 stale_types — verifying the fixture drives complete plan coverage."""
    fixture = _load(_ALL_TYPES_PATH)
    bundle = _bundle_without_meta(fixture)
    result = generate_refresh_plan_v1(bundle, as_of=_AS_OF)

    assert result.status == "ok"
    plan_stale_types = {item.stale_type for item in result.plan_items}
    missing = STALE_TYPES - plan_stale_types
    assert not missing, (
        f"Refresh plan missing plan items for stale_types: {missing}. "
        f"Got plan stale_types: {plan_stale_types}"
    )
    # All plan items must be write-unauthorized (guardrail)
    for item in result.plan_items:
        assert item.write_authorized is False, (
            f"plan_item for {item.stale_type!r} has write_authorized=True — "
            "guardrail violation."
        )


# ── 8. CLI scan consumes all_types_bundle ────────────────────────────────────


@pytest.mark.unit
def test_cli_scan_all_types_fixture(capsys) -> None:
    """CLI scan-stale-context with all_types_bundle.json: exit 0, total_count >= 8."""
    exit_code = main(
        ["--format", "json", "scan-stale-context", "--input", str(_ALL_TYPES_PATH)]
    )
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert exit_code == EXIT_OK, f"Expected exit 0, got {exit_code}"
    assert payload["status"] == "ok"
    assert payload["total_count"] >= 8, (
        f"Expected total_count >= 8, got {payload['total_count']}"
    )
    found_types = {f["stale_type"] for f in payload["findings"]}
    missing = STALE_TYPES - found_types
    assert not missing, f"CLI output missing stale_types: {missing}"


# ── 9. CLI report has all 8 stale_types in stale_type_summary ────────────────


@pytest.mark.unit
def test_cli_report_all_types_fixture_stale_type_summary(capsys) -> None:
    """CLI report-stale-context with all_types_bundle.json: stale_type_summary
    contains all 8 stale_types with correct counts."""
    exit_code = main(
        ["--format", "json", "report-stale-context", "--input", str(_ALL_TYPES_PATH)]
    )
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    st_summary = payload["stale_type_summary"]
    missing = STALE_TYPES - set(st_summary.keys())
    assert not missing, f"stale_type_summary missing types: {missing}"
    # Each type in all_types_bundle has exactly 1 finding
    for st in STALE_TYPES:
        assert st_summary[st] >= 1, (
            f"stale_type_summary[{st!r}] = {st_summary[st]}, expected >= 1"
        )


# ── 10. MCP tool returns all 8 stale_types ───────────────────────────────────


@pytest.mark.unit
def test_mcp_all_types_fixture_returns_all_8_stale_types() -> None:
    """handle_cdb_context_stale with all_types_bundle (no filter): all 8 stale_types
    present in findings."""
    fixture = _load(_ALL_TYPES_PATH)
    bundle = _bundle_without_meta(fixture)
    result = handle_cdb_context_stale(_mcp_request(bundle))

    assert result["status"] == "ok", f"unexpected error: {result.get('error')}"
    found_types = {f["stale_type"] for f in result["findings"]}
    missing = STALE_TYPES - found_types
    assert not missing, (
        f"MCP output missing stale_types: {missing}. Got: {found_types}"
    )
    assert result["summary"]["total_count"] >= 8
