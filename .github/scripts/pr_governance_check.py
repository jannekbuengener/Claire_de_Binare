#!/usr/bin/env python3
"""
PR Governance Check - Blocking checks for governance violations
Part of Issue #144 MVP (Non-blocking Phase 1)
Architecture: .github/ARCHITECTURE_ISSUE_144.md
"""

import os
import sys
import json
import yaml
import requests
from typing import Dict, List, Optional, Tuple

# GitHub API setup
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["REPO"]
PR_NUMBER = os.environ["PR_NUMBER"]
PR_TITLE = os.environ.get("PR_TITLE", "")
PR_BODY = os.environ.get("PR_BODY", "")
PR_IS_DRAFT = os.environ.get("PR_IS_DRAFT", "false").lower() == "true"
CONFIG_PATH = os.environ.get("CONFIG_PATH", ".github/pr-labels.yml")

OWNER, NAME = REPO.split("/")
BASE_URL = f"https://api.github.com/repos/{OWNER}/{NAME}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def gh(method: str, path: str, data: Optional[Dict] = None) -> requests.Response:
    """Make GitHub API request."""
    url = f"{BASE_URL}{path}"
    resp = requests.request(method, url, headers=HEADERS, json=data, timeout=30)
    resp.raise_for_status()
    return resp


def load_config() -> Dict:
    """Load configuration from pr-labels.yml."""
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {CONFIG_PATH}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Invalid YAML in config: {e}")
        sys.exit(1)


def get_pr_labels() -> List[str]:
    """Get current labels on the PR."""
    resp = gh("GET", f"/issues/{PR_NUMBER}")
    return [label["name"] for label in resp.json().get("labels", [])]


def check_governance_status(labels: List[str], config: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if PR passes governance check.

    Returns:
        (passed, reason) - True if passed, False with reason if failed
    """
    governance_label = config.get("governance", {}).get("violation_label", "governance:review-required")

    if governance_label not in labels:
        return True, None

    # MVP Phase 1: Non-blocking, just warn
    return True, f"⚠️ Governance violation detected (label: {governance_label}). Review required."


def check_template_compliance(pr_body: str, config: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if PR template is complete.

    Returns:
        (passed, reason) - True if passed, False with reason if failed
    """
    enforcement = config.get("enforcement", {})
    if not enforcement.get("enabled", False):
        return True, None

    template_blocking = enforcement.get("template_blocking", False)
    required_sections = enforcement.get("required_sections", [])

    if not required_sections:
        return True, None

    missing = []
    for section in required_sections:
        if section not in pr_body:
            missing.append(section)

    if missing:
        reason = f"❌ Missing required PR template sections: {', '.join(missing)}"
        if template_blocking:
            return False, reason
        else:
            return True, f"⚠️ {reason} (non-blocking in MVP)"

    return True, None


def check_size_gate(labels: List[str], config: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if PR size requires justification.

    Returns:
        (passed, reason) - True if passed, False with reason if failed
    """
    enforcement = config.get("enforcement", {})
    if not enforcement.get("enabled", False):
        return True, None

    size_blocking = enforcement.get("size_blocking", False)
    xl_requires_justification = enforcement.get("xl_requires_justification", False)

    xl_label = next((label for label in labels if label.startswith("size:XL")), None)

    if xl_label and xl_requires_justification:
        # Check for justification comment (not implemented in MVP)
        reason = "⚠️ XL PR detected - consider adding justification comment"
        if size_blocking:
            return False, reason
        else:
            return True, reason

    return True, None


def post_comment(message: str):
    """Post a comment on the PR."""
    try:
        gh("POST", f"/issues/{PR_NUMBER}/comments", {"body": message})
        print(f"📝 Comment posted on PR #{PR_NUMBER}")
    except requests.HTTPError as e:
        print(f"⚠️ Failed to post comment: {e}")


def set_check_status(check_name: str, state: str, description: str):
    """
    Set GitHub check run status.

    Args:
        check_name: Name of the check
        state: "success", "failure", or "neutral"
        description: Status description
    """
    # MVP Phase 1: Always return success, just log warnings
    print(f"Check: {check_name}")
    print(f"State: {state}")
    print(f"Description: {description}")


def generate_summary(
    governance_result: Tuple[bool, Optional[str]],
    template_result: Tuple[bool, Optional[str]],
    size_result: Tuple[bool, Optional[str]],
) -> str:
    """Generate GitHub Step Summary."""
    summary = ["# PR Governance Check Results", ""]

    all_passed = all(r[0] for r in [governance_result, template_result, size_result])

    if all_passed:
        summary.append("✅ **All checks passed**")
    else:
        summary.append("⚠️ **Some checks have warnings** (non-blocking in MVP Phase 1)")

    summary.append("")
    summary.append("## Check Details")
    summary.append("")

    # Governance check
    gov_passed, gov_reason = governance_result
    if gov_passed and gov_reason:
        summary.append(f"- **Governance:** {gov_reason}")
    elif gov_passed:
        summary.append("- **Governance:** ✅ Passed")
    else:
        summary.append(f"- **Governance:** ❌ {gov_reason}")

    # Template check
    tpl_passed, tpl_reason = template_result
    if tpl_passed and tpl_reason:
        summary.append(f"- **Template:** {tpl_reason}")
    elif tpl_passed:
        summary.append("- **Template:** ✅ Passed")
    else:
        summary.append(f"- **Template:** ❌ {tpl_reason}")

    # Size check
    size_passed, size_reason = size_result
    if size_passed and size_reason:
        summary.append(f"- **Size:** {size_reason}")
    elif size_passed:
        summary.append("- **Size:** ✅ Passed")
    else:
        summary.append(f"- **Size:** ❌ {size_reason}")

    summary.append("")
    summary.append("---")
    summary.append(f"**PR:** #{PR_NUMBER}")
    summary.append(f"**Title:** {PR_TITLE}")
    summary.append(f"**Draft:** {PR_IS_DRAFT}")

    return "\n".join(summary)


def main():
    """Main execution."""
    print(f"🔍 Running governance checks for PR #{PR_NUMBER}")
    print(f"Repository: {REPO}")
    print(f"Draft: {PR_IS_DRAFT}")

    # Load configuration
    config = load_config()
    print(f"✅ Loaded config from {CONFIG_PATH}")

    # Get PR labels (applied by Issue #145 workflow)
    labels = get_pr_labels()
    print(f"🏷️  PR Labels: {', '.join(labels) if labels else '(none)'}")

    # Run checks
    governance_result = check_governance_status(labels, config)
    template_result = check_template_compliance(PR_BODY, config)
    size_result = check_size_gate(labels, config)

    # Generate summary
    summary = generate_summary(governance_result, template_result, size_result)
    print("\n" + summary)

    # Write to GITHUB_STEP_SUMMARY
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        with open(github_summary, "a") as f:
            f.write(summary + "\n")

    # Post warning comment if needed (only for serious issues)
    warnings = []
    if not governance_result[0]:
        warnings.append(governance_result[1])
    if not template_result[0]:
        warnings.append(template_result[1])
    if not size_result[0]:
        warnings.append(size_result[1])

    if warnings:
        comment = "## ⚠️ PR Governance Warnings\n\n"
        for warning in warnings:
            comment += f"- {warning}\n"
        comment += "\n---\n"
        comment += "*This is a non-blocking check in MVP Phase 1. Review recommended.*"
        post_comment(comment)

    # MVP Phase 1: Always exit 0 (non-blocking)
    # Phase 2 will change to exit 1 on failures
    print("\n✅ Governance checks complete (non-blocking mode)")
    sys.exit(0)


if __name__ == "__main__":
    main()
