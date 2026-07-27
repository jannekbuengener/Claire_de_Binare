"""Trusted local CI status publisher (Phase 3a — Commit Status).

Publishes GitHub commit statuses only after fail-closed validation of local
Docker CI evidence. Check Runs require a GitHub App and are not used here.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_STATUS_CONTEXT",
    "PREVIEW_STATUS_CONTEXT",
    "EXPECTED_REPOSITORY",
]

DEFAULT_STATUS_CONTEXT = "cdb-local-ci"
PREVIEW_STATUS_CONTEXT = "cdb-local-ci-preview"
EXPECTED_REPOSITORY = "jannekbuengener/Claire_de_Binare"
