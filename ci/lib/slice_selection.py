"""Deterministic, fail-closed slice test-group selection for local Fast-CI.

Slice selection never produces merge evidence. Unknown paths, schema/parse
errors, and empty selections fall back to the full Fast-CI unit selector.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from ci.lib.config import load_yaml

SCHEMA_VERSION = "cdb-slice-validation-policy/v1"
SELECTION_REPORT_SCHEMA = "cdb-slice-selection-report/v1"
DEFAULT_POLICY_RELATIVE = Path("ci/config/slice_validation_policy.v1.yaml")
FULL_FAST_GROUP = "full_fast"
FULL_FAST_PYTEST_ARGS = ("-q", "-k", "not test_mcp_time_server_runtime")


class SlicePolicyError(ValueError):
    """Raised when the slice policy cannot be loaded or validated."""


@dataclass(frozen=True)
class SliceSelectionInput:
    changed_paths: tuple[str, ...]
    routing_lane: str
    validation_profile: str


@dataclass
class SliceSelectionResult:
    schema_version: str = SELECTION_REPORT_SCHEMA
    policy_id: str | None = None
    policy_schema_version: str | None = None
    selected_test_groups: list[str] = field(default_factory=list)
    selection_reasons: list[str] = field(default_factory=list)
    unclassified_paths: list[str] = field(default_factory=list)
    fallback_reason: str | None = None
    merge_evidence: bool = False
    pytest_paths: list[str] = field(default_factory=list)
    pytest_args: list[str] = field(default_factory=list)
    used_full_fast: bool = False
    inputs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        # Contract: slice selection is never merge evidence.
        payload["merge_evidence"] = False
        return payload


def normalize_changed_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """Deterministically normalize and sort changed paths (order-independent)."""
    cleaned: set[str] = set()
    for raw in paths:
        text = str(raw or "").strip().replace("\\", "/")
        if not text:
            continue
        while text.startswith("./"):
            text = text[2:]
        cleaned.add(text)
    return tuple(sorted(cleaned))


def default_policy_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_POLICY_RELATIVE


def load_slice_policy(path: Path) -> dict[str, Any]:
    """Load YAML policy; raise SlicePolicyError on empty/invalid structure."""
    if not path.is_file():
        raise SlicePolicyError(f"Missing slice policy file: {path}")
    try:
        data = load_yaml(path)
    except Exception as exc:  # noqa: BLE001 — fail-closed parse
        raise SlicePolicyError(f"Policy parse error: {exc}") from exc
    if not data:
        raise SlicePolicyError("Empty slice policy")
    if not isinstance(data, dict):
        raise SlicePolicyError("Slice policy root must be a mapping")
    return data


def validate_slice_policy(policy: Mapping[str, Any]) -> None:
    """Validate required schema fields; raise SlicePolicyError on violation."""
    schema = policy.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise SlicePolicyError(
            f"Unsupported schema_version {schema!r}; expected {SCHEMA_VERSION!r}"
        )
    if not policy.get("policy_id"):
        raise SlicePolicyError("Missing policy_id")
    groups = policy.get("test_groups")
    if not isinstance(groups, dict) or not groups:
        raise SlicePolicyError("test_groups must be a non-empty mapping")
    if FULL_FAST_GROUP not in groups and "full_fast_unit" not in policy:
        raise SlicePolicyError("full_fast group or full_fast_unit definition required")
    path_rules = policy.get("path_rules")
    if not isinstance(path_rules, list) or not path_rules:
        raise SlicePolicyError("path_rules must be a non-empty list")
    for rule in path_rules:
        if not isinstance(rule, dict):
            raise SlicePolicyError("path_rules entries must be mappings")
        if not rule.get("id"):
            raise SlicePolicyError("path rule missing id")
        prefixes = rule.get("match_prefixes")
        if not isinstance(prefixes, list) or not prefixes:
            raise SlicePolicyError(
                f"path rule {rule.get('id')!r} missing match_prefixes"
            )
        if rule.get("force_full_fallback"):
            continue
        groups_ref = rule.get("groups")
        if not isinstance(groups_ref, list) or not groups_ref:
            raise SlicePolicyError(
                f"path rule {rule.get('id')!r} missing groups (or force_full_fallback)"
            )


def _path_matches_prefix(path: str, prefix: str) -> bool:
    norm_prefix = prefix.replace("\\", "/").rstrip("/")
    if path == norm_prefix:
        return True
    if path.startswith(norm_prefix + "/"):
        return True
    # Allow exact file prefixes like README.md
    if not norm_prefix.endswith("/") and path == prefix.replace("\\", "/"):
        return True
    return False


def _full_fast_args(policy: Mapping[str, Any]) -> list[str]:
    unit = policy.get("full_fast_unit") or {}
    args = unit.get("pytest_args") if isinstance(unit, dict) else None
    if isinstance(args, list) and args:
        return [str(a) for a in args]
    return list(FULL_FAST_PYTEST_ARGS)


def _group_pytest_paths(policy: Mapping[str, Any], group_id: str) -> list[str]:
    groups = policy.get("test_groups") or {}
    meta = groups.get(group_id) or {}
    if not isinstance(meta, dict):
        return []
    if meta.get("inherits") == "full_fast_unit" or group_id == FULL_FAST_GROUP:
        return []
    paths = meta.get("pytest_paths") or []
    if not isinstance(paths, list):
        return []
    # Deterministic unique order
    return sorted({str(p).replace("\\", "/") for p in paths if str(p).strip()})


def _fallback_result(
    *,
    reason: str,
    inputs: SliceSelectionInput,
    policy: Mapping[str, Any] | None,
    unclassified: Iterable[str] = (),
    extra_reasons: Iterable[str] = (),
) -> SliceSelectionResult:
    policy_id = None
    schema = None
    args = list(FULL_FAST_PYTEST_ARGS)
    if policy is not None:
        policy_id = str(policy.get("policy_id") or "") or None
        schema = str(policy.get("schema_version") or "") or None
        args = _full_fast_args(policy)
    reasons = [f"fallback:{reason}", *list(extra_reasons)]
    return SliceSelectionResult(
        policy_id=policy_id,
        policy_schema_version=schema,
        selected_test_groups=[FULL_FAST_GROUP],
        selection_reasons=reasons,
        unclassified_paths=list(normalize_changed_paths(unclassified)),
        fallback_reason=reason,
        merge_evidence=False,
        pytest_paths=[],
        pytest_args=args,
        used_full_fast=True,
        inputs={
            "changed_paths": list(inputs.changed_paths),
            "routing_lane": inputs.routing_lane,
            "validation_profile": inputs.validation_profile,
        },
    )


def select_slice_test_groups(
    *,
    changed_paths: Iterable[str],
    routing_lane: str,
    validation_profile: str,
    policy: Mapping[str, Any] | None = None,
    policy_path: Path | None = None,
) -> SliceSelectionResult:
    """Select test groups deterministically; fail closed to full_fast.

    Always returns ``merge_evidence=False``.
    """
    paths = normalize_changed_paths(changed_paths)
    inputs = SliceSelectionInput(
        changed_paths=paths,
        routing_lane=str(routing_lane or "").strip(),
        validation_profile=str(validation_profile or "").strip(),
    )

    loaded: dict[str, Any] | None = None
    try:
        if policy is None:
            if policy_path is None:
                raise SlicePolicyError("policy or policy_path required")
            loaded = load_slice_policy(policy_path)
        else:
            loaded = dict(policy)
        validate_slice_policy(loaded)
    except SlicePolicyError as exc:
        reason = "policy_parse_error"
        msg = str(exc).lower()
        if "empty" in msg:
            reason = "empty_policy"
        elif "schema" in msg or "unsupported schema" in msg or "missing" in msg:
            reason = "schema_error"
        return _fallback_result(
            reason=reason,
            inputs=inputs,
            policy=loaded,
            unclassified=paths,
            extra_reasons=[f"error:{exc}"],
        )

    assert loaded is not None
    path_rules = list(loaded.get("path_rules") or [])
    selected: set[str] = set()
    reasons: list[str] = []
    unclassified: list[str] = []

    for path in paths:
        matched_any = False
        for rule in path_rules:
            prefixes = [str(p) for p in (rule.get("match_prefixes") or [])]
            if not any(_path_matches_prefix(path, p) for p in prefixes):
                continue
            matched_any = True
            rule_id = str(rule.get("id") or "unnamed")
            if rule.get("force_full_fallback"):
                fb = str(rule.get("fallback_reason") or "force_full_fallback")
                return _fallback_result(
                    reason=fb,
                    inputs=inputs,
                    policy=loaded,
                    unclassified=[],
                    extra_reasons=[f"path_rule:{rule_id}:{path}"],
                )
            for group in rule.get("groups") or []:
                selected.add(str(group))
                reasons.append(f"path:{path}->group:{group}(rule={rule_id})")
        if not matched_any:
            unclassified.append(path)

    if unclassified:
        return _fallback_result(
            reason="unclassified_paths",
            inputs=inputs,
            policy=loaded,
            unclassified=unclassified,
            extra_reasons=reasons,
        )

    # Lane / validation-profile contribution (union; never silent omit).
    for rule in loaded.get("lane_rules") or []:
        if not isinstance(rule, dict):
            continue
        lanes = {str(x) for x in (rule.get("lanes") or [])}
        profiles = {str(x) for x in (rule.get("validation_profiles") or [])}
        lane_hit = inputs.routing_lane in lanes if inputs.routing_lane else False
        profile_hit = (
            inputs.validation_profile in profiles
            if inputs.validation_profile
            else False
        )
        if not (lane_hit or profile_hit):
            continue
        rule_id = str(rule.get("id") or "lane")
        for group in rule.get("groups") or []:
            selected.add(str(group))
            if lane_hit:
                reasons.append(
                    f"lane:{inputs.routing_lane}->group:{group}(rule={rule_id})"
                )
            if profile_hit:
                reasons.append(
                    f"validation_profile:{inputs.validation_profile}"
                    f"->group:{group}(rule={rule_id})"
                )

    if not selected:
        return _fallback_result(
            reason="empty_selection",
            inputs=inputs,
            policy=loaded,
            unclassified=[],
            extra_reasons=reasons,
        )

    if FULL_FAST_GROUP in selected and len(selected) == 1:
        return _fallback_result(
            reason="selected_full_fast",
            inputs=inputs,
            policy=loaded,
            unclassified=[],
            extra_reasons=reasons,
        )

    # Narrow slice: never include full_fast alongside slice groups.
    selected.discard(FULL_FAST_GROUP)
    ordered_groups = sorted(selected)
    pytest_paths: list[str] = []
    for group_id in ordered_groups:
        pytest_paths.extend(_group_pytest_paths(loaded, group_id))
    # Deterministic unique path list
    pytest_paths = sorted(dict.fromkeys(pytest_paths))
    if not pytest_paths:
        return _fallback_result(
            reason="empty_pytest_paths",
            inputs=inputs,
            policy=loaded,
            unclassified=[],
            extra_reasons=reasons + [f"groups:{','.join(ordered_groups)}"],
        )

    reasons_sorted = sorted(set(reasons))
    return SliceSelectionResult(
        policy_id=str(loaded.get("policy_id")),
        policy_schema_version=str(loaded.get("schema_version")),
        selected_test_groups=ordered_groups,
        selection_reasons=reasons_sorted,
        unclassified_paths=[],
        fallback_reason=None,
        merge_evidence=False,
        pytest_paths=pytest_paths,
        pytest_args=["-q"],
        used_full_fast=False,
        inputs={
            "changed_paths": list(paths),
            "routing_lane": inputs.routing_lane,
            "validation_profile": inputs.validation_profile,
        },
    )


def build_unit_pytest_command(
    selection: SliceSelectionResult,
    *,
    python_executable: str,
    durations: int = 50,
) -> list[str]:
    """Build the unit-stage pytest argv from a selection result."""
    cmd = [python_executable, "-m", "pytest"]
    if selection.used_full_fast or not selection.pytest_paths:
        cmd.extend(selection.pytest_args or list(FULL_FAST_PYTEST_ARGS))
    else:
        cmd.extend(selection.pytest_paths)
        cmd.extend(selection.pytest_args or ["-q"])
    if durations > 0:
        cmd.append(f"--durations={int(durations)}")
    return cmd
