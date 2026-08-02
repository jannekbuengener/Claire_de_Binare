"""
test_id: tc_agent_dispatcher_v1_001
test_name: agent_dispatcher_v1_governed_state_machine
test_type: Bauteil-Test
cdb_area: governance
rule_ref: knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
decision_ref: cdb.agent_dispatch_run.v1
issue_ref: 4253
pr_ref: 4286
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.agent_control.cli import main as cli_main
from tools.agent_control.clock import FrozenClock
from tools.agent_control.dispatch import (
    build_dry_run_plan,
    cancel_run,
    dispatch_run,
    evidence_snapshot,
    retry_run,
    watch_run,
)
from tools.agent_control.errors import DispatchError
from tools.agent_control.lifecycle import (
    ALLOWED_TRANSITIONS,
    CANONICAL_STATES,
    ISSUE_STATE_MAPPING,
    TERMINAL_STATES,
    can_transition,
    transition,
)
from tools.agent_control.load import dump_json, load_registry_document
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT
from tools.agent_control.provider import MockProvider
from tools.agent_control.run_store import InMemoryRunStore
from tools.agent_execution_contract.hashing import attach_digest, compute_digest

REPO = Path(__file__).resolve().parents[3]
EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_dispatch"
AGENT_ID = "acp-mock-dispatcher"


def _registry() -> dict:
    return load_registry_document(DEFAULT_CONFIG_ROOT)


def _contract() -> dict:
    return json.loads(
        (EXAMPLES / "positive_mock_dispatch_contract.json").read_text(encoding="utf-8")
    )


def _hold_contract() -> dict:
    return json.loads(
        (EXAMPLES / "negative_hold_route_contract.json").read_text(encoding="utf-8")
    )


@pytest.mark.unit
def test_issue_state_mapping_is_event_only() -> None:
    assert "VALIDATED" not in CANONICAL_STATES
    assert "EVIDENCE_COLLECTED" not in CANONICAL_STATES
    assert "HANDED_OFF" not in CANONICAL_STATES
    assert "CONTRACTED" in ISSUE_STATE_MAPPING["VALIDATED"]


@pytest.mark.unit
@pytest.mark.parametrize("current", CANONICAL_STATES)
def test_transition_table_positive_and_negative(current: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    for nxt in CANONICAL_STATES:
        if current == nxt:
            assert can_transition(current, nxt)
            continue
        if current in TERMINAL_STATES:
            assert not can_transition(current, nxt)
            with pytest.raises(DispatchError) as exc:
                transition(current, nxt)
            assert exc.value.code == "DISPATCH_TERMINAL_TRANSITION"
            continue
        if nxt in allowed:
            assert transition(current, nxt) == nxt
        else:
            with pytest.raises(DispatchError) as exc:
                transition(current, nxt)
            assert exc.value.code == "DISPATCH_ILLEGAL_TRANSITION"


@pytest.mark.unit
def test_dry_run_byteidentical_and_mutation_free() -> None:
    contract = _contract()
    registry = _registry()
    provider = MockProvider()
    store = InMemoryRunStore()
    plan_a = build_dry_run_plan(contract, registry, AGENT_ID)
    plan_b = build_dry_run_plan(deepcopy(contract), deepcopy(registry), AGENT_ID)
    assert dump_json(plan_a) == dump_json(plan_b)
    result = dispatch_run(
        contract, registry, AGENT_ID, store, dry_run=True, provider=provider
    )
    assert result["dry_run"] is True
    assert result["run"] is None
    assert provider.dispatch_calls == 0
    assert store.list_runs() == []


@pytest.mark.unit
def test_happy_path_to_pass_with_delivery_receipt() -> None:
    contract = _contract()
    registry = _registry()
    store = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        contract,
        registry,
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="success",
    )
    run = result["run"]
    assert run["state"] == "DISPATCHED"
    assert run["contract_digest"] == compute_digest(contract)
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "RUNNING"
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "PASS"
    assert run["delivery_receipt"]["target_pr"] == 4286
    assert run["delivery_receipt"]["commit"] != ("0" * 40)
    assert any(e["name"] == "validation_success" for e in run["lifecycle_events"])
    assert any(e["name"] == "handed_off" for e in run["lifecycle_events"])


@pytest.mark.unit
def test_tampered_contract_no_provider_call() -> None:
    contract = _contract()
    contract["permissions"]["write_docs"] = False  # digest mismatch / or re-seal needed
    # Keep integrity digest stale → validate_contract fails hash
    registry = _registry()
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        contract,
        registry,
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    assert provider.dispatch_calls == 0
    assert result["run"]["state"] == "BLOCKED"
    assert result["run"]["terminal_code"] == "CONTRACT_HASH_MISMATCH"


@pytest.mark.unit
def test_hold_route_never_dispatches() -> None:
    contract = _hold_contract()
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    assert provider.dispatch_calls == 0
    assert result["run"]["state"] == "HOLD"
    assert result["run"]["terminal_code"] == "HOLD_NO_SAFE_ROUTE"


@pytest.mark.unit
def test_disabled_agent_blocked() -> None:
    result = dispatch_run(
        _contract(),
        _registry(),
        "acp-disabled-placeholder",
        InMemoryRunStore(),
        dry_run=False,
        allow_mock_dispatch=True,
        provider=MockProvider(),
    )
    assert result["run"]["state"] == "BLOCKED"
    assert result["run"]["terminal_code"] == "DISPATCH_AGENT_DISABLED"


@pytest.mark.unit
def test_permission_ceiling_exceeded() -> None:
    contract = _contract()
    # Escalate a permission that registry docs_only would block — use write on
    # docs steward ceiling by pointing agent to docs steward? Better: mutate
    # contract open_pr true while registry effective open_pr false.
    contract["permissions"]["open_pr"] = True
    contract = attach_digest(contract)
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        InMemoryRunStore(),
        dry_run=False,
        allow_mock_dispatch=True,
        provider=MockProvider(),
    )
    assert result["run"]["terminal_code"] == "DISPATCH_PERMISSION_CEILING"


@pytest.mark.unit
def test_forbidden_merge_permission() -> None:
    contract = _contract()
    contract["permissions"]["merge"] = True
    # Also need merge_authority still false for schema semantics — validate may
    # reject earlier. Force digest after mutation.
    contract = attach_digest(contract)
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        InMemoryRunStore(),
        dry_run=False,
        allow_mock_dispatch=True,
        provider=MockProvider(),
    )
    assert result["run"]["state"] in {"HOLD", "BLOCKED"}
    assert result["run"]["terminal_code"] in {
        "DISPATCH_FORBIDDEN_PERMISSION",
        "CONTRACT_MERGE_AUTHORITY",
    }


@pytest.mark.unit
def test_zero_budget_blocks_execute_allows_dry_run() -> None:
    contract = _contract()
    contract["budget"]["wall_time_seconds"] = 0
    contract = attach_digest(contract)
    plan = build_dry_run_plan(contract, _registry(), AGENT_ID)
    assert plan["preflight_ok"] is True  # dry-run may analyze zero budget
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        InMemoryRunStore(),
        dry_run=False,
        allow_mock_dispatch=True,
        provider=MockProvider(),
    )
    assert result["run"]["terminal_code"] == "DISPATCH_ZERO_BUDGET"


@pytest.mark.unit
def test_duplicate_dispatch_single_provider_call() -> None:
    contract = _contract()
    store = InMemoryRunStore()
    provider = MockProvider()
    first = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        run_id="adr-duptest00000001",
    )
    second = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        run_id="adr-duptest00000002",
    )
    assert first["run"]["run_id"] == second["run"]["run_id"]
    assert second.get("idempotent_replay") is True
    assert provider.dispatch_calls == 1


@pytest.mark.unit
def test_manual_cancel() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        scenario="stay_running",
    )
    run = watch_run(result["run"]["run_id"], store, provider=provider)
    assert run["state"] == "RUNNING"
    cancelled = cancel_run(run["run_id"], store, "operator_abort", provider=provider)
    assert cancelled["state"] == "CANCELLED"
    # terminal unchanged on second cancel
    with pytest.raises(DispatchError) as exc:
        cancel_run(run["run_id"], store, "again", provider=provider)
    assert exc.value.code == "DISPATCH_TERMINAL_TRANSITION"


@pytest.mark.unit
def test_timeout_cancel_unconfirmed_blocked() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="timeout_cancel_unconfirmed",
    )
    run = watch_run(result["run"]["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "RUNNING"
    clock.advance(20_000)
    timed = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert timed["state"] == "BLOCKED"
    assert timed["terminal_code"] == "PROVIDER_CANCEL_UNCONFIRMED"


@pytest.mark.unit
def test_timeout_cancel_confirmed() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="stay_running",
    )
    run = watch_run(result["run"]["run_id"], store, provider=provider, clock=clock)
    clock.advance(20_000)
    timed = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert timed["state"] == "CANCELLED"
    assert timed["terminal_code"] == "TIMEOUT"


@pytest.mark.unit
def test_unknown_provider_status_blocked() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        scenario="unknown_status",
    )
    assert result["run"]["state"] == "BLOCKED"


@pytest.mark.unit
def test_malformed_provider_response_blocked() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        scenario="malformed",
    )
    assert result["run"]["state"] == "BLOCKED"
    assert result["run"]["terminal_code"] == "DISPATCH_PROVIDER_MALFORMED"


@pytest.mark.unit
def test_budget_exceeded_on_watch() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        scenario="budget_exceeded",
    )
    run = watch_run(result["run"]["run_id"], store, provider=provider)
    assert run["state"] == "BLOCKED"
    assert run["terminal_code"] == "DISPATCH_BUDGET_EXCEEDED"


@pytest.mark.unit
def test_retry_creates_new_attempt_and_keeps_terminal_previous() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    first = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        scenario="fail_on_dispatch",
    )
    assert first["run"]["state"] == "FAILED"
    prev_id = first["run"]["run_id"]
    prev = deepcopy(store.get(prev_id))
    retried = retry_run(
        prev_id,
        _contract(),
        _registry(),
        store,
        "operator_retry",
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        scenario="success",
    )
    assert retried["previous_run_unchanged"] is True
    assert store.get(prev_id) == prev
    assert retried["run"]["attempt"] == 2
    assert retried["run"]["previous_run_id"] == prev_id


@pytest.mark.unit
def test_retry_unchanged_integrity_blocker_refused() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    bad = _contract()
    bad["permissions"]["write_docs"] = False  # stale digest
    blocked = dispatch_run(
        bad,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    assert blocked["run"]["terminal_code"] == "CONTRACT_HASH_MISMATCH"
    with pytest.raises(DispatchError) as exc:
        retry_run(
            blocked["run"]["run_id"],
            bad,
            _registry(),
            store,
            "blind_retry",
            dry_run=False,
            allow_mock_dispatch=True,
            provider=provider,
        )
    assert exc.value.code == "DISPATCH_RETRY_BLOCKER_UNCHANGED"


@pytest.mark.unit
def test_evidence_snapshot_has_negative_claims_and_no_secrets() -> None:
    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    snap = evidence_snapshot(result["run"]["run_id"], store)
    assert snap["output_type"] == "dispatcher_lifecycle_snapshot"
    assert "not_agent_run_evidence_bundle_v1" in snap["explicit_negative_claims"]
    assert "not_merge_authority" in snap["limitations"]
    blob = json.dumps(snap)
    assert "api_key=" not in blob.lower()
    # evidence is read-only
    assert store.get(result["run"]["run_id"])["state"] == result["run"]["state"]


@pytest.mark.unit
def test_cli_dispatch_help_and_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as help_exc:
        cli_main(["dispatch", "--help"])
    assert help_exc.value.code == 0
    help_out = capsys.readouterr().out
    assert "--dry-run" in help_out
    assert "--allow-mock-dispatch" in help_out
    rc = cli_main(
        [
            "dispatch",
            "--contract",
            str(EXAMPLES / "positive_mock_dispatch_contract.json"),
            "--registry",
            str(DEFAULT_CONFIG_ROOT),
            "--agent-id",
            AGENT_ID,
            "--dry-run",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["plan"]["preflight_ok"] is True


@pytest.mark.unit
def test_cli_registry_still_works() -> None:
    assert cli_main(["registry", "validate", "--config", str(DEFAULT_CONFIG_ROOT)]) == 0


@pytest.mark.unit
def test_secret_like_provider_payload_rejected() -> None:
    provider = MockProvider()
    from tools.agent_control.provider import ProviderResult, sanitize_provider_result

    with pytest.raises(DispatchError) as exc:
        sanitize_provider_result(
            ProviderResult(
                provider_id="mock",
                provider_run_id="x",
                normalized_status="SUCCEEDED",
                result_refs={"note": "api_key=supersecret"},
            )
        )
    assert exc.value.code == "DISPATCH_PROVIDER_SECRET_PAYLOAD"


@pytest.mark.unit
def test_receipt_is_provider_observed_not_pre_fabricated() -> None:
    """P1: dispatcher must not seal an all-zero success receipt before dispatch."""
    store = InMemoryRunStore()
    provider = MockProvider()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        _contract(),
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
    assert run["delivery_receipt"] is None
    assert run["expected_delivery"]["expected_status"] == "DONE_SLICE_ADDED_TO_BATCH_PR"
    assert run["expected_delivery"]["target_pr"] == 4286
    # Provider request must not carry a fabricated receipt.
    internal = next(iter(provider._runs.values()))  # noqa: SLF001
    assert internal.request is not None
    assert internal.request.delivery_receipt is None
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "PASS"
    receipt = run["delivery_receipt"]
    assert receipt["commit"] != ("0" * 40)
    assert receipt["observation_source"] == "mock_provider"
    assert len(receipt["commit"]) == 64


@pytest.mark.unit
def test_expected_status_not_copied_from_provider_receipt() -> None:
    """P2: injected provider status must not rewrite sealed expected_status."""
    from tools.agent_control.provider import ProviderResult

    class _Injected:
        provider_id = "mock"

        def __init__(self) -> None:
            self._pid = "inj-1"

        def dispatch(self, request):  # noqa: ANN001
            return ProviderResult(
                provider_id=self.provider_id,
                provider_run_id=self._pid,
                normalized_status="QUEUED",
            )

        def watch(self, provider_run_id: str) -> ProviderResult:
            return ProviderResult(
                provider_id=self.provider_id,
                provider_run_id=provider_run_id,
                normalized_status="SUCCEEDED",
                usage={"iterations": 1, "tool_calls": 1},
                delivery_receipt={
                    "target_pr": 4286,
                    "target_branch": "batch/agent-skills-issue-4250",
                    "commit": "a" * 40,
                    "delivery_status": "DONE_PR_OPEN",  # differs from sealed expected
                },
            )

        def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
            raise AssertionError("cancel not expected")

    store = InMemoryRunStore()
    provider = _Injected()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
    result = dispatch_run(
        _contract(),
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
        clock=clock,
        scenario="success",
    )
    run = watch_run(result["run"]["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "BLOCKED"
    assert run["terminal_code"] == "DISPATCH_DELIVERY_STATUS_MISMATCH"
    assert run["expected_delivery"]["expected_status"] == "DONE_SLICE_ADDED_TO_BATCH_PR"


@pytest.mark.unit
def test_create_route_accepts_observed_new_pr_number() -> None:
    """P2: CREATE_* with null contract target_pr accepts observed PR on receipt."""
    from tools.agent_control.dispatch import _validate_delivery_receipt

    contract = {
        "route": {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": None,
            "target_branch": None,
        },
        "execution_scope": {
            "delivery_target": {
                "expected_status": "DONE_PR_OPEN",
                "target_pr": None,
                "target_branch": None,
            }
        },
    }
    _validate_delivery_receipt(
        contract,
        {
            "target_pr": 99123,
            "target_branch": "batch/new-99123",
            "commit": "b" * 40,
            "delivery_status": "DONE_PR_OPEN",
        },
    )
    with pytest.raises(DispatchError) as exc:
        _validate_delivery_receipt(
            contract,
            {
                "target_pr": None,
                "target_branch": "batch/new",
                "commit": "b" * 40,
                "delivery_status": "DONE_PR_OPEN",
            },
        )
    assert exc.value.code == "DISPATCH_DELIVERY_RECEIPT_MISMATCH"


# ---------------------------------------------------------------------------
# #4293 post-merge residuals R1–R3
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_conflicting_delivery_targets_block_before_provider() -> None:
    """R1: mismatched route vs delivery_target must fail-closed; no provider call."""
    from tools.agent_control.dispatch import assert_delivery_target_consistent

    contract = _contract()
    contract["execution_scope"]["delivery_target"]["target_pr"] = 13
    # route still has 4286
    contract = attach_digest(contract)
    with pytest.raises(DispatchError) as exc:
        assert_delivery_target_consistent(contract)
    assert exc.value.code == "DISPATCH_DELIVERY_TARGET_CONFLICT"

    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    assert provider.dispatch_calls == 0
    assert result["run"]["state"] == "BLOCKED"
    assert result["run"]["terminal_code"] == "DISPATCH_DELIVERY_TARGET_CONFLICT"


@pytest.mark.unit
def test_conflicting_delivery_branches_block() -> None:
    """R1: mismatched target_branch also conflicts."""
    from tools.agent_control.dispatch import assert_delivery_target_consistent

    contract = _contract()
    contract["execution_scope"]["delivery_target"][
        "target_branch"
    ] = "batch/other-branch"
    contract = attach_digest(contract)
    with pytest.raises(DispatchError) as exc:
        assert_delivery_target_consistent(contract)
    assert exc.value.code == "DISPATCH_DELIVERY_TARGET_CONFLICT"


@pytest.mark.unit
def test_identical_duplicate_delivery_targets_allowed() -> None:
    """R1: identical route + delivery_target values remain valid."""
    from tools.agent_control.dispatch import assert_delivery_target_consistent

    contract = _contract()
    assert_delivery_target_consistent(contract)  # no raise


@pytest.mark.unit
def test_whitespace_only_delivery_branch_does_not_override_route() -> None:
    """R1: whitespace-only delivery_target branch is absent, not a sealed override."""
    from tools.agent_control.dispatch import (
        _delivery_target,
        assert_delivery_target_consistent,
    )

    contract = _contract()
    route_branch = contract["route"]["target_branch"]
    contract["execution_scope"]["delivery_target"]["target_branch"] = "   \t"
    contract = attach_digest(contract)
    assert_delivery_target_consistent(contract)
    sealed = _delivery_target(contract)
    assert sealed["target_branch"] == route_branch

    store = InMemoryRunStore()
    provider = MockProvider()
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    assert result["run"]["state"] != "BLOCKED"
    assert result["run"]["expected_delivery"]["target_branch"] == route_branch
    assert provider.dispatch_calls >= 1


@pytest.mark.unit
def test_boolean_create_receipt_pr_rejected() -> None:
    """R3: bool is not a valid observed target_pr (bool subclasses int)."""
    from tools.agent_control.dispatch import _validate_delivery_receipt

    contract = {
        "route": {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": None,
            "target_branch": None,
        },
        "execution_scope": {
            "delivery_target": {
                "expected_status": "DONE_PR_OPEN",
                "target_pr": None,
                "target_branch": None,
            }
        },
    }
    with pytest.raises(DispatchError) as exc:
        _validate_delivery_receipt(
            contract,
            {
                "target_pr": True,
                "target_branch": "batch/agent-skills-issue-4293",
                "commit": "a" * 40,
                "delivery_status": "DONE_PR_OPEN",
            },
        )
    assert exc.value.code == "DISPATCH_DELIVERY_RECEIPT_MISMATCH"


@pytest.mark.unit
def test_padded_route_branch_normalized_on_run_and_request() -> None:
    """R1: padded route branches are normalized on run record and provider request."""

    class CapturingProvider(MockProvider):
        def __init__(self) -> None:
            super().__init__()
            self.last_request = None

        def dispatch(self, request):  # type: ignore[no-untyped-def]
            self.last_request = request
            return super().dispatch(request)

    contract = _contract()
    padded = f"  {contract['route']['target_branch']}  "
    contract["route"]["target_branch"] = padded
    contract["execution_scope"]["delivery_target"]["target_branch"] = padded
    contract = attach_digest(contract)

    store = InMemoryRunStore()
    provider = CapturingProvider()
    result = dispatch_run(
        contract,
        _registry(),
        AGENT_ID,
        store,
        dry_run=False,
        allow_mock_dispatch=True,
        provider=provider,
    )
    expected = padded.strip()
    assert result["run"]["route"]["target_branch"] == expected
    assert result["run"]["expected_delivery"]["target_branch"] == expected
    assert provider.last_request is not None
    assert provider.last_request.route["target_branch"] == expected


@pytest.mark.unit
def test_create_route_empty_targets_allowed() -> None:
    """R1: CREATE routes may leave targets empty until receipt observation."""
    from tools.agent_control.dispatch import assert_delivery_target_consistent

    contract = {
        "route": {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": None,
            "target_branch": None,
        },
        "execution_scope": {
            "delivery_target": {
                "expected_status": "DONE_PR_OPEN",
                "target_pr": None,
                "target_branch": None,
            }
        },
    }
    assert_delivery_target_consistent(contract)


@pytest.mark.unit
def test_attenuated_wall_time_applied_to_run_and_request(monkeypatch) -> None:
    """R2: lower profile wall ceiling becomes effective run/request budget."""
    import tools.agent_control.preflight as pf_mod
    from tools.agent_control.dispatch import effective_dispatch_budget
    from tools.agent_control.provider import ProviderRequest, ProviderResult

    # Unit: restrictive merge
    merged = effective_dispatch_budget(
        {"wall_time_seconds": 14400, "max_iterations": 10},
        {"wall_time_seconds": 60},
    )
    assert merged["wall_time_seconds"] == 60
    assert merged["max_iterations"] == 10
    # Higher profile must not expand
    expanded = effective_dispatch_budget(
        {"wall_time_seconds": 100},
        {"wall_time_seconds": 9999},
    )
    assert expanded["wall_time_seconds"] == 100

    original_digest = compute_digest(_contract())

    class _Capture:
        provider_id = "mock"

        def __init__(self) -> None:
            self.inner = MockProvider()
            self.last_request = None

        def dispatch(self, request: ProviderRequest) -> ProviderResult:
            self.last_request = request
            return self.inner.dispatch(request)

        def watch(self, provider_run_id: str) -> ProviderResult:
            return self.inner.watch(provider_run_id)

        def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
            return self.inner.cancel(provider_run_id, reason)

    real_env = pf_mod.run_environment_preflight

    def _with_wall(**kwargs):
        result = real_env(**kwargs)
        result.effective_constraints = {
            **(result.effective_constraints or {}),
            "wall_time_seconds": 60,
        }
        return result

    monkeypatch.setattr(pf_mod, "run_environment_preflight", _with_wall)
    contract = _contract()
    store = InMemoryRunStore()
    provider = _Capture()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
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
    assert run["budget"]["wall_time_seconds"] == 60
    assert provider.last_request is not None
    assert provider.last_request.budget["wall_time_seconds"] == 60
    assert compute_digest(contract) == original_digest
    # Timeout enforcement uses the same restrictive budget
    clock.advance(61)
    timed = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert timed["state"] in {"CANCELLED", "BLOCKED"}
    assert timed["terminal_code"] in {"TIMEOUT", "PROVIDER_CANCEL_UNCONFIRMED"}


@pytest.mark.unit
def test_create_route_records_observed_targets_on_run() -> None:
    """R3: CREATE routes persist validated receipt targets onto the run route."""
    from tools.agent_control.dispatch import _merge_observed_create_targets
    from tools.agent_control.provider import ProviderRequest, ProviderResult

    class _CreateProvider:
        provider_id = "mock"

        def __init__(self) -> None:
            self._ticks = 0

        def dispatch(self, request: ProviderRequest) -> ProviderResult:
            return ProviderResult(
                provider_id="mock",
                provider_run_id=f"mock-{request.run_id}",
                normalized_status="QUEUED",
                usage={"iterations": 0, "tool_calls": 0},
            )

        def watch(self, provider_run_id: str) -> ProviderResult:
            self._ticks += 1
            if self._ticks == 1:
                return ProviderResult(
                    provider_id="mock",
                    provider_run_id=provider_run_id,
                    normalized_status="RUNNING",
                    usage={"iterations": 1, "tool_calls": 1},
                )
            return ProviderResult(
                provider_id="mock",
                provider_run_id=provider_run_id,
                normalized_status="SUCCEEDED",
                usage={"iterations": 2, "tool_calls": 2},
                delivery_receipt={
                    "target_pr": 99123,
                    "target_branch": "batch/agent-skills-issue-4293",
                    "commit": "c" * 40,
                    "delivery_status": "DONE_PR_OPEN",
                },
            )

        def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
            raise AssertionError("cancel not expected")

    contract = _contract()
    contract["route"] = {
        **contract["route"],
        "routing_decision": "CREATE_NEW_BATCH_PR",
        "target_pr": None,
        "target_branch": None,
    }
    contract["execution_scope"]["delivery_target"] = {
        **contract["execution_scope"]["delivery_target"],
        "expected_status": "DONE_PR_OPEN",
        "target_pr": None,
        "target_branch": None,
    }
    contract = attach_digest(contract)
    store = InMemoryRunStore()
    provider = _CreateProvider()
    clock = FrozenClock(datetime(2026, 8, 1, 21, 0, tzinfo=timezone.utc))
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
    run = watch_run(result["run"]["run_id"], store, provider=provider, clock=clock)
    run = watch_run(run["run_id"], store, provider=provider, clock=clock)
    assert run["state"] == "PASS"
    assert run["route"]["target_pr"] == 99123
    assert run["route"]["target_branch"] == "batch/agent-skills-issue-4293"
    assert run["route"]["target_provenance"] == "route+validated_provider_receipt"

    # HOLD / missing receipt must not invent targets
    record = {
        "route": {
            "routing_decision": "CREATE_NEW_BATCH_PR",
            "target_pr": None,
            "target_branch": None,
        }
    }
    _merge_observed_create_targets(record, {})
    assert record["route"]["target_pr"] is None
    assert record["route"].get("target_provenance") is None
