"""Read-only legacy worktree classification (no delete/migrate)."""

from __future__ import annotations

from dataclasses import dataclass, field

from tools.worktrees import codes


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
