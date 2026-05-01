"""Unit tests for the gated local-dev apply pipeline (#2073).

These tests cover the explicit local apply mode:

* ``--apply`` and ``--apply-mode local-dev`` are both required.
* ``--apply`` on a non-apply subcommand stays hard-blocked.
* The default adapter is the in-memory, no-network adapter.
* Blocking reconcile findings prevent any adapter call.
* Forbidden tables fail closed at the apply boundary.
* Adapter failures are surfaced as ``failed`` results without
  aborting the whole apply pipeline.
* No network socket is opened during apply.
* Determinism: identical input + identical injected clock + identical
  run_id produce byte-identical apply payloads.
"""

from __future__ import annotations

from datetime import datetime
import json
import socket
from pathlib import Path
from typing import Any

import pytest

from core.utils.clock import FixedClock
from tools.surrealdb.context_importer import (
    ADAPTER_KIND_IN_MEMORY,
    ALLOWED_CONTEXT_IMPORT_TABLES,
    APPLY_MODE_LOCAL_DEV,
    APPLY_OP_CREATE,
    APPLY_OP_TOMBSTONE,
    APPLY_OP_UPDATE,
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    EXIT_WRITE_DENIED,
    FORBIDDEN_CONTEXT_IMPORT_TABLES,
    InMemoryContextApplyAdapter,
    LOCAL_DEV_ALLOWED_HOSTS,
    REAL_SURREALDB_ADAPTER_AVAILABLE,
    SCHEMA_VERSION,
    SUPPORTED_APPLY_MODES,
    ApplyAdapterError,
    ContextApplyOperation,
    ContextApplyReport,
    build_import_plan,
    execute_context_apply,
    load_config,
    load_existing_records,
    main,
    reconcile_import_plan,
)


# ---------------------------------------------------------------------------
# Helpers (small, inline; mirror style of test_context_import_reconcile.py)
# ---------------------------------------------------------------------------


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def _write_valid_artifacts(tmp_path: Path, *, run_id: str = "run-apply-1") -> None:
    """Write the minimal JSONL set the importer accepts."""

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


def _write_local_dev_config(
    path: Path,
    *,
    surreal_url: str = "ws://127.0.0.1:8000/rpc",
    namespace: str = "cdb_ctx",
    database: str = "context",
) -> Path:
    forbidden = sorted(FORBIDDEN_CONTEXT_IMPORT_TABLES)
    allowed = sorted(ALLOWED_CONTEXT_IMPORT_TABLES)
    body = (
        "schema_version: context-import-local/v0\n"
        f"surreal_url: {surreal_url}\n"
        f"namespace: {namespace}\n"
        f"database: {database}\n"
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


# ---------------------------------------------------------------------------
# Constants & boundary documentation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_mode_constant_is_local_dev() -> None:
    assert APPLY_MODE_LOCAL_DEV == "local-dev"
    assert APPLY_MODE_LOCAL_DEV in SUPPORTED_APPLY_MODES
    assert SUPPORTED_APPLY_MODES == frozenset({"local-dev"})


@pytest.mark.unit
def test_real_surrealdb_adapter_is_not_available() -> None:
    """#2073: Real SurrealDB adapter is OUT-OF-SCOPE in this slice."""

    assert REAL_SURREALDB_ADAPTER_AVAILABLE is False


@pytest.mark.unit
def test_default_adapter_is_in_memory_and_has_no_delete_method() -> None:
    adapter = InMemoryContextApplyAdapter()
    assert adapter.kind == ADAPTER_KIND_IN_MEMORY
    # No hard-delete API exists at all.
    assert not hasattr(adapter, "apply_delete")
    assert not hasattr(adapter, "delete")


# ---------------------------------------------------------------------------
# CLI gate tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_subcommand_without_apply_flag_is_write_denied(capsys) -> None:
    exit_code = main(["apply"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "--apply" in payload["message"]


@pytest.mark.unit
def test_apply_with_apply_but_no_apply_mode_is_write_denied(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    exit_code = main(
        [
            "apply",
            "--apply",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "apply-mode" in payload["message"]


@pytest.mark.unit
def test_apply_without_config_is_write_denied(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--input-dir",
            str(tmp_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "--config" in payload["message"]


@pytest.mark.unit
def test_apply_without_input_dir_is_write_denied(tmp_path: Path, capsys) -> None:
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "--input-dir" in payload["message"]


@pytest.mark.unit
def test_apply_without_run_id_is_write_denied(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert "--run-id" in payload["message"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    ["validate-jsonl", "plan", "dry-run", "audit", "rollback-plan"],
)
def test_apply_flag_on_non_apply_subcommand_stays_hard_blocked(
    command: str, capsys
) -> None:
    exit_code = main([command, "--apply"])
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_apply_with_non_local_dev_url_is_blocked(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(
        tmp_path / "config.yaml", surreal_url="ws://prod.example.invalid:8000/rpc"
    )
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "APPLY_GATE_DENIED"


@pytest.mark.unit
@pytest.mark.parametrize("host", sorted(LOCAL_DEV_ALLOWED_HOSTS))
def test_apply_accepts_each_local_dev_host(
    host: str, tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    # urlparse needs brackets for IPv6; use [::1] in the URL form.
    netloc_host = f"[{host}]" if host == "::1" else host
    config_path = _write_local_dev_config(
        tmp_path / "config.yaml", surreal_url=f"ws://{netloc_host}:8000/rpc"
    )
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["apply_executed"] is True
    assert payload["apply_mode"] == APPLY_MODE_LOCAL_DEV
    assert payload["adapter"] == ADAPTER_KIND_IN_MEMORY


# ---------------------------------------------------------------------------
# Functional apply behavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_creates_records_via_in_memory_adapter(tmp_path: Path) -> None:
    """The default adapter records every operation in-memory."""

    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    config = load_config(config_path)
    plan = build_import_plan(tmp_path, "run-apply-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(None))

    adapter = InMemoryContextApplyAdapter()
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, 0))
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-apply-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=clock,
    )

    assert report.apply_executed is True
    assert report.status == "applied"
    assert report.adapter == ADAPTER_KIND_IN_MEMORY
    # All operations recorded by the in-memory adapter.
    assert len(adapter.operations) == len(report.operations)
    assert all(op_kind == APPLY_OP_CREATE for op_kind, *_ in adapter.operations)
    counts = report.counts()
    assert counts["applied"] == counts["creates"]
    assert counts["failed"] == 0
    assert counts["blocked"] == 0


@pytest.mark.unit
def test_apply_blocked_by_reconcile_blocking_findings(tmp_path: Path) -> None:
    """A forbidden-table existing record blocks reconcile and apply."""

    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "orders",  # forbidden
                "record_id": "orders:1",
                "payload_hash": "f" * 64,
                "schema_version": "context-importer/v0",
            }
        ],
    )

    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    config = load_config(config_path)
    plan = build_import_plan(tmp_path, "run-apply-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(existing))

    adapter = InMemoryContextApplyAdapter()
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-apply-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 1, 1)),
    )
    assert report.apply_executed is False
    assert report.status == "blocked"
    assert report.blocking_findings_present is True
    # No adapter call was made.
    assert adapter.operations == []


@pytest.mark.unit
def test_apply_cli_returns_validation_error_on_blocking_findings(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "orders",
                "record_id": "orders:1",
                "payload_hash": "f" * 64,
                "schema_version": "context-importer/v0",
            }
        ],
    )
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
            "--existing-records",
            str(existing),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "blocked"
    assert payload["apply_executed"] is False
    assert payload["blocking_findings_present"] is True


@pytest.mark.unit
def test_apply_failure_in_adapter_is_surfaced_without_aborting(
    tmp_path: Path,
) -> None:
    """A per-op adapter failure is reported but does not crash apply."""

    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    config = load_config(config_path)
    plan = build_import_plan(tmp_path, "run-apply-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(None))

    class FlakyAdapter(InMemoryContextApplyAdapter):
        def apply_create(
            self, table: str, record_id: str, payload: dict[str, Any]
        ) -> None:
            raise ApplyAdapterError(f"boom for {record_id}")

    adapter = FlakyAdapter()
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-apply-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=adapter,
        clock=FixedClock(datetime(2026, 1, 1)),
    )
    assert report.status == "partial"
    counts = report.counts()
    assert counts["failed"] == counts["creates"]
    assert all(r.status == "failed" for r in report.results if r.op == APPLY_OP_CREATE)


@pytest.mark.unit
def test_apply_cli_returns_internal_on_adapter_failures(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    """When the in-memory adapter reports failures, CLI exits 6 (INTERNAL)."""

    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")

    # Patch the executor to use a flaky adapter.
    from tools.surrealdb import context_importer as ci

    real_execute = ci.execute_context_apply

    def _flaky_execute(**kwargs: Any) -> ContextApplyReport:
        class _Flaky(InMemoryContextApplyAdapter):
            def apply_create(self, table, record_id, payload):  # type: ignore[no-untyped-def]
                raise ApplyAdapterError("forced")

        kwargs["adapter"] = _Flaky()
        kwargs.setdefault("clock", FixedClock(datetime(2026, 1, 1)))
        return real_execute(**kwargs)

    monkeypatch.setattr(ci, "execute_context_apply", _flaky_execute)

    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_INTERNAL
    payload = _read_json(capsys)
    assert payload["status"] == "partial"
    assert payload["counts"]["failed"] >= 1


@pytest.mark.unit
def test_apply_no_socket_is_opened(tmp_path: Path, capsys, monkeypatch) -> None:
    """The default in-memory adapter must never open a socket during apply."""

    def _boom(*args, **kwargs):  # pragma: no cover - safety net
        raise AssertionError(
            "context_importer apply must not open network sockets"
        )

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)

    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config_path),
            "--input-dir",
            str(tmp_path),
            "--run-id",
            "run-apply-1",
        ]
    )
    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["surrealdb_connection"] == "in-memory-no-network"
    assert payload["surrealdb_writes"] == "in-memory-only"


@pytest.mark.unit
def test_apply_payload_is_deterministic_with_fixed_clock(tmp_path: Path) -> None:
    """Same input + same run_id + same FixedClock => byte-identical payload."""

    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    config = load_config(config_path)
    plan = build_import_plan(tmp_path, "run-apply-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(None))

    fixed = datetime(2026, 1, 1, 12, 0, 0)

    def _run() -> str:
        report = execute_context_apply(
            reconcile_report=reconcile,
            config=config,
            run_id="run-apply-1",
            apply_mode=APPLY_MODE_LOCAL_DEV,
            adapter=InMemoryContextApplyAdapter(),
            clock=FixedClock(fixed),
        )
        return json.dumps(report.to_payload(), sort_keys=True)

    assert _run() == _run()


@pytest.mark.unit
def test_apply_payload_includes_real_adapter_disclaimer(tmp_path: Path) -> None:
    _write_valid_artifacts(tmp_path)
    config_path = _write_local_dev_config(tmp_path / "config.yaml")
    config = load_config(config_path)
    plan = build_import_plan(tmp_path, "run-apply-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(None))
    report = execute_context_apply(
        reconcile_report=reconcile,
        config=config,
        run_id="run-apply-1",
        apply_mode=APPLY_MODE_LOCAL_DEV,
        adapter=InMemoryContextApplyAdapter(),
        clock=FixedClock(datetime(2026, 1, 1)),
    )
    payload = report.to_payload()
    assert payload["real_surrealdb_adapter_available"] is False
    assert payload["adapter"] == ADAPTER_KIND_IN_MEMORY
    assert payload["surrealdb_connection"] == "in-memory-no-network"
    assert payload["schema_version"] == SCHEMA_VERSION
    assert "no production surrealdb activation" in payload["note"].lower()


@pytest.mark.unit
def test_apply_help_advertises_apply_mode_flag(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["apply", "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "--apply-mode" in out
    assert "local-dev" in out


@pytest.mark.unit
def test_unsupported_apply_mode_is_rejected_by_argparse(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["apply", "--apply", "--apply-mode", "production"])
    # argparse choices reject before our handler.
    assert excinfo.value.code != 0
