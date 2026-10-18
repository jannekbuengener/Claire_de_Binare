"""CVE-2026-16742 HOLD contract for eight CDB service images (#4570-#4577).

Protects the evidence-based upstream HOLD for Debian Trixie systemd source-package
alerts reported against libsystemd0/libudev1. The vulnerable upstream component is
systemd-homed; CDB service Dockerfiles must not silently introduce that runtime path.

Static Dockerfile/evidence parsing only — no image build, registry access, live Debian
FixedVersion probe, alert dismissal, or runtime mutation.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

CVE_ID = "CVE-2026-16742"
ISSUE_REFS = tuple(f"#{number}" for number in range(4570, 4578))
PACKAGES = ("libsystemd0", "libudev1")
INSTALLED_VERSION = "257.13-1~deb13u1"
VERDICT = "HOLD_UPSTREAM_NO_FIXED_VERSION"
RE_EVAL_DATE = "2026-11-01"
BASE_IMAGE = "python:3.14-slim-trixie"

SCOPE_DOCKERFILES = (
    REPO_ROOT / "services" / "allocation" / "Dockerfile",
    REPO_ROOT / "services" / "db_writer" / "Dockerfile",
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
    / "4570-4577_CVE-2026-16742_UPSTREAM_HOLD.md"
)
TRIVYIGNORE_FILE = REPO_ROOT / ".trivyignore"

FROM_RE = re.compile(
    r"^FROM\s+(?P<image>[^\s@]+)"
    r"(?:@(?P<digest>sha256:[0-9a-f]{64}))?"
    r"(?:\s+[Aa][Ss]\s+\S+)?"
    r"\s*$",
    re.MULTILINE,
)
OBSERVED_DIGEST_MARKER_RE = re.compile(
    r"Observed\s+base\s+digest\s*\(HOLD\s+snapshot\)\s*:\s*"
    r"`(?P<digest>sha256:[0-9a-f]{64})`",
    re.IGNORECASE,
)
FORBIDDEN_HOMED_RUNTIME_MARKERS = (
    "systemd-homed",
    "homectl",
    "systemctl enable systemd-homed",
    "/usr/lib/systemd/systemd-homed",
)


def _dockerfile_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _from_matches(path: Path) -> list[re.Match[str]]:
    matches = list(FROM_RE.finditer(_dockerfile_text(path)))
    assert matches, f"{path} must declare at least one FROM line"
    return matches


def _scope_digests_and_images() -> tuple[set[str | None], set[str]]:
    digests: set[str | None] = set()
    images: set[str] = set()
    for path in SCOPE_DOCKERFILES:
        for match in _from_matches(path):
            digests.add(match.group("digest"))
            images.add(match.group("image"))
    return digests, images


def test_scope_dockerfiles_share_one_pinned_trixie_base_digest() -> None:
    digests, images = _scope_digests_and_images()
    assert None not in digests
    assert len(digests) == 1, f"expected one shared base digest, found {digests}"
    assert images == {BASE_IMAGE}


@pytest.mark.parametrize(
    "dockerfile",
    SCOPE_DOCKERFILES,
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_scope_dockerfiles_do_not_enable_systemd_homed_runtime(
    dockerfile: Path,
) -> None:
    text = _dockerfile_text(dockerfile).lower()
    present = [marker for marker in FORBIDDEN_HOMED_RUNTIME_MARKERS if marker in text]
    assert present == [], (
        f"{dockerfile} introduces systemd-homed reachability and invalidates the "
        f"current exploitability HOLD: {present}"
    )


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
    silenced = [
        entry
        for entry in entries
        if CVE_ID in entry or any(package in entry for package in PACKAGES)
    ]
    assert silenced == [], f"{CVE_ID} must remain visible to Trivy: {silenced}"


def test_upstream_hold_evidence_documents_required_fields() -> None:
    assert EVIDENCE_FILE.is_file(), f"missing evidence file: {EVIDENCE_FILE}"
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    required = (
        CVE_ID,
        *ISSUE_REFS,
        *PACKAGES,
        INSTALLED_VERSION,
        VERDICT,
        RE_EVAL_DATE,
        "systemd-homed",
        "Debian Trixie",
        "no DSA",
        "Exploitability",
        "cdb_allocation",
        "cdb_db_writer",
        "cdb_execution",
        "cdb_market",
        "cdb_regime",
        "cdb_risk",
        "cdb_signal",
        "cdb_ws",
        "No alert dismissal",
        "Observed base digest (HOLD snapshot)",
        "Re-evaluation triggers",
        "EXTERNAL_LIVE_CHECK",
    )
    missing = [item for item in required if item not in text]
    assert missing == [], f"evidence file missing required markers: {missing}"


def test_evidence_observed_digest_matches_current_dockerfiles() -> None:
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    marker = OBSERVED_DIGEST_MARKER_RE.search(text)
    assert marker is not None, (
        "evidence must declare " "'Observed base digest (HOLD snapshot): `sha256:…`'"
    )
    observed = marker.group("digest")
    digests, _images = _scope_digests_and_images()
    assert digests == {observed}, (
        "HOLD evidence observed digest must match the shared Dockerfile pin; "
        f"evidence={observed}, dockerfiles={digests}"
    )


def test_evidence_rejects_fake_remediation_and_keeps_live_recheck_boundary() -> None:
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "Rejected" in text
    assert "no alert dismissal" in lowered
    assert VERDICT in text
    assert "EXTERNAL_LIVE_CHECK" in text
    assert "cannot detect debian fixedversion offline" in lowered
    assert "suite migration" in lowered
    assert "not an eternal required digest" in lowered


def test_evidence_utf8_is_clean() -> None:
    raw = EVIDENCE_FILE.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "evidence must be UTF-8 without BOM"
    text = raw.decode("utf-8")
    assert "\u00e2\u20ac\u201d" not in text, "evidence contains mojibake for an em dash"
    assert "\ufffd" not in text, "evidence contains Unicode replacement characters"
