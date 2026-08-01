"""Contract-bound provider work order verification (#4254)."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.paths import normalize_repo_relative_path

DIGEST_PREFIX = "sha256:"
CURSOR_PROVIDER_IDS = frozenset(
    {"cursor-sdk", "cursor-cli", "cursor-cloud-api", "cursor"}
)


def compute_prompt_digest(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{DIGEST_PREFIX}{digest}"


def _path_allowed(prompt_ref: str, allowed_paths: list[str]) -> bool:
    if not allowed_paths:
        return False
    normalized = normalize_repo_relative_path(prompt_ref)
    for raw in allowed_paths:
        path = str(raw)
        if path.endswith("/**"):
            prefix = path[:-3]
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        elif path.endswith("/*"):
            prefix = path[:-2]
            if (
                normalized.startswith(prefix + "/")
                and "/" not in normalized[len(prefix) + 1 :]
            ):
                return True
            if normalized == prefix:
                return True
        elif normalized == path or normalized.startswith(path.rstrip("/") + "/"):
            return True
    return False


def load_prompt_at_commit(
    repo_root: Path,
    prompt_ref: str,
    source_commit: str,
) -> str:
    """Load prompt bytes from git object at source_commit (no working-tree trust)."""
    rel = normalize_repo_relative_path(prompt_ref)
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{source_commit}:{rel}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # pragma: no cover - environment
        raise ContractValidationError(
            "CONTRACT_PROVIDER_WORK_ORDER_GIT",
            f"unable to read prompt via git: {exc}",
        ) from exc
    if completed.returncode != 0:
        raise ContractValidationError(
            "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
            f"prompt_ref {rel!r} not found at commit {source_commit}",
        )
    return completed.stdout


def verify_provider_work_order(
    contract: dict[str, Any],
    *,
    provider_id: str,
    repo_root: Path,
    require_for_live_provider: bool = True,
    prompt_text_override: str | None = None,
    verify_content: bool = True,
) -> tuple[str | None, str | None, str | None]:
    """Verify digest-bound work order.

    Returns (prompt_ref, prompt_digest, prompt_text).
    prompt_text is in-memory only and must never be persisted by callers.
    When verify_content=False (dry-run planning), only structural/path checks run.
    """
    work_order = contract.get("provider_work_order")
    is_live_family = provider_id in CURSOR_PROVIDER_IDS
    if work_order is None:
        if require_for_live_provider and is_live_family:
            raise ContractValidationError(
                "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
                "live Cursor provider dispatch requires provider_work_order",
            )
        return None, None, None

    prompt_ref = normalize_repo_relative_path(str(work_order["prompt_ref"]))
    source_commit = str(work_order["source_commit"])
    claimed = str(work_order["prompt_digest"])
    if not claimed.startswith(DIGEST_PREFIX) or len(claimed) != len(DIGEST_PREFIX) + 64:
        raise ContractValidationError(
            "CONTRACT_PROVIDER_WORK_ORDER_INVALID",
            "prompt_digest must use sha256:<64-hex>",
        )
    allowed = list((contract.get("execution_scope") or {}).get("allowed_paths") or [])
    if not _path_allowed(prompt_ref, allowed):
        raise ContractValidationError(
            "CONTRACT_PROVIDER_WORK_ORDER_PATH",
            f"prompt_ref {prompt_ref!r} outside allowed_paths",
        )

    if not verify_content and prompt_text_override is None:
        return prompt_ref, claimed, None

    if prompt_text_override is not None:
        text = prompt_text_override
    else:
        text = load_prompt_at_commit(repo_root, prompt_ref, source_commit)
    actual = compute_prompt_digest(text)
    if actual != claimed:
        raise ContractValidationError(
            "CONTRACT_PROVIDER_WORK_ORDER_DIGEST",
            "prompt_digest does not match file content at source_commit",
        )
    return prompt_ref, claimed, text
