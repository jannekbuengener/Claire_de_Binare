"""Docker Compose Configuration Validation Tests.

These tests validate the docker-compose.yml structure without
requiring Docker to be installed or containers to be running.
"""

from __future__ import annotations

import os

import pytest
import yaml


@pytest.mark.unit
def test_docker_compose_file_exists():
    """Verify docker-compose.yml exists in project root."""
    assert os.path.exists("docker-compose.yml"), (
        "docker-compose.yml not found in project root"
    )


@pytest.mark.unit
def test_docker_compose_yaml_valid():
    """Verify docker-compose.yml is valid YAML syntax."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert isinstance(config, dict)
    assert "services" in config


@pytest.mark.unit
def test_docker_compose_has_required_services():
    """Verify docker-compose.yml contains all required services."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    required_services = {
        "cdb_redis": "Redis message bus",
        "cdb_postgres": "PostgreSQL database",
    }

    services = config.get("services", {})

    for service_name, description in required_services.items():
        assert service_name in services, (
            f"Missing required service: {service_name} ({description})"
        )


@pytest.mark.unit
def test_docker_compose_services_have_healthchecks():
    """Verify critical services have health check configurations."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    critical_services = ["cdb_redis", "cdb_postgres"]
    services = config.get("services", {})

    for service_name in critical_services:
        service = services.get(service_name, {})
        assert "healthcheck" in service, (
            f"Service {service_name} missing healthcheck configuration. "
            "Health checks are required for production readiness."
        )

        # Validate healthcheck structure
        healthcheck = service["healthcheck"]
        assert "test" in healthcheck, f"{service_name}: healthcheck missing 'test'"
        assert "interval" in healthcheck, f"{service_name}: healthcheck missing 'interval'"


@pytest.mark.unit
def test_docker_compose_uses_env_file():
    """Verify services are configured to use .env file."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})

    # Check if at least critical services use env_file
    critical_services = ["cdb_redis", "cdb_postgres"]

    for service_name in critical_services:
        service = services.get(service_name, {})
        assert "env_file" in service or "environment" in service, (
            f"{service_name} must use env_file or environment for configuration"
        )


@pytest.mark.unit
def test_docker_compose_port_mappings():
    """Verify services expose expected ports."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    expected_ports = {
        "cdb_redis": "6379",
        "cdb_postgres": "5432",
    }

    services = config.get("services", {})

    for service_name, expected_port in expected_ports.items():
        service = services.get(service_name, {})
        ports = service.get("ports", [])

        # Convert ports list to strings for comparison
        port_strings = [str(p) for p in ports]

        assert any(expected_port in str(port) for port in port_strings), (
            f"{service_name} should expose port {expected_port}"
        )


@pytest.mark.unit
def test_docker_compose_volumes_configured():
    """Verify persistent services have volume configurations."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    persistent_services = {
        "cdb_redis": "redis_data",
        "cdb_postgres": "postgres_data",
    }

    services = config.get("services", {})
    volumes_config = config.get("volumes", {})

    for service_name, expected_volume in persistent_services.items():
        service = services.get(service_name, {})
        volumes = service.get("volumes", [])

        # Check that volume is used
        assert any(expected_volume in str(vol) for vol in volumes), (
            f"{service_name} should use volume {expected_volume} for data persistence"
        )

        # Check that volume is defined
        assert expected_volume in volumes_config, (
            f"Volume {expected_volume} should be defined in top-level volumes section"
        )


@pytest.mark.unit
def test_docker_compose_network_configuration():
    """Verify services are connected to correct networks."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})
    networks_config = config.get("networks", {})

    # If networks are defined, verify they exist
    if networks_config:
        network_names = list(networks_config.keys())

        for service_name, service in services.items():
            if "networks" in service:
                service_networks = service["networks"]
                if isinstance(service_networks, list):
                    for net in service_networks:
                        assert net in network_names, (
                            f"{service_name} references undefined network: {net}"
                        )


@pytest.mark.unit
def test_docker_compose_restart_policies():
    """Verify services have appropriate restart policies."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})
    critical_services = ["cdb_redis", "cdb_postgres"]

    valid_restart_policies = ["no", "always", "on-failure", "unless-stopped"]

    for service_name in critical_services:
        service = services.get(service_name, {})

        if "restart" in service:
            restart_policy = service["restart"]
            assert restart_policy in valid_restart_policies, (
                f"{service_name} has invalid restart policy: {restart_policy}"
            )
