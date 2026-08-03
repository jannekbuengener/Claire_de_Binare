"""Dashboardless Cursor live preflight (#4258).

Uses only officially documented Cursor Cloud Agents API v1 surfaces,
GitHub REST via ``gh``, and versioned ``.cursor/environment.json``.
Never creates agents/runs and never calls private dashboard endpoints.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

from tools.agent_control.credentials import cursor_api_key_present
from tools.agent_control.environment.cursor_config import (
    validate_cursor_environment_config,
)
from tools.agent_control.errors import DispatchError
from tools.agent_control.evidence.redact import assert_no_secrets, sanitize_result_refs
from tools.agent_control.paths import REPO_ROOT

SCHEMA_ID = "cdb.cursor_live_preflight.v1"
SCHEMA_VERSION = "1.0.0"
SCHEMA_RELPATH = "docs/contracts/cdb_cursor_live_preflight.v1.schema.json"
API_BASE = "https://api.cursor.com"
CURSOR_GITHUB_APP_SLUG = "cursor"
DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"

HttpGet = Callable[[str], tuple[int, Any]]
GhApi = Callable[[list[str]], tuple[int, Any]]


class CursorPreflightError(DispatchError):
    """Fail-closed preflight error."""


def _load_schema(repo_root: Path) -> dict[str, Any]:
    return json.loads((repo_root / SCHEMA_RELPATH).read_text(encoding="utf-8"))


def validate_preflight_report(
    report: dict[str, Any], *, repo_root: Path | None = None
) -> None:
    root = repo_root or REPO_ROOT
    validator = Draft202012Validator(_load_schema(root))
    errors = sorted(validator.iter_errors(report), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        loc = ".".join(str(p) for p in err.path) or "$"
        raise CursorPreflightError(
            "PREFLIGHT_SCHEMA_INVALID",
            f"{loc}: {err.message}",
        )
    assert_no_secrets(report)


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    **detail: Any,
) -> None:
    checks.append({"id": check_id, "status": status, "detail": detail})


def _repo_https(owner_repo: str) -> str:
    return f"https://github.com/{owner_repo}"


def _normalize_repo_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    text = url.strip().rstrip("/")
    if text.startswith("github.com/"):
        text = "https://" + text
    parsed = urlparse(text)
    path = (parsed.path or "").strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not path or "/" not in path:
        return None
    owner, name = path.split("/", 1)
    return f"{owner}/{name}"


def load_cursor_api_key_into_env(
    *,
    env: dict[str, str] | None = None,
    secrets_dir: Path | None = None,
) -> tuple[bool, dict[str, str]]:
    """Load key into a copy of env for process-local use; never returns the value."""
    environ = dict(env if env is not None else os.environ)
    presence = cursor_api_key_present(env=environ, secrets_dir=secrets_dir)
    if presence.present and environ.get("CURSOR_API_KEY", "").strip():
        return True, environ
    if secrets_dir is None:
        return False, environ
    for candidate in (
        secrets_dir / "CURSOR_API_KEY",
        secrets_dir / "CURSOR_API_KEY.txt",
        secrets_dir / "CURSOR_API.txt",
    ):
        if candidate.is_file() and candidate.stat().st_size > 0:
            # Presence already proven; load only into local environ copy.
            environ["CURSOR_API_KEY"] = candidate.read_text(encoding="utf-8").strip()
            return bool(environ["CURSOR_API_KEY"]), environ
    return False, environ


def _basic_auth_header(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def default_cursor_http_get(
    path: str, *, api_key: str, timeout: float = 90.0
) -> tuple[int, Any]:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={
            "Authorization": _basic_auth_header(api_key),
            "Accept": "application/json",
            "User-Agent": "cdb-cursor-live-preflight/1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body: Any = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"message": "non_json_error_body"}
        return int(exc.code), body


def default_gh_api(argv: list[str]) -> tuple[int, Any]:
    completed = subprocess.run(
        ["gh", "api", *argv],
        check=False,
        capture_output=True,
        text=True,
    )
    text = completed.stdout or completed.stderr or ""
    try:
        payload: Any = (
            json.loads(text)
            if text.strip().startswith(("{", "["))
            else {"message": text.strip()[:500]}
        )
    except json.JSONDecodeError:
        payload = {"message": text.strip()[:500]}
    return int(completed.returncode), payload


def extract_environment_identity(agent_or_env: dict[str, Any] | None) -> dict[str, Any]:
    """Extract publicly documented env fields only (type/name)."""
    src = agent_or_env or {}
    env = src.get("env") if isinstance(src.get("env"), dict) else src
    if not isinstance(env, dict):
        return {
            "type": None,
            "name": None,
            "environment_public_id": None,
            "environment_version_public_id": None,
        }
    return {
        "type": env.get("type"),
        "name": env.get("name"),
        # Official OpenAPI AgentEnv has no ID fields — always null.
        "environment_public_id": env.get("environmentPublicId")
        or env.get("environment_public_id"),
        "environment_version_public_id": env.get("environmentVersionPublicId")
        or env.get("environment_version_public_id"),
    }


def evaluate_named_environment_selection(
    *,
    requested_name: str | None,
    resolved: dict[str, Any] | None,
    list_environments_http: int | None,
    dashboard_duplicate_names: bool,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Return selection status, public_api_gaps, limitations."""
    gaps: list[dict[str, Any]] = []
    limitations: list[str] = []
    if list_environments_http in {404, 405} or list_environments_http is None:
        gaps.append(
            {
                "id": "PUBLIC_API_GAP_ENVIRONMENT_LIST",
                "surface": "GET /v1/environments (not in OpenAPI)",
                "impact": "Cannot enumerate cloud environments or detect duplicate names via public API",
                "evidence": f"probe_http={list_environments_http}",
            }
        )
    gaps.append(
        {
            "id": "PUBLIC_API_GAP_ENVIRONMENT_IMMUTABLE_ID",
            "surface": "AgentEnv / CreateAgentRequest.env",
            "impact": "Official schema supports only env.type + env.name; no environmentPublicId/version binding",
            "evidence": "openapi_AgentEnv_type_name_only",
        }
    )
    if not requested_name:
        return "UNKNOWN", gaps, limitations + ["no_environment_name_requested"]
    resolved = resolved or {}
    resolved_name = resolved.get("name")
    resolved_id = resolved.get("environment_public_id")
    if dashboard_duplicate_names and not resolved_id:
        limitations.append("dashboard_duplicate_environment_names_observed")
        return "BLOCKED", gaps, limitations
    if resolved_name is None and resolved_id is None:
        limitations.append("resolved_environment_identity_missing_from_agent_response")
        return "UNKNOWN", gaps, limitations
    if resolved_name is not None and resolved_name != requested_name:
        return (
            "BLOCKED",
            gaps,
            limitations + ["requested_resolved_environment_mismatch"],
        )
    if resolved_name == requested_name and not dashboard_duplicate_names:
        return "PASS", gaps, limitations
    # Name matched but duplicates or no ID → not deterministic.
    return "BLOCKED", gaps, limitations + ["environment_name_not_unique_without_id"]


def run_cursor_live_preflight(
    *,
    repository: str = DEFAULT_REPO,
    environment_name: str | None = "jannekbuengener/Claire_de_Binare",
    binding_mode: str = "repos_plus_repo_config",
    repo_root: Path | None = None,
    secrets_dir: Path | None = None,
    state_path: Path | None = None,
    existing_agent_id: str | None = "bc-d1ba82b5-db1a-5040-b50a-2007040a65c7",
    existing_run_id: str | None = "run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b",
    dashboard_observations: dict[str, Any] | None = None,
    credential_env: dict[str, str] | None = None,
    http_get: HttpGet | None = None,
    gh_api: GhApi | None = None,
) -> dict[str, Any]:
    """Execute read-only preflight; never POST to Cursor or write to GitHub."""
    root = (repo_root or REPO_ROOT).resolve()
    checks: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    consent: list[dict[str, Any]] = []
    limitations: list[str] = [
        "dashboardless_preflight_only",
        "no_cursor_create",
        "no_github_writes",
        "refs_4258_not_closes",
    ]
    cursor_gets = 0
    cursor_posts = 0
    github_writes = 0

    secrets = secrets_dir or Path.home() / "Documents" / ".secrets" / ".cdb"
    present, environ = load_cursor_api_key_into_env(
        env=credential_env, secrets_dir=secrets
    )
    _check(
        checks,
        "credential_presence",
        "PASS" if present else "BLOCKED",
        credential_present=present,
    )
    if not present:
        report = _finalize_report(
            repository=repository,
            cursor_account={"api_reachable": False},
            credential_present=False,
            environment_requested={
                "binding_mode": binding_mode,
                "name": environment_name,
            },
            environment_resolved=None,
            environment_version=None,
            environment_selection_status="UNKNOWN",
            repo_config_status="UNKNOWN",
            github_app_status="UNKNOWN",
            github_permissions={},
            existing_run_status="UNKNOWN",
            public_api_gaps=gaps,
            manual_consent_boundaries=consent,
            ready_for_live_run=False,
            limitations=limitations + ["credential_missing"],
            checks=checks,
            binding_mode=binding_mode,
            cursor_http_gets=0,
            cursor_http_posts=0,
            github_writes=0,
            dashboard_observations=dashboard_observations,
            repo_root=root,
        )
        return report

    api_key = environ["CURSOR_API_KEY"]

    def do_get(path: str) -> tuple[int, Any]:
        nonlocal cursor_gets
        cursor_gets += 1
        if http_get is not None:
            return http_get(path)
        return default_cursor_http_get(path, api_key=api_key)

    def do_gh(argv: list[str]) -> tuple[int, Any]:
        if gh_api is not None:
            return gh_api(argv)
        return default_gh_api(argv)

    # --- Cursor /v1/me ---
    me_status, me_body = do_get("/v1/me")
    cursor_account: dict[str, Any] = {"http": me_status}
    if isinstance(me_body, dict):
        cursor_account["api_key_name"] = me_body.get("apiKeyName")
        cursor_account["user_id"] = me_body.get("userId")
        cursor_account["created_at"] = me_body.get("createdAt")
    _check(
        checks,
        "cursor_me",
        "PASS" if me_status == 200 else "BLOCKED",
        http=me_status,
    )

    # --- models ---
    models_status, models_body = do_get("/v1/models")
    model_items = []
    if isinstance(models_body, dict):
        raw_items = models_body.get("items") or models_body.get("models") or []
        if isinstance(raw_items, list):
            model_items = raw_items
    _check(
        checks,
        "cursor_models",
        "PASS" if models_status == 200 and model_items else "BLOCKED",
        http=models_status,
        count=len(model_items),
    )

    # --- repositories (rate limited) ---
    repos_status, repos_body = do_get("/v1/repositories")
    listed: list[str] = []
    if isinstance(repos_body, dict):
        items = repos_body.get("items") or repos_body.get("repositories") or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    norm = _normalize_repo_url(
                        item.get("url") or item.get("repository") or item.get("name")
                    )
                elif isinstance(item, str):
                    norm = _normalize_repo_url(item)
                else:
                    norm = None
                if norm:
                    listed.append(norm)
    target_listed = repository.lower() in {x.lower() for x in listed}
    _check(
        checks,
        "cursor_repositories",
        "PASS" if repos_status == 200 and target_listed else "BLOCKED",
        http=repos_status,
        count=len(listed),
        target_listed=target_listed,
    )

    # --- probe environment list (expected PUBLIC_API_GAP) ---
    env_list_status, _env_list_body = do_get("/v1/environments")
    _check(
        checks,
        "cursor_environment_list",
        "UNKNOWN" if env_list_status == 404 else "PARTIAL",
        http=env_list_status,
        note="not_in_official_openapi",
    )

    # --- existing agent/run (immutable evidence; read-only) ---
    existing_run_status = "PASS"
    environment_resolved: dict[str, Any] | None = None
    if existing_agent_id:
        ag_status, ag_body = do_get(f"/v1/agents/{existing_agent_id}")
        if ag_status == 200 and isinstance(ag_body, dict):
            environment_resolved = extract_environment_identity(ag_body)
            run_state = None
            if existing_run_id:
                run_http, run_body = do_get(
                    f"/v1/agents/{existing_agent_id}/runs/{existing_run_id}"
                )
                if run_http == 200 and isinstance(run_body, dict):
                    run_state = run_body.get("status")
            active = str(ag_body.get("status") or "").upper() == "ACTIVE"
            terminal = str(run_state or "").upper() in {
                "ERROR",
                "FINISHED",
                "CANCELLED",
                "EXPIRED",
            }
            if active and run_state and not terminal:
                existing_run_status = "BLOCKED"
                limitations.append("existing_non_terminal_run")
            elif str(run_state or "").upper() == "ERROR":
                existing_run_status = "PARTIAL"
                limitations.append("prior_run_error_immutable_evidence")
            _check(
                checks,
                "existing_agent_run",
                existing_run_status,
                agent_http=ag_status,
                agent_status=ag_body.get("status"),
                run_status=run_state,
                autoCreatePR=ag_body.get("autoCreatePR"),
                repos=ag_body.get("repos"),
                env=environment_resolved,
            )
        else:
            existing_run_status = "UNKNOWN"
            _check(
                checks,
                "existing_agent_run",
                "UNKNOWN",
                agent_http=ag_status,
            )
    else:
        _check(checks, "existing_agent_run", "PASS", note="no_existing_ids")

    dash = dashboard_observations or {}
    dash_envs = (
        dash.get("environments") if isinstance(dash.get("environments"), list) else []
    )
    duplicate_names = False
    if environment_name and isinstance(dash_envs, list):
        names = [
            (e.get("repository") or e.get("name") or "")
            for e in dash_envs
            if isinstance(e, dict)
        ]
        duplicate_names = (
            names.count(environment_name) >= 2 or names.count(repository) >= 2
        )
    if dash.get("ambiguity") == "two active environments with the same visible name":
        duplicate_names = True

    env_requested = {
        "binding_mode": binding_mode,
        "type": "cloud",
        "name": environment_name,
        "repository": repository,
        "starting_ref": "main",
    }

    if binding_mode == "named_cloud_env":
        selection_status, env_gaps, env_limits = evaluate_named_environment_selection(
            requested_name=environment_name,
            resolved=environment_resolved,
            list_environments_http=env_list_status,
            dashboard_duplicate_names=duplicate_names,
        )
        gaps.extend(env_gaps)
        limitations.extend(env_limits)
    else:
        # Official path: repos XOR named env. Prefer repos + .cursor/environment.json.
        gaps.append(
            {
                "id": "PUBLIC_API_GAP_ENVIRONMENT_LIST",
                "surface": "GET /v1/environments (not in OpenAPI)",
                "impact": "Named dashboard environments cannot be listed or disambiguated via public API",
                "evidence": f"probe_http={env_list_status}",
            }
        )
        gaps.append(
            {
                "id": "PUBLIC_API_GAP_ENVIRONMENT_IMMUTABLE_ID",
                "surface": "AgentEnv",
                "impact": "Cannot bind environmentPublicId/version; create uses repos + repo environment.json resolution",
                "evidence": "openapi_AgentEnv_type_name_only_mutual_exclusive_with_repos",
            }
        )
        if duplicate_names:
            limitations.append(
                "dashboard_duplicate_named_environments_ignored_for_repos_binding"
            )
        # Selection for repos mode is PASS when we will send explicit repos URL
        # (deterministic request). Resolved identity may still be UNKNOWN.
        selection_status = "PASS"
        if environment_resolved and not environment_resolved.get("name"):
            selection_status = "PARTIAL"
            limitations.append(
                "agent_response_env_lacks_name_public_api_cannot_verify_named_resolution"
            )

    _check(
        checks,
        "environment_selection",
        selection_status,
        binding_mode=binding_mode,
        requested=env_requested,
        resolved=environment_resolved,
        duplicate_names_observed=duplicate_names,
    )

    # --- repo config as code ---
    repo_config_status = "UNKNOWN"
    environment_version: str | None = None
    try:
        cfg = validate_cursor_environment_config(root)
        environment_version = str(cfg.get("digest") or cfg.get("config_digest") or "")
        dockerfile = (cfg.get("payload") or {}).get("build", {}).get("dockerfile")
        install = (cfg.get("payload") or {}).get("install")
        # Ensure dockerfile exists relative to .cursor/
        env_json = root / ".cursor" / "environment.json"
        df_ok = False
        if isinstance(dockerfile, str):
            df_path = (env_json.parent / dockerfile).resolve()
            df_ok = df_path.is_file() and str(df_path).startswith(str(root))
        repo_config_status = "PASS" if df_ok and install else "BLOCKED"
        _check(
            checks,
            "repo_environment_config",
            repo_config_status,
            digest=environment_version,
            dockerfile=dockerfile,
            dockerfile_exists=df_ok,
            install_present=bool(install),
            agentCanUpdateSnapshot=(cfg.get("payload") or {}).get(
                "agentCanUpdateSnapshot"
            ),
        )
    except DispatchError as exc:
        repo_config_status = "BLOCKED"
        _check(
            checks,
            "repo_environment_config",
            "BLOCKED",
            code=exc.code,
            message=exc.message,
        )

    # --- GitHub repo + branch protection (read-only) ---
    gh_repo_rc, gh_repo = do_gh([f"repos/{repository}"])
    default_branch = None
    if gh_repo_rc == 0 and isinstance(gh_repo, dict):
        default_branch = gh_repo.get("default_branch")
    _check(
        checks,
        "github_repository",
        "PASS" if gh_repo_rc == 0 and default_branch == "main" else "BLOCKED",
        returncode=gh_repo_rc,
        default_branch=default_branch,
    )

    prot_rc, prot = do_gh([f"repos/{repository}/branches/main/protection"])
    block_creations = None
    if isinstance(prot, dict):
        block_creations = (prot.get("block_creations") or {}).get("enabled")
    # 403 may mean protection readable only to admins — still try
    _check(
        checks,
        "github_branch_creation_gate",
        (
            "PASS"
            if block_creations is False
            else ("PARTIAL" if prot_rc != 0 else "BLOCKED")
        ),
        block_creations=block_creations,
        returncode=prot_rc,
    )

    # --- GitHub App: public app manifest + installation (often unreadable) ---
    app_rc, app_body = do_gh([f"apps/{CURSOR_GITHUB_APP_SLUG}"])
    app_perms: dict[str, Any] = {}
    if app_rc == 0 and isinstance(app_body, dict):
        app_perms = app_body.get("permissions") or {}
    contents_level = app_perms.get("contents")
    pr_level = app_perms.get("pull_requests")
    _check(
        checks,
        "github_app_manifest_permissions",
        (
            "PASS"
            if contents_level == "write" and pr_level == "write"
            else ("BLOCKED" if app_rc == 0 else "UNKNOWN")
        ),
        app_slug=CURSOR_GITHUB_APP_SLUG,
        contents=contents_level,
        pull_requests=pr_level,
        note="manifest_requested_permissions_not_installation_grant",
    )

    inst_rc, inst_body = do_gh([f"repos/{repository}/installation"])
    github_app_status = "UNKNOWN"
    installation_id = None
    installation_suspended = None
    installation_repo_selection = None
    if inst_rc == 0 and isinstance(inst_body, dict) and inst_body.get("id"):
        installation_id = inst_body.get("id")
        installation_suspended = inst_body.get("suspended_at")
        installation_repo_selection = inst_body.get("repository_selection")
        perms = inst_body.get("permissions") or {}
        c = perms.get("contents")
        p = perms.get("pull_requests")
        if installation_suspended:
            github_app_status = "BLOCKED"
        elif c == "write" and p == "write":
            github_app_status = "PASS"
        elif c == "read" or p == "read":
            github_app_status = "BLOCKED"
        else:
            github_app_status = "UNKNOWN"
        _check(
            checks,
            "github_app_installation",
            github_app_status,
            installation_id=installation_id,
            suspended=bool(installation_suspended),
            repository_selection=installation_repo_selection,
            contents=c,
            pull_requests=p,
        )
    else:
        gaps.append(
            {
                "id": "PUBLIC_API_GAP_GITHUB_INSTALLATION_READ",
                "surface": "GET /repos/{owner}/{repo}/installation",
                "impact": "User gh token cannot read Cursor GitHub App installation permissions; requires GitHub App JWT or user-to-server token for that App",
                "evidence": f"returncode={inst_rc} message={(inst_body or {}).get('message') if isinstance(inst_body, dict) else None}",
            }
        )
        consent.append(
            {
                "id": "GITHUB_APP_INSTALLATION_PERMISSION_READ",
                "boundary": "GitHub does not allow arbitrary OAuth user tokens to introspect another App's installation permission grant",
                "why_not_automatable": "Reading installation permissions requires credentials belonging to the Cursor GitHub App (JWT) or a user-to-server token authorized for that App",
            }
        )
        github_app_status = "UNKNOWN"
        _check(
            checks,
            "github_app_installation",
            "UNKNOWN",
            returncode=inst_rc,
            message=(
                (inst_body or {}).get("message")
                if isinstance(inst_body, dict)
                else None
            ),
        )

    # Supporting (not sufficient): Cursor repositories list includes target.
    if target_listed:
        limitations.append(
            "cursor_repositories_lists_target_supporting_not_permission_proof"
        )

    # Dashboard observations are supporting only.
    if dash:
        limitations.append("dashboard_observations_supporting_not_machine_truth")
        if dash.get("create_prs"):
            limitations.append(
                "dashboard_create_prs_ignored_api_autoCreatePR_is_source_of_truth"
            )

    # Network / routing policy — no public management API
    gaps.append(
        {
            "id": "PUBLIC_API_GAP_NETWORK_POLICY",
            "surface": "Cloud Agents API v1",
            "impact": "No public endpoint to read or set network access policy",
            "evidence": "openapi_no_network_policy_paths",
        }
    )
    gaps.append(
        {
            "id": "PUBLIC_API_GAP_ROUTING_RULES",
            "surface": "Cloud Agents API v1",
            "impact": "No public endpoint to manage dashboard routing rules; API create uses explicit repos/env",
            "evidence": "openapi_create_uses_repos_or_env",
        }
    )
    gaps.append(
        {
            "id": "PUBLIC_API_GAP_PR_POLICY_ACCOUNT",
            "surface": "Cloud Agents API v1",
            "impact": "Account-level Create PR dashboard setting not readable; use request field autoCreatePR",
            "evidence": "CreateAgentRequest.autoCreatePR",
        }
    )

    # State / idempotency
    state_status = "PASS"
    if state_path is not None and Path(state_path).is_file():
        try:
            state_obj = json.loads(Path(state_path).read_text(encoding="utf-8"))
            # JsonFileRunStore may be dict of runs
            if isinstance(state_obj, dict):
                for run in (
                    state_obj.values() if not state_obj.get("run_id") else [state_obj]
                ):
                    if not isinstance(run, dict):
                        continue
                    st = str(run.get("state") or run.get("last_provider_status") or "")
                    if st in {"RUNNING", "DISPATCHED", "CREATING"}:
                        state_status = "BLOCKED"
                        limitations.append("unresolved_active_local_state")
        except (OSError, json.JSONDecodeError):
            state_status = "PARTIAL"
    _check(
        checks,
        "local_state_idempotency",
        state_status,
        state_path=str(state_path) if state_path else None,
    )

    # ready_for_live_run — UNKNOWN/BLOCKED never PASS; github UNKNOWN fails closed
    blocking = [
        c
        for c in checks
        if c["id"]
        in {
            "credential_presence",
            "cursor_me",
            "cursor_models",
            "cursor_repositories",
            "repo_environment_config",
            "github_repository",
        }
        and c["status"] == "BLOCKED"
    ]
    if selection_status == "BLOCKED":
        blocking.append({"id": "environment_selection", "status": "BLOCKED"})
    if github_app_status in {"BLOCKED", "UNKNOWN"}:
        blocking.append({"id": "github_app_installation", "status": github_app_status})
    if existing_run_status == "BLOCKED" or state_status == "BLOCKED":
        blocking.append({"id": "active_run_or_state", "status": "BLOCKED"})

    ready = me_status == 200 and present and target_listed and not blocking
    # Explicit: unknown github install never ready
    if github_app_status != "PASS":
        ready = False
        limitations.append("ready_blocked_github_installation_not_proven")
    if selection_status in {"BLOCKED", "UNKNOWN"} and binding_mode == "named_cloud_env":
        ready = False
        limitations.append("ready_blocked_named_environment_not_deterministic")
    if binding_mode == "repos_plus_repo_config" and repo_config_status != "PASS":
        ready = False
    if cursor_posts != 0 or github_writes != 0:
        ready = False

    # Deduplicate gaps by id
    seen = set()
    uniq_gaps = []
    for g in gaps:
        if g["id"] in seen:
            continue
        seen.add(g["id"])
        uniq_gaps.append(g)

    report = _finalize_report(
        repository=repository,
        cursor_account=cursor_account,
        credential_present=True,
        environment_requested=env_requested,
        environment_resolved=environment_resolved,
        environment_version=environment_version or None,
        environment_selection_status=selection_status,
        repo_config_status=repo_config_status,
        github_app_status=github_app_status,
        github_permissions={
            "app_slug": CURSOR_GITHUB_APP_SLUG,
            "manifest_contents": contents_level,
            "manifest_pull_requests": pr_level,
            "installation_id": installation_id,
            "installation_readable": inst_rc == 0 and bool(installation_id),
            "installation_suspended": installation_suspended,
            "repository_selection": installation_repo_selection,
            "default_branch": default_branch,
            "block_creations": block_creations,
        },
        existing_run_status=existing_run_status,
        public_api_gaps=uniq_gaps,
        manual_consent_boundaries=consent,
        ready_for_live_run=ready,
        limitations=sorted(set(limitations)),
        checks=checks,
        binding_mode=binding_mode,
        cursor_http_gets=cursor_gets,
        cursor_http_posts=cursor_posts,
        github_writes=github_writes,
        dashboard_observations=dashboard_observations,
        repo_root=root,
    )
    # Clear key from local environ copy reference (caller env untouched if copy).
    environ.pop("CURSOR_API_KEY", None)
    return report


def _finalize_report(**kwargs: Any) -> dict[str, Any]:
    repo_root: Path = kwargs.pop("repo_root")
    report = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "repository": kwargs["repository"],
        "cursor_account": kwargs["cursor_account"],
        "credential_present": kwargs["credential_present"],
        "environment_requested": kwargs["environment_requested"],
        "environment_resolved": kwargs["environment_resolved"],
        "environment_version": kwargs["environment_version"],
        "environment_selection_status": kwargs["environment_selection_status"],
        "repo_config_status": kwargs["repo_config_status"],
        "github_app_status": kwargs["github_app_status"],
        "github_permissions": kwargs["github_permissions"],
        "existing_run_status": kwargs["existing_run_status"],
        "public_api_gaps": kwargs["public_api_gaps"],
        "manual_consent_boundaries": kwargs["manual_consent_boundaries"],
        "ready_for_live_run": kwargs["ready_for_live_run"],
        "limitations": kwargs["limitations"],
        "checks": kwargs["checks"],
        "binding_mode": kwargs["binding_mode"],
        "cursor_http_gets": kwargs["cursor_http_gets"],
        "cursor_http_posts": kwargs["cursor_http_posts"],
        "github_writes": kwargs["github_writes"],
        "dashboard_observations": kwargs.get("dashboard_observations"),
    }
    # Strip any accidental secrets
    report = sanitize_result_refs(report)
    validate_preflight_report(report, repo_root=repo_root)
    return report
