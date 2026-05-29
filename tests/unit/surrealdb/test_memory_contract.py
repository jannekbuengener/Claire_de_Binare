"""Unit tests for memory_contract — #2606 Memory Reality Slice 2.

No DB. No MCP. No side effects.

Covers:
    - ID determinism and stability
    - ID sensitivity: changes to identity fields (scope, namespace,
      memory_type, created_by, content, source_refs) change the ID
    - ID insensitivity: confidence, ttl, evidence_refs do NOT affect the ID
    - content_hash determinism and strip behavior
    - source_refs fingerprint: order-insensitive and deduplicating
    - Valid record passes validation and receives memory_id
    - Missing required fields (parametrized)
    - Empty evidence_refs / source_refs rejected
    - Confidence out of [0.0, 1.0] rejected
    - TTL contract: ttl=0 OK without expires_at; ttl>0 requires expires_at after created_at
    - stale_after: valid ints pass, negatives rejected
    - superseded_by: non-empty string passes, empty/whitespace rejected
    - Unknown memory_type rejected
    - Unknown extra field in strict mode rejected
    - Unknown extra field in non-strict mode allowed
    - memory_id mismatch in record rejected
    - validate_memory_id_matches_record: correct passes, wrong raises, missing raises
    - SCHEMA_VERSION and CANONICAL_MEMORY_TYPES constants
"""

from __future__ import annotations

import uuid

import pytest

from tools.surrealdb.memory_contract import (
    CANONICAL_MEMORY_TYPES,
    SCHEMA_VERSION,
    MemoryContractError,
    compute_content_hash,
    compute_source_refs_fingerprint,
    generate_memory_id,
    validate_memory_id_matches_record,
    validate_memory_record,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_record(**overrides) -> dict:
    """Return a minimal valid memory record dict. Callers may override any field."""
    base: dict = {
        "scope": "agent:TEST/cursor",
        "namespace": "session",
        "memory_type": "working_memory",
        "content": "Test memory content for slice 2",
        "source_refs": ["docs/AGENTS.md@abc123"],
        "evidence_refs": ["ev-001"],
        "confidence": 0.9,
        "ttl": 3600,
        "expires_at": "2026-05-30T00:00:00+00:00",
        "created_by": "cursor-agent-v1",
        "created_at": "2026-05-29T04:00:00+00:00",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ID determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_memory_id_deterministic() -> None:
    """Same inputs always produce the same memory_id (idempotency)."""
    id1 = generate_memory_id(
        "s:A", "ns", "working_memory", "agent-1", "content", ["ref1"]
    )
    id2 = generate_memory_id(
        "s:A", "ns", "working_memory", "agent-1", "content", ["ref1"]
    )
    assert id1 == id2


@pytest.mark.unit
def test_generate_memory_id_is_uuidv5() -> None:
    """Generated memory_id is a valid UUIDv5 string."""
    mid = generate_memory_id("s", "n", "semantic_memory", "agent", "c", ["r"])
    parsed = uuid.UUID(mid)
    assert parsed.version == 5


@pytest.mark.unit
def test_generate_memory_id_stable_across_calls() -> None:
    """Multiple calls with identical arguments return the same ID."""
    kwargs: dict = dict(
        scope="stable:scope",
        namespace="prod",
        memory_type="risk_memory",
        created_by="risk-agent-v2",
        content="Important risk memory",
        source_refs=["risk/risk_policy.md@v1"],
    )
    ids = [generate_memory_id(**kwargs) for _ in range(5)]
    assert len(set(ids)) == 1, "All calls should return the same ID"


# ---------------------------------------------------------------------------
# ID sensitivity — any identity field change produces a different ID
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "field, value",
    [
        ("scope", "scope:B"),
        ("namespace", "different_ns"),
        ("memory_type", "semantic_memory"),
        ("created_by", "different-agent"),
        ("content", "different content string"),
        ("source_refs", ["ref2"]),
    ],
)
def test_memory_id_sensitive_to_identity_field(field: str, value) -> None:
    """Changing any identity field produces a different memory_id."""
    base_kwargs: dict = dict(
        scope="scope:A",
        namespace="ns",
        memory_type="working_memory",
        created_by="agent-1",
        content="content",
        source_refs=["ref1"],
    )
    id_base = generate_memory_id(**base_kwargs)
    changed = {**base_kwargs, field: value}
    id_changed = generate_memory_id(**changed)
    assert id_base != id_changed, f"ID should differ when {field!r} changes"


# ---------------------------------------------------------------------------
# ID insensitivity — non-identity metadata does not affect generate_memory_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_memory_id_insensitive_to_created_at_field() -> None:
    """created_at is NOT part of the ID name string; never passed to generate_memory_id."""
    id1 = generate_memory_id("s", "n", "working_memory", "a", "content", ["r"])
    id2 = generate_memory_id("s", "n", "working_memory", "a", "content", ["r"])
    assert id1 == id2


@pytest.mark.unit
def test_memory_id_insensitive_to_ttl_and_confidence() -> None:
    """Confidence and ttl are not identity fields; validate_memory_record produces
    the same memory_id for records that differ only in those fields."""
    rec_a = _valid_record(
        confidence=0.5, ttl=100, expires_at="2026-06-01T00:00:00+00:00"
    )
    rec_b = _valid_record(
        confidence=0.99, ttl=7200, expires_at="2026-06-01T00:00:00+00:00"
    )
    out_a = validate_memory_record(rec_a)
    out_b = validate_memory_record(rec_b)
    assert out_a["memory_id"] == out_b["memory_id"]


@pytest.mark.unit
def test_memory_id_insensitive_to_evidence_refs() -> None:
    """evidence_refs is not part of the ID; different evidence_refs produce the same ID."""
    rec_a = _valid_record(evidence_refs=["ev-001"])
    rec_b = _valid_record(evidence_refs=["ev-001", "ev-002", "ev-003"])
    out_a = validate_memory_record(rec_a)
    out_b = validate_memory_record(rec_b)
    assert out_a["memory_id"] == out_b["memory_id"]


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compute_content_hash_deterministic() -> None:
    h1 = compute_content_hash("hello")
    h2 = compute_content_hash("hello")
    assert h1 == h2


@pytest.mark.unit
def test_compute_content_hash_strip_whitespace() -> None:
    """Content is stripped before hashing so leading/trailing space is ignored."""
    assert compute_content_hash("  hello  ") == compute_content_hash("hello")
    assert compute_content_hash("\thello\n") == compute_content_hash("hello")


@pytest.mark.unit
def test_compute_content_hash_length() -> None:
    """SHA256 hex digest is exactly 64 characters."""
    assert len(compute_content_hash("anything")) == 64


@pytest.mark.unit
def test_compute_content_hash_sensitive_to_content() -> None:
    assert compute_content_hash("content-A") != compute_content_hash("content-B")


# ---------------------------------------------------------------------------
# compute_source_refs_fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_source_refs_fingerprint_order_insensitive() -> None:
    """Source refs are sorted before hashing — list order does not matter."""
    f1 = compute_source_refs_fingerprint(["b", "a"])
    f2 = compute_source_refs_fingerprint(["a", "b"])
    assert f1 == f2


@pytest.mark.unit
def test_source_refs_fingerprint_deduplicates() -> None:
    """Duplicate entries are collapsed before hashing."""
    f1 = compute_source_refs_fingerprint(["a", "a", "b"])
    f2 = compute_source_refs_fingerprint(["a", "b"])
    assert f1 == f2


@pytest.mark.unit
def test_source_refs_fingerprint_deterministic() -> None:
    f1 = compute_source_refs_fingerprint(["ref-x", "ref-y"])
    f2 = compute_source_refs_fingerprint(["ref-x", "ref-y"])
    assert f1 == f2


@pytest.mark.unit
def test_source_refs_fingerprint_sensitive_to_content() -> None:
    f1 = compute_source_refs_fingerprint(["ref-A"])
    f2 = compute_source_refs_fingerprint(["ref-B"])
    assert f1 != f2


@pytest.mark.unit
def test_source_refs_fingerprint_length() -> None:
    assert len(compute_source_refs_fingerprint(["x"])) == 64


# ---------------------------------------------------------------------------
# validate_memory_record — valid record
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_valid_adds_memory_id() -> None:
    """A valid record without memory_id gets one computed and attached."""
    rec = _valid_record()
    out = validate_memory_record(rec)
    assert "memory_id" in out
    mid = out["memory_id"]
    assert len(uuid.UUID(mid).hex) == 32  # valid UUID


@pytest.mark.unit
def test_validate_memory_record_normalizes_memory_type_case() -> None:
    """memory_type is lowercased in the returned record."""
    rec = _valid_record(memory_type="Working_Memory")
    out = validate_memory_record(rec)
    assert out["memory_type"] == "working_memory"


@pytest.mark.unit
def test_validate_memory_record_valid_preserves_supplied_memory_id() -> None:
    """A correct memory_id in the record passes validation unchanged."""
    rec = _valid_record()
    out_first = validate_memory_record(rec)
    mid = out_first["memory_id"]
    rec_with_id = _valid_record(memory_id=mid)
    out = validate_memory_record(rec_with_id)
    assert out["memory_id"] == mid


@pytest.mark.unit
def test_validate_memory_record_returns_all_input_fields() -> None:
    """Returned record preserves all input fields plus adds memory_id."""
    rec = _valid_record(comment="test comment")
    out = validate_memory_record(rec)
    assert out["comment"] == "test comment"
    assert out["scope"] == rec["scope"]
    assert out["evidence_refs"] == rec["evidence_refs"]


# ---------------------------------------------------------------------------
# Missing required fields (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_field",
    [
        "scope",
        "namespace",
        "memory_type",
        "content",
        "source_refs",
        "evidence_refs",
        "confidence",
        "ttl",
        "created_by",
        "created_at",
    ],
)
def test_validate_memory_record_missing_required_field(missing_field: str) -> None:
    """Removing any required field raises MemoryContractError."""
    rec = _valid_record()
    del rec[missing_field]
    with pytest.raises(MemoryContractError, match=missing_field):
        validate_memory_record(rec)


# ---------------------------------------------------------------------------
# evidence_refs and source_refs validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_empty_evidence_refs_rejected() -> None:
    rec = _valid_record(evidence_refs=[])
    with pytest.raises(MemoryContractError, match="evidence_refs"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_empty_source_refs_rejected() -> None:
    rec = _valid_record(source_refs=[])
    with pytest.raises(MemoryContractError, match="source_refs"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_evidence_refs_not_list_rejected() -> None:
    rec = _valid_record(evidence_refs="ev-001")
    with pytest.raises(MemoryContractError, match="evidence_refs"):
        validate_memory_record(rec)


# ---------------------------------------------------------------------------
# Confidence validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("bad_confidence", [-0.001, 1.001, 2.0, -1.0])
def test_validate_memory_record_bad_confidence_rejected(bad_confidence: float) -> None:
    rec = _valid_record(confidence=bad_confidence)
    with pytest.raises(MemoryContractError, match="confidence"):
        validate_memory_record(rec)


@pytest.mark.unit
@pytest.mark.parametrize("ok_confidence", [0.0, 0.5, 1.0, 0.123])
def test_validate_memory_record_confidence_edge_values_accepted(
    ok_confidence: float,
) -> None:
    rec = _valid_record(confidence=ok_confidence)
    out = validate_memory_record(rec)
    assert out["confidence"] == ok_confidence


# ---------------------------------------------------------------------------
# TTL contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_ttl_zero_without_expires_at_ok() -> None:
    """ttl=0 means no expiry; expires_at is not required."""
    rec = _valid_record(ttl=0)
    rec.pop("expires_at", None)
    out = validate_memory_record(rec)
    assert out["ttl"] == 0


@pytest.mark.unit
def test_validate_memory_record_ttl_positive_without_expires_at_rejected() -> None:
    """ttl > 0 without expires_at violates the contract."""
    rec = _valid_record(ttl=3600)
    del rec["expires_at"]
    with pytest.raises(MemoryContractError, match="expires_at"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_ttl_positive_expires_at_before_created_at_rejected() -> (
    None
):
    """expires_at must be strictly after created_at when ttl > 0."""
    rec = _valid_record(
        ttl=3600,
        created_at="2026-05-29T10:00:00+00:00",
        expires_at="2026-05-29T09:00:00+00:00",
    )
    with pytest.raises(MemoryContractError, match="expires_at"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_ttl_positive_expires_at_equal_created_at_rejected() -> (
    None
):
    """expires_at must be strictly after created_at (equal is not enough)."""
    rec = _valid_record(
        ttl=1,
        created_at="2026-05-29T10:00:00+00:00",
        expires_at="2026-05-29T10:00:00+00:00",
    )
    with pytest.raises(MemoryContractError, match="expires_at"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_ttl_negative_rejected() -> None:
    rec = _valid_record(ttl=-1)
    with pytest.raises(MemoryContractError, match="ttl"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_ttl_positive_valid() -> None:
    """ttl > 0 with expires_at after created_at passes."""
    rec = _valid_record(
        ttl=7200,
        created_at="2026-05-29T08:00:00+00:00",
        expires_at="2026-05-29T10:00:00+00:00",
    )
    out = validate_memory_record(rec)
    assert out["ttl"] == 7200


# ---------------------------------------------------------------------------
# stale_after
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_stale_after_valid() -> None:
    rec = _valid_record(stale_after=7200)
    out = validate_memory_record(rec)
    assert out["stale_after"] == 7200


@pytest.mark.unit
def test_validate_memory_record_stale_after_zero_ok() -> None:
    rec = _valid_record(stale_after=0)
    out = validate_memory_record(rec)
    assert out["stale_after"] == 0


@pytest.mark.unit
def test_validate_memory_record_stale_after_negative_rejected() -> None:
    rec = _valid_record(stale_after=-1)
    with pytest.raises(MemoryContractError, match="stale_after"):
        validate_memory_record(rec)


# ---------------------------------------------------------------------------
# superseded_by
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_superseded_by_valid() -> None:
    rec = _valid_record(superseded_by="mem-prev-id-001")
    out = validate_memory_record(rec)
    assert out["superseded_by"] == "mem-prev-id-001"


@pytest.mark.unit
def test_validate_memory_record_superseded_by_empty_string_rejected() -> None:
    """superseded_by must be non-empty if present."""
    rec = _valid_record(superseded_by="")
    with pytest.raises(MemoryContractError, match="superseded_by"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_superseded_by_whitespace_rejected() -> None:
    rec = _valid_record(superseded_by="   ")
    with pytest.raises(MemoryContractError, match="superseded_by"):
        validate_memory_record(rec)


# ---------------------------------------------------------------------------
# Unknown memory_type
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_unknown_memory_type_rejected() -> None:
    rec = _valid_record(memory_type="unknown_memory")
    with pytest.raises(MemoryContractError, match="memory_type"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_generate_memory_id_unknown_memory_type_rejected() -> None:
    with pytest.raises(MemoryContractError, match="memory_type"):
        generate_memory_id("s", "n", "bad_type", "a", "c", ["r"])


@pytest.mark.unit
@pytest.mark.parametrize(
    "memory_type",
    list(CANONICAL_MEMORY_TYPES),
)
def test_all_canonical_memory_types_accepted(memory_type: str) -> None:
    """All six canonical memory types pass validation."""
    rec = _valid_record(memory_type=memory_type)
    out = validate_memory_record(rec)
    assert out["memory_type"] == memory_type


# ---------------------------------------------------------------------------
# Unknown extra fields (strict / non-strict)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_unknown_field_strict_rejected() -> None:
    """strict=True rejects records with fields not in the known field set."""
    rec = _valid_record(totally_unknown_field_xyz="should_fail")
    with pytest.raises(MemoryContractError, match="unknown fields"):
        validate_memory_record(rec, strict=True)


@pytest.mark.unit
def test_validate_memory_record_unknown_field_non_strict_allowed() -> None:
    """strict=False permits extra unknown fields."""
    rec = _valid_record(totally_unknown_field_xyz="allowed")
    out = validate_memory_record(rec, strict=False)
    assert "memory_id" in out


# ---------------------------------------------------------------------------
# memory_id mismatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_record_memory_id_mismatch_rejected() -> None:
    """A record with an incorrect memory_id is rejected."""
    rec = _valid_record(memory_id="00000000-0000-0000-0000-000000000000")
    with pytest.raises(MemoryContractError, match="memory_id mismatch"):
        validate_memory_record(rec)


@pytest.mark.unit
def test_validate_memory_record_wrong_memory_id_rejected() -> None:
    """Any non-matching UUID is rejected."""
    import uuid as _uuid

    rec = _valid_record(memory_id=str(_uuid.uuid4()))
    with pytest.raises(MemoryContractError, match="memory_id mismatch"):
        validate_memory_record(rec)


# ---------------------------------------------------------------------------
# validate_memory_id_matches_record
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_memory_id_matches_record_correct() -> None:
    """A correctly validated record passes the post-validation ID check."""
    rec = _valid_record()
    validated = validate_memory_record(rec)
    validate_memory_id_matches_record(validated)  # must not raise


@pytest.mark.unit
def test_validate_memory_id_matches_record_wrong_id_raises() -> None:
    rec = _valid_record()
    validated = validate_memory_record(rec)
    validated["memory_id"] = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(MemoryContractError, match="memory_id mismatch"):
        validate_memory_id_matches_record(validated)


@pytest.mark.unit
def test_validate_memory_id_matches_record_missing_id_raises() -> None:
    rec = _valid_record()
    with pytest.raises(MemoryContractError, match="missing memory_id"):
        validate_memory_id_matches_record(rec)


# ---------------------------------------------------------------------------
# SCHEMA_VERSION and CANONICAL_MEMORY_TYPES constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_schema_version_constant() -> None:
    assert SCHEMA_VERSION == "memory-contract/v1"


@pytest.mark.unit
def test_canonical_memory_types_count() -> None:
    """Exactly 6 canonical memory types as per scoped-agent-memory-model-v1.md."""
    assert len(CANONICAL_MEMORY_TYPES) == 6


@pytest.mark.unit
def test_canonical_memory_types_names() -> None:
    expected = {
        "working_memory",
        "semantic_memory",
        "episodic_memory",
        "procedural_memory",
        "preference_memory",
        "risk_memory",
    }
    assert CANONICAL_MEMORY_TYPES == expected
