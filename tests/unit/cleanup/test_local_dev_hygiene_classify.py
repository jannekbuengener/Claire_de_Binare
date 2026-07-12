from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.cleanup.local_dev_hygiene_classify import (
    Candidate,
    build_candidates,
    classify_duplicate_repos,
    classify_pattern_group,
    parse_scan_as_of,
    summarize_reclaim,
    validate_candidates,
)

FIXED_SCAN_AS_OF = datetime(2026, 7, 12, 12, 0, 0, tzinfo=UTC)


def _base_inventory() -> dict:
    return {
        "schema_version": "local_dev_workspace_inventory.v1",
        "scan_as_of_utc": FIXED_SCAN_AS_OF.isoformat().replace("+00:00", "Z"),
        "roots": [
            {
                "path": "D:\\Dev\\Workspaces\\Repos",
                "pattern_groups": [
                    {
                        "pattern_id": "venv",
                        "size_bytes": 300_000_000,
                        "hit_count": 1,
                    },
                    {
                        "pattern_id": "governance_work",
                        "size_bytes": 5_000_000,
                        "hit_count": 2,
                    },
                    {
                        "pattern_id": "temp_dirs",
                        "size_bytes": 70_000_000,
                        "hit_count": 1,
                    },
                ],
                "top_directories": [],
            }
        ],
        "worktrees": [
            {
                "path": "D:\\Dev\\Workspaces\\Repos\\Claire_de_Binare",
                "branch": "main",
                "head": "abc123",
            }
        ],
        "git_repositories": [],
    }


def _base_config() -> dict:
    return {
        "classification_rules": [
            {
                "rule_id": "protected_worktree",
                "classification": "PROTECTED",
                "confidence": "high",
                "match": "is_worktree",
            },
            {
                "rule_id": "keep_provenance_governance",
                "classification": "KEEP_PROVENANCE",
                "confidence": "high",
                "match": "pattern_id",
                "pattern_id": "governance_work",
                "reason": "governance provenance",
                "required_approval": "none",
            },
            {
                "rule_id": "regenerable_venv",
                "classification": "REGENERABLE",
                "confidence": "high",
                "match": "pattern_id",
                "pattern_id": "venv",
                "recovery_method": "venv rebuild",
                "risk": "low",
                "required_approval": "human_go_regenerable",
            },
            {
                "rule_id": "delete_candidate_temp",
                "classification": "DELETE_CANDIDATE",
                "confidence": "medium",
                "match": "pattern_id",
                "pattern_id": "temp_dirs",
                "recovery_method": "regenerate",
                "risk": "medium",
                "required_approval": "human_go_delete",
            },
        ],
        "secret_path_patterns": [".env"],
    }


@pytest.mark.unit
def test_parse_scan_as_of_uses_inventory_timestamp() -> None:
    inventory = _base_inventory()
    parsed = parse_scan_as_of(inventory)
    assert parsed == FIXED_SCAN_AS_OF


@pytest.mark.unit
def test_worktree_classified_protected() -> None:
    candidates = build_candidates(_base_inventory(), _base_config())
    protected = [c for c in candidates if c.classification == "PROTECTED"]
    assert protected
    assert all(c.required_approval == "none" for c in protected)


@pytest.mark.unit
def test_pattern_group_regenerable_venv() -> None:
    item = classify_pattern_group(
        pattern_id="venv",
        size_bytes=100,
        rules=_base_config()["classification_rules"],
    )
    assert item is not None
    assert item.classification == "REGENERABLE"
    assert item.confidence == "high"


@pytest.mark.unit
def test_governance_pattern_keep_provenance() -> None:
    candidates = build_candidates(_base_inventory(), _base_config())
    gov = next(c for c in candidates if c.pattern_id == "governance_work")
    assert gov.classification == "KEEP_PROVENANCE"


@pytest.mark.unit
def test_deduplicate_requires_clean_worktree_and_same_signature() -> None:
    repos = [
        {
            "path": "D:\\Dev\\Workspaces\\Repos\\alpha",
            "remote_url": "https://github.com/org/repo.git",
            "head_commit": "deadbeef",
            "is_clean": True,
        },
        {
            "path": "D:\\Dev\\Workspaces\\Repos\\alpha-copy",
            "remote_url": "https://github.com/org/repo.git",
            "head_commit": "deadbeef",
            "is_clean": True,
        },
    ]
    candidates = classify_duplicate_repos(repos)
    assert len(candidates) == 1
    assert candidates[0].classification == "DEDUPLICATE"
    assert candidates[0].dedupe_evidence is not None


@pytest.mark.unit
def test_duplicate_without_clean_tree_is_quarantine() -> None:
    repos = [
        {
            "path": "D:\\Dev\\Workspaces\\Repos\\alpha",
            "remote_url": "https://github.com/org/repo.git",
            "head_commit": "deadbeef",
            "is_clean": True,
        },
        {
            "path": "D:\\Dev\\Workspaces\\Repos\\alpha-dirty",
            "remote_url": "https://github.com/org/repo.git",
            "head_commit": "deadbeef",
            "is_clean": False,
        },
    ]
    candidates = classify_duplicate_repos(repos)
    assert len(candidates) == 1
    assert candidates[0].classification == "QUARANTINE_REVIEW"


@pytest.mark.unit
def test_duplicate_without_remote_commit_is_quarantine() -> None:
    repos = [
        {"path": "D:\\Dev\\Workspaces\\Repos\\a", "remote_url": None, "head_commit": None},
        {"path": "D:\\Dev\\Workspaces\\Repos\\b", "remote_url": None, "head_commit": None},
    ]
    candidates = classify_duplicate_repos(repos)
    assert candidates
    assert all(c.classification == "QUARANTINE_REVIEW" for c in candidates)


@pytest.mark.unit
def test_validate_candidates_required_fields() -> None:
    candidate = Candidate(
        path="pattern:venv",
        size=1,
        last_relevant_change=None,
        classification="REGENERABLE",
        reason="test",
        estimated_reclaim=1,
        recovery_method="rebuild",
        risk="low",
        confidence="high",
        required_approval="human_go_regenerable",
        pattern_id="venv",
    )
    validate_candidates([candidate])


@pytest.mark.unit
def test_reclaim_summary_buckets_confidence() -> None:
    candidates = [
        Candidate(
            path="pattern:venv",
            size=1_000,
            last_relevant_change=None,
            classification="REGENERABLE",
            reason="r",
            estimated_reclaim=1_000,
            recovery_method="rebuild",
            risk="low",
            confidence="high",
            required_approval="human_go_regenerable",
        ),
        Candidate(
            path="pattern:temp_dirs",
            size=500,
            last_relevant_change=None,
            classification="DELETE_CANDIDATE",
            reason="r",
            estimated_reclaim=500,
            recovery_method="delete",
            risk="medium",
            confidence="medium",
            required_approval="human_go_delete",
        ),
    ]
    summary = summarize_reclaim(candidates)
    assert summary["estimated_reclaim_bytes_by_confidence"]["high"] == 1_000
    assert summary["estimated_reclaim_bytes_by_confidence"]["medium"] == 500
