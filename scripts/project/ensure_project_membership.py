#!/usr/bin/env python3
# ruff: noqa: E402
"""Ensure Control Board project membership for issue and PR events."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from route_control_board import (
    ControlBoardRouter,
    GhCommandError,
)

TRANSIENT_ERROR_MARKERS: tuple[str, ...] = (
    "<!doctype html>",
    "unicorn! · github",
    "bad gateway",
    "gateway timeout",
    "service unavailable",
    "internal server error",
    "invalid json from gh api",
    "http 502",
    "http 503",
    "http 504",
)


def is_transient_error(message: str) -> bool:
    normalized = message.casefold()
    return any(marker in normalized for marker in TRANSIENT_ERROR_MARKERS)


def ensure_membership(router: ControlBoardRouter) -> int:
    router.log(
        "Project membership ensure start "
        f"(repo={router.repo_full}, project={router.owner}/{router.project_number}, "
        f"mode={'APPLY' if router.apply_changes else 'DRY-RUN'})"
    )
    payload = router.load_event_payload()
    router.load_project_metadata()
    targets = router.collect_targets(payload)
    if not targets:
        router.log("No project membership targets for this event.")
        return 0

    for target in targets:
        if not target.node_id:
            router.log(
                f"SKIP: {target.kind} #{target.number} has no node id and cannot be added."
            )
            continue
        router.ensure_project_item(target.node_id)
        router.log(f"OK: ensured {target.kind} #{target.number} in project.")

    router.log("Project membership ensure complete.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure Control Board project membership for issue/PR events."
    )
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--owner", default=os.getenv("PROJECT_OWNER"))
    parser.add_argument(
        "--project-number",
        type=int,
        default=int(os.getenv("PROJECT_NUMBER", "0") or 0),
    )
    parser.add_argument("--event-name", default=os.getenv("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--event-path", default=os.getenv("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--backoff-seconds", type=int, default=2)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only.")
    mode.add_argument("--apply", action="store_true", help="Apply mutations.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.owner:
        print("Missing --owner (or PROJECT_OWNER).", file=sys.stderr)
        return 2
    if not args.project_number:
        print("Missing --project-number (or PROJECT_NUMBER).", file=sys.stderr)
        return 2
    if not args.repo or "/" not in args.repo:
        print("Missing --repo in '<owner>/<repo>' format.", file=sys.stderr)
        return 2
    if not args.event_name:
        print("Missing --event-name (or GITHUB_EVENT_NAME).", file=sys.stderr)
        return 2
    if not args.event_path:
        print("Missing --event-path (or GITHUB_EVENT_PATH).", file=sys.stderr)
        return 2

    repo_owner, repo_name = args.repo.split("/", maxsplit=1)
    if repo_owner.casefold() != args.owner.casefold():
        print(
            f"Owner mismatch: --owner '{args.owner}' != repo owner '{repo_owner}'.",
            file=sys.stderr,
        )
        return 2

    attempts = max(args.retries, 0) + 1
    for attempt in range(1, attempts + 1):
        router = ControlBoardRouter(
            owner=args.owner,
            repo_name=repo_name,
            project_number=args.project_number,
            event_name=args.event_name,
            event_path=Path(args.event_path),
            apply_changes=bool(args.apply),
        )
        try:
            return ensure_membership(router)
        except GhCommandError as exc:
            if attempt >= attempts or not is_transient_error(str(exc)):
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            delay = args.backoff_seconds * attempt
            print(
                f"WARN: transient GitHub/project API failure on attempt {attempt}/{attempts}: {exc}",
                file=sys.stderr,
            )
            print(f"WARN: retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
