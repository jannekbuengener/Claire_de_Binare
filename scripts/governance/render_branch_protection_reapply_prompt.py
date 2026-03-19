#!/usr/bin/env python3
"""
Render a deterministic Playwright MCP operator prompt for branch protection re-apply.

This script is read-only. It never calls GitHub APIs and never mutates settings.
It turns the saved baseline/apply payload files into a human-reviewed Playwright
MCP execution brief for the classic branch protection UI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
DEFAULT_BRANCH = "main"
DEFAULT_BASELINE = Path("reports/BRANCH_PROTECTION_BASELINE_main.json")
DEFAULT_APPLY_PAYLOAD = Path("reports/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json")
DEFAULT_OUTPUT = Path("reports/BRANCH_PROTECTION_PLAYWRIGHT_REAPPLY_main.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a Playwright MCP operator prompt from saved branch protection files."
        )
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo target")
    parser.add_argument(
        "--branch", default=DEFAULT_BRANCH, help="protected branch name"
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="saved branch protection baseline JSON",
    )
    parser.add_argument(
        "--apply-payload",
        default=str(DEFAULT_APPLY_PAYLOAD),
        help="saved branch protection apply payload JSON",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT),
        help="markdown output path for the Playwright MCP prompt",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the rendered prompt to stdout in addition to writing the file",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def on_off(value: Any) -> str:
    return "ON" if bool(value) else "OFF"


def format_named_items(items: Any, key: str) -> str:
    if not items:
        return "none"
    values: list[str] = []
    for item in items:
        if isinstance(item, str):
            values.append(item)
            continue
        if isinstance(item, dict):
            candidate = item.get(key) or item.get("name") or item.get("slug")
            if isinstance(candidate, str) and candidate:
                values.append(candidate)
    return ", ".join(sorted(dict.fromkeys(values))) if values else "none"


def format_allowances(data: Any) -> str:
    if not isinstance(data, dict):
        return "none"
    users = format_named_items(data.get("users"), "login")
    teams = format_named_items(data.get("teams"), "slug")
    apps = format_named_items(data.get("apps"), "slug")
    if users == teams == apps == "none":
        return "none"
    return f"users={users}; teams={teams}; apps={apps}"


def format_required_checks(required_status_checks: Any) -> list[str]:
    if not isinstance(required_status_checks, dict):
        return ["- none"]

    checks = required_status_checks.get("checks")
    if isinstance(checks, list) and checks:
        lines: list[str] = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            context = check.get("context")
            if not isinstance(context, str) or not context:
                continue
            app_id = check.get("app_id")
            suffix = f" (app_id={app_id})" if app_id is not None else ""
            lines.append(f"- {context}{suffix}")
        return lines or ["- none"]

    contexts = required_status_checks.get("contexts")
    if isinstance(contexts, list) and contexts:
        return [f"- {context}" for context in contexts if isinstance(context, str)]
    return ["- none"]


def render_document(
    *,
    repo: str,
    branch: str,
    baseline_path: Path,
    apply_payload_path: Path,
    baseline: Any,
    apply_payload: Any,
) -> str:
    if not isinstance(baseline, dict):
        raise ValueError("baseline JSON must be an object")
    if not isinstance(apply_payload, dict):
        raise ValueError("apply payload JSON must be an object")

    reviews = apply_payload.get("required_pull_request_reviews") or {}
    status_checks = apply_payload.get("required_status_checks") or {}
    required_signatures = (baseline.get("required_signatures") or {}).get(
        "enabled", False
    )
    dismissals = reviews.get("dismissal_restrictions")
    bypasses = reviews.get("bypass_pull_request_allowances")
    restrictions = apply_payload.get("restrictions")
    checks_lines = "\n".join(format_required_checks(status_checks))
    branch_settings_url = f"https://github.com/{repo}/settings/branches"
    classic_rule_hint = f"{branch_settings_url}"
    ruleset_url = f"https://github.com/{repo}/rules"

    return f"""# Branch Protection Re-Apply Prompt ({branch})

Repo: `{repo}`  
Branch: `{branch}`  
Classic branch settings URL: `{classic_rule_hint}`  
Ruleset URL (do not edit in this flow): `{ruleset_url}`

## Source of Truth

- Baseline snapshot: `{baseline_path.as_posix()}` (sha256 `{sha256_path(baseline_path)}`)
- Apply payload: `{apply_payload_path.as_posix()}` (sha256 `{sha256_path(apply_payload_path)}`)
- Branch protection scope for this flow: classic `branches/{branch}/protection`
- Rulesets are explicitly out of scope for this re-apply path

## Safety Contract

- This prompt is maintainer-run and human-reviewed; it is not auto-applied from CI.
- Use Playwright MCP only against the classic branch protection UI for `{branch}`.
- Before clicking save, produce a preview grouped as `already matching` vs `change needed`.
- If GitHub opens a ruleset page, a materially different UI, or a field that cannot be mapped exactly, stop and report instead of guessing.
- Do not touch merge methods, repository rulesets, team restrictions, or unrelated repo settings.
- After save, reopen the rule, verify every field below, and capture before/after screenshots.

## Expected Classic Branch Protection State

- Include administrators: `{on_off(apply_payload.get("enforce_admins"))}`
- Require a pull request before merging: `{on_off(reviews)}`
- Required approving reviews: `{reviews.get("required_approving_review_count", 0)}`
- Dismiss stale reviews: `{on_off(reviews.get("dismiss_stale_reviews"))}`
- Require review from code owners: `{on_off(reviews.get("require_code_owner_reviews"))}`
- Require approval of the most recent reviewable push: `{on_off(reviews.get("require_last_push_approval"))}`
- Dismissal restrictions: `{format_allowances(dismissals)}`
- Bypass pull request requirements: `{format_allowances(bypasses)}`
- Require status checks to pass before merging: `{on_off(status_checks)}`
- Require branches to be up to date before merging: `{on_off(status_checks.get("strict"))}`
- Required status checks:
{checks_lines}
- Require conversation resolution before merging: `{on_off(apply_payload.get("required_conversation_resolution"))}`
- Require signed commits: `{on_off(required_signatures)}`
- Require linear history: `{on_off(apply_payload.get("required_linear_history"))}`
- Allow force pushes: `{on_off(apply_payload.get("allow_force_pushes"))}`
- Allow deletions: `{on_off(apply_payload.get("allow_deletions"))}`
- Block branch creations: `{on_off(apply_payload.get("block_creations"))}`
- Lock branch: `{on_off(apply_payload.get("lock_branch"))}`
- Allow fork syncing: `{on_off(apply_payload.get("allow_fork_syncing"))}`
- Restrict who can push: `{format_allowances(restrictions)}`

## Playwright MCP Task

Use Playwright MCP to do exactly this:

1. Open `{branch_settings_url}`.
2. Authenticate as a maintainer if GitHub asks for login.
3. Open the classic branch protection rule for exact branch name `{branch}`.
   If no classic rule exists yet, create one for exact branch name `{branch}`.
4. Read the current values for every field in `Expected Classic Branch Protection State`.
5. Present a preview before any save:
   - `already matching`
   - `change needed`
   - `cannot map exactly` (if any; then stop)
6. Apply only the listed values. Do not improvise or change unrelated settings.
7. Save the rule.
8. Re-open the same rule and verify the values again against this document.
9. Capture screenshots of the rule before save and after verification.
10. Stop and report the outcome.

## Manual API Fallback

If the classic GitHub UI path is unavailable or cannot represent the saved state faithfully, stop and use the existing maintainer-run API path instead:

```bash
gh api repos/{repo}/branches/{branch}/protection > reports/BRANCH_PROTECTION_CURRENT_{branch}.json
gh api --method PUT repos/{repo}/branches/{branch}/protection --input {apply_payload_path.as_posix()}
```
"""


def main() -> int:
    args = parse_args()
    baseline_path = Path(args.baseline)
    apply_payload_path = Path(args.apply_payload)
    out_path = Path(args.out)

    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline file not found: {baseline_path.as_posix()}")
    if not apply_payload_path.exists():
        raise FileNotFoundError(
            f"Apply payload file not found: {apply_payload_path.as_posix()}"
        )

    baseline = load_json(baseline_path)
    apply_payload = load_json(apply_payload_path)
    document = render_document(
        repo=args.repo,
        branch=args.branch,
        baseline_path=baseline_path,
        apply_payload_path=apply_payload_path,
        baseline=baseline,
        apply_payload=apply_payload,
    )

    out_path.write_text(document, encoding="utf-8")
    print(f"Wrote Playwright re-apply prompt: {out_path.as_posix()}")
    if args.stdout:
        print(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
