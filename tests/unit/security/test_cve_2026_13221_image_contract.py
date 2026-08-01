"""CVE-2026-13221 HOLD contract for eight service images (#4106).

Protects the evidence-based UPSTREAM HOLD for Debian Trixie ``perl-base``:
shared base lineage, apt upgrade, no scanner silencing, and a machine-checkable
re-evaluation rule. The currently observed digest is consistency-checked
against the evidence snapshot — it is not an eternal required digest.

Static Dockerfile / evidence parsing only — no image build, no registry
access, no live Debian FixedVersion probe, no runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

CVE_ID = "CVE-2026-13221"
ISSUE_REF = "#4106"
PACKAGE = "perl-base"
INSTALLED_VERSION = "5.40.1-6"
UPSTREAM_FIXED_VERSION = "5.43.10"
VERDICT = "HOLD_UPSTREAM_NO_FIXED_VERSION"
RE_EVAL_DATE = "2026-08-15"
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
    / "4106_CVE-2026-13221_UPSTREAM_HOLD.md"
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


def _scope_digests_and_images() -> tuple[set[str | None], set[str]]:
    digests: set[str | None] = set()
    images: set[str] = set()
    for path in SCOPE_DOCKERFILES:
        for match in _from_matches(path):
            digests.add(match.group("digest"))
            images.add(match.group("image"))
    return digests, images


def test_scope_dockerfiles_share_one_pinned_base_digest() -> None:
    """Shared lineage is the root-cause premise; digests must be pinned+identical.

    Any future shared digest is allowed. This test does **not** require the
    historically vulnerable HOLD snapshot digest forever.
    """
    digests, images = _scope_digests_and_images()
    assert None not in digests, (
        "all eight service Dockerfiles must pin a sha256 digest "
        f"(found unpinned FROM among {digests})"
    )
    assert len(digests) == 1, (
        "all eight service Dockerfiles must share one base digest for the "
        f"shared OS-layer finding; found {digests}"
    )
    assert images == {BASE_IMAGE}


@pytest.mark.parametrize(
    "dockerfile",
    SCOPE_DOCKERFILES,
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_scope_dockerfiles_still_run_apt_upgrade(dockerfile: Path) -> None:
    text = _dockerfile_text(dockerfile)
    assert APT_UPGRADE_RE.search(text), (
        f"{dockerfile} must keep apt-get upgrade so suite-native security "
        "updates land automatically once Debian publishes them"
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
        "cdb_execution",
        "cdb_market",
        "cdb_regime",
        "cdb_risk",
        "cdb_signal",
        "cdb_ws",
        "UPSTREAM_NO_FIXED_VERSION",
        "ALREADY_REMEDIATED_RESCAN_PENDING",
        "No alert dismissal",
        "Observed base digest (HOLD snapshot)",
        "Re-evaluation triggers",
        "EXTERNAL_LIVE_CHECK",
    )
    missing = [item for item in required if item not in text]
    assert missing == [], f"evidence file missing required markers: {missing}"


def test_evidence_observed_digest_matches_current_dockerfiles() -> None:
    """Evidence snapshot digest must match current pins (consistency, not eternity).

    Updating Dockerfiles to a new shared digest requires updating the evidence
    observed-digest marker in the same change. A suite-native FixedVersion
    additionally requires flipping the HOLD verdict (live Debian check is
    EXTERNAL_LIVE_CHECK, not this static test).
    """
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    marker = OBSERVED_DIGEST_MARKER_RE.search(text)
    assert marker is not None, (
        "evidence must declare " "'Observed base digest (HOLD snapshot): `sha256:…`'"
    )
    observed = marker.group("digest")
    digests, _images = _scope_digests_and_images()
    assert digests == {observed}, (
        "HOLD evidence observed digest must match the shared Dockerfile pin; "
        f"evidence={observed}, dockerfiles={digests}. "
        "Update the evidence observed-digest marker together with Dockerfile pins."
    )


def test_evidence_rejects_eternal_digest_and_fake_remediation() -> None:
    text = EVIDENCE_FILE.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "Rejected" in text
    assert "no alert dismissal" in lowered
    assert VERDICT in text
    assert "Digest bump evidence" in text or "D1" in text
    assert "not an eternal required digest" in lowered
    assert "EXTERNAL_LIVE_CHECK" in text
    assert "cannot detect debian fixedversion offline" in lowered
    # Forbid claiming the observed digest is a permanent pin.
    assert "eternal required digest" in lowered
    assert "must always pin" not in lowered
    assert "Sollzustand Digest" not in text
