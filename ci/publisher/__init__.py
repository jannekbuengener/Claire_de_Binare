"""Trusted local CI status publisher (Phase 3a + #4170 App-bound Check Run).

Default publish path is ``--publisher-backend check-run`` (App auto-mint).
Legacy ``commit-status`` remains available but does **not** satisfy live Branch
Protection after #4170 Phase D (`app_id=4410232`).
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_STATUS_CONTEXT",
    "PREVIEW_STATUS_CONTEXT",
    "EXPECTED_REPOSITORY",
    "EXPECTED_GITHUB_APP_ID",
]

DEFAULT_STATUS_CONTEXT = "cdb-local-ci"
PREVIEW_STATUS_CONTEXT = "cdb-local-ci-preview"
EXPECTED_REPOSITORY = "jannekbuengener/Claire_de_Binare"
EXPECTED_GITHUB_APP_ID = 4410232
