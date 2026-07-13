from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest
import yaml

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "dependabot_autopilot_classifier.py"
)
ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "dependabot-autopilot-allowlist.yml"
)

SPEC = importlib.util.spec_from_file_location(
    "dependabot_autopilot_classifier", SCRIPT_PATH
)
assert SPEC is not None
classifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = classifier
assert SPEC.loader is not None
SPEC.loader.exec_module(classifier)

Facts = classifier.DependabotAutopilotFacts
RequiredCheckFact = classifier.RequiredCheckFact
Policy = classifier.parse_allowlist_policy


def _load_policy() -> classifier.AllowlistPolicy:
    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return Policy(raw)


def _checks(
    *, policy_ok: bool = True, ci_ok: bool = True
) -> tuple[RequiredCheckFact, ...]:
    checks = [
        RequiredCheckFact("policy-gate", "success" if policy_ok else "failure"),
        RequiredCheckFact(
            "ci (Unit/Integration + Lint gesammelt)",
            "success" if ci_ok else "pending",
        ),
    ]
    return tuple(checks)


def _facts(**overrides: object) -> Facts:
    base = {
        "pr_author": "dependabot[bot]",
        "base_branch": "main",
        "head_branch": "dependabot/pip/ruff-0.15.21",
        "is_draft": False,
        "labels": (),
        "head_sha": "abc123",
        "commit_count": 1,
        "commit_authors": ("dependabot[bot]",),
        "changed_files": ("requirements-dev.txt",),
        "required_checks": _checks(),
        "branch_is_current": True,
        "merge_state": "CLEAN",
        "ecosystem": "pip",
        "package_name": "ruff",
        "dependency_type": "direct:development",
        "update_type": "version-update:semver-patch",
        "current_version": "0.15.20",
        "target_version": "0.15.21",
        "metadata_complete": True,
        "diff_verified": True,
        "range_change": False,
        "date_versioned": False,
        "api_error": False,
        "execution_mode": "report_only",
        "kill_switch_enabled": False,
    }
    base.update(overrides)
    return Facts(**base)


def test_allowlisted_ruff_patch_report_only_is_eligible_not_merge_authorized() -> None:
    result = classifier.classify_dependabot_pr(_facts(), _load_policy())

    assert result.classification == "ELIGIBLE"
    assert result.action == "REPORT_ONLY"
    assert result.merge_authorized is False
    assert classifier.REASON_ELIGIBLE in result.reason_codes
    assert classifier.REASON_REPORT_ONLY in result.reason_codes


def test_kill_switch_false_prevents_merge_authorization_in_phase_mode() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(execution_mode="phase1", kill_switch_enabled=False),
        _load_policy(),
    )

    assert result.classification == "ELIGIBLE"
    assert result.action == "REPORT_ONLY"
    assert result.merge_authorized is False
    assert classifier.REASON_AUTOMERGE_DISABLED in result.reason_codes


def test_phase1_with_kill_switch_true_yields_merge_candidate_only() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(execution_mode="phase1", kill_switch_enabled=True),
        _load_policy(),
    )

    assert result.classification == "ELIGIBLE"
    assert result.action == "MERGE_CANDIDATE"
    assert result.merge_authorized is True
    assert classifier.REASON_ELIGIBLE in result.reason_codes


def test_major_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(update_type="version-update:semver-major"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_UPDATE_TYPE in result.reason_codes


def test_minor_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(update_type="version-update:semver-minor"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_UPDATE_TYPE in result.reason_codes


def test_range_change_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(range_change=True), _load_policy()
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_RANGE in result.reason_codes


def test_date_version_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(date_versioned=True, target_version="2026.7.10"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DATE_VERSION in result.reason_codes


def test_docker_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            ecosystem="docker",
            package_name="postgres",
            changed_files=("services/risk/Dockerfile",),
            dependency_type="direct:production",
            update_type="version-update:semver-patch",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DOCKER in result.reason_codes


def test_database_compose_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            ecosystem="docker-compose",
            package_name="postgres",
            changed_files=("infrastructure/compose/docker-compose.yml",),
            dependency_type="direct:production",
            update_type="version-update:semver-patch",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DOCKER in result.reason_codes


def test_runtime_requirements_txt_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            package_name="redis",
            changed_files=("requirements.txt",),
            dependency_type="direct:production",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_RUNTIME in result.reason_codes


def test_github_actions_update_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(
            ecosystem="github-actions",
            package_name="actions/stale",
            changed_files=(".github/workflows/stale.yml",),
            dependency_type="direct:production",
            update_type="version-update:semver-patch",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_ACTIONS in result.reason_codes


def test_non_dependabot_author_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(pr_author="jannekbuengener"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_AUTHOR in result.reason_codes


def test_wrong_base_branch_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(base_branch="develop"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_BASE in result.reason_codes


def test_wrong_head_branch_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(head_branch="feature/ruff-bump"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_HEAD in result.reason_codes


def test_two_commits_hold() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_count=2),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_COUNT in result.reason_codes


def test_human_commit_author_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(commit_authors=("dependabot[bot]", "jannekbuengener")),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_AUTHOR in result.reason_codes


def test_additional_changed_file_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(changed_files=("requirements-dev.txt", "pyproject.toml")),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_FILE in result.reason_codes


def test_diff_not_verified_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(diff_verified=False),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DIFF in result.reason_codes


def test_incomplete_metadata_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(metadata_complete=False),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_METADATA in result.reason_codes


def test_missing_required_check_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(required_checks=(RequiredCheckFact("policy-gate", "success"),)),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CHECK_MISSING in result.reason_codes


def test_failed_required_check_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(required_checks=_checks(ci_ok=False)),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_CHECK_FAIL in result.reason_codes


def test_branch_not_current_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(branch_is_current=False),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_BRANCH in result.reason_codes


@pytest.mark.parametrize("merge_state", ["BEHIND", "BLOCKED", "DIRTY", "UNKNOWN"])
def test_non_clean_merge_state_holds(merge_state: str) -> None:
    result = classifier.classify_dependabot_pr(
        _facts(merge_state=merge_state),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_MERGE_STATE in result.reason_codes


def test_api_error_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(api_error=True),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_API in result.reason_codes


def test_unknown_package_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(package_name="unknown-package"),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_PACKAGE in result.reason_codes


def test_invalid_allowlist_holds() -> None:
    invalid = Policy({"schema_version": 99, "entries": {}})
    result = classifier.classify_dependabot_pr(_facts(), invalid)

    assert result.classification == "HOLD"
    assert classifier.REASON_POLICY in result.reason_codes


def test_manual_review_label_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(labels=("dependencies:manual-review",)),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_MANUAL_REVIEW in result.reason_codes


def test_draft_pr_holds() -> None:
    result = classifier.classify_dependabot_pr(
        _facts(is_draft=True),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_DRAFT in result.reason_codes


def test_repeated_evaluation_is_deterministic() -> None:
    policy = _load_policy()
    facts = _facts()
    first = classifier.classify_dependabot_pr(facts, policy)
    second = classifier.classify_dependabot_pr(facts, policy)

    assert first == second


def test_anonymized_live_regression_fixture_two_commits_holds() -> None:
    """Mirrors live #4049: ruff patch + merge commit + behind merge state."""
    result = classifier.classify_dependabot_pr(
        _facts(
            head_branch="dependabot/pip/ruff-0.15.21",
            commit_count=2,
            commit_authors=("dependabot[bot]", "jannekbuengener"),
            changed_files=("requirements-dev.txt",),
            branch_is_current=False,
            merge_state="BEHIND",
        ),
        _load_policy(),
    )

    assert result.classification == "HOLD"
    assert classifier.REASON_COMMIT_COUNT in result.reason_codes
    assert classifier.REASON_COMMIT_AUTHOR in result.reason_codes
    assert classifier.REASON_BRANCH in result.reason_codes
    assert classifier.REASON_MERGE_STATE in result.reason_codes
