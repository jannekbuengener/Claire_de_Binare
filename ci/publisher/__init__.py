"""Trusted local CI status publisher (Phase 3a Commit Status + #4170 Check Run backend).

Default publish path remains Commit Status. Check Runs are available only via
explicit ``--publisher-backend check-run`` with App installation credentials.
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
