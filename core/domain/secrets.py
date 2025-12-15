---
relations:
  role: secret_provider
  domain: secrets
  upstream: []
  downstream:
    - docker-compose.yml
    - services/db_writer/db_writer.py
    - services/execution/service.py
    - services/risk/service.py
    - services/signal/service.py
  invariants:
    - /run/secrets/ path is a convention for Docker secrets.
---
"""
Docker Secrets Helper
Reads secrets from /run/secrets/ with fallback to environment variables
"""
import os
from pathlib import Path
from typing import Optional


def get_secret(secret_name: str, env_var: str, default: Optional[str] = None) -> Optional[str]:
    """
    Read secret from Docker Secrets file or environment variable

    Args:
        secret_name: Name of the secret file in /run/secrets/
        env_var: Environment variable name as fallback
        default: Default value if neither exists

    Returns:
        Secret value or None
    """
    # Try Docker Secrets first
    secret_file = Path(f"/run/secrets/{secret_name}")
    if secret_file.exists():
        return secret_file.read_text().strip()

    # Fallback to environment variable
    return os.getenv(env_var, default)
