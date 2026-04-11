#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

CONTROL_ISSUE_NUMBER = 1445
COMMENT_MARKER = "<!-- cdb-weekly-hygiene:{week_key} -->"
FOLLOWUP_MARKER = "<!-- cdb-weekly-hygiene-followup:{fingerprint} -->"
REPORT_WINDOW_DAYS = 21
STALE_DAYS = 60
MAX_FOLLOWUP_DEFAULT = 2
BASE_BRANCH = "main"


@dataclass
class Candidate:
    rule_id: str
    title: str
    classification: str
    confidence: float
    affected_artifacts: list[str]
    suggested_next_step: str
    evidence: str
    cleanup_state: str | None = None
    issue_title: str | None = None
    issue_labels: list[str] | None = None
    fingerprint: str | None = None


def run(args: list[str], *, input_text: str | None = None) -> str:
    proc = subprocess.run(
        args,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}"
        )
    return proc.stdout


def gh_json(repo: str, args: list[str]) -> Any:
    out = run(["gh"] + args + ["--repo", repo])
    return json.loads(out)


def gh_api_json(args: list[str], *, input_text: str | None = None) -> Any:
    out = run(["gh", "api"] + args, input_text=input_text)
    return json.loads(out)


def week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def parse_active_workflows(register_path: Path) -> dict[str, str]:
    text = register_path.read_text(encoding="utf-8")
    mapping: dict[str, str] = {}
    in_table = False
    for line in text.splitlines():
        if line.strip() == "## Aktive Infra-Workflows":
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table:
            continue
        if not line.startswith("| `"):
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cols) < 3:
            continue
        workflow = cols[0].strip("`")
        trigger = cols[1]
        mapping[workflow] = trigger
    return mapping


def extract_triggers(workflow_text: str) -> set[str]:
    triggers: set[str] = set()
    if re.search(r"(?m)^\s*schedule\s*:", workflow_text):
        triggers.add("schedule")
    if re.search(r"(?m)^\s*workflow_dispatch\s*:", workflow_text):
        triggers.add("workflow_dispatch")
    if re.search(r"(?m)^\s*workflow_run\s*:", workflow_text):
        triggers.add("workflow_run")
    if re.search(r"(?m)^\s*pull_request\s*:", workflow_text):
        triggers.add("pull_request")
    return triggers


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    value = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return None


def make_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def extract_issue_number_from_branch(branch_name: str) -> int | None:
    match = re.search(
        r"(?:^|[-_/])(issue|ops|bug|feat|feature|codex)[-_/]?(\d+)(?:$|[-_/])",
        branch_name,
    )
    if not match:
        return None
    try:
        return int(match.group(2))
    except ValueError:
        return None


def branch_obsolescence_candidates(
    repo: str, open_issues: list[dict[str, Any]]
) -> list[Candidate]:
    try:
        branches = gh_api_json([f"repos/{repo}/branches?per_page=100"])
        open_prs = gh_json(
            repo,
            [
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "200",
                "--json",
                "headRefName",
            ],
        )
        closed_prs = gh_json(
            repo,
            [
                "pr",
                "list",
                "--state",
                "closed",
                "--limit",
                "200",
                "--json",
                "number,headRefName,url,mergedAt,closedAt",
            ],
        )
    except Exception as exc:
        return [
            Candidate(
                rule_id="branch_obsolescence",
                title="Branch obsolescence scan unavailable",
                classification="unclear",
                confidence=0.55,
                affected_artifacts=["refs/heads/*"],
                suggested_next_step=(
                    "Treat branch cleanup as blocked for this run and inspect scanner access/auth before any deletion decision."
                ),
                evidence=f"Repo-backed branch scan failed: {exc}",
                cleanup_state="unclear",
            )
        ]

    if not isinstance(branches, list):
        return [
            Candidate(
                rule_id="branch_obsolescence",
                title="Branch obsolescence scan returned unexpected payload",
                classification="unclear",
                confidence=0.52,
                affected_artifacts=["refs/heads/*"],
                suggested_next_step="Fail closed and inspect branch API response shape before acting on cleanup decisions.",
                evidence="Expected a list of branches from GitHub API.",
                cleanup_state="unclear",
            )
        ]

    open_pr_heads = {
        item.get("headRefName") for item in open_prs if isinstance(item, dict)
    }
    latest_closed_by_head: dict[str, dict[str, Any]] = {}
    for item in closed_prs:
        if not isinstance(item, dict):
            continue
        head = item.get("headRefName")
        if not head or head in latest_closed_by_head:
            continue
        latest_closed_by_head[head] = item

    open_issue_numbers = {
        int(item["number"])
        for item in open_issues
        if isinstance(item.get("number"), int)
    }
    findings: list[Candidate] = []
    for raw_branch in sorted(
        branches, key=lambda x: x.get("name", "") if isinstance(x, dict) else ""
    ):
        if not isinstance(raw_branch, dict):
            continue
        branch_name = raw_branch.get("name")
        if not isinstance(branch_name, str):
            continue
        if branch_name in {BASE_BRANCH, "master"}:
            continue
        if raw_branch.get("protected") is True:
            continue
        if branch_name in open_pr_heads:
            continue

        compare_ref = f"{quote(BASE_BRANCH, safe='')}...{quote(branch_name, safe='')}"
        try:
            compare = gh_api_json([f"repos/{repo}/compare/{compare_ref}"])
        except Exception:
            findings.append(
                Candidate(
                    rule_id="branch_obsolescence",
                    title=f"Branch obsolescence unclear: {branch_name}",
                    classification="unclear",
                    confidence=0.58,
                    affected_artifacts=[f"branch:{branch_name}"],
                    suggested_next_step=(
                        "Keep branch untouched and inspect compare API state manually before classifying cleanup readiness."
                    ),
                    evidence=f"Could not compare {branch_name} against {BASE_BRANCH}.",
                    cleanup_state="unclear",
                )
            )
            continue

        ahead_by = int(compare.get("ahead_by", 0))
        behind_by = int(compare.get("behind_by", 0))
        status = str(compare.get("status", "unknown"))
        if ahead_by > 0:
            continue

        linked_issue = extract_issue_number_from_branch(branch_name)
        closed_pr = latest_closed_by_head.get(branch_name)
        pr_hint = "no closed PR metadata found"
        if closed_pr and closed_pr.get("mergedAt"):
            pr_hint = (
                f"last PR #{closed_pr.get('number')} merged ({closed_pr.get('url')})"
            )
        elif closed_pr and closed_pr.get("closedAt"):
            pr_hint = f"last PR #{closed_pr.get('number')} closed without merge ({closed_pr.get('url')})"

        if linked_issue is not None and linked_issue in open_issue_numbers:
            findings.append(
                Candidate(
                    rule_id="branch_obsolescence",
                    title=f"Branch cleanup unclear due to open linked issue: {branch_name}",
                    classification="unclear",
                    confidence=0.66,
                    affected_artifacts=[
                        f"branch:{branch_name}",
                        f"issue #{linked_issue}",
                    ],
                    suggested_next_step=(
                        "Do not delete this branch yet; reconcile linked open issue ownership/status first."
                    ),
                    evidence=(
                        f"Branch {branch_name} has no unique commits vs {BASE_BRANCH} "
                        f"(status={status}, ahead={ahead_by}, behind={behind_by}) but appears linked to open issue #{linked_issue}; "
                        f"{pr_hint}."
                    ),
                    cleanup_state="unclear",
                )
            )
            continue

        fingerprint = make_fingerprint(
            f"branch_cleanup_ready:{branch_name}:{status}:{ahead_by}:{behind_by}"
        )
        findings.append(
            Candidate(
                rule_id="branch_obsolescence",
                title=f"Branch cleanup-ready candidate: {branch_name}",
                classification="follow_up_issue",
                confidence=0.88,
                affected_artifacts=[
                    f"branch:{branch_name}",
                    f"refs/heads/{branch_name}",
                ],
                suggested_next_step=(
                    "Run report-first confirmation in the weekly lane and perform branch deletion only via explicit manual approval."
                ),
                evidence=(
                    f"Branch {branch_name} has no unique commits vs {BASE_BRANCH} "
                    f"(status={status}, ahead={ahead_by}, behind={behind_by}), no open PR, and no linked open issue signal; {pr_hint}."
                ),
                cleanup_state="cleanup_ready",
                issue_title=f"Weekly hygiene: review deletion of obsolete branch {branch_name}",
                issue_labels=[
                    "scope:ci",
                    "type:chore",
                    "agent:codex",
                    "manual-approval",
                ],
                fingerprint=fingerprint,
            )
        )

    if findings:
        return findings
    return [
        Candidate(
            rule_id="branch_obsolescence",
            title="No cleanup-ready obsolete branch candidates in this run",
            classification="report_only",
            confidence=0.8,
            affected_artifacts=["refs/heads/*"],
            suggested_next_step="Keep weekly branch obsolescence scan active; no branch delete candidate this week.",
            evidence="No non-protected branch without open PR met the cleanup-ready gate in this run.",
            cleanup_state="report_only",
        )
    ]


def local_worktree_boundary_candidate() -> Candidate:
    return Candidate(
        rule_id="worktree_obsolescence_boundary",
        title="Local worktree cleanup remains manual/local-only",
        classification="report_only",
        confidence=0.95,
        affected_artifacts=[
            "tools/cleanup/worktree_obsolescence_cleanup.ps1",
            "docs/runbooks/CDB_WEEKLY_CONTROL_HYGIENE_CLASSIFIER.md",
        ],
        suggested_next_step=(
            "Run local worktree cleanup in dry_run mode first and execute only after explicit manual approval."
        ),
        evidence=(
            "GitHub-hosted Actions cannot inspect or delete workstation-local worktrees (for example D:\\Dev\\...). "
            "Weekly hosted scan publishes classification only; local cleanup is a separate manual path."
        ),
        cleanup_state="report_only",
    )


def cleanup_state_counts(candidates: list[Candidate]) -> dict[str, int]:
    counts = {"cleanup_ready": 0, "report_only": 0, "unclear": 0}
    for cand in candidates:
        if cand.cleanup_state in counts:
            counts[cand.cleanup_state] += 1
    return counts


def parked_active_drift(open_issues: list[dict[str, Any]]) -> list[Candidate]:
    candidates: list[Candidate] = []
    active_explicit = {"prio:must", "prio:should"}
    active_prefixes = ("stage:", "milestone:")
    for issue in open_issues:
        labels = [label["name"] for label in issue.get("labels", [])]
        if "status:parked" not in labels:
            continue
        active_labels = [
            name
            for name in labels
            if name in active_explicit or name.startswith(active_prefixes)
        ]
        if not active_labels:
            continue
        issue_no = issue["number"]
        evidence = (
            f"Issue #{issue_no} is labeled status:parked but still has active delivery labels "
            f"{', '.join(active_labels)}."
        )
        fingerprint = make_fingerprint(
            f"parked_active:{issue_no}:{','.join(sorted(active_labels))}"
        )
        candidates.append(
            Candidate(
                rule_id="parked_active_drift",
                title=f"Parked vs active label drift on issue #{issue_no}",
                classification="follow_up_issue",
                confidence=0.92,
                affected_artifacts=[f"issue #{issue_no}"],
                suggested_next_step=(
                    "Open a narrow label-reconciliation follow-up that removes active delivery labels "
                    "or un-parks the issue explicitly."
                ),
                evidence=evidence,
                issue_title=f"Reconcile parked/active label drift on issue #{issue_no}",
                issue_labels=["scope:docs", "type:docs", "agent:codex"],
                fingerprint=fingerprint,
            )
        )
    return candidates


def stale_open_issue_candidates(
    open_issues: list[dict[str, Any]], now: datetime
) -> list[Candidate]:
    cutoff = now - timedelta(days=STALE_DAYS)
    stale: list[dict[str, Any]] = []
    for issue in open_issues:
        number = issue["number"]
        if number in {CONTROL_ISSUE_NUMBER, 1566, 1567}:
            continue
        labels = [label["name"] for label in issue.get("labels", [])]
        if "status:parked" in labels:
            continue
        created = parse_iso(issue.get("createdAt"))
        if created and created < cutoff:
            stale.append(issue)
    if not stale:
        return []
    stale_sorted = sorted(stale, key=lambda item: item.get("createdAt") or "")
    top = stale_sorted[:5]
    refs = ", ".join(f"#{item['number']}" for item in top)
    evidence = (
        f"{len(stale)} open issues are older than {STALE_DAYS} days and not parked "
        f"(sample: {refs})."
    )
    return [
        Candidate(
            rule_id="old_open_issues_without_leverage",
            title="Aging open issue backlog snapshot",
            classification="report_only",
            confidence=0.78,
            affected_artifacts=[f"issue #{item['number']}" for item in top],
            suggested_next_step=(
                "Review the listed issues in Monday hygiene and explicitly decide close, park, "
                "or concrete next action."
            ),
            evidence=evidence,
        )
    ]


def workflow_register_drift(
    workflow_dir: Path, register_map: dict[str, str]
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for workflow_name, trigger_note in register_map.items():
        file_path = workflow_dir / workflow_name
        if not file_path.exists():
            evidence = f"{workflow_name} is listed in CONTROL_REGISTER but file is missing in .github/workflows/."
            fingerprint = make_fingerprint(f"workflow_missing:{workflow_name}")
            candidates.append(
                Candidate(
                    rule_id="workflow_register_drift",
                    title=f"Workflow listed but file missing: {workflow_name}",
                    classification="follow_up_issue",
                    confidence=0.95,
                    affected_artifacts=[
                        "docs/runbooks/CONTROL_REGISTER.md",
                        f".github/workflows/{workflow_name}",
                    ],
                    suggested_next_step=(
                        "Open a small follow-up to either restore the workflow file or remove/update "
                        "the CONTROL_REGISTER entry."
                    ),
                    evidence=evidence,
                    issue_title=f"Reconcile missing workflow file for {workflow_name}",
                    issue_labels=["scope:ci", "scope:docs", "type:docs", "agent:codex"],
                    fingerprint=fingerprint,
                )
            )
            continue

        wf_text = file_path.read_text(encoding="utf-8")
        triggers = extract_triggers(wf_text)
        note = trigger_note.lower()
        manual_only_note = "manuell" in note and not any(
            word in note
            for word in (
                "mo",
                "di",
                "mi",
                "do",
                "fr",
                "sa",
                "so",
                "wöchentlich",
                "taeglich",
                "täglich",
            )
        )
        if manual_only_note and "schedule" in triggers:
            evidence = f"{workflow_name} is marked manual in CONTROL_REGISTER but workflow still defines schedule trigger."
            fingerprint = make_fingerprint(f"workflow_manual_schedule:{workflow_name}")
            candidates.append(
                Candidate(
                    rule_id="workflow_register_drift",
                    title=f"Manual-vs-schedule drift: {workflow_name}",
                    classification="follow_up_issue",
                    confidence=0.94,
                    affected_artifacts=[
                        "docs/runbooks/CONTROL_REGISTER.md",
                        f".github/workflows/{workflow_name}",
                    ],
                    suggested_next_step=(
                        "Open a narrow follow-up to align workflow triggers and CONTROL_REGISTER note."
                    ),
                    evidence=evidence,
                    issue_title=f"Align trigger note for {workflow_name}",
                    issue_labels=["scope:ci", "scope:docs", "type:docs", "agent:codex"],
                    fingerprint=fingerprint,
                )
            )
        if "wöchentlich" in note and "schedule" not in triggers:
            evidence = f"{workflow_name} is marked weekly in CONTROL_REGISTER but has no schedule trigger."
            candidates.append(
                Candidate(
                    rule_id="workflow_register_drift",
                    title=f"Weekly trigger note drift: {workflow_name}",
                    classification="unclear",
                    confidence=0.64,
                    affected_artifacts=[
                        "docs/runbooks/CONTROL_REGISTER.md",
                        f".github/workflows/{workflow_name}",
                    ],
                    suggested_next_step=(
                        "Verify intent in control thread first; if weekly execution is still required, open a small "
                        "trigger-note reconciliation follow-up."
                    ),
                    evidence=evidence,
                )
            )
    return candidates


def recent_workflow_noise(
    repo: str, register_map: dict[str, str], now: datetime
) -> list[Candidate]:
    candidates: list[Candidate] = []
    since = now - timedelta(days=REPORT_WINDOW_DAYS)
    for workflow_name in register_map:
        try:
            runs = gh_json(
                repo,
                [
                    "run",
                    "list",
                    "--workflow",
                    workflow_name,
                    "--limit",
                    "10",
                    "--json",
                    "databaseId,conclusion,createdAt,event,status",
                ],
            )
        except Exception:
            continue
        recent = []
        for run_item in runs:
            created = parse_iso(run_item.get("createdAt"))
            if created and created >= since:
                recent.append(run_item)
        if len(recent) < 3:
            continue
        failures = [item for item in recent if item.get("conclusion") == "failure"]
        if len(failures) >= 3 and len(failures) == len(recent):
            evidence = (
                f"{workflow_name} had {len(failures)} failures in the last {REPORT_WINDOW_DAYS} days "
                f"with no success in that window."
            )
            candidates.append(
                Candidate(
                    rule_id="workflow_noise",
                    title=f"Recurring workflow noise candidate: {workflow_name}",
                    classification="report_only",
                    confidence=0.73,
                    affected_artifacts=[f".github/workflows/{workflow_name}"],
                    suggested_next_step=(
                        "Review this workflow in Thursday inventory and decide explicit park/fix action instead of "
                        "leaving repeated noise unattended."
                    ),
                    evidence=evidence,
                )
            )
    return candidates


def existing_followup(repo: str, marker: str) -> dict[str, Any] | None:
    issues = gh_api_json([f"repos/{repo}/issues?state=all&per_page=100"])
    if not isinstance(issues, list):
        return None
    for issue in sorted(issues, key=lambda x: x.get("created_at", ""), reverse=True):
        if "pull_request" in issue:
            continue
        if marker in (issue.get("body") or ""):
            return issue
    return None


def ensure_followup_issue(repo: str, candidate: Candidate) -> dict[str, Any]:
    assert candidate.fingerprint is not None
    assert candidate.issue_title is not None
    marker = FOLLOWUP_MARKER.format(fingerprint=candidate.fingerprint)
    found = existing_followup(repo, marker)
    if found:
        return {
            "action": "existing",
            "number": found["number"],
            "url": found["html_url"],
        }

    body = (
        "## Weekly Control Hygiene Follow-up\n\n"
        f"{marker}\n\n"
        f"- Rule: `{candidate.rule_id}`\n"
        f"- Confidence: `{candidate.confidence}`\n"
        f"- Evidence: {candidate.evidence}\n\n"
        "### Affected artifacts\n\n"
        + "\n".join(f"- `{item}`" for item in candidate.affected_artifacts)
        + "\n\n### Next step\n\n"
        + candidate.suggested_next_step
        + "\n"
    )
    args = ["issue", "create", "--title", candidate.issue_title, "--body", body]
    for label in candidate.issue_labels or []:
        args.extend(["--label", label])
    url = run(["gh"] + args + ["--repo", repo]).strip()
    issue_no = int(url.rstrip("/").split("/")[-1])
    return {"action": "created", "number": issue_no, "url": url}


def build_comment(
    week: str, candidates: list[Candidate], issue_events: list[dict[str, Any]]
) -> str:
    counts = cleanup_state_counts(candidates)
    lines = [
        "## Weekly Control Hygiene Classifier",
        "",
        COMMENT_MARKER.format(week_key=week),
        "",
        f"- Week: `{week}`",
        f"- Findings: `{len(candidates)}`",
        (
            "- Cleanup states: "
            f"`cleanup_ready={counts['cleanup_ready']}`, "
            f"`report_only={counts['report_only']}`, "
            f"`unclear={counts['unclear']}`"
        ),
        f"- Follow-up issues emitted: `{len(issue_events)}`",
        "",
    ]
    if not candidates:
        lines.extend(
            [
                "No repo-backed weekly hygiene findings in this run.",
                "",
            ]
        )
    for cand in candidates:
        lines.extend(
            [
                f"### {cand.title}",
                f"- Rule: `{cand.rule_id}`",
                f"- Classification: `{cand.classification}`",
                (
                    f"- Cleanup state: `{cand.cleanup_state}`"
                    if cand.cleanup_state is not None
                    else "- Cleanup state: `n/a`"
                ),
                f"- Confidence: `{cand.confidence}`",
                f"- Affected artifacts: `{', '.join(cand.affected_artifacts)}`",
                f"- Suggested next step: {cand.suggested_next_step}",
                f"- Evidence: {cand.evidence}",
                "",
            ]
        )
    if issue_events:
        lines.append("### Follow-up issue actions")
        for event in issue_events:
            lines.append(f"- `{event['action']}`: #{event['number']} ({event['url']})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def upsert_control_comment(repo: str, week: str, body: str) -> dict[str, Any]:
    marker = COMMENT_MARKER.format(week_key=week)
    comments = gh_api_json(
        [f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments?per_page=100"]
    )
    existing = None
    if isinstance(comments, list):
        for item in comments:
            if marker in (item.get("body") or ""):
                existing = item
                break
    payload = json.dumps({"body": body})
    if existing is None:
        created = gh_api_json(
            [
                "--method",
                "POST",
                f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments",
                "--input",
                "-",
            ],
            input_text=payload,
        )
        return {"action": "created", "url": created.get("html_url")}
    updated = gh_api_json(
        [
            "--method",
            "PATCH",
            f"repos/{repo}/issues/comments/{existing['id']}",
            "--input",
            "-",
        ],
        input_text=payload,
    )
    return {"action": "updated", "url": updated.get("html_url")}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weekly control hygiene classifier")
    p.add_argument("--repo", required=True)
    p.add_argument("--register-file", type=Path, required=True)
    p.add_argument("--workflow-dir", type=Path, required=True)
    p.add_argument("--result-file", type=Path, required=True)
    p.add_argument("--summary-file", type=Path, required=True)
    p.add_argument("--publish-mode", choices=["dry_run", "publish"], default="dry_run")
    p.add_argument("--max-followup-issues", type=int, default=MAX_FOLLOWUP_DEFAULT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.now(UTC)
    wk = week_key(now)

    open_issues = gh_json(
        args.repo,
        [
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            "200",
            "--json",
            "number,title,createdAt,labels,url",
        ],
    )
    register_map = parse_active_workflows(args.register_file)

    findings: list[Candidate] = []
    findings.extend(parked_active_drift(open_issues))
    findings.extend(stale_open_issue_candidates(open_issues, now))
    findings.extend(workflow_register_drift(args.workflow_dir, register_map))
    findings.extend(recent_workflow_noise(args.repo, register_map, now))
    findings.extend(branch_obsolescence_candidates(args.repo, open_issues))
    findings.append(local_worktree_boundary_candidate())

    # keep deterministic order: follow_up_issue first, then unclear, then report_only
    order = {"follow_up_issue": 0, "unclear": 1, "report_only": 2}
    findings.sort(key=lambda x: (order.get(x.classification, 9), x.rule_id, x.title))

    issue_events: list[dict[str, Any]] = []
    if args.publish_mode == "publish":
        followups = [f for f in findings if f.classification == "follow_up_issue"][
            : args.max_followup_issues
        ]
        for cand in followups:
            issue_events.append(ensure_followup_issue(args.repo, cand))

    comment_body = build_comment(wk, findings, issue_events)
    comment_event = None
    if args.publish_mode == "publish":
        comment_event = upsert_control_comment(args.repo, wk, comment_body)

    result = {
        "repo": args.repo,
        "week_key": wk,
        "publish_mode": args.publish_mode,
        "findings_count": len(findings),
        "cleanup_state_counts": cleanup_state_counts(findings),
        "findings": [asdict(item) for item in findings],
        "issue_events": issue_events,
        "control_comment": comment_event,
    }

    args.result_file.parent.mkdir(parents=True, exist_ok=True)
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    args.result_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.summary_file.write_text(comment_body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
