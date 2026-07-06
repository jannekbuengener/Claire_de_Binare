"""Context Graph contract validation for indexer exports (Issue #3772).

Read-only helpers for graph nodes, edges, deterministic IDs, source refs,
fingerprints, and repo-only evidence posture. No SurrealDB access, no writes.
LR remains NO-GO.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.surrealdb.context_indexer import (
    SCHEMA_VERSION as INDEXER_SCHEMA_VERSION,
    DependencyEdge,
    IndexerResult,
    stable_id,
)

SCHEMA_VERSION = "context-graph-contract/v1"

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[0-9a-f]{64}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

VIRTUAL_NODE_TABLES = frozenset({"module", "symbol_mention"})

KNOWN_RECORD_TABLES = frozenset(
    {
        "repo_artifact",
        "code_symbol",
        "doc_page",
        "doc_section",
        "doc_chunk",
    }
)

ALLOWED_EDGE_TYPES = frozenset({"contains", "imports", "documents", "mentions"})

NODE_ID_FIELD_BY_KIND: dict[str, str] = {
    "repo_artifact": "artifact_id",
    "code_symbol": "symbol_id",
    "doc_page": "page_id",
    "doc_section": "section_id",
    "doc_chunk": "chunk_id",
}

NODE_SOURCE_REF_FIELDS: dict[str, tuple[str, ...]] = {
    "repo_artifact": ("source_path", "normalized_sha256", "source_hash"),
    "code_symbol": ("source_path", "source_hash"),
    "doc_page": ("source_path", "source_hash"),
    "doc_section": ("source_path", "source_hash", "page_id"),
    "doc_chunk": ("source_path", "source_hash", "page_id", "section_id"),
}

EDGE_REQUIRED_FIELDS = (
    "schema_version",
    "run_id",
    "edge_id",
    "from_id",
    "to_id",
    "edge_type",
    "from_table",
    "to_table",
)


@dataclass(frozen=True)
class GraphContractFinding:
    code: str
    severity: str
    message: str
    target_id: str | None = None


@dataclass
class GraphContractReport:
    schema_version: str = SCHEMA_VERSION
    valid: bool = True
    findings: list[GraphContractFinding] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    graph_fingerprint: str = ""
    evidence_posture: str = "repo_only"

    def add(self, finding: GraphContractFinding) -> None:
        self.findings.append(finding)
        if finding.severity == "error":
            self.valid = False


def validate_deterministic_id(value: str, *, expected_prefix: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, str) or not value.strip():
        return ["id must be a non-empty string"]
    if not ID_PATTERN.match(value):
        errors.append(f"id {value!r} does not match prefix:sha256 pattern")
    elif not value.startswith(f"{expected_prefix}:"):
        errors.append(f"id {value!r} expected prefix {expected_prefix!r}")
    return errors


def _non_empty_str(payload: Mapping[str, Any], key: str) -> str | None:
    raw = payload.get(key)
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


def validate_node_payload(
    kind: str,
    payload: Mapping[str, Any],
    *,
    run_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    id_field = NODE_ID_FIELD_BY_KIND.get(kind)
    if id_field is None:
        return [f"unsupported node kind: {kind!r}"]

    node_id = _non_empty_str(payload, id_field)
    if node_id is None:
        errors.append(f"{kind} missing {id_field}")
    else:
        prefix = kind if kind != "repo_artifact" else "repo_artifact"
        if kind == "doc_page":
            prefix = "doc_page"
        elif kind == "doc_section":
            prefix = "doc_section"
        elif kind == "doc_chunk":
            prefix = "doc_chunk"
        elif kind == "code_symbol":
            prefix = "symbol"
        errors.extend(validate_deterministic_id(node_id, expected_prefix=prefix))

    schema_version = payload.get("schema_version")
    if schema_version != INDEXER_SCHEMA_VERSION:
        errors.append(
            f"{kind} schema_version must be {INDEXER_SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    if run_id is not None:
        payload_run_id = payload.get("run_id")
        if payload_run_id != run_id:
            errors.append(
                f"{kind} run_id mismatch: expected {run_id!r}, got {payload_run_id!r}"
            )

    for field_name in NODE_SOURCE_REF_FIELDS.get(kind, ()):
        if _non_empty_str(payload, field_name) is None:
            errors.append(f"{kind} missing source ref field {field_name!r}")

    if kind == "repo_artifact":
        source_hash = _non_empty_str(payload, "source_hash")
        normalized = _non_empty_str(payload, "normalized_sha256")
        if source_hash and normalized and source_hash != normalized:
            errors.append(
                f"repo_artifact source_hash {source_hash!r} != normalized_sha256 {normalized!r}"
            )
        if normalized and not SHA256_PATTERN.match(normalized):
            errors.append(f"repo_artifact normalized_sha256 is not sha256 hex: {normalized!r}")

    return errors


def validate_edge_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in EDGE_REQUIRED_FIELDS:
        if field_name not in payload:
            errors.append(f"dependency_edge missing required field {field_name!r}")

    edge_id = _non_empty_str(payload, "edge_id")
    if edge_id is not None:
        errors.extend(validate_deterministic_id(edge_id, expected_prefix="dep_edge"))

    edge_type = _non_empty_str(payload, "edge_type")
    if edge_type is not None and edge_type not in ALLOWED_EDGE_TYPES:
        errors.append(f"unsupported edge_type {edge_type!r}")

    from_table = _non_empty_str(payload, "from_table")
    to_table = _non_empty_str(payload, "to_table")
    if from_table and from_table not in KNOWN_RECORD_TABLES | VIRTUAL_NODE_TABLES:
        errors.append(f"unknown from_table {from_table!r}")
    if to_table and to_table not in KNOWN_RECORD_TABLES | VIRTUAL_NODE_TABLES:
        errors.append(f"unknown to_table {to_table!r}")

    source_path = payload.get("source_path")
    if source_path is not None and not isinstance(source_path, str):
        errors.append("source_path must be a string when present")

    return errors


def build_node_id_index(result: IndexerResult) -> dict[str, str]:
    index: dict[str, str] = {}
    for artifact in result.repo_artifacts:
        index[artifact.artifact_id] = "repo_artifact"
    for symbol in result.code_symbols:
        index[symbol.symbol_id] = "code_symbol"
    for page in result.doc_pages:
        index[page.page_id] = "doc_page"
    for section in result.doc_sections:
        index[section.section_id] = "doc_section"
    for chunk in result.doc_chunks:
        index[chunk.chunk_id] = "doc_chunk"
    return index


def find_duplicate_nodes(result: IndexerResult) -> list[GraphContractFinding]:
    findings: list[GraphContractFinding] = []
    by_path: dict[tuple[str, str], str] = {}

    def _track(kind: str, source_path: str, node_id: str) -> None:
        key = (kind, source_path)
        prior = by_path.get(key)
        if prior is not None and prior != node_id:
            findings.append(
                GraphContractFinding(
                    code="duplicate_node",
                    severity="error",
                    message=(
                        f"duplicate {kind} for source_path {source_path!r}: "
                        f"{prior!r} vs {node_id!r}"
                    ),
                    target_id=node_id,
                )
            )
        else:
            by_path[key] = node_id

    for artifact in result.repo_artifacts:
        _track("repo_artifact", artifact.source_path, artifact.artifact_id)
    for symbol in result.code_symbols:
        _track("code_symbol", symbol.source_path, symbol.symbol_id)
    for page in result.doc_pages:
        _track("doc_page", page.source_path, page.page_id)

    id_counts: dict[str, int] = {}
    for node_id in build_node_id_index(result):
        id_counts[node_id] = id_counts.get(node_id, 0) + 1
    for node_id, count in id_counts.items():
        if count > 1:
            findings.append(
                GraphContractFinding(
                    code="duplicate_node_id",
                    severity="error",
                    message=f"node id {node_id!r} appears {count} times",
                    target_id=node_id,
                )
            )
    return findings


def find_orphan_edges(
    result: IndexerResult,
    node_index: Mapping[str, str] | None = None,
) -> list[GraphContractFinding]:
    findings: list[GraphContractFinding] = []
    index = dict(node_index or build_node_id_index(result))
    artifact_paths = {a.source_path for a in result.repo_artifacts}

    for edge in result.dependency_edges:
        if edge.from_table not in VIRTUAL_NODE_TABLES and edge.from_id not in index:
            findings.append(
                GraphContractFinding(
                    code="orphan_edge",
                    severity="error",
                    message=f"edge {edge.edge_id!r} from_id {edge.from_id!r} has no node",
                    target_id=edge.edge_id,
                )
            )
        if edge.to_table not in VIRTUAL_NODE_TABLES and edge.to_id not in index:
            findings.append(
                GraphContractFinding(
                    code="orphan_edge",
                    severity="error",
                    message=f"edge {edge.edge_id!r} to_id {edge.to_id!r} has no node",
                    target_id=edge.edge_id,
                )
            )
        if edge.source_path and edge.source_path not in artifact_paths:
            findings.append(
                GraphContractFinding(
                    code="stale_link",
                    severity="warning",
                    message=(
                        f"edge {edge.edge_id!r} source_path {edge.source_path!r} "
                        "not in repo_artifacts"
                    ),
                    target_id=edge.edge_id,
                )
            )
    return findings


def find_missing_source_refs(result: IndexerResult) -> list[GraphContractFinding]:
    findings: list[GraphContractFinding] = []
    artifact_hashes = {
        artifact.source_path: artifact.normalized_sha256
        for artifact in result.repo_artifacts
    }

    for symbol in result.code_symbols:
        expected = artifact_hashes.get(symbol.source_path)
        if expected is None:
            findings.append(
                GraphContractFinding(
                    code="missing_source_ref",
                    severity="error",
                    message=(
                        f"code_symbol {symbol.symbol_id!r} source_path "
                        f"{symbol.source_path!r} has no repo_artifact"
                    ),
                    target_id=symbol.symbol_id,
                )
            )
        elif symbol.source_hash != expected:
            findings.append(
                GraphContractFinding(
                    code="stale_link",
                    severity="error",
                    message=(
                        f"code_symbol {symbol.symbol_id!r} source_hash stale "
                        f"(expected {expected!r}, got {symbol.source_hash!r})"
                    ),
                    target_id=symbol.symbol_id,
                )
            )
    return findings


def compute_graph_fingerprint(result: IndexerResult) -> str:
    """Deterministic structural fingerprint (run_id/timestamps excluded)."""

    nodes = sorted(
        [
            {
                "kind": kind,
                "id": node_id,
                "source_path": getattr(obj, "source_path", ""),
            }
            for kind, collection, id_attr in (
                ("repo_artifact", result.repo_artifacts, "artifact_id"),
                ("code_symbol", result.code_symbols, "symbol_id"),
                ("doc_page", result.doc_pages, "page_id"),
            )
            for obj in collection
            for node_id in [getattr(obj, id_attr)]
        ],
        key=lambda item: (item["kind"], item["id"]),
    )
    edges = sorted(
        [
            {
                "edge_id": edge.edge_id,
                "edge_type": edge.edge_type,
                "from_id": edge.from_id,
                "to_id": edge.to_id,
                "from_table": edge.from_table,
                "to_table": edge.to_table,
            }
            for edge in result.dependency_edges
        ],
        key=lambda item: item["edge_id"],
    )
    return canonical_hash(
        {
            "indexer_schema_version": INDEXER_SCHEMA_VERSION,
            "contract_schema_version": SCHEMA_VERSION,
            "nodes": nodes,
            "edges": edges,
        }
    )


def classify_graph_evidence_posture(
    *,
    db_record_ids: Sequence[str] | None = None,
    record_source: str | None = None,
) -> dict[str, Any]:
    """Fail-closed posture for graph truth claims without DB record evidence."""

    has_ids = bool(db_record_ids)
    if has_ids and record_source == "surrealdb-local":
        return {
            "evidence_posture": "db_backed",
            "brain_source": "surrealdb-local",
            "brain_status": "partial",
            "db_claims_allowed": True,
            "record_ids": list(db_record_ids or ()),
        }
    return {
        "evidence_posture": "repo_only",
        "brain_source": "repo-only",
        "brain_status": "not-used",
        "db_claims_allowed": False,
        "record_ids": [],
    }


def assert_repo_only_graph_claim_blocked(
    *,
    db_record_ids: Sequence[str] | None = None,
    record_source: str | None = None,
    claimed_brain_source: str,
) -> bool:
    """Return True when a DB-backed graph claim must be rejected."""

    posture = classify_graph_evidence_posture(
        db_record_ids=db_record_ids,
        record_source=record_source,
    )
    if posture["db_claims_allowed"]:
        return False
    return claimed_brain_source in {"surrealdb-local", "used", "db_backed"}


def validate_indexer_graph(result: IndexerResult) -> GraphContractReport:
    report = GraphContractReport(
        node_count=len(build_node_id_index(result)),
        edge_count=len(result.dependency_edges),
        graph_fingerprint=compute_graph_fingerprint(result),
        evidence_posture=classify_graph_evidence_posture()["evidence_posture"],
    )

    for artifact in result.repo_artifacts:
        for message in validate_node_payload(
            "repo_artifact", artifact.to_payload(result.run_id), run_id=result.run_id
        ):
            report.add(
                GraphContractFinding(
                    code="invalid_node",
                    severity="error",
                    message=message,
                    target_id=artifact.artifact_id,
                )
            )

    for symbol in result.code_symbols:
        for message in validate_node_payload(
            "code_symbol", symbol.to_payload(result.run_id), run_id=result.run_id
        ):
            report.add(
                GraphContractFinding(
                    code="invalid_node",
                    severity="error",
                    message=message,
                    target_id=symbol.symbol_id,
                )
            )

    for edge in result.dependency_edges:
        for message in validate_edge_payload(edge.to_payload(result.run_id)):
            report.add(
                GraphContractFinding(
                    code="invalid_edge",
                    severity="error",
                    message=message,
                    target_id=edge.edge_id,
                )
            )

    for finding in (
        find_duplicate_nodes(result)
        + find_orphan_edges(result)
        + find_missing_source_refs(result)
    ):
        report.add(finding)

    return report


def synthetic_orphan_edge(run_id: str = "run-test") -> DependencyEdge:
    """Test helper: edge pointing at a non-existent node."""

    missing_id = stable_id("repo_artifact", "missing.py", "deadbeef")
    return DependencyEdge(
        edge_id=stable_id("dep_edge", "contains", missing_id, "orphan-target"),
        from_id=missing_id,
        to_id=stable_id("symbol", "missing.py", "orphan-target"),
        edge_type="contains",
        source_path="missing.py",
        confidence="high",
        inferred=False,
        from_table="repo_artifact",
        to_table="code_symbol",
    )
