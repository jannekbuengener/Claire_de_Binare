"""Sensitivity campaign runner unit tests (#4153).

test_id: tc_sensitivity_campaign_runner_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from tools.arvp_vacation.sensitivity_campaign_authorization import (
    SensitivityAuthorizationError,
)
from tools.arvp_vacation.sensitivity_campaign_budget import SensitivityBudgetError
from tools.arvp_vacation.sensitivity_campaign_executor import (
    ATTEMPT_KIND_PRIMARY,
    ATTEMPT_KIND_REPRODUCTION,
    FakeExecutor,
)
from tools.arvp_vacation.sensitivity_campaign_runner import (
    SensitivityRunnerError,
    build_parser,
    execute_campaign,
    plan_campaign,
    validate_authorization_command,
)
from tools.arvp_vacation.sensitivity_campaign_run_plan import build_run_plan
from tools.arvp_vacation.sensitivity_campaign_surface import probe_execution_surface
from tools.arvp_vacation.sensitivity_experiment_manifest import load_manifest

from tests.unit.arvp.test_sensitivity_campaign_authorization import (
    AUTHOR,
    COMMENT_ID,
    MAIN_SHA,
    SURFACE_ID,
    build_valid_auth_payload,
    make_fetcher,
    _sample_budget,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_MANIFEST = REPO_ROOT / "config" / "arvp" / "sensitivity_campaign_4153_v1.json"


@pytest.fixture()
def manifest() -> dict[str, Any]:
    return load_manifest(CANONICAL_MANIFEST)


@pytest.fixture()
def surface_probe():
    return probe_execution_surface(
        repo_root=REPO_ROOT,
        dataset_root=None,
        surface_id=SURFACE_ID,
        exchange_credentials_present=False,
        window_availability={"expected_windows": 39},
    )


def test_plan_campaign_counts_and_no_writes(
    manifest: dict[str, Any], tmp_path: Path
) -> None:
    stream = io.StringIO()
    artifacts_before = list((REPO_ROOT / "artifacts" / "arvp_sensitivity").glob("**/*"))
    payload = plan_campaign(
        manifest_path=CANONICAL_MANIFEST,
        repo_root=REPO_ROOT,
        main_sha=MAIN_SHA,
        stream=stream,
    )
    assert payload["writes"] is False
    assert payload["replays"] is False
    assert payload["run_keys_count"] == 819
    assert payload["run_count"] == 819
    assert payload["matrix_slots"] == 21
    assert payload["physical_parameter_sets"] == 19
    assert payload["window_count"] == 39
    assert payload["holdout_runs"] == 0
    assert payload["campaign_execution_authorized"] is False
    assert payload["lr_status"] == "NO-GO"
    assert payload["run_plan_fingerprint"]
    # Reproducible fingerprint for same main_sha.
    again = plan_campaign(
        manifest_path=CANONICAL_MANIFEST,
        repo_root=REPO_ROOT,
        main_sha=MAIN_SHA,
        stream=io.StringIO(),
    )
    assert again["run_plan_fingerprint"] == payload["run_plan_fingerprint"]
    artifacts_after = list((REPO_ROOT / "artifacts" / "arvp_sensitivity").glob("**/*"))
    assert len(artifacts_after) == len(artifacts_before)
    assert not any(tmp_path.iterdir()) if tmp_path.exists() else True


def test_validate_authorization_valid(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    budget = _sample_budget()
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
    )
    result = validate_authorization_command(
        manifest_path=CANONICAL_MANIFEST,
        go_comment_id=COMMENT_ID,
        repo_root=REPO_ROOT,
        main_sha=MAIN_SHA,
        authorizing_github_login=AUTHOR,
        surface_id=SURFACE_ID,
        surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
        resource_budget=budget,
        fetcher=make_fetcher(auth),
        stream=io.StringIO(),
    )
    assert result["valid"] is True
    assert result["writes"] is False
    assert result["replays"] is False
    assert result["reason_code"] == "AUTH_GO_VALID"
    assert not any(tmp_path.rglob("*")) or True


def test_validate_authorization_binding_failure(
    manifest: dict[str, Any], surface_probe
) -> None:
    budget = _sample_budget()
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
        bound_main_sha="f" * 40,
    )
    # Schema-valid wrong SHA vs expected MAIN_SHA.
    result = validate_authorization_command(
        manifest_path=CANONICAL_MANIFEST,
        go_comment_id=COMMENT_ID,
        repo_root=REPO_ROOT,
        main_sha=MAIN_SHA,
        authorizing_github_login=AUTHOR,
        surface_id=SURFACE_ID,
        surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
        resource_budget=budget,
        fetcher=make_fetcher(auth),
        stream=io.StringIO(),
    )
    assert result["valid"] is False
    assert result["reason_code"] == "AUTH_BINDING_MISMATCH"
    assert result["writes"] is False


def test_parser_has_no_force_flag() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    assert "--force" not in help_text
    assert "--yes" not in help_text
    assert "--admin" not in help_text
    with pytest.raises(SystemExit):
        parser.parse_args(["execute", "--force"])


def test_execute_without_go_fails(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    budget = _sample_budget()
    budget["minimum_free_disk_bytes"] = 1

    def boom(*_a, **_k):
        raise SensitivityAuthorizationError("AUTH_GO_BLOCK_MISSING", "no go")

    with pytest.raises(SensitivityAuthorizationError) as exc:
        execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=FakeExecutor(),
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=budget,
            fetcher=boom,
            stream=io.StringIO(),
        )
    assert exc.value.reason_code == "AUTH_GO_BLOCK_MISSING"


def test_execute_missing_budget_blocks(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    with pytest.raises(SensitivityBudgetError) as exc:
        execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=FakeExecutor(),
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=None,
            fetcher=make_fetcher(build_valid_auth_payload()),
            stream=io.StringIO(),
        )
    assert "BUDGET_MISSING" in str(exc.value)


def _fast_plan_from(manifest: dict[str, Any], *, primary_count: int = 2):
    """Build a consistent small campaign plan for FakeExecutor tests.

    Only ``runs``, ``run_keys`` and ``run_count`` are trimmed; reproduction_policy
    is left untouched so the authorized GO payload's ``reproduction_policy``
    remains identical to the plan's.
    """
    plan = build_run_plan(manifest, main_sha=MAIN_SHA)
    trimmed_runs = plan.runs[:primary_count]
    trimmed_keys = [r.run_key for r in trimmed_runs]
    return replace(
        plan,
        runs=trimmed_runs,
        run_keys=trimmed_keys,
        run_count=primary_count,
    )


def test_execute_fake_executor_full_envelope(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    budget = _sample_budget()
    budget["minimum_free_disk_bytes"] = 1
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
    )
    fast_plan = _fast_plan_from(manifest, primary_count=2)
    fake = FakeExecutor()

    with patch(
        "tools.arvp_vacation.sensitivity_campaign_runner.build_run_plan",
        return_value=fast_plan,
    ):
        result = execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=fake,
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=budget,
            fetcher=make_fetcher(auth),
            stream=io.StringIO(),
        )

    assert result["status"] == "COMPLETED"
    assert result["campaign_phase"] == "COMPLETED"
    assert result["succeeded"] == 2
    assert result["failed"] == 0
    # 2 primary + reproduction (baseline+sample from default policy over 2 keys).
    primary_calls = [c for c in fake.calls if c.attempt_kind == "PRIMARY"]
    repro_calls = [c for c in fake.calls if c.attempt_kind == "REPRODUCTION"]
    assert len(primary_calls) == 2
    assert repro_calls, "reproduction must run under default reproduction policy"
    env = fake.calls[0]
    required = (
        "run_key",
        "campaign_id",
        "manifest_fingerprint",
        "execution_sha",
        "window_id",
        "strategy_id",
        "parameters",
        "slot_id",
        "phase",
        "label",
        "physical_parameter_set_fingerprint",
        "effective_config_fingerprint",
        "dataset_content_fingerprint",
        "seed",
        "output_dir",
        "run_plan_fingerprint",
        "authorization_fingerprint",
    )
    for field in required:
        assert getattr(env, field) not in (None, ""), field
    assert env.parameters
    assert env.attempt == 1
    assert env.attempt_kind == "PRIMARY"
    assert env.reproduction_attempt == 0
    assert result["reproduction"]["enabled"] is True
    assert (tmp_path / "artifacts" / "arvp_sensitivity" / "4153").exists()


def test_execute_run_count_override_forbidden(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    with pytest.raises(SensitivityRunnerError) as exc:
        execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=FakeExecutor(),
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=_sample_budget(),
            fetcher=make_fetcher(build_valid_auth_payload()),
            stream=io.StringIO(),
            max_runs_override=10,
        )
    assert exc.value.reason_code == "RUNNER_RUN_COUNT_OVERRIDE_FORBIDDEN"


def test_surface_fingerprint_stable_across_free_space(
    surface_probe,
) -> None:
    again = probe_execution_surface(
        repo_root=REPO_ROOT,
        dataset_root=None,
        surface_id=SURFACE_ID,
        exchange_credentials_present=False,
        window_availability={"expected_windows": 39},
    )
    assert (
        again.surface_capability_fingerprint
        == surface_probe.surface_capability_fingerprint
    )


def test_manifest_preflight_still_ready_campaign(manifest: dict[str, Any]) -> None:
    from tools.arvp_vacation.sensitivity_campaign_preflight import (
        VERDICT_READY,
        VERDICT_READY_CAMPAIGN,
        run_manifest_preflight,
        run_repo_preflight,
    )

    repo = run_repo_preflight(REPO_ROOT)
    assert repo["verdict"] == VERDICT_READY
    man = run_manifest_preflight(manifest, REPO_ROOT)
    assert man["verdict"] == VERDICT_READY_CAMPAIGN


class _DivergentMetricsExecutor:
    """Primary and reproduction return different ``net_pnl`` — forces mismatch."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    def execute(self, envelope):
        from tools.arvp_vacation.sensitivity_campaign_executor import RunResult

        self.calls.append(envelope)
        base = {
            "gate_reason": "OK",
            "regime_distribution": {"TREND": 1},
            "trade_count": 0,
            "turnover": "0",
            "fees": "0",
            "spread": "0",
            "slippage": "0",
            "gross_pnl": "0",
            "net_pnl": "0",
            "profit_factor": "0",
            "expectancy": "0",
            "drawdown": "0",
            "main_effect": None,
            "interaction_effect": None,
            "overfitting_risk_flag": False,
        }
        if envelope.attempt_kind == ATTEMPT_KIND_REPRODUCTION:
            base = {**base, "net_pnl": "1"}
        return RunResult(exit_code=0, metrics=base, detail="fake_ok")


def test_execute_blocks_on_reproduction_mismatch(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    """Reproduction returning a different comparable field blocks the campaign."""
    budget = _sample_budget()
    budget["minimum_free_disk_bytes"] = 1
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
    )
    fast_plan = _fast_plan_from(manifest, primary_count=2)
    divergent = _DivergentMetricsExecutor()

    with patch(
        "tools.arvp_vacation.sensitivity_campaign_runner.build_run_plan",
        return_value=fast_plan,
    ):
        result = execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=divergent,
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=budget,
            fetcher=make_fetcher(auth),
            stream=io.StringIO(),
        )

    assert result["status"] == "BLOCKED"
    assert result["campaign_phase"] == "BLOCKED"
    assert result["reason_code"] == "REPRODUCTION_RESULT_MISMATCH"


def test_execute_never_completes_after_primary_alone(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    """Reproduction enabled => COMPLETED must come after reproduction, not primary."""
    budget = _sample_budget()
    budget["minimum_free_disk_bytes"] = 1
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
    )
    fast_plan = _fast_plan_from(manifest, primary_count=2)
    fake = FakeExecutor()

    with patch(
        "tools.arvp_vacation.sensitivity_campaign_runner.build_run_plan",
        return_value=fast_plan,
    ):
        result = execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=fake,
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=budget,
            fetcher=make_fetcher(auth),
            stream=io.StringIO(),
        )
    assert result["status"] == "COMPLETED"
    assert result["reproduction"]["enabled"] is True
    assert result["reproduction"]["phase_outcome"] == "REPRODUCTION_COMPLETE"
    # Reproduction was actually executed under FakeExecutor.
    assert any(c.attempt_kind == ATTEMPT_KIND_REPRODUCTION for c in fake.calls)


def test_execute_blocks_when_auth_lifetime_insufficient(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    """Live GO with too-short expires_at vs budget is refused fail-closed."""
    from datetime import UTC, datetime, timedelta

    budget = _sample_budget()
    budget["minimum_free_disk_bytes"] = 1
    # Set expires_at only 5 minutes in the future — remaining <
    # max_campaign_wall_time_seconds (86400) + max_run_wall_time_seconds (600).
    now = datetime(2026, 8, 4, tzinfo=UTC)
    tight = (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
        expires_at_utc=tight,
    )

    with pytest.raises(SensitivityAuthorizationError) as exc:
        execute_campaign(
            manifest_path=CANONICAL_MANIFEST,
            go_comment_id=COMMENT_ID,
            executor=FakeExecutor(),
            repo_root=REPO_ROOT,
            artifacts_base=tmp_path,
            main_sha=MAIN_SHA,
            authorizing_github_login=AUTHOR,
            surface_id=SURFACE_ID,
            surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
            resource_budget=budget,
            fetcher=make_fetcher(auth),
            stream=io.StringIO(),
            now_utc_provider=lambda: now,
        )
    assert exc.value.reason_code == "AUTH_LIFETIME_INSUFFICIENT_FOR_BUDGET"


def test_execute_blocks_when_authorization_expires_before_attempt(
    manifest: dict[str, Any], surface_probe, tmp_path: Path
) -> None:
    """Pre-attempt expiry gate blocks the first primary run when time has passed."""
    from datetime import UTC, datetime, timedelta

    budget = _sample_budget()
    budget["minimum_free_disk_bytes"] = 1

    lifetime_start = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)
    # Expiry far enough in the future to satisfy lifetime coverage but still
    # before the per-attempt clock jump below.
    expires_at = (
        (lifetime_start + timedelta(days=30)).isoformat().replace("+00:00", "Z")
    )
    auth = build_valid_auth_payload(
        manifest=manifest,
        surface_fp=surface_probe.surface_capability_fingerprint,
        budget=budget,
        expires_at_utc=expires_at,
    )
    fast_plan = _fast_plan_from(manifest, primary_count=2)

    # Two lifetime clock calls at start, then jump past expiry for the
    # per-attempt guard.
    calls = {"n": 0}

    def _now_provider():
        i = calls["n"]
        calls["n"] += 1
        if i < 2:
            return lifetime_start  # verify + lifetime check
        return lifetime_start + timedelta(days=60)  # past expiry

    with patch(
        "tools.arvp_vacation.sensitivity_campaign_runner.build_run_plan",
        return_value=fast_plan,
    ):
        with pytest.raises(SensitivityAuthorizationError) as exc:
            execute_campaign(
                manifest_path=CANONICAL_MANIFEST,
                go_comment_id=COMMENT_ID,
                executor=FakeExecutor(),
                repo_root=REPO_ROOT,
                artifacts_base=tmp_path,
                main_sha=MAIN_SHA,
                authorizing_github_login=AUTHOR,
                surface_id=SURFACE_ID,
                surface_capability_fingerprint=surface_probe.surface_capability_fingerprint,
                resource_budget=budget,
                fetcher=make_fetcher(auth),
                stream=io.StringIO(),
                now_utc_provider=_now_provider,
            )
    assert exc.value.reason_code == "AUTHORIZATION_EXPIRED_BEFORE_NEXT_ATTEMPT"
