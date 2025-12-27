"""
Unified Secret Loader
Provides centralized secret loading with Docker secrets, env var, and file path fallback.

Usage:
    from core.secrets import read_secret

    api_key = read_secret("mexc_api_key", "MEXC_API_KEY")
    # Tries: /run/secrets/mexc_api_key → $MEXC_API_KEY → ""
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def read_secret(secret_name: str, fallback_env: Optional[str] = None) -> str:
    """
    Read secret from Docker secrets or fallback to environment variable.

    Supports both production (Docker secrets) and development (.env) workflows.

    Priority order:
    1. Docker secret file: /run/secrets/{secret_name}
    2. Environment variable: {fallback_env}
    3. Empty string (if neither found)

    Args:
        secret_name: Name of the Docker secret file
        fallback_env: Environment variable name for development fallback

    Returns:
        Secret value as string, empty string if not found

    Security:
        - Uses is_file() to prevent IsADirectoryError (Issue #223)
        - Logs warnings for missing secrets (non-sensitive)
        - Never logs secret values

    Examples:
        >>> read_secret("postgres_password", "POSTGRES_PASSWORD")
        "my_secure_password"

        >>> read_secret("missing_secret")
        ""
    """
    # Try Docker secret first (production)
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.is_file():
        try:
            value = secret_path.read_text().strip()
            logger.debug(f"Loaded secret '{secret_name}' from Docker secrets")
            return value
        except Exception as e:
            logger.warning(f"Failed to read Docker secret '{secret_name}': {e}")

    # Fallback to environment variable (development)
    if fallback_env:
        value = os.getenv(fallback_env, "")
        if value:
            logger.debug(f"Loaded secret '{secret_name}' from env var '{fallback_env}'")
            return value
        else:
            logger.warning(
                f"Secret '{secret_name}' not found in Docker secrets or env var '{fallback_env}'"
            )
    else:
        logger.warning(f"Secret '{secret_name}' not found (no fallback env specified)")

    return ""


def read_secret_file(file_path: str, fallback_env: Optional[str] = None) -> str:
    """
    Read secret from a file path or fallback to environment variable.

    Used for secrets stored as file paths in .env (e.g., Windows development).

    Priority order:
    1. File at {file_path}
    2. Environment variable: {fallback_env}
    3. Empty string

    Args:
        file_path: Path to secret file (e.g., "C:\\Users\\...\\secrets\\api_key.txt")
        fallback_env: Environment variable name for fallback

    Returns:
        Secret value as string, empty string if not found

    Security:
        - Uses is_file() to prevent IsADirectoryError (Issue #223)
        - Validates file exists before reading
        - Logs warnings (non-sensitive)

    Examples:
        >>> read_secret_file("C:\\secrets\\api_key.txt", "API_KEY")
        "my_api_key"
    """
    secret_file = Path(file_path)

    # Try file path first
    if secret_file.is_file():
        try:
            value = secret_file.read_text().strip()
            logger.debug(f"Loaded secret from file: {file_path}")
            return value
        except Exception as e:
            logger.warning(f"Failed to read secret file '{file_path}': {e}")
    elif secret_file.exists():
        # Path exists but is not a file (likely a directory)
        logger.error(
            f"Secret path '{file_path}' exists but is not a file (IsADirectoryError prevented)"
        )

    # Fallback to environment variable
    if fallback_env:
        value = os.getenv(fallback_env, "")
        if value:
            logger.debug(f"Loaded secret from env var '{fallback_env}' (file path fallback)")
            return value
        else:
            logger.warning(f"Secret not found at '{file_path}' or env var '{fallback_env}'")
    else:
        logger.warning(f"Secret not found at '{file_path}' (no fallback env specified)")

    return ""


def validate_secrets(*secret_names: str) -> bool:
    """
    Validate that required secrets are present (non-empty).

    Args:
        *secret_names: Names of secrets to validate

    Returns:
        True if all secrets are non-empty, False otherwise

    Example:
        >>> api_key = read_secret("api_key", "API_KEY")
        >>> api_secret = read_secret("api_secret", "API_SECRET")
        >>> if not validate_secrets("api_key", "api_secret"):
        >>>     raise ValueError("Missing required secrets")
    """
    missing = []
    for name in secret_names:
        if not name:
            missing.append(name)

    if missing:
        logger.error(f"Missing required secrets: {', '.join(missing)}")
        return False

    return True
