"""Read-only legacy worktree classification (no delete/migrate)."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path, PureWindowsPath

from tools.worktrees import codes
from tools.worktrees.resolve import windows_drive_letter

_ISSUE_RE = re.compile(
    r"(?:issue[-_]?|gh[-_]?|#)(\d{3,5})\b|\b(\d{3,5})(?=[-_]|$)",
    re.IGNORECASE,
)

# Primary Windows main checkout path for CDB (not a migration target).
DEFAULT_MAIN_CHECKOUT = r"D:\Dev\Workspaces\Repos\Claire_de_Binare"

DEFAULT_SCAN_ROOTS: tuple[str, ...] = (r"D:\Dev\Workspaces\Repos",)

GitRunner = Callable[[Sequence[str], str | None], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class LegacyWorktreeFacts:
    path: str
    branch: str | None = None
    head: str | None = None
    is_main_checkout: bool = False
    dirty: bool | None = None
    unpushed: bool | None = None
    locked: bool | None = None
    path_exists: bool = True
    on_windows_legacy_drive: bool | None = None
    merged_into_base: bool | None = None
    active_issue: str | None = None
    prunable: bool = False


@dataclass(frozen=True)
class ReconcileResult:
    classification: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    path: str = ""
    notes: str = ""


def classify_legacy_worktree(facts: LegacyWorktreeFacts) -> ReconcileResult:
    """Classify a discovered worktree using fail-closed heuristics.

    Never deletes or migrates. Main checkout is never treated as a removal
    candidate.
    """
    if facts.is_main_checkout:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.MAIN_CHECKOUT_ALLOWED,),
            path=facts.path,
            notes="Main checkout is allowed on D:; not a legacy migration target.",
        )

    if (facts.branch or "").lower() in {"main", "master"}:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.MAIN_CHECKOUT_ALLOWED,),
            path=facts.path,
            notes="Worktree has main/master checked out; never auto-remove.",
        )

    if not facts.path_exists:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.UNCLEAR_HOLD,),
            path=facts.path,
            notes="Path missing; do not delete without evidence.",
        )

    if facts.locked is True:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.UNCLEAR_HOLD,),
            path=facts.path,
            notes="Worktree lock present.",
        )

    if facts.dirty is True:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.UNCLEAR_HOLD,),
            path=facts.path,
            notes="Dirty worktree; STOP.",
        )

    if facts.unpushed is True and facts.active_issue:
        return ReconcileResult(
            classification=codes.NEEDED_FOLLOWUP_ISSUE,
            reason_codes=(codes.NEEDED_FOLLOWUP_ISSUE,),
            path=facts.path,
            notes="Unpushed work with known issue; capture follow-up before cleanup.",
        )

    if facts.unpushed is True:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.UNCLEAR_HOLD,),
            path=facts.path,
            notes="Unpushed commits without clear ownership; STOP.",
        )

    if facts.dirty is None or facts.unpushed is None:
        return ReconcileResult(
            classification=codes.UNCLEAR_HOLD,
            reason_codes=(codes.UNCLEAR_HOLD,),
            path=facts.path,
            notes="Incomplete dirty/unpushed evidence.",
        )

    # Clean from here (dirty is False, unpushed is False)
    if facts.prunable or facts.merged_into_base is True:
        return ReconcileResult(
            classification=codes.OBSOLETE_REMOVE,
            reason_codes=(codes.OBSOLETE_REMOVE,),
            path=facts.path,
            notes="Clean and merged/prunable; candidate for controlled removal.",
        )

    if facts.active_issue and facts.merged_into_base is False:
        return ReconcileResult(
            classification=codes.NEEDED_QUICK_FINISH,
            reason_codes=(codes.NEEDED_QUICK_FINISH,),
            path=facts.path,
            notes="Clean, unmerged, active issue — consider quick finish then cleanup.",
        )

    if facts.on_windows_legacy_drive is True and facts.merged_into_base is False:
        return ReconcileResult(
            classification=codes.NEEDED_FOLLOWUP_ISSUE,
            reason_codes=(codes.NEEDED_FOLLOWUP_ISSUE,),
            path=facts.path,
            notes="Legacy C:/D: path with unclear remaining work; open/dedupe follow-up.",
        )

    return ReconcileResult(
        classification=codes.UNCLEAR_HOLD,
        reason_codes=(codes.UNCLEAR_HOLD,),
        path=facts.path,
        notes="Insufficient evidence for safe action.",
    )


def inventory_from_porcelain(porcelain_text: str) -> list[LegacyWorktreeFacts]:
    """Parse ``git worktree list --porcelain`` into facts (path/branch/head only)."""
    entries: list[LegacyWorktreeFacts] = []
    path: str | None = None
    head: str | None = None
    branch: str | None = None
    prunable = False
    locked = False

    def flush() -> None:
        nonlocal path, head, branch, prunable, locked
        if path is None:
            return
        entries.append(
            LegacyWorktreeFacts(
                path=path,
                branch=branch,
                head=head,
                path_exists=True,
                prunable=prunable,
                locked=locked if locked else None,
            )
        )
        path = None
        head = None
        branch = None
        prunable = False
        locked = False

    for raw_line in porcelain_text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if line.startswith("worktree "):
            flush()
            path = line[len("worktree ") :]
        elif line.startswith("HEAD "):
            head = line[len("HEAD ") :]
        elif line.startswith("branch "):
            ref = line[len("branch ") :]
            branch = ref.rsplit("/", 1)[-1] if ref else None
        elif line == "detached":
            branch = None
        elif line.startswith("prunable"):
            prunable = True
        elif line.startswith("locked"):
            locked = True
    flush()
    return entries


def _default_git_runner(
    args: Sequence[str], cwd: str | None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )


def _norm_path_key(path: str | Path) -> str:
    text = str(path).replace("/", "\\").rstrip("\\")
    return os.path.normcase(text)


def infer_active_issue(branch: str | None, path: str | None = None) -> str | None:
    """Best-effort issue id from branch or path segment (fail-soft)."""
    for raw in (branch, Path(path).name if path else None):
        if not raw:
            continue
        match = _ISSUE_RE.search(raw.replace("\\", "/"))
        if match:
            return match.group(1) or match.group(2)
    return None


def is_legacy_windows_drive(path: str | Path) -> bool | None:
    drive = windows_drive_letter(path)
    if drive is None:
        return None
    return drive in {"C", "D"}


def is_main_checkout_path(
    path: str | Path,
    *,
    main_checkout: str = DEFAULT_MAIN_CHECKOUT,
) -> bool:
    return _norm_path_key(path) == _norm_path_key(main_checkout)


def discover_legacy_fs_paths(
    scan_roots: Sequence[str] | None = None,
    *,
    main_checkout: str = DEFAULT_MAIN_CHECKOUT,
) -> list[str]:
    """Discover likely legacy worktree/clone directories under scan roots.

    Only returns directories that look like git checkouts (``.git`` file or dir).
    """
    roots = list(scan_roots) if scan_roots is not None else list(DEFAULT_SCAN_ROOTS)
    found: list[str] = []
    seen: set[str] = set()

    def _add(candidate: Path) -> None:
        if not candidate.is_dir():
            return
        git_meta = candidate / ".git"
        if not git_meta.exists():
            return
        key = _norm_path_key(candidate)
        if key in seen:
            return
        if is_main_checkout_path(candidate, main_checkout=main_checkout):
            return
        seen.add(key)
        found.append(str(candidate))

    for root_raw in roots:
        root = Path(root_raw)
        if not root.is_dir():
            continue
        # Sibling clones / cdb-wt-* under the workspace root
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            name = child.name
            if name.startswith("cdb-wt-") or name.startswith("Claire_de_Binare-"):
                _add(child)
        # Nested .worktrees under main checkout
        nested = Path(main_checkout) / ".worktrees"
        if nested.is_dir():
            try:
                for child in nested.iterdir():
                    _add(child)
            except OSError:
                pass
        # Also allow scan_root/.worktrees
        alt_nested = root / ".worktrees"
        if alt_nested.is_dir() and _norm_path_key(alt_nested) != _norm_path_key(nested):
            try:
                for child in alt_nested.iterdir():
                    _add(child)
            except OSError:
                pass
    return found


def _git_ok(proc: subprocess.CompletedProcess[str]) -> bool:
    return proc.returncode == 0


def enrich_worktree_facts(
    facts: LegacyWorktreeFacts,
    *,
    main_checkout: str = DEFAULT_MAIN_CHECKOUT,
    base_ref: str = "origin/main",
    git_runner: GitRunner | None = None,
) -> LegacyWorktreeFacts:
    """Enrich porcelain facts with dirty/unpushed/merged/drive evidence.

    Fail-closed: unknown probes leave dirty/unpushed/merged as None so
    classification becomes UNCLEAR_HOLD.
    """
    run = git_runner or _default_git_runner
    path = facts.path
    exists = Path(path).exists()
    legacy_drive = is_legacy_windows_drive(path)
    main = is_main_checkout_path(path, main_checkout=main_checkout)
    issue = facts.active_issue or infer_active_issue(facts.branch, path)

    if not exists:
        return replace(
            facts,
            path_exists=False,
            is_main_checkout=main,
            on_windows_legacy_drive=legacy_drive,
            active_issue=issue,
            dirty=None,
            unpushed=None,
            merged_into_base=None,
        )

    dirty: bool | None = None
    unpushed: bool | None = None
    merged: bool | None = None

    status = run(
        ["git", "-C", path, "status", "--porcelain=v1", "--untracked-files=all"],
        path,
    )
    if _git_ok(status):
        dirty = bool(status.stdout.strip())
    # else leave dirty=None (fail-closed)

    # Unpushed relative to upstream if present; else commits not in base_ref.
    ahead_upstream = run(
        ["git", "-C", path, "rev-list", "--count", "@{upstream}..HEAD"],
        path,
    )
    if _git_ok(ahead_upstream):
        try:
            unpushed = int(ahead_upstream.stdout.strip() or "0") > 0
        except ValueError:
            unpushed = None
    else:
        ahead_base = run(
            ["git", "-C", path, "rev-list", "--count", f"{base_ref}..HEAD"],
            path,
        )
        if _git_ok(ahead_base):
            try:
                unpushed = int(ahead_base.stdout.strip() or "0") > 0
            except ValueError:
                unpushed = None
        else:
            # Detached / no base: treat unknown as fail-closed unless prunable.
            unpushed = None if not facts.prunable else False

    # Merged into base: ancestry OR identical trees (squash equivalence).
    ancestor = run(
        ["git", "-C", path, "merge-base", "--is-ancestor", "HEAD", base_ref],
        path,
    )
    if _git_ok(ancestor):
        merged = True
    else:
        head_tree = run(["git", "-C", path, "rev-parse", "HEAD^{tree}"], path)
        base_tree = run(["git", "-C", path, "rev-parse", f"{base_ref}^{{tree}}"], path)
        if (
            _git_ok(head_tree)
            and _git_ok(base_tree)
            and head_tree.stdout.strip()
            and head_tree.stdout.strip() == base_tree.stdout.strip()
        ):
            merged = True
        elif _git_ok(head_tree) and _git_ok(base_tree):
            # Reachable comparison succeeded but trees differ → not merged.
            merged = False
        elif facts.prunable:
            # Git marked prunable; treat as merged/obsolete candidate when clean.
            merged = True
        else:
            merged = None

    return replace(
        facts,
        path_exists=True,
        is_main_checkout=main,
        on_windows_legacy_drive=legacy_drive if legacy_drive is not None else False,
        active_issue=issue,
        dirty=dirty,
        unpushed=unpushed,
        merged_into_base=merged,
    )


def merge_fact_lists(
    *lists: Sequence[LegacyWorktreeFacts],
) -> list[LegacyWorktreeFacts]:
    """Deduplicate facts by normalized path (first wins)."""
    out: list[LegacyWorktreeFacts] = []
    seen: set[str] = set()
    for group in lists:
        for item in group:
            key = _norm_path_key(item.path)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def facts_from_discovered_paths(
    paths: Sequence[str],
) -> list[LegacyWorktreeFacts]:
    """Build minimal facts for FS-discovered paths (enriched later)."""
    rows: list[LegacyWorktreeFacts] = []
    for raw in paths:
        path = str(PureWindowsPath(raw)) if windows_drive_letter(raw) else str(raw)
        branch: str | None = None
        head: str | None = None
        # Light porcelain substitute: try symbolic-ref / rev-parse without failing hard.
        # Full enrichment fills dirty/unpushed/merged.
        rows.append(
            LegacyWorktreeFacts(
                path=path,
                branch=branch,
                head=head,
                path_exists=True,
            )
        )
    return rows


def reconcile_inventory(
    *,
    porcelain_text: str | None = None,
    scan_roots: Sequence[str] | None = None,
    enrich: bool = False,
    main_checkout: str = DEFAULT_MAIN_CHECKOUT,
    base_ref: str = "origin/main",
    include_fs_scan: bool = False,
    git_runner: GitRunner | None = None,
) -> tuple[list[LegacyWorktreeFacts], list[ReconcileResult]]:
    """Build inventory + classifications (read-only)."""
    registered = (
        inventory_from_porcelain(porcelain_text) if porcelain_text is not None else []
    )
    discovered: list[LegacyWorktreeFacts] = []
    if include_fs_scan:
        paths = discover_legacy_fs_paths(scan_roots, main_checkout=main_checkout)
        # Skip paths already in registered list
        registered_keys = {_norm_path_key(f.path) for f in registered}
        extra = [p for p in paths if _norm_path_key(p) not in registered_keys]
        discovered = facts_from_discovered_paths(extra)

    combined = merge_fact_lists(registered, discovered)
    if enrich:
        combined = [
            enrich_worktree_facts(
                f,
                main_checkout=main_checkout,
                base_ref=base_ref,
                git_runner=git_runner,
            )
            for f in combined
        ]
        # Fill branch/head for FS-only entries when enriching
        run = git_runner or _default_git_runner
        filled: list[LegacyWorktreeFacts] = []
        for f in combined:
            if f.branch is not None and f.head is not None:
                filled.append(f)
                continue
            if not f.path_exists:
                filled.append(f)
                continue
            head_proc = run(["git", "-C", f.path, "rev-parse", "HEAD"], f.path)
            branch_proc = run(
                ["git", "-C", f.path, "symbolic-ref", "--short", "-q", "HEAD"],
                f.path,
            )
            head = head_proc.stdout.strip() if _git_ok(head_proc) else f.head
            branch = (
                branch_proc.stdout.strip()
                if _git_ok(branch_proc) and branch_proc.stdout.strip()
                else f.branch
            )
            issue = f.active_issue or infer_active_issue(branch, f.path)
            filled.append(replace(f, head=head, branch=branch, active_issue=issue))
        combined = filled

    results = [classify_legacy_worktree(f) for f in combined]
    return combined, results
