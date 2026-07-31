"""CVE-2026-57432 image contract for allocation + db_writer (#4114).

Protects the evidence-based HOLD for Debian Trixie ``perl-base``:
shared base lineage stays documented, no scanner silencing, and the
upstream-hold evidence file keeps its required remediation fields.

Static Dockerfile / evidence parsing only — no image build, no registry
access, no runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

CVE_ID = "CVE-2026-57432"
ISSUE_REF = "#4114"
PACKAGE = "perl-base"
INSTALLED_VERSION = "5.40.1-6"
UPSTREAM_FIXED_VERSION = "5.40.1-8"
VERDICT = "HOLD_UPSTREAM_NO_FIXED_VERSION"
RE_EVAL_DATE = "2026-08-28"

ALLOCATION_DOCKERFILE = REPO_ROOT / "services" / "allocation" / "Dockerfile"
DB_WRITER_DOCKERFILE = REPO_ROOT / "services" / "db_writer" / "Dockerfile"
SCOPE_DOCKERFILES = (ALLOCATION_DOCKERFILE, DB_WRITER_DOCKERFILE)

EVIDENCE_FILE = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "4114_CVE-2026-57432_UPSTREAM_HOLD.md"
)
TRIVYIGNORE_FILE = REPO_ROOT / ".trivyignore"

FROM_RE = re.compile(
    r"^FROM\s+(?P<image>\S+?)(?:@(?P<digest>sha256:[0-9a-f]{64}))?\s*$",
    re.MULTILINE,
)
APT_UPGRADE_RE = re.compile(r"apt-get\s+upgrade\s+-y")


def _dockerfile_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _from_line(path: Path) -> re.Match[str]:
    match = FROM_RE.search(_dockerfile_text(path))
    assert match is not None, f"{path} must declare a FROM line"
    return match


def test_scope_dockerfiles_share_identical_base_digest() -> None:
    """Shared lineage is the root-cause premise for the #4114 cluster."""
    digests = {_from_line(path).group("digest") for path in SCOPE_DOCKERFILES}
    images = {_from_line(path).group("image") for path in SCOPE_DOCKERFILES}
    assert len(digests) == 1 and None not in digests, (
        "allocation and db_writer must pin the same base digest for the "
        f"shared OS-layer finding; found {digests}"
    )
    assert images == {"python:3.14-slim-trixie"}


@pytest.mark.parametrize("dockerfile", SCOPE_DOCKERFILES, ids=lambda p: p.name)
def test_scope_dockerfiles_still_run_apt_upgrade(dockerfile: Path) -> None:
    text = _dockerfile_text(dockerfile)
    assert APT_UPGRADE_RE.search(text), (
        f"{dockerfile} must keep apt-get upgrade so suite-native security "
        "updates land automatically once Debian publishes them"
    )


def test_cve_is_not_silenced_by_trivyignore() -> None:
    text = TRIVYIGNORE_FILE.read_text(encoding="utf-8") if TRIVYIGNORE_FILE.exists() else ""
    entries = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    silenced = [entry for entry in entries if CVE_ID in entry or PACKAGE in entry]
    assert silenced == [], (
        f"{CVE_ID} / {PACKAGE} must not be ignored in .trivyignore: {silenced}"
    )


def test_upstream_hold_evidence_documents_required_fields() -> None:
    assert EVIDENCE_FILE.is_file(), f"missing evidence file: {EVIDENCE_FILE}"
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    required = (
        CVE_ID,
        ISSUE_REF,
        PACKAGE,
        INSTALLED_VERSION,
        UPSTREAM_FIXED_VERSION,
        VERDICT,
        RE_EVAL_DATE,
        "FixedVersion",
        "Exploitability",
        "cdb_allocation",
        "cdb_db_writer",
        "libc6",
    )
    missing = [item for item in required if item not in text]
    assert missing == [], f"evidence file missing required markers: {missing}"


def test_evidence_rejects_scanner_dismissal_and_cross_suite_glibc() -> None:
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    assert "no alert dismissal" in text.lower()
    assert "libc6 (>= 2.42)" in text
    assert "Rejected" in text
    assert VERDICT in text
