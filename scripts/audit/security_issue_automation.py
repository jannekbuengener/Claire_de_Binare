#!/usr/bin/env python3
"""Create GitHub issues from security alert issue candidates.

Read-only candidate analysis is delegated to security_alert_issue_candidates.
This script handles the GitHub write path: dedupe check + issue creation.

Design invariants:
- ``--live-mode`` must be passed explicitly; dry-run is the default.
- Dedupe: checks existing issues via GitHub GraphQL search for the dedupe
  marker before creating any issue.  A failed dedupe lookup is treated as a
  per-candidate partial failure (fail-closed — skip creation, exit 2).
- Fingerprints are validated as 16-char hex before use in GraphQL queries.
- secret_scanning: never processed (filtered in the candidates layer).
- No auto-close.  No alert dismissals.  No LR derivation.

Exit codes:
  0  ok       — all candidates processed (created or skipped)
  1  error    — input error or fatal configuration problem
  2  partial  — one or more issue creates or dedupe lookups failed
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Import sibling candidates module (robust regardless of invocation path)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from audit.security_alert_issue_candidates import (  # noqa: E402
    SecurityAlertIssueCandidatesError,
    build_candidates,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Only candidates in the "high" severity band (covers critical / high / error)
# are candidates for automated issue creation.
AUTOMATION_SEVERITY_BANDS: frozenset[str] = frozenset({"high"})
MAX_NEW_ISSUES_PER_RUN = 10
_SEVERITY_PRIORITY: dict[str, int] = {"critical": 0, "high": 1, "error": 2}

# Fingerprints are 16-char lowercase hex produced by build_fingerprint().
_FINGERPRINT_RE: re.Pattern[str] = re.compile(r"^[0-9a-f]{16}$")

CheckDedupeFn = Callable[..., bool]
CreateIssueFn = Callable[..., dict[str, Any] | None]


# ---------------------------------------------------------------------------
# GitHub helpers (real implementations; injected in tests)
# ---------------------------------------------------------------------------


def _validate_fingerprint(fingerprint: str) -> str:
    """Return fingerprint if it matches the expected hex format, raise ValueError otherwise."""
    if not _FINGERPRINT_RE.match(fingerprint):
        raise ValueError(f"Invalid fingerprint format: {fingerprint!r}")
    return fingerprint


def gh_check_dedupe(*, fingerprint: str, repo: str) -> bool:
    """Return True if an issue containing the dedupe marker already exists.

    Uses GitHub GraphQL body search.  Returns None-like errors as a
    ``ValueError`` so callers can distinguish "not found" (False) from
    "lookup failed" (raises).
    """
    _validate_fingerprint(fingerprint)
    marker_fragment = f"cdb-security-alert-group:{fingerprint}"
    query_string = f'repo:{repo} is:issue "{marker_fragment}" in:body'
    graphql = "query($q:String!){" "search(type:ISSUE,query:$q,first:5){" "issueCount}}"
    result = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={graphql}",
            "-F",
            f"q={query_string}",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh graphql dedupe check failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
        count = int(data["data"]["search"]["issueCount"])
        return count > 0
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Unexpected gh graphql response: {exc}") from exc


def _render_issue_body(candidate: dict[str, Any]) -> str:
    """Render a safe, bounded issue body from candidate ``body_safe_fields``."""
    fields = candidate["body_safe_fields"]
    refs_line = " | ".join(candidate.get("references", []))
    labels_hint = ", ".join(f"`{lbl}`" for lbl in candidate.get("suggested_labels", []))

    lines: list[str] = [
        candidate["dedupe_marker"],
        "",
        f"## Security Alert: {fields.get('severity_band', 'unknown').upper()}",
        "",
        f"**Source:** `{fields.get('source', 'unknown')}`",
        f"**Severity:** `{fields.get('severity', 'unknown')}` (band: `{fields.get('severity_band', 'unknown')}`)",
        f"**Subject:** `{fields.get('subject', 'unknown')}`",
        f"**Affected component:** `{fields.get('affected_component', 'unknown')}`",
        f"**Branch:** `{fields.get('branch', 'unknown')}`",
        "",
        f"**Fingerprint:** `{fields.get('fingerprint', 'unknown')}`",
        f"**Generated from readout:** `{fields.get('current_reference_now_utc', 'unknown')}`",
        "",
        "### Next action",
        "",
        str(
            fields.get("next_action", "Human triage and bounded remediation planning.")
        ),
        "",
        "### References",
        "",
        refs_line,
        "",
        "---",
        "",
        "> [!NOTE]",
        "> Auto-generated by Security Alert Readout workflow. Human review required.",
        "> No auto-close. No alert dismissals. No LR derivation.",
    ]
    if labels_hint:
        lines += ["", f"**Suggested labels:** {labels_hint}"]
    return "\n".join(lines)


def gh_create_issue(*, candidate: dict[str, Any], repo: str) -> dict[str, Any] | None:
    """Create a GitHub issue for the candidate via ``gh`` and return issue metadata."""
    title = candidate.get("suggested_title", "Security alert")[:220]
    body = _render_issue_body(candidate)
    labels: list[str] = candidate.get("suggested_labels", [])

    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for label in labels:
        cmd += ["--label", label]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(
            f"  gh issue create failed: {result.stderr.strip()!r}",
            file=sys.stderr,
        )
        return None

    issue_url = (
        result.stdout.strip().splitlines()[-1].strip() if result.stdout.strip() else ""
    )
    issue_number = ""
    if issue_url.rstrip("/").split("/")[-1].isdigit():
        issue_number = issue_url.rstrip("/").split("/")[-1]
    return {
        "title": title,
        "url": issue_url,
        "number": issue_number,
        "fingerprint": candidate.get("fingerprint", ""),
    }


# ---------------------------------------------------------------------------
# Core automation loop
# ---------------------------------------------------------------------------


def run_automation(
    *,
    delta_path: Path,
    repo: str,
    dry_run: bool,
    _check_dedupe: CheckDedupeFn = gh_check_dedupe,
    _create_issue: CreateIssueFn = gh_create_issue,
) -> dict[str, Any]:
    """Process candidates from the delta JSON.

    Returns:
        Summary dict with machine-readable counters and created issue refs.

    Raises:
        SecurityAlertIssueCandidatesError: on unrecoverable input error.
    """
    try:
        raw = json.loads(delta_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SecurityAlertIssueCandidatesError(
            f"Cannot read {delta_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SecurityAlertIssueCandidatesError(
            f"Invalid JSON in {delta_path}: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise SecurityAlertIssueCandidatesError("Delta JSON root must be an object")

    # Determine sources where comparison was skipped — never process these,
    # even if the delta contains residual group entries for them.
    skipped_raw = raw.get("comparison_skipped_sources") or []
    if not isinstance(skipped_raw, list):
        skipped_raw = []
    skipped_sources: frozenset[str] = frozenset(
        str(entry.get("source", "")).strip().lower()
        for entry in skipped_raw
        if isinstance(entry, dict) and entry.get("source")
    )
    if skipped_sources:
        print(f"  Ignoring comparison_skipped sources: {sorted(skipped_sources)}")

    candidates = build_candidates(raw)

    # Remove candidates from skipped sources (defense-in-depth; delta should not
    # emit them, but we guard here as well).
    skipped_comparison_sources = 0
    if skipped_sources:
        candidates = [
            c
            for c in candidates
            if c.get("source", "").strip().lower() not in skipped_sources
        ]
        skipped_comparison_sources = len(build_candidates(raw)) - len(candidates)

    # Filter to escalation-severity candidates only.
    automation_candidates = [
        c for c in candidates if c.get("severity_band") in AUTOMATION_SEVERITY_BANDS
    ]
    skipped_low = len(candidates) - len(automation_candidates)
    if skipped_low:
        print(
            f"  Skipped {skipped_low} candidate(s) below escalation threshold (severity_band not in {set(AUTOMATION_SEVERITY_BANDS)})."
        )

    def _sort_key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
        idx, cand = item
        sev = str(cand.get("severity", "")).strip().lower()
        return (
            _SEVERITY_PRIORITY.get(sev, 99),
            str(cand.get("source", "")),
            str(cand.get("subject", "")),
            str(cand.get("affected_component", "")),
            str(cand.get("branch", "")),
            idx,
        )

    ranked_candidates = [
        cand for _idx, cand in sorted(enumerate(automation_candidates), key=_sort_key)
    ]
    created = 0
    deduped = 0
    skipped = skipped_low + skipped_comparison_sources
    capped = 0
    failed = 0
    capped_titles: list[str] = []
    created_issues: list[dict[str, str]] = []
    create_slots_used = 0

    for candidate in ranked_candidates:
        fingerprint = candidate["fingerprint"]
        title = candidate.get("suggested_title", "?")

        # Dedupe check (fail-closed: skip on lookup failure).
        try:
            already_exists = _check_dedupe(fingerprint=fingerprint, repo=repo)
        except Exception as exc:  # noqa: BLE001
            print(
                f"  FAIL (dedupe error, fingerprint={fingerprint!r}): {exc}",
                file=sys.stderr,
            )
            failed += 1
            continue

        if already_exists:
            print(f"  SKIP (dedupe match): {title!r}")
            deduped += 1
            continue

        if create_slots_used >= MAX_NEW_ISSUES_PER_RUN:
            capped += 1
            capped_titles.append(str(title))
            print(f"  CAPPED (deferred): {title!r}")
            continue

        if dry_run:
            print(f"  DRY-RUN: would create issue: {title!r}")
            skipped += 1
            create_slots_used += 1
            continue

        # Live: create the issue.
        issue_meta = _create_issue(candidate=candidate, repo=repo)
        if issue_meta:
            number = str(issue_meta.get("number", "")).strip()
            url = str(issue_meta.get("url", "")).strip()
            ref = f"#{number}" if number else (url or "created")
            print(f"  CREATED: {title!r} ({ref})")
            created_issues.append(
                {
                    "number": number,
                    "url": url,
                    "title": str(issue_meta.get("title", title)),
                    "fingerprint": str(issue_meta.get("fingerprint", fingerprint)),
                }
            )
            created += 1
            create_slots_used += 1
        else:
            print(f"  FAIL (issue create): {title!r}", file=sys.stderr)
            failed += 1

    if capped:
        print(
            f"  Cap active: reached {MAX_NEW_ISSUES_PER_RUN} new issue slot(s), "
            f"deferred {capped} non-deduped candidate(s) to follow-up runs."
        )
        for capped_title in capped_titles:
            print(f"  CAPPED (summary): {capped_title!r}")

    return {
        "mode": "dry-run" if dry_run else "live",
        "cap": MAX_NEW_ISSUES_PER_RUN,
        "total_candidates": len(candidates),
        "eligible_candidates": len(automation_candidates),
        "created": created,
        "deduped": deduped,
        "skipped": skipped,
        "capped": capped,
        "failed": failed,
        "created_issues": created_issues,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create GitHub issues from security alert issue candidates. "
            "Dry-run by default; pass --live-mode to create real issues."
        ),
    )
    parser.add_argument(
        "--delta-json",
        required=True,
        metavar="PATH",
        help="Path to security_alert_delta.json",
    )
    parser.add_argument(
        "--repo",
        required=True,
        metavar="OWNER/REPO",
        help="GitHub repository (owner/repo format)",
    )
    parser.add_argument(
        "--live-mode",
        action="store_true",
        default=False,
        help="Enable live mode: create real GitHub issues (default: dry-run)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    delta_path = Path(args.delta_json)

    if not delta_path.exists():
        print(f"ERROR: delta JSON not found: {delta_path}", file=sys.stderr)
        return 1

    dry_run = not args.live_mode
    mode = "LIVE" if args.live_mode else "DRY-RUN"
    print(f"security-issue-automation: mode={mode} repo={args.repo} delta={delta_path}")

    try:
        summary = run_automation(
            delta_path=delta_path,
            repo=args.repo,
            dry_run=dry_run,
        )
    except SecurityAlertIssueCandidatesError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "Done: created={created} deduped={deduped} skipped={skipped} capped={capped} failed={failed}".format(
            created=summary["created"],
            deduped=summary["deduped"],
            skipped=summary["skipped"],
            capped=summary["capped"],
            failed=summary["failed"],
        )
    )
    print(
        "AUTOMATION_SUMMARY_JSON="
        + json.dumps(summary, sort_keys=True, separators=(",", ":"))
    )
    return 2 if int(summary["failed"]) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
