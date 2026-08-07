"""CLI for governed CDB worktree path resolution and creation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from tools.worktrees.create import create_worktree, plan_worktree_create
from tools.worktrees.policy import (
    validate_main_checkout_path,
    validate_new_worktree_path,
)
from tools.worktrees.reconcile import (
    DEFAULT_MAIN_CHECKOUT,
    reconcile_inventory,
)
from tools.worktrees.resolve import build_worktree_path, resolve_worktree_root

SUCCESS = 0
HOLD = 1
USAGE = 2


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")


def _emit(payload: object) -> None:
    if is_dataclass(payload) and not isinstance(payload, type):
        payload = asdict(payload)
    print(
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            default=_json_default,
        )
    )


def cmd_resolve_root(_args: argparse.Namespace) -> int:
    result = resolve_worktree_root()
    _emit(result)
    return SUCCESS if result.status in {"PASS", "SKIP"} else HOLD


def cmd_resolve_path(args: argparse.Namespace) -> int:
    resolved = resolve_worktree_root()
    if resolved.root is None:
        _emit(resolved)
        return HOLD
    try:
        path = build_worktree_path(resolved.root, args.repository, args.name)
    except ValueError as exc:
        _emit({"status": "FAIL", "reason_codes": [str(exc)]})
        return HOLD
    _emit(
        {
            "status": "PASS",
            "root": str(resolved.root),
            "path": str(path),
            "repository": args.repository,
            "worktree_name": args.name,
        }
    )
    return SUCCESS


def cmd_validate_path(args: argparse.Namespace) -> int:
    if args.purpose == "main_checkout":
        result = validate_main_checkout_path(args.path)
    else:
        result = validate_new_worktree_path(args.path)
    _emit(result)
    return SUCCESS if result.status in {"PASS", "SKIP"} else HOLD


def cmd_create(args: argparse.Namespace) -> int:
    plan = plan_worktree_create(
        repository=args.repository,
        worktree_name=args.name,
        ref=args.ref,
        branch=args.branch,
    )
    if plan.status != "PASS":
        _emit(plan)
        return HOLD
    result = create_worktree(
        plan,
        dry_run=not args.execute,
        repo_dir=args.repo_dir,
    )
    _emit(result)
    return SUCCESS if result.status == "PASS" else HOLD


def cmd_reconcile(args: argparse.Namespace) -> int:
    import subprocess

    porcelain_text: str | None = None
    if args.from_git:
        completed = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            cwd=args.repo_dir,
        )
        if completed.returncode != 0:
            _emit(
                {
                    "status": "FAIL",
                    "reason_codes": ["GIT_WORKTREE_LIST_FAILED"],
                    "stderr": completed.stderr,
                }
            )
            return HOLD
        porcelain_text = completed.stdout
    elif args.inventory:
        porcelain_text = Path(args.inventory).read_text(encoding="utf-8")
    elif not args.scan_roots:
        _emit(
            {
                "status": "FAIL",
                "reason_codes": ["USAGE"],
                "error": "need --from-git, --inventory, and/or --scan-roots",
            }
        )
        return USAGE

    scan_roots = list(args.scan_roots) if args.scan_roots else None
    include_fs = bool(args.scan_roots)
    facts_list, classified = reconcile_inventory(
        porcelain_text=porcelain_text,
        scan_roots=scan_roots,
        enrich=bool(args.enrich),
        main_checkout=args.main_checkout,
        base_ref=args.base_ref,
        include_fs_scan=include_fs,
    )
    rows = []
    for fact, result in zip(facts_list, classified, strict=True):
        row = asdict(result)
        row["facts"] = asdict(fact)
        rows.append(row)
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("classification") or "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    _emit(
        {
            "status": "PASS",
            "count": len(rows),
            "counts": counts,
            "enrich": bool(args.enrich),
            "results": rows,
        }
    )
    return SUCCESS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.worktrees",
        description="Governed CDB worktree root resolution and creation (Y:-only on Windows).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_root = sub.add_parser("resolve-root", help="Resolve CDB_WORKTREE_ROOT")
    p_root.set_defaults(func=cmd_resolve_root)

    p_path = sub.add_parser("resolve-path", help="Build canonical worktree path")
    p_path.add_argument("--repository", required=True)
    p_path.add_argument("--name", required=True)
    p_path.set_defaults(func=cmd_resolve_path)

    p_val = sub.add_parser("validate-path", help="Validate a path against policy")
    p_val.add_argument("--path", required=True)
    p_val.add_argument(
        "--purpose",
        choices=("create", "main_checkout"),
        default="create",
    )
    p_val.set_defaults(func=cmd_validate_path)

    p_create = sub.add_parser("create", help="Plan/create worktree (dry-run default)")
    p_create.add_argument("--repository", required=True)
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--ref", default="origin/main")
    p_create.add_argument("--branch", default=None)
    p_create.add_argument("--repo-dir", default=None)
    p_create.add_argument(
        "--execute",
        action="store_true",
        help="Actually run git worktree add (default is dry-run)",
    )
    p_create.set_defaults(func=cmd_create)

    p_rec = sub.add_parser("reconcile", help="Classify legacy worktrees (read-only)")
    p_rec.add_argument("--from-git", action="store_true")
    p_rec.add_argument("--inventory", default=None)
    p_rec.add_argument("--repo-dir", default=None)
    p_rec.add_argument(
        "--enrich",
        action="store_true",
        help="Probe dirty/unpushed/merged/drive (still read-only; no delete)",
    )
    p_rec.add_argument(
        "--scan-roots",
        nargs="*",
        default=None,
        help="Also discover legacy FS paths under these roots (e.g. D:\\Dev\\Workspaces\\Repos)",
    )
    p_rec.add_argument(
        "--main-checkout",
        default=DEFAULT_MAIN_CHECKOUT,
        help="Path treated as main checkout (never OBSOLETE_REMOVE)",
    )
    p_rec.add_argument(
        "--base-ref",
        default="origin/main",
        help="Base ref for merged/unpushed probes",
    )
    p_rec.set_defaults(func=cmd_reconcile)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
