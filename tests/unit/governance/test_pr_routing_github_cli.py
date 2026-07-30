"""Unit contracts for read-only gh inventory and dual-lock parsing (#4202)."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from tools.pr_routing.engine import LockState
from tools.pr_routing.github_cli import GhReadOnlyInventory, GitHubInventoryError
from tools.pr_routing.policy import load_policy

pytestmark = [pytest.mark.unit, pytest.mark.contract]

LOCK = (
    "LOCK: agent=Codex issue=#4202 batch_pr=#4210 "
    "ts=2026-07-30T12:00:00Z mode=batch-slice"
)
RESERVATION = (
    "LOCK_RESERVATION: agent=Codex issue=#4202 batch_pr=pending "
    "ts=2026-07-30T11:00:00Z mode=batch-slice"
)


def _comments(body: str) -> list[dict[str, str]]:
    return [{"body": body, "createdAt": "2026-07-30T12:00:00Z"}]


def test_matching_issue_and_pr_lock_pair_is_held_by_self() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    state = inventory.lock_state(
        issue_comments=_comments(LOCK),
        pr_comments=_comments(LOCK),
        current_agent="Codex",
    )
    assert state is LockState.HELD_BY_SELF


def test_one_sided_lock_is_partial_and_blocks() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    state = inventory.lock_state(
        issue_comments=_comments(LOCK),
        pr_comments=[],
        current_agent="Codex",
    )
    assert state is LockState.PARTIAL


def test_reservation_is_owned_and_foreign_reservation_blocks() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    assert (
        inventory._reservation_state(
            _comments(RESERVATION), issue_number=4202, current_agent="Codex"
        )
        is LockState.RESERVATION_HELD_BY_SELF
    )
    assert (
        inventory._reservation_state(
            _comments(RESERVATION), issue_number=4202, current_agent="Other"
        )
        is LockState.RESERVATION_HELD_BY_FOREIGN
    )


def test_unrelated_unlock_cannot_clear_lock() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    wrong_unlock = (
        "UNLOCK: agent=Codex issue=#999 batch_pr=#4210 "
        "ts=2026-07-30T13:00:00Z mode=batch-slice reason=handoff"
    )
    state = inventory.lock_state(
        issue_comments=_comments(LOCK) + _comments(wrong_unlock),
        pr_comments=_comments(LOCK),
        current_agent="Codex",
    )
    assert state is LockState.INVALID


def test_lock_cannot_be_overwritten_without_unlock() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    takeover = LOCK.replace("agent=Codex", "agent=Other").replace(
        "12:00:00Z", "13:00:00Z"
    )
    state = inventory.lock_state(
        issue_comments=_comments(LOCK) + _comments(takeover),
        pr_comments=_comments(LOCK) + _comments(takeover),
        current_agent="Other",
    )
    assert state is LockState.INVALID


def test_lock_pair_requires_identical_timestamp() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    later = LOCK.replace("12:00:00Z", "12:00:01Z")
    state = inventory.lock_state(
        issue_comments=_comments(LOCK),
        pr_comments=_comments(later),
        current_agent="Codex",
    )
    assert state is LockState.PARTIAL


def test_final_lock_consumes_reservation() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    assert (
        inventory._reservation_state(
            _comments(RESERVATION) + _comments(LOCK),
            issue_number=4202,
            current_agent="Other",
        )
        is LockState.UNLOCKED
    )


def test_pause_marker_in_owner_comment_parks_issue() -> None:
    payload = {
        "number": 4184,
        "title": "[RUNTIME] parked work",
        "body": "",
        "labels": [{"name": "runtime"}],
        "comments": [{"body": "status: PAUSED_RESOURCE_CAPACITY"}],
        "state": "OPEN",
        "url": "https://example.invalid/issues/4184",
    }

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=json.dumps(payload), stderr=""
        )

    inventory = GhReadOnlyInventory(repository="owner/repo", runner=runner)
    issue, _ = inventory.issue(4184, current_agent="Codex")
    assert issue.paused is True


def test_reference_to_other_parked_work_does_not_pause_issue() -> None:
    payload = {
        "number": 4202,
        "title": "[GOVERNANCE][PR-FLOW] Introduce PR Steward",
        "body": "Do not change parked work #4184.",
        "labels": [],
        "comments": [
            {"body": "Reservation exists; #4184 stays PAUSED_RESOURCE_CAPACITY."}
        ],
        "state": "OPEN",
        "url": "https://example.invalid/issues/4202",
    }

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=json.dumps(payload), stderr=""
        )

    inventory = GhReadOnlyInventory(repository="owner/repo", runner=runner)
    issue, _ = inventory.issue(4202, current_agent="Codex")
    assert issue.paused is False


def test_foreign_and_malformed_locks_fail_closed() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    foreign = LOCK.replace("agent=Codex", "agent=Other")
    assert (
        inventory.lock_state(
            issue_comments=_comments(foreign),
            pr_comments=_comments(foreign),
            current_agent="Codex",
        )
        is LockState.HELD_BY_FOREIGN
    )
    assert (
        inventory.lock_state(
            issue_comments=_comments("LOCK: malformed"),
            pr_comments=_comments("LOCK: malformed"),
            current_agent="Codex",
        )
        is LockState.INVALID
    )


def test_inventory_at_candidate_limit_is_incomplete() -> None:
    policy = load_policy()
    payload = [{"number": number} for number in range(1, policy.candidate_limit + 1)]

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=argv,
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    inventory = GhReadOnlyInventory(repository="owner/repo", runner=runner)
    with pytest.raises(GitHubInventoryError, match="pagination is incomplete"):
        inventory.open_pull_requests(policy)


def test_pull_request_changed_paths_paginates_all_filenames() -> None:
    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert "--paginate" in argv
        assert argv[-1] == ".[].filename"
        return subprocess.CompletedProcess(
            args=argv,
            returncode=0,
            stdout="docs/a.md\n.cursor/skills/x/SKILL.md\n",
            stderr="",
        )

    inventory = GhReadOnlyInventory(repository="owner/repo", runner=runner)
    assert inventory.pull_request_changed_paths(4219) == [
        "docs/a.md",
        ".cursor/skills/x/SKILL.md",
    ]


def test_reviewability_inventory_failure_is_incomplete() -> None:
    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=argv, returncode=1, stdout="", stderr="boom"
        )

    inventory = GhReadOnlyInventory(repository="owner/repo", runner=runner)
    paths, contents, complete = inventory._reviewability_inventory(
        pr_number=1,
        changed_files=25,
        head_ref_oid="abc",
        path_threshold=20,
    )
    assert paths is None
    assert contents is None
    assert complete is False


def test_reviewability_inventory_under_threshold_skips_paths() -> None:
    inventory = GhReadOnlyInventory(repository="owner/repo")
    paths, contents, complete = inventory._reviewability_inventory(
        pr_number=1,
        changed_files=5,
        head_ref_oid="abc",
        path_threshold=20,
    )
    assert paths is None
    assert contents is None
    assert complete is True
