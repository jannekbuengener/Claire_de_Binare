"""Read-only drift guard for CDB skill surface mirrors.

Canonical skill bodies live in ``docs/skills/<name>/SKILL.md`` (SSOT since
PR #3637). Surface adapters mirror those bodies to:

- ``.opencode/skills/<name>/SKILL.md``
- ``.cursor/skills/<name>/SKILL.md``
- ``.codex/cdb_skills/<name>/SKILL.md``
- ``.claude/skills/<name>/SKILL.md``

This validator compares each canon skill body against its expected adapters
(ignoring the surface header block) and reports drift. It never modifies files
and performs no network / GitHub / DB / MCP actions.

Usage:
    python tools/validate_skill_surface_mirror.py
    python tools/validate_skill_surface_mirror.py --json
    python tools/validate_skill_surface_mirror.py --skill cdb-session-close
    python tools/validate_skill_surface_mirror.py --repo-root .

Exit codes:
    0 - PASS (no drift)
    1 - DRIFT_FOUND (body mismatch or missing expected adapter)
    2 - BLOCKED (missing canon tree, unknown skill, parse/usage error)

Issue: #3643
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT_DEFAULT = Path(__file__).resolve().parent.parent

CANON_GLOB = "docs/skills/*/SKILL.md"

# Adapter surfaces and their path templates relative to the repo root.
SURFACES: dict[str, str] = {
    "opencode": ".opencode/skills/{name}/SKILL.md",
    "cursor": ".cursor/skills/{name}/SKILL.md",
    "codex": ".codex/cdb_skills/{name}/SKILL.md",
    "claude": ".claude/skills/{name}/SKILL.md",
}

# Documented, intentional adapter exclusions (Registry §16).
# skill -> {surface: reason}. Excluded (skill, surface) pairs are NOT drift.
EXCLUDED_ADAPTERS: dict[str, dict[str, str]] = {
    "cdb-onboarding": {
        "opencode": "codex-only alias; other surfaces use `onboarding` directly",
        "cursor": "codex-only alias; other surfaces use `onboarding` directly",
        "claude": "codex-only alias; other surfaces use `onboarding` directly",
    },
}

# Surfaces/paths intentionally out of scope for this mirror check.
# Documented for transparency; not compared, not treated as drift.
OUT_OF_SCOPE_NOTES: list[str] = [
    "`gh-fix-ci` canon extras (META.yaml, evals.json, scripts/) are canon-only; "
    "only SKILL.md bodies are compared.",
    "`.claude/skills/*.skill` package/alias files are out of scope.",
    "`.gemini/skills/` is a restricted surface; no CDB domain mirror expected.",
    "`.codex/cdb_skills/.system/` is out of scope.",
]

_HEADER_RE = re.compile(r"^\ufeff?\s*<!--.*?-->\s*", flags=re.DOTALL)
_HEADER_BLOCK_RE = re.compile(r"^\ufeff?\s*<!--(.*?)-->", flags=re.DOTALL)

# Adapters must declare they are mirrored from canon (Registry §7).
MIRRORED_MARKER = "mirrored-from-canon"


class DriftCheckError(Exception):
    """Raised for BLOCKED conditions (missing canon, unknown skill, parse error)."""


def strip_header(text: str) -> str:
    """Remove a leading HTML-comment surface header block, if present."""
    return _HEADER_RE.sub("", text, count=1)


def extract_header(text: str) -> str | None:
    """Return the leading HTML-comment header block content, or None if absent."""
    match = _HEADER_BLOCK_RE.match(text)
    return match.group(1) if match else None


def header_issue(skill: str, text: str) -> str | None:
    """Return a reason string if the adapter header is missing/invalid, else None.

    Enforces the Registry §7 rule that mirrored adapters must carry a
    ``mirrored-from-canon`` surface header referencing the canonical source.
    A body-only match is not sufficient: a lost or wrong header means the file
    is effectively unregistered / wrongly classified.
    """
    header = extract_header(text)
    if header is None:
        return "adapter has no surface header block (expected mirrored-from-canon)"
    if MIRRORED_MARKER not in header:
        return f"adapter header missing '{MIRRORED_MARKER}' marker"
    expected_source = f"docs/skills/{skill}/SKILL.md"
    if expected_source not in header:
        return f"adapter header does not reference canon source '{expected_source}'"
    return None


def normalize_body(text: str) -> str:
    """Normalize a skill body for comparison.

    Ignores surface-header differences and cosmetic line-ending / trailing
    whitespace differences that are not meaningful content drift.
    """
    body = strip_header(text)
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in body.split("\n")]
    return "\n".join(lines).strip()


def find_canon_skills(repo_root: Path) -> list[str]:
    """Return sorted canon skill names discovered under docs/skills/*/SKILL.md."""
    canon_dir = repo_root / "docs" / "skills"
    if not canon_dir.is_dir():
        raise DriftCheckError(f"canon directory not found: {canon_dir}")
    names = sorted(
        p.parent.name for p in canon_dir.glob("*/SKILL.md") if p.is_file()
    )
    if not names:
        raise DriftCheckError(f"no canon skills found under {canon_dir}/*/SKILL.md")
    return names


def exclusion_reason(skill: str, surface: str) -> str | None:
    """Return the documented exclusion reason for (skill, surface), or None."""
    return EXCLUDED_ADAPTERS.get(skill, {}).get(surface)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
        raise DriftCheckError(f"cannot read {path}: {exc}") from exc


def check_skill(repo_root: Path, skill: str) -> dict:
    """Compare one canon skill body against its expected adapter bodies."""
    canon_path = repo_root / "docs" / "skills" / skill / "SKILL.md"
    if not canon_path.is_file():
        raise DriftCheckError(f"canon file missing for skill '{skill}': {canon_path}")

    canon_body = normalize_body(_read_text(canon_path))

    mismatches: list[dict] = []
    missing: list[dict] = []
    excluded: list[dict] = []
    adapter_count = 0

    for surface, template in SURFACES.items():
        rel = template.format(name=skill)
        reason = exclusion_reason(skill, surface)
        if reason is not None:
            excluded.append({"skill": skill, "surface": surface, "reason": reason})
            continue

        adapter_path = repo_root / rel
        if not adapter_path.is_file():
            missing.append({"skill": skill, "surface": surface, "path": rel})
            continue

        adapter_count += 1
        adapter_text = _read_text(adapter_path)
        if normalize_body(adapter_text) != canon_body:
            mismatches.append(
                {
                    "skill": skill,
                    "surface": surface,
                    "path": rel,
                    "kind": "body",
                    "reason": "adapter body differs from canon (header ignored)",
                }
            )
        head_reason = header_issue(skill, adapter_text)
        if head_reason is not None:
            mismatches.append(
                {
                    "skill": skill,
                    "surface": surface,
                    "path": rel,
                    "kind": "header",
                    "reason": head_reason,
                }
            )

    return {
        "skill": skill,
        "adapter_count": adapter_count,
        "mismatches": mismatches,
        "missing": missing,
        "excluded": excluded,
    }


def run(repo_root: Path, skill_filter: str | None = None) -> dict:
    """Run the drift check across all canon skills (or one filtered skill)."""
    canon_skills = find_canon_skills(repo_root)

    if skill_filter is not None:
        if skill_filter not in canon_skills:
            raise DriftCheckError(
                f"skill '{skill_filter}' not found in canon "
                f"({len(canon_skills)} skills discovered)"
            )
        canon_skills = [skill_filter]

    mismatches: list[dict] = []
    missing: list[dict] = []
    excluded: list[dict] = []
    adapter_count = 0

    for skill in canon_skills:
        result = check_skill(repo_root, skill)
        adapter_count += result["adapter_count"]
        mismatches.extend(result["mismatches"])
        missing.extend(result["missing"])
        excluded.extend(result["excluded"])

    limitations: list[str] = list(OUT_OF_SCOPE_NOTES)

    if mismatches or missing:
        status = "DRIFT_FOUND"
    else:
        status = "PASS"

    return {
        "status": status,
        "canon_count": len(canon_skills),
        "adapter_count": adapter_count,
        "mismatches": mismatches,
        "missing": missing,
        "excluded": excluded,
        "limitations": limitations,
    }


def _status_exit_code(status: str) -> int:
    return {"PASS": 0, "DRIFT_FOUND": 1, "BLOCKED": 2}.get(status, 2)


def format_human(report: dict) -> str:
    """Render a human-readable report from a run() result."""
    lines: list[str] = []
    lines.append("CDB Skill Surface Mirror Drift Check")
    lines.append(f"Status: {report['status']}")
    lines.append(f"Canon skills: {report['canon_count']}")
    lines.append(f"Adapters compared: {report['adapter_count']}")

    mismatches = report.get("mismatches", [])
    lines.append("")
    lines.append(f"Mismatches ({len(mismatches)}):")
    if mismatches:
        for m in mismatches:
            kind = m.get("kind", "")
            tag = f"DRIFT/{kind}" if kind else "DRIFT"
            lines.append(f"  - {tag} {m['skill']} [{m['surface']}] {m['path']}: {m['reason']}")
    else:
        lines.append("  - none")

    missing = report.get("missing", [])
    lines.append("")
    lines.append(f"Missing expected adapters ({len(missing)}):")
    if missing:
        for m in missing:
            lines.append(f"  - MISSING {m['skill']} [{m['surface']}] {m['path']}")
    else:
        lines.append("  - none")

    excluded = report.get("excluded", [])
    lines.append("")
    lines.append(f"Documented exclusions ({len(excluded)}):")
    if excluded:
        for e in excluded:
            lines.append(f"  - EXCLUDED {e['skill']} [{e['surface']}]: {e['reason']}")
    else:
        lines.append("  - none")

    limitations = report.get("limitations", [])
    if limitations:
        lines.append("")
        lines.append("Limitations / out of scope:")
        for note in limitations:
            lines.append(f"  - {note}")

    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only drift guard for CDB skill surface mirrors (Issue #3643).",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT_DEFAULT),
        help="Repository root (default: repo containing this tool).",
    )
    parser.add_argument(
        "--skill",
        default=None,
        help="Limit the check to a single canon skill name.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON instead of a human report.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path(args.repo_root).resolve()

    try:
        report = run(repo_root, skill_filter=args.skill)
    except DriftCheckError as exc:
        blocked = {
            "status": "BLOCKED",
            "canon_count": 0,
            "adapter_count": 0,
            "mismatches": [],
            "missing": [],
            "excluded": [],
            "limitations": [f"blocked: {exc}"],
        }
        if args.as_json:
            print(json.dumps(blocked, indent=2, ensure_ascii=False))
        else:
            print(format_human(blocked))
            print(f"\nBLOCKED: {exc}", file=sys.stderr)
        return _status_exit_code("BLOCKED")

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))

    return _status_exit_code(report["status"])


if __name__ == "__main__":
    raise SystemExit(main())
