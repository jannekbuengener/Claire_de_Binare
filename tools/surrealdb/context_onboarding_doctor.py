"""Read-only context onboarding doctor for local SurrealDB / MCP preflight.

Validates local Context Intelligence prerequisites without dangerous actions,
secret output, DB writes, or stack mutation.

Issue: #2642
Epic: #1976

Usage:
    python -m tools.surrealdb.context_onboarding_doctor
    python -m tools.surrealdb.context_onboarding_doctor --format json
    make context-doctor

Exit codes:
    0 - core checks OK or only non-blocking warnings (e.g. MCP port down)
    1 - onboarding not usable (missing secrets/config/DB/schema)
    2 - CLI usage error
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from tools.surrealdb.local_schema_check import (
    DEFAULT_DB,
    DEFAULT_NS,
    DEFAULT_SURREAL_URL,
    EXPECTED_TABLES,
)

MCP_HOST = "127.0.0.1"
MCP_PORT = 8811
SURREALDB_URL = DEFAULT_SURREAL_URL
CONTEXT_QUERY_LOCAL_REL = Path(
    "infrastructure/config/surrealdb/context_query.local.yaml"
)
CONTEXT_QUERY_EXAMPLE_REL = Path(
    "infrastructure/config/surrealdb/context_query.local.example.yaml"
)
SURREALDB_ENV_FILENAME = "SURREALDB_ENV"
SURREALDB_ENV_EXAMPLE_REL = Path(
    "infrastructure/config/surrealdb/SURREALDB_ENV.example"
)

EnvVarStatus = Literal["set_valid", "set_invalid", "unset"]
ResolvedSource = Literal[
    "CDB_CONTEXT_SECRETS_PATH", "SECRETS_PATH", "canon_default", "none"
]
ReachableStatus = Literal["reachable", "not_reachable", "skipped"]
CheckStatus = Literal["ok", "fail", "skipped", "unsupported"]
StoreStatus = Literal["exists", "missing"]
ConfigStatus = Literal["exists", "missing"]

FORBIDDEN_OUTPUT_SUBSTRINGS = (
    "SURREAL_PASS",
    "SURREAL_USER=",
    "super-secret-password",
    "sentinel://fake-secrets-path",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _canon_default_secrets_dir() -> Path:
    if os.name == "nt":
        userprofile = os.environ.get("USERPROFILE", "").strip()
        if userprofile:
            return Path(userprofile) / "Documents" / ".secrets" / ".cdb"
    return Path.home() / "Documents" / ".secrets" / ".cdb"


def evaluate_env_var(name: str, environ: dict[str, str] | None = None) -> EnvVarStatus:
    """Classify an env var as unset, set_invalid, or set_valid directory."""
    env = os.environ if environ is None else environ
    raw = env.get(name, "").strip()
    if not raw:
        return "unset"
    path = Path(raw)
    try:
        if path.is_dir():
            return "set_valid"
    except OSError:
        pass
    return "set_invalid"


def _candidate_secrets_dirs(
    environ: dict[str, str] | None = None,
) -> list[tuple[ResolvedSource, Path]]:
    env = os.environ if environ is None else environ
    candidates: list[tuple[ResolvedSource, Path]] = []

    for env_key, source in (
        ("CDB_CONTEXT_SECRETS_PATH", "CDB_CONTEXT_SECRETS_PATH"),
        ("SECRETS_PATH", "SECRETS_PATH"),
    ):
        raw = env.get(env_key, "").strip()
        if raw:
            candidates.append((source, Path(raw)))

    candidates.append(("canon_default", _canon_default_secrets_dir()))
    return candidates


@dataclass(frozen=True)
class SecretsResolution:
    resolved_source: ResolvedSource
    canon_store: StoreStatus
    surrealdb_env: StoreStatus
    resolved_dir: Path | None = None


def resolve_secrets_dir(
    environ: dict[str, str] | None = None,
) -> SecretsResolution:
    for source, path in _candidate_secrets_dirs(environ):
        try:
            if path.is_dir():
                env_file = path / SURREALDB_ENV_FILENAME
                return SecretsResolution(
                    resolved_source=source,
                    canon_store="exists",
                    surrealdb_env="exists" if env_file.is_file() else "missing",
                    resolved_dir=path,
                )
        except OSError:
            continue
    return SecretsResolution(
        resolved_source="none",
        canon_store="missing",
        surrealdb_env="missing",
        resolved_dir=None,
    )


def check_tcp_reachable(
    host: str,
    port: int,
    timeout: float = 2.0,
    connector: Callable[[str, int, float], bool] | None = None,
) -> bool:
    if connector is not None:
        return connector(host, port, timeout)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_http_ok(
    url: str,
    timeout: float = 3.0,
    opener: Callable[[str, float], int | None] | None = None,
) -> bool:
    if opener is not None:
        status = opener(url, timeout)
        return status == 200
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return int(response.status) == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _load_credentials(env_file: Path) -> tuple[str, str] | None:
    if not env_file.is_file():
        return None
    user: str | None = None
    password: str | None = None
    try:
        with env_file.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("SURREAL_USER="):
                    user = stripped[len("SURREAL_USER=") :]
                elif stripped.startswith("SURREAL_PASS="):
                    password = stripped[len("SURREAL_PASS=") :]
    except OSError:
        return None
    if not user or not password:
        return None
    return user, password


def _sql_request(
    url: str,
    sql: str,
    user: str,
    password: str,
    ns: str,
    db: str,
    timeout: float = 10.0,
) -> tuple[int, bytes]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {
        "Accept": "application/json",
        "Content-Type": "text/plain",
        "Authorization": f"Basic {token}",
        "surreal-ns": ns,
        "surreal-db": db,
    }
    req = urllib.request.Request(
        f"{url}/sql", data=sql.encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _read_auth_mode(config_path: Path) -> str | None:
    if not config_path.is_file():
        return None
    try:
        import yaml  # noqa: PLC0415 — optional parse for doctor only

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    auth_mode = data.get("auth_mode")
    return auth_mode if isinstance(auth_mode, str) else None


def check_schema_readonly(
    url: str,
    user: str,
    password: str,
    ns: str = DEFAULT_NS,
    db: str = DEFAULT_DB,
    sql_request: Callable[..., tuple[int, bytes]] | None = None,
) -> CheckStatus:
    request = _sql_request if sql_request is None else sql_request
    status, body = request(url, "INFO FOR DB;", user, password, ns, db)
    if status not in (200, 204):
        return "fail"
    try:
        response = json.loads(body)
        if not isinstance(response, list) or not response:
            return "fail"
        result = response[0].get("result", {})
        if not isinstance(result, dict):
            return "fail"
        tables_in_db = set(result.get("tables", {}).keys())
    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
        return "fail"
    missing = [table for table in EXPECTED_TABLES if table not in tables_in_db]
    return "ok" if not missing else "fail"


@dataclass
class DoctorReport:
    mcp_server_status: ReachableStatus = "skipped"
    surrealdb_status: ReachableStatus = "skipped"
    surrealdb_health: CheckStatus = "skipped"
    surrealdb_version: CheckStatus = "skipped"
    surrealdb_schema: CheckStatus = "skipped"
    secrets_path_env: EnvVarStatus = "unset"
    cdb_context_secrets_path_env: EnvVarStatus = "unset"
    secrets_resolved_source: ResolvedSource = "none"
    secrets_canon_store: StoreStatus = "missing"
    secrets_surrealdb_env: StoreStatus = "missing"
    config_context_query_local: ConfigStatus = "missing"
    next_action: str = "no action required"
    lr_note: str = "NO-GO"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcp_server": {"status": self.mcp_server_status},
            "surrealdb": {
                "status": self.surrealdb_status,
                "health": self.surrealdb_health,
                "version": self.surrealdb_version,
                "schema": self.surrealdb_schema,
            },
            "env": {
                "SECRETS_PATH": self.secrets_path_env,
                "CDB_CONTEXT_SECRETS_PATH": self.cdb_context_secrets_path_env,
            },
            "secrets": {
                "resolved_source": self.secrets_resolved_source,
                "canon_store": self.secrets_canon_store,
                "surrealdb_env": self.secrets_surrealdb_env,
            },
            "config": {
                "context_query_local": self.config_context_query_local,
            },
            "next_action": self.next_action,
            "lr_note": self.lr_note,
            "warnings": list(self.warnings),
        }


def prioritize_next_action(report: DoctorReport) -> str:
    if report.secrets_canon_store == "missing":
        return "set SECRETS_PATH or CDB_CONTEXT_SECRETS_PATH"
    if report.secrets_surrealdb_env == "missing":
        return (
            "create SURREALDB_ENV from "
            "infrastructure/config/surrealdb/SURREALDB_ENV.example"
        )
    if report.config_context_query_local == "missing":
        return (
            "create context_query.local.yaml from " "context_query.local.example.yaml"
        )
    if report.surrealdb_status == "not_reachable":
        return "start local SurrealDB with make context-up"
    if report.surrealdb_health == "fail" or report.surrealdb_version == "fail":
        return "start local SurrealDB with make context-up"
    if report.surrealdb_schema == "fail":
        return "run make context-schema-apply"
    infra_ready = (
        report.secrets_canon_store == "exists"
        and report.secrets_surrealdb_env == "exists"
        and report.config_context_query_local == "exists"
        and report.surrealdb_status == "reachable"
        and report.surrealdb_health == "ok"
        and report.surrealdb_version == "ok"
        and report.surrealdb_schema in ("ok", "unsupported", "skipped")
    )
    if infra_ready and report.mcp_server_status == "not_reachable":
        return (
            "configure MCP host for 127.0.0.1:8811 or use stdio cdb_context "
            "via claire-de-binare.mcp.json"
        )
    if infra_ready:
        return "no action required"
    return "no action required"


def compute_exit_code(report: DoctorReport) -> int:
    blocking = (
        report.secrets_canon_store == "missing"
        or report.secrets_surrealdb_env == "missing"
        or report.config_context_query_local == "missing"
        or report.surrealdb_status == "not_reachable"
        or report.surrealdb_health == "fail"
        or report.surrealdb_version == "fail"
        or report.surrealdb_schema == "fail"
    )
    return 1 if blocking else 0


def build_report(
    repo_root: Path | None = None,
    *,
    skip_mcp: bool = False,
    skip_schema: bool = False,
    environ: dict[str, str] | None = None,
    tcp_checker: Callable[[str, int, float], bool] | None = None,
    http_checker: Callable[[str, float], bool] | None = None,
    schema_checker: Callable[..., CheckStatus] | None = None,
) -> DoctorReport:
    root = _repo_root() if repo_root is None else repo_root
    report = DoctorReport()

    report.secrets_path_env = evaluate_env_var("SECRETS_PATH", environ)
    report.cdb_context_secrets_path_env = evaluate_env_var(
        "CDB_CONTEXT_SECRETS_PATH", environ
    )

    secrets = resolve_secrets_dir(environ)
    report.secrets_resolved_source = secrets.resolved_source
    report.secrets_canon_store = secrets.canon_store
    report.secrets_surrealdb_env = secrets.surrealdb_env

    config_path = root / CONTEXT_QUERY_LOCAL_REL
    report.config_context_query_local = "exists" if config_path.is_file() else "missing"

    if skip_mcp:
        report.mcp_server_status = "skipped"
    else:
        report.mcp_server_status = (
            "reachable"
            if check_tcp_reachable(MCP_HOST, MCP_PORT, connector=tcp_checker)
            else "not_reachable"
        )
        if report.mcp_server_status == "not_reachable":
            report.warnings.append(
                "MCP HTTP port 127.0.0.1:8811 is not reachable; "
                "stdio cdb_context may still work"
            )

    surreal_reachable = check_tcp_reachable(
        "127.0.0.1",
        8010,
        connector=tcp_checker,
    )
    report.surrealdb_status = "reachable" if surreal_reachable else "not_reachable"

    if not surreal_reachable:
        report.surrealdb_health = "skipped"
        report.surrealdb_version = "skipped"
        report.surrealdb_schema = "skipped"
    else:
        health_url = f"{SURREALDB_URL}/health"
        version_url = f"{SURREALDB_URL}/version"
        report.surrealdb_health = (
            "ok" if check_http_ok(health_url, opener=http_checker) else "fail"
        )
        report.surrealdb_version = (
            "ok" if check_http_ok(version_url, opener=http_checker) else "fail"
        )

        if skip_schema:
            report.surrealdb_schema = "skipped"
        elif report.config_context_query_local == "exists":
            auth_mode = _read_auth_mode(config_path)
            if auth_mode == "none":
                report.surrealdb_schema = "unsupported"
            elif secrets.resolved_dir is None or secrets.surrealdb_env == "missing":
                report.surrealdb_schema = "skipped"
            else:
                creds = _load_credentials(secrets.resolved_dir / SURREALDB_ENV_FILENAME)
                if creds is None:
                    report.surrealdb_schema = "skipped"
                else:
                    user, password = creds
                    checker = (
                        check_schema_readonly
                        if schema_checker is None
                        else schema_checker
                    )
                    report.surrealdb_schema = checker(SURREALDB_URL, user, password)
        else:
            report.surrealdb_schema = "skipped"

    report.next_action = prioritize_next_action(report)
    return report


def format_report(report: DoctorReport, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if fmt != "text":
        raise ValueError(f"unsupported format: {fmt!r}")

    lines = [
        "=== Context Onboarding Doctor ===",
        f"lr_note: {report.lr_note}",
        "",
        f"mcp_server.status: {report.mcp_server_status}",
        f"surrealdb.status: {report.surrealdb_status}",
        f"surrealdb.health: {report.surrealdb_health}",
        f"surrealdb.version: {report.surrealdb_version}",
        f"surrealdb.schema: {report.surrealdb_schema}",
        "",
        f"env.SECRETS_PATH: {report.secrets_path_env}",
        f"env.CDB_CONTEXT_SECRETS_PATH: {report.cdb_context_secrets_path_env}",
        f"secrets.resolved_source: {report.secrets_resolved_source}",
        f"secrets.canon_store: {report.secrets_canon_store}",
        f"secrets.surrealdb_env: {report.secrets_surrealdb_env}",
        f"config.context_query_local: {report.config_context_query_local}",
        "",
        f"next_action: {report.next_action}",
    ]
    if report.warnings:
        lines.append("")
        lines.append("warnings:")
        for warning in report.warnings:
            lines.append(f"  - {warning}")
    return "\n".join(lines)


def _validate_output_safe(text: str) -> None:
    for forbidden in FORBIDDEN_OUTPUT_SUBSTRINGS:
        if forbidden in text:
            raise ValueError(f"output contains forbidden substring: {forbidden}")


_HELP_EPILOG = """\
Examples:
  python -m tools.surrealdb.context_onboarding_doctor
  python -m tools.surrealdb.context_onboarding_doctor --format json
  python -m tools.surrealdb.context_onboarding_doctor --skip-mcp --skip-schema
  make context-doctor

Exit codes:
  0  checks OK or only non-blocking warnings
  1  onboarding not usable (missing secrets/config/DB/schema)
  2  CLI usage error
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for local Context Intelligence onboarding.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_HELP_EPILOG,
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )
    parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip MCP TCP reachability check",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip read-only SurrealDB schema check",
    )
    args = parser.parse_args(argv)

    if args.format not in ("text", "json"):
        print("ERROR: unsupported --format", file=sys.stderr)
        return 2

    report = build_report(
        args.repo_root,
        skip_mcp=args.skip_mcp,
        skip_schema=args.skip_schema,
    )
    output = format_report(report, args.format)
    _validate_output_safe(output)
    print(output)
    return compute_exit_code(report)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
