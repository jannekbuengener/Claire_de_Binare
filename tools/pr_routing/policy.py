"""Versioned machine-policy loader for CDB PR routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cdb-pr-routing-policy/v1"
POLICY_ID = "cdb-pr-routing-v1"
DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "governance"
    / "pr-routing-policy.v1.yaml"
)


@dataclass(frozen=True)
class RoutingPolicy:
    schema_version: str
    policy_id: str
    base_branch: str
    candidate_limit: int
    lanes: dict[str, dict[str, Any]]
    dedicated_rules: dict[str, list[str]]
    dedicated_branch_overrides: dict[str, str]
    validation_profile_matrix: dict[str, tuple[str, ...]]
    forbidden_risk_combinations: tuple[tuple[str, ...], ...]
    reviewability: dict[str, int]
    marker_version: str
    ledger_heading: str
    ledger_columns: tuple[str, ...]
    merge_triggers: dict[str, int]

    def classify_lane(self, title: str, labels: frozenset[str]) -> str:
        matches: list[str] = []
        normalized = {label.lower() for label in labels}
        upper_title = title.upper()
        for lane, definition in self.lanes.items():
            label_hit = normalized.intersection(
                str(label).lower() for label in definition.get("labels", [])
            )
            prefix_hit = any(
                upper_title.startswith(str(prefix).upper())
                for prefix in definition.get("title_prefixes", [])
            )
            if label_hit or prefix_hit:
                matches.append(lane)
        if len(matches) != 1:
            raise ValueError(
                "Issue lane must resolve to exactly one policy lane; "
                f"resolved={sorted(matches)}"
            )
        return matches[0]

    def requires_dedicated(self, title: str, labels: frozenset[str]) -> bool:
        normalized = {label.lower() for label in labels}
        if normalized.intersection(
            str(label).lower() for label in self.dedicated_rules["labels"]
        ):
            return True
        upper_title = title.upper()
        return any(
            upper_title.startswith(prefix.upper())
            for prefix in self.dedicated_rules["title_prefixes"]
        )

    def dedicated_branch(self, title: str, lane: str, issue_number: int) -> str:
        upper_title = title.upper()
        for prefix, branch in self.dedicated_branch_overrides.items():
            if upper_title.startswith(prefix.upper()):
                return branch
        return f"dedicated/{lane}-issue-{issue_number}"

    def validation_profile(self, lane: str) -> str:
        try:
            return str(self.lanes[lane]["validation_profile"])
        except KeyError as exc:
            raise ValueError(f"Unknown lane: {lane}") from exc


def _require_mapping(data: object, name: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{name} must be an object")
    return data


def load_policy(path: Path | str | None = None) -> RoutingPolicy:
    """Load strict JSON-compatible YAML without adding a YAML dependency."""
    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH
    try:
        data = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Routing policy is unreadable: {exc}") from exc
    root = _require_mapping(data, "routing policy")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported routing schema_version: {root.get('schema_version')!r}"
        )
    if root.get("policy_id") != POLICY_ID:
        raise ValueError(f"Unsupported policy_id: {root.get('policy_id')!r}")

    lanes = _require_mapping(root.get("lanes"), "lanes")
    if not lanes:
        raise ValueError("At least one lane is required")
    dedicated = _require_mapping(root.get("dedicated_rules"), "dedicated_rules")
    compatibility = _require_mapping(root.get("compatibility"), "compatibility")
    matrix_raw = _require_mapping(
        compatibility.get("validation_profile_matrix"),
        "validation_profile_matrix",
    )
    matrix = {
        str(key): tuple(str(item) for item in value)
        for key, value in matrix_raw.items()
        if isinstance(value, list)
    }
    for lane, definition in lanes.items():
        lane_mapping = _require_mapping(definition, f"lane {lane}")
        profile = str(lane_mapping.get("validation_profile") or "")
        if not profile or profile not in matrix:
            raise ValueError(f"Lane {lane} references unknown profile {profile!r}")
        if profile not in matrix[profile]:
            raise ValueError(f"Profile matrix is not reflexive for {profile}")

    metadata = _require_mapping(root.get("metadata"), "metadata")
    triggers = _require_mapping(root.get("merge_triggers"), "merge_triggers")
    reviewability_raw = _require_mapping(root.get("reviewability"), "reviewability")
    for section_name, section in (
        ("reviewability", reviewability_raw),
        ("merge_triggers", triggers),
    ):
        meaning = section.get("changed_files_limit_meaning")
        if meaning is not None and meaning != "logical_review_units":
            raise ValueError(
                f"{section_name}.changed_files_limit_meaning must be "
                f"'logical_review_units' when present; got {meaning!r}"
            )
    return RoutingPolicy(
        schema_version=SCHEMA_VERSION,
        policy_id=POLICY_ID,
        base_branch=str(root.get("base_branch") or ""),
        candidate_limit=int(root.get("candidate_limit") or 0),
        lanes={str(key): dict(value) for key, value in lanes.items()},
        dedicated_rules={
            "labels": [str(item) for item in dedicated.get("labels", [])],
            "title_prefixes": [
                str(item) for item in dedicated.get("title_prefixes", [])
            ],
        },
        dedicated_branch_overrides={
            str(prefix): str(branch)
            for prefix, branch in _require_mapping(
                dedicated.get("branch_overrides", {}),
                "dedicated branch_overrides",
            ).items()
        },
        validation_profile_matrix=matrix,
        forbidden_risk_combinations=tuple(
            tuple(str(item) for item in pair)
            for pair in compatibility.get("forbidden_risk_combinations", [])
            if isinstance(pair, list)
        ),
        reviewability={
            str(key): int(value)
            for key, value in reviewability_raw.items()
            if key != "changed_files_limit_meaning"
        },
        marker_version=str(metadata.get("marker_version") or ""),
        ledger_heading=str(metadata.get("ledger_heading") or ""),
        ledger_columns=tuple(str(item) for item in metadata.get("ledger_columns", [])),
        merge_triggers={
            str(key): int(value)
            for key, value in triggers.items()
            if key != "changed_files_limit_meaning"
        },
    )
