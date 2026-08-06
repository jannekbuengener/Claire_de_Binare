"""hh_hl Campaign Execution-GO authorization (#4374).

Machine-readable external Owner-GO for the replay-only hh_hl campaign. Grants
exactly one capability (``campaign_execution_replay_only``) bound to the frozen
final manifest, run plan, dataset, execution surface, and a finite expiry. It
does not grant paper/live/echtgeld/orders/auto-start and never executes runs.

An :class:`AuthorizationContext` can be constructed *only* from a live-verified
GO via :func:`authorization_context_from_verified_go`; manifest/profile flags
alone are structurally incapable of producing one.
"""

from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"
AUTH_SCHEMA_PATH = (
    CONTRACTS_DIR / "cdb_hh_hl_campaign_execution_authorization.v1.schema.json"
)
AUTH_GO_PACKAGE_SCHEMA_PATH = (
    CONTRACTS_DIR / "cdb_hh_hl_campaign_execution_go_package.v1.schema.json"
)
AUTH_SCHEMA_VERSION = "cdb.hh_hl_campaign_execution_authorization.v1"
GO_STATUS = "GO_HH_HL_CAMPAIGN_EXECUTION"

# Exactly-one authorized action; anything else is a fail-closed HOLD.
AUTHORIZES_EXACT = ("exactly_bound_replay_only_campaign_execution",)
# The Execution-GO must explicitly disclaim every one of these escalations.
REQUIRED_DOES_NOT_AUTHORIZE = (
    "stage_b",
    "oos",
    "stress",
    "paper",
    "live",
    "echtgeld",
    "promotion",
    "merge",
)
MAX_RUN_COUNT = 39

DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
ISSUE_NUMBER = 4374
FINAL_MANIFEST_PATH = "config/arvp/hh_hl_campaign_4374_v1.json"
MANIFEST_ID = "arvp-hh-hl-continuation-4374-prep-v1"
CAMPAIGN_ID = "arvp-hh-hl-continuation-4374-prep-v1"
STRATEGY_ID = "hh_hl_continuation_v1"
ADAPTER_ID = "batch_b_shadow_runner_v1"
GRANTED_CAPABILITY = "campaign_execution_replay_only"
EVIDENCE_NAMESPACE = "artifacts/arvp_campaign/hh_hl_continuation/4374"

GO_FENCE_START = "```cdb.hh_hl_campaign_execution_authorization.v1"
GO_FENCE_END = "```"
REVOKE_MARKER = "REVOKED_HH_HL_CAMPAIGN_EXECUTION_CONTRACT_DEFECT"

AUTHORIZING_OWNER_ALLOWLIST = frozenset({"jannekbuengener"})

# Statuses/schemas that must never satisfy this Execution-GO (fail-closed).
FORBIDDEN_STATUSES = frozenset(
    {
        "GO_REPLAY_SENSITIVITY_CAMPAIGN_READY",
        "GO_HH_HL_CAMPAIGN_DESIGN",
        "GO_HH_HL_CONTINUATION_IMPLEMENTATION",
    }
)

BUDGET_REQUIRED_KEYS = (
    "max_parallelism",
    "max_in_flight_runs",
    "max_attempts_per_run",
    "max_run_wall_time_seconds",
    "max_campaign_wall_time_seconds",
    "max_artifact_bytes",
    "minimum_free_disk_bytes",
    "max_consecutive_failures",
    "max_total_failures",
    "log_retention_days",
)

_ASCII_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA64_RE = re.compile(r"^[0-9a-f]{64}$")
_ISSUE_URL_RE = re.compile(
    r"^https://api\.github\.com/repos/[^/\s]+/[^/\s]+/issues/(\d+)$"
)

# Module-private construction token: only this module may mint an
# AuthorizationContext, and only after a verified live GO.
_AUTH_CTX_TOKEN = object()

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore


class HhHlExecutionAuthorizationError(ValueError):
    """Fail-closed Execution-GO verification error carrying a HOLD reason code."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


@dataclass(frozen=True, slots=True)
class OwnerGoComment:
    comment_id: int
    issue_number: int
    author_login: str
    body: str
    created_at: str
    updated_at: str
    repository: str


OwnerGoFetcher = Callable[[str, int, int], OwnerGoComment]


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Frozen, factory-only proof of a live-verified Owner Execution-GO."""

    _construction_token: object
    schema_version: str
    status: str
    repository: str
    issue: int
    github_comment_id: int
    authorizing_github_login: str
    bound_main_sha: str
    execution_sha: str
    manifest_path: str
    manifest_id: str
    manifest_fingerprint: str
    campaign_id: str
    run_plan_fingerprint: str
    strategy_set: tuple[str, ...]
    adapter_id: str
    expected_run_count: int
    evidence_namespace: str
    execution_surface_id: str
    surface_capability_fingerprint: str
    granted_capabilities: tuple[str, ...]
    resource_budget: Mapping[str, Any]
    resume_policy: Mapping[str, Any]
    expires_at_utc: str
    comment_updated_at: str
    authorization_fingerprint: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self._construction_token is not _AUTH_CTX_TOKEN:
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_GO_CONTEXT_DIRECT_CONSTRUCTION_FORBIDDEN"
            )

    def binds_run_plan(self, run_plan_fingerprint: str) -> bool:
        return self.run_plan_fingerprint == run_plan_fingerprint

    def binds_manifest(self, manifest_fingerprint: str) -> bool:
        return self.manifest_fingerprint == manifest_fingerprint

    def assert_not_expired(self, now_utc: datetime | None = None) -> datetime:
        """Fail-closed re-check of the bound finite expiry at execute entry.

        Must be called on *every* campaign start/resume and immediately before a
        single run is dispatched, so a context that lapses between GO verification
        and execution can never reach the run surface.
        """
        return assert_expiry_finite_and_future(self.expires_at_utc, now_utc=now_utc)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "repository": self.repository,
            "issue": self.issue,
            "github_comment_id": self.github_comment_id,
            "authorizing_github_login": self.authorizing_github_login,
            "bound_main_sha": self.bound_main_sha,
            "execution_sha": self.execution_sha,
            "manifest_path": self.manifest_path,
            "manifest_id": self.manifest_id,
            "manifest_fingerprint": self.manifest_fingerprint,
            "campaign_id": self.campaign_id,
            "run_plan_fingerprint": self.run_plan_fingerprint,
            "strategy_set": list(self.strategy_set),
            "adapter_id": self.adapter_id,
            "expected_run_count": self.expected_run_count,
            "evidence_namespace": self.evidence_namespace,
            "execution_surface_id": self.execution_surface_id,
            "surface_capability_fingerprint": self.surface_capability_fingerprint,
            "granted_capabilities": list(self.granted_capabilities),
            "expires_at_utc": self.expires_at_utc,
            "comment_updated_at": self.comment_updated_at,
            "authorization_fingerprint": self.authorization_fingerprint,
        }


def load_authorization_schema(path: Path | None = None) -> dict[str, Any] | None:
    schema_path = path or AUTH_SCHEMA_PATH
    if not schema_path.exists():
        return None
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_SCHEMA_INVALID", "root not object"
        )
    return payload


def _reject_duplicate_object_pairs(
    pairs: Sequence[tuple[str, Any]],
) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_GO_JSON_INVALID", f"duplicate key {key!r}"
            )
        seen[key] = value
    return seen


def _strict_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_object_pairs)
    except HhHlExecutionAuthorizationError:
        raise
    except json.JSONDecodeError as exc:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_JSON_INVALID", str(exc)
        ) from exc


def parse_execution_go_payload_from_body(body: str) -> dict[str, Any]:
    raw = body or ""
    if REVOKE_MARKER in raw:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_REVOKED", "revocation sentinel present"
        )
    pattern = re.compile(
        r"```cdb\.hh_hl_campaign_execution_authorization\.v1\s*\n(.*?)\n```",
        re.DOTALL,
    )
    matches = pattern.findall(raw)
    if not matches:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_BLOCK_MISSING",
            "no fenced cdb.hh_hl_campaign_execution_authorization.v1 block",
        )
    if len(matches) > 1:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_BLOCK_AMBIGUOUS", "multiple GO fences"
        )
    inner = matches[0]
    if "```" in inner:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_BLOCK_NESTED_FENCE", "nested fence"
        )
    payload = _strict_json_loads(inner)
    if not isinstance(payload, dict):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_JSON_INVALID", "root must be object"
        )
    return payload


def normalize_authorizing_login(login: str) -> str:
    value = str(login or "")
    if not value or not _ASCII_LOGIN_RE.fullmatch(value):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_AUTHOR_LOGIN_INVALID", repr(login)
        )
    return value


def assert_author_in_owner_allowlist(login: str) -> str:
    normalized = normalize_authorizing_login(login)
    if normalized not in AUTHORIZING_OWNER_ALLOWLIST:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_AUTHOR_NOT_ALLOWLISTED", normalized
        )
    return normalized


def _parse_expires_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPIRES_AT_INVALID", "non-string"
        )
    value = raw.strip()
    try:
        if value.endswith("Z"):
            exp = datetime.fromisoformat(value[:-1] + "+00:00")
        else:
            exp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPIRES_AT_INVALID", str(exc)
        ) from exc
    if exp.tzinfo is None:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPIRES_AT_NOT_TZ_AWARE", value
        )
    return exp


def assert_expiry_finite_and_future(
    expires_at_utc: Any,
    *,
    now_utc: datetime | None = None,
) -> datetime:
    """A campaign GO must carry a finite, still-future expiry (fail-closed)."""
    exp = _parse_expires_at(expires_at_utc)
    if exp is None:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPIRES_AT_REQUIRED",
            "finite expires_at_utc required for campaign execution",
        )
    now = now_utc if now_utc is not None else cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if now.astimezone(UTC) >= exp.astimezone(UTC):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPIRED", str(expires_at_utc)
        )
    return exp


def assert_lifetime_covers_budget(
    expires_at_utc: Any,
    resource_budget: Mapping[str, Any],
    *,
    now_utc: datetime | None = None,
) -> None:
    if resource_budget is None:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_BUDGET_MISSING")
    body = dict(resource_budget)
    try:
        campaign_wall = int(body["max_campaign_wall_time_seconds"])
        run_wall = int(body["max_run_wall_time_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_BUDGET_INVALID", str(exc)
        ) from exc
    required = campaign_wall + run_wall
    exp = assert_expiry_finite_and_future(expires_at_utc, now_utc=now_utc)
    now = now_utc if now_utc is not None else cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    remaining = int((exp.astimezone(UTC) - now.astimezone(UTC)).total_seconds())
    if remaining < required:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_LIFETIME_INSUFFICIENT_FOR_BUDGET",
            f"remaining={remaining}s required={required}s",
        )


def fingerprint_execution_authorization_payload(payload: Mapping[str, Any]) -> str:
    return canonical_hash(deepcopy(dict(payload)))


def _validate_budget(budget: Any) -> None:
    if not isinstance(budget, Mapping):
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_BUDGET_INVALID")
    missing = [k for k in BUDGET_REQUIRED_KEYS if k not in budget]
    if missing:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_BUDGET_INCOMPLETE", str(missing)
        )


def _assert_authorizes_scope(payload: Mapping[str, Any]) -> None:
    """``authorizes``/``does_not_authorize`` must be present and exact.

    ``authorizes`` must be exactly the single replay-only capability, and
    ``does_not_authorize`` must explicitly list every escalation in
    :data:`REQUIRED_DOES_NOT_AUTHORIZE`. A missing or truncated disclaimer is a
    HOLD, never an implicit allow.
    """
    authorizes = payload.get("authorizes")
    if list(authorizes or []) != list(AUTHORIZES_EXACT):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_AUTHORIZES_INVALID", str(authorizes)
        )
    dna = payload.get("does_not_authorize")
    if not isinstance(dna, (list, tuple)):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_DOES_NOT_AUTHORIZE_MISSING", str(dna)
        )
    missing = [k for k in REQUIRED_DOES_NOT_AUTHORIZE if k not in dna]
    if missing:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_DOES_NOT_AUTHORIZE_INCOMPLETE", str(missing)
        )


def validate_execution_go_payload(
    payload: Mapping[str, Any],
    *,
    now_utc: datetime | None = None,
) -> None:
    """Structural fail-closed validation independent of expected bindings."""
    status = str(payload.get("status") or "")
    if status in FORBIDDEN_STATUSES:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_WRONG_GO_TYPE", status)
    if payload.get("schema_version") != AUTH_SCHEMA_VERSION:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_SCHEMA_INVALID", str(payload.get("schema_version"))
        )
    if status != GO_STATUS:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_STATUS_INVALID", status
        )
    if payload.get("lr_status") != "NO-GO":
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_LR_NOT_NO_GO")

    granted = payload.get("granted_capabilities")
    if granted != [GRANTED_CAPABILITY]:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_GRANTED_CAPABILITIES_INVALID", str(granted)
        )
    if payload.get("absolute_bans_unchanged") is not True:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_ABSOLUTE_BANS_RELAXED")

    for key, pat in (
        ("bound_main_sha", _SHA40_RE),
        ("execution_sha", _SHA40_RE),
        ("manifest_fingerprint", _SHA64_RE),
        ("run_plan_fingerprint", _SHA64_RE),
        ("surface_capability_fingerprint", _SHA64_RE),
    ):
        if not pat.fullmatch(str(payload.get(key) or "")):
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_GO_FIELD_INVALID", key
            )

    if list(payload.get("strategy_set") or []) != [STRATEGY_ID]:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_STRATEGY_SET_INVALID")
    if str(payload.get("adapter_id") or "") != ADAPTER_ID:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_ADAPTER_INVALID")
    if int(payload.get("expected_run_count") or 0) != 39:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPECTED_RUN_COUNT_INVALID"
        )
    ns = str(payload.get("evidence_namespace") or "")
    if not ns.startswith(EVIDENCE_NAMESPACE):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EVIDENCE_NAMESPACE_INVALID", ns
        )

    _assert_authorizes_scope(payload)

    _validate_budget(payload.get("resource_budget"))
    assert_lifetime_covers_budget(
        payload.get("expires_at_utc"),
        dict(payload.get("resource_budget") or {}),
        now_utc=now_utc,
    )

    if jsonschema is not None:
        schema = load_authorization_schema()
        if schema is not None:
            try:
                jsonschema.validate(instance=dict(payload), schema=schema)
            except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
                raise HhHlExecutionAuthorizationError(
                    "HOLD_EXECUTION_GO_SCHEMA_VALIDATION_FAILED", exc.message
                ) from exc


def load_execution_go_package_schema(
    path: Path | None = None,
) -> dict[str, Any] | None:
    schema_path = path or AUTH_GO_PACKAGE_SCHEMA_PATH
    if not schema_path.exists():
        return None
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_PACKAGE_SCHEMA_INVALID", "root not object"
        )
    return payload


def validate_execution_go_package(
    package: Mapping[str, Any],
    *,
    now_utc: datetime | None = None,
) -> None:
    """Validate a *pre-post* Execution-GO package body (generator side).

    Identical structural discipline to :func:`validate_execution_go_payload`
    except ``github_comment_id`` MAY be ``null`` (it is filled only once the
    Owner has posted the fenced comment). Fail-closed on: wrong schema/status,
    relaxed absolute bans, missing/short ``authorizes``/``does_not_authorize``,
    missing package-only required fields (``strategy_version``,
    ``max_run_count``, ``design_go_comment_id``, ``design_go_body_fingerprint``,
    ``reproduction_policy``, ``analyzer_profile_id``), a non-finite/lapsed expiry,
    or a budget the lifetime cannot cover. This never authorizes execution.
    """
    status = str(package.get("status") or "")
    if status in FORBIDDEN_STATUSES:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_WRONG_GO_TYPE", status)
    if package.get("schema_version") != AUTH_SCHEMA_VERSION:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_SCHEMA_INVALID", str(package.get("schema_version"))
        )
    if status != GO_STATUS:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_STATUS_INVALID", status
        )
    if package.get("lr_status") != "NO-GO":
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_LR_NOT_NO_GO")
    if package.get("absolute_bans_unchanged") is not True:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_ABSOLUTE_BANS_RELAXED")

    granted = package.get("granted_capabilities")
    if granted != [GRANTED_CAPABILITY]:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_GRANTED_CAPABILITIES_INVALID", str(granted)
        )

    for key, pat in (
        ("bound_main_sha", _SHA40_RE),
        ("execution_sha", _SHA40_RE),
        ("manifest_fingerprint", _SHA64_RE),
        ("run_plan_fingerprint", _SHA64_RE),
        ("surface_capability_fingerprint", _SHA64_RE),
        ("design_go_body_fingerprint", _SHA64_RE),
    ):
        if not pat.fullmatch(str(package.get(key) or "")):
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_GO_FIELD_INVALID", key
            )

    for key in (
        "strategy_version",
        "reproduction_policy",
        "analyzer_profile_id",
    ):
        if not str(package.get(key) or "").strip():
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_GO_PACKAGE_FIELD_REQUIRED", key
            )
    if int(package.get("design_go_comment_id") or 0) <= 0:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_PACKAGE_FIELD_REQUIRED", "design_go_comment_id"
        )
    if int(package.get("max_run_count") or 0) != MAX_RUN_COUNT:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_MAX_RUN_COUNT_INVALID", str(package.get("max_run_count"))
        )

    # Defense-in-depth: same identity checks as the live-posted validator so a
    # missing jsonschema dependency cannot silently accept drifted packages.
    if list(package.get("strategy_set") or []) != [STRATEGY_ID]:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_STRATEGY_SET_INVALID")
    if str(package.get("adapter_id") or "") != ADAPTER_ID:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_ADAPTER_INVALID")
    if int(package.get("expected_run_count") or 0) != 39:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EXPECTED_RUN_COUNT_INVALID"
        )
    ns = str(package.get("evidence_namespace") or "")
    if not ns.startswith(EVIDENCE_NAMESPACE):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_EVIDENCE_NAMESPACE_INVALID", ns
        )

    _assert_authorizes_scope(package)

    _validate_budget(package.get("resource_budget"))
    assert_lifetime_covers_budget(
        package.get("expires_at_utc"),
        dict(package.get("resource_budget") or {}),
        now_utc=now_utc,
    )

    if jsonschema is not None:
        schema = load_execution_go_package_schema()
        if schema is not None:
            try:
                jsonschema.validate(instance=dict(package), schema=schema)
            except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
                raise HhHlExecutionAuthorizationError(
                    "HOLD_EXECUTION_GO_PACKAGE_SCHEMA_VALIDATION_FAILED", exc.message
                ) from exc


def default_gh_comment_fetcher(
    repository: str, issue: int, comment_id: int
) -> OwnerGoComment:
    owner, _, name = repository.partition("/")
    if not owner or not name:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_REPO_INVALID", repository
        )
    endpoint = f"repos/{owner}/{name}/issues/comments/{comment_id}"
    try:
        raw = subprocess.check_output(
            ["gh", "api", endpoint], text=True, stderr=subprocess.STDOUT
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_COMMENT_FETCH_FAILED", str(exc)
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_COMMENT_FETCH_FAILED", "non-json gh response"
        ) from exc
    issue_url = str(data.get("issue_url") or "")
    match = _ISSUE_URL_RE.fullmatch(issue_url)
    live_issue = int(match.group(1)) if match else 0
    return OwnerGoComment(
        comment_id=int(data.get("id") or 0),
        issue_number=live_issue,
        author_login=str((data.get("user") or {}).get("login") or ""),
        body=str(data.get("body") or ""),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or ""),
        repository=repository,
    )


_BINDING_KEYS = (
    "bound_main_sha",
    "execution_sha",
    "manifest_path",
    "manifest_id",
    "manifest_fingerprint",
    "campaign_id",
    "run_plan_fingerprint",
    "expected_run_count",
    "execution_surface_id",
    "surface_capability_fingerprint",
    "evidence_namespace",
    "dataset_selection_sha256",
    "dataset_content_fingerprint_digest",
)


def verify_owner_execution_go_comment(
    *,
    comment_id: int,
    expected: Mapping[str, Any],
    repository: str = DEFAULT_REPO,
    issue: int = ISSUE_NUMBER,
    fetcher: OwnerGoFetcher | None = None,
    now_utc: datetime | None = None,
    expected_comment_updated_at: str | None = None,
) -> dict[str, Any]:
    """Load and fully verify an Owner Execution-GO comment. Fail-closed."""
    fetch = fetcher or default_gh_comment_fetcher
    comment = fetch(repository, issue, comment_id)
    if comment.comment_id != comment_id:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_COMMENT_ID_MISMATCH",
            f"fetched={comment.comment_id} requested={comment_id}",
        )
    if comment.issue_number != issue:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_ISSUE_MISMATCH",
            f"fetched_issue={comment.issue_number} expected={issue}",
        )
    if comment.repository != repository:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_REPO_MISMATCH")
    if not comment.created_at or not comment.updated_at:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_TIMESTAMP_MISSING")
    if comment.created_at != comment.updated_at:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_COMMENT_MUTATED",
            f"created={comment.created_at} updated={comment.updated_at}",
        )
    if (
        expected_comment_updated_at is not None
        and comment.updated_at != expected_comment_updated_at
    ):
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_COMMENT_MUTATED",
            f"live={comment.updated_at} bound={expected_comment_updated_at}",
        )

    payload = parse_execution_go_payload_from_body(comment.body)
    validate_execution_go_payload(payload, now_utc=now_utc)

    live_author = assert_author_in_owner_allowlist(comment.author_login)
    payload_login = assert_author_in_owner_allowlist(
        str(payload.get("authorizing_github_login") or "")
    )
    if payload_login != live_author:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_AUTHOR_PAYLOAD_MISMATCH"
        )
    if int(payload.get("github_comment_id") or 0) != comment_id:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_COMMENT_ID_PAYLOAD_MISMATCH"
        )
    if int(payload.get("issue") or 0) != issue:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_ISSUE_PAYLOAD_MISMATCH"
        )
    if str(payload.get("repository") or "") != repository:
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_REPO_PAYLOAD_MISMATCH")

    for key in _BINDING_KEYS:
        if key in expected and payload.get(key) != expected[key]:
            raise HhHlExecutionAuthorizationError(
                "HOLD_EXECUTION_GO_BINDING_MISMATCH",
                f"{key}: payload={payload.get(key)!r} expected={expected[key]!r}",
            )
    if "resource_budget" in expected and dict(
        payload.get("resource_budget") or {}
    ) != dict(expected["resource_budget"]):
        raise HhHlExecutionAuthorizationError("HOLD_EXECUTION_GO_BUDGET_MISMATCH")

    auth_fp = fingerprint_execution_authorization_payload(payload)
    return {
        "valid": True,
        "reason_code": "EXECUTION_GO_VALID",
        "payload": payload,
        "authorization_fingerprint": auth_fp,
        "github_comment_id": comment_id,
        "authorizing_github_login": live_author,
        "comment_updated_at": comment.updated_at,
        "expires_at_utc": payload.get("expires_at_utc"),
        "clock_source": "core.utils.clock.utcnow",
    }


def authorization_context_from_verified_go(
    verified: Mapping[str, Any],
) -> AuthorizationContext:
    """Mint an :class:`AuthorizationContext` from a verified GO result only."""
    if not verified.get("valid") or verified.get("reason_code") != "EXECUTION_GO_VALID":
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_CONTEXT_REQUIRES_VERIFIED_GO"
        )
    payload = dict(verified.get("payload") or {})
    if not payload:
        raise HhHlExecutionAuthorizationError(
            "HOLD_EXECUTION_GO_CONTEXT_PAYLOAD_MISSING"
        )
    return AuthorizationContext(
        _AUTH_CTX_TOKEN,
        schema_version=str(payload["schema_version"]),
        status=str(payload["status"]),
        repository=str(payload["repository"]),
        issue=int(payload["issue"]),
        github_comment_id=int(payload["github_comment_id"]),
        authorizing_github_login=str(payload["authorizing_github_login"]),
        bound_main_sha=str(payload["bound_main_sha"]),
        execution_sha=str(payload["execution_sha"]),
        manifest_path=str(payload["manifest_path"]),
        manifest_id=str(payload["manifest_id"]),
        manifest_fingerprint=str(payload["manifest_fingerprint"]),
        campaign_id=str(payload["campaign_id"]),
        run_plan_fingerprint=str(payload["run_plan_fingerprint"]),
        strategy_set=tuple(str(s) for s in (payload.get("strategy_set") or [])),
        adapter_id=str(payload["adapter_id"]),
        expected_run_count=int(payload["expected_run_count"]),
        evidence_namespace=str(payload["evidence_namespace"]),
        execution_surface_id=str(payload["execution_surface_id"]),
        surface_capability_fingerprint=str(payload["surface_capability_fingerprint"]),
        granted_capabilities=tuple(
            str(c) for c in (payload.get("granted_capabilities") or [])
        ),
        resource_budget=dict(payload.get("resource_budget") or {}),
        resume_policy=dict(payload.get("resume_policy") or {}),
        expires_at_utc=str(payload.get("expires_at_utc") or ""),
        comment_updated_at=str(verified.get("comment_updated_at") or ""),
        authorization_fingerprint=str(verified["authorization_fingerprint"]),
        payload=payload,
    )
