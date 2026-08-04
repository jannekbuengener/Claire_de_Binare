"""Sensitivity campaign Owner-GO authorization (#4153).

Machine-readable external authorization for replay-only campaign_execution.
Does not grant paper/live/echtgeld/orders/auto-start. Does not execute runs.
"""

from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.replay.canonical_json import canonical_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"
AUTH_SCHEMA_PATH = (
    CONTRACTS_DIR / "cdb_sensitivity_campaign_execution_authorization.v1.schema.json"
)
AUTH_SCHEMA_VERSION = "cdb.sensitivity_campaign_execution_authorization.v1"
GO_STATUS = "GO_REPLAY_SENSITIVITY_CAMPAIGN_READY"
RUNNER_CONTRACT_VERSION = "cdb.sensitivity_campaign_runner.v1"
ANALYZER_CONTRACT_VERSION = "cdb.sensitivity_campaign_analyzer.v1"
DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
ISSUE_NUMBER = 4153
MANIFEST_PATH = "config/arvp/sensitivity_campaign_4153_v1.json"
MANIFEST_ID = "arvp-sensitivity-4153-v1"

# Fenced JSON marker for GitHub Owner-GO comments.
GO_FENCE_START = "```cdb.sensitivity_campaign_execution_authorization.v1"
GO_FENCE_END = "```"

ABSOLUTE_BAN_KEYS = frozenset(
    {
        "campaign_execution_auto_start",
        "orders",
        "exchange_execution",
        "testnet_orders",
        "paper",
        "live",
        "echtgeld",
        "balance_usage",
        "position_mutation",
        "risk_limit_mutation",
        "kill_switch_mutation",
        "stop_loss_mutation",
        "holdout",
        "oos",
        "stress",
        "stage_b",
        "promotion",
    }
)
CONDITIONALLY_AUTHORIZABLE = frozenset({"campaign_execution"})

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore


class SensitivityAuthorizationError(ValueError):
    """Fail-closed authorization / GO verification error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        message = reason_code if not detail else f"{reason_code}: {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class GitHubComment:
    comment_id: int
    issue_number: int
    author_login: str
    body: str
    updated_at: str
    repository: str


CommentFetcher = Callable[[str, int, int], GitHubComment]


def load_authorization_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or AUTH_SCHEMA_PATH
    if not schema_path.exists():
        raise SensitivityAuthorizationError("AUTH_SCHEMA_MISSING", str(schema_path))
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SensitivityAuthorizationError("AUTH_SCHEMA_INVALID", "root not object")
    return payload


def validate_authorization_payload(
    payload: Mapping[str, Any],
    *,
    schema: Mapping[str, Any] | None = None,
) -> None:
    if jsonschema is None:
        raise SensitivityAuthorizationError(
            "AUTH_SCHEMA_ENGINE_MISSING", "jsonschema required"
        )
    resolved = dict(schema) if schema is not None else load_authorization_schema()
    try:
        jsonschema.validate(instance=dict(payload), schema=resolved)
    except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
        raise SensitivityAuthorizationError(
            "AUTH_PAYLOAD_SCHEMA_INVALID", exc.message
        ) from exc


def fingerprint_authorization_payload(payload: Mapping[str, Any]) -> str:
    """Canonical hash over GO payload excluding ephemeral comment metadata drift.

    Includes github_comment_id and authorizing fields; excludes notes-only noise
    is not stripped — notes are part of the bound payload when present.
    """
    body = deepcopy(dict(payload))
    return canonical_hash(body)


def parse_go_payload_from_comment_body(body: str) -> dict[str, Any]:
    """Extract exactly one fenced authorization JSON block from a comment body."""
    pattern = re.compile(
        r"```cdb\.sensitivity_campaign_execution_authorization\.v1\s*\n" r"(.*?)\n```",
        re.DOTALL,
    )
    matches = pattern.findall(body or "")
    if not matches:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_MISSING",
            "no fenced cdb.sensitivity_campaign_execution_authorization.v1 block",
        )
    if len(matches) > 1:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_AMBIGUOUS", "multiple GO fences in comment"
        )
    try:
        payload = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_JSON_INVALID", str(exc)
        ) from exc
    if not isinstance(payload, dict):
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_JSON_INVALID", "root must be object"
        )
    return payload


def default_gh_comment_fetcher(
    repository: str, issue: int, comment_id: int
) -> GitHubComment:
    """Live GitHub comment fetch via ``gh api`` (tests should inject a mock)."""
    owner, _, name = repository.partition("/")
    if not owner or not name:
        raise SensitivityAuthorizationError("AUTH_REPO_INVALID", repository)
    endpoint = f"repos/{owner}/{name}/issues/comments/{comment_id}"
    try:
        raw = subprocess.check_output(
            ["gh", "api", endpoint],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise SensitivityAuthorizationError(
            "AUTH_COMMENT_FETCH_FAILED", str(exc)
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SensitivityAuthorizationError(
            "AUTH_COMMENT_FETCH_FAILED", "non-json gh response"
        ) from exc
    author = ((data.get("user") or {}).get("login")) or ""
    # Issue number is not always on comment payload; bind caller-supplied issue.
    return GitHubComment(
        comment_id=int(data.get("id") or 0),
        issue_number=issue,
        author_login=str(author),
        body=str(data.get("body") or ""),
        updated_at=str(data.get("updated_at") or ""),
        repository=repository,
    )


def verify_owner_go_comment(
    *,
    comment_id: int,
    expected: Mapping[str, Any],
    repository: str = DEFAULT_REPO,
    issue: int = ISSUE_NUMBER,
    fetcher: CommentFetcher | None = None,
) -> dict[str, Any]:
    """Load and verify a structured Owner-GO GitHub comment.

    ``expected`` must contain the binding fields that the live payload must match
    (main sha, fingerprints, surface, budget, etc.).
    """
    fetch = fetcher or default_gh_comment_fetcher
    comment = fetch(repository, issue, comment_id)
    if comment.comment_id != comment_id:
        raise SensitivityAuthorizationError(
            "AUTH_COMMENT_ID_MISMATCH",
            f"fetched={comment.comment_id} requested={comment_id}",
        )
    if comment.issue_number != issue:
        raise SensitivityAuthorizationError(
            "AUTH_ISSUE_MISMATCH",
            f"fetched_issue={comment.issue_number} expected={issue}",
        )
    if comment.repository != repository:
        raise SensitivityAuthorizationError(
            "AUTH_REPO_MISMATCH",
            f"fetched={comment.repository} expected={repository}",
        )

    payload = parse_go_payload_from_comment_body(comment.body)
    validate_authorization_payload(payload)

    expected_login = str(expected.get("authorizing_github_login") or "")
    if expected_login and comment.author_login != expected_login:
        raise SensitivityAuthorizationError(
            "AUTH_AUTHOR_MISMATCH",
            f"comment_author={comment.author_login} expected={expected_login}",
        )
    if payload.get("authorizing_github_login") != comment.author_login:
        raise SensitivityAuthorizationError(
            "AUTH_AUTHOR_PAYLOAD_MISMATCH",
            "payload authorizing_github_login != comment author",
        )
    if int(payload.get("github_comment_id") or 0) != comment_id:
        raise SensitivityAuthorizationError(
            "AUTH_COMMENT_ID_PAYLOAD_MISMATCH",
            "payload github_comment_id must equal comment id",
        )
    if int(payload.get("issue") or 0) != issue:
        raise SensitivityAuthorizationError("AUTH_ISSUE_PAYLOAD_MISMATCH")
    if payload.get("repository") != repository:
        raise SensitivityAuthorizationError("AUTH_REPO_PAYLOAD_MISMATCH")
    if payload.get("status") != GO_STATUS:
        raise SensitivityAuthorizationError("AUTH_STATUS_INVALID")
    if payload.get("lr_status") != "NO-GO":
        raise SensitivityAuthorizationError("AUTH_LR_NOT_NO_GO")

    binding_keys = (
        "bound_main_sha",
        "manifest_path",
        "manifest_id",
        "manifest_fingerprint",
        "correctness_baseline_sha",
        "run_plan_fingerprint",
        "runner_contract_version",
        "selection_sha256",
        "window_count",
        "matrix_slots",
        "run_keys",
        "expected_run_count",
        "max_run_count",
        "execution_surface_id",
        "surface_capability_fingerprint",
        "evidence_namespace",
        "analyzer_contract_version",
    )
    for key in binding_keys:
        if key in expected and payload.get(key) != expected[key]:
            raise SensitivityAuthorizationError(
                "AUTH_BINDING_MISMATCH",
                f"{key}: payload={payload.get(key)!r} expected={expected[key]!r}",
            )

    if "strategy_set" in expected and list(payload.get("strategy_set") or []) != list(
        expected["strategy_set"]
    ):
        raise SensitivityAuthorizationError("AUTH_STRATEGY_SET_MISMATCH")

    if "resource_budget" in expected:
        if dict(payload.get("resource_budget") or {}) != dict(
            expected["resource_budget"]
        ):
            raise SensitivityAuthorizationError("AUTH_BUDGET_MISMATCH")

    if "resume_policy" in expected:
        if dict(payload.get("resume_policy") or {}) != dict(expected["resume_policy"]):
            raise SensitivityAuthorizationError("AUTH_RESUME_POLICY_MISMATCH")

    if "reproduction_policy" in expected:
        if dict(payload.get("reproduction_policy") or {}) != dict(
            expected["reproduction_policy"]
        ):
            raise SensitivityAuthorizationError("AUTH_REPRODUCTION_POLICY_MISMATCH")

    granted = list(payload.get("granted_capabilities") or ["campaign_execution"])
    if granted != ["campaign_execution"]:
        raise SensitivityAuthorizationError(
            "AUTH_GRANTED_CAPABILITIES_INVALID", str(granted)
        )
    if payload.get("absolute_bans_unchanged") is False:
        raise SensitivityAuthorizationError("AUTH_ABSOLUTE_BANS_RELAXED")

    auth_fp = fingerprint_authorization_payload(payload)
    return {
        "valid": True,
        "payload": payload,
        "authorization_fingerprint": auth_fp,
        "github_comment_id": comment_id,
        "authorizing_github_login": comment.author_login,
        "comment_updated_at": comment.updated_at,
        "reason_code": "AUTH_GO_VALID",
    }


def assert_absolute_bans_intact(manifest: Mapping[str, Any]) -> None:
    bans = manifest.get("explicit_bans") or {}
    for key in ABSOLUTE_BAN_KEYS:
        if bans.get(key) is not True:
            raise SensitivityAuthorizationError(
                "AUTH_ABSOLUTE_BAN_MISSING", f"explicit_bans.{key} must be true"
            )


def campaign_execution_requires_owner_go(manifest: Mapping[str, Any]) -> bool:
    """True when campaign_execution remains banned without external Owner-GO."""
    bans = manifest.get("explicit_bans") or {}
    policy = manifest.get("authorization_policy") or {}
    if bans.get("campaign_execution") is not True:
        # Missing alias is still treated as banned for v1.1 executable manifests.
        if policy.get("requires_external_owner_go") is True:
            return True
        return True
    return True


def authorization_policy_defaults() -> dict[str, Any]:
    return {
        "schema_version": "cdb.sensitivity_campaign_authorization_policy.v1",
        "requires_external_owner_go": True,
        "authorization_schema": AUTH_SCHEMA_VERSION,
        "conditionally_authorizable_capabilities": sorted(CONDITIONALLY_AUTHORIZABLE),
        "absolute_bans": sorted(ABSOLUTE_BAN_KEYS),
        "notes": (
            "explicit_bans.*=true means forbidden. campaign_execution may be "
            "released only by a live-verified Owner-GO matching "
            f"{AUTH_SCHEMA_VERSION}; absolute bans cannot be relaxed."
        ),
    }
