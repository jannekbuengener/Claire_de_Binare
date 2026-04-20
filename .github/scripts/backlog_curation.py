#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "v1"

TASK_LABEL = "task"
MANUAL_OVERRIDE_LABEL = "context:curate"
TYPE_LABELS = {"type:bug", "type:feature", "type:refactor"}
SCOPE_LABELS = {
    "scope:core",
    "scope:infra",
    "scope:ci",
    "scope:data",
    "scope:monitoring",
}
RELEVANT_EVENT_LABELS = {TASK_LABEL, MANUAL_OVERRIDE_LABEL, *TYPE_LABELS, *SCOPE_LABELS}
HISTORICAL_PREFIXES = ("docs/archive/", "knowledge/logs/", "reports/")
CONTRACT_PREFIXES = (
    "knowledge/contracts/",
    "core/contracts/",
    "docs/contracts/",
    "contracts/",
)

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")
GENERIC_PATH_PATTERN = re.compile(
    r"(?<!://)(?<![A-Za-z]:[\\/])(?:^|[\s(])([.A-Za-z0-9_\-]+(?:/[.A-Za-z0-9_\-]+)+\.[A-Za-z0-9_.-]+)(?=$|[\s),:;])"
)

DEFAULT_SOURCES = [
    {
        "path": "docs/runbooks/CONTROL_REGISTER.md",
        "category": "runbook",
        "tier": 1,
        "reason": "Primary operational control surface for board stage, guardrails, and active control workflows.",
        "confidence": 0.99,
        "must_read": True,
    },
    {
        "path": "CURRENT_STATUS.md",
        "category": "status_surface",
        "tier": 1,
        "reason": "Primary working-repo status surface for current engineering and repo state.",
        "confidence": 0.95,
        "must_read": True,
    },
    {
        "path": "knowledge/ARCHITECTURE_MAP.md",
        "category": "architecture",
        "tier": 2,
        "reason": "Canonical architecture map for service boundaries, wiring, and repo structure.",
        "confidence": 0.92,
        "must_read": True,
    },
    {
        "path": "knowledge/governance/SERVICE_CATALOG.md",
        "category": "architecture",
        "tier": 2,
        "reason": "Canonical service catalog for ownership and service-level mapping.",
        "confidence": 0.91,
        "must_read": True,
    },
    {
        "path": ".github/README.md",
        "category": "control_plane",
        "tier": 3,
        "reason": "Control-plane entrypoint for workflow and automation discovery.",
        "confidence": 0.88,
        "must_read": False,
    },
    {
        "path": "docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
        "category": "control_plane",
        "tier": 3,
        "reason": "Canonical workflow register for triggers, outputs, and coupling surfaces.",
        "confidence": 0.9,
        "must_read": False,
    },
    {
        "path": "docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md",
        "category": "control_plane",
        "tier": 3,
        "reason": "Control-plane operating guide for reading and editing GitHub workflows safely.",
        "confidence": 0.86,
        "must_read": False,
    },
]


def is_historical_path(path: str) -> bool:
    return path.startswith(HISTORICAL_PREFIXES)


def normalize_path(candidate: str) -> str | None:
    cleaned = candidate.strip().strip("\"'`<>[](){}:,;")
    if not cleaned:
        return None
    if "://" in cleaned or cleaned.startswith("#"):
        return None
    cleaned = cleaned.split("#", 1)[0].replace("\\", "/")
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if cleaned.startswith("/"):
        cleaned = cleaned[1:]
    if cleaned.startswith("../") or "/../" in cleaned:
        return None
    if not re.fullmatch(r"[.A-Za-z0-9_/\-]+", cleaned):
        return None
    return cleaned


def extract_explicit_repo_paths(*texts: str) -> tuple[list[str], list[str]]:
    direct_paths: list[str] = []
    generic_paths: list[str] = []
    for text in texts:
        if not text:
            continue
        for raw_candidate in MARKDOWN_LINK_PATTERN.findall(text):
            normalized = normalize_path(raw_candidate)
            if normalized and normalized not in direct_paths:
                direct_paths.append(normalized)
        for raw_candidate in BACKTICK_PATTERN.findall(text):
            normalized = normalize_path(raw_candidate)
            if normalized and normalized not in direct_paths:
                direct_paths.append(normalized)
        for raw_candidate in GENERIC_PATH_PATTERN.findall(text):
            normalized = normalize_path(raw_candidate)
            if (
                normalized
                and normalized not in direct_paths
                and normalized not in generic_paths
            ):
                generic_paths.append(normalized)
    return direct_paths, generic_paths


def issue_labels(payload: dict[str, Any]) -> list[str]:
    labels = payload.get("issue", {}).get("labels", [])
    result: list[str] = []
    for label in labels:
        name = (label or {}).get("name")
        if isinstance(name, str) and name:
            result.append(name)
    return result


def is_contract_path(path: str) -> bool:
    return path.startswith(CONTRACT_PREFIXES)


def categorize_explicit_path(path: str) -> str:
    if path == "docs/runbooks/CONTROL_REGISTER.md":
        return "runbook"
    if path == "CURRENT_STATUS.md":
        return "status_surface"
    if path in {
        "knowledge/ARCHITECTURE_MAP.md",
        "knowledge/governance/SERVICE_CATALOG.md",
    }:
        return "architecture"
    if path.startswith(".github/") or path.startswith("docs/runbooks/GITHUB_"):
        return "control_plane"
    if is_contract_path(path):
        return "contract"
    if "validation" in path.lower():
        return "validation"
    if "strategy" in path.lower():
        return "strategy"
    return "repo_context"


def is_tier4_explicit_path(path: str) -> bool:
    lowered = path.lower()
    return is_contract_path(path) or "validation" in lowered or "strategy" in lowered


def build_explicit_source(path: str) -> dict[str, Any]:
    category = categorize_explicit_path(path)
    if is_tier4_explicit_path(path):
        reason = "Explicitly referenced in the issue and clearly relevant as contract/validation/strategy context."
        confidence = 0.95
    else:
        reason = (
            "Explicitly referenced in the issue and exists in the active repo scope."
        )
        confidence = 0.98
    return {
        "path": path,
        "category": category,
        "reason": reason,
        "confidence": confidence,
        "must_read": True,
    }


def qualify_issue(labels: list[str]) -> tuple[bool, list[str], bool]:
    label_set = set(labels)
    manual_override = MANUAL_OVERRIDE_LABEL in label_set
    matched_rules: list[str] = []

    if manual_override:
        matched_rules.append(MANUAL_OVERRIDE_LABEL)
    if TASK_LABEL in label_set:
        matched_rules.append(TASK_LABEL)

    matched_types = sorted(TYPE_LABELS & label_set)
    matched_scopes = sorted(SCOPE_LABELS & label_set)
    if matched_types and matched_scopes:
        matched_rules.extend(matched_types)
        matched_rules.extend(matched_scopes)

    qualified = (
        manual_override
        or TASK_LABEL in label_set
        or (bool(matched_types) and bool(matched_scopes))
    )
    return qualified, matched_rules, manual_override


def resolve_sources(
    payload: dict[str, Any],
    *,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    issue = payload.get("issue", {})
    title = issue.get("title") or ""
    body = issue.get("body") or ""

    direct_candidates, generic_candidates = extract_explicit_repo_paths(title, body)
    valid_explicit: list[str] = []
    excluded_explicit: list[str] = []
    missing_explicit: list[str] = []

    for candidate in direct_candidates:
        if is_historical_path(candidate):
            excluded_explicit.append(candidate)
            continue
        full_path = repo_root / candidate
        if not full_path.is_file():
            missing_explicit.append(candidate)
            continue
        if candidate not in valid_explicit:
            valid_explicit.append(candidate)

    for candidate in generic_candidates:
        if is_historical_path(candidate):
            excluded_explicit.append(candidate)
            continue
        full_path = repo_root / candidate
        if not full_path.is_file():
            continue
        if candidate not in valid_explicit:
            valid_explicit.append(candidate)

    sources: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for path in valid_explicit:
        source = build_explicit_source(path)
        sources.append(source)
        seen_paths.add(path)

    for default in DEFAULT_SOURCES:
        path = default["path"]
        if path in seen_paths:
            continue
        if not (repo_root / path).is_file():
            continue
        sources.append(
            {
                "path": path,
                "category": default["category"],
                "reason": default["reason"],
                "confidence": default["confidence"],
                "must_read": default["must_read"],
            }
        )
        seen_paths.add(path)

    for index, source in enumerate(sources, start=1):
        source["priority"] = index

    ambiguities: list[str] = []
    for path in excluded_explicit:
        ambiguities.append(
            f"Excluded historical/archive reference `{path}`; active repo surfaces were prioritized."
        )
    for path in missing_explicit:
        ambiguities.append(
            f"Explicit repo path `{path}` was referenced in the issue but does not exist in the checked-out repo."
        )

    return sources, ambiguities, valid_explicit, excluded_explicit + missing_explicit


def determine_curation_status(
    *,
    sources: list[dict[str, Any]],
    valid_explicit: list[str],
    weak_explicit: list[str],
    matched_rules: list[str],
) -> tuple[str, float, str]:
    if weak_explicit and not valid_explicit:
        return (
            "fail_closed",
            0.31,
            "Issue qualified via labels, but explicit context references were historical or missing and the remaining default surfaces are too generic for a confident handoff.",
        )
    if valid_explicit:
        return (
            "ready",
            0.9,
            "Explicit active repo references were resolved and prioritized ahead of the stable default control-plane and architecture surfaces.",
        )
    if len(sources) >= 4 and matched_rules:
        return (
            "partial",
            0.64,
            "Issue qualified from labels, but curation relies on stable default surfaces rather than explicit issue-scoped repo references.",
        )
    return (
        "fail_closed",
        0.27,
        "Issue qualified, but relevant active sources remain too weak to justify a confident agent-first curation package.",
    )


def build_execution_hint(sources: list[dict[str, Any]], state: str) -> dict[str, Any]:
    read_order = [source["path"] for source in sources]
    first_step = (
        f"Read `{read_order[0]}` first."
        if read_order
        else "Read the event payload first and resolve active repo context manually."
    )

    if state == "ready":
        next_action = "Read the curated sources in order, then scope the implementation slice against the referenced active surfaces."
    elif state == "partial":
        next_action = "Read the Tier-1 and Tier-2 surfaces first, then narrow the issue scope manually before editing."
    else:
        next_action = "Resolve the ambiguous or historical references first; do not assume the default surfaces alone are sufficient."

    return {
        "recommended_first_step": first_step,
        "suggested_read_order": read_order,
        "suggested_next_action": next_action,
    }


def curate_issue_payload(
    payload: dict[str, Any], *, repo_root: Path
) -> dict[str, Any] | None:
    labels = issue_labels(payload)
    qualified, matched_rules, manual_override = qualify_issue(labels)
    if not qualified:
        return None

    issue = payload.get("issue", {})
    sources, ambiguities, valid_explicit, weak_explicit = resolve_sources(
        payload, repo_root=repo_root
    )
    state, confidence, summary = determine_curation_status(
        sources=sources,
        valid_explicit=valid_explicit,
        weak_explicit=weak_explicit,
        matched_rules=matched_rules,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "issue": {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "url": issue.get("html_url"),
            "labels": labels,
            "milestone": (issue.get("milestone") or {}).get("title"),
        },
        "trigger": {
            "event_name": f"issues.{payload.get('action', '')}".rstrip("."),
            "matched_rules": matched_rules,
            "manual_override": manual_override,
        },
        "curation_status": {
            "state": state,
            "confidence": confidence,
            "summary": summary,
        },
        "sources": sources,
        "execution_hint": build_execution_hint(sources, state),
        "ambiguities": ambiguities,
    }


def write_artifact_for_event(
    *,
    event_path: Path,
    repo_root: Path,
    artifact_dir: Path,
) -> Path | None:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    artifact = curate_issue_payload(payload, repo_root=repo_root)
    if artifact is None:
        return None

    issue_number_raw = artifact["issue"]["number"]
    if isinstance(issue_number_raw, int):
        issue_number = issue_number_raw
    elif isinstance(issue_number_raw, str) and issue_number_raw.isdigit():
        issue_number = int(issue_number_raw)
    else:
        print(
            "No backlog-curation artifact produced: missing/invalid issue number in payload.",
            file=sys.stderr,
        )
        return None

    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"issue-{issue_number}.json"
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build backlog-curation artifact from an issues.labeled payload."
    )
    parser.add_argument("--event-path", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_path = write_artifact_for_event(
        event_path=args.event_path,
        repo_root=args.repo_root,
        artifact_dir=args.artifact_dir,
    )
    if artifact_path is None:
        print("No backlog-curation artifact produced for the current issue state.")
        return 0

    print(f"Backlog-curation artifact written to {artifact_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
