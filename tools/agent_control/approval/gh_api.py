"""Shared gh api helpers for approval snapshots (#4505)."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def gh_api_json(argv: list[str], *, timeout: int = 60) -> Any:
    """Decode gh api output; use --slurp with --paginate for multi-page collections."""
    cmd = ["gh", *argv]
    if "--paginate" in cmd and "--slurp" not in cmd:
        idx = cmd.index("--paginate")
        cmd = cmd[: idx + 1] + ["--slurp"] + cmd[idx + 1 :]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"gh failed ({result.returncode}): {detail}")
    raw = (result.stdout or "").strip()
    if not raw:
        return None
    return json.loads(raw)


def merge_check_runs_payload(payload: Any) -> list[dict[str, Any]]:
    """Normalize slurped or single-page check-runs responses."""
    if isinstance(payload, list):
        out: list[dict[str, Any]] = []
        for page in payload:
            if isinstance(page, dict):
                runs = page.get("check_runs")
                if isinstance(runs, list):
                    out.extend(item for item in runs if isinstance(item, dict))
        return out
    if isinstance(payload, dict):
        runs = payload.get("check_runs")
        if isinstance(runs, list):
            return [item for item in runs if isinstance(item, dict)]
    return []


def merge_comment_pages(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if not payload:
            return []
        if all(isinstance(item, dict) for item in payload) and any(
            "body" in item for item in payload
        ):
            return [item for item in payload if isinstance(item, dict)]
        out: list[dict[str, Any]] = []
        for page in payload:
            if isinstance(page, list):
                out.extend(item for item in page if isinstance(item, dict))
            elif isinstance(page, dict):
                out.append(page)
        return out
    if isinstance(payload, dict):
        return [payload]
    return []
