#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "v2"
ANOMALY_SCHEMA_VERSION = "v1"

TASK_LABEL = "task"
TYPE_LABELS = {"type:bug", "type:feature", "type:refactor"}
SCOPE_LABELS = {"scope:core", "scope:infra", "scope:ci", "scope:data", "scope:monitoring"}
RELEVANT_EVENT_LABELS = {TASK_LABEL, *TYPE_LABELS, *SCOPE_LABELS}

HISTORICAL_PREFIXES = ("docs/archive/", "knowledge/logs/", "reports/")
SKIP_DIRS = {
    ".git",
    ".auto-claude",
    ".github/control-plane/generated",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "node_modules",
    "venv",
}
ALLOWED_SUFFIXES = {".md", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml", ".json"}

MUST_READ_MAX = 3
SUPPORTING_MAX = 4
BACKGROUND_MAX = 2
MAX_IMPLEMENTATION_TARGETS = 4
MAX_CONSTRAINTS = 4
MAX_WATCHOUTS = 4
STAGE_A_MAX = 18
SHORTLIST_MAX = 8
RECEIPT_MARKER_PREFIX = "cdb-backlog-curation-receipt"

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
    ".github/CONTROL_PLANE.md",
}
ARCHITECTURE_SURFACES = {
    "knowledge/ARCHITECTURE_MAP.md",
    "knowledge/governance/SERVICE_CATALOG.md",
}
GENERIC_FALLBACK_SURFACES = {
    ".github/CONTROL_PLANE.md",
    "CURRENT_STATUS.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
    "knowledge/ARCHITECTURE_MAP.md",
}
CONTRACT_PREFIXES = (
    "knowledge/contracts/",
    "core/contracts/",
    "docs/contracts/",
)

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")
GENERIC_PATH_PATTERN = re.compile(
    r"(?:^|[\s(])([.A-Za-z0-9_/\-]+\.[A-Za-z][A-Za-z0-9_./\-]*)(?=[\s),:;]|$)"
)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")

STOPWORDS = {
    "aber",
    "active",
    "aktuell",
    "als",
    "and",
    "any",
    "artefakt",
    "artifact",
    "auch",
    "auf",
    "aus",
    "back",
    "bei",
    "bleibt",
    "body",
    "bounded",
    "can",
    "comment",
    "comments",
    "dann",
    "das",
    "dem",
    "der",
    "die",
    "dieser",
    "direkt",
    "doch",
    "durch",
    "ein",
    "eine",
    "einen",
    "einer",
    "eines",
    "erwartet",
    "fuer",
    "for",
    "from",
    "gibt",
    "grosse",
    "grossen",
    "have",
    "handoff",
    "hier",
    "hint",
    "hints",
    "issue",
    "issues",
    "kein",
    "keine",
    "kleine",
    "label",
    "labels",
    "lane",
    "mit",
    "model",
    "modell",
    "nach",
    "nicht",
    "noch",
    "nur",
    "oder",
    "ohne",
    "path",
    "pfad",
    "quellen",
    "read",
    "repo",
    "run",
    "safe",
    "sein",
    "sind",
    "slice",
    "soll",
    "sollen",
    "stage",
    "status",
    "task",
    "text",
    "the",
    "then",
    "und",
    "unter",
    "use",
    "viele",
    "von",
    "vorarbeit",
    "workflow",
    "workflows",
    "wird",
    "with",
    "zuerst",
    "zum",
    "zur",
}


@dataclass(frozen=True)
class SurfaceSpec:
    path: str
    default_role: str
    reason: str
    section_hint: str
    keywords: tuple[str, ...]
    implementation_target: bool = False
    generic_fallback: bool = False
    change_hint: str = ""


SURFACE_SPECS = (
    SurfaceSpec(
        path=".github/scripts/backlog_curation.py",
        default_role="must_read",
        reason="Primary issue-scoped source selection, ranking, fingerprinting, and fail-closed curation logic.",
        section_hint="candidate ranking / handoff classes / receipt payload",
        keywords=(
            "backlog",
            "curation",
            "source",
            "issue",
            "scoped",
            "handoff",
            "ranking",
            "receipt",
            "fingerprint",
            "reuse",
            "dedupe",
            "budget",
        ),
        implementation_target=True,
        change_hint="Ranking, handoff schema, fingerprint/reuse, read budgets and fail-closed logic live here.",
    ),
    SurfaceSpec(
        path=".github/workflows/cdb-backlog-curation.yml",
        default_role="must_read",
        reason="Workflow trigger, permissions, artifact upload, and issue receipt publication for backlog curation.",
        section_hint="trigger filter / permissions / artifact upload / issue receipt",
        keywords=(
            "backlog",
            "curation",
            "workflow",
            "receipt",
            "comment",
            "issue",
            "labeled",
            "artifact",
            "permissions",
            "dedupe",
        ),
        implementation_target=True,
        change_hint="Trigger qualification, `issues: write`, artifact upload and dedupe-safe receipt commenting live here.",
    ),
    SurfaceSpec(
        path=".github/scripts/backlog_anomaly_escalation.py",
        default_role="supporting",
        reason="Downstream consumer for backlog-curation anomalies; this defines the compatibility window for the new handoff.",
        section_hint="artifact loading / anomaly classification / follow-up dedupe",
        keywords=(
            "anomaly",
            "escalation",
            "consumer",
            "follow",
            "up",
            "schema",
            "compatibility",
            "downstream",
        ),
        implementation_target=True,
        change_hint="Keep the `issue` + `anomalies` contract stable enough for the escalation lane.",
    ),
    SurfaceSpec(
        path=".github/workflows/cdb-backlog-anomaly-escalation.yml",
        default_role="supporting",
        reason="Shows how the downstream escalation lane downloads and consumes backlog-curation artifacts.",
        section_hint="workflow_run trigger / handoff artifact download / publish mode",
        keywords=(
            "anomaly",
            "escalation",
            "workflow",
            "consumer",
            "artifact",
            "downstream",
        ),
        implementation_target=True,
        change_hint="Use this to verify workflow-run wiring and artifact handoff compatibility.",
    ),
    SurfaceSpec(
        path=".github/CONTROL_PLANE.md",
        default_role="background",
        reason="Control-plane entrypoint documenting workflow inventory and where backlog curation fits in the GitHub layer.",
        section_hint="workflow inventory / reporting control signals",
        keywords=("github", "control", "plane", "workflow", "curation", "reporting"),
        generic_fallback=True,
        change_hint="Keep the control-plane entrypoint aligned with any workflow-side behavior changes.",
    ),
    SurfaceSpec(
        path="docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
        default_role="supporting",
        reason="Canonical workflow register for triggers, outputs, permissions, and human touchpoints.",
        section_hint="cdb-backlog-curation row / permission override table",
        keywords=(
            "workflow",
            "register",
            "trigger",
            "permission",
            "output",
            "receipt",
            "artifact",
            "curation",
        ),
        generic_fallback=True,
        change_hint="Document `issues: write`, artifact outputs and the receipt side effect consistently.",
    ),
    SurfaceSpec(
        path="docs/runbooks/CONTROL_REGISTER.md",
        default_role="background",
        reason="Active infra workflow list and operator-facing control-plane summary.",
        section_hint="active infra workflows",
        keywords=("control", "register", "active", "infra", "workflow", "receipt"),
        generic_fallback=True,
        change_hint="Keep the active infra workflow description aligned with the live automation behavior.",
    ),
    SurfaceSpec(
        path="CURRENT_STATUS.md",
        default_role="background",
        reason="Fallback repo-status context when broader working-repo state matters.",
        section_hint="repo / engineering status",
        keywords=("status", "current", "repo", "engineering"),
        generic_fallback=True,
    ),
    SurfaceSpec(
        path="knowledge/ARCHITECTURE_MAP.md",
        default_role="background",
        reason="Fallback architecture map when the issue touches service or control-plane boundaries.",
        section_hint="service map / repo boundaries",
        keywords=("architecture", "service", "boundary", "repo"),
        generic_fallback=True,
    ),
)

SURFACE_INDEX = {spec.path: spec for spec in SURFACE_SPECS}
NEIGHBOR_MAP = {
    ".github/scripts/backlog_curation.py": [
        ".github/workflows/cdb-backlog-curation.yml",
        ".github/scripts/backlog_anomaly_escalation.py",
        "docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
    ],
    ".github/workflows/cdb-backlog-curation.yml": [
        ".github/scripts/backlog_curation.py",
        ".github/workflows/cdb-backlog-anomaly-escalation.yml",
        ".github/CONTROL_PLANE.md",
    ],
    ".github/scripts/backlog_anomaly_escalation.py": [
        ".github/workflows/cdb-backlog-anomaly-escalation.yml",
        ".github/scripts/backlog_curation.py",
    ],
    ".github/workflows/cdb-backlog-anomaly-escalation.yml": [
        ".github/scripts/backlog_anomaly_escalation.py",
        ".github/workflows/cdb-backlog-curation.yml",
    ],
}


def is_historical_path(path: str) -> bool:
    return path.startswith(HISTORICAL_PREFIXES)


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_path(candidate: str) -> str | None:
    cleaned = candidate.strip().strip("\"'`<>[](){}:,;")
    if not cleaned:
        return None
    # Reject URLs and anchors early
    if "://" in cleaned or cleaned.startswith("#"):
        return None
    # Remove fragment identifiers and normalize path separators
    cleaned = cleaned.split("#", 1)[0].replace("\\", "/")
    # Normalize leading slashes and dots
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if cleaned.startswith("/"):
        cleaned = cleaned[1:]
    # Reject Windows drive paths (e.g., C:\path, D:/path), including prefixed forms
    # such as /C:\path or ./C:\path after normalization above
    if re.match(r"^[A-Za-z]:[/\\]", cleaned):
        return None
    # Reject path traversal attempts
    if cleaned.startswith("../") or "/../" in cleaned:
        return None
    # Validate character set: paths should contain only word chars, dots, slashes, and hyphens
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


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_PATTERN.findall(text.lower()):
        if token.isdigit():
            continue
        if len(token) < 3:
            continue
        if token in STOPWORDS:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens


def issue_keywords(title: str, body: str, labels: list[str]) -> list[str]:
    combined: list[str] = []
    for value in [title, *labels, body]:
        for token in tokenize(value):
            if token not in combined:
                combined.append(token)
    return combined


def title_keywords(title: str) -> set[str]:
    return set(tokenize(title))


def path_tokens(path: str) -> set[str]:
    tokens = set(tokenize(path.replace("/", " ")))
    stem = Path(path).stem.lower()
    tokens.update(tokenize(stem))
    return tokens


def should_skip_dir(rel_dir: str) -> bool:
    if not rel_dir:
        return False
    normalized = rel_dir.replace("\\", "/")
    if normalized.startswith(HISTORICAL_PREFIXES):
        return True
    parts = [part for part in normalized.split("/") if part]
    return any(part in SKIP_DIRS or part.startswith(".codex") for part in parts)


def iter_repo_files(repo_root: Path) -> list[str]:
    files: list[str] = []
    for root, dirs, filenames in os.walk(repo_root):
        rel_root = Path(root).relative_to(repo_root).as_posix()
        dirs[:] = [
            directory
            for directory in dirs
            if not should_skip_dir(f"{rel_root}/{directory}" if rel_root != "." else directory)
        ]
        for filename in filenames:
            rel_path = (
                f"{rel_root}/{filename}" if rel_root != "." else filename
            ).replace("\\", "/")
            if is_historical_path(rel_path):
                continue
            if Path(rel_path).suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            files.append(rel_path)
    return sorted(files)


def qualify_issue(labels: list[str]) -> tuple[bool, list[str]]:
    label_set = set(labels)
    matched_rules: list[str] = []
    if TASK_LABEL in label_set:
        matched_rules.append(TASK_LABEL)

    matched_types = sorted(TYPE_LABELS & label_set)
    matched_scopes = sorted(SCOPE_LABELS & label_set)
    if matched_types and matched_scopes:
        matched_rules.extend(matched_types)
        matched_rules.extend(matched_scopes)

    qualified = TASK_LABEL in label_set or (bool(matched_types) and bool(matched_scopes))
    return qualified, matched_rules


def build_candidate_entry(path: str) -> dict[str, Any]:
    spec = SURFACE_INDEX.get(path)
    return {
        "path": path,
        "spec": spec,
        "explicit": False,
        "neighbor": False,
        "path_score": 0.0,
        "content_score": 0.0,
        "catalog_score": 0.0,
        "matched_keywords": [],
    }


def add_candidate(
    candidates: dict[str, dict[str, Any]],
    *,
    path: str,
    path_score: float = 0.0,
    catalog_score: float = 0.0,
    explicit: bool = False,
    neighbor: bool = False,
    matched_keywords: set[str] | None = None,
) -> None:
    entry = candidates.setdefault(path, build_candidate_entry(path))
    entry["path_score"] = max(entry["path_score"], path_score)
    entry["catalog_score"] = max(entry["catalog_score"], catalog_score)
    entry["explicit"] = entry["explicit"] or explicit
    entry["neighbor"] = entry["neighbor"] or neighbor
    if matched_keywords:
        combined = set(entry["matched_keywords"])
        combined.update(matched_keywords)
        entry["matched_keywords"] = sorted(combined)


def score_path_match(path: str, keywords: list[str], title_terms: set[str]) -> tuple[float, set[str]]:
    lowered_path = path.lower()
    tokens = path_tokens(path)
    exact_matches = {keyword for keyword in keywords if keyword in tokens}
    substring_matches = {
        keyword
        for keyword in keywords
        if keyword not in exact_matches and len(keyword) >= 5 and keyword in lowered_path
    }
    matched = exact_matches | substring_matches
    if not matched:
        return 0.0, set()

    score = float(len(exact_matches) * 2 + len(substring_matches))
    score += float(len(matched & title_terms) * 1.5)
    if path.startswith(".github/scripts/"):
        score += 1.5
    if path.startswith(".github/workflows/"):
        score += 1.5
    if "backlog" in lowered_path:
        score += 1.0
    if "curation" in lowered_path:
        score += 1.0
    return score, matched


def find_line_hint(path: Path, keywords: list[str]) -> tuple[str, str]:
    if not path.is_file():
        return "", "file overview"

    heading = ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "", "file overview"

    lowered_keywords = [keyword.lower() for keyword in keywords]
    for line_number, raw_line in enumerate(lines[:240], start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
        lowered_line = stripped.lower()
        if any(keyword in lowered_line for keyword in lowered_keywords):
            snippet = normalize_text(stripped)[:180]
            if heading:
                return snippet, heading
            return snippet, f"line {line_number}"

    snippet = normalize_text(lines[0])[:180] if lines else ""
    return snippet, heading or "file overview"


def prefilter_candidates(
    *,
    repo_root: Path,
    title: str,
    body: str,
    labels: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    keywords = issue_keywords(title, body, labels)
    title_terms = title_keywords(title)
    explicit_candidates = extract_explicit_repo_paths(title, body)
    candidates: dict[str, dict[str, Any]] = {}
    ambiguities: list[str] = []
    valid_explicit: list[str] = []
    weak_explicit: list[str] = []
    missing_explicit: list[str] = []

    for candidate in explicit_candidates:
        if is_historical_path(candidate):
            weak_explicit.append(candidate)
            ambiguities.append(
                f"Excluded historical/archive reference `{candidate}`; active repo surfaces were prioritized."
            )
            continue
        full_path = repo_root / candidate
        if not full_path.is_file():
            missing_explicit.append(candidate)
            ambiguities.append(
                f"Explicit repo path `{candidate}` was referenced in the issue but does not exist in the checked-out repo."
            )
            continue
        valid_explicit.append(candidate)
        matched = path_tokens(candidate) & set(keywords)
        add_candidate(
            candidates,
            path=candidate,
            path_score=14.0 + float(len(matched & title_terms)),
            explicit=True,
            matched_keywords=matched,
        )
        for neighbor_path in NEIGHBOR_MAP.get(candidate, []):
            if (repo_root / neighbor_path).is_file():
                add_candidate(
                    candidates,
                    path=neighbor_path,
                    path_score=6.0,
                    neighbor=True,
                    matched_keywords=matched,
                )

    for spec in SURFACE_SPECS:
        if not (repo_root / spec.path).is_file():
            continue
        matched = {keyword for keyword in keywords if keyword in spec.keywords}
        if matched:
            add_candidate(
                candidates,
                path=spec.path,
                path_score=float(len(matched) * 2),
                catalog_score=4.0 + float(len(matched & title_terms)),
                matched_keywords=matched,
            )

    repo_files = iter_repo_files(repo_root)
    stage_a_rows: list[tuple[float, str, set[str]]] = []
    for rel_path in repo_files:
        score, matched = score_path_match(rel_path, keywords, title_terms)
        if score <= 0:
            continue
        stage_a_rows.append((score, rel_path, matched))

    stage_a_rows.sort(key=lambda item: (-item[0], item[1]))
    for score, rel_path, matched in stage_a_rows[:STAGE_A_MAX]:
        add_candidate(
            candidates,
            path=rel_path,
            path_score=score,
            matched_keywords=matched,
        )

    if not candidates:
        for fallback_path in sorted(GENERIC_FALLBACK_SURFACES):
            if (repo_root / fallback_path).is_file():
                add_candidate(candidates, path=fallback_path, catalog_score=1.0)

    ranked_stage_a = sorted(
        candidates.values(),
        key=lambda item: (-(item["path_score"] + item["catalog_score"]), item["path"]),
    )
    return ranked_stage_a[:STAGE_A_MAX], ambiguities, valid_explicit, weak_explicit, missing_explicit


def rank_candidates(
    *,
    repo_root: Path,
    candidates: list[dict[str, Any]],
    keywords: list[str],
    title_terms: set[str],
    matched_rules: list[str],
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        path = candidate["path"]
        full_path = repo_root / path
        snippet, section_hint = find_line_hint(full_path, keywords)
        content_score = 0.0
        matched_keywords = set(candidate["matched_keywords"])
        if snippet:
            lowered_snippet = snippet.lower()
            content_hits = {keyword for keyword in keywords if keyword in lowered_snippet}
            matched_keywords.update(content_hits)
            content_score = float(len(content_hits) * 1.5)

        spec = candidate["spec"]
        total_score = candidate["path_score"] + candidate["catalog_score"] + content_score
        if candidate["explicit"]:
            total_score += 8.0
        if candidate["neighbor"]:
            total_score += 1.0
        if spec is not None:
            total_score += 1.5
            if any(rule.startswith("scope:ci") for rule in matched_rules) and path.startswith(".github/"):
                total_score += 1.0
            total_score += float(len(set(spec.keywords) & title_terms) * 0.75)
        if path.startswith(".github/workflows/") and {"receipt", "comment", "dedupe"} & matched_keywords:
            total_score += 1.0
        if path.startswith(".github/scripts/") and {"ranking", "handoff", "schema", "fingerprint"} & matched_keywords:
            total_score += 1.0

        ranked.append(
            {
                **candidate,
                "content_score": content_score,
                "score": round(total_score, 2),
                "snippet": snippet,
                "section_hint": spec.section_hint if spec is not None else section_hint,
                "matched_keywords": sorted(matched_keywords),
                "issue_specific": candidate["explicit"]
                or (
                    path not in GENERIC_FALLBACK_SURFACES
                    and total_score >= 8.0
                    and (
                        len(matched_keywords) >= 2
                        or bool(matched_keywords & title_terms)
                    )
                ),
                "implementation_target": bool(
                    (spec and spec.implementation_target)
                    or (
                        path.startswith((".github/scripts/", ".github/workflows/"))
                        and total_score >= 7.0
                    )
                ),
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["score"],
            not item["explicit"],
            item["path"] in GENERIC_FALLBACK_SURFACES,
            item["path"],
        )
    )
    return ranked[:SHORTLIST_MAX]


def build_source_reason(candidate: dict[str, Any]) -> str:
    spec: SurfaceSpec | None = candidate["spec"]
    matched_keywords = candidate["matched_keywords"]
    if candidate["explicit"]:
        suffix = ""
        if matched_keywords:
            suffix = f" Matched issue signals: {', '.join(matched_keywords[:4])}."
        return f"Explicitly referenced in the issue and confirmed in the active repo scope.{suffix}"
    if spec is not None:
        if matched_keywords:
            return f"{spec.reason} Matched issue signals: {', '.join(matched_keywords[:4])}."
        return spec.reason
    if matched_keywords:
        return (
            "Issue keywords matched this active repo path; "
            f"strongest overlap: {', '.join(matched_keywords[:4])}."
        )
    return "Active repo path survived bounded prefilter and shortlist ranking."


def build_source_entry(candidate: dict[str, Any], *, role: str, priority: int) -> dict[str, Any]:
    spec: SurfaceSpec | None = candidate["spec"]
    entry = {
        "path": candidate["path"],
        "priority": priority,
        "role": role,
        "score": candidate["score"],
        "reason": build_source_reason(candidate),
        "section_hint": candidate["section_hint"],
        "snippet": candidate["snippet"],
        "matched_keywords": candidate["matched_keywords"],
    }
    if spec is not None and spec.change_hint:
        entry["change_hint"] = spec.change_hint
    return entry


def classify_handoff(
    *,
    ranked_candidates: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    handoff = {
        "must_read": [],
        "supporting": [],
        "background": [],
        "constraints": [],
        "watchouts": [],
        "implementation_targets": [],
    }
    flattened: list[dict[str, Any]] = []
    issue_specific_present = any(candidate["issue_specific"] for candidate in ranked_candidates)

    for candidate in ranked_candidates:
        spec: SurfaceSpec | None = candidate["spec"]
        role = "background"
        if candidate["explicit"] or (candidate["issue_specific"] and candidate["score"] >= 9.0):
            role = "must_read"
        elif candidate["issue_specific"] and candidate["implementation_target"]:
            role = "must_read"
        elif spec is not None and spec.default_role == "supporting":
            role = "supporting"
        elif spec is not None and spec.default_role == "must_read":
            role = "must_read"
        elif candidate["score"] >= 6.5:
            role = "supporting"

        if issue_specific_present and spec is not None and spec.generic_fallback and role == "must_read":
            role = "supporting"
        if issue_specific_present and spec is not None and spec.generic_fallback and role == "supporting":
            role = "background"

        target_list = handoff[role]
        limit = {
            "must_read": MUST_READ_MAX,
            "supporting": SUPPORTING_MAX,
            "background": BACKGROUND_MAX,
        }[role]
        if len(target_list) >= limit:
            continue
        entry = build_source_entry(candidate, role=role, priority=len(flattened) + 1)
        target_list.append(entry)
        flattened.append(entry)

    for candidate in ranked_candidates:
        if not candidate["implementation_target"]:
            continue
        if len(handoff["implementation_targets"]) >= MAX_IMPLEMENTATION_TARGETS:
            break
        spec: SurfaceSpec | None = candidate["spec"]
        handoff["implementation_targets"].append(
            {
                "path": candidate["path"],
                "reason": build_source_reason(candidate),
                "change_hint": spec.change_hint if spec is not None and spec.change_hint else "Likely edit surface based on the bounded issue-scoped ranking.",
            }
        )

    return handoff, flattened


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

    source_paths = {source["path"] for source in sources}
    text_has_workflow_signal = ".github/workflows/" in body or ".github/workflows/" in title or re.search(
        r"\bworkflow(s)?\b",
        f"{title}\n{body}",
        flags=re.IGNORECASE,
    )
    has_runbook_signal = bool(source_paths & WORKFLOW_DOC_SURFACES)
    if text_has_workflow_signal and not has_runbook_signal:
        findings.append(
            build_anomaly(
                issue_number=issue_number if isinstance(issue_number, int) else None,
                anomaly_type="missing_runbook",
                confidence=0.62,
                summary="Workflow/control context was referenced, but no concrete runbook/control source survived the bounded handoff shortlist.",
                evidence=["workflow_context_detected_without_runbook_reference"],
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
    handoff: dict[str, list[dict[str, Any]]],
    ambiguities: list[str],
    weak_explicit: list[str],
) -> tuple[str, float, str, bool]:
    strong_issue_targets = [
        item for item in handoff["must_read"] if item["path"] not in GENERIC_FALLBACK_SURFACES
    ]
    strong_supporting = [
        item for item in handoff["supporting"] if item["path"] not in GENERIC_FALLBACK_SURFACES
    ]

    if weak_explicit and not strong_issue_targets:
        return (
            "fail_closed",
            0.31,
            "Historical or missing issue references dominated the signal; the remaining shortlist is too weak for a safe implementation handoff.",
            True,
        )
    if len(strong_issue_targets) >= 2 and handoff["implementation_targets"]:
        return (
            "ready",
            0.91,
            "Issue-scoped implementation surfaces were prioritized ahead of generic fallback docs and the handoff is narrow enough to start from directly.",
            False,
        )
    if strong_issue_targets or len(strong_supporting) >= 2:
        review_needed = bool(ambiguities)
        return (
            "partial",
            0.66 if not review_needed else 0.58,
            "The shortlist is issue-scoped but still mixed with ambiguity or weaker supporting evidence; keep the implementation start narrow and operator-aware.",
            review_needed,
        )
    return (
        "fail_closed",
        0.27,
        "The shortlist remains too generic to justify a confident implementation handoff; do not substitute default/background sources for issue-specific evidence.",
        True,
    )


def build_constraints(
    *,
    title: str,
    body: str,
    handoff: dict[str, list[dict[str, Any]]],
    state: str,
) -> list[dict[str, str]]:
    text = f"{title}\n{body}".lower()
    constraints: list[dict[str, str]] = []

    if any(keyword in text for keyword in ("bounded", "cheap", "budget", "token", "small-model")):
        constraints.append(
            {
                "summary": "Keep the lane cheap and bounded; only shortlist-backed sources should drive the handoff.",
                "why": "The issue explicitly calls for bounded pre-curation instead of broad late search.",
            }
        )
    if any(keyword in text for keyword in ("fail-closed", "fail_closed", "ambigu")) or state == "fail_closed":
        constraints.append(
            {
                "summary": "Fail closed when the shortlist is ambiguous or too generic.",
                "why": "The issue requires honesty over synthetic certainty for unclear curation states.",
            }
        )
    if handoff["implementation_targets"]:
        constraints.append(
            {
                "summary": "Drive the next slice from `implementation_targets` before expanding into background docs.",
                "why": "The artifact is meant to narrow the later implementation model's read scope.",
            }
        )
    return constraints[:MAX_CONSTRAINTS]


def build_watchouts(
    *,
    ambiguities: list[str],
    missing_explicit: list[str],
    handoff: dict[str, list[dict[str, Any]]],
) -> list[dict[str, str]]:
    watchouts: list[dict[str, str]] = []
    if ambiguities:
        watchouts.append(
            {
                "summary": ambiguities[0],
                "why": "Historical or missing references should not silently inflate confidence.",
            }
        )
    if missing_explicit:
        watchouts.append(
            {
                "summary": f"Missing explicit repo reference(s): {', '.join(sorted(set(missing_explicit))[:3])}.",
                "why": "Broken references are emitted as anomalies and require deliberate follow-up.",
            }
        )
    if handoff["implementation_targets"]:
        watchouts.append(
            {
                "summary": "Do not rely on `context:curate`; the live qualification path is `task` or paired `type:*` + `scope:*` labels only.",
                "why": "The previously assumed manual-override label does not exist live and would keep the workflow/issue state inconsistent.",
            }
        )
    return watchouts[:MAX_WATCHOUTS]


def issue_fingerprint(title: str, body: str, labels: list[str], matched_rules: list[str]) -> str:
    fingerprint_seed = "|".join(
        [
            normalize_text(title).lower(),
            normalize_text(body).lower(),
            ",".join(sorted(label.lower() for label in labels)),
            ",".join(sorted(rule.lower() for rule in matched_rules)),
        ]
    )
    return short_hash(fingerprint_seed)


def estimate_tokens(handoff: dict[str, list[dict[str, Any]]]) -> int:
    return (
        len(handoff["must_read"]) * 650
        + len(handoff["supporting"]) * 360
        + len(handoff["background"]) * 200
        + len(handoff["constraints"]) * 60
        + len(handoff["watchouts"]) * 60
        + len(handoff["implementation_targets"]) * 90
    )


def build_execution_hint(sources: list[dict[str, Any]], state: str) -> dict[str, Any]:
    read_order = [source["path"] for source in sources]
    first_step = (
        f"Read `{read_order[0]}` first."
        if read_order
        else "No safe issue-scoped source pack is available yet; inspect the issue payload manually."
    )

    if state == "ready":
        next_action = "Consume `must_read`, then patch only the listed implementation targets before broadening the search."
    elif state == "partial":
        next_action = "Start with `must_read`, validate the ambiguous edge in `watchouts`, then decide whether supporting/background reads are necessary."
    else:
        next_action = "Do not start broad implementation; resolve the missing or historical references first."

    return {
        "recommended_first_step": first_step,
        "suggested_read_order": read_order,
        "suggested_next_action": next_action,
    }


def build_receipt(
    *,
    state: str,
    fingerprint: str,
    top_sources: list[str],
    next_step: str,
    artifact_ref: str,
    artifact_name: str,
) -> dict[str, Any]:
    status = {"ready": "curation ready", "partial": "partial", "fail_closed": "fail_closed"}[state]
    marker = f"<!-- {RECEIPT_MARKER_PREFIX}:{fingerprint} -->"
    body_lines = [
        marker,
        f"Backlog-Curation: `{status}`",
        f"- Fingerprint: `{fingerprint}`",
        f"- Top-Quellen: {', '.join(f'`{path}`' for path in top_sources) if top_sources else '`n/a`'}",
        f"- Naechster Schritt: {next_step}",
        f"- Handoff: `{artifact_ref}` (`{artifact_name}`)",
    ]
    return {
        "marker": marker,
        "status": status,
        "fingerprint": fingerprint,
        "top_sources": top_sources,
        "next_step": next_step,
        "artifact_name": artifact_name,
        "artifact_ref": artifact_ref,
        "body": "\n".join(body_lines) + "\n",
    }


def coerce_issue_number(raw_issue_number: Any) -> int | None:
    if isinstance(raw_issue_number, bool):
        return None
    if isinstance(raw_issue_number, int):
        return raw_issue_number
    if isinstance(raw_issue_number, str) and raw_issue_number.isdigit():
        return int(raw_issue_number)
    return None


def curate_issue_payload(payload: dict[str, Any], *, repo_root: Path) -> dict[str, Any] | None:
    labels = issue_labels(payload)
    qualified, matched_rules = qualify_issue(labels)
    if not qualified:
        return None

    issue = payload.get("issue", {})
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")
    issue_number = coerce_issue_number(issue.get("number"))

    stage_a, ambiguities, valid_explicit, weak_explicit, missing_explicit = prefilter_candidates(
        repo_root=repo_root,
        title=title,
        body=body,
        labels=labels,
    )
    keywords = issue_keywords(title, body, labels)
    title_terms = title_keywords(title)
    ranked = rank_candidates(
        repo_root=repo_root,
        candidates=stage_a,
        keywords=keywords,
        title_terms=title_terms,
        matched_rules=matched_rules,
    )
    handoff, sources = classify_handoff(ranked_candidates=ranked)
    state, confidence, summary, operator_review_needed = determine_curation_status(
        handoff=handoff,
        ambiguities=ambiguities,
        weak_explicit=weak_explicit,
    )
    handoff["constraints"] = build_constraints(
        title=title,
        body=body,
        handoff=handoff,
        state=state,
    )
    handoff["watchouts"] = build_watchouts(
        ambiguities=ambiguities,
        missing_explicit=missing_explicit,
        handoff=handoff,
    )
    safe_for_implementation_start = state == "ready" and not operator_review_needed
    fingerprint = issue_fingerprint(title, body, labels, matched_rules)
    artifact_ref = f"artifacts/backlog-curation/issue-{issue_number if issue_number is not None else 'unknown'}.json"
    artifact_name = f"backlog-curation-issue-{issue_number if issue_number is not None else 'unknown'}"
    receipt = build_receipt(
        state=state,
        fingerprint=fingerprint,
        top_sources=[source["path"] for source in sources[:3]],
        next_step=build_execution_hint(sources, state)["suggested_next_action"],
        artifact_ref=artifact_ref,
        artifact_name=artifact_name,
    )
    anomalies = detect_anomalies(
        payload=payload,
        labels=labels,
        sources=sources,
        valid_explicit=valid_explicit,
        missing_explicit=missing_explicit,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "issue": {
            "number": issue.get("number"),
            "title": title,
            "url": issue.get("html_url"),
            "labels": labels,
            "milestone": (issue.get("milestone") or {}).get("title"),
        },
        "trigger": {
            "event_name": f"issues.{payload.get('action', '')}".rstrip("."),
            "matched_rules": matched_rules,
        },
        "curation_status": {
            "state": state,
            "confidence": confidence,
            "summary": summary,
        },
        "operator_review_needed": operator_review_needed,
        "safe_for_implementation_start": safe_for_implementation_start,
        "fingerprint": fingerprint,
        "read_budget": {
            "must_read_max": MUST_READ_MAX,
            "supporting_max": SUPPORTING_MAX,
            "background_max": BACKGROUND_MAX,
            "estimated_tokens": estimate_tokens(handoff),
        },
        "sources": sources,
        "handoff": handoff,
        "execution_hint": build_execution_hint(sources, state),
        "ambiguities": ambiguities,
        "reuse": {
            "fingerprint": fingerprint,
            "receipt_marker": receipt["marker"],
            "unchanged_issue_can_reuse": True,
            "strategy": "If the issue title/body/labels fingerprint stays unchanged, reuse the existing receipt and prior handoff instead of treating the issue as newly curated.",
        },
        "receipt": receipt,
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

    issue_number = coerce_issue_number(artifact["issue"]["number"])
    if issue_number is None:
        print(
            f"Invalid issue number in curated artifact: expected int or digit string, got {artifact['issue']['number']!r}.",
            file=sys.stderr,
        )
        return None

    artifact["issue"]["number"] = issue_number
    artifact["receipt"]["artifact_name"] = f"backlog-curation-issue-{issue_number}"
    artifact["receipt"]["artifact_ref"] = f"artifacts/backlog-curation/issue-{issue_number}.json"
    artifact["receipt"]["body"] = artifact["receipt"]["body"].replace(
        "issue-unknown.json", f"issue-{issue_number}.json"
    ).replace(
        "backlog-curation-issue-unknown", f"backlog-curation-issue-{issue_number}"
    )

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
