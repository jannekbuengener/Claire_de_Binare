"""OS-level Hermes profile identity mapping (#4289 Phase B2.0).

PROFILE_POLICY and separate HERMES_HOME directories are not an OS security
boundary. Each active profile MUST run under a distinct non-login Unix UID
and primary GID. Shared supplementary groups that mediate token/session/secret
access are forbidden.
"""

from __future__ import annotations

from typing import Final

# Profile instance name → dedicated system user / primary group (same name).
PROFILE_LINUX_USERS: Final[dict[str, str]] = {
    "jannek-assistant": "hermes-jannek-assistant",
    "cdb-engineer": "hermes-cdb-engineer",
}

# Shared installer/opt owner only — MUST NOT own profile homes, tokens, or PEM.
SHARED_INSTALL_USER: Final[str] = "hermes"

# Token delivery contract (cdb-engineer only).
TOKEN_RUNTIME_DIR: Final[str] = "/run/hermes/cdb-engineer"
TOKEN_FILE_NAME: Final[str] = "token"
PEM_HOST_PATH: Final[str] = "/etc/hermes/secrets/cdb-hermes-engineer.pem"

FORBIDDEN_TOKEN_CONSUMERS: Final[frozenset[str]] = frozenset(
    {
        "hermes-jannek-assistant",
        "hermes",
        "validation-chief",
        "hermes-validation-chief",
    }
)


def linux_user_for_profile(profile: str) -> str:
    """Return the dedicated non-login Linux user for a Hermes profile."""
    try:
        return PROFILE_LINUX_USERS[profile]
    except KeyError as exc:
        raise KeyError(
            f"no dedicated Linux user mapping for profile: {profile}"
        ) from exc


def linux_group_for_profile(profile: str) -> str:
    """Primary group equals the dedicated user name (no shared hermes group)."""
    return linux_user_for_profile(profile)


def profile_home(profile: str, *, base: str = "/var/lib/hermes") -> str:
    return f"{base.rstrip('/')}/profiles/{profile}"


def profile_log_dir(profile: str, *, base: str = "/var/log/hermes") -> str:
    return f"{base.rstrip('/')}/{profile}"


def token_file_path() -> str:
    return f"{TOKEN_RUNTIME_DIR.rstrip('/')}/{TOKEN_FILE_NAME}"


def assert_token_consumer_allowed(linux_user: str) -> None:
    """Fail closed when a forbidden identity would receive/read tokens."""
    if linux_user in FORBIDDEN_TOKEN_CONSUMERS:
        raise PermissionError(
            f"Linux user {linux_user} is forbidden from Hermes GitHub token delivery"
        )
    if linux_user != PROFILE_LINUX_USERS["cdb-engineer"]:
        raise PermissionError(
            f"only {PROFILE_LINUX_USERS['cdb-engineer']} may receive GitHub tokens "
            f"(got {linux_user})"
        )


def expected_dashboard_user_line(profile: str) -> str:
    """systemd User= line for hermes-dashboard@ instance (template uses %i)."""
    # Template expands User=hermes-%i → hermes-cdb-engineer etc.
    _ = linux_user_for_profile(profile)  # validate mapping exists
    return "User=hermes-%i"
