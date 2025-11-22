"""E2E Test: Docker Compose Full Stack Validierung.

Dieser Test prüft, ob alle Claire-Services erfolgreich starten und
ihre Health-Checks bestehen.

Voraussetzung: docker compose up -d
Ausführung: pytest -v -m e2e tests/e2e/test_docker_compose_full_stack.py
"""

from __future__ import annotations

import subprocess
import time
from typing import List

import pytest
import requests


# Alle Claire-Services mit erwarteten Health-Endpoints
SERVICES = {
    "cdb_redis": {"port": 6379, "health_cmd": "redis-cli ping"},
    "cdb_postgres": {"port": 5432, "health_cmd": None},  # Nur Container-Health
    "cdb_ws": {"port": 8000, "health_url": "http://localhost:8000/health"},
    "cdb_core": {"port": 8001, "health_url": "http://localhost:8001/health"},
    "cdb_risk": {"port": 8002, "health_url": "http://localhost:8002/health"},
    "cdb_execution": {
        "port": 8003,
        "health_url": "http://localhost:8003/health",
    },
}


def _run_command(cmd: List[str]) -> tuple[int, str, str]:
    """Führt Command aus und gibt (returncode, stdout, stderr) zurück."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _check_container_running(container_name: str) -> bool:
    """Prüft ob Container läuft via docker compose ps."""
    returncode, stdout, _ = _run_command(
        ["docker", "compose", "ps", "-q", container_name]
    )
    if returncode != 0:
        return False
    # Wenn Container-ID zurückgegeben wird, läuft er
    return len(stdout.strip()) > 0


def _check_container_healthy(container_name: str) -> bool:
    """Prüft Health-Status via docker inspect."""
    returncode, stdout, _ = _run_command(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Health.Status}}",
            container_name,
        ]
    )
    if returncode != 0:
        # Container hat evtl. keinen Health-Check definiert
        # In diesem Fall: Als "healthy" werten wenn er läuft
        return _check_container_running(container_name)

    health_status = stdout.strip()
    return health_status == "healthy"


def _check_http_health(url: str, timeout: int = 5) -> bool:
    """Prüft HTTP Health-Endpoint."""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_docker_compose_stack_is_running():
    """Test: Alle Claire-Container sind gestartet und laufen."""
    for service_name in SERVICES:
        is_running = _check_container_running(service_name)
        assert is_running, (
            f"Container '{service_name}' läuft nicht. "
            f"Starte mit: docker compose up -d"
        )


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_docker_compose_containers_are_healthy():
    """Test: Alle Claire-Container bestehen Health-Checks."""
    # Warte kurz, damit Health-Checks Zeit haben sich zu stabilisieren
    time.sleep(2)

    for service_name in SERVICES:
        is_healthy = _check_container_healthy(service_name)
        assert is_healthy, (
            f"Container '{service_name}' ist nicht healthy. "
            f"Prüfe Logs: docker compose logs {service_name}"
        )


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_http_health_endpoints_respond():
    """Test: Alle HTTP Health-Endpoints antworten korrekt."""
    # Warte kurz, damit Services hochgefahren sind
    time.sleep(3)

    tested_services = 0
    for service_name, config in SERVICES.items():
        health_url = config.get("health_url")
        if not health_url:
            # Überspringe Services ohne HTTP Health-Endpoint (z.B. Redis, Postgres)
            continue

        is_healthy = _check_http_health(health_url)
        assert is_healthy, (
            f"Health-Endpoint von '{service_name}' antwortet nicht: {health_url}\n"
            f"Prüfe Service-Logs: docker compose logs {service_name}"
        )
        tested_services += 1

    # Stelle sicher, dass mindestens ein Service getestet wurde
    assert tested_services > 0, "Keine Services mit HTTP Health-Endpoint gefunden"


@pytest.mark.e2e
@pytest.mark.local_only
@pytest.mark.slow
def test_services_respond_with_valid_health_json():
    """Test: Health-Endpoints liefern valides JSON."""
    required_field = "status"  # Mindestens "status" sollte vorhanden sein

    for service_name, config in SERVICES.items():
        health_url = config.get("health_url")
        if not health_url:
            continue

        try:
            response = requests.get(health_url, timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert required_field in data, (
                f"Health-Response von '{service_name}' fehlt Feld '{required_field}'. "
                f"Actual: {data}"
            )

            # Status sollte "ok", "healthy" oder "stale" sein
            # (cdb_ws kann "stale" sein wenn keine aktuellen Daten vorliegen)
            assert data["status"] in ["ok", "healthy", "stale"], (
                f"Health-Status von '{service_name}' hat unerwarteten Wert: {data['status']}"
            )

        except requests.RequestException as e:
            pytest.fail(f"Health-Check für '{service_name}' fehlgeschlagen: {e}")


@pytest.mark.e2e
@pytest.mark.local_only
def test_docker_compose_config_is_valid():
    """Test: docker-compose.yml ist syntaktisch valide."""
    returncode, stdout, stderr = _run_command(["docker", "compose", "config"])

    assert returncode == 0, (
        f"docker compose config fehlgeschlagen:\n{stderr}\n"
        "Prüfe docker-compose.yml auf Syntaxfehler"
    )

    # Config sollte "services" Section enthalten
    assert "services:" in stdout, (
        "docker-compose.yml enthält keine 'services' Section"
    )
