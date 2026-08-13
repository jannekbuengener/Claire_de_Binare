"""Deterministic execution window-bank resolution for hh_hl campaigns (#4395).

Exact-SHA git worktrees often lack a local ``artifacts/market_data`` tree.
Prove-dataset can still pass against the parent Claire_de_Binare bank, while
execute defaults to ``repo_root/artifacts/market_data/...`` and fail-closes on
the first missing window.

This module:

* resolves a read-only bank root with locked Batch-A 39 windows present
* asserts availability for preflight / execute (no silent skip)
* optionally creates a worktree junction/symlink to the parent bank
  (no dataset content copy, no mutation of candle files)

Never repairs campaign evidence or Owner-GO state.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from tools.arvp_vacation.sensitivity_campaign_dataset_root import (
    SensitivityDatasetRootError,
    WINDOW_BANK_SUFFIX,
    _pick_window_bank_root,
)
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)

HOLD_WINDOW_BANK_UNAVAILABLE = "HOLD_EXECUTION_WINDOW_BANK_UNAVAILABLE"
HOLD_WINDOW_BANK_LINK_FAILED = "HOLD_EXECUTION_WINDOW_BANK_LINK_FAILED"
HOLD_WINDOW_BANK_LINK_CONFLICT = "HOLD_EXECUTION_WINDOW_BANK_LINK_CONFLICT"

SourceKind = Literal["local", "parent", "env", "link"]


class HhHlExecutionWindowBankError(ValueError):
    """Fail-closed window-bank availability / wiring error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        message = reason_code if not detail else f"{reason_code}:{detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ExecutionWindowBankResolution:
    """Resolved physical bank root (the ``.../BTCUSDT/1m`` directory)."""

    window_bank_root: Path
    source_kind: SourceKind
    window_count: int
    market_data_root: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_bank_root": self.window_bank_root.as_posix(),
            "market_data_root": self.market_data_root.as_posix(),
            "source_kind": self.source_kind,
            "window_count": int(self.window_count),
            "required_window_count": len(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS),
        }


def _module_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def local_market_data_root(repo_root: Path) -> Path:
    return Path(repo_root).resolve() / "artifacts" / "market_data"


def local_window_bank_root(repo_root: Path) -> Path:
    return local_market_data_root(repo_root) / Path(WINDOW_BANK_SUFFIX)


def parent_checkout_root(repo_root: Path) -> Path | None:
    """Return the deterministic parent checkout for known Git worktree layouts."""
    root = Path(repo_root).resolve()
    # Common layout: <checkout>/.worktrees/<wt-name>
    if root.parent.name == ".worktrees":
        return root.parent.parent

    # Governed Windows layout: Y:/Worktrees/<repo>/<worktree>.  A worktree's
    # .git file points to <checkout>/.git/worktrees/<worktree>; derive the
    # checkout from that Git metadata instead of guessing from nearby folders.
    if root.parent.parent.name != "Worktrees":
        return None
    git_file = root / ".git"
    try:
        git_pointer = git_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not git_pointer.startswith("gitdir: "):
        return None
    worktree_git_dir = Path(git_pointer.removeprefix("gitdir: ").strip())
    if not worktree_git_dir.is_absolute():
        worktree_git_dir = git_file.parent / worktree_git_dir
    worktree_git_dir = worktree_git_dir.resolve()
    if (
        worktree_git_dir.parent.name != "worktrees"
        or worktree_git_dir.name != root.name
    ):
        return None
    checkout = worktree_git_dir.parent.parent.parent
    if checkout.name != root.parent.name or not (checkout / ".git").is_dir():
        return None
    return checkout


def _windows_complete(bank: Path) -> bool:
    return all((bank / wid).is_dir() for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)


def _try_pick_bank(candidate: Path, repo_root: Path) -> Path | None:
    try:
        if not candidate.exists() or not candidate.is_dir():
            return None
        bank = _pick_window_bank_root(candidate, Path(repo_root)).resolve()
    except (SensitivityDatasetRootError, OSError):
        return None
    if not _windows_complete(bank):
        return None
    return bank


def _market_data_from_bank(bank: Path) -> Path:
    # .../market_data/window_bank/binance/spot/BTCUSDT/1m → market_data
    return bank.resolve().parents[4]


def resolve_execution_window_bank(
    repo_root: Path | None = None,
) -> ExecutionWindowBankResolution | None:
    """Resolve a complete locked 39-window bank readable for offline replay.

    Preference order (first complete match wins):
    1. ``CDB_WINDOW_BANK_ROOT`` / ``CDB_DATASET_ROOT``
    2. ``repo_root/artifacts/market_data`` (local / junction)
    3. parent Claire_de_Binare checkout ``artifacts/market_data``
    """
    root = (
        Path(repo_root).resolve() if repo_root is not None else _module_project_root()
    )
    candidates: list[tuple[SourceKind, Path]] = []

    env = os.environ.get("CDB_WINDOW_BANK_ROOT") or os.environ.get("CDB_DATASET_ROOT")
    if env:
        candidates.append(("env", Path(env)))

    local_md = local_market_data_root(root)
    candidates.append(("local", local_window_bank_root(root)))
    candidates.append(("local", local_md))

    parent = parent_checkout_root(root)
    if parent is not None:
        parent_md = parent / "artifacts" / "market_data"
        candidates.append(("parent", parent_md / Path(WINDOW_BANK_SUFFIX)))
        candidates.append(("parent", parent_md))

    for kind, cand in candidates:
        bank = _try_pick_bank(cand, root)
        if bank is None:
            continue
        # Junction under local market_data that resolves to parent still reports
        # source_kind=local (operator wiring path is present).
        if kind == "local" and local_md.exists():
            reported: SourceKind = "link" if _is_reparse_point(local_md) else "local"
        else:
            reported = kind
        return ExecutionWindowBankResolution(
            window_bank_root=bank,
            source_kind=reported,
            window_count=len(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS),
            market_data_root=_market_data_from_bank(bank),
        )
    return None


def assert_execution_window_bank_available(
    repo_root: Path | None = None,
) -> ExecutionWindowBankResolution:
    """Fail-closed: required for preflight and production execute."""
    resolved = resolve_execution_window_bank(repo_root)
    if resolved is None:
        root = (
            Path(repo_root).resolve()
            if repo_root is not None
            else _module_project_root()
        )
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_UNAVAILABLE,
            f"no complete locked 39-window bank under {local_window_bank_root(root)} "
            f"or parent checkout artifacts/market_data",
        )
    return resolved


def _is_reparse_point(path: Path) -> bool:
    """True when path is a Windows junction/symlink or POSIX symlink."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return False
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
        GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
        GetFileAttributesW.restype = wintypes.DWORD
        attrs = GetFileAttributesW(str(path))
        if attrs == 0xFFFFFFFF:
            return False
        # FILE_ATTRIBUTE_REPARSE_POINT
        return bool(attrs & 0x400)
    except (AttributeError, OSError, ValueError):
        return False


def ensure_worktree_market_data_link(
    repo_root: Path,
    *,
    parent_market_data: Path | None = None,
) -> Mapping[str, Any]:
    """Create a read-only junction/symlink to the parent market_data tree.

    Does not copy datasets. Does not modify candle content. Refuses to replace
    a real non-empty directory or a link pointing elsewhere.
    """
    root = Path(repo_root).resolve()
    link_path = local_market_data_root(root)
    if parent_market_data is not None:
        target = Path(parent_market_data).resolve()
    else:
        parent = parent_checkout_root(root)
        if parent is None:
            raise HhHlExecutionWindowBankError(
                HOLD_WINDOW_BANK_LINK_FAILED,
                "cannot locate parent Claire_de_Binare checkout",
            )
        target = (parent / "artifacts" / "market_data").resolve()

    if not target.is_dir():
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_LINK_FAILED, f"parent market_data missing: {target}"
        )
    bank = _try_pick_bank(target, root)
    if bank is None:
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_LINK_FAILED,
            "parent market_data is not a complete locked 39-window bank",
        )

    if link_path.exists() or _is_reparse_point(link_path):
        try:
            same = link_path.resolve() == target
        except OSError:
            same = False
        if same and _windows_complete(local_window_bank_root(root)):
            return {
                "ok": True,
                "action": "already_linked",
                "link_path": link_path.as_posix(),
                "target": target.as_posix(),
                "window_bank_root": bank.as_posix(),
                "replays": False,
            }
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_LINK_CONFLICT,
            f"path exists and is not the expected parent link: {link_path}",
        )

    link_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            # Directory junction (no admin required for local volumes).
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if completed.returncode != 0:
                raise HhHlExecutionWindowBankError(
                    HOLD_WINDOW_BANK_LINK_FAILED,
                    (completed.stderr or completed.stdout or "mklink failed").strip(),
                )
        else:
            os.symlink(str(target), str(link_path), target_is_directory=True)
    except OSError as exc:
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_LINK_FAILED, str(exc)
        ) from exc

    if not _windows_complete(local_window_bank_root(root)):
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_LINK_FAILED,
            "link created but locked windows still incomplete under worktree",
        )

    return {
        "ok": True,
        "action": "linked",
        "link_path": link_path.as_posix(),
        "target": target.as_posix(),
        "window_bank_root": bank.as_posix(),
        "replays": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hh_hl_execution_window_bank",
        description="Resolve / assert / link hh_hl execution window bank (#4395)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Execution repo root (default: this checkout)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("resolve", help="Print resolution JSON (ok may be false)")
    sub.add_parser("assert", help="Fail closed unless a complete bank is available")
    p_link = sub.add_parser(
        "ensure-link",
        help="Create worktree artifacts/market_data junction/symlink to parent bank",
    )
    p_link.add_argument(
        "--parent-market-data",
        type=Path,
        default=None,
        help="Optional explicit parent artifacts/market_data path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else _module_project_root()
    )
    try:
        if args.command == "resolve":
            resolved = resolve_execution_window_bank(repo_root)
            payload = {
                "ok": resolved is not None,
                "command": "resolve",
                "replays": False,
                "resolution": None if resolved is None else resolved.as_dict(),
                "reason_code": (
                    None if resolved is not None else HOLD_WINDOW_BANK_UNAVAILABLE
                ),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if resolved is not None else 1
        if args.command == "assert":
            resolved = assert_execution_window_bank_available(repo_root)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "command": "assert",
                        "replays": False,
                        "resolution": resolved.as_dict(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "ensure-link":
            result = ensure_worktree_market_data_link(
                repo_root, parent_market_data=args.parent_market_data
            )
            print(json.dumps(dict(result), indent=2, sort_keys=True))
            return 0
        print(json.dumps({"ok": False, "reason_code": "UNKNOWN_COMMAND"}))
        return 2
    except HhHlExecutionWindowBankError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "command": args.command,
                    "reason_code": exc.reason_code,
                    "detail": str(exc),
                    "replays": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "HOLD_WINDOW_BANK_LINK_CONFLICT",
    "HOLD_WINDOW_BANK_LINK_FAILED",
    "HOLD_WINDOW_BANK_UNAVAILABLE",
    "ExecutionWindowBankResolution",
    "HhHlExecutionWindowBankError",
    "assert_execution_window_bank_available",
    "ensure_worktree_market_data_link",
    "local_market_data_root",
    "local_window_bank_root",
    "main",
    "parent_checkout_root",
    "resolve_execution_window_bank",
]
