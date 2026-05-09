"""Local SurrealDB reset — removes data from context-intelligence tables only.

DESTRUCTIVE. Local-only guard enforced. Requires explicit --confirm flag.
Trading/live/risk/governance tables are hard-blocked and never touched.
Schema definitions (DEFINE TABLE) are preserved — only record data is cleared.

Issues:
    #2395 - Local schema apply and reset workflow
    Parent: #2391
    Epic: #1976

Usage:
    python tools/surrealdb/local_reset.py --confirm
    python tools/surrealdb/local_reset.py --confirm --url http://127.0.0.1:8010

Guardrails:
    - Only connects to 127.0.0.1 or localhost (hard-reject)
    - --confirm is REQUIRED; no silent destructive operations
    - Only CONTEXT_INTELLIGENCE_TABLES are cleared (DELETE, not REMOVE TABLE)
    - FORBIDDEN_TABLES are never touched — any attempt hard-exits with code 2
    - No credential values are ever printed
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

# ONLY these context-intelligence tables may be cleared.
CONTEXT_INTELLIGENCE_TABLES = [
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

# Trading/live/governance tables that MUST NEVER be touched.
FORBIDDEN_TABLES: frozenset[str] = frozenset(
    {
        "orders",
        "fills",
        "positions",
        "balances",
        "pnl",
        "risk_state",
        "execution_state",
        "governance_event",
        "governance_decision",
        "governance_state",
    }
)


def _check_delete_result(table: str, body: bytes) -> None:
    """Parse SurrealDB /sql response for a single DELETE statement.

    SurrealDB returns HTTP 200 even when the statement fails (e.g. table not
    defined, permission denied, incompatible version). Requires every result
    item to carry ``status == "OK"``; any ``"ERR"`` or missing/unexpected
    field is treated as a fatal failure for that table.

    Raises ValueError with an operator-friendly message on any failure.
    """
    try:
        raw = body.decode("utf-8", errors="replace")
    except Exception as exc:
        raise ValueError(f"response body not decodable: {exc}") from exc

    if not raw.strip():
        raise ValueError(
            "response body is empty — expected JSON array from SurrealDB /sql"
        )

    try:
        results = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"response body is not valid JSON: {exc} "
            f"(first 400 chars: {raw[:400]!r})"
        ) from exc

    if not isinstance(results, list):
        raise ValueError(
            f"expected JSON array from /sql, got {type(results).__name__}: "
            f"{raw[:400]!r}"
        )

    stmt_errors: list[str] = []
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            stmt_errors.append(
                f"statement {idx}: expected object, got {type(item).__name__}"
            )
            continue
        stmt_status = item.get("status")
        if stmt_status is None:
            stmt_errors.append(
                f"statement {idx}: missing 'status' field ({str(item)[:120]})"
            )
        elif stmt_status != "OK":
            detail = item.get("detail") or item.get("result") or ""
            stmt_errors.append(
                f"statement {idx}: status={stmt_status!r} — {str(detail)[:200]}"
            )

    if stmt_errors:
        raise ValueError(
            f"DELETE {table} failed:\n" + "\n".join(f"  {e}" for e in stmt_errors)
        )


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
    """Hard-reject any non-local target. Reset is local-dev only."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host not in LOCAL_ALLOWED_HOSTS:
        print(
            f"ERROR: Remote/production target rejected: {host!r}",
            file=sys.stderr,
        )
        print(
            "       Reset is ONLY allowed on local dev instances (127.0.0.1 / localhost).",
            file=sys.stderr,
        )
        sys.exit(2)


def _guard_no_forbidden(tables: list[str]) -> None:
    """Hard-exit if any forbidden (trading/live) table is in the reset list."""
    overlap = FORBIDDEN_TABLES & set(tables)
    if overlap:
        print(
            f"ERROR: Forbidden tables in reset list: {sorted(overlap)}",
            file=sys.stderr,
        )
        print(
            "       Trading/live/governance tables must never be cleared by this script.",
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
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "DESTRUCTIVE: Clear all record data from context-intelligence tables "
            "in local SurrealDB. Trading/live tables are never touched. "
            "Schema definitions (DEFINE TABLE) are preserved."
        )
    )
    parser.add_argument("--url", default=DEFAULT_SURREAL_URL)
    parser.add_argument("--ns", default=DEFAULT_NS)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--secrets-path", default=None)
    parser.add_argument(
        "--confirm",
        action="store_true",
        required=True,
        help="REQUIRED: Explicit confirmation that this is a destructive local reset.",
    )
    args = parser.parse_args()

    # Hard guards
    _guard_local(args.url)
    _guard_no_forbidden(CONTEXT_INTELLIGENCE_TABLES)

    print("=== LOCAL RESET: context_intelligence_v0 ===")
    print("DESTRUCTIVE: All record data in context-intelligence tables will be cleared.")
    print("Trading / live / risk / governance tables are NOT touched.")
    print("Schema definitions (DEFINE TABLE) are preserved.")
    print(f"Target : {args.url} / NS={args.ns} / DB={args.db}")
    print("")

    env_file = _resolve_env_file(args.secrets_path)
    user, password = _load_credentials(env_file)

    if not _health_check(args.url):
        print(
            f"ERROR: cdb_surrealdb not reachable at {args.url}/health",
            file=sys.stderr,
        )
        print("       Run 'make context-up' to start the container.", file=sys.stderr)
        sys.exit(4)

    print("[OK] Container healthy.")
    print(f"[INFO] Clearing {len(CONTEXT_INTELLIGENCE_TABLES)} context-intelligence tables...")
    print("")

    errors: list[str] = []
    for table in CONTEXT_INTELLIGENCE_TABLES:
        # Double-check: skip if somehow in forbidden set (belt-and-suspenders)
        if table in FORBIDDEN_TABLES:
            print(f"  [GUARD] Skipping forbidden table: {table}", file=sys.stderr)
            continue
        sql = f"DELETE {table};"
        status, body = _sql_request(args.url, sql, user, password, args.ns, args.db)
        if status not in (200, 204):
            print(f"  [WARN] {table}: unexpected HTTP status={status}", file=sys.stderr)
            errors.append(table)
            continue
        # HTTP 200 is not sufficient — SurrealDB returns 200 even when the
        # statement fails. Parse each result and require status == "OK".
        try:
            _check_delete_result(table, body)
            print(f"  [OK] {table}: cleared")
        except ValueError as exc:
            print(f"  [WARN] {table}: {exc}", file=sys.stderr)
            errors.append(table)

    print("")
    if errors:
        print(f"[WARN] Some tables had errors: {errors}", file=sys.stderr)
        print("       Schema definitions remain intact.", file=sys.stderr)
        sys.exit(1)
    else:
        print("[OK] Local context reset complete.")
        print("     Schema definitions (DEFINE TABLE) preserved.")
        print("     Run 'make context-schema-apply' to re-apply schema if needed.")
        print("NOTE: This was a local context reset only — not a Live/Trading Go.")


if __name__ == "__main__":
    main()
