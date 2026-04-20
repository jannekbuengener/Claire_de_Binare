#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

FOLLOWUP_MARKER_TEMPLATE = "<!-- cdb-backlog-anomaly-followup:{fingerprint} -->"
ALLOWED_ANOMALY_TYPES = {
    "broken_reference",
    "missing_runbook",
    "architecture_doc_drift",
    "workflow_doc_drift",
    "missing_expected_source",
}
ESCALATION_THRESHOLDS = {
    "broken_reference": 0.86,
    "missing_expected_source": 0.9,
    "missing_runbook": 0.94,
    "architecture_doc_drift": 0.92,
    "workflow_doc_drift": 0.9,
}
MAX_FOLLOWUP_DEFAULT = 1


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


def gh_api_json(repo: str, endpoint: str) -> Any:
    out = run(["gh", "api", f"repos/{repo}/{endpoint}"])
    return json.loads(out)


def list_open_issues(repo: str) -> list[dict[str, Any]]:
    payload = gh_api_json(repo, "issues?state=open&per_page=100")
    if not isinstance(payload, list):
        return []
    issues: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if "pull_request" in item:
            continue
        issues.append(item)
    return issues


def load_artifact(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("backlog curation artifact must be a JSON object")
    issue = payload.get("issue")
    anomalies = payload.get("anomalies")
    if not isinstance(issue, dict):
        raise RuntimeError("backlog curation artifact missing issue block")
    if not isinstance(anomalies, dict):
        raise RuntimeError("backlog curation artifact missing anomalies block")
    findings = anomalies.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("backlog curation artifact anomalies.findings must be a list")
    return payload


def classify_anomaly(
    *,
    anomaly: dict[str, Any],
    artifact_sensitive: bool,
    artifact_sensitive_reasons: list[str],
) -> tuple[str, float, str]:
    anomaly_type = anomaly.get("type")
    if anomaly_type not in ALLOWED_ANOMALY_TYPES:
        return "unclear", 0.4, f"Unsupported anomaly type `{anomaly_type}`; fail-closed."

    confidence_raw = anomaly.get("confidence")
    if not isinstance(confidence_raw, (int, float)):
        return "unclear", 0.41, "Anomaly confidence is missing or invalid."
    confidence = float(confidence_raw)
    if confidence < 0 or confidence > 1:
        return "unclear", 0.42, "Anomaly confidence is out of range."

    strength = anomaly.get("strength")
    if strength not in {"strong", "medium", "weak"}:
        return "unclear", 0.43, "Anomaly strength is missing or invalid."

    if artifact_sensitive or not anomaly.get("public_issue_allowed", True):
        reason = "Sensitive/private context blocks public issue emission."
        if artifact_sensitive_reasons:
            reason = f"{reason} Reasons: {', '.join(artifact_sensitive_reasons)}"
        return "report_only", max(confidence, 0.95), reason

    if not anomaly.get("minimum_evidence_met", False):
        return "report_only", confidence, "Minimum evidence gate not met; keep report-only."

    threshold = ESCALATION_THRESHOLDS[anomaly_type]
    if (
        strength == "strong"
        and confidence >= threshold
        and anomaly.get("escalation_hint") == "follow_up_candidate"
    ):
        return (
            "follow_up_issue",
            confidence,
            "Strong typed anomaly passed threshold and escalation hint gates.",
        )

    if strength == "weak" or confidence < 0.7:
        return "report_only", confidence, "Weak/low-confidence anomaly; no follow-up issue emission."

    return "unclear", confidence, "Evidence is medium/ambiguous; keep unresolved for manual triage."


def find_existing_followup(
    *,
    open_issues: list[dict[str, Any]],
    marker: str,
    source_issue_number: int,
    anomaly_type: str,
) -> tuple[dict[str, Any] | None, str]:
    source_ref = f"source issue: #{source_issue_number}"
    typed_prefix = f"backlog anomaly: {anomaly_type}"

    for issue in sorted(open_issues, key=lambda item: item.get("created_at") or "", reverse=True):
        body = (issue.get("body") or "").lower()
        title = (issue.get("title") or "").lower()
        if marker in (issue.get("body") or ""):
            return issue, "marker_match"
        if typed_prefix in title and source_ref in body:
            return issue, "thematic_match"
    return None, "none"


def ensure_followup_issue(
    *,
    repo: str,
    source_issue: dict[str, Any],
    anomaly: dict[str, Any],
    decision_reason: str,
    open_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    anomaly_type = str(anomaly["type"])
    source_issue_number = int(source_issue["number"])
    source_issue_url = str(source_issue.get("url") or "")
    marker = FOLLOWUP_MARKER_TEMPLATE.format(fingerprint=anomaly["id"])

    existing, dedupe_mode = find_existing_followup(
        open_issues=open_issues,
        marker=marker,
        source_issue_number=source_issue_number,
        anomaly_type=anomaly_type,
    )
    if existing is not None:
        return {
            "action": "existing",
            "dedupe_mode": dedupe_mode,
            "number": existing.get("number"),
            "url": existing.get("html_url"),
        }

    affected = "\n".join(
        f"- `{path}`" for path in anomaly.get("affected_artifacts", [])
    ) or "- `n/a`"
    evidence = "\n".join(f"- {item}" for item in anomaly.get("evidence", [])) or "- n/a"
    title = f"Backlog anomaly: {anomaly_type} in issue #{source_issue_number}"
    body = (
        "## Backlog Curation Anomaly Follow-up\n\n"
        f"{marker}\n\n"
        f"- Source issue: #{source_issue_number} ({source_issue_url})\n"
        f"- Anomaly type: `{anomaly_type}`\n"
        f"- Confidence: `{anomaly.get('confidence')}`\n"
        f"- Strength: `{anomaly.get('strength')}`\n"
        f"- Escalation decision: `{decision_reason}`\n\n"
        "### Summary\n\n"
        f"{anomaly.get('summary', 'n/a')}\n\n"
        "### Affected artifacts\n\n"
        f"{affected}\n\n"
        "### Repo-backed evidence\n\n"
        f"{evidence}\n"
    )

    args = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body",
        body,
        "--label",
        "scope:ci",
        "--label",
        "scope:docs",
        "--label",
        "type:docs",
        "--label",
        "agent:codex",
    ]
    url = run(args).strip()
    number = int(url.rstrip("/").split("/")[-1])
    return {"action": "created", "dedupe_mode": "none", "number": number, "url": url}


def build_summary(result: dict[str, Any]) -> str:
    issue = result["source_issue"]
    counts = result["decision_counts"]
    lines = [
        "# CDB Backlog Anomaly Escalation",
        "",
        f"- Source issue: #{issue['number']} ({issue['url']})",
        f"- Publish mode: `{result['publish_mode']}`",
        f"- Input anomalies: `{result['anomaly_count']}`",
        (
            "- Decisions: "
            f"`follow_up_issue={counts['follow_up_issue']}`, "
            f"`report_only={counts['report_only']}`, "
            f"`unclear={counts['unclear']}`"
        ),
        f"- Follow-up issue actions: `{len(result['issue_events'])}`",
        "",
    ]
    if not result["decisions"]:
        lines.extend(
            [
                "No anomalies were present in the backlog-curation handoff artifact.",
                "",
            ]
        )
        return "\n".join(lines)

    for decision in result["decisions"]:
        lines.extend(
            [
                f"## {decision['type']} ({decision['anomaly_id']})",
                "",
                f"- Classification: `{decision['classification']}`",
                f"- Confidence: `{decision['confidence']}`",
                f"- Decision reason: {decision['decision_reason']}",
                f"- Public issue allowed: `{decision['public_issue_allowed']}`",
            ]
        )
        publication = decision.get("publication")
        if isinstance(publication, dict):
            lines.extend(
                [
                    f"- Publication action: `{publication['action']}`",
                    f"- URL: {publication.get('url', 'n/a')}",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escalate strong backlog-curation anomalies")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--artifact-file", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    parser.add_argument("--summary-file", required=True, type=Path)
    parser.add_argument("--publish-mode", choices=["dry_run", "publish"], default="dry_run")
    parser.add_argument("--max-followup-issues", type=int, default=MAX_FOLLOWUP_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_followup_issues < 0 or args.max_followup_issues > 1:
        raise RuntimeError("max_followup_issues must be between 0 and 1 for backlog anomaly escalation")

    artifact = load_artifact(args.artifact_file)
    source_issue = artifact["issue"]
    if not isinstance(source_issue.get("number"), int):
        raise RuntimeError("backlog curation artifact issue.number must be an integer")

    anomalies_block = artifact["anomalies"]
    anomaly_rows = anomalies_block.get("findings", [])
    if not isinstance(anomaly_rows, list):
        raise RuntimeError("anomalies.findings must be a list")
    anomalies = [row for row in anomaly_rows if isinstance(row, dict)]
    anomalies.sort(
        key=lambda row: (
            -(float(row.get("confidence", 0)) if isinstance(row.get("confidence"), (int, float)) else 0.0),
            str(row.get("type", "")),
            str(row.get("id", "")),
        )
    )

    artifact_sensitive = bool(anomalies_block.get("contains_sensitive_signals", False))
    sensitive_reasons = anomalies_block.get("sensitivity_reasons", [])
    if not isinstance(sensitive_reasons, list):
        sensitive_reasons = []

    open_issues: list[dict[str, Any]] = []
    if args.publish_mode == "publish" and anomalies:
        open_issues = list_open_issues(args.repo)

    decisions: list[dict[str, Any]] = []
    issue_events: list[dict[str, Any]] = []
    created_followups = 0

    for anomaly in anomalies:
        classification, confidence, decision_reason = classify_anomaly(
            anomaly=anomaly,
            artifact_sensitive=artifact_sensitive,
            artifact_sensitive_reasons=[str(reason) for reason in sensitive_reasons],
        )
        public_issue_allowed = bool(anomaly.get("public_issue_allowed", False)) and not artifact_sensitive

        decision: dict[str, Any] = {
            "anomaly_id": anomaly.get("id"),
            "type": anomaly.get("type"),
            "classification": classification,
            "confidence": round(float(confidence), 2),
            "decision_reason": decision_reason,
            "public_issue_allowed": public_issue_allowed,
        }

        if classification == "follow_up_issue" and args.publish_mode == "publish":
            if created_followups >= args.max_followup_issues:
                decision["classification"] = "report_only"
                decision["decision_reason"] = (
                    "Escalation budget exhausted; demoted to report_only to avoid issue-cascade."
                )
            else:
                publication = ensure_followup_issue(
                    repo=args.repo,
                    source_issue=source_issue,
                    anomaly=anomaly,
                    decision_reason=decision_reason,
                    open_issues=open_issues,
                )
                decision["publication"] = publication
                issue_events.append(publication)
                if publication.get("action") == "created":
                    created_followups += 1
                    open_issues.append(
                        {
                            "number": publication["number"],
                            "html_url": publication["url"],
                            "title": f"Backlog anomaly: {anomaly.get('type')}",
                            "body": FOLLOWUP_MARKER_TEMPLATE.format(
                                fingerprint=anomaly.get("id", "unknown")
                            )
                            + f"\nSource issue: #{source_issue['number']}",
                        }
                    )

        decisions.append(decision)

    counts = {"follow_up_issue": 0, "report_only": 0, "unclear": 0}
    for decision in decisions:
        label = decision["classification"]
        if label in counts:
            counts[label] += 1

    result = {
        "repo": args.repo,
        "publish_mode": args.publish_mode,
        "source_issue": {
            "number": source_issue["number"],
            "title": source_issue.get("title"),
            "url": source_issue.get("url"),
        },
        "anomaly_count": len(anomalies),
        "decision_counts": counts,
        "decisions": decisions,
        "issue_events": issue_events,
        "artifact_sensitive": artifact_sensitive,
        "sensitivity_reasons": sensitive_reasons,
    }

    args.result_file.parent.mkdir(parents=True, exist_ok=True)
    args.summary_file.parent.mkdir(parents=True, exist_ok=True)
    args.result_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.summary_file.write_text(build_summary(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - fail-closed entrypoint
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
