"""Bootstrap governed non-localhost T3 audit trail SurrealDB endpoint."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from tools.surrealdb.audit_trail_t3_common import (
    COMPOSE_ENV_FILENAME,
    COMPOSE_FILE,
    SCHEMA_FILE,
    build_ssl_context,
    check_statement_results,
    detect_private_lan_ipv4,
    generate_credentials,
    generate_tls_material,
    guard_non_localhost,
    health_check,
    load_env_file,
    resolve_env_file,
    resolve_secrets_path,
    sql_request,
    write_compose_env_file,
    write_env_file,
)


def _run_compose_up(
    secrets_path: Path,
    compose_env_file: Path,
    *,
    surreal_user: str,
    surreal_pass: str,
) -> None:
    cmd = [
        "docker",
        "compose",
        "--env-file",
        str(compose_env_file),
        "-f",
        str(COMPOSE_FILE),
        "up",
        "-d",
    ]
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["SECRETS_PATH"] = str(secrets_path)
    env["SURREAL_USER"] = surreal_user
    env["SURREAL_PASS"] = surreal_pass
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "docker compose up failed; ensure Docker Desktop is running"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision isolated T3 audit trail SurrealDB endpoint."
    )
    parser.add_argument("--secrets-path", default=None)
    parser.add_argument(
        "--skip-compose-up",
        action="store_true",
        help="Only generate secrets/TLS/env and apply schema if endpoint already up.",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Regenerate credentials/TLS even if files already exist.",
    )
    args = parser.parse_args()

    secrets_path = resolve_secrets_path(args.secrets_path)
    env_file = resolve_env_file(str(secrets_path))
    compose_env_file = secrets_path / COMPOSE_ENV_FILENAME
    tls_dir = secrets_path / "audit_trail_tls"

    lan_ip = detect_private_lan_ipv4()
    surreal_url = f"https://{lan_ip}:8020"
    guard_non_localhost(surreal_url)

    if args.force_regenerate or not env_file.is_file():
        user, password = generate_credentials()
    else:
        try:
            existing = load_env_file(env_file)
            user, password = existing.surreal_user, existing.surreal_pass
        except ValueError:
            user, password = generate_credentials()

    if args.force_regenerate or not (tls_dir / "cert.pem").is_file():
        generate_tls_material(tls_dir, san_ip=lan_ip)

    write_env_file(
        env_file,
        surreal_url=surreal_url,
        surreal_user=user,
        surreal_pass=password,
    )
    write_compose_env_file(compose_env_file, surreal_user=user)

    print("[OK] Wrote SURREALDB_AUDIT_TRAIL_ENV (values redacted)")
    print("[OK] Wrote compose env + TLS material under SECRETS_PATH")

    if not args.skip_compose_up:
        print("[INFO] Starting cdb_audit_trail_t3 stack...")
        _run_compose_up(
            secrets_path,
            compose_env_file,
            surreal_user=user,
            surreal_pass=password,
        )

    env = load_env_file(env_file)
    ssl_context = build_ssl_context(env.tls_dir / "cert.pem")

    print("[INFO] Waiting for endpoint health...")
    healthy = False
    for _ in range(30):
        if health_check(env.surreal_url, ssl_context=ssl_context):
            healthy = True
            break
        time.sleep(2)
    if not healthy:
        print("ERROR: T3 endpoint health check failed", file=sys.stderr)
        sys.exit(4)

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    print("[INFO] Applying audit_trail_v0 schema...")
    status, body = sql_request(env, schema_sql, ssl_context=ssl_context)
    if status not in (200, 204):
        print(f"ERROR: schema apply HTTP {status}", file=sys.stderr)
        sys.exit(5)
    check_statement_results(body)
    cleanup_status, cleanup_body = sql_request(
        env,
        "REMOVE TABLE IF EXISTS agent_memory;",
        ssl_context=ssl_context,
    )
    if cleanup_status in (200, 204):
        try:
            check_statement_results(cleanup_body)
        except ValueError:
            pass
    print("[OK] Schema applied (audit_observation only)")
    print("NOTE: T3 endpoint provisioned; productive persist path NOT activated.")


if __name__ == "__main__":
    main()
