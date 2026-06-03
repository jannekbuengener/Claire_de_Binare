"""Deterministic cross-repo root and GitHub target inventory (#2853).

Read-only discovery: local filesystem checks and optional ``gh repo view``.
Never clones repositories or reports MISSING local roots as PASS.

Issue: #2853
Parent: #2847

Usage:
    python -m tools.mcp.cross_repo_root_inventory
    python -m tools.mcp.cross_repo_root_inventory --format json
    python -m tools.mcp.cross_repo_root_inventory --format markdown
    make context-root-inventory
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from core.utils.clock import utcnow

LocalStatus = Literal["OK", "MISSING", "LIMITED"]
GithubTargetStatus = Literal[
    "OK", "MISSING", "LIMITED", "NOT_CONFIGURED", "SKIPPED"
]
RootsVerdict = Literal["pass", "fail", "pass_with_limits"]
OutputFormat = Literal["text", "json", "markdown"]

CONFIG_REL = Path("infrastructure/config/mcp/cross_repo_root_inventory.json")
ISSUE_REF = "#2853"
PARENT_ISSUE_REF = "#2847"

_GITHUB_SLUG_RE = re.compile(
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.\s]+)",
    re.IGNORECASE,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_inventory_config(
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = _repo_root() if repo_root is None else repo_root
    config_path = root / CONFIG_REL
    if not config_path.is_file():
        raise FileNotFoundError(f"missing inventory config: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("inventory config must be a JSON object")
    return payload


def resolve_workspaces_repos_dir(
    working_repo_root: Path,
    config: dict[str, Any],
) -> Path:
    defaults = config.get("defaults") or {}
    env_name = defaults.get("workspaces_repos_dir_env")
    if isinstance(env_name, str) and env_name.strip():
        override = os.environ.get(env_name.strip())
        if override and override.strip():
            candidate = Path(override.strip()).expanduser()
            if candidate.is_dir():
                return candidate.resolve()
    return working_repo_root.resolve().parent


def _display_path(path: Path, working_repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(working_repo_root.resolve()))
    except ValueError:
        return str(resolved)


def _git_remote_slug(path: Path) -> tuple[str | None, str | None, list[str]]:
    limitations: list[str] = []
    git_dir = path / ".git"
    if not git_dir.exists():
        return None, None, ["no .git directory; github slug not inferred from local"]
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, None, [f"git remote lookup failed: {type(exc).__name__}"]
    if proc.returncode != 0:
        return None, None, ["origin remote not configured"]
    url = (proc.stdout or "").strip()
    match = _GITHUB_SLUG_RE.search(url)
    if not match:
        return None, None, [f"origin URL not parsed as GitHub slug: {url!r}"]
    return match.group("owner"), match.group("repo"), limitations


def _gh_repo_visible(owner: str, repo: str) -> tuple[GithubTargetStatus, list[str]]:
    slug = f"{owner}/{repo}"
    limitations: list[str] = []
    try:
        proc = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                slug,
                "--json",
                "nameWithOwner",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "LIMITED", [f"gh unavailable: {type(exc).__name__}"]
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        snippet = err[:200] if err else "gh repo view failed"
        return "MISSING", [f"github target not reachable: {snippet}"]
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return "LIMITED", ["gh returned non-JSON response"]
    name = payload.get("nameWithOwner")
    if isinstance(name, str) and name.lower() == slug.lower():
        return "OK", limitations
    return "LIMITED", [f"gh nameWithOwner mismatch: {name!r}"]


def _resolve_github_slug(
    entry: dict[str, Any],
    *,
    working_slug: tuple[str | None, str | None],
) -> tuple[str | None, str | None, list[str]]:
    github = entry.get("github")
    if not isinstance(github, dict):
        return None, None, []
    kind = github.get("kind")
    if kind == "same_as_working":
        owner, repo = working_slug
        return owner, repo, ["github target inherits working repo slug"]
    owner = github.get("owner")
    repo = github.get("repo")
    if isinstance(owner, str) and isinstance(repo, str) and owner and repo:
        return owner, repo, []
    return None, None, ["github owner/repo not configured"]


def _evaluate_local(
    entry: dict[str, Any],
    *,
    working_repo_root: Path,
    workspaces_repos_dir: Path,
) -> tuple[Path | None, LocalStatus, list[str]]:
    limitations: list[str] = []
    local = entry.get("local")
    if not isinstance(local, dict):
        return None, "MISSING", ["local spec missing"]

    kind = local.get("kind")
    if kind == "repo_root":
        path = working_repo_root.resolve()
        markers = [path / ".git", path / "AGENTS.md"]
        if all(marker.exists() for marker in markers):
            return path, "OK", limitations
        missing = [m.name for m in markers if not m.exists()]
        return path, "LIMITED", [f"missing working repo markers: {missing}"]

    rel = local.get("relative_path")
    if isinstance(rel, str) and rel.strip():
        path = (working_repo_root / rel.strip()).resolve()
        if path.is_dir():
            return path, "OK", limitations
        return path, "MISSING", [f"directory not found: {rel.strip()}"]

    rel_paths = local.get("relative_paths")
    if isinstance(rel_paths, list) and rel_paths:
        missing_files: list[str] = []
        first: Path | None = None
        for item in rel_paths:
            if not isinstance(item, str) or not item.strip():
                continue
            candidate = (working_repo_root / item.strip()).resolve()
            if first is None:
                first = candidate
            if not candidate.is_file():
                missing_files.append(item.strip())
        if not missing_files:
            return first, "OK", limitations
        if len(missing_files) == len(rel_paths):
            return first, "MISSING", [f"config files missing: {missing_files}"]
        return first, "LIMITED", [f"partial config missing: {missing_files}"]

    sibling = local.get("sibling_dir")
    if isinstance(sibling, str) and sibling.strip():
        path = (workspaces_repos_dir / sibling.strip()).resolve()
        if path.is_dir():
            return path, "OK", limitations
        return path, "MISSING", [f"sibling repo directory not present: {sibling.strip()}"]

    return None, "MISSING", ["unsupported or empty local spec"]


def _evaluate_github_target(
    entry: dict[str, Any],
    *,
    local_status: LocalStatus,
    local_path: Path | None,
    owner: str | None,
    repo: str | None,
    check_github: bool,
) -> tuple[GithubTargetStatus, list[str]]:
    limitations: list[str] = []
    if owner is None or repo is None:
        return "NOT_CONFIGURED", limitations

    if local_path is not None and local_path.is_dir():
        inferred_owner, inferred_repo, infer_notes = _git_remote_slug(local_path)
        limitations.extend(infer_notes)
        if inferred_owner and inferred_repo:
            if inferred_owner.lower() != owner.lower() or inferred_repo.lower() != (
                repo.lower()
            ):
                limitations.append(
                    "configured github slug differs from local origin remote"
                )

    if not check_github:
        return "SKIPPED", limitations + ["github reachability check disabled"]

    if local_status == "MISSING":
        gh_status, gh_notes = _gh_repo_visible(owner, repo)
        limitations.extend(gh_notes)
        limitations.append(
            "local path missing; github status does not imply local PASS"
        )
        return gh_status, limitations

    return _gh_repo_visible(owner, repo) if check_github else ("SKIPPED", limitations)


@dataclass
class RootInventoryRow:
    key: str
    display_name: str
    local_path: str | None
    local_status: LocalStatus
    github_owner: str | None
    github_repo: str | None
    github_slug: str | None
    github_target_status: GithubTargetStatus
    limitations: list[str] = field(default_factory=list)
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "local_path": self.local_path,
            "local_status": self.local_status,
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
            "github_slug": self.github_slug,
            "github_target_status": self.github_target_status,
            "limitations": list(self.limitations),
            "required": self.required,
        }


@dataclass
class RootInventoryReport:
    schema_version: str
    timestamp: str
    issue_refs: list[str]
    working_repo_root: str
    workspaces_repos_dir: str
    config_path: str
    rows: list[RootInventoryRow] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    roots_verdict: RootsVerdict = "pass"
    fail_reasons: list[str] = field(default_factory=list)
    discovery_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "issue_refs": list(self.issue_refs),
            "working_repo_root": self.working_repo_root,
            "workspaces_repos_dir": self.workspaces_repos_dir,
            "config_path": self.config_path,
            "rows": [row.to_dict() for row in self.rows],
            "summary": dict(self.summary),
            "roots_verdict": self.roots_verdict,
            "fail_reasons": list(self.fail_reasons),
            "discovery_notes": list(self.discovery_notes),
            "issue_ref": ISSUE_REF,
            "parent_issue_ref": PARENT_ISSUE_REF,
        }


def build_inventory(
    working_repo_root: Path | None = None,
    *,
    check_github: bool = True,
    config: dict[str, Any] | None = None,
) -> RootInventoryReport:
    """Build the cross-repo root inventory from canonical config."""
    root = _repo_root() if working_repo_root is None else working_repo_root.resolve()
    cfg = load_inventory_config(root) if config is None else config
    workspaces_dir = resolve_workspaces_repos_dir(root, cfg)
    entries = cfg.get("entries")
    if not isinstance(entries, list):
        raise ValueError("inventory config entries must be a list")

    working_owner, working_repo, _ = _git_remote_slug(root)
    working_slug = (working_owner, working_repo)

    rows: list[RootInventoryRow] = []
    summary: dict[str, int] = {"OK": 0, "MISSING": 0, "LIMITED": 0}
    fail_reasons: list[str] = []

    for raw in entries:
        if not isinstance(raw, dict):
            continue
        key = raw.get("key")
        if not isinstance(key, str) or not key.strip():
            continue
        display = raw.get("display_name")
        display_name = display if isinstance(display, str) else key
        required = bool(raw.get("required"))

        local_path, local_status, local_notes = _evaluate_local(
            raw,
            working_repo_root=root,
            workspaces_repos_dir=workspaces_dir,
        )
        owner, repo, slug_notes = _resolve_github_slug(
            raw, working_slug=working_slug
        )
        gh_status, gh_notes = _evaluate_github_target(
            raw,
            local_status=local_status,
            local_path=local_path,
            owner=owner,
            repo=repo,
            check_github=check_github,
        )
        limitations = list(local_notes) + list(slug_notes) + list(gh_notes)
        if local_status in summary:
            summary[local_status] += 1

        path_display = (
            _display_path(local_path, root) if local_path is not None else None
        )
        slug = f"{owner}/{repo}" if owner and repo else None

        if required and local_status != "OK":
            fail_reasons.append(
                f"required root {key!r} local_status={local_status}"
            )

        rows.append(
            RootInventoryRow(
                key=key,
                display_name=display_name,
                local_path=path_display,
                local_status=local_status,
                github_owner=owner,
                github_repo=repo,
                github_slug=slug,
                github_target_status=gh_status,
                limitations=limitations,
                required=required,
            )
        )

    optional_missing = [
        r.key
        for r in rows
        if not r.required and r.local_status == "MISSING"
    ]
    roots_verdict: RootsVerdict
    if fail_reasons:
        roots_verdict = "fail"
    elif optional_missing:
        roots_verdict = "pass_with_limits"
    else:
        roots_verdict = "pass"

    notes = cfg.get("discovery_notes")
    discovery_notes = (
        [str(item) for item in notes if isinstance(item, str)]
        if isinstance(notes, list)
        else []
    )

    return RootInventoryReport(
        schema_version=str(cfg.get("schema_version") or "1.0"),
        timestamp=utcnow().isoformat(),
        issue_refs=[
            str(item)
            for item in (cfg.get("issue_refs") or [ISSUE_REF, PARENT_ISSUE_REF])
            if isinstance(item, str)
        ],
        working_repo_root=str(root),
        workspaces_repos_dir=str(workspaces_dir),
        config_path=str((root / CONFIG_REL).as_posix()),
        rows=rows,
        summary=summary,
        roots_verdict=roots_verdict,
        fail_reasons=fail_reasons,
        discovery_notes=discovery_notes,
    )


def compute_exit_code(report: RootInventoryReport) -> int:
    return 1 if report.roots_verdict == "fail" else 0


def format_report_markdown(report: RootInventoryReport) -> str:
    lines = [
        "# Cross-repo root and GitHub target inventory",
        "",
        f"- **timestamp:** {report.timestamp}",
        f"- **roots_verdict:** {report.roots_verdict}",
        f"- **working_repo_root:** `{report.working_repo_root}`",
        f"- **workspaces_repos_dir:** `{report.workspaces_repos_dir}`",
        f"- **config:** `{report.config_path}`",
        "",
        "## Summary (local status)",
    ]
    for key in ("OK", "MISSING", "LIMITED"):
        lines.append(f"- **{key}:** {report.summary.get(key, 0)}")
    if report.fail_reasons:
        lines.extend(["", "## Fail reasons"])
        for reason in report.fail_reasons:
            lines.append(f"- {reason}")
    lines.extend(
        [
            "",
            "## Inventory",
            "",
            "| key | local_status | local_path | github_slug | github_target_status | required |",
            "|-----|--------------|------------|-------------|----------------------|----------|",
        ]
    )
    for row in report.rows:
        lines.append(
            f"| `{row.key}` | **{row.local_status}** | "
            f"{row.local_path or '—'} | {row.github_slug or '—'} | "
            f"**{row.github_target_status}** | {row.required} |"
        )
        if row.limitations:
            lines.append(f"| | | _{'; '.join(row.limitations)}_ | | | |")
    if report.discovery_notes:
        lines.extend(["", "## Discovery notes"])
        for note in report.discovery_notes:
            lines.append(f"- {note}")
    return "\n".join(lines)


def format_report(report: RootInventoryReport, fmt: OutputFormat) -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if fmt == "markdown":
        return format_report_markdown(report)
    lines = [
        f"roots_verdict={report.roots_verdict}",
        f"working_repo_root={report.working_repo_root}",
        f"workspaces_repos_dir={report.workspaces_repos_dir}",
        "",
    ]
    for row in report.rows:
        lines.append(
            f"{row.key}: local={row.local_status} path={row.local_path or '—'} "
            f"github={row.github_target_status} slug={row.github_slug or '—'}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cross-repo root and GitHub target inventory (#2853)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override working repo root (default: package parent)",
    )
    parser.add_argument(
        "--no-github-check",
        action="store_true",
        help="Skip gh repo view reachability checks",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write report (json or markdown by --format)",
    )
    args = parser.parse_args(argv)

    try:
        report = build_inventory(
            args.repo_root,
            check_github=not args.no_github_check,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"inventory error: {exc}", file=sys.stderr)
        return 2

    fmt: OutputFormat = args.format
    rendered = format_report(report, fmt)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return compute_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
