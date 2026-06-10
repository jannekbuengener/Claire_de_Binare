from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

ISSUE_CAMPAIGN = 3095
ISSUE_REFERENCE_WINDOW = 3087
ISSUE_UMBRELLA = 3102

STATE_CHAIN_FOUND = "CHAIN_FOUND"
STATE_TIMEOUT_NO_CHAIN = "TIMEOUT_NO_CHAIN"
STATE_INTERRUPTED = "INTERRUPTED"
STATE_BLOCKED_RUNTIME = "BLOCKED_RUNTIME"
STATE_BLOCKED_DB_READONLY = "BLOCKED_DB_READONLY"
STATE_BLOCKED_GOVERNANCE = "BLOCKED_GOVERNANCE"
STATE_EVIDENCE_MERGED = "EVIDENCE_MERGED"

TERMINAL_STATES = {
    STATE_CHAIN_FOUND,
    STATE_TIMEOUT_NO_CHAIN,
    STATE_INTERRUPTED,
    STATE_BLOCKED_RUNTIME,
    STATE_BLOCKED_DB_READONLY,
    STATE_BLOCKED_GOVERNANCE,
    STATE_EVIDENCE_MERGED,
}


def _format_probe_table(probe_statuses: dict[str, str]) -> str:
    if not probe_statuses:
        return "*No probe data*"
    lines = ["| Probe | Status |", "|-------|--------|"]
    for name in sorted(probe_statuses):
        lines.append(f"| {name} | {probe_statuses[name]} |")
    return "\n".join(lines)


def _should_comment_3087(state: str, campaign_failure_count: int) -> bool:
    if state == STATE_CHAIN_FOUND:
        return True
    if state == STATE_TIMEOUT_NO_CHAIN and campaign_failure_count >= 3:
        return True
    return False


def _git_branch_name(campaign_id: str, state: str) -> str:
    safe_id = campaign_id.replace(" ", "_").replace("/", "_")
    safe_state = state.lower().replace(" ", "_").replace("/", "_")
    return f"evidence/arvp-{safe_id}-{safe_state}"


# ---------------------------------------------------------------------------
# Template renderers (pure functions, no side effects)
# ---------------------------------------------------------------------------


def render_chain_found(entry: dict[str, Any], manifest: dict[str, Any]) -> str:
    details = entry.get("chain_details", {})
    campaign_id = entry.get("campaign_id", "unknown")
    observed = entry.get("observed_at_utc", "unknown")
    event_count = details.get("event_count", "?")
    first_ts = details.get("first_event_ts", "?")
    last_ts = details.get("last_event_ts", "?")
    event_ids = details.get("event_ids", [])
    ids_str = ", ".join(str(i) for i in (event_ids or [])) if event_ids else "none"
    evidence_doc = manifest.get("evidence_doc", "?")
    evidence_log = manifest.get("evidence_log_jsonl", "?")

    return (
        f"## Chain Found — Campaign {campaign_id}\n\n"
        f"**State:** CHAIN_FOUND\n"
        f"**Observed:** {observed}\n"
        f"**Event count:** {event_count}\n"
        f"**First event:** {first_ts}\n"
        f"**Last event:** {last_ts}\n"
        f"**Event IDs:** {ids_str}\n\n"
        f"**Evidence doc:** {evidence_doc}\n"
        f"**Evidence log:** {evidence_log}\n\n"
        f"---\n"
        f"*This is paper-only evidence (MOCK_TRADING=true). LR remains NO-GO.*"
    )


def render_timeout_no_chain(entry: dict[str, Any], manifest: dict[str, Any]) -> str:
    campaign_id = entry.get("campaign_id", "unknown")
    observed = entry.get("observed_at_utc", "unknown")
    event_count = entry.get("event_count_since_start", "?")
    probe_statuses = entry.get("probe_statuses", {})

    return (
        f"## Timeout — No Chain Detected\n\n"
        f"**Campaign:** {campaign_id}\n"
        f"**State:** TIMEOUT_NO_CHAIN\n"
        f"**Observed:** {observed}\n"
        f"**Event count:** {event_count}\n\n"
        f"**Probe Statuses:**\n"
        f"{_format_probe_table(probe_statuses)}\n\n"
        f"**Classification:** campaign_timeout_record (counts as failure)\n\n"
        f"---\n"
        f"*LR remains NO-GO.*"
    )


def render_interrupted(entry: dict[str, Any], manifest: dict[str, Any]) -> str:
    campaign_id = entry.get("campaign_id", "unknown")
    observed = entry.get("observed_at_utc", "unknown")
    event_count = entry.get("event_count_since_start", "?")
    probe_statuses = entry.get("probe_statuses", {})

    return (
        f"## Campaign Interrupted\n\n"
        f"**Campaign:** {campaign_id}\n"
        f"**State:** INTERRUPTED\n"
        f"**Observed:** {observed}\n"
        f"**Event count:** {event_count}\n\n"
        f"**Probe Statuses:**\n"
        f"{_format_probe_table(probe_statuses)}\n\n"
        f"**Classification:** interruption_record (does NOT count as failure)\n\n"
        f"---\n"
        f"*LR remains NO-GO.*"
    )


def render_blocked(entry: dict[str, Any], manifest: dict[str, Any]) -> str:
    campaign_id = entry.get("campaign_id", "unknown")
    state = entry.get("state", "BLOCKED_UNKNOWN")
    observed = entry.get("observed_at_utc", "unknown")
    probe_statuses = entry.get("probe_statuses", {})

    blocked_probes = [k for k, v in probe_statuses.items() if v == "blocked"]
    label = state.replace("BLOCKED_", "").replace("_", " ").title()

    return (
        f"## Campaign Blocked — {label}\n\n"
        f"**Campaign:** {campaign_id}\n"
        f"**State:** {state}\n"
        f"**Observed:** {observed}\n"
        f"**Blocking probe(s):** "
        f"{', '.join(blocked_probes) if blocked_probes else '?'}\n\n"
        f"**Probe Statuses:**\n"
        f"{_format_probe_table(probe_statuses)}\n\n"
        f"---\n"
        f"*LR remains NO-GO.*"
    )


def render_merged(entry: dict[str, Any], manifest: dict[str, Any]) -> str:
    campaign_id = entry.get("campaign_id", "unknown")
    pr_url = entry.get("pr_url", "?")
    merge_sha = entry.get("merge_sha", "?")
    evidence_doc = manifest.get("evidence_doc", "?")

    return (
        f"## Evidence PR Merged — {campaign_id}\n\n"
        f"**PR:** {pr_url}\n"
        f"**Merge SHA:** {merge_sha}\n"
        f"**Evidence doc:** {evidence_doc}\n\n"
        f"---\n"
        f"*LR remains NO-GO. No Echtgeld claim.*"
    )


_RENDERERS: dict[str, Any] = {
    STATE_CHAIN_FOUND: render_chain_found,
    STATE_TIMEOUT_NO_CHAIN: render_timeout_no_chain,
    STATE_INTERRUPTED: render_interrupted,
    STATE_BLOCKED_RUNTIME: render_blocked,
    STATE_BLOCKED_DB_READONLY: render_blocked,
    STATE_BLOCKED_GOVERNANCE: render_blocked,
    STATE_EVIDENCE_MERGED: render_merged,
}


def render_body(state: str, entry: dict[str, Any], manifest: dict[str, Any]) -> str:
    renderer = _RENDERERS.get(state)
    if renderer is None:
        raise ValueError(f"unknown state for template: {state}")
    return renderer(entry, manifest)


def pr_body(
    campaign_id: str,
    state: str,
    entry: dict[str, Any],
    evidence_doc: str,
    evidence_log: str,
) -> str:
    observed = entry.get("observed_at_utc", "?")
    chain_details = entry.get("chain_details", {})
    event_count = chain_details.get("event_count", "?") if chain_details else "?"

    return (
        f"## {campaign_id} — {state}\n\n"
        f"**Observed:** {observed}\n"
        f"**Event count:** {event_count}\n\n"
        f"**Evidence doc:** `{evidence_doc}`\n"
        f"**Evidence log:** `{evidence_log}`\n\n"
        f"**Parent:** #3102\n"
        f"**Related:** #3095 #3087\n\n"
        f"---\n"
        f"*This is paper-only evidence (MOCK_TRADING=true). LR remains NO-GO.*\n"
        f"*No Echtgeld claim. No live trading authorization.*"
    )


# ---------------------------------------------------------------------------
# GitHubReporter
# ---------------------------------------------------------------------------


class GitHubReporter:
    def __init__(
        self,
        manifest: dict[str, Any],
        github_write: bool = False,
        create_pr: bool = False,
        gh_executable: str = "gh",
    ):
        if create_pr and not github_write:
            raise ValueError("--create-pr requires --github-write")

        self._manifest = manifest
        self._github_write = github_write
        self._create_pr = create_pr
        self._gh = gh_executable

        reporting = manifest.get("github_reporting", {})
        self._post_3095 = reporting.get("post_on_issue_3095", True)
        self._post_3087 = reporting.get("post_on_issue_3087", False)
        self._post_3102 = reporting.get("post_on_issue_3102", False)
        self._pr_on_chain = reporting.get("pr_create_on_chain_found", True)

    def report_terminal(
        self, entry: dict[str, Any], campaign_failure_count: int = 0
    ) -> list[dict[str, Any]]:
        state = entry.get("state", "")
        if state not in TERMINAL_STATES:
            raise ValueError(f"non-terminal state: {state}")

        body = render_body(state, entry, self._manifest)
        results: list[dict[str, Any]] = []

        targets = self._resolve_targets(state, campaign_failure_count)
        for issue in targets:
            results.append(self._post_comment(issue, body))

        if state == STATE_CHAIN_FOUND and self._pr_on_chain:
            results.append(self._maybe_create_pr(entry))

        return results

    def _resolve_targets(self, state: str, campaign_failure_count: int) -> list[int]:
        targets: list[int] = []
        if self._post_3095:
            targets.append(ISSUE_CAMPAIGN)
        if self._post_3087 and _should_comment_3087(state, campaign_failure_count):
            targets.append(ISSUE_REFERENCE_WINDOW)
        if self._post_3102:
            targets.append(ISSUE_UMBRELLA)
        return targets

    def _post_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        if not self._github_write:
            return {
                "action": "dry_run_comment",
                "issue": issue_number,
                "body": body,
            }

        cmd = [self._gh, "issue", "comment", str(issue_number), "--body", body]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {
                    "action": "comment_failed",
                    "issue": issue_number,
                    "error": result.stderr.strip(),
                }
            return {
                "action": "comment_posted",
                "issue": issue_number,
                "url": result.stdout.strip(),
            }
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return {
                "action": "comment_failed",
                "issue": issue_number,
                "error": str(exc),
            }

    def _maybe_create_pr(self, entry: dict[str, Any]) -> dict[str, Any]:
        campaign_id = entry.get("campaign_id", "unknown")
        state = entry.get("state", "unknown")
        branch = _git_branch_name(campaign_id, state)

        if not self._create_pr:
            return {
                "action": "dry_run_pr",
                "branch": branch,
                "body": self._build_pr_body(entry),
            }

        return self._execute_create_pr(entry, campaign_id, state, branch)

    def _build_pr_body(self, entry: dict[str, Any]) -> str:
        campaign_id = entry.get("campaign_id", "unknown")
        state = entry.get("state", "unknown")
        evidence_doc = self._manifest.get("evidence_doc", "?")
        evidence_log = self._manifest.get("evidence_log_jsonl", "?")
        return pr_body(campaign_id, state, entry, evidence_doc, evidence_log)

    def _execute_create_pr(
        self, entry: dict[str, Any], campaign_id: str, state: str, branch: str
    ) -> dict[str, Any]:
        evidence_doc = self._manifest.get("evidence_doc", "")
        evidence_log = self._manifest.get("evidence_log_jsonl", "")
        pr_title = f"[ARVP][EVIDENCE] {campaign_id} — {state}"
        pr_body_content = self._build_pr_body(entry)

        try:
            exists = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if exists.returncode == 0:
                return {
                    "action": "pr_skipped",
                    "branch": branch,
                    "error": f"branch already exists: {branch}",
                }

            subprocess.run(
                ["git", "checkout", "-b", branch],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            paths = [p for p in [evidence_doc, evidence_log] if p and os.path.isfile(p)]
            for p in paths:
                subprocess.run(
                    ["git", "add", p],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )

            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"docs/evidence: add {campaign_id} {state} evidence",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            subprocess.run(
                ["git", "push", "-u", "origin", branch],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            pr_cmd = [
                self._gh,
                "pr",
                "create",
                "--title",
                pr_title,
                "--body",
                pr_body_content,
                "--base",
                "main",
                "--head",
                branch,
                "--draft",
                "--label",
                "ARVP,evidence",
            ]
            pr_result = subprocess.run(
                pr_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if pr_result.returncode != 0:
                subprocess.run(
                    ["git", "checkout", "main"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return {
                    "action": "pr_create_failed",
                    "branch": branch,
                    "error": pr_result.stderr.strip(),
                }

            subprocess.run(
                ["git", "checkout", "main"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return {
                "action": "pr_created",
                "branch": branch,
                "url": pr_result.stdout.strip(),
            }

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
        ) as exc:
            subprocess.run(
                ["git", "checkout", "main"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "action": "pr_create_failed",
                "branch": branch,
                "error": str(exc),
            }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "ARVP GitHub Reporter — controlled GitHub reporting "
            "for campaign supervisor results"
        )
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to campaign manifest (YAML or JSON)",
    )
    parser.add_argument(
        "--cycle-entry",
        default=None,
        help="JSON string of the supervisor cycle entry",
    )
    parser.add_argument(
        "--cycle-entry-file",
        default=None,
        help="Path to JSON file containing the cycle entry",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Override terminal state (used without cycle entry for simple reports)",
    )
    parser.add_argument(
        "--campaign-failure-count",
        type=int,
        default=0,
        help="Number of consecutive campaign failures (for #3087 escalation)",
    )
    parser.add_argument(
        "--github-write",
        action="store_true",
        help="Enable live GitHub issue comments via gh CLI",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create evidence PR (implies --github-write)",
    )
    parser.add_argument(
        "--gh-executable",
        default="gh",
        help="Path to gh executable (default: gh)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def load_entry(args: argparse.Namespace) -> dict[str, Any]:
    if args.cycle_entry:
        return json.loads(args.cycle_entry)
    if args.cycle_entry_file:
        with open(args.cycle_entry_file, encoding="utf-8") as f:
            return json.load(f)
    if args.state:
        return {"state": args.state, "observed_at_utc": "unknown"}
    raise ValueError("one of --cycle-entry, --cycle-entry-file, or --state is required")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    from tools.arvp_campaign_supervisor import load_manifest

    manifest = load_manifest(args.manifest)
    entry = load_entry(args)

    reporter = GitHubReporter(
        manifest=manifest,
        github_write=args.github_write,
        create_pr=args.create_pr,
        gh_executable=args.gh_executable,
    )

    results = reporter.report_terminal(
        entry, campaign_failure_count=args.campaign_failure_count
    )

    for result in results:
        print(json.dumps(result, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
