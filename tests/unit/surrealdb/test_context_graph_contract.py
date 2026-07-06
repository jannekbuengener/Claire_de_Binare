"""Context Graph contract tests for nodes, edges, IDs, hashes, fallback (#3772)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.surrealdb.context_graph_contract import (
    ALLOWED_EDGE_TYPES,
    SCHEMA_VERSION,
    assert_repo_only_graph_claim_blocked,
    build_node_id_index,
    classify_graph_evidence_posture,
    compute_graph_fingerprint,
    find_duplicate_nodes,
    find_missing_source_refs,
    find_orphan_edges,
    synthetic_orphan_edge,
    validate_deterministic_id,
    validate_edge_payload,
    validate_indexer_graph,
    validate_node_payload,
)
from tools.surrealdb.context_indexer import (
    CodeSymbol,
    DependencyEdge,
    RepoArtifact,
    derive_dependency_edges,
    extract_code_symbols,
    run_indexer,
    stable_id,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

SCOPE_CONFIG = Path("infrastructure/config/surrealdb/context_ingestion_scope.yaml")
FIXTURE_ROOT = Path("tests/fixtures/surrealdb/context_indexer/repo_clean")
CONTEXT_GRAPH_FIXTURE = Path("tests/fixtures/surrealdb/context_graph/sample_module.py")
_FAKE_HASH = "a" * 64


def _make_artifact(
    source_path: str,
    file_type: str = "python",
    normalized_sha256: str = _FAKE_HASH,
) -> RepoArtifact:
    return RepoArtifact(
        artifact_id=stable_id("repo_artifact", source_path, normalized_sha256),
        source_path=source_path,
        file_type=file_type,
        raw_sha256=normalized_sha256,
        normalized_sha256=normalized_sha256,
        size_bytes=100,
        git_commit=None,
        observed_at="2026-01-01T00:00:00Z",
        sensitivity="internal_context",
    )


def _make_symbol(
    source_path: str,
    name: str = "top_level_function",
    source_hash: str = _FAKE_HASH,
) -> CodeSymbol:
    return CodeSymbol(
        symbol_id=stable_id("symbol", source_path, name),
        source_path=source_path,
        source_hash=source_hash,
        symbol_type="function",
        name=name,
        qualified_name=name,
        line_start=1,
        line_end=2,
        decorators=[],
        is_async=False,
        parent_class=None,
        confidence="high",
        inferred=False,
    )


# ---------------------------------------------------------------------------
# Deterministic IDs
# ---------------------------------------------------------------------------


def test_stable_id_is_deterministic_for_same_inputs() -> None:
    first = stable_id("repo_artifact", "core/a.py", _FAKE_HASH)
    second = stable_id("repo_artifact", "core/a.py", _FAKE_HASH)
    assert first == second
    assert validate_deterministic_id(first, expected_prefix="repo_artifact") == []


def test_stable_id_changes_when_inputs_change() -> None:
    base = stable_id("repo_artifact", "core/a.py", _FAKE_HASH)
    changed = stable_id("repo_artifact", "core/a.py", "b" * 64)
    assert base != changed


def test_validate_deterministic_id_rejects_bad_prefix() -> None:
    node_id = stable_id("symbol", "svc.py", "fn")
    errors = validate_deterministic_id(node_id, expected_prefix="repo_artifact")
    assert errors
    assert "expected prefix" in errors[0]


# ---------------------------------------------------------------------------
# Node / edge schema
# ---------------------------------------------------------------------------


def test_validate_node_payload_repo_artifact_accepts_canonical_payload() -> None:
    artifact = _make_artifact("services/risk/service.py")
    errors = validate_node_payload(
        "repo_artifact", artifact.to_payload("run-contract"), run_id="run-contract"
    )
    assert errors == []


def test_validate_node_payload_rejects_missing_source_refs() -> None:
    artifact = _make_artifact("core/x.py")
    payload = artifact.to_payload("run-contract")
    del payload["source_hash"]
    errors = validate_node_payload("repo_artifact", payload)
    assert any("source_hash" in err for err in errors)


def test_validate_edge_payload_accepts_derived_contains_edge() -> None:
    artifact = _make_artifact("mymod.py")
    source = CONTEXT_GRAPH_FIXTURE.read_text(encoding="utf-8")
    symbols, _ = extract_code_symbols(artifact, source)
    edges = derive_dependency_edges([artifact], symbols, [], [])
    contains = next(edge for edge in edges if edge.edge_type == "contains")
    errors = validate_edge_payload(contains.to_payload("run-contract"))
    assert errors == []
    assert contains.edge_type in ALLOWED_EDGE_TYPES


def test_validate_edge_payload_rejects_unknown_edge_type() -> None:
    payload = synthetic_orphan_edge().to_payload("run-contract")
    payload["edge_type"] = "depends_on_magic"
    errors = validate_edge_payload(payload)
    assert any("edge_type" in err for err in errors)


# ---------------------------------------------------------------------------
# Fingerprint stability
# ---------------------------------------------------------------------------


def test_graph_fingerprint_stable_for_same_fixture_indexer_run() -> None:
    scope = FIXTURE_ROOT / "infrastructure/config/surrealdb/context_ingestion_scope.yaml"
    first = run_indexer(FIXTURE_ROOT, scope)
    second = run_indexer(FIXTURE_ROOT, scope)
    assert compute_graph_fingerprint(first) == compute_graph_fingerprint(second)


def test_graph_fingerprint_changes_when_symbol_set_changes() -> None:
    artifact = _make_artifact("mod.py")
    source = CONTEXT_GRAPH_FIXTURE.read_text(encoding="utf-8")
    symbols, _ = extract_code_symbols(artifact, source)

    class _MiniResult:
        run_id = "run-mini"
        repo_artifacts = [artifact]
        code_symbols = symbols
        doc_pages = []
        doc_sections = []
        doc_chunks = []
        dependency_edges = derive_dependency_edges([artifact], symbols, [], [])

    full_fp = compute_graph_fingerprint(_MiniResult())  # type: ignore[arg-type]
    trimmed = list(symbols)[:-1]
    _MiniResult.code_symbols = trimmed
    _MiniResult.dependency_edges = derive_dependency_edges(
        [artifact], trimmed, [], []
    )
    reduced_fp = compute_graph_fingerprint(_MiniResult())  # type: ignore[arg-type]
    assert full_fp != reduced_fp


# ---------------------------------------------------------------------------
# Integrity regressions: duplicate / orphan / stale
# ---------------------------------------------------------------------------


def test_find_duplicate_nodes_flags_same_path_different_ids() -> None:
    artifact_a = _make_artifact("dup.py", normalized_sha256="a" * 64)
    artifact_b = _make_artifact("dup.py", normalized_sha256="b" * 64)

    class _DupResult:
        run_id = "run-dup"
        repo_artifacts = [artifact_a, artifact_b]
        code_symbols = []
        doc_pages = []
        doc_sections = []
        doc_chunks = []
        dependency_edges = []

    findings = find_duplicate_nodes(_DupResult())  # type: ignore[arg-type]
    assert any(f.code == "duplicate_node" for f in findings)


def test_find_orphan_edges_flags_missing_endpoint() -> None:
    artifact = _make_artifact("only.py")
    orphan = synthetic_orphan_edge()

    class _OrphanResult:
        run_id = "run-orphan"
        repo_artifacts = [artifact]
        code_symbols = []
        doc_pages = []
        doc_sections = []
        doc_chunks = []
        dependency_edges = [orphan]

    findings = find_orphan_edges(_OrphanResult())  # type: ignore[arg-type]
    assert any(f.code == "orphan_edge" for f in findings)


def test_find_missing_source_refs_flags_stale_symbol_hash() -> None:
    artifact = _make_artifact("stale.py", normalized_sha256="c" * 64)
    symbol = _make_symbol("stale.py", source_hash="d" * 64)

    class _StaleResult:
        run_id = "run-stale"
        repo_artifacts = [artifact]
        code_symbols = [symbol]
        doc_pages = []
        doc_sections = []
        doc_chunks = []
        dependency_edges = []

    findings = find_missing_source_refs(_StaleResult())  # type: ignore[arg-type]
    assert any(f.code == "stale_link" for f in findings)


def test_virtual_symbol_mention_target_is_not_orphan() -> None:
    doc = _make_artifact("docs/x.md", file_type="markdown")
    mention_edge = DependencyEdge(
        edge_id=stable_id("dep_edge", "mentions", doc.artifact_id, "ghost"),
        from_id=doc.artifact_id,
        to_id=stable_id("symbol_mention", "GhostSym"),
        edge_type="mentions",
        source_path=doc.source_path,
        confidence="high",
        inferred=True,
        from_table="repo_artifact",
        to_table="symbol_mention",
    )

    class _MentionResult:
        run_id = "run-mention"
        repo_artifacts = [doc]
        code_symbols = []
        doc_pages = []
        doc_sections = []
        doc_chunks = []
        dependency_edges = [mention_edge]

    findings = find_orphan_edges(_MentionResult())  # type: ignore[arg-type]
    assert findings == []


# ---------------------------------------------------------------------------
# Repo-only fallback / negative control
# ---------------------------------------------------------------------------


def test_classify_graph_evidence_posture_defaults_repo_only() -> None:
    posture = classify_graph_evidence_posture()
    assert posture["evidence_posture"] == "repo_only"
    assert posture["brain_source"] == "repo-only"
    assert posture["brain_status"] == "not-used"
    assert posture["db_claims_allowed"] is False


def test_repo_only_blocks_db_backed_graph_claim_negative_control() -> None:
    blocked = assert_repo_only_graph_claim_blocked(
        db_record_ids=None,
        record_source=None,
        claimed_brain_source="surrealdb-local",
    )
    assert blocked is True


def test_db_record_ids_allow_db_backed_posture_only_with_record_source() -> None:
    posture = classify_graph_evidence_posture(
        db_record_ids=["dependency_edge:abc"],
        record_source="surrealdb-local",
    )
    assert posture["db_claims_allowed"] is True
    assert posture["evidence_posture"] == "db_backed"
    assert assert_repo_only_graph_claim_blocked(
        db_record_ids=["dependency_edge:abc"],
        record_source="surrealdb-local",
        claimed_brain_source="surrealdb-local",
    ) is False


def test_caller_record_ids_without_record_source_stays_repo_only() -> None:
    posture = classify_graph_evidence_posture(
        db_record_ids=["dependency_edge:abc"],
        record_source=None,
    )
    assert posture["evidence_posture"] == "repo_only"
    assert assert_repo_only_graph_claim_blocked(
        db_record_ids=["dependency_edge:abc"],
        record_source=None,
        claimed_brain_source="surrealdb-local",
    ) is True


# ---------------------------------------------------------------------------
# End-to-end contract on fixture indexer output (no live SurrealDB)
# ---------------------------------------------------------------------------


def test_validate_indexer_graph_passes_repo_clean_fixture() -> None:
    scope = FIXTURE_ROOT / "infrastructure/config/surrealdb/context_ingestion_scope.yaml"
    result = run_indexer(FIXTURE_ROOT, scope)
    report = validate_indexer_graph(result)

    assert report.schema_version == SCHEMA_VERSION
    assert report.valid is True
    assert report.edge_count == len(result.dependency_edges)
    assert report.node_count == len(build_node_id_index(result))
    assert report.graph_fingerprint
    assert report.evidence_posture == "repo_only"
    assert not [f for f in report.findings if f.severity == "error"]


def test_context_graph_sample_module_derives_valid_contains_edges() -> None:
    artifact = _make_artifact("tests/fixtures/surrealdb/context_graph/sample_module.py")
    source = CONTEXT_GRAPH_FIXTURE.read_text(encoding="utf-8")
    symbols, _ = extract_code_symbols(artifact, source)
    edges = derive_dependency_edges([artifact], symbols, [], [])

    assert symbols
    assert any(edge.edge_type == "contains" for edge in edges)
    for edge in edges:
        assert validate_edge_payload(edge.to_payload("run-graph")) == []
