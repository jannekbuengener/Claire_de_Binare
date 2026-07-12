"""Local D:\\Dev hygiene classification and redacted evidence (#3999).

Read-only: consumes workspace_inventory.json, emits local candidates/plan and
git-tracked redacted evidence summary. No deletion or mutation.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

Classification = Literal[
    "KEEP_ACTIVE",
    "KEEP_PROVENANCE",
    "REGENERABLE",
    "ARCHIVE_MOVE",
    "DEDUPLICATE",
    "QUARANTINE_REVIEW",
    "DELETE_CANDIDATE",
    "PROTECTED",
]

REQUIRED_CANDIDATE_FIELDS = (
    "path",
    "size",
    "last_relevant_change",
    "classification",
    "reason",
    "estimated_reclaim",
    "recovery_method",
    "risk",
    "confidence",
    "required_approval",
)

CONFIG_REL = Path("infrastructure/config/ops/local_dev_hygiene.json")
ISSUE_REF = "#3999"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(repo_root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if repo_root is None else repo_root
    path = root / CONFIG_REL
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("config must be a JSON object")
    return payload


def load_inventory(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("inventory must be a JSON object")
    return payload


def parse_scan_as_of(inventory: dict[str, Any]) -> datetime:
    raw = inventory.get("scan_as_of_utc")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("inventory missing scan_as_of_utc")
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def redact_path(path: str, secret_patterns: list[str]) -> str:
    lowered = path.lower().replace("/", "\\")
    for pattern in secret_patterns:
        if pattern.lower() in lowered:
            return "[REDACTED_SECRET_PATH]"
    return path


def redact_remote_url(url: str | None) -> str | None:
    if url is None:
        return None
    if "@" in url:
        return re.sub(r"//[^@]+@", "//[REDACTED]@", url)
    return url


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    size: int
    last_relevant_change: str | None
    classification: Classification
    reason: str
    estimated_reclaim: int
    recovery_method: str
    risk: str
    confidence: str
    required_approval: str
    pattern_id: str | None = None
    dedupe_evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "size": self.size,
            "last_relevant_change": self.last_relevant_change,
            "classification": self.classification,
            "reason": self.reason,
            "estimated_reclaim": self.estimated_reclaim,
            "recovery_method": self.recovery_method,
            "risk": self.risk,
            "confidence": self.confidence,
            "required_approval": self.required_approval,
        }
        if self.pattern_id:
            payload["pattern_id"] = self.pattern_id
        if self.dedupe_evidence:
            payload["dedupe_evidence"] = self.dedupe_evidence
        return payload


def _rule_matches_pattern(pattern_id: str, rule: dict[str, Any]) -> bool:
    return rule.get("match") == "pattern_id" and rule.get("pattern_id") == pattern_id


def classify_pattern_group(
    *,
    pattern_id: str,
    size_bytes: int,
    rules: list[dict[str, Any]],
) -> Candidate | None:
    rule = next((r for r in rules if _rule_matches_pattern(pattern_id, r)), None)
    if rule is None:
        return None
    return Candidate(
        path=f"pattern:{pattern_id}",
        size=size_bytes,
        last_relevant_change=None,
        classification=rule["classification"],
        reason=rule.get("reason", f"Matched pattern group {pattern_id}"),
        estimated_reclaim=size_bytes,
        recovery_method=rule.get("recovery_method", "review_required"),
        risk=rule.get("risk", "unknown"),
        confidence=rule["confidence"],
        required_approval=rule.get("required_approval", "human_go"),
        pattern_id=pattern_id,
    )


def build_worktree_candidates(worktrees: list[dict[str, Any]]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for entry in worktrees:
        path = str(entry.get("path", ""))
        if not path:
            continue
        candidates.append(
            Candidate(
                path=path,
                size=0,
                last_relevant_change=None,
                classification="PROTECTED",
                reason="Dynamically discovered git worktree.",
                estimated_reclaim=0,
                recovery_method="n/a",
                risk="high",
                confidence="high",
                required_approval="none",
            )
        )
    return candidates


def _repo_signature(repo: dict[str, Any]) -> tuple[str | None, str | None]:
    remote = repo.get("remote_url")
    head = repo.get("head_commit")
    remote_s = str(remote) if remote else None
    head_s = str(head) if head else None
    return remote_s, head_s


def classify_duplicate_repos(
    git_repositories: list[dict[str, Any]],
) -> list[Candidate]:
    """DEDUPLICATE only with identical remote+commit and clean tree evidence."""
    by_signature: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {}
    for repo in git_repositories:
        sig = _repo_signature(repo)
        by_signature.setdefault(sig, []).append(repo)

    candidates: list[Candidate] = []
    for sig, group in by_signature.items():
        if len(group) < 2:
            continue
        remote, commit = sig
        if not remote or not commit:
            for repo in group[1:]:
                candidates.append(
                    Candidate(
                        path=str(repo.get("path", "")),
                        size=0,
                        last_relevant_change=None,
                        classification="QUARANTINE_REVIEW",
                        reason="Potential duplicate repo without remote+commit evidence.",
                        estimated_reclaim=0,
                        recovery_method="manual_review",
                        risk="high",
                        confidence="low",
                        required_approval="human_go_quarantine",
                    )
                )
            continue

        canonical = sorted(group, key=lambda item: str(item.get("path", "")))[0]
        for repo in group[1:]:
            is_clean = repo.get("is_clean")
            if is_clean is True:
                candidates.append(
                    Candidate(
                        path=str(repo.get("path", "")),
                        size=0,
                        last_relevant_change=None,
                        classification="DEDUPLICATE",
                        reason=(
                            f"Same remote and commit as canonical repo "
                            f"{canonical.get('path')}; clean worktree."
                        ),
                        estimated_reclaim=0,
                        recovery_method="archive_or_remove_after_canonical_confirmed",
                        risk="medium",
                        confidence="medium",
                        required_approval="human_go_deduplicate",
                        dedupe_evidence="identical_git_remote_and_commit+clean_worktree",
                    )
                )
            else:
                candidates.append(
                    Candidate(
                        path=str(repo.get("path", "")),
                        size=0,
                        last_relevant_change=None,
                        classification="QUARANTINE_REVIEW",
                        reason=(
                            "Same remote/commit as another repo but worktree not clean; "
                            "cannot assign DEDUPLICATE."
                        ),
                        estimated_reclaim=0,
                        recovery_method="manual_review",
                        risk="high",
                        confidence="low",
                        required_approval="human_go_quarantine",
                    )
                )
    return candidates


def classify_top_directories(
    roots: list[dict[str, Any]],
    *,
    worktree_paths: set[str],
    rules: list[dict[str, Any]],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    normalized_worktrees = {p.lower().rstrip("\\/") for p in worktree_paths}
    for root in roots:
        for entry in root.get("top_directories") or []:
            path = str(entry.get("path", ""))
            size = int(entry.get("size_bytes", 0))
            norm = path.lower().rstrip("\\/")
            if any(norm == wt or norm.startswith(wt + "\\") for wt in normalized_worktrees):
                continue
            if "\\.git" in norm or norm.endswith(".git"):
                candidates.append(
                    Candidate(
                        path=path,
                        size=size,
                        last_relevant_change=None,
                        classification="PROTECTED",
                        reason="Git metadata path.",
                        estimated_reclaim=0,
                        recovery_method="n/a",
                        risk="high",
                        confidence="high",
                        required_approval="none",
                    )
                )
                continue
            matched_rule = next(
                (
                    r
                    for r in rules
                    if r.get("match") == "path_contains"
                    and isinstance(r.get("pattern"), str)
                    and r["pattern"].lower() in norm
                ),
                None,
            )
            if matched_rule:
                candidates.append(
                    Candidate(
                        path=path,
                        size=size,
                        last_relevant_change=None,
                        classification=matched_rule["classification"],
                        reason=matched_rule.get("reason", "Rule match"),
                        estimated_reclaim=size,
                        recovery_method=matched_rule.get("recovery_method", "review"),
                        risk=matched_rule.get("risk", "unknown"),
                        confidence=matched_rule["confidence"],
                        required_approval=matched_rule.get("required_approval", "human_go"),
                    )
                )
    return candidates


def build_candidates(
    inventory: dict[str, Any],
    config: dict[str, Any],
) -> list[Candidate]:
    rules = list(config.get("classification_rules") or [])
    candidates: list[Candidate] = []

    worktrees = list(inventory.get("worktrees") or [])
    worktree_paths = {str(w.get("path", "")) for w in worktrees if w.get("path")}
    candidates.extend(build_worktree_candidates(worktrees))

    for root in inventory.get("roots") or []:
        for group in root.get("pattern_groups") or []:
            pattern_id = str(group.get("pattern_id", ""))
            size_bytes = int(group.get("size_bytes", 0))
            item = classify_pattern_group(
                pattern_id=pattern_id,
                size_bytes=size_bytes,
                rules=rules,
            )
            if item is not None:
                candidates.append(item)

    candidates.extend(
        classify_top_directories(
            list(inventory.get("roots") or []),
            worktree_paths=worktree_paths,
            rules=rules,
        )
    )
    candidates.extend(classify_duplicate_repos(list(inventory.get("git_repositories") or [])))

    deduped: dict[str, Candidate] = {}
    for item in candidates:
        key = f"{item.classification}:{item.path}:{item.pattern_id or ''}"
        deduped[key] = item
    return list(deduped.values())


def validate_candidates(candidates: list[Candidate]) -> None:
    for item in candidates:
        payload = item.to_dict()
        missing = [field for field in REQUIRED_CANDIDATE_FIELDS if field not in payload]
        if missing:
            raise ValueError(f"candidate missing fields {missing}: {payload}")


def summarize_reclaim(candidates: list[Candidate]) -> dict[str, Any]:
    by_confidence: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    by_class: dict[str, int] = {}
    for item in candidates:
        by_class[item.classification] = by_class.get(item.classification, 0) + 1
        if item.classification in {
            "REGENERABLE",
            "DELETE_CANDIDATE",
            "ARCHIVE_MOVE",
            "DEDUPLICATE",
        }:
            by_confidence[item.confidence] = (
                by_confidence.get(item.confidence, 0) + item.estimated_reclaim
            )
    return {
        "candidate_count": len(candidates),
        "by_classification": by_class,
        "estimated_reclaim_bytes_by_confidence": by_confidence,
        "estimated_reclaim_gb_by_confidence": {
            key: round(value / (1024**3), 3) for key, value in by_confidence.items()
        },
    }


def render_cleanup_plan_md(
    *,
    inventory: dict[str, Any],
    candidates: list[Candidate],
    reclaim_summary: dict[str, Any],
) -> str:
    scan_as_of = inventory.get("scan_as_of_utc", "unknown")
    lines = [
        "# Local Dev Cleanup Plan (read-only manifest)",
        "",
        f"Issue: {ISSUE_REF}",
        f"Scan as of (UTC): `{scan_as_of}`",
        "",
        "This document is a reversible cleanup manifest. **No actions are executed.**",
        "",
        "## Human-GO thresholds",
        "",
        "| Action type | Approval gate |",
        "|-------------|---------------|",
        "| REGENERABLE caches/venvs | `human_go_regenerable` |",
        "| ARCHIVE_MOVE | `human_go_archive` |",
        "| DELETE_CANDIDATE | `human_go_delete` |",
        "| DEDUPLICATE | `human_go_deduplicate` + evidence |",
        "| QUARANTINE_REVIEW | `human_go_quarantine` |",
        "| PROTECTED / KEEP_* | no automated action |",
        "",
        "## Estimated reclaim (by confidence)",
        "",
        f"- high: {reclaim_summary['estimated_reclaim_gb_by_confidence'].get('high', 0)} GB",
        f"- medium: {reclaim_summary['estimated_reclaim_gb_by_confidence'].get('medium', 0)} GB",
        f"- low: {reclaim_summary['estimated_reclaim_gb_by_confidence'].get('low', 0)} GB",
        "",
        "## Candidates by confidence",
        "",
    ]
    for confidence in ("high", "medium", "low"):
        lines.append(f"### {confidence}")
        lines.append("")
        group = [c for c in candidates if c.confidence == confidence]
        if not group:
            lines.append("_none_")
            lines.append("")
            continue
        for item in sorted(group, key=lambda c: (-c.estimated_reclaim, c.path)):
            lines.append(
                f"- **{item.classification}** `{item.path}` "
                f"({item.estimated_reclaim} bytes) — {item.reason}"
            )
        lines.append("")
    protected = [c for c in candidates if c.classification == "PROTECTED"]
    lines.extend(
        [
            "## PROTECTED summary",
            "",
            f"Protected entries: {len(protected)} (includes all discovered worktrees).",
            "",
            "## Restore notes",
            "",
            "- REGENERABLE: rebuild from lockfiles/installers.",
            "- ARCHIVE_MOVE: move to archive volume before deleting active copy.",
            "- DEDUPLICATE: keep canonical repo; archive duplicate only after review.",
            "",
        ]
    )
    return "\n".join(lines)


def render_inventory_md(inventory: dict[str, Any]) -> str:
    agg = inventory.get("aggregate") or {}
    delta = agg.get("baseline_delta") or {}
    lines = [
        "# Local Dev Workspace Inventory (raw local summary)",
        "",
        f"Issue: {ISSUE_REF}",
        f"Scan as of (UTC): `{inventory.get('scan_as_of_utc')}`",
        "",
        "## Aggregate",
        "",
        f"- Total size: {agg.get('total_size_gb')} GB",
        f"- Files: {agg.get('total_files')}",
        f"- Directories: {agg.get('total_directories')}",
        f"- Completeness: {agg.get('scan_completeness')}",
        "",
        "## Baseline delta",
        "",
        f"- Screenshot total GB: {delta.get('screenshot_total_gb')}",
        f"- Measured total GB: {delta.get('measured_total_gb')}",
        f"- Delta GB: {delta.get('delta_gb')}",
        f"- Within size tolerance: {delta.get('within_size_tolerance')}",
        f"- Notes: {delta.get('tolerance_notes')}",
        "",
        "## Roots",
        "",
        "| Root | Status | GB | Files | Dirs | Duration s | Completeness |",
        "|------|--------|---:|------:|-----:|-----------:|--------------|",
    ]
    for root in inventory.get("roots") or []:
        lines.append(
            f"| `{root.get('path')}` | {root.get('scan_status')} | "
            f"{root.get('size_gb')} | {root.get('file_count')} | "
            f"{root.get('directory_count')} | {root.get('scan_duration_seconds')} | "
            f"{root.get('completeness')} |"
        )
    lines.extend(
        [
            "",
            f"Git repositories discovered: {len(inventory.get('git_repositories') or [])}",
            f"Worktrees discovered: {len(inventory.get('worktrees') or [])}",
            "",
        ]
    )
    return "\n".join(lines)


def build_redacted_evidence(
    *,
    inventory: dict[str, Any],
    candidates: list[Candidate],
    config: dict[str, Any],
) -> dict[str, Any]:
    secret_patterns = list(config.get("secret_path_patterns") or [])
    reclaim = summarize_reclaim(candidates)
    roots_summary = []
    for root in inventory.get("roots") or []:
        top_dirs = []
        for entry in (root.get("top_directories") or [])[:10]:
            top_dirs.append(
                {
                    "path": redact_path(str(entry.get("path", "")), secret_patterns),
                    "size_gb": round(int(entry.get("size_bytes", 0)) / (1024**3), 3),
                }
            )
        roots_summary.append(
            {
                "root": redact_path(str(root.get("path", "")), secret_patterns),
                "scan_status": root.get("scan_status"),
                "completeness": root.get("completeness"),
                "size_gb": root.get("size_gb"),
                "file_count": root.get("file_count"),
                "directory_count": root.get("directory_count"),
                "scan_duration_seconds": root.get("scan_duration_seconds"),
                "skipped_reparse_points_count": root.get(
                    "skipped_reparse_points_count", 0
                ),
                "access_error_count": len(root.get("access_errors") or []),
                "limitations": list(root.get("limitations") or []),
                "baseline_delta": root.get("baseline_delta") or {},
                "top_directories": top_dirs,
                "pattern_groups": [
                    {
                        "pattern_id": g.get("pattern_id"),
                        "size_gb": g.get("size_gb"),
                        "hit_count": g.get("hit_count"),
                    }
                    for g in (root.get("pattern_groups") or [])
                ],
            }
        )

    git_summary = []
    for repo in inventory.get("git_repositories") or []:
        git_summary.append(
            {
                "path": redact_path(str(repo.get("path", "")), secret_patterns),
                "head_commit": (
                    str(repo.get("head_commit", ""))[:12]
                    if repo.get("head_commit")
                    else None
                ),
                "remote_url": redact_remote_url(
                    str(repo.get("remote_url")) if repo.get("remote_url") else None
                ),
                "is_clean": repo.get("is_clean"),
            }
        )

    candidate_summary = []
    for item in candidates:
        if item.classification == "PROTECTED":
            candidate_summary.append(
                {
                    "classification": item.classification,
                    "path": "[PROTECTED_WORKTREE_OR_GIT_PATH]",
                    "confidence": item.confidence,
                    "estimated_reclaim_gb": 0,
                }
            )
            continue
        candidate_summary.append(
            {
                "classification": item.classification,
                "path": redact_path(item.path, secret_patterns),
                "pattern_id": item.pattern_id,
                "confidence": item.confidence,
                "estimated_reclaim_gb": round(item.estimated_reclaim / (1024**3), 3),
                "required_approval": item.required_approval,
                "dedupe_evidence": item.dedupe_evidence,
            }
        )

    agg = inventory.get("aggregate") or {}
    payload = {
        "schema_version": "local_dev_hygiene_evidence_redacted.v1",
        "issue": ISSUE_REF,
        "scan_as_of_utc": inventory.get("scan_as_of_utc"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "aggregate": {
            "total_size_gb": agg.get("total_size_gb"),
            "total_files": agg.get("total_files"),
            "total_directories": agg.get("total_directories"),
            "scan_completeness": agg.get("scan_completeness"),
            "baseline_delta": agg.get("baseline_delta"),
        },
        "roots": roots_summary,
        "git_repository_count": len(git_summary),
        "git_repositories": git_summary,
        "worktree_count": len(inventory.get("worktrees") or []),
        "reclaim_summary": reclaim,
        "candidates": candidate_summary,
        "redaction_note": (
            "Raw inventory under artifacts/local-dev-hygiene/ is gitignored. "
            "This file is aggregated and redacted; no secret paths or full file lists."
        ),
    }
    return payload


def render_redacted_evidence_md(evidence: dict[str, Any]) -> str:
    agg = evidence.get("aggregate") or {}
    delta = agg.get("baseline_delta") or {}
    reclaim = evidence.get("reclaim_summary") or {}
    lines = [
        "# Local Dev Hygiene Evidence (redacted)",
        "",
        f"Issue: {ISSUE_REF}",
        f"Scan as of (UTC): `{evidence.get('scan_as_of_utc')}`",
        "",
        "## Aggregate",
        "",
        f"- Total: {agg.get('total_size_gb')} GB / {agg.get('total_files')} files / "
        f"{agg.get('total_directories')} directories",
        f"- Completeness: {agg.get('scan_completeness')}",
        f"- Baseline delta GB: {delta.get('delta_gb')} "
        f"(within tolerance: {delta.get('within_size_tolerance')})",
        "",
        "## Reclaim estimate",
        "",
        f"- high confidence: "
        f"{reclaim.get('estimated_reclaim_gb_by_confidence', {}).get('high', 0)} GB",
        f"- medium confidence: "
        f"{reclaim.get('estimated_reclaim_gb_by_confidence', {}).get('medium', 0)} GB",
        f"- low confidence: "
        f"{reclaim.get('estimated_reclaim_gb_by_confidence', {}).get('low', 0)} GB",
        "",
        "## Discovery",
        "",
        f"- Git repositories: {evidence.get('git_repository_count')}",
        f"- Worktrees (all PROTECTED): {evidence.get('worktree_count')}",
        "",
        "## Root completeness",
        "",
        "| Root | Status | Completeness | GB | Reparse skipped | Access errors |",
        "|------|--------|--------------|---:|----------------:|--------------:|",
    ]
    for root in evidence.get("roots") or []:
        lines.append(
            f"| `{root.get('root')}` | {root.get('scan_status')} | "
            f"{root.get('completeness')} | {root.get('size_gb')} | "
            f"{root.get('skipped_reparse_points_count')} | "
            f"{root.get('access_error_count')} |"
        )
    lines.extend(["", evidence.get("redaction_note", ""), ""])
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_classification(
    *,
    inventory_path: Path,
    repo_root: Path | None = None,
    write_local_outputs: bool = True,
    write_published_evidence: bool = True,
) -> dict[str, Any]:
    root = _repo_root() if repo_root is None else repo_root
    config = load_config(root)
    inventory = load_inventory(inventory_path)
    _ = parse_scan_as_of(inventory)

    candidates = build_candidates(inventory, config)
    validate_candidates(candidates)
    reclaim = summarize_reclaim(candidates)

    raw_dir = root / str(config.get("raw_output_dir", "artifacts/local-dev-hygiene"))
    published_dir = root / str(
        config.get("published_evidence_dir", "docs/evidence/local_dev_hygiene")
    )

    if write_local_outputs:
        candidates_payload = {
            "schema_version": "local_dev_cleanup_candidates.v1",
            "issue": ISSUE_REF,
            "scan_as_of_utc": inventory.get("scan_as_of_utc"),
            "candidate_count": len(candidates),
            "candidates": [item.to_dict() for item in candidates],
            "reclaim_summary": reclaim,
        }
        write_json(raw_dir / "cleanup_candidates.json", candidates_payload)
        (raw_dir / "cleanup_plan.md").write_text(
            render_cleanup_plan_md(
                inventory=inventory,
                candidates=candidates,
                reclaim_summary=reclaim,
            ),
            encoding="utf-8",
        )
        (raw_dir / "workspace_inventory.md").write_text(
            render_inventory_md(inventory),
            encoding="utf-8",
        )

    evidence = build_redacted_evidence(
        inventory=inventory, candidates=candidates, config=config
    )
    if write_published_evidence:
        write_json(published_dir / "LOCAL_DEV_HYGIENE_EVIDENCE.json", evidence)
        (published_dir / "LOCAL_DEV_HYGIENE_EVIDENCE.md").write_text(
            render_redacted_evidence_md(evidence),
            encoding="utf-8",
        )

    return {
        "candidate_count": len(candidates),
        "reclaim_summary": reclaim,
        "published_evidence_dir": str(published_dir),
        "raw_output_dir": str(raw_dir),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local dev hygiene classifier (#3999)")
    parser.add_argument(
        "--inventory",
        default="artifacts/local-dev-hygiene/workspace_inventory.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--no-local-outputs", action="store_true")
    parser.add_argument("--no-published-evidence", action="store_true")
    args = parser.parse_args(argv)

    root = _repo_root()
    inventory_path = Path(args.inventory)
    if not inventory_path.is_absolute():
        inventory_path = root / inventory_path

    if args.validate_only:
        config = load_config(root)
        inventory = load_inventory(inventory_path)
        candidates = build_candidates(inventory, config)
        validate_candidates(candidates)
        print(json.dumps({"valid": True, "candidate_count": len(candidates)}, indent=2))
        return 0

    result = run_classification(
        inventory_path=inventory_path,
        repo_root=root,
        write_local_outputs=not args.no_local_outputs,
        write_published_evidence=not args.no_published_evidence,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
