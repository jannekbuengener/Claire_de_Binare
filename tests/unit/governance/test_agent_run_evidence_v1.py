"""
test_id: tc_agent_run_evidence_v1_001
test_name: agent_run_evidence_v1_emitter_store_verifier
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/contracts/agent_run_evidence/CDB_AGENT_RUN_EVIDENCE_V1.md
decision_ref: cdb.agent_run_evidence.v1
issue_ref: 4256
pr_ref: 4286
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.agent_control.cli import main as cli_main
from tools.agent_control.clock import FrozenClock
from tools.agent_control.dispatch import (
    dispatch_run,
    evidence_snapshot,
    watch_run,
)
from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.digest import compute_bundle_digest
from tools.agent_control.evidence.emit import build_evidence_bundle, emit_evidence
from tools.agent_control.evidence.redact import (
    assert_no_secrets,
    validate_repo_relative_path,
)
from tools.agent_control.evidence.store import EvidenceJsonlStore
from tools.agent_control.evidence.verify import verify_bundle, verify_store
from tools.agent_control.load import dump_json, load_registry_document
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT
from tools.agent_control.provider import MockProvider
from tools.agent_control.run_store import InMemoryRunStore, JsonFileRunStore
from tools.agent_execution_contract.hashing import compute_digest

REPO = Path(__file__).resolve().parents[3]
EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_dispatch"
EVIDENCE_EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_run_evidence"
AGENT_ID = "acp-mock-dispatcher"


def _registry() -> dict:
    return load_registry_document(DEFAULT_CONFIG_ROOT)


def _contract() -> dict:
    return json.loads(
        (EXAMPLES / "positive_mock_dispatch_contract.json").read_text(encoding="utf-8")
    )


def _pass_run(
    tmp_path: Path | None = None,
) -> tuple[InMemoryRunStore, dict]:
    contract = _contract()
    store = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="success",
    )
    run = result["run"]
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "PASS"
    return store, run


def _mutate(store: InMemoryRunStore, run_id: str, mutator) -> dict:
    record = store.get(run_id)
    assert record is not None
    rev = int(record["revision"])
    mutator(record)
    record["revision"] = rev + 1
    return store.update_cas(run_id, rev, record)


@pytest.mark.unit
def test_mock_pass_bundle_schema_and_verifier() -> None:
    store, run = _pass_run()
    emitted = emit_evidence(run["run_id"], store)
    assert emitted["verdict"] == "PASS"
    assert emitted["evidence_class"] == "agent_run_evidence_bundle_v1"
    verified = verify_bundle(emitted["bundle"])
    assert verified["ok"] is True
    assert emitted["bundle"]["authority_limits"]["not_live_go"] is True
    assert "not_final_ci" in emitted["limitations"]


@pytest.mark.unit
def test_blocked_failed_cancelled_honest_bundles() -> None:
    contract = _contract()
    registry = _registry()
    clock = FrozenClock(datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc))

    # FAILED
    store_f = InMemoryRunStore()
    provider_f = MockProvider()
    out = dispatch_run(
        contract,
        registry,
        AGENT_ID,
        store_f,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider_f,
        clock=clock,
        scenario="fail_on_dispatch",
    )
    failed = out["run"]
    assert failed["state"] == "FAILED"
    ev_f = emit_evidence(failed["run_id"], store_f)
    assert ev_f["verdict"] == "FAILED"
    verify_bundle(ev_f["bundle"])

    # CANCELLED via cancel path after dispatch
    from tools.agent_control.dispatch import cancel_run

    store_c = InMemoryRunStore()
    provider_c = MockProvider()
    out_c = dispatch_run(
        contract,
        registry,
        AGENT_ID,
        store_c,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider_c,
        clock=clock,
        scenario="success",
    )
    cancelled = cancel_run(
        out_c["run"]["run_id"],
        store_c,
        reason="operator_cancel",
        provider=provider_c,
        clock=clock,
    )
    assert cancelled["state"] == "CANCELLED"
    ev_c = emit_evidence(cancelled["run_id"], store_c)
    assert ev_c["verdict"] == "CANCELLED"
    verify_bundle(ev_c["bundle"])

    # BLOCKED via HOLD route
    hold = json.loads(
        (EXAMPLES / "negative_hold_route_contract.json").read_text(encoding="utf-8")
    )
    store_b = InMemoryRunStore()
    out_b = dispatch_run(
        hold,
        registry,
        AGENT_ID,
        store_b,
        dry_run=False,
        allow_mock_dispatch=True,
        clock=clock,
    )
    blocked = out_b["run"]
    assert blocked["state"] in {"HOLD", "BLOCKED"}
    ev_b = emit_evidence(blocked["run_id"], store_b)
    assert ev_b["verdict"] in {"HOLD", "BLOCKED"}
    verify_bundle(ev_b["bundle"])


@pytest.mark.unit
def test_evidence_id_and_digest_stable_under_key_reorder() -> None:
    store, run = _pass_run()
    b1 = emit_evidence(run["run_id"], store)["bundle"]
    b2 = emit_evidence(run["run_id"], store)["bundle"]
    assert b1 == b2
    assert b1["evidence_id"] == b2["evidence_id"]
    assert b1["bundle_digest"] == b2["bundle_digest"]
    # Whitespace/key order via dump/load
    reloaded = json.loads(json.dumps(b1, indent=4, sort_keys=False))
    assert compute_bundle_digest(reloaded) == b1["bundle_digest"]


@pytest.mark.unit
def test_changed_files_sorted_deduped() -> None:
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        receipt = dict(record["delivery_receipt"])
        receipt["changed_files"] = ["z.py", "a.py", "a.py", "m.py"]
        record["delivery_receipt"] = receipt

    _mutate(store, run["run_id"], mutate)
    bundle = build_evidence_bundle(store.get(run["run_id"]))
    assert bundle["changed_files"] == ["a.py", "m.py", "z.py"]


@pytest.mark.unit
def test_artifact_digest_binding(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts" / "agent-control" / "note.txt"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("hello-evidence", encoding="utf-8")
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        record["result_refs"] = {
            "artifacts": [{"path": "artifacts/agent-control/note.txt", "type": "file"}]
        }

    _mutate(store, run["run_id"], mutate)
    # Point repo_root at tmp so artifact resolves
    bundle = build_evidence_bundle(store.get(run["run_id"]), repo_root=tmp_path)
    assert bundle["artifacts"][0]["digest"].startswith("sha256:")
    assert bundle["artifacts"][0]["size_bytes"] == len("hello-evidence")
    # PASS with unbound digest would be incomplete — here digest is bound.
    assert bundle["delivery_verdict"]["verdict"] in {"PASS", "HOLD"}


@pytest.mark.unit
def test_usage_cost_normalization_mock_not_applicable() -> None:
    store, run = _pass_run()
    bundle = emit_evidence(run["run_id"], store)["bundle"]
    assert bundle["usage"]["cost"]["status"] == "NOT_APPLICABLE"
    assert bundle["usage"]["cost"]["amount"] is None


@pytest.mark.unit
def test_bindings_survive_store_reload(tmp_path: Path) -> None:
    store, run = _pass_run()
    jsonl = tmp_path / "agent_run_evidence.v1.jsonl"
    first = emit_evidence(run["run_id"], store, jsonl_path=jsonl)
    second = emit_evidence(run["run_id"], store, jsonl_path=jsonl)
    assert first["store"]["written"] is True
    assert second["store"]["idempotent"] is True
    loaded = EvidenceJsonlStore(jsonl).read_all()
    assert len(loaded) == 1
    assert loaded[0]["environment"]["profile_id"] == "mock.v1"
    assert loaded[0]["provider"]["provider_id"] == "mock"
    assert loaded[0]["execution_contract"]["contract_digest"] == compute_digest(
        _contract()
    )


@pytest.mark.unit
def test_stdout_emit_writes_no_file(tmp_path: Path) -> None:
    store, run = _pass_run()
    before = list(tmp_path.iterdir()) if tmp_path.exists() else []
    emitted = emit_evidence(run["run_id"], store, jsonl_path=None)
    assert emitted["store"] is None
    assert list(tmp_path.iterdir()) == before


@pytest.mark.unit
def test_legacy_snapshot_compatible_and_limited() -> None:
    store, run = _pass_run()
    snap = evidence_snapshot(run["run_id"], store)
    assert snap["schema_id"] == "cdb.agent_dispatch_evidence_snapshot.v1"
    assert "not_agent_run_evidence_bundle_v1" in snap["limitations"]
    assert "not_agent_run_evidence_bundle_v1" in snap["explicit_negative_claims"]


@pytest.mark.unit
def test_secret_in_result_refs_fail_closed() -> None:
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        record["result_refs"] = {
            "nested": {"Authorization": "Bearer super-secret-token"},
        }

    _mutate(store, run["run_id"], mutate)
    with pytest.raises(EvidenceError) as exc:
        emit_evidence(run["run_id"], store)
    assert exc.value.code == "EVIDENCE_SECRET_DETECTED"


@pytest.mark.unit
def test_prompt_text_rejected() -> None:
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        record["prompt_text"] = "do not store me"

    _mutate(store, run["run_id"], mutate)
    with pytest.raises(EvidenceError) as exc:
        emit_evidence(run["run_id"], store)
    assert exc.value.code == "EVIDENCE_SECRET_DETECTED"


@pytest.mark.unit
def test_path_traversal_and_absolute_rejected() -> None:
    with pytest.raises(EvidenceError):
        validate_repo_relative_path("../etc/passwd")
    with pytest.raises(EvidenceError):
        validate_repo_relative_path("/tmp/x")
    with pytest.raises(EvidenceError):
        validate_repo_relative_path("docs/readme.md")  # outside artifacts/


@pytest.mark.unit
def test_digest_tamper_and_id_collision(tmp_path: Path) -> None:
    store, run = _pass_run()
    bundle = emit_evidence(run["run_id"], store)["bundle"]
    tampered = deepcopy(bundle)
    tampered["bundle_digest"] = "sha256:" + ("0" * 64)
    with pytest.raises(EvidenceError) as exc:
        verify_bundle(tampered)
    assert exc.value.code == "EVIDENCE_DIGEST_MISMATCH"

    jsonl = tmp_path / "store.jsonl"
    EvidenceJsonlStore(jsonl).append_idempotent(bundle)
    other = deepcopy(bundle)
    other["limitations"] = list(bundle["limitations"]) + ["extra"]
    from tools.agent_control.evidence.digest import attach_bundle_digest

    other.pop("bundle_digest", None)
    other.get("integrity", {}).pop("digest", None)
    other = attach_bundle_digest(other)
    assert other["bundle_digest"] != bundle["bundle_digest"]
    with pytest.raises(EvidenceError) as exc2:
        EvidenceJsonlStore(jsonl).append_idempotent(other)
    assert exc2.value.code == "EVIDENCE_ID_DIGEST_COLLISION"


@pytest.mark.unit
def test_malformed_and_truncated_jsonl(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(EvidenceError):
        verify_store(bad)
    trunc = tmp_path / "trunc.jsonl"
    trunc.write_text('{"schema_id":"cdb.agent_run_evidence.v1"}', encoding="utf-8")
    with pytest.raises(EvidenceError) as exc:
        EvidenceJsonlStore(trunc).read_all()
    assert exc.value.code == "EVIDENCE_STORE_TRUNCATED_LINE"


@pytest.mark.unit
def test_lock_conflict(tmp_path: Path) -> None:
    store, run = _pass_run()
    bundle = emit_evidence(run["run_id"], store)["bundle"]
    jsonl = tmp_path / "locked.jsonl"
    lock = Path(str(jsonl) + ".lock")
    lock.write_text("held", encoding="utf-8")
    with pytest.raises(EvidenceError) as exc:
        EvidenceJsonlStore(jsonl, lock_timeout_s=0.2).append_idempotent(bundle)
    assert exc.value.code == "EVIDENCE_STORE_LOCK_CONFLICT"


@pytest.mark.unit
def test_provider_success_without_receipt_is_hold() -> None:
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        record["delivery_receipt"] = None

    _mutate(store, run["run_id"], mutate)
    emitted = emit_evidence(run["run_id"], store)
    assert emitted["verdict"] == "HOLD"
    assert "EVIDENCE_DELIVERY_RECEIPT_MISSING" in emitted["reason_codes"] or (
        "EVIDENCE_INCOMPLETE" in emitted["reason_codes"]
    )


@pytest.mark.unit
def test_authority_claim_rejected() -> None:
    store, run = _pass_run()
    bundle = emit_evidence(run["run_id"], store)["bundle"]
    bundle["final_ci_success"] = True
    with pytest.raises(EvidenceError):
        # rebuild path rejects before seal; simulate verify input
        from tools.agent_control.evidence.emit import _reject_authority_claims

        _reject_authority_claims(bundle)


@pytest.mark.unit
def test_float_cost_rejected() -> None:
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        record["provider_id"] = "cursor-sdk"
        record["usage"] = {
            "iterations": 1,
            "tool_calls": 1,
            "cost": 1.25,
            "currency": "USD",
        }

    _mutate(store, run["run_id"], mutate)
    with pytest.raises(EvidenceError) as exc:
        emit_evidence(run["run_id"], store)
    assert exc.value.code == "EVIDENCE_USAGE_INVALID"


@pytest.mark.unit
def test_unknown_schema_field_rejected() -> None:
    store, run = _pass_run()
    bundle = emit_evidence(run["run_id"], store)["bundle"]
    bundle["unexpected_field"] = True
    with pytest.raises(EvidenceError) as exc:
        verify_bundle(bundle)
    assert exc.value.code in {"EVIDENCE_SCHEMA_INVALID", "EVIDENCE_UNKNOWN_FIELD"}


@pytest.mark.unit
def test_cli_snapshot_emit_verify_show(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store, run = _pass_run()
    state = tmp_path / "runs.json"
    # Persist run into file store for CLI
    file_store = JsonFileRunStore(state)
    record = store.get(run["run_id"])
    assert record is not None
    file_store.create(record)

    assert cli_main(["evidence", "--run-id", run["run_id"], "--state", str(state)]) == 0
    snap_out = json.loads(capsys.readouterr().out)
    assert snap_out["schema_id"] == "cdb.agent_dispatch_evidence_snapshot.v1"

    jsonl = tmp_path / "evidence.jsonl"
    assert (
        cli_main(
            [
                "evidence",
                "emit",
                "--run",
                run["run_id"],
                "--state",
                str(state),
                "--store",
                str(jsonl),
            ]
        )
        == 0
    )
    emit_out = json.loads(capsys.readouterr().out)
    assert emit_out["verdict"] == "PASS"

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(dump_json(emit_out["bundle"]), encoding="utf-8")
    assert cli_main(["evidence", "verify", "--bundle", str(bundle_path)]) == 0
    capsys.readouterr()
    assert cli_main(["evidence", "verify", "--store", str(jsonl)]) == 0
    capsys.readouterr()
    assert (
        cli_main(["evidence", "show", "--run", run["run_id"], "--store", str(jsonl)])
        == 0
    )
    capsys.readouterr()

    # Bundle entry alias
    assert cli_main(["evidence", "--run", run["run_id"], "--state", str(state)]) == 0
    alias = json.loads(capsys.readouterr().out)
    assert alias["evidence_class"] == "agent_run_evidence_bundle_v1"


@pytest.mark.unit
def test_multiple_store_records_verify(tmp_path: Path) -> None:
    store1, run1 = _pass_run()
    # Second run with different scenario seed via new store
    contract = _contract()
    store2 = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 2, 13, 0, tzinfo=timezone.utc))
    out = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store2,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="success",
        run_id="adr-aaaaaaaaaaaaaaaa",
    )
    run2 = watch_run(out["run"]["run_id"], store2, provider=provider, clock=clock)
    run2 = watch_run(run2["run_id"], store2, provider=provider, clock=clock)

    jsonl = tmp_path / "multi.jsonl"
    emit_evidence(run1["run_id"], store1, jsonl_path=jsonl)
    emit_evidence(run2["run_id"], store2, jsonl_path=jsonl)
    result = verify_store(jsonl)
    assert result["count"] == 2


@pytest.mark.unit
def test_evidence_id_versions_across_lifecycle_states() -> None:
    """P2: HOLD then PASS emissions must not collide on evidence_id."""
    store, run = _pass_run()
    pass_id = emit_evidence(run["run_id"], store)["bundle"]["evidence_id"]

    def to_hold(record: dict) -> None:
        record["state"] = "HOLD"
        record["terminal_code"] = "HOLD_TEST"
        record["terminal_reason"] = "lifecycle versioning probe"

    _mutate(store, run["run_id"], to_hold)
    hold_id = build_evidence_bundle(store.get(run["run_id"]))["evidence_id"]
    assert hold_id != pass_id
    assert hold_id.startswith("are-")
    assert pass_id.startswith("are-")


@pytest.mark.unit
def test_lifecycle_versioned_store_allows_hold_then_pass(tmp_path: Path) -> None:
    """R4: HOLD + PASS for same run/attempt verify together in the store."""
    store, run = _pass_run()
    jsonl = tmp_path / "lifecycle.jsonl"

    def to_hold(record: dict) -> None:
        record["state"] = "HOLD"
        record["terminal_code"] = "HOLD_TEST"
        record["terminal_reason"] = "pre-pass hold emission"

    _mutate(store, run["run_id"], to_hold)
    hold_bundle = emit_evidence(run["run_id"], store, jsonl_path=jsonl)["bundle"]

    def to_pass(record: dict) -> None:
        record["state"] = "PASS"
        record["terminal_code"] = "PASS"
        record["terminal_reason"] = "delivery_goals_met"

    _mutate(store, run["run_id"], to_pass)
    pass_bundle = emit_evidence(run["run_id"], store, jsonl_path=jsonl)["bundle"]

    assert hold_bundle["evidence_id"] != pass_bundle["evidence_id"]
    assert hold_bundle["lifecycle"]["state"] == "HOLD"
    assert pass_bundle["lifecycle"]["state"] == "PASS"
    result = verify_store(jsonl)
    assert result["ok"] is True
    assert result["count"] == 2


@pytest.mark.unit
def test_same_lifecycle_conflicting_bundles_still_blocked(tmp_path: Path) -> None:
    """R4: same run/attempt/lifecycle with conflicting content remains blocked."""
    store, run = _pass_run()
    jsonl = tmp_path / "collision.jsonl"
    bundle = emit_evidence(run["run_id"], store, jsonl_path=jsonl)["bundle"]
    other = deepcopy(bundle)
    other["limitations"] = list(bundle["limitations"]) + ["extra-conflict"]
    from tools.agent_control.evidence.digest import attach_bundle_digest

    other.pop("bundle_digest", None)
    other.get("integrity", {}).pop("digest", None)
    other = attach_bundle_digest(other)
    with pytest.raises(EvidenceError) as exc:
        EvidenceJsonlStore(jsonl).append_idempotent(other)
    assert exc.value.code == "EVIDENCE_ID_DIGEST_COLLISION"


@pytest.mark.unit
def test_create_route_evidence_includes_observed_targets() -> None:
    """R3: evidence delivery_context carries observed create-route targets."""
    store, run = _pass_run()

    def mutate(record: dict) -> None:
        record["route"] = {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": None,
            "target_branch": None,
        }
        record["delivery_receipt"] = {
            "target_pr": 77777,
            "target_branch": "batch/create-77777",
            "commit": "d" * 40,
            "delivery_status": "DONE_PR_OPEN",
        }

    _mutate(store, run["run_id"], mutate)
    bundle = build_evidence_bundle(store.get(run["run_id"]))
    ctx = bundle["delivery_context"]
    assert ctx["target_pr"] == 77777
    assert ctx["target_branch"] == "batch/create-77777"
    assert ctx["provenance"]["source"] == "run.route+validated_provider_receipt"

    # After route merge (happy path), provenance must still mark receipt origin.
    def mutate_merged(record: dict) -> None:
        record["route"] = {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": 77777,
            "target_branch": "batch/create-77777",
            "target_provenance": "route+validated_provider_receipt",
        }
        record["delivery_receipt"] = {
            "target_pr": 77777,
            "target_branch": "batch/create-77777",
            "commit": "d" * 40,
            "delivery_status": "DONE_PR_OPEN",
        }

    _mutate(store, run["run_id"], mutate_merged)
    merged = build_evidence_bundle(store.get(run["run_id"]))
    assert merged["delivery_context"]["target_pr"] == 77777
    assert (
        merged["delivery_context"]["provenance"]["source"]
        == "run.route+validated_provider_receipt"
    )

    # Missing receipt → no invented target
    def clear_receipt(record: dict) -> None:
        record["route"] = {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": None,
            "target_branch": None,
        }
        record["delivery_receipt"] = None

    _mutate(store, run["run_id"], clear_receipt)
    bare = build_evidence_bundle(store.get(run["run_id"]))
    assert bare["delivery_context"]["target_pr"] is None
    assert bare["delivery_context"]["target_branch"] is None
