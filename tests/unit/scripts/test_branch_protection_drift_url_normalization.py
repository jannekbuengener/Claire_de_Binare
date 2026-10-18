"""Regression contracts for the compatibility-named main ruleset drift checker."""

from __future__ import annotations

from scripts.governance.check_branch_protection_drift import (
    build_apply_payload,
    collect_drift_paths,
    normalize,
)


def _ruleset_snapshot(
    *, integration_id: int = 15368, enforcement: str = "active"
) -> dict[str, object]:
    return {
        "id": 11617228,
        "name": "main-strict",
        "target": "branch",
        "source_type": "Repository",
        "source": "jannekbuengener/Claire_de_Binare",
        "enforcement": enforcement,
        "conditions": {"ref_name": {"exclude": [], "include": ["refs/heads/main"]}},
        "rules": [
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "dismiss_stale_reviews_on_push": False,
                    "required_reviewers": [],
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": False,
                    "require_extra_approval_for_unattributed_changes": False,
                    "allowed_merge_methods": ["squash", "rebase"],
                },
            },
            {"type": "deletion"},
            {"type": "required_linear_history"},
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": False,
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [
                        {
                            "context": "ci (Unit/Integration + Lint gesammelt)",
                            "integration_id": integration_id,
                        },
                        {"context": "policy-gate", "integration_id": integration_id},
                    ],
                },
            },
        ],
        "bypass_actors": [],
        "current_user_can_bypass": "never",
        "node_id": "volatile",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-10-18T00:00:00Z",
        "_links": {"self": {"href": "https://api.github.com/example"}},
    }


def test_ruleset_normalization_ignores_volatile_metadata_and_rule_order() -> None:
    baseline = _ruleset_snapshot()
    current = _ruleset_snapshot()
    current["updated_at"] = "later"
    current["node_id"] = "different"
    current["rules"] = list(reversed(current["rules"]))
    assert collect_drift_paths(normalize(baseline), normalize(current)) == []


def test_ruleset_required_check_integration_drift_is_not_masked() -> None:
    assert collect_drift_paths(
        normalize(_ruleset_snapshot()), normalize(_ruleset_snapshot(integration_id=7))
    )


def test_ruleset_enforcement_drift_is_not_masked() -> None:
    assert collect_drift_paths(
        normalize(_ruleset_snapshot()),
        normalize(_ruleset_snapshot(enforcement="disabled")),
    ) == ["enforcement"]


def test_ruleset_apply_payload_excludes_read_only_fields() -> None:
    payload = build_apply_payload(_ruleset_snapshot())
    assert payload["name"] == "main-strict"
    assert payload["enforcement"] == "active"
    assert payload["bypass_actors"] == []
    assert "id" not in payload
    assert "source" not in payload
    assert "current_user_can_bypass" not in payload
    assert "updated_at" not in payload
    assert any(rule["type"] == "required_status_checks" for rule in payload["rules"])


def test_ruleset_checker_creates_output_parent_directories(
    tmp_path, monkeypatch
) -> None:
    import json
    import sys
    import scripts.governance.check_branch_protection_drift as drift

    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    payload = _ruleset_snapshot()
    baseline.write_text(json.dumps(drift.normalize(payload)), encoding="utf-8")
    current.write_text(json.dumps(payload), encoding="utf-8")
    report = tmp_path / "nested" / "report.md"
    apply_out = tmp_path / "nested" / "apply.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_branch_protection_drift.py",
            "--baseline",
            str(baseline),
            "--current-json",
            str(current),
            "--report",
            str(report),
            "--apply-payload-out",
            str(apply_out),
        ],
    )
    assert drift.main() == 0
    assert report.exists()
    assert apply_out.exists()
