from __future__ import annotations

import hashlib
import json
import os
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, Final, Iterable

import pytest
import redis
import requests

RUN_DATE = os.environ.get("RUN_DATE", "local")
ARTIFACT_ROOT = Path(f"backoffice/artifacts/{RUN_DATE}/integration")
ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

RETRY_ATTEMPTS: Final[int] = 10
RETRY_DELAY_SECONDS: Final[int] = 3
REQUIRED_ENV_KEYS: Final[tuple[str, ...]] = (
    "MEXC_API_KEY",
    "MEXC_API_SECRET",
    "REDIS_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)
SERVICES: Final[dict[str, int]] = {
    "cdb_core": 8001,
    "cdb_risk": 8002,
    "cdb_execution": 8003,
}


def _parse_env(env_path: Path) -> tuple[dict[str, str], list[str]]:
    env: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            striped = line.strip()
            if not striped or striped.startswith("#") or "=" not in striped:
                continue
            key, value = striped.split("=", 1)
            env[key.strip()] = value.strip()
    missing = [key for key in REQUIRED_ENV_KEYS if key not in env]
    sha_input = "\n".join(f"{key}={env.get(key, '')}" for key in sorted(env))
    sha256 = hashlib.sha256(sha_input.encode("utf-8")).hexdigest()
    env_report = ARTIFACT_ROOT / "env_sha256.txt"
    env_report.write_text(
        f"sha256={sha256}\n"
        f"missing_keys={','.join(missing) if missing else 'none'}\n",
        encoding="utf-8",
    )
    return env, missing


def _request_with_retries(url: str) -> tuple[int, float]:
    last_exception: Exception | None = None
    response: requests.Response | None = None
    for _ in range(RETRY_ATTEMPTS):
        start = time.perf_counter()
        try:
            response = requests.get(url, timeout=5)
            elapsed = time.perf_counter() - start
        except requests.RequestException as exc:
            last_exception = exc
            time.sleep(RETRY_DELAY_SECONDS)
            continue
        if response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
            return response.status_code, elapsed
        time.sleep(RETRY_DELAY_SECONDS)
    if last_exception:
        raise AssertionError(f"Request to {url} failed") from last_exception
    raise AssertionError(f"No response from {url}")


def _collect_metrics(urls: Iterable[str]) -> list[str]:
    lines: list[str] = []
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
        except requests.RequestException:
            continue
        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            continue
        snippet = "\n".join(response.text.splitlines()[:5])
        if snippet:
            lines.append(f"# {url}\n{snippet}\n")
    return lines


def _redis_smoke(env: dict[str, str]) -> None:
    password = env.get("REDIS_PASSWORD")
    client: Any = redis.Redis(
        host="cdb_redis",
        port=6379,
        password=password,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    assert client.ping(), "Redis PING failed"
    channel = "market_data_smoke"
    message = f"smoke:{time.time()}"
    pubsub = client.pubsub()
    pubsub.subscribe(channel)
    # Drain subscription confirmation before publishing.
    start = time.time()
    while time.time() - start < 5:
        msg = pubsub.get_message(timeout=1)
        if msg and msg.get("type") == "subscribe":
            break
    client.publish(channel, message)
    received = None
    start = time.time()
    while time.time() - start < 5:
        msg = pubsub.get_message(timeout=1)
        if msg and msg.get("type") == "message":
            received = msg["data"]
            break
        time.sleep(0.1)
    pubsub.close()
    assert received == message, "Redis Pub/Sub did not round-trip message"


@pytest.mark.integration
def test_infrastructure_health_and_bus_flow() -> None:
    env_values, missing_keys = _parse_env(Path(".env"))
    health_results: list[dict[str, object]] = []
    metrics_urls = [
        f"http://{service}:{port}/metrics" for service, port in SERVICES.items()
    ]

    for service, port in SERVICES.items():
        status_code, elapsed = _request_with_retries(f"http://{service}:{port}/health")
        assert (
            status_code < HTTPStatus.INTERNAL_SERVER_ERROR
        ), f"{service} health returned {status_code}"
        health_results.append(
            {"service": service, "status_code": status_code, "response_time": elapsed}
        )

    metrics = _collect_metrics(metrics_urls)
    if metrics:
        (ARTIFACT_ROOT / "metrics.txt").write_text("\n".join(metrics), encoding="utf-8")

    (ARTIFACT_ROOT / "health_checks.json").write_text(
        json.dumps(health_results, indent=2), encoding="utf-8"
    )

    _redis_smoke(env_values)

    # Missing env keys do not fail the test but are recorded for Evidence.
    if missing_keys:
        (ARTIFACT_ROOT / "env_missing.txt").write_text(
            ",".join(missing_keys), encoding="utf-8"
        )
