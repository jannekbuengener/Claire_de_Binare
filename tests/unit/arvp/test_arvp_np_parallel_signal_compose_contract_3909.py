"""Parallel natural-paper multi-cdb_signal compose contract tests (#3909)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_RED = REPO_ROOT / "infrastructure" / "compose" / "compose.red.yml"
SIGNAL_OVERRIDE = (
    REPO_ROOT / "manifests" / "runtime_np_parallel_signal_compose_override.yml"
)
MANIFESTS_README = REPO_ROOT / "manifests" / "README.md"
SIGNAL_README = REPO_ROOT / "services" / "signal" / "README.md"

PARALLEL_SERVICES = ("cdb_signal_pb1", "cdb_signal_donchian")
EXPECTED_STRATEGY_IDS = {
    "cdb_signal_pb1": "primary_breakout_v1",
    "cdb_signal_donchian": "donchian_breakout_v1",
}
EXPECTED_BOT_IDS = {
    "cdb_signal_pb1": "np-pb1-parallel-01",
    "cdb_signal_donchian": "np-donchian-parallel-01",
}
EXPECTED_PORTS = {
    "cdb_signal_pb1": "8015",
    "cdb_signal_donchian": "8016",
}

COMPOSE_SECRET_FILES = (
    "REDIS_PASSWORD",
    "POSTGRES_PASSWORD",
    "POSTGRES_PASSWORD_DSN",
    "GRAFANA_PASSWORD",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "ALERT_EMAIL_TO",
)


def _write_compose_secrets_stub(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name in COMPOSE_SECRET_FILES:
        (directory / name).write_text("stub\n", encoding="utf-8")
    return directory


def _load_override() -> dict:
    return yaml.safe_load(SIGNAL_OVERRIDE.read_text(encoding="utf-8"))


def _service_env(service_name: str) -> dict[str, str]:
    override = _load_override()
    env = override["services"][service_name]["environment"]
    return {key: str(value) for key, value in env.items()}


def test_override_declares_two_parallel_signal_services() -> None:
    override = _load_override()
    services = set(override["services"])
    assert set(PARALLEL_SERVICES).issubset(services)


def test_canonical_cdb_signal_is_profile_gated() -> None:
    override = _load_override()
    profiles = override["services"]["cdb_signal"]["profiles"]
    assert profiles == ["single-signal-default"]


@pytest.mark.parametrize("service_name", PARALLEL_SERVICES)
def test_parallel_service_has_distinct_container_name(service_name: str) -> None:
    override = _load_override()
    container_name = override["services"][service_name]["container_name"]
    assert container_name == service_name


@pytest.mark.parametrize("service_name", PARALLEL_SERVICES)
def test_parallel_service_has_distinct_signal_port(service_name: str) -> None:
    env = _service_env(service_name)
    assert env["SIGNAL_PORT"] == EXPECTED_PORTS[service_name]


@pytest.mark.parametrize("service_name", PARALLEL_SERVICES)
def test_parallel_service_has_expected_strategy_id(service_name: str) -> None:
    env = _service_env(service_name)
    assert env["SIGNAL_STRATEGY_ID"] == EXPECTED_STRATEGY_IDS[service_name]


@pytest.mark.parametrize("service_name", PARALLEL_SERVICES)
def test_parallel_service_has_non_empty_signal_bot_id(service_name: str) -> None:
    env = _service_env(service_name)
    bot_id = env["SIGNAL_BOT_ID"].strip()
    assert bot_id
    assert bot_id == EXPECTED_BOT_IDS[service_name]


def test_signal_bot_ids_are_distinct_across_instances() -> None:
    bot_ids = [EXPECTED_BOT_IDS[name] for name in PARALLEL_SERVICES]
    assert len(bot_ids) == len(set(bot_ids))


def test_host_ports_do_not_collide_with_canonical_signal() -> None:
    override = _load_override()
    canonical = yaml.safe_load(COMPOSE_RED.read_text(encoding="utf-8"))
    canonical_port = canonical["services"]["cdb_signal"]["ports"][0]
    assert "8005" in canonical_port

    parallel_ports = []
    for service_name in PARALLEL_SERVICES:
        port_mapping = override["services"][service_name]["ports"][0]
        parallel_ports.append(port_mapping)
        assert "8005" not in port_mapping
    assert len(parallel_ports) == len(set(parallel_ports))


def test_override_header_documents_lr_no_go_and_pilot_not_ready() -> None:
    header = SIGNAL_OVERRIDE.read_text(encoding="utf-8").lower()
    assert "lr no-go" in header
    assert "#3912" in header
    assert "not ready" in header
    assert "runtime-go" in header
    assert "#3893" in header


def test_override_documents_risk_side_filter_contract() -> None:
    header = SIGNAL_OVERRIDE.read_text(encoding="utf-8").lower()
    assert "risk-side filter" in header or "risk-side filter contract" in header
    assert "strategy_id" in header
    assert "#3911" in header


def test_manifests_readme_documents_campaign_scope_and_no_runtime_go() -> None:
    text = MANIFESTS_README.read_text(encoding="utf-8").lower()
    assert "runtime_np_parallel_signal_compose_override.yml" in text
    assert "no-go" in text
    assert "#3912" in text
    assert "not ready" in text
    assert "runtime-go" in text


def test_signal_readme_links_parallel_override() -> None:
    text = SIGNAL_README.read_text(encoding="utf-8")
    assert "runtime_np_parallel_signal_compose_override.yml" in text


def test_pilot_issue_3912_is_not_freed_by_compose_delivery() -> None:
    """#3909 delivers infra only; #3912 still requires #3911 + RUNTIME-GO."""
    header = SIGNAL_OVERRIDE.read_text(encoding="utf-8")
    manifests_readme = MANIFESTS_README.read_text(encoding="utf-8")
    joined = f"{header}\n{manifests_readme}".lower()
    assert "#3911" in joined
    assert "not ready" in joined


def test_docker_compose_config_merge_is_valid(tmp_path: Path) -> None:
    secrets_dir = _write_compose_secrets_stub(tmp_path / "compose-secrets")
    env = {**os.environ, "SECRETS_PATH": str(secrets_dir)}
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_RED),
            "-f",
            str(SIGNAL_OVERRIDE),
            "config",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and "docker" in (result.stderr or "").lower():
        pytest.skip(f"docker compose unavailable: {result.stderr}")
    assert result.returncode == 0, result.stderr
    merged = yaml.safe_load(result.stdout)
    assert "cdb_signal_pb1" in merged["services"]
    assert "cdb_signal_donchian" in merged["services"]
