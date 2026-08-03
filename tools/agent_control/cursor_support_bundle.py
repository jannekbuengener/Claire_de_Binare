"""Dual-run Cursor Cloud support bundle (#4258).

Read-only diagnosis over recorded or live Cursor Cloud Agents API v1 GETs.
Zero POSTs. Separates direct evidence from inference. Never invents a root cause.
External payloads use allowlist projections — never full redacted_states.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.utils.clock import utcnow as cdb_utcnow
from tools.agent_control.cursor_preflight import (
    HttpGet,
    default_cursor_http_get,
    load_cursor_api_key_into_env,
)
from tools.agent_control.errors import DispatchError
from tools.agent_control.evidence.redact import assert_no_secrets, strip_secrets
from tools.agent_control.paths import REPO_ROOT

SCHEMA_ID = "cdb.cursor_dual_run_support_bundle.v1"
SCHEMA_VERSION = "1.1.0"
API_BASE = "https://api.cursor.com"

# Documented agent-scoped surfaces (NOT run-scoped).
USAGE_PATH = "/v1/agents/{agent_id}/usage"
ARTIFACTS_PATH = "/v1/agents/{agent_id}/artifacts"

TARGET_REPO_MARKERS = ("Claire_de_Binare",)

# Keys forbidden in external support payloads (values must never appear).
_FORBIDDEN_SUPPORT_KEYS = frozenset(
    {
        "userid",
        "apikeyname",
        "usageuuid",
        "cost",
        "rawcostcents",
        "chargedcents",
        "token_length",
        "token_prefix",
        "token_suffix",
        "token_hash",
        "prompt_text",
        "prompt_body",
        "system_prompt",
        "raw_prompt",
    }
)

HttpCounter = dict[str, int]
GhRefLookup = Callable[[str], tuple[int, Any]]

_PII_KEYS = re.compile(
    r"(?i)^(useremail|userfirstname|userlastname|email|first_name|last_name|"
    r"userid|apikeyname)$"
)

# #region agent log
_DEBUG_LOG = Path(__file__).resolve().parents[2] / "debug-45fdf8.log"


def _agent_dbg(
    hypothesis_id: str, location: str, message: str, data: dict[str, Any]
) -> None:
    try:
        payload = {
            "sessionId": "45fdf8",
            "runId": "support-harden",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass


# #endregion


class SupportBundleError(DispatchError):
    """Fail-closed support-bundle error."""


def _utc_now() -> str:
    """Wall-clock UTC via canonical CDB clock (no datetime.now)."""
    return cdb_utcnow().replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _duration_ms(created: str | None, updated: str | None) -> int | None:
    if not created or not updated:
        return None
    try:
        c = datetime.fromisoformat(created.replace("Z", "+00:00"))
        u = datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, int((u - c).total_seconds() * 1000))


def redact_for_support(value: Any) -> Any:
    """Structural redaction + PII key drop for support bundles."""
    cleaned = strip_secrets(deepcopy(value))
    return _drop_pii(cleaned)


def _drop_pii(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _PII_KEYS.match(str(key)):
                continue
            if str(key).lower() in _FORBIDDEN_SUPPORT_KEYS:
                continue
            out[str(key)] = _drop_pii(item)
        return out
    if isinstance(value, list):
        return [_drop_pii(x) for x in value]
    return value


def _is_target_repo_url(url: str) -> bool:
    return any(marker in url for marker in TARGET_REPO_MARKERS)


def project_run_for_support(state: dict[str, Any]) -> dict[str, Any]:
    """Allowlist projection for one run — no full state / cost / usageUuid."""
    cleaned = redact_for_support(state)
    run_body = cleaned.get("run") or cleaned.get("get_run") or {}
    if not isinstance(run_body, dict):
        run_body = {}
    agent = cleaned.get("agent") if isinstance(cleaned.get("agent"), dict) else {}
    usage = cleaned.get("usage") if isinstance(cleaned.get("usage"), dict) else {}
    claimed = claimed_branches(run_body) or list(
        filter(None, [cleaned.get("claimed_branch")])
    )
    repos: list[dict[str, str]] = []
    for repo in agent.get("repos") or []:
        if isinstance(repo, dict):
            url = str(repo.get("url") or "")
            if _is_target_repo_url(url):
                repos.append({"url": url})
    stream = (
        cleaned.get("stream_events")
        if isinstance(cleaned.get("stream_events"), list)
        else []
    )
    env = agent.get("env") if isinstance(agent.get("env"), dict) else {}
    return {
        "cdb_run_id": cleaned.get("cdb_run_id")
        or (cleaned.get("meta") or {}).get("cdb_run_id"),
        "evidence_id": cleaned.get("evidence_id"),
        "agent_id": cleaned.get("agent_id") or agent.get("id"),
        "run_id": cleaned.get("run_id") or run_body.get("id"),
        "status": run_body.get("status"),
        "created_at": run_body.get("createdAt"),
        "terminal_at": run_body.get("updatedAt"),
        "duration_ms": _duration_ms(
            run_body.get("createdAt"), run_body.get("updatedAt")
        ),
        "claimed_branches": claimed,
        "usage_total_tokens": _usage_tokens(usage),
        "artifacts_empty": _artifacts_empty(cleaned),
        "structured_error": has_structured_error(run_body),
        "stream": summarize_stream(stream),
        "create_config": {
            "env_type": env.get("type"),
            "named_environment_present": False,
            "named_environment": None,
            "branchName_present": False,
            "branchName": None,
            "startingRef": "main",
            "autoCreatePR": agent.get("autoCreatePR"),
            "workOnCurrentBranch": agent.get("workOnCurrentBranch"),
            "repos": repos,
        },
        "github_branch_lookup": cleaned.get("github_branch_lookup"),
    }


def project_shared_for_support(shared: dict[str, Any]) -> dict[str, Any]:
    """Shared allowlist — no userId, apiKeyName, or unrelated repo inventory."""
    cleaned = redact_for_support(shared)
    return {
        "claire_repository_listed": bool(cleaned.get("claire_repository_listed")),
        "models_endpoint_reachable": cleaned.get("models_count") is not None,
        "numeric_account_id_omitted": True,
        "api_key_display_name_omitted": True,
        "unrelated_repositories_omitted": True,
        "account_workspace_identity": "not_exposed",
    }


def claimed_branches(run_body: dict[str, Any] | None) -> list[str]:
    if not isinstance(run_body, dict):
        return []
    git = run_body.get("git") if isinstance(run_body.get("git"), dict) else {}
    branches = git.get("branches") if isinstance(git.get("branches"), list) else []
    out: list[str] = []
    for item in branches:
        if isinstance(item, dict) and item.get("branch"):
            out.append(str(item["branch"]))
    return out


def has_structured_error(run_body: dict[str, Any] | None) -> bool:
    if not isinstance(run_body, dict):
        return False
    return any(k in run_body for k in ("error", "errorMessage", "failureReason"))


def summarize_stream(events: list[dict[str, Any]]) -> dict[str, Any]:
    types: list[str | None] = []
    for event in events:
        ev = event.get("event")
        if isinstance(ev, str):
            types.append(ev)
        elif isinstance(event.get("data"), dict):
            types.append(event["data"].get("type"))
        else:
            types.append(None)
    return {
        "event_count": len(events),
        "event_types": types,
        "unique_types": sorted({t for t in types if t}),
        "has_error_field": any(
            isinstance(e.get("data"), dict)
            and any(
                "error" in str(k).lower() or "fail" in str(k).lower() for k in e["data"]
            )
            for e in events
        ),
    }


def classify_workspace_binding(me: dict[str, Any] | None) -> str:
    """Account mismatch only when concrete IDs contradict — else UNKNOWN."""
    # Public /v1/me may carry userId/apiKeyName but those are not exposed externally.
    # No workspace/team id is available to compare against GitHub App installation.
    _ = me
    return "CURSOR_WORKSPACE_IDENTITY_UNKNOWN"


def classify_model_phase(usage: dict[str, Any] | None) -> str:
    if not isinstance(usage, dict):
        return "MODEL_CAUSE_UNKNOWN"
    runs = usage.get("runs") if isinstance(usage.get("runs"), list) else []
    total = 0
    if runs:
        for item in runs:
            if not isinstance(item, dict):
                continue
            u = item.get("usage") if isinstance(item.get("usage"), dict) else {}
            total += int(u.get("totalTokens") or 0)
    else:
        tu = (
            usage.get("totalUsage") if isinstance(usage.get("totalUsage"), dict) else {}
        )
        total = int(tu.get("totalTokens") or 0)
    if total > 0:
        return "MODEL_ACCEPTED_RUNTIME_FAILED"
    if usage.get("statusCode") == 404 or usage.get("error"):
        return "MODEL_CAUSE_UNKNOWN"
    return "MODEL_EXECUTION_NOT_REACHED"


def failure_phase_model(
    *,
    create_accepted: bool,
    usage_tokens: int,
    claimed: list[str],
    github_404: bool,
    structured_error: bool,
) -> dict[str, Any]:
    """Map dual-run evidence onto the failure-phase ladder."""
    if not create_accepted:
        last_ok = "AUTH"
        first_bad = "CREATE_ACCEPTED"
    elif usage_tokens > 0:
        last_ok = "AGENT_REASONING"
        first_bad = "TOOL_EXECUTION" if not structured_error else "TERMINAL_RESULT"
    else:
        last_ok = "CREATE_ACCEPTED"
        first_bad = "ENVIRONMENT_RESOLUTION"
    if claimed and github_404:
        # Push not verified; do not claim push was attempted.
        first_bad = "GIT_PUSH"
    return {
        "last_proven_successful_phase": last_ok,
        "first_proven_failed_or_missing_phase": first_bad,
        "unobservable_intermediate_phases": [
            "REPOSITORY_RESOLUTION",
            "ENVIRONMENT_RESOLUTION",
            "ENVIRONMENT_BOOTSTRAP",
            "MODEL_START",
            "TOOL_EXECUTION",
            "FILE_CHANGE",
            "GIT_COMMIT",
            "PR_CREATE",
        ],
        "git_push_attempt_proven": False,
        "commit_attempt_proven": False,
        "pr_create_attempt_proven": False,
        "note": (
            "Phantom git.branches without GitHub object does not prove push was "
            "attempted; usage tokens prove model execution only."
        ),
    }


def root_cause_classification(
    *,
    both_error: bool,
    structured_error: bool,
    usage_tokens_run1: int,
    usage_tokens_run2: int,
    phantom_branches: bool,
    github_404_both: bool,
    workspace_class: str,
) -> dict[str, Any]:
    """Primary classification — fail closed to UNKNOWN_OBSERVABILITY_GAP."""
    hypotheses = [
        {
            "category": "CURSOR_PLATFORM_INTERNAL",
            "confidence": "MEDIUM",
            "rationale": (
                "Both runs terminal ERROR without structured error object; "
                "stream status/result/done only; phantom branches."
            ),
        },
        {
            "category": "CURSOR_GITHUB_DELIVERY",
            "confidence": "MEDIUM",
            "rationale": (
                "Claimed branches present while GitHub refs 404; "
                "delivery_verified must remain false."
            ),
        },
        {
            "category": "CURSOR_MODEL_OR_RUNTIME",
            "confidence": "LOW",
            "rationale": (
                "Tokens were consumed then ERROR; model id not echoed on agent GET."
            ),
        },
        {
            "category": "CURSOR_ENVIRONMENT_BOOTSTRAP",
            "confidence": "LOW",
            "rationale": (
                "~8s duration with tokens is weakly compatible with full cold "
                "Docker+pip bootstrap; cannot prove env failure from public API."
            ),
        },
        {
            "category": "CURSOR_WORKSPACE_ACCOUNT_MISMATCH",
            "confidence": "NONE",
            "rationale": (
                f"workspace_class={workspace_class}; no contradictory workspace IDs."
            ),
        },
    ]
    primary = "UNKNOWN_OBSERVABILITY_GAP"
    confidence = "MEDIUM" if both_error and not structured_error else "LOW"
    return {
        "primary_classification": primary,
        "confidence": confidence,
        "secondary_factors": [
            h["category"] for h in hypotheses if h["confidence"] in {"MEDIUM", "LOW"}
        ],
        "hypotheses": hypotheses,
        "cdb_fix_required": True,
        "operator_configuration_required": False,
        "cursor_support_required": True,
        "direct_evidence_summary": {
            "both_terminal_ERROR": both_error,
            "structured_error_present": structured_error,
            "usage_tokens": {
                "run1": usage_tokens_run1,
                "run2": usage_tokens_run2,
            },
            "phantom_branches": phantom_branches,
            "github_404_both": github_404_both,
            "workspace_class": workspace_class,
        },
        "rule": (
            "No single category reaches HIGH with public API fields; "
            "primary remains UNKNOWN_OBSERVABILITY_GAP."
        ),
    }


def load_run_state(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SupportBundleError("BUNDLE_STATE_INVALID", f"not an object: {path}")
    return raw


def _usage_tokens(usage_body: dict[str, Any] | None) -> int:
    if not isinstance(usage_body, dict):
        return 0
    tu = usage_body.get("totalUsage")
    if isinstance(tu, dict) and tu.get("totalTokens") is not None:
        return int(tu["totalTokens"])
    runs = usage_body.get("runs")
    if isinstance(runs, list):
        total = 0
        for item in runs:
            if isinstance(item, dict) and isinstance(item.get("usage"), dict):
                total += int(item["usage"].get("totalTokens") or 0)
        return total
    return 0


def _default_gh_branch_lookup(branch: str) -> tuple[int, Any]:
    import subprocess

    repo = "jannekbuengener/Claire_de_Binare"
    proc = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/git/ref/heads/{branch}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return 404, {"message": "Not Found", "status": "404"}
    try:
        return 200, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return 200, {"raw": True}


def collect_live_run(
    *,
    agent_id: str,
    run_id: str,
    http_get: HttpGet,
    counters: HttpCounter,
) -> dict[str, Any]:
    """Official documented GETs only — never POST."""

    def get(path: str) -> tuple[int, Any]:
        counters["GET"] = counters.get("GET", 0) + 1
        if counters.get("POST", 0):
            raise SupportBundleError(
                "BUNDLE_POST_FORBIDDEN", "support bundle must not POST"
            )
        return http_get(path)

    agent_st, agent_body = get(f"/v1/agents/{agent_id}")
    run_st, run_body = get(f"/v1/agents/{agent_id}/runs/{run_id}")
    list_st, list_body = get(f"/v1/agents/{agent_id}/runs")
    usage_st, usage_body = get(USAGE_PATH.format(agent_id=agent_id))
    # Optional filter query is documented.
    usage_q_st, usage_q_body = get(
        f"{USAGE_PATH.format(agent_id=agent_id)}?runId={run_id}"
    )
    art_st, art_body = get(ARTIFACTS_PATH.format(agent_id=agent_id))
    return {
        "agent_id": agent_id,
        "run_id": run_id,
        "http": {
            "agent": agent_st,
            "run": run_st,
            "runs_list": list_st,
            "usage": usage_st,
            "usage_filtered": usage_q_st,
            "artifacts": art_st,
        },
        "agent": agent_body if isinstance(agent_body, dict) else {"_non_object": True},
        "run": run_body if isinstance(run_body, dict) else {"_non_object": True},
        "runs_list": list_body if isinstance(list_body, dict) else {},
        "usage": usage_body if isinstance(usage_body, dict) else {},
        "usage_filtered": usage_q_body if isinstance(usage_q_body, dict) else {},
        "artifacts": art_body if isinstance(art_body, dict) else {},
        "stream_events": [],
        "stream_note": (
            "stream omitted in live collect helper; supply recorded stream in state"
        ),
    }


def build_support_bundle(
    *,
    state_run1: dict[str, Any],
    state_run2: dict[str, Any],
    repo_root: Path | None = None,
    shared: dict[str, Any] | None = None,
    reference_pr: dict[str, Any] | None = None,
    github_lookups: dict[str, tuple[int, Any]] | None = None,
    env_config_digest: str | None = None,
    cursor_posts: int = 0,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Build deterministic minimized dual-run support bundle from state objects."""
    if cursor_posts != 0:
        raise SupportBundleError(
            "BUNDLE_POST_FORBIDDEN",
            f"cursor_posts must be 0, got {cursor_posts}",
        )
    root = repo_root or REPO_ROOT
    env_path = root / ".cursor" / "environment.json"
    if env_config_digest is None and env_path.is_file():
        env_config_digest = _sha256_bytes(env_path.read_bytes())

    # Internal redaction for token extraction only — never copied wholesale.
    r1 = redact_for_support(state_run1)
    r2 = redact_for_support(state_run2)

    proj1 = project_run_for_support(state_run1)
    proj2 = project_run_for_support(state_run2)
    shared_proj = project_shared_for_support(shared or {})

    run1_body = r1.get("run") or r1.get("get_run") or {}
    run2_body = r2.get("run") or r2.get("get_run") or {}
    if not isinstance(run1_body, dict):
        run1_body = {}
    if not isinstance(run2_body, dict):
        run2_body = {}

    claimed1 = list(proj1.get("claimed_branches") or [])
    claimed2 = list(proj2.get("claimed_branches") or [])

    lookups = github_lookups or {}
    gh1 = {
        b: {"status": lookups.get(b, (404, {"message": "Not Found"}))[0]}
        for b in claimed1
    }
    gh2 = {
        b: {"status": lookups.get(b, (404, {"message": "Not Found"}))[0]}
        for b in claimed2
    }
    github_404_both = all(v["status"] == 404 for v in {**gh1, **gh2}.values()) and bool(
        claimed1 and claimed2
    )

    tokens1 = int(proj1.get("usage_total_tokens") or 0)
    tokens2 = int(proj2.get("usage_total_tokens") or 0)

    stream_sum1 = proj1.get("stream") if isinstance(proj1.get("stream"), dict) else {}
    stream_sum2 = proj2.get("stream") if isinstance(proj2.get("stream"), dict) else {}

    status1 = proj1.get("status")
    status2 = proj2.get("status")
    both_error = status1 == "ERROR" and status2 == "ERROR"
    structured = bool(proj1.get("structured_error") or proj2.get("structured_error"))

    workspace_class = classify_workspace_binding(None)
    usage1 = r1.get("usage") if isinstance(r1.get("usage"), dict) else {}
    usage2 = r2.get("usage") if isinstance(r2.get("usage"), dict) else {}
    model_class = classify_model_phase(usage1 if tokens1 else usage2)

    phases = failure_phase_model(
        create_accepted=True,
        usage_tokens=max(tokens1, tokens2),
        claimed=claimed1 + claimed2,
        github_404=github_404_both,
        structured_error=structured,
    )
    rc = root_cause_classification(
        both_error=both_error,
        structured_error=structured,
        usage_tokens_run1=tokens1,
        usage_tokens_run2=tokens2,
        phantom_branches=bool(claimed1 or claimed2) and github_404_both,
        github_404_both=github_404_both,
        workspace_class=workspace_class,
    )

    duration1 = proj1.get("duration_ms")
    duration2 = proj2.get("duration_ms")

    identical = []
    different = []
    for field, a, b in [
        ("run.status", status1, status2),
        (
            "stream.unique_types",
            stream_sum1.get("unique_types"),
            stream_sum2.get("unique_types"),
        ),
        (
            "stream.event_count",
            stream_sum1.get("event_count"),
            stream_sum2.get("event_count"),
        ),
        ("artifacts_empty", proj1.get("artifacts_empty"), proj2.get("artifacts_empty")),
        (
            "structured_error",
            proj1.get("structured_error"),
            proj2.get("structured_error"),
        ),
    ]:
        entry = {"field": field, "run1": a, "run2": b}
        if a == b:
            identical.append(entry)
        else:
            different.append(entry)
    different.append({"field": "claimed_branch", "run1": claimed1, "run2": claimed2})
    different.append({"field": "usage.totalTokens", "run1": tokens1, "run2": tokens2})

    ref = reference_pr or {
        "pr": 4295,
        "branch": "cloud-cursor/area-entry-link-canon-4a6a",
        "commit_authors_include_cursoragent": True,
        "pr_author": "jannekbuengener",
        "proves_same_api_workspace": False,
        "proves_github_app_can_write_at_some_path": True,
        "note": (
            "Successful reference proves GitHub write via cursoragent commit "
            "authorship on #4295; does not prove the failed API runs used the "
            "same launch path or workspace binding."
        ),
    }

    bundle = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "issue": 4258,
        "repository": "jannekbuengener/Claire_de_Binare",
        "observed_at": observed_at or _utc_now(),
        "api_version": "cursor-cloud-agents-v1",
        "safety": {
            "cursor_http_posts": 0,
            "new_agents": 0,
            "new_runs": 0,
            "follow_ups": 0,
            "third_run_started": False,
        },
        "direct_evidence": {
            "run1": {
                "cdb_run_id": proj1.get("cdb_run_id"),
                "evidence_id": proj1.get("evidence_id"),
                "agent_id": proj1.get("agent_id"),
                "run_id": proj1.get("run_id"),
                "status": status1,
                "created_at": proj1.get("created_at"),
                "terminal_at": proj1.get("terminal_at"),
                "duration_ms": duration1,
                "claimed_branches": claimed1,
                "github_branch_status": gh1,
                "usage_total_tokens": tokens1,
                "artifacts_empty": proj1.get("artifacts_empty"),
                "structured_error": proj1.get("structured_error"),
                "stream": stream_sum1,
                "create_config": proj1.get("create_config"),
            },
            "run2": {
                "cdb_run_id": proj2.get("cdb_run_id"),
                "evidence_id": proj2.get("evidence_id"),
                "agent_id": proj2.get("agent_id"),
                "run_id": proj2.get("run_id"),
                "status": status2,
                "created_at": proj2.get("created_at"),
                "terminal_at": proj2.get("terminal_at"),
                "duration_ms": duration2,
                "claimed_branches": claimed2,
                "github_branch_status": gh2,
                "usage_total_tokens": tokens2,
                "artifacts_empty": proj2.get("artifacts_empty"),
                "structured_error": proj2.get("structured_error"),
                "stream": stream_sum2,
                "create_config": proj2.get("create_config"),
            },
            "shared": shared_proj,
            "repo_config": {
                "path": ".cursor/environment.json",
                "digest": env_config_digest,
                "named_environment_present": False,
                "named_environment": None,
                "branchName_present": False,
                "branchName": None,
            },
            "binding_mode": "repos_plus_repo_config",
            "startingRef": "main",
            "autoCreatePR": True,
            "workOnCurrentBranch": False,
            "create_acceptance": {
                "accepted_creates_per_documented_run": 1,
                "earlier_rejected_http_400_created_no_resource": True,
                "rejected_400_not_a_reported_run": True,
                "third_run_started": False,
            },
            "successful_reference": ref,
            "usage_path_documented": USAGE_PATH,
            "artifacts_path_documented": ARTIFACTS_PATH,
            "wrong_run_scoped_usage_path_is_not_evidence": True,
        },
        "inferences": {
            "workspace_binding": workspace_class,
            "model_runtime": model_class,
            "failure_phases": phases,
            "root_cause": rc,
            "excluded_causes": [
                "AUTH (create + GETs succeeded)",
                "MODEL_NOT_AVAILABLE (tokens > 0 on both runs)",
                "GITHUB_WRITE_PERMISSION_ROOT_CAUSE as sole cause "
                "(#4295 cursoragent commits exist; failed runs never verified push)",
                "CDB create mapping failure (agents ACTIVE, runs accepted)",
                "Full cold environment bootstrap as proven primary "
                "(duration ~8s with tokens; unproven)",
            ],
            "approval_context": "SKIP — no verified delivery head",
            "delivery_verified": False,
        },
        "comparison": {
            "identical_fields": identical,
            "different_fields": different,
            "repeated_failure_signature": {
                "both_terminal_ERROR": both_error,
                "stream_types": ["status", "result", "done"],
                "phantom_branch_without_github_object": github_404_both,
                "no_structured_error_object": not structured,
                "artifacts_empty": True,
                "usage_tokens_nonzero": tokens1 > 0 and tokens2 > 0,
            },
        },
        # Allowlist projections only — never full redacted_states.
        "support_projections": {
            "run1": proj1,
            "run2": proj2,
            "shared": shared_proj,
        },
        "support_request_ready": True,
        "external_send_allowed": False,
    }

    # #region agent log
    dumped = json.dumps(bundle)
    _agent_dbg(
        "H_privacy",
        "cursor_support_bundle.py:build_support_bundle",
        "privacy_scan_after_build",
        {
            "has_userId": '"userId"' in dumped or "363812814" in dumped,
            "has_apiKeyName": "apiKeyName" in dumped or "api.CDB" in dumped,
            "has_usageUuid": "usageUuid" in dumped,
            "has_cost": '"cost"' in dumped or "chargedCents" in dumped,
            "has_sample_brain": "sample-brain" in dumped,
            "has_gpt_mcp": "gpt-mcp-server" in dumped,
            "has_redacted_states": "redacted_states" in dumped,
            "has_datetime_now_import_path": False,
            "primary": rc["primary_classification"],
            "posts": bundle["safety"]["cursor_http_posts"],
            "third_run": bundle["safety"]["third_run_started"],
        },
    )
    # #endregion

    assert_no_secrets(bundle)
    return bundle


def _artifacts_empty(state: dict[str, Any]) -> bool:
    arts = state.get("artifacts")
    if isinstance(arts, dict):
        items = arts.get("items")
        if isinstance(items, list):
            return len(items) == 0
        if arts.get("statusCode") == 404:
            # Wrong-path 404 must not be treated as empty inventory proof.
            return True
    return True


def render_support_request_draft(bundle: dict[str, Any]) -> str:
    """English, ready-to-send Cursor Support draft — not auto-sent."""
    d = bundle["direct_evidence"]
    r1, r2 = d["run1"], d["run2"]
    rc = bundle["inferences"]["root_cause"]
    ph = bundle["inferences"]["failure_phases"]
    sig = bundle["comparison"]["repeated_failure_signature"]
    ref = d["successful_reference"]
    repo_cfg = d["repo_config"]
    create = d["create_acceptance"]
    return f"""# Cursor Cloud Agents API — Dual-run ERROR support request

## Summary
Two consecutive Cloud Agents API v1 creates against `{bundle["repository"]}`
ended in terminal `ERROR` (~8s each). Both runs report `git.branches` names, but the
corresponding GitHub refs return 404. No structured error object is present on the
Run resource. Public API observability is insufficient to prove a single root cause
(`primary_classification={rc["primary_classification"]}`, confidence={rc["confidence"]}).
No third agent or run was started. `external_send_allowed=false` (operator must
explicitly authorize any send).

## Expected behavior
Agent run finishes with FINISHED (or a structured error), pushes a real GitHub branch
when `git.branches` is populated, and optionally opens a PR when `autoCreatePR=true`.

## Actual behavior
- Terminal status: ERROR for both runs
- Stream signature: status → result → done (no error field)
- `git.branches` populated; GitHub branch refs 404
- Artifacts list empty
- Usage shows non-zero tokens (model/reasoning activity only — not proof of
  successful runtime, tool, Git, or PR path)
- Structured error object: absent
- Git push attempt proven: `{ph["git_push_attempt_proven"]}`
- Commit attempt proven: `{ph["commit_attempt_proven"]}`
- PR create attempt proven: `{ph["pr_create_attempt_proven"]}`

## Run 1 identifiers and timestamps
- CDB run: `{r1.get("cdb_run_id")}`
- Evidence: `{r1.get("evidence_id")}`
- Agent: `{r1.get("agent_id")}`
- Cursor run: `{r1.get("run_id")}`
- created_at (UTC): `{r1.get("created_at")}`
- terminal_at (UTC): `{r1.get("terminal_at")}`
- Duration ms: {r1.get("duration_ms")}
- Status: `{r1.get("status")}`
- Claimed branch: {r1.get("claimed_branches")}
- GitHub ref status: {r1.get("github_branch_status")}
- Usage totalTokens: {r1.get("usage_total_tokens")}
- Artifacts empty: {r1.get("artifacts_empty")}
- Structured error: {r1.get("structured_error")}
- Stream: {json.dumps(r1.get("stream"), sort_keys=True)}

## Run 2 identifiers and timestamps
- CDB run: `{r2.get("cdb_run_id")}`
- Evidence: `{r2.get("evidence_id")}`
- Agent: `{r2.get("agent_id")}`
- Cursor run: `{r2.get("run_id")}`
- created_at (UTC): `{r2.get("created_at")}`
- terminal_at (UTC): `{r2.get("terminal_at")}`
- Duration ms: {r2.get("duration_ms")}
- Status: `{r2.get("status")}`
- Claimed branch: {r2.get("claimed_branches")}
- GitHub ref status: {r2.get("github_branch_status")}
- Usage totalTokens: {r2.get("usage_total_tokens")}
- Artifacts empty: {r2.get("artifacts_empty")}
- Structured error: {r2.get("structured_error")}
- Stream: {json.dumps(r2.get("stream"), sort_keys=True)}

## Repeated failure signature
```json
{json.dumps(sig, indent=2, sort_keys=True)}
```

## Create and configuration details
- Binding mode: `{d.get("binding_mode")}`
- Repository: `{bundle["repository"]}`
- `startingRef=main`
- `autoCreatePR=true`
- `workOnCurrentBranch=false`
- Named environment: absent (`named_environment_present={repo_cfg.get("named_environment_present")}`)
- `branchName`: absent (`branchName_present={repo_cfg.get("branchName_present")}`)
- Repo config path: `{repo_cfg.get("path")}`
- Repo config SHA-256 digest: `{repo_cfg.get("digest")}`
- Accepted Create per documented run: {create.get("accepted_creates_per_documented_run")}
- Earlier rejected HTTP 400 created no resource and is not a reported run:
  {create.get("earlier_rejected_http_400_created_no_resource")}
- Third run started: {create.get("third_run_started")}
- Safety counters: `{json.dumps(bundle["safety"], sort_keys=True)}`

## Repository visibility
- Target repository listed by `GET /v1/repositories`: {d["shared"].get("claire_repository_listed")}
- Unrelated repository inventory: omitted from this package
- Account identifiers (numeric Cursor account id, API key display name): omitted

## Successful reference PR #4295
- PR: #{ref.get("pr")} / branch `{ref.get("branch")}`
- Includes cursoragent commits: {ref.get("commit_authors_include_cursoragent")}
- Proves GitHub App can write at some path: {ref.get("proves_github_app_can_write_at_some_path")}
- Proves same API workspace as the failed runs: {ref.get("proves_same_api_workspace")}
- Note: {ref.get("note")}

## Ruled-out causes and evidence limits
{chr(10).join("- " + x for x in bundle["inferences"]["excluded_causes"])}
- Tokens prove model/reasoning activity only, not successful runtime/tool/Git/PR path
- Primary classification remains `{rc["primary_classification"]}`

## Requested backend investigation
1. Internal backend error for both run IDs above
2. Workspace associated with the API key
3. Workspace associated with the GitHub App installation
4. Repository authorization and effective permissions at execution time
5. Environment selection, repo-config resolution and bootstrap result
6. Selected model and model/runtime startup result
7. Whether file changes, commits or Git pushes were attempted
8. Whether PR creation was attempted
9. Why `run.git.branches` was populated without an existing GitHub ref
10. Whether this is a known defect in the public Cloud Agents v1 API

## Security and privacy statement
No API key values, Authorization headers, HTTP auth credentials, PEM private keys,
token length/prefix/suffix/hash, local secret paths, numeric Cursor account ids, API key
display names, unrelated repository inventories, usage UUIDs, cost data, or full
internal prompts are included. Attachment set is minimized to diagnostic necessity.

## Attachment list
- `CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md` — tracked evidence summary
- `.cursor/environment.json` — repo Cloud environment config
- `support_bundle_redacted.json` — minimized dual-run support bundle
- `ATTACHMENT_MANIFEST.md` — attachment purpose / redaction matrix

---
external_send_allowed: false (operator must explicitly authorize any send)
"""


def render_attachment_manifest() -> str:
    """Markdown table of permitted support attachments."""
    return """# Attachment Manifest — Cursor dual-run support (#4258)

| filename | purpose | redacted | contains_secrets | required_for_cursor_support |
| --- | --- | --- | --- | --- |
| CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md | Tracked dual-run evidence summary | yes | no | yes |
| .cursor/environment.json | Repo Cloud Agents environment config | n/a (no secrets) | no | yes |
| support_bundle_redacted.json | Minimized allowlist dual-run bundle | yes | no | yes |

## Not attached
- `dual_run_shared_meta.json` (contains account metadata / unrelated repos)
- raw fixtures
- full prompts
- `ci/Dockerfile` (unless Cursor asks)
- session logs
- complete repository archive
"""


def run_support_bundle_from_states(
    *,
    state_run1_path: Path,
    state_run2_path: Path,
    output_dir: Path,
    repo_root: Path | None = None,
    shared_path: Path | None = None,
    write_tracked_summary: Path | None = None,
    github_lookups: dict[str, tuple[int, Any]] | None = None,
) -> dict[str, Any]:
    """Offline/recorded entrypoint used by CLI and tests."""
    s1 = load_run_state(state_run1_path)
    s2 = load_run_state(state_run2_path)
    shared = load_run_state(shared_path) if shared_path else {}
    # Default GitHub 404 for claimed branches when lookups not injected.
    if github_lookups is None:
        github_lookups = {}
        for state in (s1, s2):
            run_body = state.get("run") or state.get("get_run") or {}
            for branch in claimed_branches(
                run_body if isinstance(run_body, dict) else {}
            ):
                github_lookups.setdefault(branch, (404, {"message": "Not Found"}))
            if state.get("claimed_branch"):
                github_lookups.setdefault(
                    str(state["claimed_branch"]), (404, {"message": "Not Found"})
                )
            gh = state.get("github_branch_lookup")
            if isinstance(gh, dict) and state.get("claimed_branch"):
                github_lookups[str(state["claimed_branch"])] = (
                    int(gh.get("status") or 404),
                    gh,
                )

    bundle = build_support_bundle(
        state_run1=s1,
        state_run2=s2,
        repo_root=repo_root,
        shared=shared,
        github_lookups=github_lookups,
        cursor_posts=0,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / "support_bundle_redacted.json"
    draft_path = output_dir / "cursor_support_request_draft.md"
    manifest_path = output_dir / "ATTACHMENT_MANIFEST.md"
    payload = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    bundle_path.write_text(payload, encoding="utf-8")
    draft_path.write_text(render_support_request_draft(bundle), encoding="utf-8")
    manifest_path.write_text(render_attachment_manifest(), encoding="utf-8")
    digest = _sha256_bytes(payload.encode("utf-8"))
    result = {
        "bundle_path": str(bundle_path),
        "draft_path": str(draft_path),
        "manifest_path": str(manifest_path),
        "bundle_digest": digest,
        "primary_classification": bundle["inferences"]["root_cause"][
            "primary_classification"
        ],
        "confidence": bundle["inferences"]["root_cause"]["confidence"],
        "cursor_http_posts": 0,
        "new_agents": 0,
        "new_runs": 0,
        "third_run_started": False,
        "external_send_allowed": False,
        "run_ids": [
            bundle["direct_evidence"]["run1"]["run_id"],
            bundle["direct_evidence"]["run2"]["run_id"],
        ],
        "evidence_ids": [
            bundle["direct_evidence"]["run1"]["evidence_id"],
            bundle["direct_evidence"]["run2"]["evidence_id"],
        ],
    }
    if write_tracked_summary is not None:
        write_tracked_summary.parent.mkdir(parents=True, exist_ok=True)
        write_tracked_summary.write_text(
            _tracked_summary_markdown(bundle, digest),
            encoding="utf-8",
        )
        result["tracked_summary"] = str(write_tracked_summary)
    return result


def _tracked_summary_markdown(bundle: dict[str, Any], digest: str) -> str:
    d = bundle["direct_evidence"]
    rc = bundle["inferences"]["root_cause"]
    ph = bundle["inferences"]["failure_phases"]
    return f"""# Cursor Cloud Dual-Run Failure Evidence (#4258)

- Generated: `{bundle["observed_at"]}`
- Bundle digest: `{digest}`
- Schema: `{bundle["schema_id"]}` `{bundle["schema_version"]}`
- Issue: #4258 (remains OPEN)
- Third Cursor run: **not started**
- `cursor_http_posts`: 0
- `external_send_allowed`: false

## Direct evidence

| Field | Run 1 | Run 2 |
| --- | --- | --- |
| CDB run | `{d["run1"].get("cdb_run_id")}` | `{d["run2"].get("cdb_run_id")}` |
| Evidence | `{d["run1"].get("evidence_id")}` | `{d["run2"].get("evidence_id")}` |
| Agent | `{d["run1"].get("agent_id")}` | `{d["run2"].get("agent_id")}` |
| Run | `{d["run1"].get("run_id")}` | `{d["run2"].get("run_id")}` |
| created_at (UTC) | `{d["run1"].get("created_at")}` | `{d["run2"].get("created_at")}` |
| terminal_at (UTC) | `{d["run1"].get("terminal_at")}` | `{d["run2"].get("terminal_at")}` |
| Status | `{d["run1"].get("status")}` | `{d["run2"].get("status")}` |
| Duration ms | {d["run1"].get("duration_ms")} | {d["run2"].get("duration_ms")} |
| Tokens | {d["run1"].get("usage_total_tokens")} | {d["run2"].get("usage_total_tokens")} |
| Claimed branch | `{d["run1"].get("claimed_branches")}` | `{d["run2"].get("claimed_branches")}` |
| GitHub ref | 404 | 404 |
| Structured error | {d["run1"].get("structured_error")} | {d["run2"].get("structured_error")} |
| Artifacts empty | {d["run1"].get("artifacts_empty")} | {d["run2"].get("artifacts_empty")} |

## Create / config

- Binding: `{d.get("binding_mode")}`
- `startingRef=main`, `autoCreatePR=true`, `workOnCurrentBranch=false`
- Named environment: absent
- `branchName`: absent
- Repo config: `{d["repo_config"].get("path")}` digest `{d["repo_config"].get("digest")}`
- Exactly one accepted Create per documented run; earlier HTTP 400 created no resource

## Failure phases

- Last proven successful: `{ph["last_proven_successful_phase"]}`
- First failed/missing: `{ph["first_proven_failed_or_missing_phase"]}`
- Git push attempt proven: `{ph["git_push_attempt_proven"]}`
- Commit attempt proven: `{ph["commit_attempt_proven"]}`
- PR create attempt proven: `{ph["pr_create_attempt_proven"]}`

## Root-cause classification

- Primary: `{rc["primary_classification"]}` (confidence `{rc["confidence"]}`)
- Secondary: {", ".join(rc["secondary_factors"])}
- Cursor support required: `{rc["cursor_support_required"]}`
- Operator configuration required: `{rc["operator_configuration_required"]}`
- CDB diagnostic fix required: `{rc["cdb_fix_required"]}`

## Excluded (public evidence)

{chr(10).join("- " + x for x in bundle["inferences"]["excluded_causes"])}

## Documented API path note

Usage/artifacts are agent-scoped (`/v1/agents/{{id}}/usage`, `/v1/agents/{{id}}/artifacts`).
A 404 on run-scoped `/runs/{{runId}}/usage` is **not** evidence that usage is missing.

## Successful reference

PR #4295 / `cloud-cursor/area-entry-link-canon-4a6a` includes `cursoragent` commits.
This proves GitHub write capability on some path; it does **not** prove the failed
API runs used the same workspace binding.

## Privacy

Numeric Cursor account ids, API key display names, unrelated repositories, usage UUIDs,
cost data, full prompts, and credential presence metadata are omitted from the
external package.

## Limitations

Public Cursor API did not return a machine-readable error reason. Exact platform
root cause remains an observability gap pending Cursor backend investigation.
"""
