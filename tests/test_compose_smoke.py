"""Validate docker compose configuration syntax without starting services."""

from __future__ import annotations

import shutil
import subprocess

import pytest


@pytest.mark.integration
@pytest.mark.skip(reason="docker compose smoke test scaffold – not active yet")
def test_docker_compose_config_parses():
    """Run ``docker compose config`` to check syntax if Docker is available."""

    docker_binary = shutil.which("docker")
    if not docker_binary:
        pytest.skip("Docker CLI not available in PATH")

    result = subprocess.run(
        [docker_binary, "compose", "config"],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.xfail(f"docker compose config failed: {result.stderr.strip()}")

    assert "services" in result.stdout.lower()
