#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CONTROL_ISSUE_NUMBER = 1445
ARCHITECTURE_DOCS = [
    "knowledge/ARCHITECTURE_MAP.md",
    "knowledge/governance/SERVICE_CATALOG.md",
]
DISCOVERY_SURFACES = [
    "mcp_navpack_working_repo/ENTRYPOINTS.yaml",
    "mcp_navpack_working_repo/CHEATSHEET.md",
]
RUNBOOK_SURFACES = [
    "docs/runbooks/CONTROL_REGISTER.md",
]
EVIDENCE_SURFACES = [
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
]
ISSUE_MARKER_TEMPLATE = "<!-- cdb-post-merge-followup-issue:{fingerprint} -->"
COMMENT_MARKER_TEMPLATE = "<!-- cdb-post-merge-followup-comment:pr-{pr_number} -->"
COMMENT_HEADER = "## Post-Merge Follow-up Scan"
CANON_PATTERNS = [
    ("BLACK terminology", re.compile(r"\bBLACK\b")),
    (
        "legacy base/dev runtime start",
        re.compile(r"docker compose .*base\.yml.*dev\.yml.* up -d", re.IGNORECASE),
    ),
    (
        "unqualified docker compose up",
        re.compile(r"docker compose up -d", re.IGNORECASE),
    ),
    (
        "legacy secrets path",
        re.compile(r"(~[/\\]Documents[/\\]\.secrets[/\\]cdb|SECRETS_PATH=.*\.secrets[/\\]cdb)"),
    ),
]


@dataclass
class Finding:
    fingerprint: str
    rule_id: str
    title: str
    classification_input: str
    trigger_files: list[str]
    affected_candidates: list[str]
    evidence_lines: list[str]
    issue_title: str
    labels: list[str]


def run_command(args: list[str], *, input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr.strip()}"
        )
    return result.stdout


def run_gh_repo(repo: str, args: list[str], *, input_text: str | None = None) -> str:
    full_args = ["gh"] + args + ["--repo", repo]
    return run_command(full_args, input_text=input_text)


def run_gh_api(args: list[str], *, input_text: str | None = None) -> str:
    return run_command(["gh", "api"] + args, input_text=input_text)


def sha16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def is_archived_or_historical(path: str) -> bool:
    prefixes = (
        "docs/archive/",
        "knowledge/logs/",
        "reports/",
    )
    return path.startswith(prefixes)


def is_active_surface(path: str) -> bool:
    return not is_archived_or_historical(path)


def parse_added_lines(diff_text: str) -> dict[str, list[str]]:
    added: dict[str, list[str]] = {}
    current_file: str | None = None
    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            added.setdefault(current_file, [])
            continue
        if raw_line.startswith("diff --git "):
            current_file = None
            continue
        if current_file is None:
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added[current_file].append(raw_line[1:])
    return added


def relative_paths(files: list[dict[str, Any]]) -> list[str]:
    return [entry["path"] for entry in files]


def touched(files: list[str], paths: list[str]) -> bool:
    wanted = set(paths)
    return any(path in wanted for path in files)


def touched_prefix(files: list[str], prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefixes) for path in files)


def shortlist(paths: list[str], *, limit: int = 4) -> list[str]:
    if len(paths) <= limit:
        return paths
    return paths[:limit]


def build_finding(
    *,
    pr_number: int,
    rule_id: str,
    title: str,
    classification_input: str,
    trigger_files: list[str],
    affected_candidates: list[str],
    evidence_lines: list[str],
    issue_title: str,
    labels: list[str],
) -> Finding:
    key = "|".join([str(pr_number), rule_id] + sorted(trigger_files))
    return Finding(
        fingerprint=sha16(key),
        rule_id=rule_id,
        title=title,
        classification_input=classification_input.strip(),
        trigger_files=trigger_files,
        affected_candidates=affected_candidates,
        evidence_lines=evidence_lines,
        issue_title=issue_title,
        labels=labels,
    )


def detect_findings(pr: dict[str, Any], diff_text: str) -> list[Finding]:
    findings: list[Finding] = []
    files = relative_paths(pr["files"])
    active_files = [path for path in files if is_active_surface(path)]
    pr_number = pr["number"]
    pr_url = pr["url"]
    pr_title = pr["title"]
    added_lines = parse_added_lines(diff_text)

    service_runtime_files = [
        path
        for path in active_files
        if path.startswith("services/")
        or path.startswith("core/")
        or path.startswith("infrastructure/database/")
        or path
        in {
            "infrastructure/compose/compose.blue.yml",
            "infrastructure/compose/compose.red.yml",
            "infrastructure/compose/SERVICE_MAPPING.md",
            "infrastructure/compose/COMPOSE_LAYERS.md",
        }
    ]
    if service_runtime_files and not touched(active_files, ARCHITECTURE_DOCS):
        trigger_files = shortlist(service_runtime_files)
        affected_candidates = trigger_files + ARCHITECTURE_DOCS
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed service/runtime surfaces {", ".join(trigger_files)}, but did not update knowledge/ARCHITECTURE_MAP.md or knowledge/governance/SERVICE_CATALOG.md. Evidence is repo-backed from the merged PR diff {pr_url}. Affected artifacts are {", ".join(affected_candidates)}. The likely follow-up is a small, documentation-only architecture/service-catalog reconciliation if drift is real.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="architecture_service_catalog_drift",
                title="Service/runtime change without architecture catalog follow-up",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=affected_candidates,
                evidence_lines=[],
                issue_title=f"Reconcile architecture docs after PR #{pr_number} service/runtime changes",
                labels=["scope:docs", "type:docs", "agent:codex"],
            )
        )

    control_runtime_files = [
        path
        for path in active_files
        if path.startswith(".github/workflows/")
        or path.startswith(".github/scripts/")
        or path in {"infrastructure/monitoring/alerts.yml", "infrastructure/monitoring/prometheus.yml"}
    ]
    support_followup_touched = touched(active_files, RUNBOOK_SURFACES + EVIDENCE_SURFACES) or touched_prefix(
        active_files, ("docs/runbooks/", "docs/operations/", "docs/ci/")
    )
    if control_runtime_files and not support_followup_touched:
        trigger_files = shortlist(control_runtime_files)
        affected_candidates = trigger_files + RUNBOOK_SURFACES
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed workflow/control surfaces {", ".join(trigger_files)}, but no runbook or evidence companion was changed in docs/runbooks/, docs/operations/, docs/ci/, CURRENT_STATUS.md, or docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md. Evidence is repo-backed from merged PR diff {pr_url}. Affected artifacts are {", ".join(affected_candidates)}. If a small control-note or runbook follow-up is clearly needed, treat it as a separate fix package; otherwise keep it in the control thread.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="runbook_evidence_followup_drift",
                title="Workflow/control change without runbook or evidence follow-up",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=affected_candidates,
                evidence_lines=[],
                issue_title=f"Reconcile control docs after PR #{pr_number} workflow changes",
                labels=["scope:ci", "scope:docs", "type:docs", "agent:codex"],
            )
        )

    discovery_trigger_files = [
        path
        for path in active_files
        if path.startswith(".github/workflows/")
        or path.startswith("docs/runbooks/")
        or path in ARCHITECTURE_DOCS
        or path in {"README.md", "docs/index.md", "services/README.md", "infrastructure/compose/README.md"}
    ]
    if discovery_trigger_files and not touched(active_files, DISCOVERY_SURFACES):
        trigger_files = shortlist(discovery_trigger_files)
        affected_candidates = trigger_files + DISCOVERY_SURFACES
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed front-door or operator-facing surfaces {", ".join(trigger_files)}, but did not touch mcp_navpack_working_repo/ENTRYPOINTS.yaml or mcp_navpack_working_repo/CHEATSHEET.md. Evidence is repo-backed from merged PR diff {pr_url}. Affected artifacts are {", ".join(affected_candidates)}. This may leave discovery surfaces stale, but the need for a repo change is not proven from the diff alone.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="discovery_surface_drift",
                title="Possible discovery-surface drift after operator-facing changes",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=affected_candidates,
                evidence_lines=[],
                issue_title=f"Update discovery surfaces after PR #{pr_number}",
                labels=["scope:docs", "type:docs", "agent:codex"],
            )
        )

    canon_hits: list[tuple[str, str, str]] = []
    for path, lines in added_lines.items():
        if not is_active_surface(path):
            continue
        if path.startswith(("tests/", "docs/archive/", "knowledge/logs/")):
            continue
        for line in lines:
            for label, pattern in CANON_PATTERNS:
                if pattern.search(line):
                    canon_hits.append((path, label, line.strip()))
    if canon_hits:
        seen_files: list[str] = []
        evidence_lines: list[str] = []
        for path, label, line in canon_hits[:6]:
            if path not in seen_files:
                seen_files.append(path)
            evidence_lines.append(f"{path}: {label}: {line}")
        trigger_files = shortlist(seen_files)
        joined_evidence = "; ".join(evidence_lines)
        finding_input = f"""
PR #{pr_number} ({pr_title}) reintroduced active-surface canon or terminology drift. Repo-backed added lines show: {joined_evidence}. Evidence comes directly from merged PR diff {pr_url}. The likely fix is a small, separate clean-up in the touched active files only.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="canon_terminology_drift",
                title="Canon or terminology drift reintroduced in active surfaces",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=trigger_files,
                evidence_lines=evidence_lines,
                issue_title=f"Remove reintroduced canon drift after PR #{pr_number}",
                labels=["scope:docs", "type:docs", "agent:codex"],
            )
        )

    unique: dict[str, Finding] = {}
    for finding in findings:
        unique[finding.fingerprint] = finding
    return list(unique.values())


def classify_finding(
    *,
    prompt_file: Path,
    finding: Finding,
) -> dict[str, Any]:
    raw = run_command(
        [
            "gh",
            "models",
            "run",
            "--file",
            str(prompt_file),
            "--var",
            f"input={finding.classification_input}",
        ]
    )
    payload = json.loads(raw)
    if payload.get("classification") not in {"report_only", "follow_up_issue", "unclear"}:
        raise RuntimeError("classifier returned invalid classification")
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise RuntimeError("classifier returned invalid confidence")
    affected = payload.get("affected_artifacts")
    if not isinstance(affected, list) or not all(isinstance(item, str) and item for item in affected):
        raise RuntimeError("classifier returned invalid affected_artifacts")
    normalized_affected: list[str] = []
    for item in affected:
        cleaned = item.strip()
        if cleaned and cleaned not in normalized_affected:
            normalized_affected.append(cleaned)
    payload["affected_artifacts"] = normalized_affected
    next_step = payload.get("suggested_next_step")
    if not isinstance(next_step, str) or not next_step:
        raise RuntimeError("classifier returned invalid suggested_next_step")
    return payload


def gh_repo_json(repo: str, args: list[str]) -> Any:
    return json.loads(run_gh_repo(repo, args))


def gh_api_json(args: list[str], *, input_text: str | None = None) -> Any:
    return json.loads(run_gh_api(args, input_text=input_text))


def find_existing_issue(repo: str, marker: str) -> dict[str, Any] | None:
    issues = gh_api_json(
        [
            f"repos/{repo}/issues?state=all&per_page=100",
        ],
    )
    flattened: list[dict[str, Any]]
    if isinstance(issues, list):
        flattened = [issue for issue in issues if isinstance(issue, dict)]
    else:
        flattened = [issues] if isinstance(issues, dict) else []
    matches = [
        issue
        for issue in flattened
        if "pull_request" not in issue and marker in (issue.get("body") or "")
    ]
    if not matches:
        return None
    matches.sort(key=lambda issue: issue.get("created_at") or "", reverse=True)
    return matches[0]


def ensure_issue(
    *,
    repo: str,
    pr: dict[str, Any],
    finding: Finding,
    classification: dict[str, Any],
) -> dict[str, Any]:
    marker = ISSUE_MARKER_TEMPLATE.format(fingerprint=finding.fingerprint)
    existing = find_existing_issue(repo, marker)
    if existing is not None:
        return {
            "action": "existing_open" if existing.get("state") == "open" else "existing_closed",
            "number": existing.get("number"),
            "url": existing.get("html_url"),
        }

    affected = "\n".join(f"- `{path}`" for path in classification["affected_artifacts"])
    body = (
        f"## Post-Merge Follow-up Finding\n\n"
        f"{marker}\n\n"
        f"- Source PR: #{pr['number']} ({pr['url']})\n"
        f"- Rule: `{finding.rule_id}`\n"
        f"- Classification: `{classification['classification']}`\n"
        f"- Confidence: `{classification['confidence']}`\n\n"
        f"### Why this is a small follow-up\n\n"
        f"{classification['suggested_next_step']}\n\n"
        f"### Affected artifacts\n\n"
        f"{affected}\n\n"
        f"### Repo-backed evidence\n\n"
        f"{finding.classification_input}\n"
    )

    args = [
        "issue",
        "create",
        "--title",
        finding.issue_title,
        "--body",
        body,
    ]
    for label in finding.labels:
        args.extend(["--label", label])
    url = run_gh_repo(repo, args).strip()
    number = int(url.rstrip("/").split("/")[-1])
    return {"action": "created", "number": number, "url": url}


def load_issue_comments(repo: str, issue_number: int) -> list[dict[str, Any]]:
    comments = gh_api_json(
        [
            f"repos/{repo}/issues/{issue_number}/comments?per_page=100",
        ],
    )
    if isinstance(comments, list):
        flattened = [comment for comment in comments if isinstance(comment, dict)]
    else:
        flattened = [comments] if isinstance(comments, dict) else []
    return flattened


def upsert_control_comment(
    *,
    repo: str,
    pr: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    marker = COMMENT_MARKER_TEMPLATE.format(pr_number=pr["number"])
    body_lines = [
        COMMENT_HEADER,
        "",
        marker,
        "",
        f"- PR: #{pr['number']} ({pr['url']})",
        f"- Title: {pr['title']}",
        f"- Findings: {len(findings)}",
        "",
    ]
    for finding in findings:
        body_lines.extend(
            [
                f"### {finding['title']}",
                "",
                f"- Rule: `{finding['rule_id']}`",
                f"- Classification: `{finding['classification']['classification']}`",
                f"- Confidence: `{finding['classification']['confidence']}`",
                f"- Affected artifacts: `{', '.join(finding['classification']['affected_artifacts'])}`",
                f"- Suggested next step: {finding['classification']['suggested_next_step']}",
                "",
            ]
        )
    body = "\n".join(body_lines).strip() + "\n"
    body_json = json.dumps({"body": body})

    comments = load_issue_comments(repo, CONTROL_ISSUE_NUMBER)
    existing = next((comment for comment in comments if marker in (comment.get("body") or "")), None)
    if existing is None:
        response = gh_api_json(
            [
                "--method",
                "POST",
                f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments",
                "--input",
                "-",
            ],
            input_text=body_json,
        )
        return {"action": "created", "url": response.get("html_url"), "body": body}

    response = gh_api_json(
        [
            "--method",
            "PATCH",
            f"repos/{repo}/issues/comments/{existing['id']}",
            "--input",
            "-",
        ],
        input_text=body_json,
    )
    return {"action": "updated", "url": response.get("html_url"), "body": body}


def build_summary(result: dict[str, Any]) -> str:
    pr = result["pr"]
    lines = [
        "# CDB Post-Merge Follow-up Scan",
        "",
        f"- PR: #{pr['number']} ({pr['url']})",
        f"- Title: {pr['title']}",
        f"- Mode: `{result['publish_mode']}`",
        f"- Candidate findings: `{result['candidate_count']}`",
        f"- Classified findings: `{len(result['findings'])}`",
        "",
    ]
    if not result["findings"]:
        lines.extend(
            [
                "## Result",
                "",
                "No repo-backed follow-up finding was emitted by the deterministic V1 rules.",
                "",
            ]
        )
        return "\n".join(lines)

    for finding in result["findings"]:
        cls = finding["classification"]
        lines.extend(
            [
                f"## {finding['title']}",
                "",
                f"- Rule: `{finding['rule_id']}`",
                f"- Classification: `{cls['classification']}`",
                f"- Confidence: `{cls['confidence']}`",
                f"- Affected artifacts: `{', '.join(cls['affected_artifacts'])}`",
                f"- Suggested next step: {cls['suggested_next_step']}",
            ]
        )
        if finding.get("publication"):
            publication = finding["publication"]
            lines.append(f"- Publication: `{publication['action']}`")
            if publication.get("url"):
                lines.append(f"- URL: {publication['url']}")
        lines.append("")
    if result.get("control_comment"):
        lines.extend(
            [
                "## Control Comment",
                "",
                f"- Action: `{result['control_comment']['action']}`",
                f"- URL: {result['control_comment'].get('url', 'n/a')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(result_file: Path, summary_file: Path, result: dict[str, Any]) -> None:
    result_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary_file.write_text(build_summary(result), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan merged PRs for small post-merge follow-up drift")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    parser.add_argument("--pr-number", required=True, type=int, help="Merged PR number to inspect")
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    parser.add_argument("--summary-file", required=True, type=Path)
    parser.add_argument(
        "--publish-mode",
        choices=["dry_run", "publish"],
        default="dry_run",
        help="Whether to publish comments/issues or only write artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pr = gh_repo_json(
        args.repo,
        [
            "pr",
            "view",
            str(args.pr_number),
            "--json",
            "number,title,url,mergedAt,files",
        ],
    )
    if not pr.get("mergedAt"):
        raise RuntimeError(f"PR #{args.pr_number} is not merged; scanner is merged-PR only")

    diff_text = run_gh_repo(args.repo, ["pr", "diff", str(args.pr_number)])
    candidates = detect_findings(pr, diff_text)

    results: list[dict[str, Any]] = []
    comment_findings: list[dict[str, Any]] = []
    for finding in candidates:
        classification = classify_finding(
            prompt_file=args.prompt_file,
            finding=finding,
        )
        item = asdict(finding)
        item["classification"] = classification
        if args.publish_mode == "publish":
            if classification["classification"] == "follow_up_issue":
                item["publication"] = ensure_issue(
                    repo=args.repo,
                    pr=pr,
                    finding=finding,
                    classification=classification,
                )
            else:
                comment_findings.append(item)
        results.append(item)

    control_comment: dict[str, Any] | None = None
    if args.publish_mode == "publish" and comment_findings:
        control_comment = upsert_control_comment(
            repo=args.repo,
            pr=pr,
            findings=comment_findings,
        )

    payload = {
        "repo": args.repo,
        "publish_mode": args.publish_mode,
        "pr": {
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["url"],
            "mergedAt": pr["mergedAt"],
        },
        "candidate_count": len(candidates),
        "findings": results,
        "control_comment": control_comment,
    }
    write_outputs(args.result_file, args.summary_file, payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - fail-closed entrypoint
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
