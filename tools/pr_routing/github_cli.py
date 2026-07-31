"""Read-only GitHub inventory adapter using only the authenticated gh CLI."""

from __future__ import annotations

import base64
import json
import re
import subprocess
from datetime import datetime
from typing import Any, Callable

from tools.pr_routing.engine import CandidatePullRequest, IssueFacts, LockState
from tools.pr_routing.policy import RoutingPolicy
from tools.pr_routing.reviewability import classify_skill_path

Runner = Callable[..., subprocess.CompletedProcess[str]]

LOCK_RE = re.compile(
    r"^LOCK: agent=(?P<agent>\S+) issue=#(?P<issue>[1-9][0-9]*) "
    r"batch_pr=#(?P<pr>[1-9][0-9]*) ts=(?P<ts>\S+) mode=batch-slice$"
)
RESERVATION_RE = re.compile(
    r"^LOCK_RESERVATION: agent=(?P<agent>\S+) issue=#(?P<issue>[1-9][0-9]*) "
    r"batch_pr=pending ts=(?P<ts>\S+) mode=batch-slice$"
)
UNLOCK_RE = re.compile(
    r"^UNLOCK: agent=(?P<agent>\S+) issue=#(?P<issue>[1-9][0-9]*) "
    r"batch_pr=#(?P<pr>[1-9][0-9]*) ts=(?P<ts>\S+) mode=batch-slice "
    r"reason=(?P<reason>\S+)$"
)
PAUSED_STATE_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:status:\s*)?(?:PAUSED_[A-Z0-9_]+|PARKED)\s*$"
)


class GitHubInventoryError(RuntimeError):
    """Raised when the live GitHub inventory is incomplete or ambiguous."""


def _default_runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, **kwargs)


class GhReadOnlyInventory:
    def __init__(
        self,
        *,
        repository: str,
        runner: Runner = _default_runner,
        timeout_seconds: int = 30,
    ) -> None:
        self.repository = repository
        self._runner = runner
        self.timeout_seconds = timeout_seconds

    def _json(self, argv: list[str]) -> Any:
        try:
            result = self._runner(
                argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitHubInventoryError(f"gh inventory command failed: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or "").strip()
            raise GitHubInventoryError(
                f"gh inventory command returned {result.returncode}: {detail}"
            )
        try:
            return json.loads(result.stdout or "null")
        except json.JSONDecodeError as exc:
            raise GitHubInventoryError("gh returned malformed JSON") from exc

    def issue(
        self, issue_number: int, *, current_agent: str
    ) -> tuple[IssueFacts, list[dict[str, Any]]]:
        data = self._json(
            [
                "gh",
                "issue",
                "view",
                str(issue_number),
                "--repo",
                self.repository,
                "--json",
                "number,title,body,labels,comments,state,url",
            ]
        )
        if not isinstance(data, dict) or data.get("state") != "OPEN":
            raise GitHubInventoryError(f"Issue #{issue_number} is not live and open")
        labels = frozenset(
            str(entry.get("name") or "").lower()
            for entry in data.get("labels") or []
            if isinstance(entry, dict) and entry.get("name")
        )
        body = str(data.get("body") or "")
        comments = list(data.get("comments") or [])
        comment_bodies = "\n".join(str(item.get("body") or "") for item in comments)
        paused = bool(
            labels.intersection({"paused", "blocked", "parked"})
            or PAUSED_STATE_RE.search(body)
            or PAUSED_STATE_RE.search(comment_bodies)
        )
        reservation = self._reservation_state(
            comments,
            issue_number=int(data["number"]),
            current_agent=current_agent,
        )
        objective_keys = sorted(
            label.removeprefix("objective:")
            for label in labels
            if label.startswith("objective:")
        )
        contract_keys = tuple(
            sorted(
                label.removeprefix("contract:")
                for label in labels
                if label.startswith("contract:")
            )
        )
        risk_flags = tuple(
            sorted(
                label.removeprefix("risk:")
                for label in labels
                if label.startswith("risk:")
            )
        )
        return (
            IssueFacts(
                number=int(data["number"]),
                title=str(data.get("title") or ""),
                labels=labels,
                base_branch="main",
                paused=paused,
                lock_state=reservation,
                objective_key=objective_keys[0] if len(objective_keys) == 1 else None,
                contract_keys=contract_keys,
                risk_flags=risk_flags,
            ),
            comments,
        )

    def open_pull_requests(self, policy: RoutingPolicy) -> list[dict[str, Any]]:
        data = self._json(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                self.repository,
                "--state",
                "open",
                "--limit",
                str(policy.candidate_limit),
                "--json",
                (
                    "number,title,isDraft,headRefName,baseRefName,body,labels,"
                    "updatedAt,mergeable,url"
                ),
            ]
        )
        if not isinstance(data, list):
            raise GitHubInventoryError("Open PR inventory is not a list")
        if len(data) >= policy.candidate_limit:
            raise GitHubInventoryError(
                "Open PR inventory reached candidate_limit; pagination is incomplete"
            )
        return [item for item in data if isinstance(item, dict)]

    def pull_request_details(self, pr_number: int) -> dict[str, Any]:
        data = self._json(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--repo",
                self.repository,
                "--json",
                (
                    "number,comments,createdAt,changedFiles,additions,deletions,"
                    "headRefOid"
                ),
            ]
        )
        if not isinstance(data, dict):
            raise GitHubInventoryError(f"PR #{pr_number} details are malformed")
        return data

    def pull_request_changed_paths(self, pr_number: int) -> list[str]:
        """Return the complete paginated list of changed file paths for a PR."""
        try:
            result = self._runner(
                [
                    "gh",
                    "api",
                    "--paginate",
                    f"repos/{self.repository}/pulls/{pr_number}/files",
                    "--jq",
                    ".[].filename",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitHubInventoryError(f"gh PR file inventory failed: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or "").strip()
            raise GitHubInventoryError(
                f"gh PR file inventory returned {result.returncode}: {detail}"
            )
        paths = [
            line.strip().replace("\\", "/")
            for line in (result.stdout or "").splitlines()
            if line.strip()
        ]
        return paths

    def pull_request_file_text(self, path: str, ref: str) -> str | None:
        """Fetch a single file body at ``ref``; return None on failure."""
        try:
            data = self._json(
                [
                    "gh",
                    "api",
                    (f"repos/{self.repository}/contents/" f"{path}?ref={ref}"),
                ]
            )
        except GitHubInventoryError:
            return None
        if not isinstance(data, dict):
            return None
        encoding = str(data.get("encoding") or "")
        content = data.get("content")
        if encoding != "base64" or not isinstance(content, str):
            return None
        try:
            return base64.b64decode(content).decode("utf-8")
        except (OSError, UnicodeDecodeError, ValueError):
            return None

    def _reviewability_inventory(
        self,
        *,
        pr_number: int,
        changed_files: int,
        head_ref_oid: str,
        path_threshold: int,
    ) -> tuple[tuple[str, ...] | None, dict[str, str] | None, bool]:
        """Load paths/contents once physical count reaches the reviewability gate."""
        if changed_files < path_threshold:
            return None, None, True
        try:
            paths = tuple(self.pull_request_changed_paths(pr_number))
        except GitHubInventoryError:
            return None, None, False
        if len(paths) != changed_files:
            return paths, None, False
        if not head_ref_oid:
            return paths, None, True
        contents: dict[str, str] = {}
        for path in paths:
            if classify_skill_path(path) is None:
                continue
            text = self.pull_request_file_text(path, head_ref_oid)
            if text is None:
                continue
            contents[path] = text
        return paths, contents or None, True

    @staticmethod
    def _reservation_state(
        comments: list[dict[str, Any]], *, issue_number: int, current_agent: str
    ) -> LockState:
        active_agent: str | None = None
        for comment in comments:
            body = str(comment.get("body") or "").strip().splitlines()[0]
            if body.startswith("LOCK_RESERVATION:"):
                match = RESERVATION_RE.fullmatch(body)
                if not match or int(match.group("issue")) != issue_number:
                    return LockState.INVALID
                if active_agent is not None:
                    return LockState.INVALID
                active_agent = match.group("agent")
            elif active_agent is not None and (
                LOCK_RE.fullmatch(body) or UNLOCK_RE.fullmatch(body)
            ):
                # A final lock consumes the pre-PR reservation. A later paired
                # UNLOCK is evaluated by the dual-lock parser.
                active_agent = None
        if active_agent is None:
            return LockState.UNLOCKED
        return (
            LockState.RESERVATION_HELD_BY_SELF
            if active_agent == current_agent
            else LockState.RESERVATION_HELD_BY_FOREIGN
        )

    @staticmethod
    def _lock_event(
        comments: list[dict[str, Any]], *, issue_number: int, pr_number: int
    ) -> tuple[str, ...] | None:
        active: tuple[str, ...] | None = None
        for comment in comments:
            body = str(comment.get("body") or "").strip()
            if body.startswith("LOCK:"):
                match = LOCK_RE.fullmatch(body.splitlines()[0])
                if not match:
                    return ("INVALID",)
                if (
                    int(match.group("issue")) != issue_number
                    or int(match.group("pr")) != pr_number
                ):
                    return ("INVALID",)
                new_lock = (
                    match.group("agent"),
                    match.group("issue"),
                    match.group("pr"),
                    match.group("ts"),
                )
                if active is not None and active != new_lock:
                    return ("INVALID",)
                active = new_lock
            elif body.startswith("UNLOCK:"):
                match = UNLOCK_RE.fullmatch(body.splitlines()[0])
                if (
                    not match
                    or int(match.group("issue")) != issue_number
                    or int(match.group("pr")) != pr_number
                    or active is None
                    or active[0] != match.group("agent")
                ):
                    return ("INVALID",)
                active = None
        return active

    def lock_state(
        self,
        *,
        issue_comments: list[dict[str, Any]],
        pr_comments: list[dict[str, Any]],
        current_agent: str,
        issue_number: int = 4202,
        pr_number: int = 4210,
    ) -> LockState:
        issue_lock = self._lock_event(
            issue_comments, issue_number=issue_number, pr_number=pr_number
        )
        pr_lock = self._lock_event(
            pr_comments, issue_number=issue_number, pr_number=pr_number
        )
        if issue_lock == ("INVALID",) or pr_lock == ("INVALID",):
            return LockState.INVALID
        if issue_lock is None and pr_lock is None:
            return LockState.UNLOCKED
        if issue_lock != pr_lock:
            return LockState.PARTIAL
        if issue_lock and issue_lock[0] == current_agent:
            return LockState.HELD_BY_SELF
        return LockState.HELD_BY_FOREIGN

    def candidates(
        self,
        *,
        policy: RoutingPolicy,
        issue_comments: list[dict[str, Any]],
        current_agent: str,
    ) -> list[CandidatePullRequest]:
        candidates: list[CandidatePullRequest] = []
        for raw in self.open_pull_requests(policy):
            number = int(raw["number"])
            details = self.pull_request_details(number)
            body = str(raw.get("body") or "")
            lock_state = self.lock_state(
                issue_comments=issue_comments,
                pr_comments=list(details.get("comments") or []),
                current_agent=current_agent,
                issue_number=int(
                    next(
                        (
                            match.group("issue")
                            for comment in issue_comments
                            if (
                                match := LOCK_RE.fullmatch(
                                    str(comment.get("body") or "")
                                    .strip()
                                    .splitlines()[0]
                                )
                            )
                        ),
                        0,
                    )
                )
                or 0,
                pr_number=number,
            )
            changed_files = int(details.get("changedFiles") or 0)
            head_ref_oid = str(details.get("headRefOid") or "") or None
            path_threshold = min(
                int(policy.reviewability["changed_files_limit"]),
                int(policy.merge_triggers["changed_files_limit"]),
            )
            paths, contents, inventory_complete = self._reviewability_inventory(
                pr_number=number,
                changed_files=changed_files,
                head_ref_oid=head_ref_oid or "",
                path_threshold=path_threshold,
            )
            merge_mode = "dedicated"
            if "cdb-batch-pr:v1" in body:
                # Prefer the marker's merge_mode so dedicated PRs that carry a
                # ledger/marker are not misclassified as batch-only.
                mode_match = re.search(
                    r"(?m)^merge_mode:\s*(batch|dedicated)\s*$", body
                )
                merge_mode = mode_match.group(1) if mode_match else "batch"
            candidates.append(
                CandidatePullRequest(
                    number=number,
                    title=str(raw.get("title") or ""),
                    head_branch=str(raw.get("headRefName") or ""),
                    base_branch=str(raw.get("baseRefName") or ""),
                    is_draft=bool(raw.get("isDraft")),
                    body=body,
                    lock_state=lock_state,
                    created_at=datetime.fromisoformat(
                        str(details["createdAt"]).replace("Z", "+00:00")
                    ),
                    changed_files=changed_files,
                    additions=int(details.get("additions") or 0),
                    deletions=int(details.get("deletions") or 0),
                    merge_mode=merge_mode,
                    changed_file_paths=paths,
                    file_contents=contents,
                    inventory_complete=inventory_complete,
                    head_ref_oid=head_ref_oid,
                )
            )
        return candidates
