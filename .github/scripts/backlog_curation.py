#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "v1"
ANOMALY_SCHEMA_VERSION = "v1"

TASK_LABEL = "task"
MANUAL_OVERRIDE_LABEL = "context:curate"
TYPE_LABELS = {"type:bug", "type:feature", "type:refactor"}
SCOPE_LABELS = {"scope:core", "scope:infra", "scope:ci", "scope:data", "scope:monitoring"}
RELEVANT_EVENT_LABELS = {TASK_LABEL, MANUAL_OVERRIDE_LABEL, *TYPE_LABELS, *SCOPE_LABELS}
HISTORICAL_PREFIXES = ("docs/archive/", "knowledge/logs/", "reports/")
DRIFT_KEYWORDS = (
    "drift",
    "mismatch",
    "outdated",
    "stale",
    "misaligned",
    "diverg",
    "inconsistent",
)
SENSITIVE_LABEL_HINTS = ("security", "private", "secret", "vuln", "incident")
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE),
    re.compile(r"\b(secret|credential|token|password|private key)\b", re.IGNORECASE),
    re.compile(r"\bsecurity incident\b", re.IGNORECASE),
)
WORKFLOW_DOC_SURFACES = {
    "docs/runbooks/CONTROL_REGISTER.md",
    "docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
    "docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md",
    ".github/README.md",
}
ARCHITECTURE_SURFACES = {
    "knowledge/ARCHITECTURE_MAP.md",
    "knowledge/governance/SERVICE_CATALOG.md",
}
CONTRACT_PREFIXES = (
    "knowledge/contracts/",
    "core/contracts/",
    "docs/contracts/",
)

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")
GENERIC_PATH_PATTERN = re.compile(
    r"(?<!://)(?<![A-Za-z]:[\\/])(?:^|[\s(])([.A-Za-z0-9_\-]+(?:/[.A-Za-z0-9_/\-]+)+\.[A-Za-z][A-Za-z0-9_.-]*)(?=$|[\s),:;])"
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


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


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


def extract_explicit_repo_paths(*texts: str) -> list[str]:
    paths: list[str] = []
    for text in texts:
        if not text:
            continue
        for raw_candidate in MARKDOWN_LINK_PATTERN.findall(text):
            normalized = normalize_path(raw_candidate)
            if normalized and normalized not in paths:
                paths.append(normalized)
        for raw_candidate in BACKTICK_PATTERN.findall(text):
            normalized = normalize_path(raw_candidate)
            if normalized and normalized not in paths:
                paths.append(normalized)
        for raw_candidate in GENERIC_PATH_PATTERN.findall(text):
            normalized = normalize_path(raw_candidate)
            if normalized and normalized not in paths:
                paths.append(normalized)
    return paths


def issue_labels(payload: dict[str, Any]) -> list[str]:
    labels = payload.get("issue", {}).get("labels", [])
    result: list[str] = []
    for label in labels:
        name = (label or {}).get("name")
        if isinstance(name, str) and name:
            result.append(name)
    return result


def categorize_explicit_path(path: str) -> str:
    if path == "docs/runbooks/CONTROL_REGISTER.md":
        return "runbook"
    if path == "CURRENT_STATUS.md":
        return "status_surface"
    if path in {"knowledge/ARCHITECTURE_MAP.md", "knowledge/governance/SERVICE_CATALOG.md"}:
        return "architecture"
    if path.startswith(".github/") or path.startswith("docs/runbooks/GITHUB_"):
        return "control_plane"
    if path.startswith(CONTRACT_PREFIXES):
        return "contract"
    if "validation" in path.lower():
        return "validation"
    if "strategy" in path.lower():
        return "strategy"
    return "repo_context"


def is_tier4_explicit_path(path: str) -> bool:
    lowered = path.lower()
    return (
        path.startswith(CONTRACT_PREFIXES)
        or "validation" in lowered
        or "strategy" in lowered
    )


def build_explicit_source(path: str) -> dict[str, Any]:
    category = categorize_explicit_path(path)
    if is_tier4_explicit_path(path):
        reason = "Explicitly referenced in the issue and clearly relevant as contract/validation/strategy context."
        confidence = 0.95
    else:
        reason = "Explicitly referenced in the issue and exists in the active repo scope."
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

    qualified = manual_override or TASK_LABEL in label_set or (bool(matched_types) and bool(matched_scopes))
    return qualified, matched_rules, manual_override


def resolve_sources(
    payload: dict[str, Any],
    *,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    issue = payload.get("issue", {})
    title = issue.get("title") or ""
    body = issue.get("body") or ""

    explicit_candidates = extract_explicit_repo_paths(title, body)
    valid_explicit: list[str] = []
    excluded_explicit: list[str] = []
    missing_explicit: list[str] = []

    for candidate in explicit_candidates:
        if is_historical_path(candidate):
            excluded_explicit.append(candidate)
            continue
        full_path = repo_root / candidate
        if not full_path.is_file():
            missing_explicit.append(candidate)
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

    return (
        sources,
        ambiguities,
        valid_explicit,
        excluded_explicit + missing_explicit,
        missing_explicit,
    )


def detect_sensitive_context(labels: list[str], title: str, body: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    lowered_labels = [label.lower() for label in labels]
    for label in lowered_labels:
        if any(hint in label for hint in SENSITIVE_LABEL_HINTS):
            reasons.append(f"sensitive label `{label}` detected")
    joined = f"{title}\n{body}"
    for pattern in SENSITIVE_TEXT_PATTERNS:
        if pattern.search(joined):
            reasons.append(f"sensitive keyword pattern `{pattern.pattern}` detected")
    unique_reasons: list[str] = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)
    return bool(unique_reasons), unique_reasons


def confidence_strength(confidence: float) -> str:
    if confidence >= 0.86:
        return "strong"
    if confidence >= 0.7:
        return "medium"
    return "weak"


def has_drift_signal(*texts: str) -> bool:
    lowered = " ".join(texts).lower()
    return any(keyword in lowered for keyword in DRIFT_KEYWORDS)


def build_anomaly(
    *,
    issue_number: int | None,
    anomaly_type: str,
    confidence: float,
    summary: str,
    evidence: list[str],
    affected_artifacts: list[str],
    sensitive_context: bool,
    sensitive_reasons: list[str],
) -> dict[str, Any]:
    strength = confidence_strength(confidence)
    minimum_evidence_met = bool(evidence and affected_artifacts)
    if sensitive_context:
        escalation_hint = "report_only"
        policy_reason = "Sensitive/private context detected; public auto-issue emission is blocked."
    elif strength == "strong" and anomaly_type in {"broken_reference", "missing_expected_source"}:
        escalation_hint = "follow_up_candidate"
        policy_reason = "Strong typed anomaly with concrete, repo-backed evidence."
    elif strength == "weak":
        escalation_hint = "report_only"
        policy_reason = "Weak anomaly confidence; keep inside curation/report path."
    else:
        escalation_hint = "unclear"
        policy_reason = "Evidence is present but not strong enough for direct follow-up issue emission."

    fingerprint_seed = "|".join(
        [
            str(issue_number or "unknown"),
            anomaly_type,
            ",".join(sorted(affected_artifacts)),
            ",".join(sorted(evidence)),
        ]
    )
    return {
        "id": short_hash(fingerprint_seed),
        "type": anomaly_type,
        "confidence": round(confidence, 2),
        "strength": strength,
        "summary": summary,
        "evidence": evidence,
        "affected_artifacts": affected_artifacts,
        "minimum_evidence_met": minimum_evidence_met,
        "escalation_hint": escalation_hint,
        "public_issue_allowed": not sensitive_context,
        "policy_reason": policy_reason,
        "sensitivity_reasons": sensitive_reasons if sensitive_context else [],
    }


def detect_anomalies(
    *,
    payload: dict[str, Any],
    repo_root: Path,
    labels: list[str],
    sources: list[dict[str, Any]],
    valid_explicit: list[str],
    missing_explicit: list[str],
) -> dict[str, Any]:
    issue = payload.get("issue", {})
    issue_number = issue.get("number")
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    sensitive_context, sensitive_reasons = detect_sensitive_context(labels, title, body)

    findings: list[dict[str, Any]] = []
    for path in sorted(set(missing_explicit)):
        findings.append(
            build_anomaly(
                issue_number=issue_number if isinstance(issue_number, int) else None,
                anomaly_type="broken_reference",
                confidence=0.93,
                summary=f"Explicit repo path `{path}` was referenced but does not exist in the checked-out repo.",
                evidence=[f"path_missing:{path}"],
                affected_artifacts=[path],
                sensitive_context=sensitive_context,
                sensitive_reasons=sensitive_reasons,
            )
        )

    missing_expected_sources: list[str] = []
    for source in DEFAULT_SOURCES:
        path = source["path"]
        if source["must_read"] and not (repo_root / path).is_file():
            missing_expected_sources.append(path)
    if missing_expected_sources:
        findings.append(
            build_anomaly(
                issue_number=issue_number if isinstance(issue_number, int) else None,
                anomaly_type="missing_expected_source",
                confidence=0.96,
                summary="One or more canonical must-read curation sources are missing in the active repo scope.",
                evidence=[f"must_read_missing:{path}" for path in missing_expected_sources],
                affected_artifacts=sorted(missing_expected_sources),
                sensitive_context=sensitive_context,
                sensitive_reasons=sensitive_reasons,
            )
        )

    valid_set = set(valid_explicit)
    text_has_workflow_signal = ".github/workflows/" in body or ".github/workflows/" in title or re.search(
        r"\bworkflow(s)?\b",
        f"{title}\n{body}",
        flags=re.IGNORECASE,
    )
    has_runbook_signal = bool(
        valid_set
        & (WORKFLOW_DOC_SURFACES | {"docs/runbooks/CONTROL_REGISTER.md", "CURRENT_STATUS.md"})
    )
    if text_has_workflow_signal and not has_runbook_signal:
        findings.append(
            build_anomaly(
                issue_number=issue_number if isinstance(issue_number, int) else None,
                anomaly_type="missing_runbook",
                confidence=0.62,
                summary="Workflow/control context was referenced, but no concrete runbook/control source was resolved in curated paths.",
                evidence=[
                    "workflow_context_detected_without_runbook_reference",
                ],
                affected_artifacts=[
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
                ],
                sensitive_context=sensitive_context,
                sensitive_reasons=sensitive_reasons,
            )
        )

    explicit_workflows = [path for path in valid_explicit if path.startswith(".github/workflows/")]
    explicit_workflow_docs = [path for path in valid_explicit if path in WORKFLOW_DOC_SURFACES]
    if explicit_workflows and explicit_workflow_docs and has_drift_signal(title, body):
        findings.append(
            build_anomaly(
                issue_number=issue_number if isinstance(issue_number, int) else None,
                anomaly_type="workflow_doc_drift",
                confidence=0.8,
                summary="Issue references both workflow and workflow-doc surfaces with drift language; reconciliation may be required.",
                evidence=[
                    f"workflow_refs:{', '.join(sorted(explicit_workflows))}",
                    f"doc_refs:{', '.join(sorted(explicit_workflow_docs))}",
                ],
                affected_artifacts=sorted(set(explicit_workflows + explicit_workflow_docs)),
                sensitive_context=sensitive_context,
                sensitive_reasons=sensitive_reasons,
            )
        )

    explicit_arch_docs = [path for path in valid_explicit if path in ARCHITECTURE_SURFACES]
    if explicit_arch_docs and has_drift_signal(title, body):
        findings.append(
            build_anomaly(
                issue_number=issue_number if isinstance(issue_number, int) else None,
                anomaly_type="architecture_doc_drift",
                confidence=0.78,
                summary="Issue references architecture surfaces with drift language; architecture documentation alignment may be pending.",
                evidence=[f"architecture_refs:{', '.join(sorted(explicit_arch_docs))}"],
                affected_artifacts=sorted(set(explicit_arch_docs)),
                sensitive_context=sensitive_context,
                sensitive_reasons=sensitive_reasons,
            )
        )

    findings.sort(key=lambda item: (item["type"], item["id"]))
    counts = {"strong": 0, "medium": 0, "weak": 0}
    for finding in findings:
        strength = finding["strength"]
        if strength in counts:
            counts[strength] += 1

    return {
        "schema_version": ANOMALY_SCHEMA_VERSION,
        "contains_sensitive_signals": sensitive_context,
        "sensitivity_reasons": sensitive_reasons,
        "counts_by_strength": counts,
        "findings": findings,
    }


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


def curate_issue_payload(payload: dict[str, Any], *, repo_root: Path) -> dict[str, Any] | None:
    labels = issue_labels(payload)
    qualified, matched_rules, manual_override = qualify_issue(labels)
    if not qualified:
        return None

    issue = payload.get("issue", {})
    sources, ambiguities, valid_explicit, weak_explicit, missing_explicit = resolve_sources(
        payload,
        repo_root=repo_root,
    )
    state, confidence, summary = determine_curation_status(
        sources=sources,
        valid_explicit=valid_explicit,
        weak_explicit=weak_explicit,
        matched_rules=matched_rules,
    )
    anomalies = detect_anomalies(
        payload=payload,
        repo_root=repo_root,
        labels=labels,
        sources=sources,
        valid_explicit=valid_explicit,
        missing_explicit=missing_explicit,
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
        "anomalies": anomalies,
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

    raw_issue_number = artifact["issue"]["number"]
    if isinstance(raw_issue_number, bool):
        print(
            f"Invalid issue number in curated artifact: expected int or digit string, got {raw_issue_number!r}.",
            file=sys.stderr,
        )
        return None
    if isinstance(raw_issue_number, int):
        issue_number = raw_issue_number
    elif isinstance(raw_issue_number, str) and raw_issue_number.isdigit():
        issue_number = int(raw_issue_number)
    else:
        print(
            f"Invalid issue number in curated artifact: expected int or digit string, got {raw_issue_number!r}.",
            file=sys.stderr,
        )
        return None

    artifact["issue"]["number"] = issue_number
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"issue-{issue_number}.json"
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build backlog-curation artifact from an issues.labeled payload.")
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
