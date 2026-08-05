"""Cursor environment Dockerfile build-context contract (#4360).

Ensures every local COPY/ADD source in the Dockerfile referenced by
``.cursor/environment.json`` exists under the configured build context and is
not excluded by the context-root ``.dockerignore``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Sequence

from tools.agent_control.environment.codes import (
    REASON_CONFIG_MISSING,
    REASON_CONFIG_SCHEMA_INVALID,
)
from tools.agent_control.environment.digest import resolve_repo_relative
from tools.agent_control.errors import DispatchError

DEFAULT_CONFIG_REL = Path(".cursor") / "environment.json"

_COPY_ADD_RE = re.compile(
    r"^\s*(COPY|ADD)\s+(.+?)\s+(\S+)\s*$",
    re.IGNORECASE,
)
_FROM_FLAG_RE = re.compile(r"^--from=.+$", re.IGNORECASE)
_CHMOD_CHOWN_RE = re.compile(r"^--(chmod|chown)=.+$", re.IGNORECASE)
_URL_RE = re.compile(r"^(?:https?|git|ftp)://", re.IGNORECASE)


@dataclass(frozen=True)
class CopySourceCheck:
    instruction: str
    source: str
    exists: bool
    excluded_by_dockerignore: bool
    matching_pattern: str | None

    @property
    def ok(self) -> bool:
        return self.exists and not self.excluded_by_dockerignore


@dataclass(frozen=True)
class DockerfileContextReport:
    config_path: str
    dockerfile_path: str
    context_path: str
    dockerignore_path: str | None
    sources: tuple[CopySourceCheck, ...]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.sources)

    @property
    def failures(self) -> tuple[CopySourceCheck, ...]:
        return tuple(item for item in self.sources if not item.ok)


def load_dockerignore_patterns(dockerignore: Path) -> list[str]:
    if not dockerignore.is_file():
        return []
    patterns: list[str] = []
    for raw in dockerignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def dockerignore_excludes(
    rel_path: str,
    patterns: Sequence[str],
) -> tuple[bool, str | None]:
    """Return whether ``rel_path`` is excluded and the last matching pattern."""
    normalized = rel_path.replace("\\", "/").lstrip("./")
    excluded = False
    last_match: str | None = None
    for raw in patterns:
        negate = raw.startswith("!")
        pat = raw[1:] if negate else raw
        pat = pat.lstrip("/")
        if not _dockerignore_match(normalized, pat):
            continue
        excluded = not negate
        last_match = raw
    return excluded, last_match


def _dockerignore_match(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        prefix = pattern.rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    if pattern == path:
        return True
    if "**" in pattern:
        # Conservative fnmatch after collapsing ** to *
        collapsed = pattern.replace("**/", "").replace("**", "*")
        return fnmatch(path, collapsed) or fnmatch(path.split("/")[-1], collapsed)
    if "/" in pattern:
        return fnmatch(path, pattern)
    # Basename-only patterns match in any directory (Docker/.gitignore style).
    return fnmatch(path, pattern) or fnmatch(path.split("/")[-1], pattern)


def parse_local_copy_sources(dockerfile_text: str) -> list[tuple[str, str]]:
    """Yield (instruction, source) for local COPY/ADD sources (not URLs / --from)."""
    sources: list[tuple[str, str]] = []
    for raw_line in dockerfile_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _COPY_ADD_RE.match(line)
        if not match:
            continue
        instruction = match.group(1).upper()
        mid = match.group(2).strip()
        # Dest is group(3); sources are everything before it in mid after flags.
        tokens = _tokenize_dockerfile_args(mid)
        # Multi-stage COPY --from=... is not a local context source.
        if any(_FROM_FLAG_RE.match(token) for token in tokens):
            continue
        filtered: list[str] = []
        for token in tokens:
            if _CHMOD_CHOWN_RE.match(token):
                continue
            filtered.append(token)
        for src in filtered:
            if src in {".", ".."}:
                continue
            if _URL_RE.match(src):
                continue
            if src.startswith("--"):
                continue
            # Absolute paths are not context-relative sources.
            if src.startswith("/"):
                continue
            sources.append((instruction, src))
    return sources


def _tokenize_dockerfile_args(mid: str) -> list[str]:
    # JSON-array form: COPY ["a","b","dest"] — regex already excluded dest via last token
    # of non-JSON form. For JSON, mid may be '["a", "b"]' without dest when dest is last
    # in full line — handle both.
    stripped = mid.strip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped.split()
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return stripped.split()
    return stripped.split()


def check_cursor_dockerfile_context(
    repo_root: Path,
    *,
    config_path: Path | None = None,
) -> DockerfileContextReport:
    """Validate Cursor environment Dockerfile COPY/ADD sources vs .dockerignore."""
    root = repo_root.resolve()
    path = (config_path or (root / DEFAULT_CONFIG_REL)).resolve()
    if not path.is_file():
        raise DispatchError(
            REASON_CONFIG_MISSING,
            f"missing provider environment config: {path}",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            f"invalid environment.json: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            "environment.json must be an object",
        )

    build = payload.get("build") or {}
    if not isinstance(build, dict):
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            "environment.json build must be an object",
        )
    dockerfile_rel = build.get("dockerfile")
    context_rel = build.get("context", ".")
    if not isinstance(dockerfile_rel, str) or not dockerfile_rel.strip():
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            "environment.json build.dockerfile is required",
        )
    if not isinstance(context_rel, str) or not context_rel.strip():
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            "environment.json build.context is required",
        )

    base_dir = path.parent
    dockerfile = resolve_repo_relative(
        root, base_dir, dockerfile_rel, code=REASON_CONFIG_SCHEMA_INVALID
    )
    context = resolve_repo_relative(
        root, base_dir, context_rel, code=REASON_CONFIG_SCHEMA_INVALID
    )
    if not dockerfile.is_file():
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            f"dockerfile not found: {dockerfile_rel}",
        )
    if not context.is_dir():
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            f"build context not found: {context_rel}",
        )

    dockerignore = context / ".dockerignore"
    patterns = load_dockerignore_patterns(dockerignore)
    text = dockerfile.read_text(encoding="utf-8")
    checks: list[CopySourceCheck] = []
    for instruction, src in parse_local_copy_sources(text):
        # Sources are relative to the build context for typical Cursor/ci usage.
        src_norm = src.replace("\\", "/").lstrip("./")
        abs_src = (context / src_norm).resolve()
        try:
            abs_src.relative_to(context.resolve())
        except ValueError:
            exists = False
            excluded = True
            matching = "path-escape"
        else:
            exists = abs_src.exists()
            excluded, matching = dockerignore_excludes(src_norm, patterns)
        checks.append(
            CopySourceCheck(
                instruction=instruction,
                source=src_norm,
                exists=exists,
                excluded_by_dockerignore=excluded,
                matching_pattern=matching,
            )
        )

    return DockerfileContextReport(
        config_path=str(path.relative_to(root)).replace("\\", "/"),
        dockerfile_path=str(dockerfile.relative_to(root)).replace("\\", "/"),
        context_path=str(context.relative_to(root)).replace("\\", "/") or ".",
        dockerignore_path=(
            str(dockerignore.relative_to(root)).replace("\\", "/")
            if dockerignore.is_file()
            else None
        ),
        sources=tuple(checks),
    )


def assert_cursor_dockerfile_context_ok(
    repo_root: Path,
    *,
    config_path: Path | None = None,
) -> DockerfileContextReport:
    report = check_cursor_dockerfile_context(repo_root, config_path=config_path)
    if report.ok:
        return report
    details = "; ".join(
        f"{item.instruction} {item.source} "
        f"(exists={item.exists}, excluded={item.excluded_by_dockerignore}, "
        f"pattern={item.matching_pattern!r})"
        for item in report.failures
    )
    raise DispatchError(
        REASON_CONFIG_SCHEMA_INVALID,
        f"cursor Dockerfile build-context contract failed: {details}",
    )


def format_report(report: DockerfileContextReport) -> str:
    lines = [
        f"config={report.config_path}",
        f"dockerfile={report.dockerfile_path}",
        f"context={report.context_path}",
        f"dockerignore={report.dockerignore_path or '(none)'}",
        f"ok={report.ok}",
    ]
    for item in report.sources:
        lines.append(
            f"  {item.instruction} {item.source}: "
            f"exists={item.exists} excluded={item.excluded_by_dockerignore} "
            f"pattern={item.matching_pattern!r} ok={item.ok}"
        )
    return "\n".join(lines)


def iter_failure_messages(report: DockerfileContextReport) -> Iterable[str]:
    for item in report.failures:
        yield (
            f"{item.instruction} source {item.source!r} "
            f"exists={item.exists} excluded={item.excluded_by_dockerignore} "
            f"pattern={item.matching_pattern!r}"
        )
