#!/usr/bin/env python3
"""
alert_to_issue.py — Create or update GitHub issues from critical alerts.

Usage:
    # Dry-run (default): prints what would happen, no GitHub writes
    python scripts/alert_to_issue.py \
        --component cdb_risk --severity CRITICAL \
        --title "Circuit breaker triggered" \
        --body "Details of the incident..."

    # Execute: actually create/comment on GitHub
    python scripts/alert_to_issue.py --execute \
        --component cdb_risk --severity CRITICAL \
        --title "Circuit breaker triggered" \
        --body "Details of the incident..."

    # From JSON stdin:
    echo '{"component":"cdb_risk","severity":"CRITICAL","title":"...","body":"..."}' \
        | python scripts/alert_to_issue.py --stdin

Requires: gh CLI authenticated with repo scope.
"""

import argparse
import hashlib
import json
import logging
import subprocess
import sys
from datetime import timezone

from core.utils.clock import utcnow

logger = logging.getLogger(__name__)

SEVERITY_LEVELS = ("INFO", "WARNING", "ERROR", "CRITICAL")
DEFAULT_THRESHOLD = "CRITICAL"
FINGERPRINT_MARKER = "<!-- alert-fingerprint:{fp} -->"
LABELS = ["type:operations", "pipeline:generated"]


def fingerprint(component: str, title: str) -> str:
    """Deterministic fingerprint from component + title."""
    raw = f"{component}::{title}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def severity_at_or_above(severity: str, threshold: str) -> bool:
    """Return True if severity meets or exceeds threshold."""
    try:
        return SEVERITY_LEVELS.index(severity.upper()) >= SEVERITY_LEVELS.index(
            threshold.upper()
        )
    except ValueError:
        return False


def _run_gh(
    args: list[str], input_data: str | None = None
) -> subprocess.CompletedProcess:
    """Run a gh CLI command and return the result."""
    cmd = ["gh"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=input_data,
        timeout=30,
    )


def find_existing_issue(fp: str) -> int | None:
    """Search for an open issue containing the fingerprint marker."""
    marker = FINGERPRINT_MARKER.format(fp=fp)
    result = _run_gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--search",
            f"in:body {fp}",
            "--json",
            "number,body",
            "--limit",
            "20",
        ]
    )
    if result.returncode != 0:
        logger.warning("gh issue list failed: %s", result.stderr.strip())
        return None
    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    for issue in issues:
        if marker in issue.get("body", ""):
            return issue["number"]
    return None


def create_issue(title: str, body: str, labels: list[str]) -> int | None:
    """Create a new GitHub issue. Returns issue number or None."""
    cmd = ["issue", "create", "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])
    result = _run_gh(cmd)
    if result.returncode != 0:
        logger.error("gh issue create failed: %s", result.stderr.strip())
        return None
    # gh issue create prints the URL; extract number from it
    url = result.stdout.strip()
    try:
        return int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        logger.warning("Could not parse issue number from: %s", url)
        return None


def comment_on_issue(issue_number: int, body: str) -> bool:
    """Add a comment to an existing issue."""
    result = _run_gh(["issue", "comment", str(issue_number), "--body", body])
    if result.returncode != 0:
        logger.error("gh issue comment failed: %s", result.stderr.strip())
        return False
    return True


def build_issue_body(
    component: str,
    severity: str,
    body: str,
    fp: str,
    environment: str = "local",
) -> str:
    """Build the GitHub issue body with operational context."""
    now = utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    marker = FINGERPRINT_MARKER.format(fp=fp)
    return (
        f"## Alert: {severity}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| Component | `{component}` |\n"
        f"| Severity | **{severity}** |\n"
        f"| Environment | {environment} |\n"
        f"| First seen | {now} |\n"
        f"| Fingerprint | `{fp}` |\n\n"
        f"## Details\n\n{body}\n\n"
        f"---\n"
        f"*Auto-created by `scripts/alert_to_issue.py`*\n\n"
        f"{marker}\n"
    )


def build_comment_body(severity: str, body: str) -> str:
    """Build a comment body for repeat occurrences."""
    now = utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"## Repeat alert — {severity}\n\n"
        f"**Time:** {now}\n\n"
        f"{body}\n\n"
        f"---\n"
        f"*Auto-comment by `scripts/alert_to_issue.py`*\n"
    )


def process_alert(
    component: str,
    severity: str,
    title: str,
    body: str,
    threshold: str = DEFAULT_THRESHOLD,
    execute: bool = False,
    environment: str = "local",
) -> dict:
    """
    Process an alert: create or update a GitHub issue.

    Returns a result dict with action taken and details.
    """
    result = {
        "component": component,
        "severity": severity,
        "title": title,
        "threshold": threshold,
        "execute": execute,
        "action": "none",
    }

    if not severity_at_or_above(severity, threshold):
        result["action"] = "skipped"
        result["reason"] = f"Severity {severity} below threshold {threshold}"
        return result

    fp = fingerprint(component, title)
    result["fingerprint"] = fp

    issue_title = f"[ALERT][{severity}] {component}: {title}"

    # Always check for existing issue — dry-run must mirror execute logic
    existing = find_existing_issue(fp)
    result["existing_issue"] = existing

    if not execute:
        result["action"] = "dry_run"
        result["would_create"] = existing is None
        result["would_comment"] = existing is not None
        result["issue_title"] = issue_title
        return result

    if existing:
        comment = build_comment_body(severity, body)
        success = comment_on_issue(existing, comment)
        result["action"] = "commented" if success else "comment_failed"
        result["issue_number"] = existing
    else:
        issue_body = build_issue_body(component, severity, body, fp, environment)
        number = create_issue(issue_title, issue_body, LABELS)
        result["action"] = "created" if number else "create_failed"
        result["issue_number"] = number

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Create or update GitHub issues from critical alerts."
    )
    parser.add_argument(
        "--component",
        required="--stdin" not in sys.argv,
        help="Service/component name (e.g. cdb_risk)",
    )
    parser.add_argument(
        "--severity",
        required="--stdin" not in sys.argv,
        choices=SEVERITY_LEVELS,
        help="Alert severity",
    )
    parser.add_argument(
        "--title", required="--stdin" not in sys.argv, help="Alert title/subject"
    )
    parser.add_argument("--body", default="", help="Alert details")
    parser.add_argument(
        "--threshold",
        default=DEFAULT_THRESHOLD,
        choices=SEVERITY_LEVELS,
        help=f"Minimum severity for issue creation (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--environment", default="local", help="Environment name (default: local)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create/comment on GitHub (default: dry-run)",
    )
    parser.add_argument(
        "--stdin", action="store_true", help="Read alert payload as JSON from stdin"
    )
    args = parser.parse_args()

    if args.stdin:
        payload = json.load(sys.stdin)
        component = payload["component"]
        severity = payload["severity"]
        title = payload["title"]
        body = payload.get("body", "")
        threshold = payload.get("threshold", args.threshold)
        environment = payload.get("environment", args.environment)
    else:
        component = args.component
        severity = args.severity
        title = args.title
        body = args.body
        threshold = args.threshold
        environment = args.environment

    result = process_alert(
        component=component,
        severity=severity,
        title=title,
        body=body,
        threshold=threshold,
        execute=args.execute,
        environment=environment,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["action"] not in ("create_failed", "comment_failed") else 1)


if __name__ == "__main__":
    main()
