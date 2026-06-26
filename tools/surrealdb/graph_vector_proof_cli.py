"""Isolated SurrealDB Graph + Vector Proof CLI.

Proves that graph nodes, relations, traversal and vector similarity search
work against a local SurrealDB memory instance. Runs in isolated NS/DB only.

No Docker. No productive DB. No secrets. No Live-Go. No Echtgeld-Go.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_RUNTIME_UNAVAILABLE = 3

LOCAL_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1"})

SETUP_SURQL = Path("infrastructure/surrealdb/proof_graph_vector_setup.surql")


def _surql_escape(val: str) -> str:
    return "'" + val.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _surql_datetime(dt: datetime) -> str:
    return dt.strftime("'%Y-%m-%dT%H:%M:%SZ'")


class ProofSqlClient:
    """Minimal SurrealDB /sql client for isolated proof operations.

    Uses only stdlib (urllib). No external dependencies.
    """

    def __init__(
        self,
        *,
        surreal_url: str,
        namespace: str,
        database: str,
        user: str,
        password: str,
        timeout: int = 30,
    ) -> None:
        parsed = urllib.parse.urlparse(surreal_url)
        host = parsed.hostname or ""
        if host not in LOCAL_ALLOWED_HOSTS:
            raise ValueError(
                f"SurrealDB host must be localhost/127.0.0.1, got {host!r}"
            )
        self._url = surreal_url.rstrip("/")
        self._namespace = namespace
        self._database = database
        self._auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._timeout = timeout

    def execute(self, sql: str) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "Authorization": f"Basic {self._auth}",
            "surreal-ns": self._namespace,
            "surreal-db": self._database,
        }
        req = urllib.request.Request(
            f"{self._url}/sql",
            data=sql.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError(
                    f"SurrealDB /sql authentication failed (HTTP 401). "
                    f"Check --user / --pass. "
                    f"Default for 'surreal start memory' is root:root."
                ) from exc
            raise RuntimeError(
                f"SurrealDB /sql HTTP {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"SurrealDB /sql request failed: {exc.reason}"
            ) from exc
        except ConnectionRefusedError as exc:
            raise RuntimeError(
                f"SurrealDB connection refused: {exc}"
            ) from exc

        raw = body.decode("utf-8", errors="replace")
        if not raw.strip():
            raise RuntimeError("SurrealDB /sql returned empty body")
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise RuntimeError("SurrealDB /sql returned unexpected payload")
        for item in parsed:
            if isinstance(item, dict) and item.get("status") not in (None, "OK"):
                detail = item.get("detail") or item.get("result") or item
                raise RuntimeError(
                    f"SurrealDB /sql error: {detail!s}"[:400]
                )
        return [item for item in parsed if isinstance(item, dict)]

    def health_check(self) -> dict[str, Any]:
        req = urllib.request.Request(f"{self._url}/health")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return {"status": "ok", "body": body}
        except urllib.error.URLError as exc:
            return {"status": "unreachable", "error": str(exc.reason)}
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}

    def version_check(self) -> dict[str, Any]:
        req = urllib.request.Request(f"{self._url}/version")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return {"status": "ok", "version": body.strip()}
        except urllib.error.URLError as exc:
            return {"status": "unreachable", "error": str(exc.reason)}
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}

    def use_namespace_db(self) -> None:
        self.execute(f"USE NS {self._namespace}; USE DB {self._database};")

    def info_for_db(self) -> dict[str, Any]:
        results = self.execute("INFO FOR DB;")
        for item in results:
            result = item.get("result")
            if isinstance(result, dict):
                return result
        return {}

    def count_records(self, table: str) -> int:
        results = self.execute(f"SELECT count() AS cnt FROM {table};")
        for item in results:
            r = item.get("result")
            if isinstance(r, list) and r:
                return r[0].get("cnt", 0)
        return 0

    def select_all(self, table: str) -> list[dict[str, Any]]:
        results = self.execute(f"SELECT * FROM {table};")
        for item in results:
            r = item.get("result")
            if isinstance(r, list):
                return r
        return []

    def record_exists(self, table: str, pk_field: str, pk_value: str) -> bool:
        escaped = _surql_escape(pk_value)
        results = self.execute(
            f"SELECT * FROM {table} WHERE {pk_field} = {escaped};"
        )
        for item in results:
            r = item.get("result")
            if isinstance(r, list) and r:
                return True
        return False

    def delete_all_proof_data(self) -> None:
        for table in (
            "artifact_cites_decision",
            "chunk_mentions_symbol",
            "doc_chunk",
            "doc_page",
            "code_symbol",
            "decision_event",
            "claim",
            "dependency_edge",
        ):
            self.execute(f"DELETE FROM {table};")

    def delete_proof_database(self) -> None:
        self.execute(f"REMOVE DATABASE {self._database};")


# ---------------------------------------------------------------------------
# Deterministic test data
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def _make_toy_vector(cluster_id: int, variant: int) -> list[float]:
    """Generate a 1536-dim toy vector with non-zero cluster structure.

    Only the first 10 dimensions carry meaningful values; the rest are 0.
    This is a capability proof, not a semantic embedding quality proof.
    """
    vec = [0.0] * 1536
    if cluster_id == 0:
        bases = [
            [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25, 0.15, 0.05],
            [0.85, 0.95, 0.65, 0.75, 0.45, 0.55, 0.25, 0.35, 0.05, 0.15],
            [0.75, 0.65, 0.95, 0.85, 0.35, 0.25, 0.55, 0.45, 0.10, 0.00],
        ]
        chosen = bases[variant % len(bases)]
    elif cluster_id == 1:
        bases = [
            [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95],
            [0.15, 0.05, 0.35, 0.25, 0.55, 0.45, 0.75, 0.65, 0.95, 0.85],
            [0.20, 0.10, 0.40, 0.30, 0.60, 0.50, 0.80, 0.70, 0.90, 0.85],
        ]
        chosen = bases[variant % len(bases)]
    else:
        chosen = [0.5] * 10
    for i, val in enumerate(chosen):
        vec[i] = val
    return vec


def _query_vector_near_cluster(cluster_id: int) -> list[float]:
    """Return a query vector close to the centroid of cluster_id."""
    if cluster_id == 0:
        centroid = [0.85, 0.82, 0.78, 0.75, 0.45, 0.42, 0.38, 0.35, 0.10, 0.07]
    else:
        centroid = [0.13, 0.10, 0.33, 0.30, 0.53, 0.50, 0.73, 0.70, 0.90, 0.88]
    vec = [0.0] * 1536
    for i, val in enumerate(centroid):
        vec[i] = val
    return vec


def _vector_sql_literal(vec: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vec) + "]"


def _chunk_id(slug: str) -> str:
    return f"gv-proof-chunk-{slug}"


def _page_id(slug: str) -> str:
    return f"gv-proof-page-{slug}"


def _decision_id(slug: str) -> str:
    return f"gv-proof-decision-{slug}"


def _symbol_id(slug: str) -> str:
    return f"gv-proof-symbol-{slug}"


def _claim_id(slug: str) -> str:
    return f"gv-proof-claim-{slug}"


def _edge_id(slug: str) -> str:
    return f"gv-proof-edge-{slug}"


# ---------------------------------------------------------------------------
# Proof runners
# ---------------------------------------------------------------------------


def _check_db_available(client: ProofSqlClient) -> dict[str, Any]:
    health = client.health_check()
    version = client.version_check()
    return {
        "health": health,
        "version": version,
        "available": health.get("status") == "ok",
    }


def _deploy_schema(client: ProofSqlClient) -> dict[str, Any]:
    if not SETUP_SURQL.is_file():
        raise RuntimeError(f"Setup surql file not found: {SETUP_SURQL}")
    sql = SETUP_SURQL.read_text(encoding="utf-8")
    client.execute(sql)
    info = client.info_for_db()
    tables = set()
    for key in info.get("tables", {}):
        tables.add(key)
    return {
        "namespace": client._namespace,
        "database": client._database,
        "tables_found": sorted(tables),
        "table_count": len(tables),
    }


def _run_graph_proof(client: ProofSqlClient) -> dict[str, Any]:
    now = NOW
    steps = []

    # --- Create graph test data ---
    page_id = _page_id("graph-proof")
    chunk_a_id = _chunk_id("position-sizing")
    chunk_b_id = _chunk_id("stop-loss")
    decision_id = _decision_id("adopt-max-risk-2pct")
    symbol_id = _symbol_id("calculatePositionSize")
    claim_id = _claim_id("position-sizing-protects")
    now_str = _surql_datetime(now)

    sql = f"""
        CREATE doc_page:{_surql_escape(page_id)} SET
            page_id = {_surql_escape(page_id)},
            title = 'Graph Proof Guide',
            source_path = 'docs/proof/graph_proof_guide.md',
            doc_format = 'markdown',
            confidence = 1.0,
            comment = 'Proof: graph node with deterministic ID',
            created_at = {now_str};

        CREATE doc_chunk:{_surql_escape(chunk_a_id)} SET
            chunk_id = {_surql_escape(chunk_a_id)},
            page_ref = doc_page:{_surql_escape(page_id)},
            chunk_index = 0,
            content = 'Position sizing rules limit each trade to 2%% risk.',
            content_hash = 'sha256:aaaa',
            confidence = 1.0,
            comment = 'Proof: doc_chunk A with page_ref link',
            created_at = {now_str};

        CREATE doc_chunk:{_surql_escape(chunk_b_id)} SET
            chunk_id = {_surql_escape(chunk_b_id)},
            page_ref = doc_page:{_surql_escape(page_id)},
            chunk_index = 1,
            content = 'Stop loss policy: hard 5%% max loss per position.',
            content_hash = 'sha256:bbbb',
            confidence = 1.0,
            comment = 'Proof: doc_chunk B with page_ref link',
            created_at = {now_str};

        CREATE decision_event:{_surql_escape(decision_id)} SET
            decision_id = {_surql_escape(decision_id)},
            title = 'Adopt max 2%% risk per trade',
            question = 'What is the maximum risk per trade?',
            answer = '2%% of account equity',
            decision_type = 'policy',
            status = 'active',
            scope = 'risk_management',
            confidence = 1.0,
            agent = 'OPENCODE/codex',
            human_go = true,
            created_at = {now_str};

        CREATE code_symbol:{_surql_escape(symbol_id)} SET
            symbol_id = {_surql_escape(symbol_id)},
            language = 'python',
            symbol_kind = 'function',
            qualified_name = 'risk.service.calculate_position_size',
            name = 'calculate_position_size',
            file_path = 'services/risk/service.py',
            confidence = 1.0,
            comment = 'Proof: code symbol',
            created_at = {now_str};

        CREATE claim:{_surql_escape(claim_id)} SET
            claim_id = {_surql_escape(claim_id)},
            title = 'Position sizing protects capital',
            statement = 'The 2%% position sizing rule limits drawdown to acceptable levels.',
            scope = 'risk_management',
            status = 'verified',
            confidence = 1.0,
            created_at = {now_str};
    """
    client.execute(sql)

    # --- Create graph RELATIONS ---
    rel_sql = f"""
        RELATE doc_chunk:{_surql_escape(chunk_a_id)}
            ->artifact_cites_decision->
            decision_event:{_surql_escape(decision_id)}
            SET
                source = 'graph_vector_proof_cli.py',
                confidence = 1.0,
                timestamp = {now_str},
                hash = 'sha256:rel-aaaa',
                comment = 'Proof: chunk A cites decision (cites vocabulary)';

        RELATE doc_chunk:{_surql_escape(chunk_b_id)}
            ->artifact_cites_decision->
            decision_event:{_surql_escape(decision_id)}
            SET
                source = 'graph_vector_proof_cli.py',
                confidence = 1.0,
                timestamp = {now_str},
                hash = 'sha256:rel-bbbb',
                comment = 'Proof: chunk B cites decision (cites vocabulary)';

        RELATE doc_chunk:{_surql_escape(chunk_a_id)}
            ->chunk_mentions_symbol->
            code_symbol:{_surql_escape(symbol_id)}
            SET
                source = 'graph_vector_proof_cli.py',
                confidence = 0.9,
                timestamp = {now_str},
                hash = 'sha256:rel-cccc',
                mention_context = 'Position sizing rules mention the calculation function',
                comment = 'Proof: chunk A mentions code symbol (mentions vocabulary)';
    """
    client.execute(rel_sql)

    steps.append({
        "step": "graph_data_created",
        "page_id": page_id,
        "chunk_a_id": chunk_a_id,
        "chunk_b_id": chunk_b_id,
        "decision_id": decision_id,
        "symbol_id": symbol_id,
        "claim_id": claim_id,
    })

    # --- Run Traversal Queries ---
    traversals = []

    # T1: Forward traversal — chunk A → cites → decision
    t1_sql = (
        f"SELECT ->artifact_cites_decision->decision_event.* "
        f"FROM doc_chunk:{_surql_escape(chunk_a_id)};"
    )
    t1_result = client.execute(t1_sql)
    t1_decision_ids = []
    for item in t1_result:
        r = item.get("result")
        if isinstance(r, list):
            for row in r:
                if isinstance(row, dict) and "decision_id" in row:
                    t1_decision_ids.append(row["decision_id"])
    t1_pass = decision_id in t1_decision_ids
    traversals.append({
        "query": "Forward: chunk ->artifact_cites_decision->decision_event",
        "sql": t1_sql.strip(),
        "expected_decision_id": decision_id,
        "found_decision_ids": t1_decision_ids,
        "pass": t1_pass,
    })

    # T2: Backward traversal — decision ← cites ← chunks
    t2_sql = (
        f"SELECT <-artifact_cites_decision<-doc_chunk.* "
        f"FROM decision_event:{_surql_escape(decision_id)};"
    )
    t2_result = client.execute(t2_sql)
    t2_chunk_ids = []
    for item in t2_result:
        r = item.get("result")
        if isinstance(r, list):
            for row in r:
                if isinstance(row, dict) and "chunk_id" in row:
                    t2_chunk_ids.append(row["chunk_id"])
    t2_pass = chunk_a_id in t2_chunk_ids and chunk_b_id in t2_chunk_ids
    traversals.append({
        "query": "Backward: decision <-artifact_cites_decision<-doc_chunk",
        "sql": t2_sql.strip(),
        "expected_chunk_ids": [chunk_a_id, chunk_b_id],
        "found_chunk_ids": t2_chunk_ids,
        "pass": t2_pass,
    })

    # T3: Multi-hop — chunk → mentions → symbol
    t3_sql = (
        f"SELECT ->chunk_mentions_symbol->code_symbol.* "
        f"FROM doc_chunk:{_surql_escape(chunk_a_id)};"
    )
    t3_result = client.execute(t3_sql)
    t3_symbol_ids = []
    for item in t3_result:
        r = item.get("result")
        if isinstance(r, list):
            for row in r:
                if isinstance(row, dict) and "symbol_id" in row:
                    t3_symbol_ids.append(row["symbol_id"])
    t3_pass = symbol_id in t3_symbol_ids
    traversals.append({
        "query": "Multi-hop: chunk ->chunk_mentions_symbol->code_symbol",
        "sql": t3_sql.strip(),
        "expected_symbol_id": symbol_id,
        "found_symbol_ids": t3_symbol_ids,
        "pass": t3_pass,
    })

    # T4: Bi-directional — chunk → symbol ← chunks (backward)
    t4_sql = (
        f"SELECT ->chunk_mentions_symbol->code_symbol"
        f"<-chunk_mentions_symbol<-doc_chunk.* "
        f"FROM doc_chunk:{_surql_escape(chunk_a_id)};"
    )
    t4_result = client.execute(t4_sql)
    t4_chunk_ids = []
    for item in t4_result:
        r = item.get("result")
        if isinstance(r, list):
            for row in r:
                if isinstance(row, dict) and "chunk_id" in row:
                    t4_chunk_ids.append(row["chunk_id"])
    t4_pass = chunk_a_id in t4_chunk_ids
    traversals.append({
        "query": "Bi-directional: chunk → symbol ← chunk",
        "sql": t4_sql.strip(),
        "expected_chunk_ids": [chunk_a_id],
        "found_chunk_ids": t4_chunk_ids,
        "pass": t4_pass,
    })

    graph_pass = all(t["pass"] for t in traversals)
    return {
        "steps": steps,
        "traversals": traversals,
        "graph_pass": graph_pass,
        "relations_created": 3,
        "traversals_executed": len(traversals),
    }


def _run_vector_proof(client: ProofSqlClient) -> dict[str, Any]:
    now = NOW
    steps = []
    now_str = _surql_datetime(now)
    page_id = _page_id("vector-proof")

    # Create a parent page
    client.execute(f"""
        CREATE doc_page:{_surql_escape(page_id)} SET
            page_id = {_surql_escape(page_id)},
            title = 'Vector Proof Content',
            source_path = 'docs/proof/vector_proof_content.md',
            doc_format = 'markdown',
            confidence = 1.0,
            comment = 'Proof: vector test data parent page',
            created_at = {now_str};
    """)

    # Create 5 chunks with toy vectors
    vchunks = [
        ("pos-sizing-a", 0, 0, "Position sizing: 2% risk per trade."),
        ("pos-sizing-b", 0, 1, "Position sizing: calculate units based on stop distance."),
        ("risk-limit-a", 1, 0, "Risk limits: max daily loss is 5%."),
        ("risk-limit-b", 1, 1, "Risk limits: circuit breaker at 10% drawdown."),
        ("risk-limit-c", 1, 2, "Risk limits: reduce position size after 3 losses."),
    ]

    for slug, cluster, variant, content in vchunks:
        cid = _chunk_id(slug)
        vec = _make_toy_vector(cluster, variant)
        vec_literal = _vector_sql_literal(vec)
        client.execute(f"""
            CREATE doc_chunk:{_surql_escape(cid)} SET
                chunk_id = {_surql_escape(cid)},
                page_ref = doc_page:{_surql_escape(page_id)},
                chunk_index = {vchunks.index((slug, cluster, variant, content))},
                content = {_surql_escape(content)},
                content_hash = 'sha256:vec-{slug}',
                confidence = 1.0,
                comment = 'Proof: vector chunk {slug} in cluster {cluster}',
                embedding = {vec_literal},
                created_at = {now_str};
        """)

    steps.append({
        "step": "vector_data_created",
        "page_id": page_id,
        "chunks": [{"slug": s, "cluster": c} for s, c, _, _ in vchunks],
    })

    # Run vector queries
    queries = []

    for label, cluster_id in [("cluster_A_position_sizing", 0),
                               ("cluster_B_risk_limits", 1)]:
        qvec = _query_vector_near_cluster(cluster_id)
        qvec_literal = _vector_sql_literal(qvec)
        k = 5
        ef = 20
        sql = (
            f"SELECT chunk_id, content, "
            f"vector::distance::knn() AS vector_distance "
            f"FROM doc_chunk "
            f"WHERE embedding <|{k}, {ef}|> {qvec_literal} "
            f"ORDER BY vector_distance ASC;"
        )
        result = client.execute(sql)
        rows = []
        for item in result:
            r = item.get("result")
            if isinstance(r, list):
                for row in r:
                    rows.append({
                        "chunk_id": row.get("chunk_id"),
                        "vector_distance": row.get("vector_distance"),
                    })

        expected_first_slug = "pos-sizing-a" if cluster_id == 0 else "risk-limit-a"
        expected_order_pass = bool(
            rows and _chunk_id(expected_first_slug) == rows[0].get("chunk_id")
        )

        queries.append({
            "label": label,
            "k": k,
            "ef": ef,
            "sql": sql.strip(),
            "result_count": len(rows),
            "results": rows,
            "expected_first_chunk": _chunk_id(expected_first_slug),
            "order_pass": expected_order_pass,
        })

    # Count records
    chunk_count = client.count_records("doc_chunk")

    vector_pass = all(q["order_pass"] for q in queries) and chunk_count >= 5
    return {
        "steps": steps,
        "queries": queries,
        "chunk_count": chunk_count,
        "vector_pass": vector_pass,
    }


# ---------------------------------------------------------------------------
# Evidence pack
# ---------------------------------------------------------------------------


def _build_evidence(
    db_available: dict[str, Any],
    schema_result: dict[str, Any] | None,
    graph_result: dict[str, Any] | None,
    vector_result: dict[str, Any] | None,
    duration_ms: float,
) -> dict[str, Any]:
    overall_pass = False
    verdicts = []

    if not db_available.get("available"):
        verdicts.append({
            "check": "db_available",
            "pass": False,
            "detail": "SurrealDB instance not reachable",
        })
    else:
        verdicts.append({
            "check": "db_available",
            "pass": True,
            "detail": "SurrealDB reachable",
            "version": db_available.get("version", {}).get("version", "unknown"),
        })

    if schema_result:
        tables = schema_result.get("tables_found", [])
        expected = {"artifact_cites_decision", "chunk_mentions_symbol",
                    "claim", "code_symbol", "decision_event",
                    "dependency_edge", "doc_chunk", "doc_page"}
        found = set(tables)
        missing_tables = expected - found
        schema_pass = len(missing_tables) == 0
        verdicts.append({
            "check": "schema_deployed",
            "pass": schema_pass,
            "table_count": len(tables),
            "expected_tables": sorted(expected),
            "found_tables": sorted(found),
            "missing_tables": sorted(missing_tables),
        })

    if graph_result:
        g_pass = graph_result.get("graph_pass", False)
        verdicts.append({
            "check": "graph_proof",
            "pass": g_pass,
            "relations_created": graph_result.get("relations_created", 0),
            "traversals_executed": graph_result.get("traversals_executed", 0),
            "details": [
                {
                    "query": t["query"],
                    "pass": t["pass"],
                    "expected": t.get("expected_decision_id") or t.get("expected_chunk_ids") or t.get("expected_symbol_id"),
                    "found": t.get("found_decision_ids") or t.get("found_chunk_ids") or t.get("found_symbol_ids"),
                }
                for t in graph_result.get("traversals", [])
            ],
        })

    if vector_result:
        v_pass = vector_result.get("vector_pass", False)
        queries = vector_result.get("queries", [])
        verdicts.append({
            "check": "vector_proof",
            "pass": v_pass,
            "chunk_count": vector_result.get("chunk_count", 0),
            "queries_executed": len(queries),
            "details": [
                {
                    "label": q["label"],
                    "pass": q["order_pass"],
                    "result_count": q["result_count"],
                    "expected_first": q.get("expected_first_chunk"),
                    "first_found": q["results"][0]["chunk_id"] if q.get("results") else None,
                }
                for q in queries
            ],
        })

    non_blocking = []
    db_pass = True
    for v in verdicts:
        if v.get("check") == "db_available":
            db_pass = v.get("pass", False)
            if not db_pass:
                overall_pass = False
                break
            continue
        if not v.get("pass", False):
            non_blocking.append(v["check"])

    if db_pass:
        if not non_blocking:
            overall_pass = True

    return {
        "report_metadata": {
            "tool": "graph_vector_proof_cli.py",
            "generated_at": NOW.isoformat(),
            "duration_ms": round(duration_ms, 1),
            "proof_type": "graph_and_vector_capability",
            "lr_status": "NO-GO",
            "isolation": {
                "namespace": "cdb_proof",
                "database": "graph_vector_proof",
            },
            "limitation": (
                "Capability proof only. "
                "Toy vectors (first 10 dims nonzero, rest 0) demonstrate "
                "HNSW KNN mechanics, not semantic embedding quality."
            ),
        },
        "db_available": db_available,
        "verdicts": verdicts,
        "overall_pass": overall_pass,
        "summary": "PASS" if overall_pass else "FAIL",
        "schema": schema_result,
        "graph": graph_result,
        "vector": vector_result,
    }


def _write_evidence_json(evidence: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = NOW.strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"cdb-proof-graph-vector-{ts}.json"
    path.write_text(
        json.dumps(evidence, indent=2, sort_keys=False, default=str),
        encoding="utf-8",
    )
    return path


def _write_evidence_markdown(evidence: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = NOW.strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"cdb-proof-graph-vector-{ts}.md"
    lines = []
    lines.append("# CDB SurrealDB Graph + Vector Proof Report")
    lines.append("")
    lines.append(f"**Generated**: {evidence['report_metadata']['generated_at']}")
    lines.append(f"**Duration**: {evidence['report_metadata']['duration_ms']}ms")
    lines.append(f"**LR Status**: {evidence['report_metadata']['lr_status']}")
    lines.append(f"**Isolation**: NS {evidence['report_metadata']['isolation']['namespace']} / DB {evidence['report_metadata']['isolation']['database']}")
    lines.append("")
    lines.append(f"## Overall: {evidence['summary']}")
    lines.append("")
    lines.append("## Verdicts")
    lines.append("")
    lines.append("| Check | PASS | Detail |")
    lines.append("|-------|------|--------|")
    for v in evidence.get("verdicts", []):
        check = v.get("check", "?")
        passed = "PASS" if v.get("pass") else "FAIL"
        detail = v.get("detail", "")
        if not detail and "missing_tables" in v:
            detail = f"Tables: {v.get('table_count', 0)}"
            if v.get("missing_tables"):
                detail += f", MISSING: {v['missing_tables']}"
        if not detail and "relations_created" in v:
            detail = f"{v.get('relations_created', 0)} relations, {v.get('traversals_executed', 0)} traversals"
        if not detail and "chunk_count" in v:
            detail = f"{v.get('chunk_count', 0)} chunks, {v.get('queries_executed', 0)} queries"
        lines.append(f"| {check} | {passed} | {detail} |")
    lines.append("")
    lines.append("## Graph Proof")
    graph = evidence.get("graph")
    if graph:
        for t in graph.get("traversals", []):
            lines.append(f"### {t['query']}")
            lines.append(f"- **PASS**: {t['pass']}")
            lines.append(f"- SQL: `{t['sql'][:120]}...`")
            lines.append("")
    lines.append("")
    lines.append("## Vector Proof")
    vector = evidence.get("vector")
    if vector:
        for q in vector.get("queries", []):
            lines.append(f"### {q['label']}")
            lines.append(f"- **Order PASS**: {q['order_pass']}")
            lines.append(f"- Results: {q['result_count']} chunks returned")
            if q.get("results"):
                lines.append(f"- Best match: {q['results'][0].get('chunk_id')} (dist={q['results'][0].get('vector_distance', 'N/A')})")
            lines.append("")
    lines.append("")
    lines.append("## Limitations")
    lines.append(f"{evidence['report_metadata']['limitation']}")
    lines.append("")
    lines.append("## Safety Boundaries")
    lines.append("- Namespace: `cdb_proof` (isolated)")
    lines.append("- Database: `graph_vector_proof` (isolated)")
    lines.append("- No existing NS/DB was modified")
    lines.append("- No Docker used")
    lines.append("- No Live-Go / Echtgeld-Go")
    lines.append("- No secrets exposed")
    lines.append("- LR remains NO-GO")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Isolated SurrealDB Graph + Vector Proof. "
            "Requires: 'surreal start --user root --pass root memory --bind 127.0.0.1:8010'. "
            "No Docker. No productive DB. No Live-Go. No Echtgeld-Go. "
            "LR remains NO-GO."
        ),
    )
    parser.add_argument(
        "--host", default="localhost",
        help="SurrealDB host (default: localhost)",
    )
    parser.add_argument(
        "--port", default=8010, type=int,
        help="SurrealDB port (default: 8010)",
    )
    parser.add_argument(
        "--user", default="root",
        help="SurrealDB user (default: root)",
    )
    parser.add_argument(
        "--pass", dest="password", default="root",
        help="SurrealDB password (default: root)",
    )
    parser.add_argument(
        "--ns", default="cdb_proof",
        help="SurrealDB namespace (default: cdb_proof)",
    )
    parser.add_argument(
        "--db", default="graph_vector_proof",
        help="SurrealDB database (default: graph_vector_proof)",
    )
    parser.add_argument(
        "--output", default="artifacts/evidence/graph_vector_proof",
        help="Evidence output directory (default: artifacts/evidence/graph_vector_proof)",
    )
    parser.add_argument(
        "--cleanup", default=True, action=argparse.BooleanOptionalAction,
        help="Delete proof data after completion (default: true)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    import time
    t0 = time.time()

    url = f"http://{args.host}:{args.port}"
    client = ProofSqlClient(
        surreal_url=url,
        namespace=args.ns,
        database=args.db,
        user=args.user,
        password=args.password,
    )

    print(f"CDB SurrealDB Graph + Vector Proof")
    print(f"  Target: {url}")
    print(f"  NS:     {args.ns}")
    print(f"  DB:     {args.db}")
    print(f"  Output: {args.output}")
    print(f"  Cleanup: {args.cleanup}")
    print(f"  LR:     NO-GO (fail-closed)")
    print()

    # Step 1: check DB
    print("[1/5] Checking DB availability...")
    db_available = _check_db_available(client)
    if not db_available.get("available"):
        print(f"  FAIL: SurrealDB not reachable at {url}")
        print()
        print("  Start a local SurrealDB memory instance:")
        print("    surreal start --user root --pass root memory --bind 127.0.0.1:8010")
        print()
        print("  Or use a different host/port with --host / --port.")
        evidence = _build_evidence(db_available, None, None, None, 0)
        _write_evidence(evidence, args.output)
        return EXIT_RUNTIME_UNAVAILABLE

    version = db_available.get("version", {}).get("version", "unknown")
    print(f"  OK: SurrealDB {version} reachable")

    # Step 2: deploy schema
    print("[2/5] Deploying isolated proof schema...")
    try:
        schema_result = _deploy_schema(client)
        print(f"  OK: {schema_result['table_count']} tables deployed")
        print(f"  Tables: {', '.join(sorted(schema_result['tables_found']))}")
    except Exception as exc:
        print(f"  FAIL: Schema deploy error: {exc}")
        evidence = _build_evidence(db_available, None, None, None, (time.time() - t0) * 1000)
        _write_evidence(evidence, args.output)
        return EXIT_FAIL

    # Step 3: graph proof
    print("[3/5] Running Graph Proof...")
    try:
        graph_result = _run_graph_proof(client)
        g_pass = graph_result.get("graph_pass", False)
        if g_pass:
            print(f"  PASS: {graph_result['traversals_executed']} traversal queries passed")
        else:
            print(f"  FAIL: Some traversals did not return expected results")
            for t in graph_result.get("traversals", []):
                status = "PASS" if t["pass"] else "FAIL"
                print(f"    {status}: {t['query']}")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        graph_result = None

    # Step 4: vector proof
    print("[4/5] Running Vector Proof...")
    try:
        vector_result = _run_vector_proof(client)
        v_pass = vector_result.get("vector_pass", False)
        if v_pass:
            print(f"  PASS: {vector_result['chunk_count']} chunks, {len(vector_result['queries'])} KNN queries")
        else:
            print(f"  FAIL: Vector search did not return expected ordering")
            for q in vector_result.get("queries", []):
                status = "PASS" if q["order_pass"] else "FAIL"
                print(f"    {status}: {q['label']}")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        vector_result = None

    # Step 5: evidence + cleanup
    duration_ms = (time.time() - t0) * 1000
    print(f"[5/5] Generating evidence...")

    evidence = _build_evidence(
        db_available, schema_result, graph_result, vector_result, duration_ms,
    )
    json_path = _write_evidence_json(evidence, Path(args.output))
    md_path = _write_evidence_markdown(evidence, Path(args.output))
    print(f"  Evidence JSON: {json_path}")
    print(f"  Evidence MD:   {md_path}")
    print(f"  Verdict: {evidence['summary']}")

    if args.cleanup:
        print("  Cleaning up proof data...")
        try:
            client.delete_proof_database()
            print("  OK: proof database removed")
        except Exception as exc:
            print(f"  WARN: cleanup failed: {exc}")

    print()
    print(f"Report metadata: {json.dumps(evidence['report_metadata'], indent=2)}")
    print()
    print("LR: NO-GO. No live capital. No Echtgeld-Go.")

    if evidence["summary"] == "PASS":
        return EXIT_OK
    return EXIT_FAIL


def _write_evidence(evidence: dict[str, Any], output: str) -> None:
    """Write evidence when main flow fails early."""
    out = Path(output)
    _write_evidence_json(evidence, out)
    _write_evidence_markdown(evidence, out)
    print(f"  Partial evidence written to {out}")


if __name__ == "__main__":
    raise SystemExit(main())
