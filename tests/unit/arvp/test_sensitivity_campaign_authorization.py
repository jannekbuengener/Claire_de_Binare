"""Owner-GO authorization contract tests (#4153).

test_id: tc_sensitivity_campaign_authorization_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tools.arvp_vacation.sensitivity_campaign_authorization import (
    AUTH_SCHEMA_VERSION,
    DEFAULT_REPO,
    GO_FENCE_END,
    GO_FENCE_START,
    GO_STATUS,
    GitHubComment,
    ISSUE_NUMBER,
    SensitivityAuthorizationError,
    assert_absolute_bans_intact,
    authorization_policy_defaults,
    campaign_execution_requires_owner_go,
    fingerprint_authorization_payload,
    parse_go_payload_from_comment_body,
    validate_authorization_payload,
    verify_owner_go_comment,
)
from tools.arvp_vacation.sensitivity_campaign_run_plan import build_run_plan
from tools.arvp_vacation.sensitivity_experiment_manifest import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_MANIFEST = REPO_ROOT / "config" / "arvp" / "sensitivity_campaign_4153_v1.json"
FIXTURE_AUTH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "arvp"
    / "sensitivity"
    / "execution_authorization_valid_v1.json"
)
MAIN_SHA = "a" * 40
COMMENT_ID = 999000001
AUTHOR = "jannekbuengener"
SURFACE_ID = "test-surface-local-v1"


def _sample_budget() -> dict[str, int]:
    return {
        "max_parallelism": 2,
        "max_in_flight_runs": 2,
        "max_attempts_per_run": 2,
        "max_run_wall_time_seconds": 600,
        "max_campaign_wall_time_seconds": 86400,
        "max_artifact_bytes": 50 * 1024**3,
        "minimum_free_disk_bytes": 1,
        "max_consecutive_failures": 5,
        "max_total_failures": 50,
        "log_retention_days": 30,
    }


def build_valid_auth_payload(
    *,
    manifest: dict[str, Any] | None = None,
    main_sha: str = MAIN_SHA,
    comment_id: int = COMMENT_ID,
    author: str = AUTHOR,
    surface_id: str = SURFACE_ID,
    surface_fp: str | None = None,
    budget: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    man = manifest or load_manifest(CANONICAL_MANIFEST)
    plan = build_run_plan(man, main_sha=main_sha)
    fp = surface_fp or ("b" * 64)
    payload: dict[str, Any] = {
        "schema_version": AUTH_SCHEMA_VERSION,
        "status": GO_STATUS,
        "repository": DEFAULT_REPO,
        "issue": ISSUE_NUMBER,
        "github_comment_id": comment_id,
        "authorizing_github_login": author,
        "bound_main_sha": main_sha,
        "manifest_path": "config/arvp/sensitivity_campaign_4153_v1.json",
        "manifest_id": "arvp-sensitivity-4153-v1",
        "manifest_fingerprint": plan.manifest_fingerprint,
        "correctness_baseline_sha": man["correctness_baseline_sha"],
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "runner_contract_version": "cdb.sensitivity_campaign_runner.v1",
        "strategy_set": ["primary_breakout_v1"],
        "selection_sha256": man["development_windows"]["selection_sha256"],
        "window_count": 39,
        "matrix_slots": 21,
        "run_keys": 819,
        "expected_run_count": 819,
        "max_run_count": 819,
        "execution_surface_id": surface_id,
        "surface_capability_fingerprint": fp,
        "resource_budget": dict(budget or _sample_budget()),
        "evidence_namespace": "artifacts/arvp_sensitivity/4153",
        "resume_policy": plan.resume_policy,
        "reproduction_policy": plan.reproduction_policy,
        "analyzer_contract_version": "cdb.sensitivity_campaign_analyzer.v1",
        "granted_capabilities": ["campaign_execution"],
        "absolute_bans_unchanged": True,
        "expires_at_utc": None,
        "lr_status": "NO-GO",
        "notes": "unit-test GO payload",
    }
    payload.update(overrides)
    return payload


def build_go_comment_body(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, indent=2, sort_keys=True)
    return (
        "Owner GO for #4153 sensitivity campaign (unit test).\n\n"
        f"{GO_FENCE_START}\n{body}\n{GO_FENCE_END}\n"
    )


def make_fetcher(
    payload: dict[str, Any],
    *,
    author: str | None = None,
    issue: int = ISSUE_NUMBER,
    comment_id: int | None = None,
    repository: str = DEFAULT_REPO,
    body: str | None = None,
    assert_fetch_issue: int | None = None,
):
    cid = comment_id if comment_id is not None else int(payload["github_comment_id"])
    comment = GitHubComment(
        comment_id=cid,
        issue_number=issue,
        author_login=(
            author if author is not None else str(payload["authorizing_github_login"])
        ),
        body=body if body is not None else build_go_comment_body(payload),
        updated_at="2026-08-04T08:00:00Z",
        repository=repository,
    )
    expected_fetch_issue = (
        assert_fetch_issue if assert_fetch_issue is not None else issue
    )

    def _fetch(repo: str, issue_n: int, requested_id: int) -> GitHubComment:
        assert repo == repository
        assert issue_n == expected_fetch_issue
        assert requested_id == cid
        return comment

    return _fetch


@pytest.fixture()
def valid_payload() -> dict[str, Any]:
    return build_valid_auth_payload()


def test_fixture_schema_valid() -> None:
    payload = json.loads(FIXTURE_AUTH.read_text(encoding="utf-8"))
    validate_authorization_payload(payload)
    assert payload["schema_version"] == AUTH_SCHEMA_VERSION
    assert payload["status"] == GO_STATUS
    assert payload["lr_status"] == "NO-GO"


def test_parse_go_fence_happy_path(valid_payload: dict[str, Any]) -> None:
    body = build_go_comment_body(valid_payload)
    parsed = parse_go_payload_from_comment_body(body)
    assert parsed["github_comment_id"] == COMMENT_ID


def test_parse_go_fence_missing() -> None:
    with pytest.raises(SensitivityAuthorizationError) as exc:
        parse_go_payload_from_comment_body("no fence here")
    assert exc.value.reason_code == "AUTH_GO_BLOCK_MISSING"


def test_parse_go_fence_ambiguous(valid_payload: dict[str, Any]) -> None:
    one = build_go_comment_body(valid_payload)
    with pytest.raises(SensitivityAuthorizationError) as exc:
        parse_go_payload_from_comment_body(one + "\n" + one)
    assert exc.value.reason_code == "AUTH_GO_BLOCK_AMBIGUOUS"


def test_verify_valid_mocked_go_no_writes(
    valid_payload: dict[str, Any], tmp_path: Path
) -> None:
    before = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    result = verify_owner_go_comment(
        comment_id=COMMENT_ID,
        expected={
            "authorizing_github_login": AUTHOR,
            "bound_main_sha": MAIN_SHA,
            "manifest_fingerprint": valid_payload["manifest_fingerprint"],
            "run_plan_fingerprint": valid_payload["run_plan_fingerprint"],
            "execution_surface_id": SURFACE_ID,
            "surface_capability_fingerprint": valid_payload[
                "surface_capability_fingerprint"
            ],
            "resource_budget": valid_payload["resource_budget"],
        },
        fetcher=make_fetcher(valid_payload),
    )
    assert result["valid"] is True
    assert result["reason_code"] == "AUTH_GO_VALID"
    assert result["authorization_fingerprint"] == fingerprint_authorization_payload(
        valid_payload
    )
    after = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    assert after == before


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda p: {**p, "authorizing_github_login": "not-jannek"},
            "AUTH_AUTHOR_NOT_ALLOWLISTED",
        ),
        (
            lambda p: {**p, "bound_main_sha": "c" * 40},
            "AUTH_BINDING_MISMATCH",
        ),
        (
            lambda p: {**p, "run_plan_fingerprint": "d" * 64},
            "AUTH_BINDING_MISMATCH",
        ),
        (
            lambda p: {**p, "manifest_fingerprint": "e" * 64},
            "AUTH_BINDING_MISMATCH",
        ),
        (
            lambda p: {**p, "execution_surface_id": "other-surface"},
            "AUTH_BINDING_MISMATCH",
        ),
        (
            lambda p: {
                **p,
                "resource_budget": {**p["resource_budget"], "max_parallelism": 1},
            },
            "AUTH_BUDGET_MISMATCH",
        ),
    ],
)
def test_authorization_failures_reason_codes(
    valid_payload: dict[str, Any],
    mutate,
    expected_code: str,
) -> None:
    bad = mutate(copy.deepcopy(valid_payload))
    expected = {
        "authorizing_github_login": AUTHOR,
        "bound_main_sha": MAIN_SHA,
        "manifest_fingerprint": valid_payload["manifest_fingerprint"],
        "run_plan_fingerprint": valid_payload["run_plan_fingerprint"],
        "execution_surface_id": SURFACE_ID,
        "surface_capability_fingerprint": valid_payload[
            "surface_capability_fingerprint"
        ],
        "resource_budget": valid_payload["resource_budget"],
    }
    with pytest.raises(SensitivityAuthorizationError) as exc:
        verify_owner_go_comment(
            comment_id=COMMENT_ID,
            expected=expected,
            # Comment author stays OWNER so payload-author mismatch is isolated.
            fetcher=make_fetcher(bad, author=AUTHOR),
        )
    assert exc.value.reason_code == expected_code


def test_wrong_comment_author(valid_payload: dict[str, Any]) -> None:
    with pytest.raises(SensitivityAuthorizationError) as exc:
        verify_owner_go_comment(
            comment_id=COMMENT_ID,
            expected={"authorizing_github_login": AUTHOR},
            fetcher=make_fetcher(valid_payload, author="impostor"),
        )
    assert exc.value.reason_code == "AUTH_AUTHOR_NOT_ALLOWLISTED"


def test_wrong_issue_on_comment(valid_payload: dict[str, Any]) -> None:
    with pytest.raises(SensitivityAuthorizationError) as exc:
        verify_owner_go_comment(
            comment_id=COMMENT_ID,
            expected={"authorizing_github_login": AUTHOR},
            issue=4153,
            fetcher=make_fetcher(valid_payload, issue=1, assert_fetch_issue=4153),
        )
    assert exc.value.reason_code == "AUTH_ISSUE_MISMATCH"


def test_duplicate_json_keys_rejected(valid_payload: dict[str, Any]) -> None:
    body = (
        "Owner GO\n\n"
        f"{GO_FENCE_START}\n"
        '{\n  "granted_capabilities": ["campaign_execution"],\n'
        '  "granted_capabilities": ["paper"]\n}\n'
        f"{GO_FENCE_END}\n"
    )
    with pytest.raises(SensitivityAuthorizationError) as exc:
        parse_go_payload_from_comment_body(body)
    assert exc.value.reason_code == "AUTH_GO_BLOCK_DUPLICATE_KEY"


def test_missing_granted_capabilities_rejected(valid_payload: dict[str, Any]) -> None:
    bad = copy.deepcopy(valid_payload)
    del bad["granted_capabilities"]
    with pytest.raises(SensitivityAuthorizationError) as exc:
        validate_authorization_payload(bad)
    assert exc.value.reason_code in {
        "AUTH_GRANTED_CAPABILITIES_MISSING",
        "AUTH_PAYLOAD_SCHEMA_INVALID",
    }


def test_missing_absolute_bans_field_rejected(valid_payload: dict[str, Any]) -> None:
    bad = copy.deepcopy(valid_payload)
    del bad["absolute_bans_unchanged"]
    with pytest.raises(SensitivityAuthorizationError) as exc:
        validate_authorization_payload(bad)
    assert exc.value.reason_code in {
        "AUTH_ABSOLUTE_BANS_FIELD_MISSING",
        "AUTH_PAYLOAD_SCHEMA_INVALID",
    }


def test_extra_capability_rejected(valid_payload: dict[str, Any]) -> None:
    bad = copy.deepcopy(valid_payload)
    bad["granted_capabilities"] = ["campaign_execution", "paper"]
    with pytest.raises(SensitivityAuthorizationError) as exc:
        validate_authorization_payload(bad)
    assert exc.value.reason_code in {
        "AUTH_PAYLOAD_SCHEMA_INVALID",
        "AUTH_GRANTED_CAPABILITIES_INVALID",
    }


def test_expired_go_rejected(valid_payload: dict[str, Any]) -> None:
    from datetime import UTC, datetime

    bad = copy.deepcopy(valid_payload)
    bad["expires_at_utc"] = "2020-01-01T00:00:00Z"
    with pytest.raises(SensitivityAuthorizationError) as exc:
        validate_authorization_payload(bad, now_utc=datetime(2026, 8, 4, tzinfo=UTC))
    assert exc.value.reason_code == "AUTH_GO_EXPIRED"


def test_non_allowlisted_author_rejected(valid_payload: dict[str, Any]) -> None:
    with pytest.raises(SensitivityAuthorizationError) as exc:
        verify_owner_go_comment(
            comment_id=COMMENT_ID,
            expected={"authorizing_github_login": "random-collaborator"},
            fetcher=make_fetcher(valid_payload, author="random-collaborator"),
        )
    assert exc.value.reason_code == "AUTH_AUTHOR_NOT_ALLOWLISTED"


def test_comment_mutation_detected(valid_payload: dict[str, Any]) -> None:
    with pytest.raises(SensitivityAuthorizationError) as exc:
        verify_owner_go_comment(
            comment_id=COMMENT_ID,
            expected={"authorizing_github_login": AUTHOR},
            fetcher=make_fetcher(valid_payload),
            expected_comment_updated_at="2020-01-01T00:00:00Z",
        )
    assert exc.value.reason_code == "AUTH_COMMENT_MUTATED"


def test_draft_placeholder_is_not_authorizing() -> None:
    from tools.arvp_vacation.sensitivity_campaign_authorization import (
        draft_owner_go_placeholder_body,
    )

    body = draft_owner_go_placeholder_body()
    with pytest.raises(SensitivityAuthorizationError) as exc:
        parse_go_payload_from_comment_body(body)
    assert exc.value.reason_code == "AUTH_GO_BLOCK_MISSING"


def test_issue_url_parser() -> None:
    from tools.arvp_vacation.sensitivity_campaign_authorization import (
        parse_issue_number_from_issue_url,
    )

    assert (
        parse_issue_number_from_issue_url(
            "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/issues/4153"
        )
        == 4153
    )
    with pytest.raises(SensitivityAuthorizationError) as exc:
        parse_issue_number_from_issue_url("https://example.com/not-an-issue")
    assert exc.value.reason_code == "AUTH_COMMENT_ISSUE_URL_INVALID"


def test_absolute_bans_and_policy_defaults() -> None:
    man = load_manifest(CANONICAL_MANIFEST)
    assert_absolute_bans_intact(man)
    assert campaign_execution_requires_owner_go(man) is True
    policy = authorization_policy_defaults()
    assert policy["requires_external_owner_go"] is True
    assert "campaign_execution" in policy["conditionally_authorizable_capabilities"]
    assert "paper" in policy["absolute_bans"]
    assert "live" in policy["absolute_bans"]
    assert "jannekbuengener" in policy["authorizing_owner_allowlist"]
