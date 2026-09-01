"""Regression contracts for branch-protection URL comparison."""

from __future__ import annotations

from scripts.governance.check_branch_protection_drift import (
    collect_drift_paths,
    normalize,
    normalize_github_repository_url,
)


def _protection_snapshot(
    *, app_id: int = 4410232, strict: bool = True
) -> dict[str, object]:
    return {
        "url": "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/branches/main/protection",
        "required_status_checks": {
            "url": "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks",
            "contexts_url": "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks/contexts",
            "strict": strict,
            "checks": [{"context": "cdb-local-ci", "app_id": app_id}],
        },
        "required_pull_request_reviews": {
            "url": "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews",
            "required_approving_review_count": 0,
        },
        "required_signatures": {
            "url": "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_signatures",
            "enabled": False,
        },
        "enforce_admins": {
            "url": "https://api.github.com/repos/jannekbuengener/Claire_de_Binare/branches/main/protection/enforce_admins",
            "enabled": True,
        },
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }


def test_github_repository_url_owner_and_repo_casing_is_equivalent() -> None:
    baseline = _protection_snapshot()
    current = _protection_snapshot()
    current["url"] = str(current["url"]).replace("Claire_de_Binare", "claire_de_binare")
    checks = current["required_status_checks"]
    assert isinstance(checks, dict)
    checks["url"] = str(checks["url"]).replace("Claire_de_Binare", "claire_de_binare")
    checks["contexts_url"] = str(checks["contexts_url"]).replace(
        "Claire_de_Binare", "claire_de_binare"
    )
    reviews = current["required_pull_request_reviews"]
    assert isinstance(reviews, dict)
    reviews["url"] = str(reviews["url"]).replace("Claire_de_Binare", "claire_de_binare")
    signatures = current["required_signatures"]
    assert isinstance(signatures, dict)
    signatures["url"] = str(signatures["url"]).replace(
        "Claire_de_Binare", "claire_de_binare"
    )
    admins = current["enforce_admins"]
    assert isinstance(admins, dict)
    admins["url"] = str(admins["url"]).replace("Claire_de_Binare", "claire_de_binare")

    assert collect_drift_paths(normalize(baseline), normalize(current)) == []


def test_normalization_is_limited_to_standard_github_repository_urls() -> None:
    assert (
        normalize_github_repository_url(
            "https://api.github.com/repos/Owner/Repository/branches/main/protection"
        )
        == "https://api.github.com/repos/owner/repository/branches/main/protection"
    )
    assert normalize_github_repository_url("https://example.test/Owner/Repository") == (
        "https://example.test/Owner/Repository"
    )
    assert normalize_github_repository_url("https://api.github.com/users/Owner") == (
        "https://api.github.com/users/Owner"
    )


def test_url_shaped_required_check_context_remains_case_sensitive() -> None:
    baseline = _protection_snapshot()
    current = _protection_snapshot()
    baseline_checks = baseline["required_status_checks"]
    current_checks = current["required_status_checks"]
    assert isinstance(baseline_checks, dict)
    assert isinstance(current_checks, dict)
    baseline_checks["checks"] = [
        {
            "context": "https://api.github.com/repos/Owner/Repository/check",
            "app_id": 4410232,
        }
    ]
    current_checks["checks"] = [
        {
            "context": "https://api.github.com/repos/owner/repository/check",
            "app_id": 4410232,
        }
    ]

    assert collect_drift_paths(normalize(baseline), normalize(current)) == [
        "required_status_checks.checks[0].context"
    ]


def test_url_shaped_required_status_context_list_remains_case_sensitive() -> None:
    baseline = {
        "required_status_checks": {
            "contexts": ["https://api.github.com/repos/Owner/Repository/check"]
        }
    }
    current = {
        "required_status_checks": {
            "contexts": ["https://api.github.com/repos/owner/repository/check"]
        }
    }

    assert collect_drift_paths(normalize(baseline), normalize(current)) == [
        "required_status_checks.contexts[0]"
    ]


def test_material_required_check_app_id_drift_is_not_masked() -> None:
    assert collect_drift_paths(
        normalize(_protection_snapshot()), normalize(_protection_snapshot(app_id=7))
    ) == ["required_status_checks.checks[0].app_id"]


def test_material_required_check_context_drift_is_not_masked() -> None:
    current = _protection_snapshot()
    checks = current["required_status_checks"]
    assert isinstance(checks, dict)
    checks["checks"] = [{"context": "different-check", "app_id": 4410232}]

    assert collect_drift_paths(
        normalize(_protection_snapshot()), normalize(current)
    ) == ["required_status_checks.checks[0].context"]


def test_material_strict_force_push_and_delete_drift_is_not_masked() -> None:
    current = _protection_snapshot(strict=False)
    admins = current["enforce_admins"]
    assert isinstance(admins, dict)
    current["enforce_admins"] = {**admins, "enabled": False}
    current["allow_force_pushes"] = {"enabled": True}
    current["allow_deletions"] = {"enabled": True}

    assert collect_drift_paths(
        normalize(_protection_snapshot()), normalize(current)
    ) == [
        "allow_deletions.enabled",
        "allow_force_pushes.enabled",
        "enforce_admins.enabled",
        "required_status_checks.strict",
    ]
