"""CVE-2026-57432 image contract for allocation + db_writer (#4114).

Protects the evidence-based HOLD for Debian Trixie ``perl-base``:
shared base lineage stays documented, no scanner silencing, and the
upstream-hold evidence file keeps its required remediation fields.

Scope is exactly allocation + db_writer (not the eight-image #4106 cluster).
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
BASE_IMAGE = "python:3.14-slim-trixie"

ALLOCATION_DOCKERFILE = REPO_ROOT / "services" / "allocation" / "Dockerfile"
DB_WRITER_DOCKERFILE = REPO_ROOT / "services" / "db_writer" / "Dockerfile"
SCOPE_DOCKERFILES = (ALLOCATION_DOCKERFILE, DB_WRITER_DOCKERFILE)

# Explicit non-scope guard: #4106 covers eight images; #4114 must stay narrow.
OUT_OF_SCOPE_DOCKERFILES = (
    REPO_ROOT / "services" / "execution" / "Dockerfile",
    REPO_ROOT / "services" / "market" / "Dockerfile",
    REPO_ROOT / "services" / "regime" / "Dockerfile",
    REPO_ROOT / "services" / "risk" / "Dockerfile",
    REPO_ROOT / "services" / "signal" / "Dockerfile",
    REPO_ROOT / "services" / "ws" / "Dockerfile",
)

EVIDENCE_FILE = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "4114_CVE-2026-57432_UPSTREAM_HOLD.md"
)
RECONCILIATION_MD = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "security"
    / "CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-03.md"
)
TRIVYIGNORE_FILE = REPO_ROOT / ".trivyignore"

FROM_RE = re.compile(
    r"^FROM\s+(?P<image>[^\s@]+)"
    r"(?:@(?P<digest>sha256:[0-9a-f]{64}))?"
    r"(?:\s+[Aa][Ss]\s+\S+)?"
    r"\s*$",
    re.MULTILINE,
)
APT_UPGRADE_RE = re.compile(r"apt-get\s+upgrade\s+-y")
OBSERVED_DIGEST_MARKER_RE = re.compile(
    r"Observed\s+base\s+digest\s*\(HOLD\s+snapshot\)\s*:\s*"
    r"`(?P<digest>sha256:[0-9a-f]{64})`",
    re.IGNORECASE,
)


def _dockerfile_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _from_matches(path: Path) -> list[re.Match[str]]:
    matches = list(FROM_RE.finditer(_dockerfile_text(path)))
    assert matches, f"{path} must declare at least one FROM line"
    return matches


def _runtime_from(path: Path) -> re.Match[str]:
    return _from_matches(path)[-1]


def test_scope_dockerfiles_share_identical_base_digest() -> None:
    """Shared lineage is the root-cause premise for the #4114 cluster."""
    digests = {_runtime_from(path).group("digest") for path in SCOPE_DOCKERFILES}
    images = {_runtime_from(path).group("image") for path in SCOPE_DOCKERFILES}
    assert None not in digests, "allocation and db_writer must pin a sha256 digest"
    assert len(digests) == 1, (
        "allocation and db_writer must pin the same base digest for the "
        f"shared OS-layer finding; found {digests}"
    )
    assert images == {BASE_IMAGE}


@pytest.mark.parametrize("dockerfile", SCOPE_DOCKERFILES, ids=lambda p: p.parent.name)
def test_scope_dockerfiles_still_run_apt_upgrade(dockerfile: Path) -> None:
    text = _dockerfile_text(dockerfile)
    assert APT_UPGRADE_RE.search(text), (
        f"{dockerfile} must keep apt-get upgrade so suite-native security "
        "updates land automatically once Debian publishes them"
    )


def test_scope_is_exactly_allocation_and_db_writer() -> None:
    """#4114 must not silently expand to the eight-image #4106 surface."""
    assert {p.parent.name for p in SCOPE_DOCKERFILES} == {"allocation", "db_writer"}
    for path in OUT_OF_SCOPE_DOCKERFILES:
        assert path.is_file(), f"expected sibling Dockerfile present: {path}"


def test_cve_is_not_silenced_by_trivyignore() -> None:
    text = (
        TRIVYIGNORE_FILE.read_text(encoding="utf-8")
        if TRIVYIGNORE_FILE.exists()
        else ""
    )
    entries = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    silenced = [entry for entry in entries if CVE_ID in entry or PACKAGE in entry]
    assert (
        silenced == []
    ), f"{CVE_ID} / {PACKAGE} must not be ignored in .trivyignore: {silenced}"


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
        "Scope-drift correction",
        "EXTERNAL_LIVE_CHECK",
        "Observed base digest (HOLD snapshot)",
        "not an eternal required digest",
        "UPSTREAM_NO_FIXED_VERSION",
    )
    missing = [item for item in required if item not in text]
    assert missing == [], f"evidence file missing required markers: {missing}"


def test_evidence_observed_digest_matches_current_dockerfiles() -> None:
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    marker = OBSERVED_DIGEST_MARKER_RE.search(text)
    assert (
        marker is not None
    ), "evidence must declare Observed base digest (HOLD snapshot): `sha256:…`"
    observed = marker.group("digest")
    digests = {_runtime_from(path).group("digest") for path in SCOPE_DOCKERFILES}
    assert digests == {observed}, (
        "HOLD evidence observed digest must match scoped Dockerfile pins; "
        f"evidence={observed}, dockerfiles={digests}"
    )


def test_evidence_rejects_scanner_dismissal_and_cross_suite_glibc() -> None:
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    assert "no alert dismissal" in text.lower()
    assert "libc6 (>= 2.42)" in text
    assert "Rejected" in text
    assert VERDICT in text
    assert "cannot detect Debian FixedVersion offline" in text
    assert "a new shared digest is allowed" in text.lower()


def test_reconciliation_snapshot_names_4114_hold() -> None:
    assert RECONCILIATION_MD.is_file()
    text = RECONCILIATION_MD.read_text(encoding="utf-8")
    assert "#4114" in text
    assert CVE_ID in text
    assert VERDICT in text
    assert "cdb_allocation" in text and "cdb_db_writer" in text
