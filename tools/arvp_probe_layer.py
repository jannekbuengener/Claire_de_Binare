from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

ProbeResult = dict[str, Any]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ok(evidence: dict, limitations: list[str] | None = None) -> ProbeResult:
    return {
        "status": "ok",
        "evidence": evidence,
        "observed_at_utc": _utcnow(),
        "limitations": limitations or [],
        "no_mutation": True,
    }


def _warn(evidence: dict, limitations: list[str] | None = None) -> ProbeResult:
    return {
        "status": "warn",
        "evidence": evidence,
        "observed_at_utc": _utcnow(),
        "limitations": limitations or [],
        "no_mutation": True,
    }


def _blocked(evidence: dict, limitations: list[str] | None = None) -> ProbeResult:
    return {
        "status": "blocked",
        "evidence": evidence,
        "observed_at_utc": _utcnow(),
        "limitations": limitations or [],
        "no_mutation": True,
    }


def _unavailable(evidence: dict, limitations: list[str] | None = None) -> ProbeResult:
    return {
        "status": "unavailable",
        "evidence": evidence,
        "observed_at_utc": _utcnow(),
        "limitations": limitations or [],
        "no_mutation": True,
    }


# ---------------------------------------------------------------------------
# 1. Host probe
# ---------------------------------------------------------------------------


def probe_host() -> ProbeResult:
    """Windows host: LastBootUpTime, uptime, sleep/wake indicators."""
    if platform.system() != "Windows":
        return _unavailable(
            {"note": "host probe is Windows-only (WMI/CIM)"},
            ["platform is not Windows"],
        )
    try:
        ps_cmd = [
            "powershell",
            "-Command",
            "Get-CimInstance Win32_OperatingSystem | "
            "Select-Object LastBootUpTime | "
            "ConvertTo-Json",
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return _blocked(
                {"error": result.stderr.strip()},
                ["Get-CimInstance failed"],
            )
        data = json.loads(result.stdout)
        last_boot_raw = data.get("LastBootUpTime")
        if not last_boot_raw:
            return _warn(
                {"raw_output": result.stdout.strip()},
                ["could not parse LastBootUpTime"],
            )
        boot_dt = datetime.fromisoformat(last_boot_raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        uptime_seconds = int((now - boot_dt).total_seconds())

        sleep_events = []
        try:
            wake = subprocess.run(
                ["powercfg", "/lastwake"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if wake.returncode == 0 and wake.stdout.strip():
                sleep_events.append(wake.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return _ok(
            {
                "last_boot_up_time_utc": boot_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "uptime_seconds": uptime_seconds,
                "uptime_display": _format_uptime(uptime_seconds),
                "sleep_wake_indicators": (
                    sleep_events if sleep_events else ["none detected"]
                ),
                "command": "Get-CimInstance Win32_OperatingSystem",
            },
            ["powercfg may require admin rights"],
        )
    except FileNotFoundError:
        return _unavailable(
            {"error": "powershell not found"},
            ["PowerShell is not installed or not in PATH"],
        )
    except subprocess.TimeoutExpired:
        return _blocked(
            {"error": "powershell command timed out after 15s"},
            ["host did not respond in time; possible sleep/hibernate"],
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return _warn(
            {"error": str(exc)},
            ["unexpected output from Get-CimInstance"],
        )


def _format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# 2. Docker probe
# ---------------------------------------------------------------------------

DEFAULT_RUNTIME_TARGETS = [
    "cdb_execution",
    "cdb_regime",
    "cdb_risk",
    "cdb_market",
    "cdb_candles",
    "cdb_db_writer",
]


def _run_docker_cmd(args: list[str], timeout: int = 15) -> str:
    result = subprocess.run(
        ["docker"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def probe_docker(targets: list[str] | None = None) -> ProbeResult:
    if targets is None:
        targets = DEFAULT_RUNTIME_TARGETS
    try:
        _run_docker_cmd(["ps", "--format", "{{.ID}}"], timeout=10)
    except (FileNotFoundError, RuntimeError) as exc:
        return _blocked(
            {"error": str(exc)},
            ["Docker not available; is Docker Desktop running?"],
        )

    containers: list[dict] = []
    for name in targets:
        try:
            state = _run_docker_cmd(
                [
                    "inspect",
                    name,
                    "--format",
                    "{{.State.Status}}\t{{.State.Health.Status}}\t{{.State.StartedAt}}",
                ],
                timeout=10,
            )
            parts = state.strip().split("\t")
            status = parts[0] if len(parts) > 0 else "unknown"
            health = parts[1] if len(parts) > 1 else "none"
            started_raw = parts[2] if len(parts) > 2 else ""

            uptime_s = None
            if started_raw and status == "running":
                try:
                    started_dt = datetime.fromisoformat(
                        started_raw.replace("Z", "+00:00")
                    )
                    uptime_s = int(
                        (datetime.now(timezone.utc) - started_dt).total_seconds()
                    )
                except ValueError:
                    pass

            containers.append(
                {
                    "service": name,
                    "status": status,
                    "health": health if health != "<nil>" else "none",
                    "started_at_utc": started_raw,
                    "uptime_seconds": uptime_s,
                }
            )
        except (RuntimeError, FileNotFoundError) as exc:
            containers.append(
                {
                    "service": name,
                    "status": "not_found",
                    "health": "none",
                    "started_at_utc": "",
                    "uptime_seconds": None,
                    "error": str(exc),
                }
            )

    running = [c for c in containers if c["status"] == "running"]
    healthy = [c for c in containers if c["health"] == "healthy"]
    missing = [c for c in containers if c["status"] == "not_found"]

    limitations = []
    if missing:
        limitations.append(
            f"missing containers: {', '.join(c['service'] for c in missing)}"
        )

    if missing:
        status = "warn"
    elif len(healthy) == len(targets):
        status = "ok"
    elif len(running) > 0:
        status = "warn"
    else:
        status = "blocked"

    return {
        "status": status,
        "evidence": {
            "containers": containers,
            "total_targets": len(targets),
            "running": len(running),
            "healthy": len(healthy),
            "missing": len(missing),
            "command": "docker inspect <name> --format 'State.Status\\tState.Health.Status\\tState.StartedAt'",
        },
        "observed_at_utc": _utcnow(),
        "limitations": limitations,
        "no_mutation": True,
    }


# ---------------------------------------------------------------------------
# 3. Safety probe (cdb_execution env flags)
# ---------------------------------------------------------------------------

SAFETY_FLAGS_EXPECTED: dict[str, str] = {
    "MOCK_TRADING": "true",
    "USE_REAL_BALANCE": "false",
    "DRY_RUN": "true",
    "MEXC_TESTNET": "true",
}


def probe_safety(container: str = "cdb_execution") -> ProbeResult:
    try:
        raw_env = _run_docker_cmd(
            ["inspect", container, "--format", "{{json .Config.Env}}"],
            timeout=10,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        return _blocked(
            {"error": str(exc)},
            [f"container {container} not found or Docker unavailable"],
        )

    try:
        env_list: list[str] = json.loads(raw_env)
    except json.JSONDecodeError as exc:
        return _warn(
            {"error": str(exc), "raw": raw_env},
            ["could not parse container env JSON"],
        )

    env_dict: dict[str, str] = {}
    for entry in env_list:
        if "=" in entry:
            key, _, val = entry.partition("=")
            env_dict[key] = val

    flags: list[dict[str, Any]] = []
    all_match = True
    for flag, expected in SAFETY_FLAGS_EXPECTED.items():
        actual = env_dict.get(flag)
        match = actual is not None and actual.lower() == expected.lower()
        if not match:
            all_match = False
        flags.append(
            {
                "flag": flag,
                "value": actual,
                "expected": expected,
                "match": match,
            }
        )

    status = "ok" if all_match else "blocked"
    limitations = []
    if not all_match:
        mismatched = [f for f in flags if not f["match"]]
        limitations.append(
            f"safety flag drift: {', '.join(f['flag'] for f in mismatched)}"
        )

    return {
        "status": status,
        "evidence": {
            "container": container,
            "flags": flags,
            "all_flags_match_expected": all_match,
            "command": f"docker inspect {container} --format '{{{{json .Config.Env}}}}'",
        },
        "observed_at_utc": _utcnow(),
        "limitations": limitations,
        "no_mutation": True,
    }


# ---------------------------------------------------------------------------
# 4. DB readonly probe
# ---------------------------------------------------------------------------

DB_DEFAULTS = {
    "host": os.environ.get("CDB_DB_HOST", "localhost"),
    "port": int(os.environ.get("CDB_DB_PORT", "5432")),
    "dbname": os.environ.get("CDB_DB_NAME", "claire"),
    "user": os.environ.get("CDB_DB_USER", "claire_user"),
}


def probe_db_readonly(
    host: str = DB_DEFAULTS["host"],
    port: int = DB_DEFAULTS["port"],
    dbname: str = DB_DEFAULTS["dbname"],
    user: str = DB_DEFAULTS["user"],
) -> ProbeResult:
    import importlib

    psycopg2_available = importlib.util.find_spec("psycopg2") is not None
    pg_isready_available = False
    try:
        subprocess.run(
            ["pg_isready", "--version"], capture_output=True, timeout=5
        )
        pg_isready_available = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if not psycopg2_available and not pg_isready_available:
        return _unavailable(
            {"error": "neither psycopg2 nor pg_isready available"},
            ["install psycopg2 or postgresql-client for DB probes"],
        )

    limitations = []

    if pg_isready_available:
        try:
            ready = subprocess.run(
                [
                    "pg_isready",
                    "-h", host,
                    "-p", str(port),
                    "-d", dbname,
                    "-U", user,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if ready.returncode != 0:
                return _blocked(
                    {
                        "connectivity": "fail",
                        "pg_isready_output": (
                            ready.stdout.strip() or ready.stderr.strip()
                        ),
                    },
                    [f"DB not reachable at {host}:{port}/{dbname}"],
                )
        except subprocess.TimeoutExpired:
            return _blocked(
                {"connectivity": "timeout"},
                [f"pg_isready timed out at {host}:{port}"],
            )
    else:
        limitations.append("pg_isready not available; connectivity not verified")

    if psycopg2_available:
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=host, port=port, dbname=dbname,
                user=user, connect_timeout=10,
            )
            cur = conn.cursor()
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
            cur.close()
            conn.close()

            select_ok = row is not None and row[0] == 1

            svr_version = None
            try:
                conn2 = psycopg2.connect(
                    host=host, port=port, dbname=dbname,
                    user=user, connect_timeout=10,
                )
                cur2 = conn2.cursor()
                cur2.execute("SELECT version()")
                svr_version = cur2.fetchone()[0]
                cur2.close()
                conn2.close()
            except Exception:
                pass

            return _ok(
                {
                    "connectivity": "ok",
                    "select_1_ok": select_ok,
                    "server_version": svr_version or "unknown",
                    "host": host,
                    "port": port,
                    "dbname": dbname,
                    "user": user,
                    "method": "psycopg2",
                },
                limitations,
            )
        except Exception as exc:
            return _blocked(
                {"connectivity": "fail", "error": str(exc)},
                limitations + [f"psycopg2 connection failed: {exc}"],
            )

    return _ok(
        {
            "connectivity": "ok (pg_isready only)",
            "host": host, "port": port, "dbname": dbname,
        },
        limitations + ["pg_isready only; no SELECT verification"],
    )


# ---------------------------------------------------------------------------
# 5. Candle probe (market data: BTCUSDT candles_1m)
# ---------------------------------------------------------------------------


def _run_sql(
    host: str, port: int, dbname: str, user: str, query: str
) -> list[tuple]:
    import psycopg2

    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname,
        user=user, connect_timeout=10,
    )
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def probe_candles(
    symbol: str = "BTCUSDT",
    host: str = DB_DEFAULTS["host"],
    port: int = DB_DEFAULTS["port"],
    dbname: str = DB_DEFAULTS["dbname"],
    user: str = DB_DEFAULTS["user"],
    gap_threshold_minutes: int = 3,
) -> ProbeResult:
    import importlib

    if not importlib.util.find_spec("psycopg2"):
        return _unavailable(
            {"error": "psycopg2 not installed"},
            ["install psycopg2 for candle probes"],
        )

    try:
        latest = _run_sql(
            host, port, dbname, user,
            f"SELECT MAX(ts_ms) FROM candles_1m WHERE symbol='{symbol}'",
        )
        latest_ts = latest[0][0] if latest and latest[0][0] else None
        if latest_ts is None:
            return _unavailable(
                {"note": f"no candles found for {symbol}"},
                [f"candles_1m table has no entries for {symbol}"],
            )

        range_15m = _run_sql(
            host, port, dbname, user,
            f"SELECT MAX(high) - MIN(low) FROM candles_1m "
            f"WHERE symbol='{symbol}' "
            f"AND ts_ms >= NOW() - INTERVAL '15 minutes'",
        )
        range_15m_val = (
            float(range_15m[0][0]) if range_15m and range_15m[0][0] else None
        )

        range_60m = _run_sql(
            host, port, dbname, user,
            f"SELECT MAX(high) - MIN(low) FROM candles_1m "
            f"WHERE symbol='{symbol}' "
            f"AND ts_ms >= NOW() - INTERVAL '60 minutes'",
        )
        range_60m_val = (
            float(range_60m[0][0]) if range_60m and range_60m[0][0] else None
        )

        gaps = _run_sql(
            host, port, dbname, user,
            f"SELECT ts_ms - LAG(ts_ms) OVER (ORDER BY ts_ms) AS gap "
            f"FROM candles_1m WHERE symbol='{symbol}' "
            f"ORDER BY ts_ms DESC LIMIT 10",
        )
        gap_minutes_list: list[float] = []
        for row in gaps:
            gap_val = row[0]
            if gap_val is not None:
                try:
                    gap_minutes_list.append(float(gap_val) / 60000.0)
                except (ValueError, TypeError):
                    pass

        large_gaps = [g for g in gap_minutes_list if g > gap_threshold_minutes]

        latest_close = _run_sql(
            host, port, dbname, user,
            f"SELECT close FROM candles_1m WHERE symbol='{symbol}' "
            f"ORDER BY ts_ms DESC LIMIT 1",
        )
        latest_price = (
            float(latest_close[0][0])
            if latest_close and latest_close[0][0]
            else None
        )

        evidence = {
            "symbol": symbol,
            "latest_candle_utc": (
                latest_ts.isoformat()
                if hasattr(latest_ts, "isoformat")
                else str(latest_ts)
            ),
            "latest_price": latest_price,
            "range_15m": range_15m_val,
            "range_60m": range_60m_val,
            "gap_detected": len(large_gaps) > 0,
            "largest_gap_minutes": max(large_gaps) if large_gaps else None,
            "recent_gaps_minutes": gap_minutes_list,
            "gap_threshold_minutes": gap_threshold_minutes,
            "queries": [
                "SELECT MAX(ts_ms) FROM candles_1m WHERE symbol='BTCUSDT'",
                "SELECT MAX(high)-MIN(low) FROM candles_1m WHERE symbol='BTCUSDT' AND ts_ms >= NOW()-INTERVAL '15 minutes'",
                "SELECT MAX(high)-MIN(low) FROM candles_1m WHERE symbol='BTCUSDT' AND ts_ms >= NOW()-INTERVAL '60 minutes'",
                "SELECT ts_ms - LAG(ts_ms) OVER (ORDER BY ts_ms) FROM candles_1m WHERE symbol='BTCUSDT' ORDER BY ts_ms DESC LIMIT 10",
            ],
        }
        status = "blocked" if len(large_gaps) > 0 else "ok"
        limitations = []
        if len(large_gaps) > 0:
            limitations.append(
                f"candle gap(s) >{gap_threshold_minutes} min detected: "
                f"{large_gaps}"
            )
        return {
            "status": status,
            "evidence": evidence,
            "observed_at_utc": _utcnow(),
            "limitations": limitations,
            "no_mutation": True,
        }
    except Exception as exc:
        return _blocked(
            {"error": str(exc)},
            [f"candle probe failed: {exc}"],
        )


# ---------------------------------------------------------------------------
# 6. correlation_ledger probe
# ---------------------------------------------------------------------------


def probe_ledger(
    campaign_start_utc: str | None = None,
    host: str = DB_DEFAULTS["host"],
    port: int = DB_DEFAULTS["port"],
    dbname: str = DB_DEFAULTS["dbname"],
    user: str = DB_DEFAULTS["user"],
) -> ProbeResult:
    import importlib

    if not importlib.util.find_spec("psycopg2"):
        return _unavailable(
            {"error": "psycopg2 not installed"},
            ["install psycopg2 for ledger probes"],
        )

    try:
        latest = _run_sql(
            host, port, dbname, user,
            "SELECT ts_ms, event_type, status, lineage_hash "
            "FROM correlation_ledger ORDER BY ts_ms DESC LIMIT 1",
        )
        latest_event: dict | None = None
        if latest:
            latest_event = {
                "ts_ms": (
                    latest[0][0].isoformat()
                    if hasattr(latest[0][0], "isoformat")
                    else str(latest[0][0])
                ),
                "event_type": latest[0][1],
                "status": latest[0][2],
                "lineage_hash": latest[0][3],
            }

        count_since_start: int | None = None
        if campaign_start_utc:
            count_rows = _run_sql(
                host, port, dbname, user,
                f"SELECT COUNT(*) FROM correlation_ledger "
                f"WHERE ts_ms >= '{campaign_start_utc}'::timestamptz",
            )
            count_since_start = int(count_rows[0][0]) if count_rows else 0

        grouped = _run_sql(
            host, port, dbname, user,
            "SELECT event_type, status, COUNT(*) as cnt "
            "FROM correlation_ledger "
            "GROUP BY event_type, status ORDER BY event_type, status",
        )
        events_by_type_status: list[dict] = []
        for row in grouped:
            events_by_type_status.append(
                {
                    "event_type": row[0],
                    "status": row[1],
                    "count": int(row[2]),
                }
            )

        return _ok(
            {
                "latest_event": latest_event,
                "events_since_campaign_start": count_since_start,
                "events_by_type_status": events_by_type_status,
                "campaign_start_utc": campaign_start_utc,
                "queries": [
                    "SELECT ... FROM correlation_ledger ORDER BY ts_ms DESC LIMIT 1",
                    "SELECT COUNT(*) FROM correlation_ledger WHERE ts_ms >= ...",
                    "SELECT event_type, status, COUNT(*) FROM correlation_ledger GROUP BY ...",
                ],
            }
        )
    except Exception as exc:
        return _blocked(
            {"error": str(exc)},
            [f"ledger probe failed: {exc}"],
        )


# ---------------------------------------------------------------------------
# 7. Regime probe
# ---------------------------------------------------------------------------

REGIME_PATTERNS: list[tuple[str, str]] = [
    (r"HIGH_VOL_CHAOTIC", "HIGH_VOL_CHAOTIC"),
    (r"TREND", "TREND"),
    (r"\bRANGE\b", "RANGE"),
    (r"UNKNOWN", "UNKNOWN"),
]


def _try_http_regime(port: int = 8008, timeout: int = 5) -> str | None:
    try:
        import urllib.request
        url = f"http://localhost:{port}/health"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def probe_regime(
    container: str = "cdb_regime", health_port: int = 8008
) -> ProbeResult:
    http_body = _try_http_regime(port=health_port)
    if http_body:
        for pattern, label in REGIME_PATTERNS:
            if re.search(pattern, http_body):
                return _ok(
                    {
                        "current_regime": label,
                        "source": f"http://localhost:{health_port}/health",
                        "raw": http_body.strip()[:500],
                    }
                )
        return _warn(
            {
                "current_regime": "unknown",
                "source": f"http://localhost:{health_port}/health",
                "raw": http_body.strip()[:500],
            },
            ["regime health endpoint did not contain known regime pattern"],
        )

    try:
        logs = _run_docker_cmd(
            ["logs", container, "--tail", "10"], timeout=10
        )
    except (FileNotFoundError, RuntimeError) as exc:
        return _unavailable(
            {"error": str(exc)},
            [f"container {container} not found or Docker unavailable"],
        )

    for pattern, label in REGIME_PATTERNS:
        if re.search(pattern, logs, re.IGNORECASE):
            return _ok(
                {
                    "current_regime": label,
                    "source": f"docker logs {container} --tail 10",
                    "raw": logs.strip()[:500],
                },
                ["regime extracted from logs; may be stale"],
            )

    return _unavailable(
        {
            "current_regime": "unknown",
            "source": f"docker logs {container} --tail 10",
            "raw": logs.strip()[:500],
        },
        ["no known regime pattern found in logs or health endpoint"],
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ARVP Campaign Supervisor \u2014 Read-Only Probe Layer"
    )
    parser.add_argument("--all", action="store_true", help="Run all probes")
    parser.add_argument("--host", action="store_true", help="Host probe")
    parser.add_argument("--docker", action="store_true", help="Docker probe")
    parser.add_argument(
        "--safety", action="store_true", help="Safety flags probe"
    )
    parser.add_argument("--db", action="store_true", help="DB readonly probe")
    parser.add_argument(
        "--candles", action="store_true", help="Candle/market data probe"
    )
    parser.add_argument(
        "--ledger", action="store_true", help="correlation_ledger probe"
    )
    parser.add_argument("--regime", action="store_true", help="Regime probe")
    parser.add_argument(
        "--campaign-start",
        help="Campaign start UTC (ISO-8601) for ledger probe",
    )
    parser.add_argument(
        "--docker-targets",
        nargs="*",
        default=DEFAULT_RUNTIME_TARGETS,
        help="Docker container targets",
    )

    args = parser.parse_args()

    if not any(
        [
            args.all,
            args.host,
            args.docker,
            args.safety,
            args.db,
            args.candles,
            args.ledger,
            args.regime,
        ]
    ):
        parser.print_help()
        sys.exit(1)

    results: list[ProbeResult] = []

    if args.all or args.host:
        results.append({"probe": "host", **probe_host()})
    if args.all or args.docker:
        results.append(
            {"probe": "docker", **probe_docker(targets=args.docker_targets)}
        )
    if args.all or args.safety:
        results.append({"probe": "safety", **probe_safety()})
    if args.all or args.db:
        results.append({"probe": "db_readonly", **probe_db_readonly()})
    if args.all or args.candles:
        results.append({"probe": "candles", **probe_candles()})
    if args.all or args.ledger:
        results.append(
            {
                "probe": "correlation_ledger",
                **probe_ledger(campaign_start_utc=args.campaign_start),
            }
        )
    if args.all or args.regime:
        results.append({"probe": "regime", **probe_regime()})

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
