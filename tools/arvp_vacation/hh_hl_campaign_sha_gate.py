"""hh_hl campaign post-merge SHA live-main gate (#4374).

Fail-closed helpers that bind a FINAL run plan / Execution-GO package to a
*live* ``origin/main`` tip rather than any 40-hex string. The git surface is
fully injectable so unit tests never touch the network: tests pass a
:class:`GitShaResolver` built from fakes, production builds one from
``git`` subprocess calls via :func:`default_git_sha_resolver`.

Guarantees for FINAL planning:

* ``planning_sha`` must be 40-hex, an existing ``commit`` object, and equal to
  the current ``origin/main`` tip — otherwise ``HOLD_POST_MERGE_SHA_NOT_LIVE_MAIN``.
* Re-using the design-bound pre-merge base as "final" is refused with
  ``HOLD_POST_MERGE_MAIN_SHA_REQUIRED``.
* ``execution_sha`` must be an existing commit; the checked-out ``HEAD`` must
  match the authorized ``execution_sha`` at execute entry
  (``HOLD_EXECUTION_SHA_CHECKOUT_DRIFT``).

This module never starts a replay and never mutates git state beyond
``git fetch origin --prune``.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")

FetchFn = Callable[[], None]
MainTipFn = Callable[[], str]
ObjectTypeFn = Callable[[str], str | None]
HeadFn = Callable[[], str]


class HhHlShaGateError(ValueError):
    """Fail-closed SHA-gate error carrying a HOLD reason code."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


@dataclass(frozen=True)
class GitShaResolver:
    """Injectable git surface for the live-main gate.

    ``fetch`` refreshes remotes, ``resolve_main_tip`` returns the current
    ``origin/main`` tip SHA, ``object_type`` returns the git object type for a
    SHA (``commit`` / ``tree`` / ``tag`` / ``None`` when absent), and ``head``
    returns the checked-out ``HEAD`` SHA.
    """

    fetch: FetchFn
    resolve_main_tip: MainTipFn
    object_type: ObjectTypeFn
    head: HeadFn


def _run_git(repo_root: Path, args: list[str]) -> str:
    out = subprocess.check_output(
        ["git", "-C", str(repo_root), *args],
        text=True,
        stderr=subprocess.STDOUT,
    )
    return out.strip()


def default_git_sha_resolver(repo_root: Path | str) -> GitShaResolver:
    """Build a real subprocess-backed resolver (production default)."""
    root = Path(repo_root)

    def _fetch() -> None:
        try:
            _run_git(root, ["fetch", "origin", "--prune"])
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            raise HhHlShaGateError(
                "HOLD_POST_MERGE_MAIN_FETCH_FAILED", str(exc)
            ) from exc

    def _main_tip() -> str:
        try:
            return _run_git(root, ["rev-parse", "origin/main"])
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            raise HhHlShaGateError(
                "HOLD_POST_MERGE_MAIN_TIP_UNRESOLVED", str(exc)
            ) from exc

    def _object_type(sha: str) -> str | None:
        try:
            return _run_git(root, ["cat-file", "-t", sha])
        except subprocess.CalledProcessError:
            return None
        except (FileNotFoundError, OSError) as exc:
            raise HhHlShaGateError("HOLD_POST_MERGE_GIT_UNAVAILABLE", str(exc)) from exc

    def _head() -> str:
        try:
            return _run_git(root, ["rev-parse", "HEAD"])
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            raise HhHlShaGateError(
                "HOLD_EXECUTION_SHA_HEAD_UNRESOLVED", str(exc)
            ) from exc

    return GitShaResolver(
        fetch=_fetch,
        resolve_main_tip=_main_tip,
        object_type=_object_type,
        head=_head,
    )


def assert_planning_sha_format_and_distinct(
    planning_sha: str,
    *,
    design_bound_main_sha: str = "",
) -> str:
    """Format + distinct-from-base checks only (no network).

    Used when no live resolver is supplied (pure planning unit tests). FINAL
    still requires a real, distinct post-merge SHA at the CLI via the live gate.
    """
    sha = str(planning_sha or "").strip()
    if not _SHA40_RE.fullmatch(sha):
        raise HhHlShaGateError(
            "HOLD_POST_MERGE_MAIN_SHA_REQUIRED", f"not 40-hex: {sha!r}"
        )
    if design_bound_main_sha and sha == str(design_bound_main_sha):
        raise HhHlShaGateError(
            "HOLD_POST_MERGE_MAIN_SHA_REQUIRED",
            "planning_sha equals design-bound pre-merge base",
        )
    return sha


def assert_planning_sha_is_live_main(
    planning_sha: str,
    *,
    resolver: GitShaResolver,
    design_bound_main_sha: str = "",
) -> str:
    """FINAL gate: planning_sha must be an existing commit == live origin/main."""
    sha = assert_planning_sha_format_and_distinct(
        planning_sha, design_bound_main_sha=design_bound_main_sha
    )
    resolver.fetch()
    obj_type = resolver.object_type(sha)
    if obj_type != "commit":
        raise HhHlShaGateError(
            "HOLD_POST_MERGE_SHA_NOT_LIVE_MAIN",
            f"planning_sha object_type={obj_type!r} (expected commit)",
        )
    tip = str(resolver.resolve_main_tip() or "").strip()
    if not _SHA40_RE.fullmatch(tip):
        raise HhHlShaGateError(
            "HOLD_POST_MERGE_SHA_NOT_LIVE_MAIN", f"unresolved origin/main tip {tip!r}"
        )
    if sha != tip:
        raise HhHlShaGateError(
            "HOLD_POST_MERGE_SHA_NOT_LIVE_MAIN",
            f"planning_sha={sha} != origin/main tip={tip}",
        )
    return sha


def assert_execution_sha_exists(
    execution_sha: str,
    *,
    resolver: GitShaResolver,
) -> str:
    """``execution_sha`` must be 40-hex and an existing commit object."""
    sha = str(execution_sha or "").strip()
    if not _SHA40_RE.fullmatch(sha):
        raise HhHlShaGateError("HOLD_EXECUTION_SHA_INVALID", f"not 40-hex: {sha!r}")
    if resolver.object_type(sha) != "commit":
        raise HhHlShaGateError("HOLD_EXECUTION_SHA_NOT_A_COMMIT", sha)
    return sha


def assert_checked_out_matches_execution_sha(
    execution_sha: str,
    *,
    resolver: GitShaResolver,
) -> str:
    """At execute entry, checked-out ``HEAD`` must equal the authorized SHA."""
    want = str(execution_sha or "").strip()
    if not _SHA40_RE.fullmatch(want):
        raise HhHlShaGateError("HOLD_EXECUTION_SHA_INVALID", f"not 40-hex: {want!r}")
    head = str(resolver.head() or "").strip()
    if head != want:
        raise HhHlShaGateError(
            "HOLD_EXECUTION_SHA_CHECKOUT_DRIFT",
            f"HEAD={head} authorized_execution_sha={want}",
        )
    return head
