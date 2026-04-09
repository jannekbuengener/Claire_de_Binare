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


CONTROL_ISSUE_NUMBER = 1445
COMMENT_MARKER = "<!-- cdb-daily-delta:{day_key} -->"
FOLLOWUP_MARKER = "<!-- cdb-daily-delta-followup:{fingerprint} -->"
LOOKBACK_HOURS = 30
MAX_FOLLOWUP_DEFAULT = 1


@dataclass
class Candidate:
    rule_id: str
    title: str
    classification: str
    confidence: float
    affected_artifacts: list[str]
    suggested_next_step: str
    evidence: str
    fingerprint: str
    issue_title: str | None = None
    issue_labels: list[str] | None = None


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
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def gh_json(repo: str, args: list[str]) -> Any:
    out = run(["gh"] + args + ["--repo", repo])
    return json.loads(out)


def gh_api_json(args: list[str], *, input_text: str | None = None) -> Any:
    out = run(["gh", "api"] + args, input_text=input_text)
    return json.loads(out)


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def make_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def parse_active_workflows(register_file: Path) -> list[str]:
    text = register_file.read_text(encoding="utf-8")
    in_table = False
    names: list[str] = []
    for line in text.splitlines():
        if line.strip() == "## Aktive Infra-Workflows":
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("| `"):
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if cols:
            names.append(cols[0].strip("`"))
    return names


def parse_previous_fingerprints(repo: str) -> set[str]:
    comments = gh_api_json([f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments?per_page=100"])
    if not isinstance(comments, list):
        return set()
    marker = "<!-- cdb-daily-delta:"
    daily_comments = [item for item in comments if marker in (item.get("body") or "")]
    if not daily_comments:
        return set()
    daily_comments.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    latest_body = daily_comments[0].get("body") or ""
    return set(re.findall(r"`([0-9a-f]{16})`", latest_body))


def detect_missing_workflow_file(
    *,
    workflow_dir: Path,
    workflow_names: list[str],
    changed_since: datetime,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for name in workflow_names:
        file_path = workflow_dir / name
        if file_path.exists():
            continue
        key = f"missing_workflow_file:{name}"
        candidates.append(
            Candidate(
                rule_id="register_missing_workflow_file",
                title=f"Workflow listed but file missing: {name}",
                classification="follow_up_issue",
                confidence=0.96,
                affected_artifacts=["docs/runbooks/CONTROL_REGISTER.md", f".github/workflows/{name}"],
                suggested_next_step=(
                    "Open a narrow reconciliation issue to either restore the workflow file or remove/update the "
                    "CONTROL_REGISTER row."
                ),
                evidence=(
                    f"{name} is listed as active in CONTROL_REGISTER but file is missing from .github/workflows/. "
                    f"This remains a direct daily drift candidate after {changed_since.isoformat()}."
                ),
                fingerprint=make_fingerprint(key),
                issue_title=f"Reconcile missing workflow file for {name}",
                issue_labels=["scope:ci", "scope:docs", "type:docs", "agent:codex"],
            )
        )
    return candidates


def detect_recent_workflow_failures(
    *,
    repo: str,
    workflow_names: list[str],
    since: datetime,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for name in workflow_names:
        try:
            runs = gh_json(
                repo,
                [
                    "run",
                    "list",
                    "--workflow",
                    name,
                    "--limit",
                    "6",
                    "--json",
                    "databaseId,conclusion,createdAt,event",
                ],
            )
        except Exception:
            continue
        recent = []
        for item in runs:
            created = parse_iso(item.get("createdAt"))
            if created and created >= since:
                recent.append(item)
        failures = [item for item in recent if item.get("conclusion") == "failure"]
        if not failures:
            continue
        latest = sorted(failures, key=lambda x: x.get("createdAt") or "", reverse=True)[0]
        run_id = latest.get("databaseId")
        key = f"recent_failure:{name}:{run_id}"
        candidates.append(
            Candidate(
                rule_id="recent_workflow_failure_delta",
                title=f"Recent workflow failure delta: {name}",
                classification="report_only",
                confidence=0.67,
                affected_artifacts=[f".github/workflows/{name}"],
                suggested_next_step=(
                    "Keep this in the control thread unless a clear, small and currently untracked fix package is "
                    "confirmed."
                ),
                evidence=(
                    f"{name} has {len(failures)} failure run(s) since {since.isoformat()} "
                    f"(latest run id: {run_id})."
                ),
                fingerprint=make_fingerprint(key),
            )
        )
    return candidates


def detect_new_open_prs(repo: str, since: datetime) -> list[Candidate]:
    prs = gh_json(repo, ["pr", "list", "--state", "open", "--limit", "20", "--json", "number,title,createdAt,url"])
    new_prs = [pr for pr in prs if (parse_iso(pr.get("createdAt")) or datetime.min.replace(tzinfo=UTC)) >= since]
    if not new_prs:
        return []
    refs = ", ".join(f"#{pr['number']}" for pr in new_prs[:5])
    fp = make_fingerprint("new_open_prs:" + ",".join(str(pr["number"]) for pr in sorted(new_prs, key=lambda p: p["number"])))
    return [
        Candidate(
            rule_id="new_open_pr_delta",
            title="New open PRs since last daily window",
            classification="unclear",
            confidence=0.55,
            affected_artifacts=[f"PR #{pr['number']}" for pr in new_prs[:5]],
            suggested_next_step=(
                "Review whether any new PR requires control follow-up; do not open issues until a concrete, separate "
                "fix package is evidenced."
            ),
            evidence=f"{len(new_prs)} PR(s) opened since {since.isoformat()} (sample: {refs}).",
            fingerprint=fp,
        )
    ]


def existing_followup(repo: str, marker: str) -> dict[str, Any] | None:
    issues = gh_api_json([f"repos/{repo}/issues?state=all&per_page=100"])
    if not isinstance(issues, list):
        return None
    for item in sorted(issues, key=lambda x: x.get("created_at") or "", reverse=True):
        if "pull_request" in item:
            continue
        if marker in (item.get("body") or ""):
            return item
    return None


def ensure_followup_issue(repo: str, candidate: Candidate) -> dict[str, Any]:
    marker = FOLLOWUP_MARKER.format(fingerprint=candidate.fingerprint)
    found = existing_followup(repo, marker)
    if found:
        return {"action": "existing", "number": found["number"], "url": found["html_url"]}
    assert candidate.issue_title is not None
    body = (
        "## Daily Delta Triage Follow-up\n\n"
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
    args = ["gh", "issue", "create", "--repo", repo, "--title", candidate.issue_title, "--body", body]
    for label in candidate.issue_labels or []:
        args.extend(["--label", label])
    url = run(args).strip()
    number = int(url.rstrip("/").split("/")[-1])
    return {"action": "created", "number": number, "url": url}


def build_comment(day_key: str, findings: list[Candidate], issue_events: list[dict[str, Any]]) -> str:
    lines = [
        "## Daily Delta Triage",
        "",
        COMMENT_MARKER.format(day_key=day_key),
        "",
        f"- Day: `{day_key}`",
        f"- Delta findings: `{len(findings)}`",
        f"- Follow-up issues emitted: `{len(issue_events)}`",
        "",
    ]
    if not findings:
        lines.extend(
            [
                "No new repo-backed daily deltas since the previous daily triage marker.",
                "",
            ]
        )
    for item in findings:
        lines.extend(
            [
                f"### {item.title}",
                f"- Rule: `{item.rule_id}`",
                f"- Classification: `{item.classification}`",
                f"- Confidence: `{item.confidence}`",
                f"- Affected artifacts: `{', '.join(item.affected_artifacts)}`",
                f"- Suggested next step: {item.suggested_next_step}",
                f"- Fingerprint: `{item.fingerprint}`",
                f"- Evidence: {item.evidence}",
                "",
            ]
        )
    if issue_events:
        lines.append("### Follow-up issue actions")
        for event in issue_events:
            lines.append(f"- `{event['action']}`: #{event['number']} ({event['url']})")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def upsert_comment(repo: str, day_key: str, body: str) -> dict[str, Any]:
    marker = COMMENT_MARKER.format(day_key=day_key)
    comments = gh_api_json([f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments?per_page=100"])
    existing = None
    if isinstance(comments, list):
        for item in comments:
            if marker in (item.get("body") or ""):
                existing = item
                break
    payload = json.dumps({"body": body})
    if existing is None:
        created = gh_api_json(
            ["--method", "POST", f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments", "--input", "-"],
            input_text=payload,
        )
        return {"action": "created", "url": created.get("html_url")}
    updated = gh_api_json(
        ["--method", "PATCH", f"repos/{repo}/issues/comments/{existing['id']}", "--input", "-"],
        input_text=payload,
    )
    return {"action": "updated", "url": updated.get("html_url")}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Daily control delta triage")
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
    if args.max_followup_issues < 0 or args.max_followup_issues > 1:
        raise RuntimeError("max_followup_issues must be between 0 and 1 for daily slice")

    now = datetime.now(UTC)
    since = now - timedelta(hours=LOOKBACK_HOURS)
    day_key = now.date().isoformat()
    workflow_names = parse_active_workflows(args.register_file)
    previous_fingerprints = parse_previous_fingerprints(args.repo)

    candidates: list[Candidate] = []
    candidates.extend(detect_missing_workflow_file(workflow_dir=args.workflow_dir, workflow_names=workflow_names, changed_since=since))
    candidates.extend(detect_recent_workflow_failures(repo=args.repo, workflow_names=workflow_names, since=since))
    candidates.extend(detect_new_open_prs(args.repo, since))

    # Delta filter vs latest daily marker comment
    new_findings = [cand for cand in candidates if cand.fingerprint not in previous_fingerprints]

    # Deterministic order by severity then title
    order = {"follow_up_issue": 0, "unclear": 1, "report_only": 2}
    new_findings.sort(key=lambda x: (order.get(x.classification, 9), x.rule_id, x.title))

    issue_events: list[dict[str, Any]] = []
    if args.publish_mode == "publish":
        followups = [item for item in new_findings if item.classification == "follow_up_issue"][: args.max_followup_issues]
        for item in followups:
            issue_events.append(ensure_followup_issue(args.repo, item))

    summary = build_comment(day_key, new_findings, issue_events)
    comment_event = None
    if args.publish_mode == "publish":
        comment_event = upsert_comment(args.repo, day_key, summary)

    result = {
        "repo": args.repo,
        "day_key": day_key,
        "publish_mode": args.publish_mode,
        "lookback_hours": LOOKBACK_HOURS,
        "candidate_count": len(candidates),
        "delta_count": len(new_findings),
        "findings": [asdict(item) for item in new_findings],
        "issue_events": issue_events,
        "control_comment": comment_event,
    }
    args.result_file.parent.mkdir(parents=True, exist_ok=True)
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    args.result_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.summary_file.write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
