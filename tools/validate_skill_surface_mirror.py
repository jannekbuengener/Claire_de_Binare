"""Read-only drift guard for CDB skill surface mirrors.

Canonical skill bodies live in ``docs/skills/<name>/SKILL.md`` (SSOT since
PR #3637). Surface adapters mirror those bodies to:

- ``.opencode/skills/<name>/SKILL.md``
- ``.cursor/skills/<name>/SKILL.md``
- ``.codex/cdb_skills/<name>/SKILL.md``
- ``.claude/skills/<name>/SKILL.md``

This validator compares each canon skill body against its expected adapters
(ignoring the surface header block), checks local markdown links / anchors,
and enforces mirror parity for skill-local assets referenced from SKILL.md.
It never modifies files and performs no network / GitHub / DB / MCP actions.

Usage:
    python tools/validate_skill_surface_mirror.py
    python tools/validate_skill_surface_mirror.py --json
    python tools/validate_skill_surface_mirror.py --skill cdb-session-close
    python tools/validate_skill_surface_mirror.py --repo-root .

Exit codes:
    0 - PASS (no drift)
    1 - DRIFT_FOUND (body/header/link/asset mismatch or missing adapter)
    2 - BLOCKED (missing canon tree, unknown skill, parse/usage error)

Issues: #3643, #4122
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import unquote, urlparse

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

# Skill-local paths that stay canon-only (Issue #4122). Relative SKILL.md links
# to these paths are invalid because adapters would not resolve them.
# Values are POSIX-style relative paths under the skill directory.
CANON_ONLY_ASSETS: dict[str, frozenset[str]] = {
    "gh-fix-ci": frozenset(
        {
            "META.yaml",
            "evals.json",
            "scripts",
            "DISCOVERY_REPORT.md",
        }
    ),
}

# Schemes that are never resolved against the local filesystem.
EXTERNAL_SCHEMES = frozenset({"http", "https", "mailto", "http+unix"})

# Surfaces/paths intentionally out of scope for this mirror check.
# Documented for transparency; not compared, not treated as drift.
OUT_OF_SCOPE_NOTES: list[str] = [
    "`gh-fix-ci` canon extras (META.yaml, evals.json, scripts/, "
    "DISCOVERY_REPORT.md) are canon-only; SKILL.md must link DISCOVERY_REPORT "
    "via the explicit canon path (#4122).",
    "`.claude/skills/*.skill` package/alias files are out of scope.",
    "`.gemini/skills/` is a restricted surface; no CDB domain mirror expected.",
    "`.codex/cdb_skills/.system/` is out of scope.",
    "External http(s)/mailto links are classified but not fetched (no network).",
]

_HEADER_RE = re.compile(r"^\ufeff?\s*<!--.*?-->\s*", flags=re.DOTALL)
_HEADER_BLOCK_RE = re.compile(r"^\ufeff?\s*<!--(.*?)-->", flags=re.DOTALL)
_MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", flags=re.MULTILINE)

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


def normalize_asset_bytes(data: bytes) -> bytes:
    """Normalize asset bytes for cross-surface parity (text line endings)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def find_canon_skills(repo_root: Path) -> list[str]:
    """Return sorted canon skill names discovered under docs/skills/*/SKILL.md."""
    canon_dir = repo_root / "docs" / "skills"
    if not canon_dir.is_dir():
        raise DriftCheckError(f"canon directory not found: {canon_dir}")
    names = sorted(p.parent.name for p in canon_dir.glob("*/SKILL.md") if p.is_file())
    if not names:
        raise DriftCheckError(f"no canon skills found under {canon_dir}/*/SKILL.md")
    return names


def exclusion_reason(skill: str, surface: str) -> str | None:
    """Return the documented exclusion reason for (skill, surface), or None."""
    return EXCLUDED_ADAPTERS.get(skill, {}).get(surface)


def skill_dir_for_surface(repo_root: Path, skill: str, surface: str) -> Path:
    """Return the skill directory path for canon or an adapter surface."""
    if surface == "canon":
        return repo_root / "docs" / "skills" / skill
    return (repo_root / SURFACES[surface].format(name=skill)).parent


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
        raise DriftCheckError(f"cannot read {path}: {exc}") from exc


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:  # pragma: no cover - defensive
        raise DriftCheckError(f"cannot read {path}: {exc}") from exc


def github_slug(heading: str) -> str:
    """Approximate GitHub / CommonMark heading slug used in this repo."""
    text = heading.strip().lower()
    # Drop markdown emphasis/code markers commonly seen in headings.
    text = re.sub(r"[`*_~]", "", text)
    # Keep word chars, spaces, and hyphens; drop other punctuation.
    text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text)
    return text


def collect_heading_anchors(markdown: str) -> set[str]:
    """Return the set of heading anchors for a markdown document."""
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for match in _HEADING_RE.finditer(markdown):
        base = github_slug(match.group(2))
        if not base:
            continue
        count = seen.get(base, 0)
        seen[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def _is_canon_only_rel(skill: str, rel_posix: str) -> bool:
    """True if rel_posix is a documented canon-only asset path for the skill."""
    allowed = CANON_ONLY_ASSETS.get(skill, frozenset())
    if not allowed:
        return False
    parts = PurePosixPath(rel_posix).parts
    if not parts:
        return False
    # Exact file match or anything under a canon-only directory (e.g. scripts/).
    if parts[0] in allowed:
        return True
    return rel_posix in allowed


def _is_skill_local_link_path(path_part: str) -> bool:
    """True when the written link path stays under the skill dir (no ``..``)."""
    if not path_part:
        return False
    return ".." not in PurePosixPath(path_part).parts


def iter_markdown_links(text: str) -> list[tuple[int, str, str]]:
    """Yield (1-based line, link_text, raw_target) for markdown links in text."""
    results: list[tuple[int, str, str]] = []
    for match in _MD_LINK_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        raw = match.group(2).strip()
        # Angle-bracket autolinks / titles: take first token before whitespace/title.
        if raw.startswith("<") and ">" in raw:
            raw = raw[1 : raw.index(">")].strip()
        else:
            raw = raw.split()[0] if raw else raw
            if (raw.startswith('"') and raw.endswith('"')) or (
                raw.startswith("'") and raw.endswith("'")
            ):
                raw = raw[1:-1]
        results.append((line_no, match.group(1), raw))
    return results


def _classify_link_target(raw_target: str) -> tuple[str, str, str]:
    """Return (kind, path_part, fragment) for a markdown link target.

    kind is one of: external | empty | local
    """
    if not raw_target or raw_target == "#":
        return "empty", "", ""
    parsed = urlparse(raw_target)
    if parsed.scheme and parsed.scheme.lower() in EXTERNAL_SCHEMES:
        return "external", "", ""
    if parsed.scheme and parsed.scheme.lower() not in {"", "file"}:
        # Unknown / disallowed scheme — treat as external (not locally resolved).
        return "external", "", ""
    # urlparse("references/foo.md#bar") puts path in path; fragment separate.
    # urlparse("./a.md") works; Windows paths are not expected in skill links.
    path_part = unquote(parsed.path or "")
    # Handle targets that are fragment-only (#anchor).
    if raw_target.startswith("#"):
        return "local", "", unquote(parsed.fragment or raw_target[1:])
    fragment = unquote(parsed.fragment or "")
    # Drop query for local resolution (external queries already handled).
    return "local", path_part, fragment


def check_local_links(
    *,
    repo_root: Path,
    skill: str,
    surface: str,
    skill_md_path: Path,
    text: str,
) -> list[dict]:
    """Validate local markdown links in one SKILL.md file."""
    mismatches: list[dict] = []
    skill_dir = skill_md_path.parent
    repo_root_resolved = repo_root.resolve()
    rel_skill_md = skill_md_path.relative_to(repo_root).as_posix()

    for line_no, _link_text, raw_target in iter_markdown_links(text):
        kind, path_part, fragment = _classify_link_target(raw_target)
        if kind in {"external", "empty"}:
            continue

        if path_part == "" and fragment:
            # Same-file anchor.
            anchors = collect_heading_anchors(strip_header(text))
            if fragment not in anchors:
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": rel_skill_md,
                        "kind": "MISSING_ANCHOR",
                        "line": line_no,
                        "target": raw_target,
                        "reason": (f"anchor '#{fragment}' not found in {rel_skill_md}"),
                    }
                )
            continue

        # Resolve relative to the source file directory (POSIX-neutral).
        resolved = (skill_md_path.parent / Path(path_part)).resolve()
        try:
            resolved.relative_to(repo_root_resolved)
        except ValueError:
            mismatches.append(
                {
                    "skill": skill,
                    "surface": surface,
                    "path": rel_skill_md,
                    "kind": "PATH_ESCAPES_REPO_ROOT",
                    "line": line_no,
                    "target": raw_target,
                    "reason": (f"local link resolves outside repo root: {raw_target}"),
                }
            )
            continue

        # Skill-local relative path (for asset-class checks).
        try:
            rel_to_skill = resolved.relative_to(skill_dir.resolve()).as_posix()
            inside_skill = True
        except ValueError:
            rel_to_skill = ""
            inside_skill = False

        # Skill-local relative links (no "..") to canon-only assets are invalid
        # because body parity would leave adapters with dead links. Explicit
        # repo-relative canon paths (with "..") remain allowed.
        if (
            inside_skill
            and _is_skill_local_link_path(path_part)
            and _is_canon_only_rel(skill, rel_to_skill)
        ):
            mismatches.append(
                {
                    "skill": skill,
                    "surface": surface,
                    "path": rel_skill_md,
                    "kind": "INVALID_ASSET_CLASS",
                    "line": line_no,
                    "target": raw_target,
                    "reason": (
                        f"skill-local relative link to canon-only asset "
                        f"'{rel_to_skill}' is not allowed in SKILL.md "
                        f"(use explicit canon path or reclassify as mirrored)"
                    ),
                }
            )
            continue

        expects_dir = path_part.endswith("/")
        if expects_dir:
            if not resolved.is_dir():
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": rel_skill_md,
                        "kind": "MISSING_LOCAL_TARGET",
                        "line": line_no,
                        "target": raw_target,
                        "reason": (f"missing directory for link target: {raw_target}"),
                    }
                )
            continue

        if not resolved.exists():
            mismatches.append(
                {
                    "skill": skill,
                    "surface": surface,
                    "path": rel_skill_md,
                    "kind": "MISSING_LOCAL_TARGET",
                    "line": line_no,
                    "target": raw_target,
                    "reason": f"missing local target for link: {raw_target}",
                }
            )
            continue

        if resolved.is_dir():
            # Directory linked without trailing slash — still valid existence.
            continue

        if fragment and resolved.suffix.lower() in {".md", ".markdown"}:
            try:
                target_text = _read_text(resolved)
            except DriftCheckError as exc:
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": rel_skill_md,
                        "kind": "MISSING_LOCAL_TARGET",
                        "line": line_no,
                        "target": raw_target,
                        "reason": str(exc),
                    }
                )
                continue
            anchors = collect_heading_anchors(target_text)
            if fragment not in anchors:
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": rel_skill_md,
                        "kind": "MISSING_ANCHOR",
                        "line": line_no,
                        "target": raw_target,
                        "reason": (
                            f"anchor '#{fragment}' not found in "
                            f"{resolved.relative_to(repo_root_resolved).as_posix()}"
                        ),
                    }
                )

    return mismatches


def collect_mirrored_asset_rels(
    skill: str, canon_text: str, canon_md: Path
) -> set[str]:
    """Return skill-relative asset paths that must be mirrored across surfaces."""
    mirrored: set[str] = set()
    skill_dir = canon_md.parent.resolve()
    for _line, _text, raw_target in iter_markdown_links(canon_text):
        kind, path_part, _fragment = _classify_link_target(raw_target)
        if kind != "local" or not path_part:
            continue
        resolved = (canon_md.parent / Path(path_part)).resolve()
        try:
            rel = resolved.relative_to(skill_dir).as_posix()
        except ValueError:
            continue
        if rel in {"", "."} or rel == "SKILL.md":
            continue
        if _is_canon_only_rel(skill, rel):
            continue
        mirrored.add(rel)
    return mirrored


def check_mirrored_assets(
    *,
    repo_root: Path,
    skill: str,
    asset_rels: set[str],
) -> list[dict]:
    """Ensure skill-local mirrored assets exist on all active surfaces with parity."""
    mismatches: list[dict] = []
    if not asset_rels:
        return mismatches

    surfaces_to_check = ["canon"] + [
        surface for surface in SURFACES if exclusion_reason(skill, surface) is None
    ]

    for rel in sorted(asset_rels):
        payloads: dict[str, bytes | None] = {}
        for surface in surfaces_to_check:
            skill_dir = skill_dir_for_surface(repo_root, skill, surface)
            asset_path = skill_dir / Path(rel)
            if not asset_path.exists():
                payloads[surface] = None
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": (
                            asset_path.relative_to(repo_root).as_posix()
                            if asset_path.is_relative_to(repo_root)
                            else str(asset_path)
                        ),
                        "kind": "MISSING_MIRRORED_ASSET",
                        "line": None,
                        "target": rel,
                        "reason": (
                            f"mirrored asset missing on surface '{surface}': {rel}"
                        ),
                    }
                )
                continue
            if asset_path.is_dir():
                # Directory presence is enough; children linked separately.
                payloads[surface] = b"__DIR__"
                continue
            payloads[surface] = normalize_asset_bytes(_read_bytes(asset_path))

        present = {s: data for s, data in payloads.items() if data is not None}
        if len(present) < 2:
            continue
        # Compare all present surfaces to the first present payload.
        baseline_surface, baseline = next(iter(present.items()))
        for surface, data in present.items():
            if surface == baseline_surface:
                continue
            if data != baseline:
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": (
                            skill_dir_for_surface(repo_root, skill, surface) / Path(rel)
                        )
                        .relative_to(repo_root)
                        .as_posix(),
                        "kind": "ASSET_CONTENT_DRIFT",
                        "line": None,
                        "target": rel,
                        "reason": (
                            f"mirrored asset content drifts vs '{baseline_surface}': "
                            f"{rel}"
                        ),
                    }
                )
    return mismatches


def validate_exclusion_tables() -> list[dict]:
    """Return INVALID_EXCEPTION mismatches for undocumented exclusion surfaces."""
    mismatches: list[dict] = []
    for skill, surfaces in EXCLUDED_ADAPTERS.items():
        for surface, reason in surfaces.items():
            if surface not in SURFACES:
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": "tools/validate_skill_surface_mirror.py",
                        "kind": "INVALID_EXCEPTION",
                        "line": None,
                        "target": surface,
                        "reason": (
                            f"EXCLUDED_ADAPTERS references unknown surface "
                            f"'{surface}' (reason={reason!r})"
                        ),
                    }
                )
            if not str(reason).strip():
                mismatches.append(
                    {
                        "skill": skill,
                        "surface": surface,
                        "path": "tools/validate_skill_surface_mirror.py",
                        "kind": "INVALID_EXCEPTION",
                        "line": None,
                        "target": surface,
                        "reason": f"empty exclusion reason for {skill}/{surface}",
                    }
                )
    return mismatches


def check_skill(repo_root: Path, skill: str) -> dict:
    """Compare one canon skill body against its expected adapter bodies."""
    canon_path = repo_root / "docs" / "skills" / skill / "SKILL.md"
    if not canon_path.is_file():
        raise DriftCheckError(f"canon file missing for skill '{skill}': {canon_path}")

    canon_text = _read_text(canon_path)
    canon_body = normalize_body(canon_text)

    mismatches: list[dict] = []
    missing: list[dict] = []
    excluded: list[dict] = []
    adapter_count = 0

    mismatches.extend(
        check_local_links(
            repo_root=repo_root,
            skill=skill,
            surface="canon",
            skill_md_path=canon_path,
            text=canon_text,
        )
    )

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
        mismatches.extend(
            check_local_links(
                repo_root=repo_root,
                skill=skill,
                surface=surface,
                skill_md_path=adapter_path,
                text=adapter_text,
            )
        )

    asset_rels = collect_mirrored_asset_rels(skill, canon_text, canon_path)
    mismatches.extend(
        check_mirrored_assets(
            repo_root=repo_root,
            skill=skill,
            asset_rels=asset_rels,
        )
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

    # Validate exclusion table once per run (not per skill filter miss).
    mismatches.extend(validate_exclusion_tables())

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
            line = m.get("line")
            line_bit = f":L{line}" if line is not None else ""
            target = m.get("target")
            target_bit = f" target={target!r}" if target else ""
            lines.append(
                f"  - {tag} {m['skill']} [{m.get('surface', '?')}] "
                f"{m.get('path', '?')}{line_bit}{target_bit}: {m['reason']}"
            )
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
        description=(
            "Read-only drift guard for CDB skill surface mirrors "
            "(Issues #3643, #4122)."
        ),
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
