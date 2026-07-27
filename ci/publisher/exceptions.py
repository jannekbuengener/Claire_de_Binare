"""Publisher-specific fail-closed exceptions."""

from __future__ import annotations

from ci.lib.evidence import EvidenceError


class PublisherError(EvidenceError):
    """Raised when publication validation or GitHub interaction fails closed."""


class AuthenticationError(PublisherError):
    """Token missing or insufficient permissions."""


class GitHubApiError(PublisherError):
    """Ambiguous or failed GitHub API response."""


class LedgerError(PublisherError):
    """Published-run ledger corruption or anti-replay violation."""
