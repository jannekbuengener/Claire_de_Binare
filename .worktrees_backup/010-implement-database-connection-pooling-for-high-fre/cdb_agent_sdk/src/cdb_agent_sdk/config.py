"""
Configuration for the CDB Agent SDK.

Lädt Konfiguration aus Environment-Variablen.
Keine API-Keys erforderlich - nutzt Claude Code Max Plan Auth.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache


@dataclass
class Config:
    """Konfiguration für den Data Flow & Observability Engineer."""

    # CDB Project Root
    cdb_root: str

    # Grafana
    grafana_url: str
    grafana_api_key: str | None

    # Redis
    redis_host: str
    redis_port: int
    redis_password: str | None

    # PostgreSQL
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str | None

    # Features
    use_mcp_docker: bool

    @property
    def redis_url(self) -> str:
        """Konstruiert Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    @property
    def postgres_url(self) -> str:
        """Konstruiert PostgreSQL URL."""
        auth = f"{self.postgres_user}"
        if self.postgres_password:
            auth = f"{auth}:{self.postgres_password}"
        return f"postgresql://{auth}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


def _find_cdb_root() -> str:
    """
    Findet das CDB Projekt-Root-Verzeichnis.

    Sucht nach oben bis ein Verzeichnis mit 'core/' und 'services/' gefunden wird.
    """
    # Start from current file's location
    current = Path(__file__).resolve().parent

    # Walk up to find the CDB root (contains core/ and services/)
    for _ in range(10):  # Max 10 levels up
        if (current / "core").is_dir() and (current / "services").is_dir():
            return str(current)
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Fallback to environment or current directory
    return os.getenv("CDB_ROOT", str(Path.cwd()))


@lru_cache
def get_config() -> Config:
    """
    Lädt und cached die Konfiguration.

    Returns:
        Config object mit allen Einstellungen
    """
    return Config(
        # CDB Root
        cdb_root=os.getenv("CDB_ROOT", _find_cdb_root()),

        # Grafana
        grafana_url=os.getenv("GRAFANA_URL", "http://localhost:3000"),
        grafana_api_key=os.getenv("GRAFANA_API_KEY"),

        # Redis
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_password=os.getenv("REDIS_PASSWORD"),

        # PostgreSQL
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "cdb"),
        postgres_user=os.getenv("POSTGRES_USER", "cdb"),
        postgres_password=os.getenv("POSTGRES_PASSWORD"),

        # Features
        use_mcp_docker=os.getenv("USE_MCP_DOCKER", "1").lower() in ("1", "true", "yes"),
    )
