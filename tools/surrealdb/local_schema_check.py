"""Local SurrealDB schema check — verifies context_intelligence_v0 tables exist.

Local-only guard enforced. No credential output. Exits 0 if all expected tables
are present, exits 1 if tables are missing. Exits 0 gracefully if container is
offline (container absence is not an error condition during development).

Issues:
    #2395 - Local schema apply and reset workflow
    Parent: #2391
    Epic: #1976

Usage:
    python tools/surrealdb/local_schema_check.py
    python tools/surrealdb/local_schema_check.py --url http://127.0.0.1:8010

Guardrails:
    - Only connects to 127.0.0.1 or localhost
    - No credential values are ever printed
    - Graceful exit when container is not running
    - LR-Go remains NO-GO; this script has no effect on live-readiness
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOCAL_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
DEFAULT_SURREAL_URL = "http://127.0.0.1:8010"
DEFAULT_NS = "cdb_context_local"
DEFAULT_DB = "cdb_context_intel"

# Tables expected from context_intelligence_v0.surql
EXPECTED_TABLES = [
    "repo_artifact",
    "code_symbol",
    "doc_page",
    "doc_section",
    "doc_chunk",
    "concept",
    "dependency_edge",
    "evidence_ref",
    "claim",
    "decision_event",
    "agent_memory",
    "context_query",
    "audit_observation",
    "contradiction",
    "stale_context",
    "scope_drift_event",
    "knowledge_quality_score",
    "visual_control_view",
]


def _resolve_env_file(secrets_path: str | None = None) -> Path:
    if secrets_path is None:
        secrets_path = os.environ.get(
            "SECRETS_PATH",
            str(Path.home() / "Documents" / ".secrets" / ".cdb"),
        )
    return Path(secrets_path) / "SURREALDB_ENV"


def _load_credentials(env_file: Path) -> tuple[str, str]:
    """Load credentials from env file. Never prints values."""
    if not env_file.exists():
        print(f"ERROR: SURREALDB_ENV not found at {env_file}", file=sys.stderr)
        print(
            "       Create it from infrastructure/config/surrealdb/SURREALDB_ENV.example",
            file=sys.stderr,
        )
        sys.exit(1)

    user: str | None = None
    password: str | None = None
    with env_file.open() as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("SURREAL_USER="):
                user = stripped[len("SURREAL_USER="):]
            elif stripped.startswith("SURREAL_PASS="):
                password = stripped[len("SURREAL_PASS="):]

    if not user or not password:
        print(
            "ERROR: SURREALDB_ENV missing SURREAL_USER or SURREAL_PASS",
            file=sys.stderr,
        )
        sys.exit(1)

    return user, password


def _guard_local(url: str) -> None:
    """Hard-reject any non-local target."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host not in LOCAL_ALLOWED_HOSTS:
        print(
            f"ERROR: Non-local target rejected: {host!r}  Allowed: {sorted(LOCAL_ALLOWED_HOSTS)}",
            file=sys.stderr,
        )
        sys.exit(2)


def _health_check(url: str) -> bool:
    """Return True if SurrealDB health endpoint responds OK."""
    try:
        resp = urllib.request.urlopen(f"{url}/health", timeout=3)
        return resp.status == 200
    except Exception:
        return False


def _sql_request(
    url: str,
    sql: str,
    user: str,
    password: str,
    ns: str,
    db: str,
) -> tuple[int, bytes]:
    """Execute SQL via SurrealDB HTTP API. Returns (status_code, body)."""
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check context_intelligence_v0 schema presence in local SurrealDB."
    )
    parser.add_argument("--url", default=DEFAULT_SURREAL_URL)
    parser.add_argument("--ns", default=DEFAULT_NS)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--secrets-path", default=None)
    args = parser.parse_args()

    _guard_local(args.url)

    print(f"[INFO] Checking container at {args.url}/health...")
    if not _health_check(args.url):
        print("[WARN] cdb_surrealdb not reachable. Container may not be running.")
        print("       Run 'make context-up' to start the container.")
        print("[SKIP] Schema check skipped (container offline).")
        sys.exit(0)

    print("[OK] Container reachable.")

    env_file = _resolve_env_file(args.secrets_path)
    user, password = _load_credentials(env_file)

    print(f"[INFO] Querying NS={args.ns}  DB={args.db}...")
    status, body = _sql_request(
        args.url, "INFO FOR DB;", user, password, args.ns, args.db
    )

    if status not in (200, 204):
        print(f"ERROR: INFO FOR DB failed (HTTP {status})", file=sys.stderr)
        sys.exit(5)

    tables_in_db: set[str] = set()
    try:
        response = json.loads(body)
        if isinstance(response, list) and response:
            result = response[0].get("result", {})
            if isinstance(result, dict):
                tables_in_db = set(result.get("tables", {}).keys())
    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
        print("ERROR: Could not parse INFO FOR DB response", file=sys.stderr)
        sys.exit(5)

    print(f"\n=== Schema Check: context_intelligence_v0 ===")
    print(f"Target : {args.url} / NS={args.ns} / DB={args.db}")
    print(f"Expected: {len(EXPECTED_TABLES)} tables\n")

    missing = []
    present = []
    for table in EXPECTED_TABLES:
        if table in tables_in_db:
            print(f"  [OK]      {table}")
            present.append(table)
        else:
            print(f"  [MISSING] {table}")
            missing.append(table)

    extra = sorted(tables_in_db - set(EXPECTED_TABLES))
    if extra:
        print(f"\n  Extra tables (not in v0 schema): {extra}")

    print(f"\nSummary: {len(present)}/{len(EXPECTED_TABLES)} tables present")
    if missing:
        print(f"Missing : {missing}")
        print("Action  : Run 'make context-schema-apply' to apply the schema.")
        sys.exit(1)
    else:
        print("[OK] All expected v0 tables present.")
        print("NOTE: This is local context infrastructure only — not a Live/Trading Go.")
        sys.exit(0)


if __name__ == "__main__":
    main()
