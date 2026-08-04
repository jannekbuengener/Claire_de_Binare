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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow

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

# Canonical Owner allowlist (repository governance / human gate). Case-sensitive
# exact match after rejecting non-ASCII / confusable logins.
AUTHORIZING_OWNER_ALLOWLIST = frozenset({"jannekbuengener"})

# Fenced JSON marker for GitHub Owner-GO comments.
GO_FENCE_START = "```cdb.sensitivity_campaign_execution_authorization.v1"
GO_FENCE_END = "```"

# Sentinel marker documenting an explicit revocation of the fenced GO block by
# the authorizing owner. Presence anywhere in the comment body (case-sensitive)
# fails the parse fail-closed even if a fenced block is still present.
REVOKE_MARKER = "REVOKED_CAMPAIGN_EXECUTION_CONTRACT_DEFECT"

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

_ISSUE_URL_RE = re.compile(
    r"^https://api\.github\.com/repos/[^/\s]+/[^/\s]+/issues/(\d+)$"
)
_ASCII_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

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


def _reject_duplicate_object_pairs(
    pairs: Sequence[tuple[str, Any]],
) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise SensitivityAuthorizationError(
                "AUTH_GO_BLOCK_DUPLICATE_KEY", f"duplicate JSON key {key!r}"
            )
        seen[key] = value
    return seen


def _strict_json_loads(raw: str) -> Any:
    """Parse JSON fail-closed: reject duplicate keys and non-object roots later."""
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_object_pairs)
    except SensitivityAuthorizationError:
        raise
    except json.JSONDecodeError as exc:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_JSON_INVALID", str(exc)
        ) from exc


def validate_authorization_payload(
    payload: Mapping[str, Any],
    *,
    schema: Mapping[str, Any] | None = None,
    now_utc: datetime | None = None,
) -> None:
    if jsonschema is None:
        raise SensitivityAuthorizationError(
            "AUTH_SCHEMA_ENGINE_MISSING", "jsonschema required"
        )
    resolved = dict(schema) if schema is not None else load_authorization_schema()
    format_checker = getattr(jsonschema, "FormatChecker", None)
    checker = format_checker() if format_checker is not None else None
    try:
        if checker is not None:
            jsonschema.validate(
                instance=dict(payload),
                schema=resolved,
                format_checker=checker,
            )
        else:
            jsonschema.validate(instance=dict(payload), schema=resolved)
    except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
        raise SensitivityAuthorizationError(
            "AUTH_PAYLOAD_SCHEMA_INVALID", exc.message
        ) from exc

    # Schema defaults must not authorize; require explicit capability/ban fields.
    if "granted_capabilities" not in payload:
        raise SensitivityAuthorizationError("AUTH_GRANTED_CAPABILITIES_MISSING")
    granted = payload.get("granted_capabilities")
    if granted != ["campaign_execution"]:
        raise SensitivityAuthorizationError(
            "AUTH_GRANTED_CAPABILITIES_INVALID", str(granted)
        )
    if "absolute_bans_unchanged" not in payload:
        raise SensitivityAuthorizationError("AUTH_ABSOLUTE_BANS_FIELD_MISSING")
    if payload.get("absolute_bans_unchanged") is not True:
        raise SensitivityAuthorizationError("AUTH_ABSOLUTE_BANS_RELAXED")

    _assert_expires_at_valid(payload.get("expires_at_utc"), now_utc=now_utc)


def _parse_expires_at(raw: Any) -> datetime | None:
    """Parse ``expires_at_utc``. Returns None when null; raises on malformed input."""
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise SensitivityAuthorizationError("AUTH_EXPIRES_AT_INVALID", "non-string")
    value = raw.strip()
    try:
        if value.endswith("Z"):
            exp = datetime.fromisoformat(value[:-1] + "+00:00")
        else:
            exp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SensitivityAuthorizationError(
            "AUTH_EXPIRES_AT_INVALID", str(exc)
        ) from exc
    if exp.tzinfo is None:
        raise SensitivityAuthorizationError("AUTH_EXPIRES_AT_NOT_TIMEZONE_AWARE", value)
    return exp


def _assert_expires_at_valid(
    expires_at_utc: Any,
    *,
    now_utc: datetime | None = None,
) -> None:
    """Clock source: core.utils.clock.utcnow unless injected for tests."""
    exp = _parse_expires_at(expires_at_utc)
    if exp is None:
        return
    now = now_utc if now_utc is not None else cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if now.astimezone(UTC) >= exp.astimezone(UTC):
        raise SensitivityAuthorizationError("AUTH_GO_EXPIRED", str(expires_at_utc))


def assert_authorization_not_expired_for_next_attempt(
    expires_at_utc: Any,
    *,
    now_utc: datetime | None = None,
) -> None:
    """Fail-closed pre-attempt gate: refuse to start a new run when expired.

    Called before every primary / retry / reproduction attempt so a long-running
    campaign cannot cross a live expiry mid-flight. ``null`` expiry is allowed.
    """
    exp = _parse_expires_at(expires_at_utc)
    if exp is None:
        return
    now = now_utc if now_utc is not None else cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if now.astimezone(UTC) >= exp.astimezone(UTC):
        raise SensitivityAuthorizationError(
            "AUTHORIZATION_EXPIRED_BEFORE_NEXT_ATTEMPT",
            str(expires_at_utc),
        )


def assert_authorization_lifetime_covers_budget(
    expires_at_utc: Any,
    resource_budget: Mapping[str, Any],
    *,
    now_utc: datetime | None = None,
) -> None:
    """Assert remaining GO lifetime >= campaign_wall + run_wall seconds.

    A campaign whose GO expiry cannot cover the configured budget is refused
    fail-closed before any side effects. ``null`` expiry is refused for a
    campaign path (finite lifetime required to bound the human gate).
    """
    if resource_budget is None:
        raise SensitivityAuthorizationError("AUTH_LIFETIME_BUDGET_MISSING")
    body = dict(resource_budget)
    try:
        campaign_wall = int(body["max_campaign_wall_time_seconds"])
        run_wall = int(body["max_run_wall_time_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SensitivityAuthorizationError(
            "AUTH_LIFETIME_BUDGET_INVALID", str(exc)
        ) from exc
    required = campaign_wall + run_wall
    if expires_at_utc is None:
        raise SensitivityAuthorizationError(
            "AUTH_EXPIRES_AT_REQUIRED_FOR_CAMPAIGN",
            "finite expires_at_utc required to bound campaign execution",
        )
    exp = _parse_expires_at(expires_at_utc)
    assert exp is not None  # narrows for type checker; None handled above
    now = now_utc if now_utc is not None else cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    remaining = int((exp.astimezone(UTC) - now.astimezone(UTC)).total_seconds())
    if remaining < required:
        raise SensitivityAuthorizationError(
            "AUTH_LIFETIME_INSUFFICIENT_FOR_BUDGET",
            f"remaining={remaining}s required={required}s",
        )


def fingerprint_authorization_payload(payload: Mapping[str, Any]) -> str:
    """Canonical hash over GO payload excluding ephemeral comment metadata drift.

    Includes github_comment_id and authorizing fields; excludes notes-only noise
    is not stripped — notes are part of the bound payload when present.
    """
    body = deepcopy(dict(payload))
    return canonical_hash(body)


def parse_go_payload_from_comment_body(body: str) -> dict[str, Any]:
    """Extract exactly one fenced authorization JSON block from a comment body.

    A body containing the explicit revocation sentinel is rejected fail-closed
    before any JSON parsing.
    """
    raw = body or ""
    if REVOKE_MARKER in raw:
        raise SensitivityAuthorizationError(
            "AUTH_GO_REVOKED",
            "comment body carries REVOKED_CAMPAIGN_EXECUTION_CONTRACT_DEFECT sentinel",
        )
    pattern = re.compile(
        r"```cdb\.sensitivity_campaign_execution_authorization\.v1\s*\n" r"(.*?)\n```",
        re.DOTALL,
    )
    matches = pattern.findall(raw)
    if not matches:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_MISSING",
            "no fenced cdb.sensitivity_campaign_execution_authorization.v1 block",
        )
    if len(matches) > 1:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_AMBIGUOUS", "multiple GO fences in comment"
        )
    # Reject nested fences / trailing payload inside the captured block.
    inner = matches[0]
    if "```" in inner:
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_NESTED_FENCE", "nested markdown fence inside GO block"
        )
    payload = _strict_json_loads(inner)
    if not isinstance(payload, dict):
        raise SensitivityAuthorizationError(
            "AUTH_GO_BLOCK_JSON_INVALID", "root must be object"
        )
    return payload


def normalize_authorizing_login(login: str) -> str:
    """Reject Unicode/confusable logins; require ASCII GitHub login shape."""
    value = str(login or "")
    if not value or not _ASCII_LOGIN_RE.fullmatch(value):
        raise SensitivityAuthorizationError("AUTH_AUTHOR_LOGIN_INVALID", repr(login))
    return value


def assert_author_in_owner_allowlist(login: str) -> str:
    normalized = normalize_authorizing_login(login)
    # Exact allowlist match (case-sensitive) — bots/apps/collabs cannot authorize.
    if normalized not in AUTHORIZING_OWNER_ALLOWLIST:
        raise SensitivityAuthorizationError("AUTH_AUTHOR_NOT_ALLOWLISTED", normalized)
    return normalized


def build_owner_go_comment_body(payload: Mapping[str, Any]) -> str:
    """Render the canonical fenced GO body for a fully bound payload."""
    body = json.dumps(dict(payload), indent=2, sort_keys=True)
    return (
        "Owner GO for #4153 sensitivity campaign.\n\n"
        f"{GO_FENCE_START}\n{body}\n{GO_FENCE_END}\n"
    )


def draft_owner_go_placeholder_body(*, comment_id_placeholder: int = 0) -> str:
    """Non-authorizing draft body used only to obtain a GitHub comment id.

    The placeholder must not validate as a live Owner-GO (comment_id 0 / incomplete).
    Atomic finalize flow:
      1) create comment with this draft
      2) read comment id
      3) build full payload including github_comment_id
      4) update the *same* comment exactly once
      5) live-verify body, updated_at, payload fingerprint, comment id
      6) only the final payload may authorize
    """
    return (
        "DRAFT — not an Owner-GO. Placeholder pending comment-id bind "
        f"(placeholder_id={comment_id_placeholder}).\n"
    )


def parse_issue_number_from_issue_url(issue_url: str) -> int:
    match = _ISSUE_URL_RE.fullmatch(str(issue_url or "").strip())
    if not match:
        raise SensitivityAuthorizationError(
            "AUTH_COMMENT_ISSUE_URL_INVALID", repr(issue_url)
        )
    return int(match.group(1))


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
    issue_url = str(data.get("issue_url") or "")
    live_issue = parse_issue_number_from_issue_url(issue_url)
    if live_issue != issue:
        raise SensitivityAuthorizationError(
            "AUTH_ISSUE_MISMATCH",
            f"fetched_issue={live_issue} expected={issue}",
        )
    return GitHubComment(
        comment_id=int(data.get("id") or 0),
        issue_number=live_issue,
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
    now_utc: datetime | None = None,
    expected_comment_updated_at: str | None = None,
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
    if not comment.updated_at:
        raise SensitivityAuthorizationError("AUTH_COMMENT_UPDATED_AT_MISSING")
    if (
        expected_comment_updated_at is not None
        and comment.updated_at != expected_comment_updated_at
    ):
        raise SensitivityAuthorizationError(
            "AUTH_COMMENT_MUTATED",
            f"live={comment.updated_at} bound={expected_comment_updated_at}",
        )

    payload = parse_go_payload_from_comment_body(comment.body)
    validate_authorization_payload(payload, now_utc=now_utc)

    live_author = assert_author_in_owner_allowlist(comment.author_login)
    expected_login_raw = str(expected.get("authorizing_github_login") or "")
    if not expected_login_raw:
        raise SensitivityAuthorizationError("AUTH_EXPECTED_LOGIN_REQUIRED")
    expected_login = assert_author_in_owner_allowlist(expected_login_raw)
    if live_author != expected_login:
        raise SensitivityAuthorizationError(
            "AUTH_AUTHOR_MISMATCH",
            f"comment_author={live_author} expected={expected_login}",
        )
    payload_login = assert_author_in_owner_allowlist(
        str(payload.get("authorizing_github_login") or "")
    )
    if payload_login != live_author:
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

    auth_fp = fingerprint_authorization_payload(payload)
    return {
        "valid": True,
        "payload": payload,
        "authorization_fingerprint": auth_fp,
        "github_comment_id": comment_id,
        "authorizing_github_login": live_author,
        "comment_updated_at": comment.updated_at,
        "expires_at_utc": payload.get("expires_at_utc"),
        "reason_code": "AUTH_GO_VALID",
        "clock_source": "core.utils.clock.utcnow",
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
        "authorizing_owner_allowlist": sorted(AUTHORIZING_OWNER_ALLOWLIST),
        "notes": (
            "explicit_bans.*=true means forbidden. campaign_execution may be "
            "released only by a live-verified Owner-GO matching "
            f"{AUTH_SCHEMA_VERSION}; absolute bans cannot be relaxed. "
            "Owner allowlist is enforced independently of payload self-claims."
        ),
    }
