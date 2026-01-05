import os
import re
import fnmatch
from typing import Dict, List, Tuple, Set

import requests
import yaml

TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["REPO"]  # owner/name
PR_NUMBER = int(os.environ["PR_NUMBER"])
PR_TITLE = os.environ.get("PR_TITLE", "")
PR_IS_DRAFT = os.environ.get("PR_IS_DRAFT", "false").lower() == "true"
EVENT_ACTION = os.environ.get("EVENT_ACTION", "")
CONFIG_PATH = os.environ.get("CONFIG_PATH", ".github/pr-labels.yml")

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

OWNER, NAME = REPO.split("/", 1)

SIZE_LABEL_PREFIX = "size:"
REVIEW_LABEL_PREFIX = "review:"


def gh(method: str, path: str, **kwargs):
    url = f"{API}{path}"
    r = requests.request(method, url, headers=HEADERS, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(
            f"GitHub API {method} {path} failed: {r.status_code} {r.text}"
        )
    return r


def load_config() -> Dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_pr_files() -> List[str]:
    files = []
    page = 1
    while True:
        r = gh(
            "GET",
            f"/repos/{OWNER}/{NAME}/pulls/{PR_NUMBER}/files",
            params={"per_page": 100, "page": page},
        )
        batch = r.json()
        if not batch:
            break
        files.extend([x["filename"] for x in batch])
        page += 1
    return files


def get_issue_labels() -> List[str]:
    r = gh("GET", f"/repos/{OWNER}/{NAME}/issues/{PR_NUMBER}")
    return [label["name"] for label in r.json().get("labels", [])]


def ensure_label_exists(label: str):
    # Create label if missing; ignore "already exists"
    color = "ededed"
    if label.startswith("area:"):
        color = "0e8a16"
    elif label.startswith("type:"):
        color = "d73a4a"
    elif label.startswith("priority:"):
        color = "fbca04"
    elif label.startswith("governance:"):
        color = "b60205"
    elif label.startswith("review:") or label == "needs-review":
        color = "1d76db"
    elif label.startswith("size:"):
        color = "c2e0c6"

    try:
        gh(
            "POST",
            f"/repos/{OWNER}/{NAME}/labels",
            json={
                "name": label,
                "color": color,
                "description": "managed by pr-auto-label",
            },
        )
    except RuntimeError as e:
        if "already_exists" in str(e) or "Validation Failed" in str(e):
            return
        raise


def add_labels(labels: List[str]):
    if not labels:
        return
    gh(
        "POST",
        f"/repos/{OWNER}/{NAME}/issues/{PR_NUMBER}/labels",
        json={"labels": labels},
    )


def remove_label(label: str):
    # 404 is fine if label not present
    url = f"/repos/{OWNER}/{NAME}/issues/{PR_NUMBER}/labels/{requests.utils.quote(label, safe='')}"
    r = requests.request("DELETE", f"{API}{url}", headers=HEADERS)
    if r.status_code in (200, 204, 404):
        return
    raise RuntimeError(f"DELETE {url} failed: {r.status_code} {r.text}")


def match_any(path: str, globs: List[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in globs)


def compute_size_label(cfg: Dict, file_count: int) -> str:
    th = cfg["size"]["thresholds"]
    labels = cfg["size"]["labels"]
    if file_count <= th["XS"]:
        return labels["XS"]
    if file_count <= th["S"]:
        return labels["S"]
    if file_count <= th["M"]:
        return labels["M"]
    if file_count <= th["L"]:
        return labels["L"]
    return labels["XL"]


def governance_violations(cfg: Dict, files: List[str]) -> Tuple[bool, List[str]]:
    g = cfg.get("governance", {})
    if not g.get("enabled", False):
        return False, []
    violations = []
    for rule in g.get("rules", []):
        name = rule.get("name", "Unnamed rule")
        match_paths = rule.get("match_paths", [])
        exclude_paths = rule.get("exclude_paths", [])
        hit = []
        for f in files:
            if match_paths and not match_any(f, match_paths):
                continue
            if exclude_paths and match_any(f, exclude_paths):
                continue
            hit.append(f)
        if hit:
            violations.append(
                f"{name}: {', '.join(hit[:10])}{' …' if len(hit) > 10 else ''}"
            )
    return (len(violations) > 0), violations


def post_governance_comment(violations: List[str]):
    marker = "<!-- pr-auto-label:governance -->"

    # Avoid spam: check last 50 comments for marker
    r = gh(
        "GET",
        f"/repos/{OWNER}/{NAME}/issues/{PR_NUMBER}/comments",
        params={"per_page": 50},
    )
    for c in r.json():
        if marker in c.get("body", ""):
            return

    body = (
        f"{marker}\n"
        "## ⚠️ Governance Review Required\n"
        "This PR touches paths that are typically Docs-Hub-only or root documentation.\n\n"
        "**Signals:**\n" + "\n".join([f"- {v}" for v in violations]) + "\n\n"
        "Action: confirm this is intentional, otherwise move docs to the Docs Hub.\n"
    )
    gh(
        "POST",
        f"/repos/{OWNER}/{NAME}/issues/{PR_NUMBER}/comments",
        json={"body": body},
    )


def main():
    cfg = load_config()
    files = list_pr_files()
    file_count = len(files)

    wanted: Set[str] = set()

    # Path-based area labels
    for item in cfg.get("area_labels", []):
        label = item["label"]
        paths = item.get("paths", [])
        if any(match_any(f, paths) for f in files):
            wanted.add(label)

    # Title-based labels
    for item in cfg.get("title_labels", []):
        label = item["label"]
        rx = item.get("regex")
        if rx and re.search(rx, PR_TITLE or ""):
            wanted.add(label)

    # Review labels
    if cfg.get("review", {}).get("enabled", False):
        if PR_IS_DRAFT:
            wanted.add(cfg["review"]["draft_label"])
        else:
            wanted.add(cfg["review"]["ready_label"])

    # Size label
    if cfg.get("size", {}).get("enabled", False):
        wanted.add(compute_size_label(cfg, file_count))

    # Governance detection
    has_gov, gov_details = governance_violations(cfg, files)
    if has_gov:
        wanted.add(cfg["governance"]["violation_label"])

    # Ensure labels exist
    for label in sorted(wanted):
        ensure_label_exists(label)

    # Remove conflicting managed labels (size + review)
    existing = get_issue_labels()
    for label in existing:
        if label.startswith(SIZE_LABEL_PREFIX):
            remove_label(label)
        if label.startswith(REVIEW_LABEL_PREFIX):
            remove_label(label)

    # Apply
    add_labels(sorted(wanted))

    # Comment if governance violation
    if has_gov and gov_details:
        post_governance_comment(gov_details)

    # Step summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("## PR Auto Label Result\n")
            f.write(f"- PR: #{PR_NUMBER}\n")
            f.write(f"- Files changed: {file_count}\n")
            f.write("- Labels applied:\n")
            for label in sorted(wanted):
                f.write(f"  - {label}\n")
            if has_gov:
                f.write("\n### Governance flags\n")
                for d in gov_details:
                    f.write(f"- {d}\n")


if __name__ == "__main__":
    main()
