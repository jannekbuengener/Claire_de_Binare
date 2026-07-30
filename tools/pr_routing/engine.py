"""Pure, deterministic routing, metadata, lock, and trigger evaluation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from tools.pr_routing.policy import RoutingPolicy
from tools.pr_routing.reviewability import (
    ReviewabilityAssessment,
    assess_reviewability,
    mapping_content_reader,
)

MARKER_RE = re.compile(
    r"<!-- cdb-batch-pr:v1\r?\n(?P<body>.*?)\r?\n-->",
    flags=re.DOTALL,
)
ISSUE_RE = re.compile(r"#(?P<number>[1-9][0-9]*)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CLOSURE_RE = re.compile(
    r"(?im)^\s*(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(?P<number>[1-9][0-9]*)\s*$"
)

REQUIRED_MARKER_KEYS = frozenset(
    {
        "policy_id",
        "batch_key",
        "lane",
        "base_branch",
        "validation_profile",
        "merge_mode",
        "steward_state",
        "objective_key",
        "planned_issues",
        "contract_keys",
        "risk_flags",
    }
)
STEWARD_STATES = frozenset({"accepting_slices", "merge_candidate", "frozen"})
LEDGER_STATUSES = frozenset({"PLANNED", "LOCKED", "SLICE_DELIVERED", "MERGE_VERIFIED"})


class RoutingDecision(str, Enum):
    ROUTE_TO_EXISTING_BATCH_PR = "ROUTE_TO_EXISTING_BATCH_PR"
    ROUTE_TO_EXISTING_DEDICATED_PR = "ROUTE_TO_EXISTING_DEDICATED_PR"
    CREATE_NEW_BATCH_PR = "CREATE_NEW_BATCH_PR"
    CREATE_DEDICATED_PR = "CREATE_DEDICATED_PR"
    HOLD_PR_LOCK_CONFLICT = "HOLD_PR_LOCK_CONFLICT"
    HOLD_NO_SAFE_ROUTE = "HOLD_NO_SAFE_ROUTE"


class LockState(str, Enum):
    UNLOCKED = "UNLOCKED"
    RESERVATION_HELD_BY_SELF = "RESERVATION_HELD_BY_SELF"
    RESERVATION_HELD_BY_FOREIGN = "RESERVATION_HELD_BY_FOREIGN"
    HELD_BY_SELF = "HELD_BY_SELF"
    HELD_BY_FOREIGN = "HELD_BY_FOREIGN"
    PARTIAL = "PARTIAL_LOCK"
    INVALID = "LOCK_STATE_INVALID"


@dataclass(frozen=True)
class IssueFacts:
    number: int
    title: str
    labels: frozenset[str]
    base_branch: str
    paused: bool = False
    lock_state: LockState = LockState.UNLOCKED
    objective_key: str | None = None
    contract_keys: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class LedgerRow:
    issue_number: int
    status: str
    commit: str
    targeted_validation: str
    risk_class: str
    residual_uncertainty: str


@dataclass(frozen=True)
class BatchMetadata:
    policy_id: str
    batch_key: str
    lane: str
    base_branch: str
    validation_profile: str
    merge_mode: str
    steward_state: str
    objective_key: str
    planned_issues: tuple[int, ...]
    contract_keys: tuple[str, ...]
    risk_flags: tuple[str, ...]
    ledger: dict[int, LedgerRow]


@dataclass(frozen=True)
class CandidatePullRequest:
    number: int
    title: str
    head_branch: str
    base_branch: str
    is_draft: bool
    body: str
    lock_state: LockState
    created_at: datetime
    changed_files: int
    additions: int
    deletions: int
    merge_mode: str | None = None
    changed_file_paths: tuple[str, ...] | None = None
    file_contents: Mapping[str, str] | None = None
    inventory_complete: bool = True
    head_ref_oid: str | None = None


@dataclass(frozen=True)
class RoutingResult:
    issue_number: int
    routing_decision: RoutingDecision
    target_pr: int | None
    target_branch: str | None
    batch_key: str | None
    lane: str | None
    compatibility_reasons: tuple[str, ...]
    incompatibility_reasons: tuple[str, ...]
    lock_state: str
    validation_profile: str | None
    merge_mode: str
    merge_trigger_state: str
    policy_id: str
    reason_codes: tuple[str, ...]
    candidate_prs_considered: tuple[int, ...]
    reviewability_evidence: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class MergeTriggerResult:
    triggered: bool
    trigger_ids: tuple[str, ...]
    next_steward_state: str
    reviewability_evidence: dict[str, object] | None = None


def _split_sorted(value: str) -> tuple[str, ...]:
    items = tuple(sorted(item.strip() for item in value.split(",") if item.strip()))
    return items if items else ("none",)


def _parse_marker(body: str) -> dict[str, str]:
    if "cdb-batch-pr:" in body and "cdb-batch-pr:v1" not in body:
        raise ValueError("Unsupported batch marker version")
    matches = list(MARKER_RE.finditer(body))
    if len(matches) != 1:
        raise ValueError("PR body must contain exactly one cdb-batch-pr:v1 marker")
    values: dict[str, str] = {}
    for raw_line in matches[0].group("body").splitlines():
        if not raw_line.strip():
            continue
        if ":" not in raw_line:
            raise ValueError(f"Malformed marker line: {raw_line!r}")
        key, value = (part.strip() for part in raw_line.split(":", 1))
        if key in values:
            raise ValueError(f"Duplicate marker key: {key}")
        if key not in REQUIRED_MARKER_KEYS:
            raise ValueError(f"Unknown marker key: {key}")
        if not value:
            raise ValueError(f"Empty marker value: {key}")
        values[key] = value
    missing = REQUIRED_MARKER_KEYS.difference(values)
    if missing:
        raise ValueError(f"Missing marker keys: {sorted(missing)}")
    if values["steward_state"] not in STEWARD_STATES:
        raise ValueError(f"Unknown steward_state: {values['steward_state']}")
    if values["merge_mode"] not in {"batch", "dedicated"}:
        raise ValueError(f"Unknown merge_mode: {values['merge_mode']}")
    return values


def _parse_ledger(body: str) -> dict[int, LedgerRow]:
    heading = "## CDB Batch Ledger"
    if body.count(heading) != 1:
        raise ValueError("PR body must contain exactly one CDB Batch Ledger")
    section = body.split(heading, 1)[1]
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    expected_header = (
        "| Issue | Status | Commit | Targeted Validation | Risk Class | "
        "Restunsicherheit |"
    )
    try:
        start = lines.index(expected_header)
    except ValueError as exc:
        raise ValueError("Batch ledger header is invalid") from exc
    rows: dict[int, LedgerRow] = {}
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            raise ValueError("Batch ledger row must have exactly six columns")
        issue_match = ISSUE_RE.fullmatch(cells[0])
        if not issue_match:
            raise ValueError(f"Invalid ledger issue: {cells[0]!r}")
        issue_number = int(issue_match.group("number"))
        if issue_number in rows:
            raise ValueError(f"Duplicate ledger issue #{issue_number}")
        status, commit = cells[1], cells[2]
        if status not in LEDGER_STATUSES:
            raise ValueError(f"Unknown ledger status: {status}")
        if status in {"SLICE_DELIVERED", "MERGE_VERIFIED"} and not SHA_RE.fullmatch(
            commit
        ):
            raise ValueError(
                f"{status} for issue #{issue_number} requires a full commit SHA"
            )
        rows[issue_number] = LedgerRow(
            issue_number=issue_number,
            status=status,
            commit=commit,
            targeted_validation=cells[3],
            risk_class=cells[4],
            residual_uncertainty=cells[5],
        )
    if not rows:
        raise ValueError("Batch ledger has no issue rows")
    closures = [int(match.group("number")) for match in CLOSURE_RE.finditer(body)]
    if sorted(closures) != sorted(rows):
        raise ValueError("Closure entries must map one-to-one to ledger issues")
    return rows


def parse_batch_pr_body(body: str) -> BatchMetadata:
    values = _parse_marker(body)
    ledger = _parse_ledger(body)
    planned = tuple(
        sorted(
            int(match.group("number"))
            for match in ISSUE_RE.finditer(values["planned_issues"])
        )
    )
    if not planned or len(planned) != len(set(planned)):
        raise ValueError("planned_issues must be a unique non-empty issue list")
    if set(planned) != set(ledger):
        raise ValueError("planned_issues and ledger issues must match")
    return BatchMetadata(
        policy_id=values["policy_id"],
        batch_key=values["batch_key"],
        lane=values["lane"],
        base_branch=values["base_branch"],
        validation_profile=values["validation_profile"],
        merge_mode=values["merge_mode"],
        steward_state=values["steward_state"],
        objective_key=values["objective_key"],
        planned_issues=planned,
        contract_keys=_split_sorted(values["contract_keys"]),
        risk_flags=_split_sorted(values["risk_flags"]),
        ledger=ledger,
    )


def _references_issue(body: str, issue_number: int) -> bool:
    return issue_number in {
        int(match.group("number")) for match in ISSUE_RE.finditer(body)
    }


def assess_candidate_reviewability(
    policy: RoutingPolicy,
    candidate: CandidatePullRequest,
    *,
    limit_source: str = "reviewability",
) -> ReviewabilityAssessment:
    """Shared size assessment for router compatibility and merge triggers."""
    if limit_source == "merge_triggers":
        limits = policy.merge_triggers
    else:
        limits = policy.reviewability
    reader = None
    if candidate.file_contents is not None:
        reader = mapping_content_reader(candidate.file_contents)
    return assess_reviewability(
        physical_changed_files=candidate.changed_files,
        additions=candidate.additions,
        deletions=candidate.deletions,
        files_limit=int(limits["changed_files_limit"]),
        diff_lines_limit=int(limits["diff_lines_limit"]),
        changed_paths=candidate.changed_file_paths,
        inventory_complete=candidate.inventory_complete,
        content_reader=reader,
    )


def _result(
    *,
    policy: RoutingPolicy,
    issue: IssueFacts,
    decision: RoutingDecision,
    lane: str | None,
    profile: str | None,
    target_pr: int | None = None,
    target_branch: str | None = None,
    batch_key: str | None = None,
    compatible: tuple[str, ...] = (),
    incompatible: tuple[str, ...] = (),
    lock_state: str = LockState.UNLOCKED.value,
    merge_mode: str = "batch",
    reasons: tuple[str, ...] = (),
    considered: tuple[int, ...] = (),
    reviewability_evidence: tuple[dict[str, object], ...] = (),
) -> RoutingResult:
    return RoutingResult(
        issue_number=issue.number,
        routing_decision=decision,
        target_pr=target_pr,
        target_branch=target_branch,
        batch_key=batch_key,
        lane=lane,
        compatibility_reasons=compatible,
        incompatibility_reasons=incompatible,
        lock_state=lock_state,
        validation_profile=profile,
        merge_mode=merge_mode,
        merge_trigger_state="NOT_TRIGGERED",
        policy_id=policy.policy_id,
        reason_codes=reasons,
        candidate_prs_considered=considered,
        reviewability_evidence=reviewability_evidence,
    )


def route_issue(
    policy: RoutingPolicy,
    issue: IssueFacts,
    candidates: list[CandidatePullRequest],
) -> RoutingResult:
    considered = tuple(sorted(pr.number for pr in candidates))
    if issue.paused:
        return _result(
            policy=policy,
            issue=issue,
            decision=RoutingDecision.HOLD_NO_SAFE_ROUTE,
            lane=None,
            profile=None,
            reasons=("ISSUE_PAUSED_OR_BLOCKED",),
            considered=considered,
        )
    if issue.lock_state in {
        LockState.RESERVATION_HELD_BY_FOREIGN,
        LockState.PARTIAL,
        LockState.INVALID,
    }:
        return _result(
            policy=policy,
            issue=issue,
            decision=RoutingDecision.HOLD_PR_LOCK_CONFLICT,
            lane=None,
            profile=None,
            lock_state=issue.lock_state.value,
            reasons=("ISSUE_LOCK_CONFLICT",),
            considered=considered,
        )
    dedicated = policy.requires_dedicated(issue.title, issue.labels)
    try:
        lane = policy.classify_lane(issue.title, issue.labels)
        profile = policy.validation_profile(lane)
    except ValueError:
        if dedicated:
            lane = "dedicated"
            profile = "dedicated-v1"
        else:
            return _result(
                policy=policy,
                issue=issue,
                decision=RoutingDecision.HOLD_NO_SAFE_ROUTE,
                lane=None,
                profile=None,
                reasons=("LANE_AMBIGUOUS_OR_UNKNOWN",),
                considered=considered,
            )

    for pr in candidates:
        if (
            dedicated
            and pr.merge_mode == "dedicated"
            and pr.base_branch == issue.base_branch
            and _references_issue(pr.body, issue.number)
        ):
            if pr.lock_state in {
                LockState.HELD_BY_FOREIGN,
                LockState.PARTIAL,
                LockState.INVALID,
            }:
                return _result(
                    policy=policy,
                    issue=issue,
                    decision=RoutingDecision.HOLD_PR_LOCK_CONFLICT,
                    lane=lane,
                    profile=profile,
                    lock_state=pr.lock_state.value,
                    merge_mode="dedicated",
                    reasons=("LOCK_CONFLICT",),
                    considered=considered,
                )
            return _result(
                policy=policy,
                issue=issue,
                decision=RoutingDecision.ROUTE_TO_EXISTING_DEDICATED_PR,
                lane=lane,
                profile=profile,
                target_pr=pr.number,
                target_branch=pr.head_branch,
                lock_state=pr.lock_state.value,
                merge_mode="dedicated",
                compatible=("ISSUE_ALREADY_LINKED", "DEDICATED_MODE"),
                considered=considered,
            )
    if dedicated:
        return _result(
            policy=policy,
            issue=issue,
            decision=RoutingDecision.CREATE_DEDICATED_PR,
            lane=lane,
            profile=profile,
            target_branch=policy.dedicated_branch(issue.title, lane, issue.number),
            batch_key=f"{lane}-issue-{issue.number}",
            lock_state=issue.lock_state.value,
            merge_mode="dedicated",
            reasons=("DEDICATED_RULE_MATCH",),
            considered=considered,
        )

    if issue.objective_key is None or not issue.contract_keys or not issue.risk_flags:
        return _result(
            policy=policy,
            issue=issue,
            decision=RoutingDecision.HOLD_NO_SAFE_ROUTE,
            lane=lane,
            profile=profile,
            incompatible=("ISSUE_COMPATIBILITY_METADATA_INCOMPLETE",),
            reasons=("ISSUE_COMPATIBILITY_METADATA_INCOMPLETE",),
            considered=considered,
        )

    compatible: list[tuple[CandidatePullRequest, BatchMetadata]] = []
    incompatibilities: set[str] = set()
    reviewability_evidence: list[dict[str, object]] = []
    for pr in candidates:
        if "cdb-batch-pr:" not in pr.body:
            continue
        try:
            metadata = parse_batch_pr_body(pr.body)
        except ValueError:
            return _result(
                policy=policy,
                issue=issue,
                decision=RoutingDecision.HOLD_NO_SAFE_ROUTE,
                lane=lane,
                profile=profile,
                incompatible=("PR_METADATA_INVALID",),
                reasons=("PR_METADATA_INVALID",),
                considered=considered,
            )
        if (
            metadata.base_branch != issue.base_branch
            or pr.base_branch != issue.base_branch
        ):
            incompatibilities.add("BASE_BRANCH_MISMATCH")
            continue
        if metadata.policy_id != policy.policy_id:
            incompatibilities.add("POLICY_ID_MISMATCH")
            continue
        if metadata.merge_mode != "batch" or pr.merge_mode != "batch":
            incompatibilities.add("MERGE_MODE_INCOMPATIBLE")
            continue
        if metadata.lane != lane:
            incompatibilities.add("LANE_MISMATCH")
            continue
        if profile not in policy.validation_profile_matrix.get(
            metadata.validation_profile, ()
        ):
            incompatibilities.add("VALIDATION_PROFILE_INCOMPATIBLE")
            continue
        if issue.objective_key is None or metadata.objective_key != issue.objective_key:
            incompatibilities.add("OBJECTIVE_KEY_INCOMPATIBLE")
            continue
        if tuple(sorted(issue.contract_keys or ("none",))) != metadata.contract_keys:
            incompatibilities.add("CONTRACT_KEYS_INCOMPATIBLE")
            continue
        issue_risks = tuple(sorted(issue.risk_flags or ("none",)))
        if issue_risks != metadata.risk_flags:
            incompatibilities.add("RISK_FLAGS_INCOMPATIBLE")
            continue
        combined_risks = set(issue_risks).union(metadata.risk_flags)
        if any(
            set(pair).issubset(combined_risks)
            for pair in policy.forbidden_risk_combinations
        ):
            incompatibilities.add("FORBIDDEN_RISK_COMBINATION")
            continue
        assessment = assess_candidate_reviewability(policy, pr)
        reviewability_evidence.append(
            {"pr": pr.number, **assessment.to_evidence()}
        )
        if assessment.exceeds_reviewability:
            incompatibilities.add("REVIEWABILITY_LIMIT_REACHED")
            continue
        if metadata.steward_state != "accepting_slices":
            incompatibilities.add("PR_NOT_ACCEPTING_SLICES")
            continue
        if not pr.is_draft:
            incompatibilities.add("PR_NOT_OPEN_FOR_SLICES")
            continue
        if pr.lock_state in {
            LockState.HELD_BY_FOREIGN,
            LockState.PARTIAL,
            LockState.INVALID,
        }:
            return _result(
                policy=policy,
                issue=issue,
                decision=RoutingDecision.HOLD_PR_LOCK_CONFLICT,
                lane=lane,
                profile=profile,
                lock_state=pr.lock_state.value,
                incompatible=("LOCK_CONFLICT",),
                reasons=("LOCK_CONFLICT",),
                considered=considered,
                reviewability_evidence=tuple(reviewability_evidence),
            )
        compatible.append((pr, metadata))

    evidence = tuple(reviewability_evidence)
    if len(compatible) > 1:
        return _result(
            policy=policy,
            issue=issue,
            decision=RoutingDecision.HOLD_NO_SAFE_ROUTE,
            lane=lane,
            profile=profile,
            incompatible=tuple(sorted(incompatibilities)),
            reasons=("MULTIPLE_COMPATIBLE_PRS",),
            considered=considered,
            reviewability_evidence=evidence,
        )
    if compatible:
        pr, metadata = compatible[0]
        return _result(
            policy=policy,
            issue=issue,
            decision=RoutingDecision.ROUTE_TO_EXISTING_BATCH_PR,
            lane=lane,
            profile=profile,
            target_pr=pr.number,
            target_branch=pr.head_branch,
            batch_key=metadata.batch_key,
            compatible=(
                "BASE_BRANCH_MATCH",
                "LANE_MATCH",
                "VALIDATION_PROFILE_COMPATIBLE",
                "PR_ACCEPTING_SLICES",
            ),
            incompatible=tuple(sorted(incompatibilities)),
            lock_state=pr.lock_state.value,
            considered=considered,
            reviewability_evidence=evidence,
        )
    return _result(
        policy=policy,
        issue=issue,
        decision=RoutingDecision.CREATE_NEW_BATCH_PR,
        lane=lane,
        profile=profile,
        target_branch=f"batch/{lane}-issue-{issue.number}",
        batch_key=lane,
        lock_state=issue.lock_state.value,
        incompatible=tuple(sorted(incompatibilities)),
        reasons=("NO_COMPATIBLE_OPEN_PR",),
        considered=considered,
        reviewability_evidence=evidence,
    )


def evaluate_merge_triggers(
    policy: RoutingPolicy,
    candidate: CandidatePullRequest,
    *,
    observed_at: datetime,
    explicit_operator_go: bool,
    dependency_blocker: bool,
    security_or_safety: bool,
) -> MergeTriggerResult:
    metadata = parse_batch_pr_body(candidate.body)
    triggers: list[str] = []
    delivered = {
        issue
        for issue, row in metadata.ledger.items()
        if row.status == "SLICE_DELIVERED"
    }
    if set(metadata.planned_issues) == delivered:
        triggers.append("BATCH_COMPLETE")
    if len(delivered) >= policy.merge_triggers["issue_count_limit"]:
        triggers.append("ISSUE_COUNT_LIMIT")
    age_seconds = (observed_at - candidate.created_at).total_seconds()
    if age_seconds >= policy.merge_triggers["age_days"] * 86400:
        triggers.append("AGE_LIMIT")
    assessment = assess_candidate_reviewability(
        policy, candidate, limit_source="merge_triggers"
    )
    if assessment.exceeds_reviewability:
        triggers.append("SIZE_LIMIT")
    if dependency_blocker:
        triggers.append("DEPENDENCY_BLOCKER")
    if security_or_safety:
        triggers.append("SECURITY_OR_SAFETY")
    if explicit_operator_go:
        triggers.append("EXPLICIT_OPERATOR_GO")
    return MergeTriggerResult(
        triggered=bool(triggers),
        trigger_ids=tuple(triggers),
        next_steward_state="merge_candidate" if triggers else metadata.steward_state,
        reviewability_evidence=assessment.to_evidence(),
    )
