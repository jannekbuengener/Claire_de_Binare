"""Repository Canon Guard — local mirror of repository-canon-guard.yml.

Extracted for local Docker CI Phase 1 reuse. The GitHub workflow remains the
inline SSOT until Phase 2 thins it to call this module.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REQUIRED_FOLDERS = (
    "agents",
    "docs",
    "knowledge",
    "knowledge/governance",
    ".github/governance",
)
CREDENTIAL_RE = re.compile(
    r"(BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16})"
)
INCLUDE_PATHS = ("agents", "knowledge", "governance", "docs")
CANON_MARKERS = (
    "Repository `Claire_de_Binare` is the only canonical source",
    "Repository `Claire_de_Binare` ist die einzige kanonische Quelle",
)
LEGACY_RE = re.compile(
    r"([Dd][Oo][Cc][Ss][ _-]?[Hh][Uu][Bb]|"
    r"[Ww][Oo][Rr][Kk][Ii][Nn][Gg][ _-]?[Rr][Ee][Pp][Oo]|"
    r"Claire_de_Binare_[Dd][Oo][Cc][Ss])"
)
LEGACY_EXCLUDES = (
    "artifacts/",
    "docs/archive/",
    "docs/evidence/",
    "docs/governance/status/",
    "knowledge/agent_trust/ledger/",
    "knowledge/archive/",
    "knowledge/context_build/",
    "knowledge/evidence/",
    "knowledge/executions/",
    "knowledge/logs/",
    "knowledge/reports/",
    "knowledge/reviews/",
    "tests/fixtures/",
)


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )


def check_runtime_artifacts(repo_root: Path) -> list[str]:
    result = _git(repo_root, "ls-files")
    bad: list[str] = []
    for path in result.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if re.search(
            r"(^|/)((__pycache__/|\.pytest_cache/|.*\.pyc$|.*\.pyo$|(^|/)logs/))",
            path,
        ):
            bad.append(path)
            continue
        if path.endswith(".log") and not path.startswith("docs/runbooks/evidence/"):
            bad.append(path)
    return sorted(set(bad))


def check_required_folders(repo_root: Path) -> list[str]:
    return [name for name in REQUIRED_FOLDERS if not (repo_root / name).is_dir()]


def check_credential_additions(repo_root: Path) -> list[str]:
    result = _git(repo_root, "diff", "--unified=0", "origin/main", "--", *INCLUDE_PATHS)
    hits: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if CREDENTIAL_RE.search(line):
            hits.append(line)
    return hits


def check_single_repo_canon(repo_root: Path) -> list[str]:
    errors: list[str] = []
    if (repo_root / ".gitmodules").is_file():
        errors.append("A second repository must not be attached as a submodule.")
    canon = repo_root / "docs" / "meta" / "REPOSITORY_CANON.md"
    if not canon.is_file():
        errors.append("Missing docs/meta/REPOSITORY_CANON.md")
        return errors
    text = canon.read_text(encoding="utf-8", errors="replace")
    if not any(marker in text for marker in CANON_MARKERS):
        errors.append("REPOSITORY_CANON.md missing required canon marker sentence")
    for rel in ("AGENTS.md", "agents/AGENTS.md"):
        content = (repo_root / rel).read_text(encoding="utf-8", errors="replace")
        if "docs/meta/REPOSITORY_CANON.md" not in content:
            errors.append(f"{rel} must reference docs/meta/REPOSITORY_CANON.md")
    return errors


def _excluded(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in LEGACY_EXCLUDES)


def check_legacy_terminology(repo_root: Path) -> list[str]:
    text_suffixes = {
        ".md",
        ".py",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".txt",
        ".rst",
        ".ini",
        ".cfg",
        ".ps1",
        ".sh",
    }
    result = _git(repo_root, "ls-files")
    hits: list[str] = []
    for path in result.stdout.splitlines():
        path = path.strip()
        if not path or _excluded(path):
            continue
        if LEGACY_RE.search(path):
            hits.append(f"path:{path}")
        file_path = repo_root / path
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in text_suffixes and file_path.name not in {
            "Makefile",
            "Dockerfile",
            "AGENTS.md",
        }:
            continue
        try:
            if file_path.stat().st_size > 1_000_000:
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, MemoryError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if LEGACY_RE.search(line):
                hits.append(f"{path}:{idx}:{line.strip()}")
                if len(hits) > 50:
                    return hits
    return hits


def main(argv: list[str] | None = None) -> int:
    del argv
    repo_root = Path(__file__).resolve().parents[2]

    bad = check_runtime_artifacts(repo_root)
    if bad:
        print("Found forbidden runtime artifacts tracked in git:")
        print("\n".join(bad))
        return 1

    missing = check_required_folders(repo_root)
    if missing:
        print("Missing required canonical folder(s): " + ", ".join(missing))
        return 1

    secrets = check_credential_additions(repo_root)
    if secrets:
        print("Potential secret-like strings found in changed files (review required):")
        print("\n".join(secrets))
        return 1

    canon_errors = check_single_repo_canon(repo_root)
    if canon_errors:
        print("Repository canon enforcement failed:")
        print("\n".join(canon_errors))
        return 1

    legacy = check_legacy_terminology(repo_root)
    if legacy:
        print(
            "Retired repository terminology must not re-enter canonical files or paths."
        )
        print("\n".join(legacy))
        return 1

    print("OK: repository canon guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
