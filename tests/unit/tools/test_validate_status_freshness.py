"""Targeted tests for the semantic status freshness guard (#4119).

The guard must fail on genuinely stale live claims, must accept correctly
marked historical blocks, and must accept an old-but-still-correct document.
A pure age or date comparison would violate all three expectations at once.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import validate_status_freshness as guard

REPO_ROOT = Path(__file__).resolve().parents[3]

CURRENT_SHA = "aaaaaaaabbbbbbbbccccccccdddddddd11111111"
UNKNOWN_SHA = "ffffffffeeeeeeeeddddddddcccccccc22222222"


class FakeGit:
    def __init__(
        self,
        reachable: set[str] | None = None,
        resolvable: bool = True,
        known: set[str] | None = None,
    ):
        self._reachable = reachable if reachable is not None else {CURRENT_SHA}
        self._known = known if known is not None else self._reachable
        self._resolvable = resolvable

    def reachability_from_main(self, sha: str) -> str:
        if not self._resolvable:
            return guard.GIT_UNAVAILABLE
        if not any(candidate.startswith(sha) for candidate in self._known):
            return guard.UNKNOWN_OBJECT
        if any(candidate.startswith(sha) for candidate in self._reachable):
            return guard.REACHABLE
        return guard.NOT_REACHABLE


class FakeIssues:
    def __init__(self, states: dict[int, str] | None = None):
        self._states = states or {}

    def state(self, number: int) -> str | None:
        return self._states.get(number)


def run(
    documents: dict[str, str],
    *,
    git: FakeGit | None = None,
    issues: FakeIssues | None = None,
) -> list[guard.ClaimResult]:
    docs = [guard.parse_surface(name, text) for name, text in documents.items()]
    return guard.validate_documents(docs, git or FakeGit(), issues or FakeIssues())


def statuses(results: list[guard.ClaimResult], claim_type: str) -> set[str]:
    return {r.status for r in results if r.claim_type == claim_type}


def failures(results: list[guard.ClaimResult]) -> list[guard.ClaimResult]:
    return [r for r in results if r.status == guard.FAIL]


CORRECT_DOC = f"""# Current Status

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:live-claim type=main_sha value={CURRENT_SHA[:8]} -->
Auf `origin/main` (`{CURRENT_SHA[:8]}`) steht der bestaetigte Stand.

<!-- cdb:live-claim type=issue_state issue=1445 state=open -->
Operatives Cockpit: #1445.

<!-- cdb:historical-as-of date=2026-07-12 -->
## Repo / Engineering Status (2026-07-12)

- #3995 (OPEN — nav/snapshot reconcile in delivery)
<!-- cdb:historical-end -->
"""


@pytest.mark.unit
def test_correct_document_passes_without_failures():
    results = run({"doc.md": CORRECT_DOC}, issues=FakeIssues({1445: "open"}))

    assert failures(results) == []
    assert statuses(results, "main_sha") == {guard.PASS}
    assert statuses(results, "issue_state") == {guard.PASS}
    assert statuses(results, "header_date") == {guard.PASS}


@pytest.mark.unit
def test_stale_issue_state_claim_fails():
    doc = CORRECT_DOC.replace("issue=1445 state=open", "issue=4005 state=open").replace(
        "#1445.", "#4005."
    )

    results = run({"doc.md": doc}, issues=FakeIssues({4005: "closed"}))

    detail = [r.detail for r in failures(results) if r.claim_type == "issue_state"]
    assert detail == ["#4005 is declared open but GitHub reports closed"]


@pytest.mark.unit
def test_main_sha_claim_not_reachable_from_main_fails():
    doc = CORRECT_DOC.replace(CURRENT_SHA[:8], UNKNOWN_SHA[:8])

    results = run(
        {"doc.md": doc},
        git=FakeGit(reachable={CURRENT_SHA}, known={CURRENT_SHA, UNKNOWN_SHA}),
        issues=FakeIssues({1445: "open"}),
    )

    assert any(
        r.claim_type == "main_sha" and "not reachable from origin/main" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_fabricated_main_sha_claim_fails_instead_of_unverified():
    doc = CORRECT_DOC.replace(CURRENT_SHA[:8], "deadbee")

    results = run({"doc.md": doc}, issues=FakeIssues({1445: "open"}))

    assert any(
        r.claim_type == "main_sha" and "does not exist in this repository" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_header_date_older_than_newest_body_date_fails():
    doc = """# Control Register

<!-- cdb:status-freshness header-date=2026-07-14 -->
**Letzte Aktualisierung:** 2026-07-14

- Workflow-Hygiene (2026-07-16): Bestand nachgezogen.
"""

    results = run({"doc.md": doc})

    assert any(
        r.claim_type == "header_date"
        and "older than the newest body date 2026-07-16" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_header_date_not_anchored_to_visible_text_fails():
    doc = """# Control Register

<!-- cdb:status-freshness header-date=2026-07-16 -->
**Letzte Aktualisierung:** 2026-07-14
"""

    results = run({"doc.md": doc})

    assert any(
        r.claim_type == "header_date"
        and "is not visible in the document text" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_marked_historical_block_is_exempt_from_live_verification():
    doc = f"""# Ledger

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:historical-as-of date=2026-07-12 -->
## Repo / Engineering Status (2026-07-12)

- Auf `origin/main` (`{UNKNOWN_SHA[:8]}`) stand damals der Cluster.
- #3995 OPEN — nav/snapshot reconcile in delivery.
<!-- cdb:historical-end -->
"""

    results = run({"doc.md": doc})

    assert failures(results) == []
    assert statuses(results, "historical_marking") == {guard.PASS}


@pytest.mark.unit
def test_old_but_still_correct_document_passes():
    doc = f"""# Legacy Status Surface

<!-- cdb:status-freshness header-date=2024-01-05 -->
**Last Updated**: 2024-01-05

<!-- cdb:live-claim type=main_sha value={CURRENT_SHA[:8]} -->
Bestaetigter Stand auf `origin/main` (`{CURRENT_SHA[:8]}`).

<!-- cdb:live-claim type=issue_state issue=1445 state=open -->
Cockpit #1445 bleibt offen.
"""

    results = run({"doc.md": doc}, issues=FakeIssues({1445: "open"}))

    assert failures(results) == []
    assert statuses(results, "header_date") == {guard.PASS}


@pytest.mark.unit
def test_unmarked_historical_block_is_treated_as_live_and_fails():
    doc = f"""# Ledger

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

## Repo / Engineering Status (2026-07-12)

- Auf `origin/main` (`{UNKNOWN_SHA[:8]}`) stand damals der Cluster.
"""

    results = run({"doc.md": doc})

    assert any(
        r.claim_type == "main_sha" and "without a matching cdb:live-claim" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_live_claim_inside_historical_block_fails():
    doc = f"""# Ledger

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:historical-as-of date=2026-07-12 -->
<!-- cdb:live-claim type=main_sha value={CURRENT_SHA[:8]} -->
<!-- cdb:historical-end -->
"""

    results = run({"doc.md": doc})

    assert any(
        r.claim_type == "historical_marking"
        and "must not assert live state" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_unclosed_historical_region_fails():
    doc = """# Ledger

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:historical-as-of date=2026-07-12 -->
- historischer Eintrag
"""

    results = run({"doc.md": doc})

    assert any("never closed" in r.detail for r in failures(results))


@pytest.mark.unit
def test_historical_marker_without_date_fails():
    doc = """# Ledger

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:historical-as-of -->
- historischer Eintrag
<!-- cdb:historical-end -->
"""

    results = run({"doc.md": doc})

    assert any(
        "missing or malformed date attribute" in r.detail for r in failures(results)
    )


@pytest.mark.unit
def test_historical_block_newer_than_header_date_fails():
    doc = """# Ledger

<!-- cdb:status-freshness header-date=2026-07-12 -->
**Last Updated**: 2026-07-12

<!-- cdb:historical-as-of date=2026-07-31 -->
- angeblich historischer Eintrag aus der Zukunft
<!-- cdb:historical-end -->
"""

    results = run({"doc.md": doc})

    assert any(
        r.claim_type == "historical_marking"
        and "is newer than the header-date" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_prose_in_delivery_without_declaration_fails():
    doc = """# Front Door

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

Community-Health-Reconcile: Issue #4005 (in delivery).
"""

    results = run({"doc.md": doc})

    assert any(
        r.claim_type == "issue_state" and "#4005" in r.detail for r in failures(results)
    )


@pytest.mark.unit
def test_prose_in_delivery_with_declaration_is_verified_against_github():
    doc = """# Front Door

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:live-claim type=issue_state issue=4005 state=open -->
Community-Health-Reconcile: Issue #4005 (in delivery).
"""

    results = run({"doc.md": doc}, issues=FakeIssues({4005: "closed"}))

    assert [r.detail for r in failures(results)] == [
        "#4005 is declared open but GitHub reports closed"
    ]


@pytest.mark.unit
def test_diverging_main_sha_between_surfaces_fails():
    readme = f"""# README

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:live-claim type=main_sha value={CURRENT_SHA[:8]} -->
Stand `origin/main` (`{CURRENT_SHA[:8]}`).
"""
    status = f"""# Status

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:live-claim type=main_sha value={UNKNOWN_SHA[:8]} -->
Stand `origin/main` (`{UNKNOWN_SHA[:8]}`).
"""

    results = run(
        {"README.md": readme, "CURRENT_STATUS.md": status},
        git=FakeGit(reachable={CURRENT_SHA, UNKNOWN_SHA}),
    )

    assert any(
        "status surfaces must agree on one confirmed main state" in r.detail
        for r in failures(results)
    )


@pytest.mark.unit
def test_github_unavailable_yields_unverified_not_pass():
    results = run({"doc.md": CORRECT_DOC}, issues=FakeIssues({}))

    assert statuses(results, "issue_state") == {guard.UNVERIFIED}
    assert failures(results) == []


@pytest.mark.unit
def test_git_unavailable_yields_unverified_not_pass():
    results = run(
        {"doc.md": CORRECT_DOC},
        git=FakeGit(resolvable=False),
        issues=FakeIssues({1445: "open"}),
    )

    assert statuses(results, "main_sha") == {guard.UNVERIFIED}
    assert failures(results) == []


@pytest.mark.unit
def test_unsupported_claim_type_fails():
    doc = """# Doc

<!-- cdb:status-freshness header-date=2026-07-31 -->
**Last Updated**: 2026-07-31

<!-- cdb:live-claim type=vibes value=good -->
"""

    results = run({"doc.md": doc})

    assert any("unsupported live-claim type" in r.detail for r in failures(results))


@pytest.mark.unit
def test_missing_surface_is_reported_as_failure(tmp_path: Path):
    results = guard.validate_all(
        tmp_path,
        surfaces=("does-not-exist.md",),
        git=FakeGit(),
        issues=FakeIssues(),
    )

    assert [r.detail for r in failures(results)] == ["registered surface is missing"]


@pytest.mark.unit
def test_repository_status_surfaces_have_no_failing_claims():
    """The real repository surfaces must be reconciled and marker-consistent."""
    results = guard.validate_all(
        REPO_ROOT,
        git=FakeGit(resolvable=False),
        issues=FakeIssues({}),
    )

    assert [f"{r.surface}:{r.line} {r.detail}" for r in failures(results)] == []
