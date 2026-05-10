"""Unit tests for tombstone handling in the apply pipeline (#2074).

These tests cover:

* Tombstone-only field set (no hard delete).
* ``tombstoned_at`` is real ISO8601 UTC produced via an injected
  :class:`core.utils.clock.ClockProvider` (no ``datetime.now`` call).
* Determinism: a :class:`FixedClock` produces the same timestamp.
* The default in-memory adapter exposes no delete API.
* Reconcile ``tombstone_candidate`` actions map to apply tombstone
  operations against the in-memory adapter, with the tombstone payload
  carrying every required field.
* Tombstone reason defaults to ``record_removed_from_snapshot``.
* Per-table tombstoning works for stale records of the relevant
  context tables (doc_page, doc_chunk, code_symbol, dependency_edge).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pytest

from core.utils.clock import FixedClock
from tools.surrealdb.context_importer import (
    ADAPTER_KIND_IN_MEMORY,
    APPLY_MODE_LOCAL_DEV,
    APPLY_OP_TOMBSTONE,
    InMemoryContextApplyAdapter,
    TOMBSTONE_FIELD_AT,
    TOMBSTONE_FIELD_FLAG,
    TOMBSTONE_FIELD_LAST_SEEN_RUN_ID,
    TOMBSTONE_FIELD_REASON,
    TOMBSTONE_FIELD_SUPERSEDED_BY,
    TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT,
    TOMBSTONE_REQUIRED_FIELDS,
    ApplyAdapterError,
    build_import_plan,
    execute_context_apply,
    load_config,
    load_existing_records,
    reconcile_import_plan,
)


# ---------------------------------------------------------------------------
# Local helpers (mirror style of test_context_import_apply.py)
# ---------------------------------------------------------------------------


def _write_valid_artifacts(tmp_path: Path, *, run_id: str = "run-tomb-1") -> None:
    rows: dict[str, list[dict[str, Any]]] = {
        "repo_artifacts.jsonl": [
            {
                "schema_version": "context-indexer/v0",
                "run_id": run_id,
                "artifact_id": "art-1",
                "source_path": "docs/example.md",
                "file_type": "markdown",
                "raw_sha256": "a" * 64,
                "normalized_sha256": "a" * 64,
                "source_hash": "a" * 64,
                "integrity_algo": "sha256",
                "size_bytes": 12,
                "sensitivity": "public",
            }
        ],
        "doc_pages.jsonl": [
            {
                "schema_version": "context-indexer/v0",
                "run_id": run_id,
                "page_id": "page-example",
                "source_path": "docs/example.md",
                "source_hash": "a" * 64,
                "title": "Example",
            }
        ],
        "doc_sections.jsonl": [],
        "doc_chunks.jsonl": [],
        "code_symbols.jsonl": [],
        "import_references.jsonl": [],
        "test_cases.jsonl": [],
        "config_references.jsonl": [],
        "doc_code_links.jsonl": [],
        "dependency_edges.jsonl": [],
    }
    for name, items in rows.items():
        path = tmp_path / name
        with path.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item, sort_keys=True) + "\n")


def _write_existing(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, sort_keys=True), encoding="utf-8")


def _write_local_dev_config(path: Path) -> Path:
    from tools.surrealdb.context_importer import (
        ALLOWED_CONTEXT_IMPORT_TABLES,
        FORBIDDEN_CONTEXT_IMPORT_TABLES,
    )

    forbidden = sorted(FORBIDDEN_CONTEXT_IMPORT_TABLES)
    allowed = sorted(ALLOWED_CONTEXT_IMPORT_TABLES)
    body = (
        "schema_version: context-import-local/v0\n"
        "surreal_url: ws://127.0.0.1:8000/rpc\n"
        "namespace: cdb_ctx\n"
        "database: context\n"
        "auth_mode: none\n"
        "timeout: 5\n"
        "allow_apply_default: false\n"
        "allowed_tables:\n"
        + "".join(f"  - {t}\n" for t in allowed)
        + "forbidden_tables:\n"
        + "".join(f"  - {t}\n" for t in forbidden)
    )
    path.write_text(body, encoding="utf-8")
    return path


def _stale_existing(table: str, record_id: str) -> dict[str, Any]:
    return {
        "table": table,
        "record_id": record_id,
        "payload_hash": "e" * 64,
        "schema_version": "context-importer/v0",
    }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tombstone_field_set_is_pinned() -> None:
    assert TOMBSTONE_FIELD_FLAG == "tombstoned"
    assert TOMBSTONE_FIELD_AT == "tombstoned_at"
    assert TOMBSTONE_FIELD_REASON == "tombstone_reason"
    assert TOMBSTONE_FIELD_LAST_SEEN_RUN_ID == "last_seen_run_id"
    assert TOMBSTONE_FIELD_SUPERSEDED_BY == "superseded_by"
    assert TOMBSTONE_REQUIRED_FIELDS == frozenset(
        {
            "tombstoned",
            "tombstoned_at",
            "tombstone_reason",
            "last_seen_run_id",
            "superseded_by",
        }
    )


@pytest.mark.unit
def test_tombstone_default_reason_is_record_removed_from_snapshot() -> None:
    assert TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT == "record_removed_from_snapshot"


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_in_memory_adapter_has_no_hard_delete() -> None:
    """#2074: tombstone-only; no hard delete API exists."""

    adapter = InMemoryContextApplyAdapter()
    assert not hasattr(adapter, "delete")
    assert not hasattr(adapter, "apply_delete")
    assert not hasattr(adapter, "hard_delete")


@pytest.mark.unit
def test_in_memory_adapter_rejects_tombstone_missing_fields() -> None:
    adapter = InMemoryContextApplyAdapter()
    with pytest.raises(ApplyAdapterError):
        adapter.apply_tombstone("doc_page", "doc_page:x", {"tombstoned": True})


@pytest.mark.unit
def test_in_memory_adapter_rejects_tombstone_with_flag_false() -> None:
    adapter = InMemoryContextApplyAdapter()
    payload = {
        TOMBSTONE_FIELD_FLAG: False,
        TOMBSTONE_FIELD_AT: "2026-01-01T00:00:00Z",
        TOMBSTONE_FIELD_REASON: "record_removed_from_snapshot",
        TOMBSTONE_FIELD_LAST_SEEN_RUN_ID: None,
        TOMBSTONE_FIELD_SUPERSEDED_BY: None,
    }
    with pytest.raises(ApplyAdapterError):
        adapter.apply_tombstone("doc_page", "doc_page:x", payload)


@pytest.mark.unit
def test_in_memory_adapter_keeps_record_after_tombstone() -> None:
    """Tombstone never deletes; the record stays and gains tombstone fields."""

    adapter = InMemoryContextApplyAdapter()
    adapter.apply_create(
        "doc_page", "doc_page:keep", {"page_id": "keep", "title": "Old"}
    )
    adapter.apply_tombstone(
        "doc_page",
        "doc_page:keep",
        {
            TOMBSTONE_FIELD_FLAG: True,
            TOMBSTONE_FIELD_AT: "2026-01-01T12:00:00Z",
            TOMBSTONE_FIELD_REASON: TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT,
            TOMBSTONE_FIELD_LAST_SEEN_RUN_ID: "run-prev",
            TOMBSTONE_FIELD_SUPERSEDED_BY: None,
        },
    )
    record = adapter.records["doc_page:keep"]
    assert record["title"] == "Old"  # original payload preserved
    assert record[TOMBSTONE_FIELD_FLAG] is True
    assert record[TOMBSTONE_FIELD_AT] == "2026-01-01T12:00:00Z"
    assert record[TOMBSTONE_FIELD_REASON] == TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT


# ---------------------------------------------------------------------------
# Apply: tombstone candidates from reconcile
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_stale_doc_page_is_tombstoned_with_real_iso8601(tmp_path: Path) -> None:
    """tombstoned_at must be real ISO8601 UTC, not a sentinel marker."""

    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing("doc_page", "doc_page:stale")])

    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    fixed = datetime(2026, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
    adapter = InMemoryContextApplyAdapter()
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(fixed),
    )

    tomb_results = [r for r in report.results if r.op == APPLY_OP_TOMBSTONE]
    assert len(tomb_results) == 1
    result = tomb_results[0]
    assert result.status == "applied"
    assert result.record_id == "doc_page:stale"
    # ISO8601 UTC with explicit Z, no placeholder.
    assert result.tombstoned_at == "2026-01-15T09:30:00Z"
    assert "<run-derived>" not in (result.tombstoned_at or "")

    # The adapter saw the tombstone with the full required field set.
    op_kind, table, record_id, payload = adapter.operations[-1]
    assert op_kind == APPLY_OP_TOMBSTONE
    assert table == "doc_page"
    assert record_id == "doc_page:stale"
    assert TOMBSTONE_REQUIRED_FIELDS.issubset(payload.keys())
    assert payload[TOMBSTONE_FIELD_FLAG] is True
    assert payload[TOMBSTONE_FIELD_AT] == "2026-01-15T09:30:00Z"
    assert (
        payload[TOMBSTONE_FIELD_REASON] == TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT
    )


@pytest.mark.unit
def test_tombstoned_at_is_deterministic_with_fixed_clock(tmp_path: Path) -> None:
    """Two apply runs with the same FixedClock produce the same tombstoned_at."""

    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing("doc_page", "doc_page:stale")])
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    fixed = datetime(2026, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

    def _ts() -> str | None:
        report = execute_context_apply(
            reconcile_report=reconcile,
            config=config,
            run_id="run-tomb-1",
            apply_mode=APPLY_MODE_LOCAL_DEV,
            adapter=InMemoryContextApplyAdapter(),
            clock=FixedClock(fixed),
        )
        tomb = [r for r in report.results if r.op == APPLY_OP_TOMBSTONE][0]
        return tomb.tombstoned_at

    assert _ts() == _ts() == "2026-01-15T09:30:00Z"


@pytest.mark.unit
def test_tombstoned_at_changes_when_clock_changes(tmp_path: Path) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing("doc_page", "doc_page:stale")])
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    def _ts(at: datetime) -> str | None:
        report = execute_context_apply(
            reconcile_report=reconcile,
            config=config,
            run_id="run-tomb-1",
            apply_mode=APPLY_MODE_LOCAL_DEV,
            adapter=InMemoryContextApplyAdapter(),
            clock=FixedClock(at),
        )
        return [r for r in report.results if r.op == APPLY_OP_TOMBSTONE][0].tombstoned_at

    a = _ts(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    b = _ts(datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc))
    assert a == "2026-01-01T00:00:00Z"
    assert b == "2026-06-30T23:59:59Z"
    assert a != b


@pytest.mark.unit
@pytest.mark.parametrize(
    ("table", "record_id"),
    [
        ("doc_page", "doc_page:stale-page"),
        ("doc_chunk", "doc_chunk:stale-chunk"),
        ("code_symbol", "code_symbol:stale-symbol"),
        ("dependency_edge", "dependency_edge:stale-edge"),
    ],
)
def test_tombstone_works_for_each_context_table(
    table: str, record_id: str, tmp_path: Path
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing(table, record_id)])
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    adapter = InMemoryContextApplyAdapter()
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    tomb = [r for r in report.results if r.op == APPLY_OP_TOMBSTONE]
    assert len(tomb) == 1
    assert tomb[0].record_id == record_id
    assert tomb[0].status == "applied"
    # Adapter records persist (no hard delete).
    assert record_id in adapter.records
    assert adapter.records[record_id][TOMBSTONE_FIELD_FLAG] is True


@pytest.mark.unit
def test_tombstone_payload_default_reason_is_record_removed_from_snapshot(
    tmp_path: Path,
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing("doc_page", "doc_page:stale")])
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    adapter = InMemoryContextApplyAdapter()
    execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    op_kind, _, _, payload = adapter.operations[-1]
    assert op_kind == APPLY_OP_TOMBSTONE
    assert payload[TOMBSTONE_FIELD_REASON] == TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT


@pytest.mark.unit
def test_tombstone_payload_carries_run_id(tmp_path: Path) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing("doc_page", "doc_page:stale")])
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    adapter = InMemoryContextApplyAdapter()
    execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    _, _, _, payload = adapter.operations[-1]
    assert payload["run_id"] == "run-tomb-1"
    # superseded_by is intentionally None in v0; no chain replacement support.
    assert payload[TOMBSTONE_FIELD_SUPERSEDED_BY] is None


@pytest.mark.unit
def test_apply_pipeline_uses_injected_clock_not_datetime_now(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression guard: the apply path must not call datetime.now()."""

    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(existing, [_stale_existing("doc_page", "doc_page:stale")])
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    # If anything in the apply path called datetime.now()/utcnow(), this
    # would explode. The injected FixedClock produces all timestamps.
    from tools.surrealdb import context_importer as ci

    class _ExplodingDatetime:
        @classmethod
        def now(cls, *a, **kw):  # pragma: no cover - guard
            raise AssertionError("apply must use injected clock, not datetime.now()")

        @classmethod
        def utcnow(cls):  # pragma: no cover - guard
            raise AssertionError("apply must use injected clock, not datetime.utcnow()")

    monkeypatch.setattr(ci, "datetime", _ExplodingDatetime)

    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=InMemoryContextApplyAdapter(),
        clock=FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )
    tomb = [r for r in report.results if r.op == APPLY_OP_TOMBSTONE][0]
    assert tomb.tombstoned_at == "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Prior-field retention on tombstone (PR #2248 P2 fix; #2073/#2074 contract
# §5.3: "Der Adapter ueberschreibt das Original-Record nicht; es bleibt
# erhalten und bekommt die Tombstone-Felder dazu.").
# ---------------------------------------------------------------------------


def _stale_existing_with_payload(
    table: str, record_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """An existing-records fixture entry that carries a ``payload`` object.

    The loader uses the object payload to compute the hash and to retain
    the prior record fields for downstream tombstone preservation.
    """

    return {
        "table": table,
        "record_id": record_id,
        "payload": payload,
        "schema_version": "context-importer/v0",
    }


@pytest.mark.unit
def test_tombstone_preserves_prior_record_fields_from_existing_records(
    tmp_path: Path,
) -> None:
    """A tombstoned record must retain its original fields after apply.

    Regression test for PR #2248 (thread ``PRRT_kwDOQUkXUM5_D1__``):
    when the only source of the prior record is the ``--existing-records``
    fixture (the in-memory adapter has no previous ``apply_create`` for
    that id), the tombstone payload must still carry the original record
    fields under the tombstone metadata.
    """

    _write_valid_artifacts(tmp_path, run_id="run-tomb-keep")
    existing_path = tmp_path / "existing.json"
    prior_payload = {
        "page_id": "stale",
        "title": "Original Title",
        "source_path": "docs/stale.md",
        "source_hash": "b" * 64,
    }
    _write_existing(
        existing_path,
        [_stale_existing_with_payload("doc_page", "doc_page:stale", prior_payload)],
    )

    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-keep")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing_path))

    adapter = InMemoryContextApplyAdapter()
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-keep",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 1, 15, 9, 30, 0, tzinfo=timezone.utc)),
    )

    # The tombstone op was emitted and applied.
    tomb_results = [r for r in report.results if r.op == APPLY_OP_TOMBSTONE]
    assert len(tomb_results) == 1
    assert tomb_results[0].status == "applied"
    assert tomb_results[0].record_id == "doc_page:stale"

    # The adapter received a payload that carries every prior field.
    op_kind, table, record_id, payload = adapter.operations[-1]
    assert op_kind == APPLY_OP_TOMBSTONE
    assert table == "doc_page"
    assert record_id == "doc_page:stale"
    for key, value in prior_payload.items():
        assert payload[key] == value, f"prior field {key!r} must be preserved"

    # Tombstone metadata is present and overlays prior fields if any
    # collide. The required field set is a strict subset of the keys.
    assert TOMBSTONE_REQUIRED_FIELDS.issubset(payload.keys())
    assert payload[TOMBSTONE_FIELD_FLAG] is True
    assert payload[TOMBSTONE_FIELD_AT] == "2026-01-15T09:30:00Z"
    assert payload[TOMBSTONE_FIELD_REASON] == TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT

    # And the in-memory record reflects the union: prior + tombstone.
    record = adapter.records["doc_page:stale"]
    for key, value in prior_payload.items():
        assert record[key] == value
    assert record[TOMBSTONE_FIELD_FLAG] is True
    assert record[TOMBSTONE_FIELD_AT] == "2026-01-15T09:30:00Z"


@pytest.mark.unit
def test_tombstone_metadata_overlays_colliding_prior_fields(tmp_path: Path) -> None:
    """Tombstone metadata + identity keys win over colliding prior fields.

    A prior record that itself happens to contain a ``tombstoned``,
    ``tombstoned_at``, ``run_id`` or ``payload_hash`` key must not be
    able to override the tombstone metadata produced by the apply
    pipeline. The pipeline is the single source of truth for those keys.
    """

    _write_valid_artifacts(tmp_path, run_id="run-tomb-overlay")
    existing_path = tmp_path / "existing.json"
    prior_payload = {
        "page_id": "stale",
        "title": "Original Title",
        "source_path": "docs/stale.md",
        "source_hash": "c" * 64,
        # Adversarial collisions: the tombstone metadata + identity
        # fields must overlay these.
        TOMBSTONE_FIELD_FLAG: False,
        TOMBSTONE_FIELD_AT: "1999-01-01T00:00:00Z",
        TOMBSTONE_FIELD_REASON: "attacker_controlled",
        "run_id": "attacker-run",
        "payload_hash": "0" * 64,
    }
    _write_existing(
        existing_path,
        [_stale_existing_with_payload("doc_page", "doc_page:stale", prior_payload)],
    )

    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-overlay")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing_path))

    adapter = InMemoryContextApplyAdapter()
    execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-overlay",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 2, 2, 12, 0, 0, tzinfo=timezone.utc)),
    )

    _, _, _, payload = adapter.operations[-1]
    # Pipeline-controlled keys must reflect the apply, not the prior values.
    assert payload[TOMBSTONE_FIELD_FLAG] is True
    assert payload[TOMBSTONE_FIELD_AT] == "2026-02-02T12:00:00Z"
    assert payload[TOMBSTONE_FIELD_REASON] == TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT
    assert payload["run_id"] == "run-tomb-overlay"
    # Existing payload hash from the fixture, not the colliding prior key.
    assert payload["payload_hash"] != "0" * 64
    # Non-colliding prior fields are preserved verbatim.
    assert payload["page_id"] == "stale"
    assert payload["title"] == "Original Title"
    assert payload["source_path"] == "docs/stale.md"


@pytest.mark.unit
def test_tombstone_without_prior_payload_is_minimal_deterministic(
    tmp_path: Path,
) -> None:
    """Hash-only existing-records entries keep the minimal tombstone shape.

    When the existing record provides only ``payload_hash`` (no
    ``payload`` object), there are no prior fields to preserve, so the
    tombstone payload remains the deterministic minimal shape: tombstone
    metadata + identity keys + the carried-over ``payload_hash``.
    """

    _write_valid_artifacts(tmp_path, run_id="run-tomb-min")
    existing_path = tmp_path / "existing.json"
    # Hash-only entry; no ``payload`` dict provided.
    hash_only_entry = {
        "table": "doc_page",
        "record_id": "doc_page:stale",
        "payload_hash": "e" * 64,
        "schema_version": "context-importer/v0",
    }
    _write_existing(existing_path, [hash_only_entry])

    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-min")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing_path))

    adapter = InMemoryContextApplyAdapter()
    execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-tomb-min",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 3, 3, 0, 0, 0, tzinfo=timezone.utc)),
    )

    _, _, _, payload = adapter.operations[-1]
    expected_keys = {
        TOMBSTONE_FIELD_FLAG,
        TOMBSTONE_FIELD_AT,
        TOMBSTONE_FIELD_REASON,
        TOMBSTONE_FIELD_LAST_SEEN_RUN_ID,
        TOMBSTONE_FIELD_SUPERSEDED_BY,
        "table",
        "record_id",
        "run_id",
        "payload_hash",
    }
    assert set(payload.keys()) == expected_keys
    assert payload["payload_hash"] == "e" * 64


@pytest.mark.unit
def test_tombstone_does_not_leak_prior_payload_into_report_or_results(
    tmp_path: Path,
) -> None:
    """Prior record fields must not appear in dry-run or apply reports.

    The retention is delivered to the adapter only. Reports and result
    detail strings must not serialize prior payload values, otherwise a
    sensitive-shaped field name in a fixture would leak into reports.
    """

    _write_valid_artifacts(tmp_path, run_id="run-tomb-leak")
    existing_path = tmp_path / "existing.json"
    sentinel = "SECRET-SENTINEL-VALUE-MUST-NOT-LEAK"
    prior_payload = {
        "page_id": "stale",
        "title": "Public Title",
        "source_path": "docs/stale.md",
        "source_hash": "d" * 64,
        # A value that, if leaked into any serialized report or result,
        # would make this test fail.
        "internal_note": sentinel,
    }
    _write_existing(
        existing_path,
        [_stale_existing_with_payload("doc_page", "doc_page:stale", prior_payload)],
    )

    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))
    plan = build_import_plan(tmp_path, "run-tomb-leak")
    reconcile_report = reconcile_import_plan(
        plan, load_existing_records(existing_path)
    )

    # Dry-run reconcile report must not contain the sentinel.
    reconcile_payload = json.dumps(reconcile_report.to_payload(), sort_keys=True)
    assert sentinel not in reconcile_payload, (
        "reconcile report must not serialize prior record fields"
    )

    adapter = InMemoryContextApplyAdapter()
    apply_report = execute_context_apply(
        reconcile_report=reconcile_report,
        config=config,
        run_id="run-tomb-leak",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 4, 4, 0, 0, 0, tzinfo=timezone.utc)),
    )

    # Apply report (including operations + results) must not contain the
    # sentinel either.
    apply_payload = json.dumps(apply_report.to_payload(), sort_keys=True)
    assert sentinel not in apply_payload, (
        "apply report must not serialize prior record fields"
    )

    # But the adapter must have received it (retention contract).
    _, _, _, payload = adapter.operations[-1]
    assert payload["internal_note"] == sentinel
    # Sanity: the in-memory adapter is the one that ran.
    assert apply_report.adapter == ADAPTER_KIND_IN_MEMORY
