"""Shared fixtures für E2E Tests.

Diese Fixtures stellen echte Verbindungen zu Redis und PostgreSQL her
(keine Mocks).
"""

from __future__ import annotations

import os
import subprocess
from typing import Generator

import psycopg2
import pytest
import redis


@pytest.fixture(scope="session")
def docker_compose_running() -> bool:
    """Prüft ob docker compose Stack läuft."""
    result = subprocess.run(
        ["docker", "compose", "ps", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        pytest.skip("Docker Compose nicht verfügbar oder nicht gestartet")

    # Wenn Container-IDs zurückgegeben werden, läuft der Stack
    container_ids = result.stdout.strip().split("\n")
    running = len(container_ids) > 0 and container_ids[0] != ""

    if not running:
        pytest.skip(
            "Docker Compose Stack nicht gestartet. " "Starte mit: docker compose up -d"
        )

    return True


@pytest.fixture(scope="session")
def redis_connection(
    docker_compose_running: bool,
) -> Generator[redis.Redis, None, None]:
    """Echte Redis-Verbindung für Session-Scope."""
    redis_password = os.getenv("REDIS_PASSWORD", "claire_redis_secret_2024")

    client = redis.Redis(
        host="localhost",
        port=6379,
        password=redis_password,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )

    try:
        client.ping()
    except redis.ConnectionError as e:
        pytest.skip(f"Redis nicht erreichbar: {e}")

    yield client
    client.close()


@pytest.fixture(scope="session")
def postgres_connection(
    docker_compose_running: bool,
) -> Generator[psycopg2.extensions.connection, None, None]:
    """Echte PostgreSQL-Verbindung für Session-Scope."""
    pg_user = os.getenv("POSTGRES_USER", "claire_user")
    pg_password = os.getenv("POSTGRES_PASSWORD", "claire_db_secret_2024")
    pg_db = os.getenv("POSTGRES_DB", "claire_de_binare")

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database=pg_db,
            user=pg_user,
            password=pg_password,
            connect_timeout=5,
        )
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL nicht erreichbar: {e}")

    yield conn
    conn.close()


@pytest.fixture
def clean_test_data(postgres_connection):
    """Cleanup-Fixture: Entfernt Test-Daten nach jedem Test."""
    yield

    # Cleanup nach Test
    cursor = postgres_connection.cursor()

    # Lösche Test-Einträge (erkennbar an _TEST suffix im Symbol)
    cleanup_queries = [
        "DELETE FROM trades WHERE symbol LIKE '%_TEST'",
        "DELETE FROM signals WHERE symbol LIKE '%_TEST'",
        "DELETE FROM orders WHERE symbol LIKE '%_TEST'",
    ]

    for query in cleanup_queries:
        try:
            cursor.execute(query)
        except psycopg2.Error:
            # Tabelle existiert evtl. noch nicht
            pass

    postgres_connection.commit()
    cursor.close()
