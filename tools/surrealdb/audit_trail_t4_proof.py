"""Redacted proof checks for governed T4 agent_memory endpoint scaffold (#2759)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.surrealdb.audit_trail_t4_common import (
    CONTAINER_NAME,
    T4_ENDPOINT_CLASS,
    T4_PRODUCTIVE_ENV_VAR,
    T4_PROOF_SCOPE,
    T4_WRITE_PROOF_BLOCKED_CODE,
    T4_WRITE_PROOF_BLOCKED_MESSAGE,
    T4_WRITER_SCOPE,
    build_ssl_context,
    check_statement_results,
    container_network_names,
    endpoint_fingerprint,
    guard_non_localhost,
    health_check,
    load_env_file,
    redact_output,
    resolve_env_file,
    sql_request,
)


def _table_exists(env, ssl_context, table: str) -> bool:
    status, body = sql_request(
        env,
        f"INFO FOR TABLE {table};",
        ssl_context=ssl_context,
    )
    if status != 200:
        return False
    try:
        results = json.loads(body.decode("utf-8"))
        check_statement_results(body)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(results, list) and bool(results)


def _write_proof_row_status(*, write_proof_row: bool) -> dict[str, str]:
    if not write_proof_row:
        return {
            "write_proof_row_requested": "no",
            "write_proof_row_status": "skipped",
            "proof_row_written": "no",
        }
    return {
        "write_proof_row_requested": "yes",
        "write_proof_row_status": "refused",
        "write_proof_row_blocked_code": T4_WRITE_PROOF_BLOCKED_CODE,
        "write_proof_row_blocked_message": T4_WRITE_PROOF_BLOCKED_MESSAGE,
        "proof_row_written": "no",
        "agent_memory_written": "no",
        "audit_observation_written": "no",
    }


def run_proof(*, secrets_path: str | None, write_proof_row: bool, check_env_only: bool) -> dict:
    env_file = resolve_env_file(secrets_path)
    env = load_env_file(env_file)

    matrix: dict[str, str | bool] = {
        "endpoint_class": T4_ENDPOINT_CLASS,
        "mtls_policy": "optional",
        "secret_values_printed": "no",
        "proof_scope": T4_PROOF_SCOPE,
        "writer_scope": T4_WRITER_SCOPE,
        "productive_env_var": T4_PRODUCTIVE_ENV_VAR,
        "endpoint_fingerprint": endpoint_fingerprint(
            ns=env.surreal_ns, db=env.surreal_db
        ),
    }
    matrix.update(_write_proof_row_status(write_proof_row=write_proof_row))

    if check_env_only:
        for key in (
            "SURREAL_URL",
            "SURREAL_NS",
            "SURREAL_DB",
            "SURREAL_USER",
            "SURREAL_PASS",
        ):
            matrix[f"env_key_{key}"] = "present"
        matrix["env_structure"] = "ok"
        matrix["ns_present"] = env.surreal_ns == "cdb"
        matrix["db_present"] = env.surreal_db == "audit_trail"
        failures: list[str] = []
        if matrix["ns_present"] is not True:
            failures.append("ns_present")
        if matrix["db_present"] is not True:
            failures.append("db_present")
        if write_proof_row:
            failures.append("write_proof_row_blocked")
        matrix["failures"] = failures
        matrix["pass"] = not failures
        return matrix

    ssl_context = build_ssl_context(env.tls_dir / "cert.pem")
    host = guard_non_localhost(env.surreal_url)
    matrix["non_localhost"] = host not in {"127.0.0.1", "localhost", "::1"}
    matrix["tls_baseline"] = health_check(env.surreal_url, ssl_context=ssl_context)
    matrix["endpoint_reachable"] = matrix["tls_baseline"]
    matrix["ns_present"] = env.surreal_ns == "cdb"
    matrix["db_present"] = env.surreal_db == "audit_trail"
    matrix["audit_observation_available"] = _table_exists(
        env, ssl_context, "audit_observation"
    )
    matrix["agent_memory_table_present"] = _table_exists(env, ssl_context, "agent_memory")
    inspect_ok, t4_networks = container_network_names(CONTAINER_NAME)
    matrix["container_inspect"] = "ok" if inspect_ok else "failed"
    matrix["blue_red_coupling"] = (
        "no"
        if inspect_ok and "cdb_network" not in t4_networks
        else ("yes" if "cdb_network" in t4_networks else "unknown")
    )
    matrix["t2_localhost_excluded"] = "yes"
    matrix["scaffold_activation"] = "not_activated"

    failures = []
    if matrix["endpoint_reachable"] is not True:
        failures.append("endpoint_reachable")
    if matrix["non_localhost"] is not True:
        failures.append("non_localhost")
    if matrix["tls_baseline"] is not True:
        failures.append("tls_baseline")
    if matrix["audit_observation_available"] is not True:
        failures.append("audit_observation_available")
    if matrix["agent_memory_table_present"] is not True:
        failures.append("agent_memory_table_present")
    if matrix["ns_present"] is not True:
        failures.append("ns_present")
    if matrix["db_present"] is not True:
        failures.append("db_present")
    if matrix["blue_red_coupling"] != "no":
        failures.append("blue_red_coupling")
    if matrix.get("container_inspect") != "ok":
        failures.append("container_inspect")
    if write_proof_row:
        failures.append("write_proof_row_blocked")

    matrix["pass"] = not failures
    matrix["failures"] = failures
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="T4 agent_memory proof matrix.")
    parser.add_argument("--secrets-path", default=None)
    parser.add_argument(
        "--write-proof-row",
        action="store_true",
        help=(
            "Request one scoped agent_memory proof write (refused until HG-W + "
            "CDB_PERSIST_ALLOWED + #2759 track)."
        ),
    )
    parser.add_argument(
        "--check-env-only",
        action="store_true",
        help="Validate env file structure only.",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path for redacted JSON proof output.",
    )
    args = parser.parse_args()

    try:
        matrix = run_proof(
            secrets_path=args.secrets_path,
            write_proof_row=args.write_proof_row,
            check_env_only=args.check_env_only,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    env_file = resolve_env_file(args.secrets_path)
    env = load_env_file(env_file)
    rendered = json.dumps(matrix, indent=2, sort_keys=True)
    safe = redact_output(rendered, env)
    print(safe)
    if args.json_out:
        Path(args.json_out).write_text(safe + "\n", encoding="utf-8")

    if matrix.get("pass") is False:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
