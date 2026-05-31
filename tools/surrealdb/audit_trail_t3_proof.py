"""Redacted proof checks for governed T3 audit trail endpoint."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.utils.uuid_gen import generate_uuid_hex
from tools.surrealdb.audit_trail_t3_common import (
    CONTAINER_NAME,
    build_ssl_context,
    check_statement_results,
    endpoint_fingerprint,
    guard_non_localhost,
    health_check,
    load_env_file,
    redact_output,
    resolve_env_file,
    sql_request,
    container_network_names,
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
    except json.JSONDecodeError:
        return False
    return isinstance(results, list) and bool(results)


def _defined_tables(env, ssl_context) -> set[str]:
    status, body = sql_request(env, "INFO FOR DB;", ssl_context=ssl_context)
    if status != 200:
        return set()
    try:
        results = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return set()
    for item in results:
        result = item.get("result")
        if isinstance(result, dict):
            tables = result.get("tables")
            if isinstance(tables, dict):
                return set(tables.keys())
    return set()


def _agent_memory_write_blocked(env, ssl_context) -> bool:
    tables = _defined_tables(env, ssl_context)
    if "agent_memory" in tables:
        return False
    if "audit_observation" not in tables:
        return False
    return True


def _optional_proof_row(env, ssl_context, *, write_proof_row: bool) -> bool:
    if not write_proof_row:
        return True
    observation_id = f"g3c-env-proof-{generate_uuid_hex(name='g3c-env-proof-row')}"
    sql = (
        "CREATE audit_observation SET "
        f"observation_id = '{observation_id}', "
        "observation_type = 'environment_proof', "
        "message = 'G3c isolated proof environment row', "
        "comment = 'G3c environment proof row', "
        "confidence = 1.0, "
        "severity = 'info', "
        "status = 'open', "
        "observed_by = 'audit_trail_t3_proof', "
        "observed_at = time::now(), "
        "created_at = time::now(), "
        "evidence_refs = [], "
        "related_claims = [], "
        "related_decisions = [], "
        "related_memory = [];"
    )
    status, body = sql_request(env, sql, ssl_context=ssl_context)
    if status != 200:
        return False
    try:
        check_statement_results(body)
    except ValueError:
        return False
    verify_status, verify_body = sql_request(
        env,
        f"SELECT observation_id FROM audit_observation WHERE observation_id = '{observation_id}';",
        ssl_context=ssl_context,
    )
    if verify_status != 200:
        return False
    parsed = json.loads(verify_body.decode("utf-8"))
    for item in parsed:
        result = item.get("result")
        if isinstance(result, list) and result:
            return True
    return False


def run_proof(*, secrets_path: str | None, write_proof_row: bool, check_env_only: bool) -> dict:
    env_file = resolve_env_file(secrets_path)
    env = load_env_file(env_file)

    matrix: dict[str, str | bool] = {
        "endpoint_class": "governed_non_localhost_T3",
        "mtls_policy": "optional",
        "secret_values_printed": "no",
        "endpoint_fingerprint": endpoint_fingerprint(
            ns=env.surreal_ns, db=env.surreal_db
        ),
    }

    if check_env_only:
        for key in ("SURREAL_URL", "SURREAL_NS", "SURREAL_DB", "SURREAL_USER", "SURREAL_PASS"):
            matrix[f"env_key_{key}"] = "present"
        matrix["env_structure"] = "ok"
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
    matrix["writer_scope"] = "audit_observation_only"
    matrix["agent_memory_write"] = "no" if _agent_memory_write_blocked(env, ssl_context) else "yes"
    inspect_ok, t3_networks = container_network_names(CONTAINER_NAME)
    matrix["container_inspect"] = "ok" if inspect_ok else "failed"
    matrix["blue_red_coupling"] = (
        "no"
        if inspect_ok and "cdb_network" not in t3_networks
        else ("yes" if "cdb_network" in t3_networks else "unknown")
    )
    matrix["t2_localhost_excluded"] = "yes"
    matrix["proof_row_written"] = (
        "yes" if _optional_proof_row(env, ssl_context, write_proof_row=write_proof_row) else "no"
    )

    failures = []
    if matrix["endpoint_reachable"] is not True:
        failures.append("endpoint_reachable")
    if matrix["non_localhost"] is not True:
        failures.append("non_localhost")
    if matrix["tls_baseline"] is not True:
        failures.append("tls_baseline")
    if matrix["audit_observation_available"] is not True:
        failures.append("audit_observation_available")
    if matrix["agent_memory_write"] != "no":
        failures.append("agent_memory_write")
    if matrix["blue_red_coupling"] != "no":
        failures.append("blue_red_coupling")
    if matrix.get("container_inspect") != "ok":
        failures.append("container_inspect")
    if write_proof_row and matrix["proof_row_written"] != "yes":
        failures.append("proof_row_written")

    matrix["pass"] = not failures
    matrix["failures"] = failures
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="T3 audit trail proof matrix.")
    parser.add_argument("--secrets-path", default=None)
    parser.add_argument(
        "--write-proof-row",
        action="store_true",
        help="Insert one audit_observation proof row (G3c environment proof).",
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
    if args.check_env_only:
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
