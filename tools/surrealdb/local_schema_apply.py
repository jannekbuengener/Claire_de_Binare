"""Local SurrealDB schema apply — context_intelligence_v0.

Local-only guard enforced. Reads credentials from SECRETS_PATH.
No credential output. No remote/production target allowed.

Issues:
    #2395 - Local schema apply and reset workflow
    Parent: #2391
    Epic: #1976

Usage:
    python tools/surrealdb/local_schema_apply.py
    python tools/surrealdb/local_schema_apply.py --url http://127.0.0.1:8010
    python tools/surrealdb/local_schema_apply.py --dry-run

Guardrails:
    - Only connects to 127.0.0.1 or localhost (hard-reject all other hosts)
    - No credential values are ever printed
    - No trading/live/risk tables are touched (schema is context-intelligence only)
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

# Schema file path relative to repo root
_REPO_ROOT = Path(__file__).parent.parent.parent
SCHEMA_FILE = _REPO_ROOT / "infrastructure" / "surrealdb" / "context_intelligence_v0.surql"


def _resolve_env_file(secrets_path: str | None = None) -> Path:
    if secrets_path is None:
        secrets_path = os.environ.get(
            "SECRETS_PATH",
            str(Path.home() / "Documents" / ".secrets" / ".cdb"),
        )
    return Path(secrets_path) / "SURREALDB_ENV"


def _load_credentials(env_file: Path) -> tuple[str, str]:
    """Load credentials from env file. Returns (user, pass). Never prints values."""
    if not env_file.exists():
        print(f"ERROR: SURREALDB_ENV not found at {env_file}", file=sys.stderr)
        print(
            "       Create it from infrastructure/config/surrealdb/SURREALDB_ENV.example",
            file=sys.stderr,
        )
        print(
            "       and store the real file outside the repository.",
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

    if not user:
        print("ERROR: SURREALDB_ENV missing field SURREAL_USER", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("ERROR: SURREALDB_ENV missing field SURREAL_PASS", file=sys.stderr)
        sys.exit(1)

    return user, password


def _guard_local(url: str) -> None:
    """Hard-reject any non-local target. Remote/production URLs are always rejected."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host not in LOCAL_ALLOWED_HOSTS:
        print(
            f"ERROR: Remote/production target rejected. Only local connections allowed.",
            file=sys.stderr,
        )
        print(
            f"       Got host: {host!r}  Allowed: {sorted(LOCAL_ALLOWED_HOSTS)}",
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
    data = sql.encode("utf-8")
    req = urllib.request.Request(
        f"{url}/sql", data=data, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _check_statement_results(body: bytes) -> list[dict]:
    """Parse SurrealDB /sql response and fail on any non-OK statement.

    SurrealDB returns HTTP 200 even when individual statements fail.
    Each result item must have ``status: "OK"``; any ``"ERR"`` (or missing
    status, malformed JSON, empty body) is treated as a fatal apply failure.

    Returns the parsed results list on full success.
    Raises ValueError with an operator-friendly message on any failure.
    """
    try:
        raw = body.decode("utf-8", errors="replace")
    except Exception as exc:
        raise ValueError(f"Response body not decodable: {exc}") from exc

    if not raw.strip():
        raise ValueError("Response body is empty — expected JSON array from SurrealDB /sql")

    try:
        results = json.loads(raw)
    except json.JSONDecodeError as exc:
        truncated = raw[:400]
        raise ValueError(
            f"Response body is not valid JSON: {exc}\n  Body (first 400 chars): {truncated}"
        ) from exc

    if not isinstance(results, list):
        raise ValueError(
            f"Expected JSON array from /sql, got {type(results).__name__}: {raw[:400]}"
        )

    errors: list[str] = []
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"  Statement {idx}: expected object, got {type(item).__name__}")
            continue
        stmt_status = item.get("status")
        if stmt_status is None:
            errors.append(
                f"  Statement {idx}: missing 'status' field (item: {str(item)[:120]})"
            )
        elif stmt_status != "OK":
            detail = item.get("detail") or item.get("result") or ""
            errors.append(
                f"  Statement {idx}: status={stmt_status!r} — {str(detail)[:200]}"
            )

    if errors:
        raise ValueError(
            "One or more schema statements failed:\n" + "\n".join(errors)
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply context_intelligence_v0 schema to local SurrealDB (local-only)."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SURREAL_URL,
        help=f"SurrealDB HTTP URL (default: {DEFAULT_SURREAL_URL})",
    )
    parser.add_argument("--ns", default=DEFAULT_NS, help=f"SurrealDB namespace (default: {DEFAULT_NS})")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SurrealDB database (default: {DEFAULT_DB})")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate schema file exists and is readable, but do not apply.",
    )
    parser.add_argument(
        "--secrets-path",
        default=None,
        help="Override SECRETS_PATH directory.",
    )
    args = parser.parse_args()

    # Hard guard: local only
    _guard_local(args.url)

    # Validate schema file exists
    schema_path = SCHEMA_FILE
    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(3)

    schema_sql = schema_path.read_text(encoding="utf-8")
    print(f"[INFO] Schema file: {schema_path.relative_to(_REPO_ROOT)} ({len(schema_sql)} bytes)")
    print(f"[INFO] Target: {args.url} / NS={args.ns} / DB={args.db}")
    print(f"[INFO] Scope: context-intelligence only (no trading/live tables)")

    if args.dry_run:
        print("[DRY-RUN] Schema file readable. No apply performed.")
        sys.exit(0)

    # Load credentials (after dry-run check so dry-run doesn't require env file)
    env_file = _resolve_env_file(args.secrets_path)
    user, password = _load_credentials(env_file)

    # Check container health
    print("[INFO] Checking container health...")
    if not _health_check(args.url):
        print(
            f"ERROR: cdb_surrealdb not reachable at {args.url}/health",
            file=sys.stderr,
        )
        print("       Run 'make context-up' to start the container.", file=sys.stderr)
        sys.exit(4)
    print("[OK] Container healthy.")

    # Apply schema
    print("[INFO] Applying schema...")
    status, body = _sql_request(args.url, schema_sql, user, password, args.ns, args.db)

    if status not in (200, 204):
        print(f"ERROR: Schema apply failed (HTTP {status})", file=sys.stderr)
        # Show response body but truncate (guard against accidental secret echo)
        try:
            body_text = body.decode("utf-8", errors="replace")[:800]
        except Exception:
            body_text = "<unreadable>"
        print(f"       Response: {body_text}", file=sys.stderr)
        sys.exit(5)

    # HTTP 200 is not sufficient — SurrealDB returns 200 even when statements fail.
    # Parse each statement result and fail if any status != "OK".
    try:
        results = _check_statement_results(body)
    except ValueError as exc:
        print(f"ERROR: Schema apply failed — {exc}", file=sys.stderr)
        sys.exit(5)

    print(f"[OK] Schema applied successfully ({len(results)} statement(s) — all OK).")
    print(f"     NS={args.ns}  DB={args.db}")
    print("NOTE: This is local context infrastructure only — not a Live/Trading Go.")


if __name__ == "__main__":
    main()
