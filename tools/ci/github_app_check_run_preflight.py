"""Credential-free, read-only GitHub App Check Run cutover preflight (#4170 Phase B).

Evaluates an evidence snapshot for App ID, Installation ID, permission posture,
and unambiguous App-bound Check Run identity. Never reads or prints token values.
Does not install Apps, mutate Branch Protection, or publish Check Runs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from ci.publisher import EXPECTED_REPOSITORY
from ci.publisher.models import CHECK_RUN_NAME, SHADOW_CHECK_RUN_NAME

SCHEMA_VERSION = "cdb-github-app-check-run-preflight/v1"
REQUIRED_CHECK_CONTEXT = CHECK_RUN_NAME
ALLOWED_CHECK_RUN_NAMES = frozenset({CHECK_RUN_NAME, SHADOW_CHECK_RUN_NAME})

VERDICT_NOT_READY = "NOT_READY"
VERDICT_READY = "READY_FOR_OPERATOR_SMOKE"

REASON_APP_MISSING = "APP_MISSING"
REASON_INSTALLATION_MISSING = "INSTALLATION_MISSING"
REASON_CHECKS_WRITE_MISSING = "CHECKS_WRITE_MISSING"
REASON_PROHIBITED_PERMISSION = "PROHIBITED_PERMISSION"
REASON_COMMIT_STATUS_NOT_APP_BOUND = "COMMIT_STATUS_NOT_APP_BOUND"
REASON_CHECK_RUN_MISSING = "APP_BOUND_CHECK_RUN_MISSING"
REASON_CHECK_RUN_AMBIGUOUS = "APP_BOUND_CHECK_RUN_AMBIGUOUS"
REASON_CHECK_RUN_APP_MISMATCH = "APP_BOUND_CHECK_RUN_APP_MISMATCH"
REASON_READY = "APP_BOUND_CHECK_RUN_READY"
REASON_LIVE_READONLY = "LIVE_READONLY_OBSERVED"

# GitHub App permission keys that must not be write-capable for the publisher App.
_PROHIBITED_WRITE_PERMISSIONS = frozenset(
    {
        "administration",
        "actions",
        "contents",
        "statuses",
        "deployments",
        "secrets",
    }
)
_WRITE_LEVELS = frozenset({"write", "read_write", "read_and_write", "admin"})

_TOKEN_RE = re.compile(
    r"(?i)\b("
    r"gh[pousr]_[A-Za-z0-9_]{8,}"
    r"|github_pat_[A-Za-z0-9_]{8,}"
    r"|gho_[A-Za-z0-9_]{8,}"
    r"|ghu_[A-Za-z0-9_]{8,}"
    r"|ghs_[A-Za-z0-9_]{8,}"
    r"|ghr_[A-Za-z0-9_]{8,}"
    r"|Bearer\s+[A-Za-z0-9\-._~+/]+=*"
    r")\b"
)
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"
)
_AUTH_HEADER_RE = re.compile(
    r"(?i)(authorization\s*[:=]\s*)(['\"]?)([^'\"\s,;]+)(['\"]?)"
)
_QUERY_TOKEN_RE = re.compile(r"(?i)([?&](?:access_token|token|auth)=)([^&\s]+)")
_SECRET_KEYS = frozenset(
    {
        "authorization",
        "token",
        "access_token",
        "password",
        "secret",
        "private_key",
        "privatekey",
        "installation_token",
        "cdb_gh_app_installation_token",
    }
)


@dataclass(frozen=True)
class PreflightResult:
    """Fail-closed preflight verdict for Phase-B operator readiness."""

    schema_version: str
    verdict: str
    ready: bool
    reasons: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    expected_repository: str = EXPECTED_REPOSITORY
    app_id: int | None = None
    installation_id: int | None = None
    checks_write: bool = False
    app_bound_check_run_names: list[str] = field(default_factory=list)
    live_readonly: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return redact_mapping(asdict(self))


def redact_text(value: str) -> str:
    """Redact token-like substrings from text. Never echo secrets."""
    if not value:
        return value
    redacted = _AUTH_HEADER_RE.sub(r"\1\2[REDACTED]\4", value)
    redacted = _QUERY_TOKEN_RE.sub(r"\1[REDACTED]", redacted)
    redacted = _PRIVATE_KEY_RE.sub("[REDACTED_PRIVATE_KEY]", redacted)
    redacted = _TOKEN_RE.sub("[REDACTED]", redacted)
    return redacted


def redact_mapping(payload: Any) -> Any:
    """Deep redaction for dict/list structures used in diagnostics."""
    if isinstance(payload, dict):
        out: dict[Any, Any] = {}
        for key, value in payload.items():
            key_str = str(key).lower()
            if key_str in _SECRET_KEYS or "token" in key_str or "secret" in key_str:
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_mapping(value)
        return out
    if isinstance(payload, list):
        return [redact_mapping(item) for item in payload]
    if isinstance(payload, str):
        return redact_text(payload)
    return payload


def _positive_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _permission_level(permissions: Mapping[str, Any], key: str) -> str:
    raw = permissions.get(key)
    if raw is None:
        return ""
    return str(raw).strip().lower()


def _has_checks_write(permissions: Mapping[str, Any]) -> bool:
    level = _permission_level(permissions, "checks")
    return level in _WRITE_LEVELS


def _prohibited_permission_findings(permissions: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    for key in sorted(_PROHIBITED_WRITE_PERMISSIONS):
        level = _permission_level(permissions, key)
        if level in _WRITE_LEVELS:
            findings.append(f"prohibited permission {key}={level}")
    return findings


def is_app_bound_check_run(
    check_run: Mapping[str, Any], *, expected_app_id: int | None = None
) -> bool:
    """Return True only when a Check Run is bound to a positive GitHub App id."""
    name = str(check_run.get("name") or "").strip()
    if name not in ALLOWED_CHECK_RUN_NAMES:
        return False
    app = check_run.get("app")
    app_id: int | None = None
    if isinstance(app, Mapping):
        app_id = _positive_int(app.get("id"))
    if app_id is None:
        app_id = _positive_int(check_run.get("app_id"))
    if app_id is None:
        return False
    if expected_app_id is not None and app_id != expected_app_id:
        return False
    return True


def is_app_bound_commit_status(status: Mapping[str, Any]) -> bool:
    """Commit Status with app_id=null is never App-bound (interim trust model)."""
    context = str(status.get("context") or status.get("name") or "").strip()
    if context != REQUIRED_CHECK_CONTEXT:
        return False
    app_id = status.get("app_id", status.get("appId"))
    if app_id is None:
        return False
    if isinstance(app_id, Mapping):
        app_id = app_id.get("id")
    return _positive_int(app_id) is not None


def evaluate_preflight(
    evidence: Mapping[str, Any] | None = None,
    *,
    live_readonly: Mapping[str, Any] | None = None,
) -> PreflightResult:
    """Evaluate App / Installation / permission / Check Run evidence fail-closed."""
    evidence = dict(evidence or {})
    live = dict(live_readonly or {})
    reasons: list[str] = []
    findings: list[str] = []

    app = evidence.get("app")
    if not isinstance(app, Mapping):
        app = {}
    permissions_raw = app.get("permissions") if isinstance(app, Mapping) else None
    permissions: Mapping[str, Any]
    if isinstance(permissions_raw, Mapping):
        permissions = permissions_raw
    else:
        permissions = {}

    app_id = _positive_int(app.get("id") if isinstance(app, Mapping) else None)
    if app_id is None:
        app_id = _positive_int(
            evidence.get("app_id") or evidence.get("expected_app_id")
        )

    installation = evidence.get("installation")
    if not isinstance(installation, Mapping):
        installation = {}
    installation_id = _positive_int(
        installation.get("id") if isinstance(installation, Mapping) else None
    )
    if installation_id is None:
        installation_id = _positive_int(
            evidence.get("installation_id") or evidence.get("expected_installation_id")
        )

    if app_id is None:
        reasons.append(REASON_APP_MISSING)
        findings.append("GitHub App id missing or not a positive integer")

    if installation_id is None:
        reasons.append(REASON_INSTALLATION_MISSING)
        findings.append("GitHub App installation id missing or not a positive integer")

    checks_write = _has_checks_write(permissions)
    if not checks_write:
        reasons.append(REASON_CHECKS_WRITE_MISSING)
        findings.append("app.permissions.checks must be write (or read_and_write)")

    for finding in _prohibited_permission_findings(permissions):
        reasons.append(REASON_PROHIBITED_PERMISSION)
        findings.append(finding)

    install_repo = ""
    if isinstance(installation, Mapping):
        install_repo = str(
            installation.get("repository")
            or installation.get("repository_full_name")
            or ""
        ).strip()
    if install_repo and install_repo != EXPECTED_REPOSITORY:
        findings.append(
            f"installation repository {install_repo!r} != {EXPECTED_REPOSITORY!r}"
        )
        if REASON_INSTALLATION_MISSING not in reasons:
            reasons.append(REASON_INSTALLATION_MISSING)

    # Commit statuses with app_id=null must never count as App-bound.
    commit_statuses = evidence.get("commit_statuses") or []
    if not isinstance(commit_statuses, list):
        commit_statuses = []
    for status in commit_statuses:
        if not isinstance(status, Mapping):
            continue
        context = str(status.get("context") or status.get("name") or "").strip()
        if context != REQUIRED_CHECK_CONTEXT:
            continue
        if is_app_bound_commit_status(status):
            findings.append(
                f"commit status {context} has app_id bound — unexpected interim model"
            )
        else:
            findings.append(
                f"commit status {context} app_id=null is not App-bound "
                f"({REASON_COMMIT_STATUS_NOT_APP_BOUND})"
            )
            if REASON_COMMIT_STATUS_NOT_APP_BOUND not in reasons:
                reasons.append(REASON_COMMIT_STATUS_NOT_APP_BOUND)

    check_runs = evidence.get("check_runs") or []
    if not isinstance(check_runs, list):
        check_runs = []

    app_bound: list[Mapping[str, Any]] = []
    mismatched: list[str] = []
    for run in check_runs:
        if not isinstance(run, Mapping):
            continue
        name = str(run.get("name") or "").strip()
        if name not in ALLOWED_CHECK_RUN_NAMES:
            continue
        if is_app_bound_check_run(run, expected_app_id=app_id):
            app_bound.append(run)
        elif is_app_bound_check_run(run, expected_app_id=None):
            mismatched.append(name)
            findings.append(
                f"check run {name!r} app.id does not match expected app_id={app_id}"
            )

    bound_names = sorted(
        {str(run.get("name") or "").strip() for run in app_bound if run.get("name")}
    )

    if mismatched and REASON_CHECK_RUN_APP_MISMATCH not in reasons:
        reasons.append(REASON_CHECK_RUN_APP_MISMATCH)

    if not app_bound:
        reasons.append(REASON_CHECK_RUN_MISSING)
        findings.append(
            "no unambiguous App-bound Check Run "
            f"(allowed names: {sorted(ALLOWED_CHECK_RUN_NAMES)})"
        )
    elif len(bound_names) > 1:
        # Multiple distinct allowed names both present is OK for shadow+required
        # only when each is uniquely bound; ambiguity = same name duplicated
        # with conflicting app identity already handled. Require exactly one
        # matching name for READY, preferring shadow preview for Phase B smoke.
        shadow = [n for n in bound_names if n == SHADOW_CHECK_RUN_NAME]
        required = [n for n in bound_names if n == CHECK_RUN_NAME]
        if shadow and required:
            findings.append(
                "both shadow and required App-bound Check Runs present; "
                "operator smoke should use shadow name only before BP cutover"
            )
        # Still ready if at least one unambiguous App-bound run matches app_id.
    else:
        # Deduplicate same-name runs: more than one run with same name+app is fine;
        # conflicting apps already filtered.
        pass

    # Ambiguity: same allowed name appears with different positive app ids.
    by_name: dict[str, set[int]] = {}
    for run in check_runs:
        if not isinstance(run, Mapping):
            continue
        name = str(run.get("name") or "").strip()
        if name not in ALLOWED_CHECK_RUN_NAMES:
            continue
        app_obj = run.get("app")
        rid: int | None = None
        if isinstance(app_obj, Mapping):
            rid = _positive_int(app_obj.get("id"))
        if rid is None:
            rid = _positive_int(run.get("app_id"))
        if rid is None:
            continue
        by_name.setdefault(name, set()).add(rid)
    for name, ids in by_name.items():
        if len(ids) > 1:
            reasons.append(REASON_CHECK_RUN_AMBIGUOUS)
            findings.append(
                f"check run name {name!r} bound to multiple app ids: {sorted(ids)}"
            )

    blocking = {
        REASON_APP_MISSING,
        REASON_INSTALLATION_MISSING,
        REASON_CHECKS_WRITE_MISSING,
        REASON_PROHIBITED_PERMISSION,
        REASON_CHECK_RUN_MISSING,
        REASON_CHECK_RUN_AMBIGUOUS,
        REASON_CHECK_RUN_APP_MISMATCH,
    }
    blocked = bool(blocking.intersection(reasons))
    if not blocked and app_bound:
        reasons.append(REASON_READY)
        verdict = VERDICT_READY
        ready = True
    else:
        verdict = VERDICT_NOT_READY
        ready = False

    if live:
        findings.append(f"{REASON_LIVE_READONLY}: live read-only observation attached")

    # Stable unique reason order
    seen: set[str] = set()
    ordered_reasons: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            ordered_reasons.append(reason)

    return PreflightResult(
        schema_version=SCHEMA_VERSION,
        verdict=verdict,
        ready=ready,
        reasons=ordered_reasons,
        findings=findings,
        expected_repository=EXPECTED_REPOSITORY,
        app_id=app_id,
        installation_id=installation_id,
        checks_write=checks_write,
        app_bound_check_run_names=bound_names,
        live_readonly=dict(live),
    )


def load_evidence_file(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("evidence file must be a JSON object")
    return raw


def _gh_api_json(path: str) -> Any:
    """Read-only GitHub API via gh CLI. Never prints auth headers or tokens."""
    completed = subprocess.run(
        ["gh", "api", path],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        err = redact_text(
            (completed.stderr or "").strip()
            or (completed.stdout or "").strip()
            or "gh api failed"
        )
        raise RuntimeError(err)
    stdout = completed.stdout
    if stdout is None or not str(stdout).strip():
        raise RuntimeError(f"gh api returned empty body for {path}")
    return json.loads(stdout)


def collect_live_readonly(*, owner_repo: str = EXPECTED_REPOSITORY) -> dict[str, Any]:
    """Observe Branch Protection + commit statuses/check-runs without App credentials."""
    owner, repo = owner_repo.split("/", 1)
    live: dict[str, Any] = {
        "repository": owner_repo,
        "credential_free": True,
        "note": (
            "Does not read CDB_GH_APP_INSTALLATION_TOKEN or private keys; "
            "uses operator gh auth for repository metadata only."
        ),
    }
    try:
        protection = _gh_api_json(f"repos/{owner}/{repo}/branches/main/protection")
        contexts = (
            (protection.get("required_status_checks") or {}).get("contexts")
            if isinstance(protection, dict)
            else None
        )
        live["branch_protection"] = {
            "required_contexts": contexts,
            "strict": (
                (protection.get("required_status_checks") or {}).get("strict")
                if isinstance(protection, dict)
                else None
            ),
            "enforce_admins": (
                (protection.get("enforce_admins") or {}).get("enabled")
                if isinstance(protection, dict)
                else None
            ),
        }
    except Exception as exc:  # noqa: BLE001 — fail-closed observation
        live["branch_protection_error"] = redact_text(str(exc))

    try:
        ref = _gh_api_json(f"repos/{owner}/{repo}/git/ref/heads/main")
        sha = ((ref.get("object") or {}) if isinstance(ref, dict) else {}).get("sha")
        live["main_sha"] = sha
        if sha:
            status_payload = _gh_api_json(f"repos/{owner}/{repo}/commits/{sha}/status")
            statuses = []
            if isinstance(status_payload, dict):
                for item in status_payload.get("statuses") or []:
                    if not isinstance(item, Mapping):
                        continue
                    statuses.append(
                        {
                            "context": item.get("context"),
                            "state": item.get("state"),
                            "app_id": None,
                            "creator": (
                                (item.get("creator") or {}).get("login")
                                if isinstance(item.get("creator"), Mapping)
                                else None
                            ),
                        }
                    )
            live["commit_statuses"] = statuses
            checks_payload = _gh_api_json(
                f"repos/{owner}/{repo}/commits/{sha}/check-runs"
            )
            check_runs = []
            if isinstance(checks_payload, dict):
                for item in checks_payload.get("check_runs") or []:
                    if not isinstance(item, Mapping):
                        continue
                    app = (
                        item.get("app") if isinstance(item.get("app"), Mapping) else {}
                    )
                    check_runs.append(
                        {
                            "name": item.get("name"),
                            "head_sha": item.get("head_sha"),
                            "conclusion": item.get("conclusion"),
                            "app": {
                                "id": (
                                    app.get("id") if isinstance(app, Mapping) else None
                                )
                            },
                        }
                    )
            live["check_runs"] = check_runs
    except Exception as exc:  # noqa: BLE001 — fail-closed observation
        live["commit_observation_error"] = redact_text(str(exc))

    return redact_mapping(live)


def merge_live_into_evidence(
    evidence: dict[str, Any], live: Mapping[str, Any]
) -> dict[str, Any]:
    """Attach live observations without inventing App/Installation posture."""
    merged = dict(evidence)
    if "commit_statuses" not in merged and live.get("commit_statuses"):
        merged["commit_statuses"] = list(live["commit_statuses"])  # type: ignore[arg-type]
    if "check_runs" not in merged and live.get("check_runs"):
        merged["check_runs"] = list(live["check_runs"])  # type: ignore[arg-type]
    return merged


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Credential-free GitHub App Check Run cutover preflight "
            "(#4170 Phase B). Read-only; no App install; no BP mutation."
        )
    )
    parser.add_argument(
        "--evidence-file",
        help="JSON evidence snapshot (app, installation, permissions, check_runs)",
    )
    parser.add_argument(
        "--live-readonly",
        action="store_true",
        help="Observe live BP/status/check-runs via gh api (no App tokens)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit redacted JSON result",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    evidence: dict[str, Any] = {}
    if args.evidence_file:
        evidence = load_evidence_file(args.evidence_file)

    live: dict[str, Any] = {}
    if args.live_readonly:
        live = collect_live_readonly()
        evidence = merge_live_into_evidence(evidence, live)

    result = evaluate_preflight(evidence, live_readonly=live)
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"verdict={result.verdict}")
        print(f"ready={result.ready}")
        print(f"reasons={','.join(result.reasons) or '(none)'}")
        for finding in result.findings:
            print(f"- {redact_text(finding)}")
    return 0 if result.ready else 2


if __name__ == "__main__":
    sys.exit(main())
