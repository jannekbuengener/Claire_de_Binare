"""Versioned machine-policy loader for CDB PR routing."""

from __future__ import annotations

import json
import re
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

# Leading bracket tokens in CDB issue titles, e.g. [OPS][CI] → OPS, CI.
_TITLE_TOKEN_RE = re.compile(r"^\[([^\]]+)\]")


def extract_title_tokens(title: str) -> tuple[str, ...]:
    """Return ordered leading ``[TOKEN]`` segments from an issue title."""
    remaining = title.lstrip()
    tokens: list[str] = []
    while remaining.startswith("["):
        match = _TITLE_TOKEN_RE.match(remaining)
        if match is None:
            break
        tokens.append(match.group(1).strip().upper())
        remaining = remaining[match.end() :].lstrip()
    return tuple(tokens)


def normalize_routing_token(value: str) -> str:
    """Normalize a title token or policy prefix for comparison."""
    token = value.strip().upper()
    if token.startswith("[") and token.endswith("]") and len(token) > 2:
        token = token[1:-1].strip()
    return token


def tokens_equivalent(left: str, right: str) -> bool:
    """Match singular/plural title families (``AGENT`` ↔ ``AGENTS``)."""
    a = normalize_routing_token(left)
    b = normalize_routing_token(right)
    if a == b:
        return True
    if a.endswith("S") and a[:-1] == b:
        return True
    if b.endswith("S") and b[:-1] == a:
        return True
    return False


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

    def _lane_label_set(self, definition: dict[str, Any]) -> set[str]:
        return {str(label).lower() for label in definition.get("labels", [])}

    def _lane_prefix_tokens(self, definition: dict[str, Any]) -> tuple[str, ...]:
        return tuple(
            normalize_routing_token(str(prefix))
            for prefix in definition.get("title_prefixes", [])
        )

    def _lanes_for_title_token(self, token: str) -> list[str]:
        matches: list[str] = []
        for lane, definition in self.lanes.items():
            if any(
                tokens_equivalent(token, prefix)
                for prefix in self._lane_prefix_tokens(definition)
            ):
                matches.append(lane)
        return matches

    def _lanes_for_labels(self, labels: frozenset[str]) -> set[str]:
        normalized = {label.lower() for label in labels}
        matches: set[str] = set()
        for lane, definition in self.lanes.items():
            if normalized.intersection(self._lane_label_set(definition)):
                matches.add(lane)
        return matches

    def classify_lane(self, title: str, labels: frozenset[str]) -> str:
        """Resolve exactly one lane from leftmost title token and repo labels.

        Title tokens are scanned left-to-right; the first token that maps to
        exactly one lane wins. Label hits must not contradict that lane.
        Label-only resolution requires exactly one matching lane.
        """
        title_lane: str | None = None
        for token in extract_title_tokens(title):
            matched = self._lanes_for_title_token(token)
            if len(matched) > 1:
                raise ValueError(
                    "Issue lane must resolve to exactly one policy lane; "
                    f"resolved={sorted(matched)}"
                )
            if len(matched) == 1:
                title_lane = matched[0]
                break

        label_lanes = self._lanes_for_labels(labels)
        if title_lane is not None:
            if label_lanes and title_lane not in label_lanes:
                raise ValueError(
                    "Issue lane must resolve to exactly one policy lane; "
                    f"resolved={sorted({title_lane, *label_lanes})}"
                )
            return title_lane
        if len(label_lanes) == 1:
            return next(iter(label_lanes))
        raise ValueError(
            "Issue lane must resolve to exactly one policy lane; "
            f"resolved={sorted(label_lanes)}"
        )

    def requires_dedicated(self, title: str, labels: frozenset[str]) -> bool:
        normalized = {label.lower() for label in labels}
        if normalized.intersection(
            str(label).lower() for label in self.dedicated_rules["labels"]
        ):
            return True
        upper_title = title.upper()
        title_tokens = extract_title_tokens(title)
        for prefix in self.dedicated_rules["title_prefixes"]:
            raw = str(prefix)
            # Compound prefixes (e.g. [GOVERNANCE][PR-FLOW]) stay startswith-only.
            if "][" in raw.upper():
                if upper_title.startswith(raw.upper()):
                    return True
                continue
            if upper_title.startswith(raw.upper()):
                return True
            prefix_token = normalize_routing_token(raw)
            if any(tokens_equivalent(token, prefix_token) for token in title_tokens):
                return True
        return False

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
