"""hh_hl Campaign Design-GO ratification (#4374).

Parses and live-verifies a ``GO_HH_HL_CAMPAIGN_DESIGN`` Owner comment that
ratifies the frozen draft design (grid + dataset + manifest fingerprint). This
module ratifies *design only* — it never authorizes campaign execution, paper,
live, echtgeld, or promotion. Execution needs a separate Owner Execution-GO
(``hh_hl_campaign_execution_authorization``).

Body fingerprint contract: ``body_fingerprint = canonical_hash(binding_view)``
where ``binding_view`` is the normalized binding-relevant projection of the
parsed Design-GO JSON (not the raw markdown body). Extra Owner-comment fields
(``notes``, ``authorizes``, ``grid.rationale``, ``dataset_root_kind``,
``window_count``) and a ``.draft`` schema suffix do not participate.
``github_comment_id`` is taken from the verified comment when the live payload
omits it. Live verify and ``build_reference_design_receipt`` therefore share one
fingerprint for the same ratified bindings.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.replay.canonical_json import canonical_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"
DESIGN_SCHEMA_PATH = (
    CONTRACTS_DIR / "cdb_hh_hl_campaign_design_authorization.v1.schema.json"
)

RATIFICATION_SCHEMA_VERSION = "cdb.hh_hl_campaign_design_ratification.v1"
DESIGN_GO_STATUS = "GO_HH_HL_CAMPAIGN_DESIGN"
DESIGN_GO_SCHEMA_VERSIONS = frozenset(
    {
        "cdb.hh_hl_campaign_design_go.v1",
        "cdb.hh_hl_campaign_design_go.v1.draft",
    }
)

DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
ISSUE_NUMBER = 4374
SOURCE_MANIFEST_PATH = "config/arvp/hh_hl_campaign_4374_draft_v1.json"
SOURCE_MANIFEST_FINGERPRINT = (
    "ab095923a795445ff41d319b1b3941412c9429d38128a5edd2256f4a777afa80"
)
DATASET_SELECTION_SHA256 = (
    "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
)
DATASET_CONTENT_FINGERPRINT_DIGEST = (
    "10f94c34e32db28a9393c38f944db4968b42e87d9ed223397e3637ff44323af9"
)
REQUIRED_SLOT = "hh_hl_baseline_001"
REQUIRED_VARIANT_COUNT = 1
GRID_PROVIDER_ID = "hh_hl_baseline_only_grid_v1"

# Design-GO must explicitly disclaim (at minimum) these downstream capabilities.
REQUIRED_DOES_NOT_AUTHORIZE = frozenset(
    {
        "campaign_execute",
        "paper",
        "live",
        "echtgeld",
        "promotion",
        "stage_b",
        "oos",
        "stress",
    }
)

AUTHORIZING_OWNER_ALLOWLIST = frozenset({"jannekbuengener"})

# Live-verified Design-GO facts (Owner comment on #4374). Recorded here as
# repo-only evidence; the authoritative body_fingerprint is recomputed live by
# ``verify_design_go_comment`` at finalize/execute time.
VERIFIED_DESIGN_GO_COMMENT_ID = 5206657394
VERIFIED_DESIGN_GO_TIMESTAMP_UTC = "2026-08-06T15:08:54Z"
VERIFIED_DESIGN_GO_BOUND_MAIN_SHA = "7875651ba3c907a1e5cc815f974085e42a1807bc"

_ASCII_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_ISSUE_URL_RE = re.compile(
    r"^https://api\.github\.com/repos/[^/\s]+/[^/\s]+/issues/(\d+)$"
)


class HhHlDesignAuthorizationError(ValueError):
    """Fail-closed Design-GO verification error carrying a HOLD reason code."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


@dataclass(frozen=True, slots=True)
class DesignGoComment:
    comment_id: int
    issue_number: int
    author_login: str
    body: str
    created_at: str
    updated_at: str
    repository: str


DesignCommentFetcher = Callable[[str, int, int], DesignGoComment]


@dataclass(frozen=True, slots=True)
class DesignRatificationReceipt:
    schema_version: str
    status: str
    repository: str
    issue: int
    comment_id: int
    authorizing_github_login: str
    created_at_utc: str
    updated_at_utc: str
    bound_main_sha: str
    source_manifest_path: str
    source_manifest_fingerprint: str
    grid_provider_id: str
    variant_count: int
    slots: tuple[str, ...]
    dataset_selection_sha256: str
    dataset_content_fingerprint_digest: str
    does_not_authorize: tuple[str, ...]
    lr_status: str
    body_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "repository": self.repository,
            "issue": self.issue,
            "comment_id": self.comment_id,
            "authorizing_github_login": self.authorizing_github_login,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "bound_main_sha": self.bound_main_sha,
            "source_manifest_path": self.source_manifest_path,
            "source_manifest_fingerprint": self.source_manifest_fingerprint,
            "grid_provider_id": self.grid_provider_id,
            "variant_count": self.variant_count,
            "slots": list(self.slots),
            "dataset_selection_sha256": self.dataset_selection_sha256,
            "dataset_content_fingerprint_digest": (
                self.dataset_content_fingerprint_digest
            ),
            "does_not_authorize": list(self.does_not_authorize),
            "lr_status": self.lr_status,
            "body_fingerprint": self.body_fingerprint,
        }


def _reject_duplicate_object_pairs(
    pairs: Sequence[tuple[str, Any]],
) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise HhHlDesignAuthorizationError(
                "HOLD_DESIGN_GO_JSON_INVALID", f"duplicate JSON key {key!r}"
            )
        seen[key] = value
    return seen


def _strict_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_object_pairs)
    except HhHlDesignAuthorizationError:
        raise
    except json.JSONDecodeError as exc:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_JSON_INVALID", str(exc)
        ) from exc


def parse_design_go_payload_from_body(body: str) -> dict[str, Any]:
    """Extract a Design-GO JSON payload from a ```json fence or a plain object."""
    raw = body or ""
    json_fences = re.findall(r"```json\s*\n(.*?)\n```", raw, re.DOTALL)
    if json_fences:
        if len(json_fences) > 1:
            raise HhHlDesignAuthorizationError(
                "HOLD_DESIGN_GO_BLOCK_AMBIGUOUS", "multiple json fences"
            )
        inner = json_fences[0]
        if "```" in inner:
            raise HhHlDesignAuthorizationError(
                "HOLD_DESIGN_GO_BLOCK_NESTED_FENCE", "nested fence"
            )
        payload = _strict_json_loads(inner)
    else:
        stripped = raw.strip()
        if not stripped.startswith("{"):
            raise HhHlDesignAuthorizationError(
                "HOLD_DESIGN_GO_BLOCK_MISSING", "no json fence or plain object"
            )
        payload = _strict_json_loads(stripped)
    if not isinstance(payload, dict):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_JSON_INVALID", "root must be object"
        )
    return payload


def normalize_design_go_payload_for_fingerprint(
    payload: Mapping[str, Any],
    *,
    comment_id: int | None = None,
) -> dict[str, Any]:
    """Project any valid Design-GO payload onto the binding fingerprint view.

    Live Owner comments may carry advisory extras and ``schema_version``
    ``*.draft``; those must not drift the fingerprint away from the reference
    receipt built from the same bindings. ``comment_id`` supplies
    ``github_comment_id`` when the live payload omits it.
    """
    grid = payload.get("grid") or {}
    dataset = payload.get("dataset") or {}
    cid = comment_id
    if cid is None:
        raw = payload.get("github_comment_id")
        if raw is None or raw == "":
            raise HhHlDesignAuthorizationError(
                "HOLD_DESIGN_GO_COMMENT_ID_MISMATCH",
                "github_comment_id required for fingerprint",
            )
        cid = int(raw)
    return {
        "schema_version": "cdb.hh_hl_campaign_design_go.v1",
        "status": str(payload.get("status") or ""),
        "repository": str(payload.get("repository") or ""),
        "issue": int(payload.get("issue") or 0),
        "authorizing_github_login": str(payload.get("authorizing_github_login") or ""),
        "github_comment_id": int(cid),
        "bound_main_sha": str(payload.get("bound_main_sha") or ""),
        "profile_id": str(payload.get("profile_id") or ""),
        "campaign_id": str(payload.get("campaign_id") or ""),
        "manifest_path": str(payload.get("manifest_path") or ""),
        "manifest_fingerprint": str(payload.get("manifest_fingerprint") or ""),
        "strategy_set": [str(x) for x in (payload.get("strategy_set") or [])],
        "grid": {
            "grid_provider_id": str(grid.get("grid_provider_id") or ""),
            "variant_count": int(grid.get("variant_count") or 0),
            "slots": _grid_slots(payload),
        },
        "dataset": {
            "selection_sha256": str(dataset.get("selection_sha256") or ""),
            "content_fingerprint_digest": str(
                dataset.get("content_fingerprint_digest") or ""
            ),
        },
        "does_not_authorize": sorted(
            str(x) for x in (payload.get("does_not_authorize") or [])
        ),
        "lr_status": str(payload.get("lr_status") or ""),
    }


def fingerprint_design_go_payload(
    payload: Mapping[str, Any],
    *,
    comment_id: int | None = None,
) -> str:
    """Canonical hash over the binding fingerprint view (documented contract)."""
    return canonical_hash(
        normalize_design_go_payload_for_fingerprint(payload, comment_id=comment_id)
    )


def normalize_authorizing_login(login: str) -> str:
    value = str(login or "")
    if not value or not _ASCII_LOGIN_RE.fullmatch(value):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_AUTHOR_LOGIN_INVALID", repr(login)
        )
    return value


def assert_author_in_owner_allowlist(login: str) -> str:
    normalized = normalize_authorizing_login(login)
    if normalized not in AUTHORIZING_OWNER_ALLOWLIST:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_AUTHOR_NOT_ALLOWLISTED", normalized
        )
    return normalized


def expected_design_bindings(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Derive expected Design-GO bindings from the immutable source draft manifest.

    Cross-checks the on-disk source fingerprint against the pinned constant so a
    mutated source manifest fails closed instead of silently re-anchoring.
    """
    root = repo_root or PROJECT_ROOT
    src_path = root / SOURCE_MANIFEST_PATH
    if not src_path.exists():
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_SOURCE_MANIFEST_MISSING", src_path.as_posix()
        )
    src = json.loads(src_path.read_text(encoding="utf-8"))
    fp = str(src.get("manifest_fingerprint") or "")
    if fp != SOURCE_MANIFEST_FINGERPRINT:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_SOURCE_MANIFEST_MUTATED",
            f"on_disk={fp} pinned={SOURCE_MANIFEST_FINGERPRINT}",
        )
    binding = src.get("dataset_binding") or {}
    selection = str(binding.get("selection_sha256") or "")
    content = str(binding.get("content_fingerprint_digest") or "")
    if selection != DATASET_SELECTION_SHA256:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_SOURCE_DATASET_MUTATED", "selection_sha256"
        )
    if content != DATASET_CONTENT_FINGERPRINT_DIGEST:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_SOURCE_DATASET_MUTATED", "content_fingerprint_digest"
        )
    return {
        "source_manifest_path": SOURCE_MANIFEST_PATH,
        "source_manifest_fingerprint": fp,
        "dataset_selection_sha256": selection,
        "dataset_content_fingerprint_digest": content,
        "variant_count": REQUIRED_VARIANT_COUNT,
        "slots": [REQUIRED_SLOT],
        "grid_provider_id": GRID_PROVIDER_ID,
    }


def _grid_slots(payload: Mapping[str, Any]) -> list[str]:
    grid = payload.get("grid") or {}
    slots = grid.get("slots")
    if isinstance(slots, list):
        return [str(s) for s in slots]
    return []


def _validate_payload_bindings(
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    schema_version = str(payload.get("schema_version") or "")
    if schema_version not in DESIGN_GO_SCHEMA_VERSIONS:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_SCHEMA_INVALID", schema_version
        )
    if payload.get("status") != DESIGN_GO_STATUS:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_STATUS_INVALID", str(payload.get("status"))
        )
    if payload.get("lr_status") != "NO-GO":
        raise HhHlDesignAuthorizationError("HOLD_DESIGN_GO_LR_NOT_NO_GO")

    bound_main_sha = str(payload.get("bound_main_sha") or "")
    if not _SHA40_RE.fullmatch(bound_main_sha):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_BOUND_MAIN_SHA_INVALID", bound_main_sha
        )

    if str(payload.get("manifest_path") or "") != expected["source_manifest_path"]:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_BINDING_MISMATCH", "manifest_path"
        )
    if (
        str(payload.get("manifest_fingerprint") or "")
        != expected["source_manifest_fingerprint"]
    ):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_MANIFEST_FINGERPRINT_MISMATCH",
            str(payload.get("manifest_fingerprint")),
        )
    if list(payload.get("strategy_set") or []) != ["hh_hl_continuation_v1"]:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_BINDING_MISMATCH", "strategy_set"
        )

    grid = payload.get("grid") or {}
    if int(grid.get("variant_count") or 0) != int(expected["variant_count"]):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_GRID_MISMATCH", "variant_count"
        )
    if _grid_slots(payload) != list(expected["slots"]):
        raise HhHlDesignAuthorizationError("HOLD_DESIGN_GO_GRID_MISMATCH", "slots")
    if str(grid.get("grid_provider_id") or "") != expected["grid_provider_id"]:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_GRID_MISMATCH", "grid_provider_id"
        )

    dataset = payload.get("dataset") or {}
    if (
        str(dataset.get("selection_sha256") or "")
        != expected["dataset_selection_sha256"]
    ):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_DATASET_MISMATCH", "selection_sha256"
        )
    if (
        str(dataset.get("content_fingerprint_digest") or "")
        != expected["dataset_content_fingerprint_digest"]
    ):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_DATASET_MISMATCH", "content_fingerprint_digest"
        )

    dna = set(str(x) for x in (payload.get("does_not_authorize") or []))
    missing = sorted(REQUIRED_DOES_NOT_AUTHORIZE - dna)
    if missing:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_DOES_NOT_AUTHORIZE_INCOMPLETE", str(missing)
        )


def _receipt_from_payload(
    *,
    payload: Mapping[str, Any],
    comment: DesignGoComment,
    login: str,
) -> DesignRatificationReceipt:
    return DesignRatificationReceipt(
        schema_version=RATIFICATION_SCHEMA_VERSION,
        status=DESIGN_GO_STATUS,
        repository=comment.repository,
        issue=comment.issue_number,
        comment_id=comment.comment_id,
        authorizing_github_login=login,
        created_at_utc=comment.created_at,
        updated_at_utc=comment.updated_at,
        bound_main_sha=str(payload["bound_main_sha"]),
        source_manifest_path=str(payload["manifest_path"]),
        source_manifest_fingerprint=str(payload["manifest_fingerprint"]),
        grid_provider_id=str((payload.get("grid") or {}).get("grid_provider_id")),
        variant_count=int((payload.get("grid") or {}).get("variant_count") or 0),
        slots=tuple(_grid_slots(payload)),
        dataset_selection_sha256=str(
            (payload.get("dataset") or {}).get("selection_sha256")
        ),
        dataset_content_fingerprint_digest=str(
            (payload.get("dataset") or {}).get("content_fingerprint_digest")
        ),
        does_not_authorize=tuple(
            str(x) for x in (payload.get("does_not_authorize") or [])
        ),
        lr_status="NO-GO",
        body_fingerprint=fingerprint_design_go_payload(
            payload, comment_id=comment.comment_id
        ),
    )


def canonical_design_go_payload(
    *,
    bound_main_sha: str,
    comment_id: int,
    repo_root: Path | None = None,
    repository: str = DEFAULT_REPO,
    issue: int = ISSUE_NUMBER,
) -> dict[str, Any]:
    """Reconstruct the canonical Design-GO payload from verified bindings.

    Used to materialize a deterministic ratification receipt without a live
    fetch. The reconstructed payload validates against the same binding rules a
    live comment must satisfy.
    """
    expected = expected_design_bindings(repo_root=repo_root)
    return {
        "schema_version": "cdb.hh_hl_campaign_design_go.v1",
        "status": DESIGN_GO_STATUS,
        "repository": repository,
        "issue": issue,
        "authorizing_github_login": "jannekbuengener",
        "github_comment_id": int(comment_id),
        "bound_main_sha": bound_main_sha,
        "profile_id": "hh_hl_continuation_prep_v1",
        "campaign_id": "arvp-hh-hl-continuation-4374-prep-v1",
        "manifest_path": expected["source_manifest_path"],
        "manifest_fingerprint": expected["source_manifest_fingerprint"],
        "strategy_set": ["hh_hl_continuation_v1"],
        "grid": {
            "grid_provider_id": expected["grid_provider_id"],
            "variant_count": expected["variant_count"],
            "slots": list(expected["slots"]),
        },
        "dataset": {
            "selection_sha256": expected["dataset_selection_sha256"],
            "content_fingerprint_digest": expected[
                "dataset_content_fingerprint_digest"
            ],
        },
        "does_not_authorize": sorted(REQUIRED_DOES_NOT_AUTHORIZE),
        "lr_status": "NO-GO",
    }


def build_reference_design_receipt(
    *,
    comment_id: int = VERIFIED_DESIGN_GO_COMMENT_ID,
    bound_main_sha: str = VERIFIED_DESIGN_GO_BOUND_MAIN_SHA,
    created_at_utc: str = VERIFIED_DESIGN_GO_TIMESTAMP_UTC,
    updated_at_utc: str = VERIFIED_DESIGN_GO_TIMESTAMP_UTC,
    repo_root: Path | None = None,
    repository: str = DEFAULT_REPO,
    issue: int = ISSUE_NUMBER,
) -> DesignRatificationReceipt:
    """Deterministic ratification receipt from live-verified Design-GO facts."""
    payload = canonical_design_go_payload(
        bound_main_sha=bound_main_sha,
        comment_id=comment_id,
        repo_root=repo_root,
        repository=repository,
        issue=issue,
    )
    _validate_payload_bindings(payload, expected_design_bindings(repo_root=repo_root))
    comment = DesignGoComment(
        comment_id=int(comment_id),
        issue_number=issue,
        author_login="jannekbuengener",
        body=json.dumps(payload),
        created_at=created_at_utc,
        updated_at=updated_at_utc,
        repository=repository,
    )
    return _receipt_from_payload(
        payload=payload, comment=comment, login="jannekbuengener"
    )


def default_gh_comment_fetcher(
    repository: str, issue: int, comment_id: int
) -> DesignGoComment:
    """Live GitHub comment fetch via ``gh api`` (tests should inject a mock)."""
    owner, _, name = repository.partition("/")
    if not owner or not name:
        raise HhHlDesignAuthorizationError("HOLD_DESIGN_GO_REPO_INVALID", repository)
    endpoint = f"repos/{owner}/{name}/issues/comments/{comment_id}"
    try:
        raw = subprocess.check_output(
            ["gh", "api", endpoint], text=True, stderr=subprocess.STDOUT
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_COMMENT_FETCH_FAILED", str(exc)
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_COMMENT_FETCH_FAILED", "non-json gh response"
        ) from exc
    issue_url = str(data.get("issue_url") or "")
    match = _ISSUE_URL_RE.fullmatch(issue_url)
    live_issue = int(match.group(1)) if match else 0
    return DesignGoComment(
        comment_id=int(data.get("id") or 0),
        issue_number=live_issue,
        author_login=str((data.get("user") or {}).get("login") or ""),
        body=str(data.get("body") or ""),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or ""),
        repository=repository,
    )


def verify_design_go_comment(
    *,
    comment_id: int,
    repository: str = DEFAULT_REPO,
    issue: int = ISSUE_NUMBER,
    fetcher: DesignCommentFetcher | None = None,
    expected: Mapping[str, Any] | None = None,
    repo_root: Path | None = None,
    expected_comment_updated_at: str | None = None,
) -> dict[str, Any]:
    """Load and fully verify a Design-GO comment. Fail-closed on every mismatch."""
    fetch = fetcher or default_gh_comment_fetcher
    comment = fetch(repository, issue, comment_id)
    if comment.comment_id != comment_id:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_COMMENT_ID_MISMATCH",
            f"fetched={comment.comment_id} requested={comment_id}",
        )
    if comment.issue_number != issue:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_ISSUE_MISMATCH",
            f"fetched_issue={comment.issue_number} expected={issue}",
        )
    if comment.repository != repository:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_REPO_MISMATCH",
            f"fetched={comment.repository} expected={repository}",
        )
    if not comment.created_at or not comment.updated_at:
        raise HhHlDesignAuthorizationError("HOLD_DESIGN_GO_TIMESTAMP_MISSING")
    if comment.created_at != comment.updated_at:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_COMMENT_MUTATED",
            f"created={comment.created_at} updated={comment.updated_at}",
        )
    if (
        expected_comment_updated_at is not None
        and comment.updated_at != expected_comment_updated_at
    ):
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_COMMENT_MUTATED",
            f"live={comment.updated_at} bound={expected_comment_updated_at}",
        )

    login = assert_author_in_owner_allowlist(comment.author_login)
    payload = parse_design_go_payload_from_body(comment.body)
    payload_login = assert_author_in_owner_allowlist(
        str(payload.get("authorizing_github_login") or "")
    )
    if payload_login != login:
        raise HhHlDesignAuthorizationError(
            "HOLD_DESIGN_GO_AUTHOR_PAYLOAD_MISMATCH",
            "payload authorizing_github_login != comment author",
        )
    if int(payload.get("issue") or 0) != issue:
        raise HhHlDesignAuthorizationError("HOLD_DESIGN_GO_ISSUE_MISMATCH", "payload")
    if str(payload.get("repository") or "") != repository:
        raise HhHlDesignAuthorizationError("HOLD_DESIGN_GO_REPO_MISMATCH", "payload")

    resolved_expected = (
        dict(expected)
        if expected is not None
        else expected_design_bindings(repo_root=repo_root)
    )
    _validate_payload_bindings(payload, resolved_expected)

    receipt = _receipt_from_payload(payload=payload, comment=comment, login=login)
    return {
        "valid": True,
        "reason_code": "DESIGN_GO_VALID",
        "receipt": receipt,
        "receipt_dict": receipt.as_dict(),
        "body_fingerprint": receipt.body_fingerprint,
        "comment_updated_at": comment.updated_at,
    }
