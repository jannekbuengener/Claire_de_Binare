"""Semantic freshness guard for repository status surfaces.

The guard validates *declared* live claims on the canonical status surfaces
(`README.md`, `CURRENT_STATUS.md`, `docs/runbooks/CONTROL_REGISTER.md`).
It is deliberately **not** an age or "last touched" comparison: a document may
be arbitrarily old and still pass as long as every live claim it makes is still
true. Conversely, a document edited today fails if it asserts a stale issue
state.

Marker grammar (HTML comments, invisible in rendered Markdown)::

    <!-- cdb:status-freshness header-date=YYYY-MM-DD -->
    <!-- cdb:live-claim type=main_sha value=<sha> -->
    <!-- cdb:live-claim type=issue_state issue=<n> state=open|closed|merged -->
    <!-- cdb:historical-as-of date=YYYY-MM-DD -->
    <!-- cdb:historical-end -->

Claim semantics:

``main_sha``
    The declared commit must exist and be reachable from ``origin/main``, and
    every surface declaring a main SHA must declare the same one. A moving
    ``main`` therefore does not invalidate a correct snapshot, but a
    fabricated, rewritten or diverging snapshot does.

``issue_state``
    The declared state must match the live GitHub state. Without a working
    ``gh`` CLI the claim is reported ``UNVERIFIED`` — never ``PASS``.

``header_date``
    The declared header date must be visible in the rendered text next to the
    marker and must not be older than the newest date used anywhere in the
    body. This is an internal-consistency check, not a freshness-by-age check.

Historical regions are exempt from live verification, but their marking is
validated: the ``date`` attribute is mandatory, must not be newer than the
header date, regions must be balanced, and a historical region must not assert
live state.

Usage::

    python -m tools.validate_status_freshness
    python -m tools.validate_status_freshness --strict
    python -m tools.validate_status_freshness --json

Exit codes:
    0 - no FAIL results (UNVERIFIED tolerated unless ``--strict``)
    1 - at least one FAIL result, or an UNVERIFIED result under ``--strict``

Issue: #4119
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Protocol, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SURFACES: tuple[str, ...] = (
    "README.md",
    "CURRENT_STATUS.md",
    "docs/runbooks/CONTROL_REGISTER.md",
)

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIED = "UNVERIFIED"

_MARKER_RE = re.compile(r"<!--\s*cdb:(?P<kind>[a-z-]+)(?P<attrs>[^>]*?)-->")
_ATTR_RE = re.compile(r"(?P<key>[a-z-]+)=(?P<value>[^\s]+)")
_ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")

# Prose patterns that constitute a live claim and therefore must be declared.
_PROSE_MAIN_SHA_RE = re.compile(r"origin/main[^\n]*?`(?P<sha>[0-9a-f]{7,40})`")
_PROSE_IN_DELIVERY_RE = re.compile(r"in delivery", re.IGNORECASE)
_PROSE_ISSUE_REF_RE = re.compile(r"#(?P<issue>\d{2,6})\b")

# How far from the marker the declared header date must be visible in prose.
_HEADER_ANCHOR_RADIUS = 5


REACHABLE = "reachable"
NOT_REACHABLE = "not_reachable"
UNKNOWN_OBJECT = "unknown_object"
GIT_UNAVAILABLE = "unavailable"


class GitResolver(Protocol):
    """Resolves git facts needed by the ``main_sha`` claim."""

    def reachability_from_main(self, sha: str) -> str:
        """One of REACHABLE, NOT_REACHABLE, UNKNOWN_OBJECT, GIT_UNAVAILABLE."""


class IssueStateResolver(Protocol):
    """Resolves the live GitHub state of an issue or pull request."""

    def state(self, number: int) -> str | None: ...


class SubprocessGitResolver:
    def __init__(self, root: Path, ref: str = "origin/main") -> None:
        self._root = root
        self._ref = ref

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                list(args),
                cwd=self._root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    def _resolve_main_sha(self) -> str | None:
        result = self._run(["git", "rev-parse", self._ref])
        if result is None or result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def reachability_from_main(self, sha: str) -> str:
        if self._resolve_main_sha() is None:
            return GIT_UNAVAILABLE
        exists = self._run(["git", "cat-file", "-e", f"{sha}^{{commit}}"])
        if exists is None:
            return GIT_UNAVAILABLE
        if exists.returncode != 0:
            return UNKNOWN_OBJECT
        result = self._run(["git", "merge-base", "--is-ancestor", sha, self._ref])
        if result is None:
            return GIT_UNAVAILABLE
        if result.returncode == 0:
            return REACHABLE
        if result.returncode == 1:
            return NOT_REACHABLE
        return GIT_UNAVAILABLE


class GhIssueStateResolver:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._cache: dict[int, str | None] = {}

    def state(self, number: int) -> str | None:
        if number in self._cache:
            return self._cache[number]
        resolved = self._query(number)
        self._cache[number] = resolved
        return resolved

    def _query(self, number: int) -> str | None:
        try:
            result = subprocess.run(
                ["gh", "issue", "view", str(number), "--json", "state"],
                cwd=self._root,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        state = payload.get("state")
        return str(state).lower() if state else None


@dataclass(frozen=True)
class Marker:
    kind: str
    attrs: dict[str, str]
    line: int


@dataclass(frozen=True)
class ClaimResult:
    surface: str
    line: int
    claim_type: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "line": self.line,
            "claim_type": self.claim_type,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class HistoricalRegion:
    start_line: int
    end_line: int
    as_of: date | None

    def contains(self, line: int) -> bool:
        return self.start_line <= line <= self.end_line


@dataclass
class SurfaceDocument:
    surface: str
    lines: list[str]
    markers: list[Marker]
    historical_regions: list[HistoricalRegion]
    structural_failures: list[ClaimResult]

    def in_historical_region(self, line: int) -> bool:
        return any(region.contains(line) for region in self.historical_regions)


def _parse_attrs(raw: str) -> dict[str, str]:
    return {m.group("key"): m.group("value") for m in _ATTR_RE.finditer(raw)}


def _parse_iso_date(raw: str) -> date | None:
    match = _ISO_DATE_RE.fullmatch(raw.strip())
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def parse_surface(surface: str, content: str) -> SurfaceDocument:
    lines = content.splitlines()
    markers: list[Marker] = []
    for index, line in enumerate(lines, start=1):
        for match in _MARKER_RE.finditer(line):
            markers.append(
                Marker(
                    kind=match.group("kind"),
                    attrs=_parse_attrs(match.group("attrs")),
                    line=index,
                )
            )

    regions: list[HistoricalRegion] = []
    failures: list[ClaimResult] = []
    open_marker: Marker | None = None

    for marker in markers:
        if marker.kind == "historical-as-of":
            if open_marker is not None:
                failures.append(
                    ClaimResult(
                        surface,
                        marker.line,
                        "historical_marking",
                        FAIL,
                        f"nested historical region; previous region opened at line {open_marker.line}",
                    )
                )
                continue
            open_marker = marker
        elif marker.kind == "historical-end":
            if open_marker is None:
                failures.append(
                    ClaimResult(
                        surface,
                        marker.line,
                        "historical_marking",
                        FAIL,
                        "historical-end without a matching historical-as-of",
                    )
                )
                continue
            regions.append(
                HistoricalRegion(
                    start_line=open_marker.line,
                    end_line=marker.line,
                    as_of=_parse_iso_date(open_marker.attrs.get("date", "")),
                )
            )
            open_marker = None

    if open_marker is not None:
        failures.append(
            ClaimResult(
                surface,
                open_marker.line,
                "historical_marking",
                FAIL,
                "historical region is never closed with historical-end",
            )
        )

    return SurfaceDocument(
        surface=surface,
        lines=lines,
        markers=markers,
        historical_regions=regions,
        structural_failures=failures,
    )


def _header_date(doc: SurfaceDocument) -> tuple[date | None, int]:
    for marker in doc.markers:
        if marker.kind != "status-freshness":
            continue
        raw = marker.attrs.get("header-date", "")
        return _parse_iso_date(raw), marker.line
    return None, 0


def _body_dates(doc: SurfaceDocument) -> list[tuple[date, int]]:
    found: list[tuple[date, int]] = []
    for index, line in enumerate(doc.lines, start=1):
        stripped = _MARKER_RE.sub("", line)
        for match in _ISO_DATE_RE.finditer(stripped):
            try:
                found.append(
                    (
                        date(
                            int(match.group(1)),
                            int(match.group(2)),
                            int(match.group(3)),
                        ),
                        index,
                    )
                )
            except ValueError:
                continue
    return found


def _check_header_date(doc: SurfaceDocument) -> list[ClaimResult]:
    declared, marker_line = _header_date(doc)
    if declared is None:
        if marker_line:
            return [
                ClaimResult(
                    doc.surface,
                    marker_line,
                    "header_date",
                    FAIL,
                    "status-freshness marker has a missing or malformed header-date",
                )
            ]
        return []

    results: list[ClaimResult] = []
    anchor_start = max(0, marker_line - 1 - _HEADER_ANCHOR_RADIUS)
    anchor_end = marker_line + _HEADER_ANCHOR_RADIUS
    anchor = "\n".join(doc.lines[anchor_start:anchor_end])
    if declared.isoformat() not in _MARKER_RE.sub("", anchor):
        results.append(
            ClaimResult(
                doc.surface,
                marker_line,
                "header_date",
                FAIL,
                f"declared header-date {declared.isoformat()} is not visible in the "
                f"document text within {_HEADER_ANCHOR_RADIUS} lines of the marker",
            )
        )

    body = _body_dates(doc)
    newest = max(body, default=None, key=lambda item: item[0])
    if newest is not None and newest[0] > declared:
        results.append(
            ClaimResult(
                doc.surface,
                newest[1],
                "header_date",
                FAIL,
                f"header-date {declared.isoformat()} is older than the newest body date "
                f"{newest[0].isoformat()} (line {newest[1]})",
            )
        )

    if not results:
        results.append(
            ClaimResult(
                doc.surface,
                marker_line,
                "header_date",
                PASS,
                f"header-date {declared.isoformat()} covers every date used in the body",
            )
        )
    return results


def _check_historical_marking(doc: SurfaceDocument) -> list[ClaimResult]:
    results = list(doc.structural_failures)
    declared_header, _ = _header_date(doc)

    for region in doc.historical_regions:
        if region.as_of is None:
            results.append(
                ClaimResult(
                    doc.surface,
                    region.start_line,
                    "historical_marking",
                    FAIL,
                    "historical-as-of marker has a missing or malformed date attribute",
                )
            )
            continue
        if declared_header is not None and region.as_of > declared_header:
            results.append(
                ClaimResult(
                    doc.surface,
                    region.start_line,
                    "historical_marking",
                    FAIL,
                    f"historical-as-of {region.as_of.isoformat()} is newer than the "
                    f"header-date {declared_header.isoformat()}",
                )
            )
            continue
        results.append(
            ClaimResult(
                doc.surface,
                region.start_line,
                "historical_marking",
                PASS,
                f"historical block marked as-of {region.as_of.isoformat()} and exempt "
                "from live verification",
            )
        )

    for marker in doc.markers:
        if marker.kind == "live-claim" and doc.in_historical_region(marker.line):
            results.append(
                ClaimResult(
                    doc.surface,
                    marker.line,
                    "historical_marking",
                    FAIL,
                    "live-claim declared inside a historical block; historical blocks "
                    "must not assert live state",
                )
            )

    return results


def _live_claim_markers(doc: SurfaceDocument) -> list[Marker]:
    return [
        marker
        for marker in doc.markers
        if marker.kind == "live-claim" and not doc.in_historical_region(marker.line)
    ]


def _check_main_sha(
    doc: SurfaceDocument, marker: Marker, git: GitResolver
) -> ClaimResult:
    value = marker.attrs.get("value", "").strip().lower()
    if not _SHA_RE.fullmatch(value):
        return ClaimResult(
            doc.surface,
            marker.line,
            "main_sha",
            FAIL,
            f"main_sha claim has a missing or malformed value: {value!r}",
        )

    verdict = git.reachability_from_main(value)
    if verdict == GIT_UNAVAILABLE:
        return ClaimResult(
            doc.surface,
            marker.line,
            "main_sha",
            UNVERIFIED,
            f"origin/main could not be resolved; claimed SHA {value} not verified",
        )
    if verdict == UNKNOWN_OBJECT:
        return ClaimResult(
            doc.surface,
            marker.line,
            "main_sha",
            FAIL,
            f"claimed main SHA {value} does not exist in this repository",
        )
    if verdict == NOT_REACHABLE:
        return ClaimResult(
            doc.surface,
            marker.line,
            "main_sha",
            FAIL,
            f"claimed main SHA {value} is not reachable from origin/main",
        )
    return ClaimResult(
        doc.surface,
        marker.line,
        "main_sha",
        PASS,
        f"claimed main SHA {value} is reachable from origin/main",
    )


def _check_issue_state(
    doc: SurfaceDocument, marker: Marker, issues: IssueStateResolver
) -> ClaimResult:
    raw_issue = marker.attrs.get("issue", "")
    declared = marker.attrs.get("state", "").strip().lower()
    if not raw_issue.isdigit() or not declared:
        return ClaimResult(
            doc.surface,
            marker.line,
            "issue_state",
            FAIL,
            "issue_state claim needs a numeric issue= and a non-empty state=",
        )

    number = int(raw_issue)
    actual = issues.state(number)
    if actual is None:
        return ClaimResult(
            doc.surface,
            marker.line,
            "issue_state",
            UNVERIFIED,
            f"GitHub state for #{number} is unavailable; declared {declared} not verified",
        )
    if actual != declared:
        return ClaimResult(
            doc.surface,
            marker.line,
            "issue_state",
            FAIL,
            f"#{number} is declared {declared} but GitHub reports {actual}",
        )
    return ClaimResult(
        doc.surface,
        marker.line,
        "issue_state",
        PASS,
        f"#{number} is {actual} on GitHub as declared",
    )


def _check_undeclared_prose_claims(doc: SurfaceDocument) -> list[ClaimResult]:
    """Reject live claims written in prose without a machine-checkable marker."""
    results: list[ClaimResult] = []
    declared_shas = {
        marker.attrs.get("value", "").strip().lower()
        for marker in _live_claim_markers(doc)
        if marker.attrs.get("type") == "main_sha"
    }
    declared_issues = {
        marker.attrs.get("issue", "")
        for marker in _live_claim_markers(doc)
        if marker.attrs.get("type") == "issue_state"
    }

    for index, line in enumerate(doc.lines, start=1):
        if doc.in_historical_region(index):
            continue

        for match in _PROSE_MAIN_SHA_RE.finditer(line):
            sha = match.group("sha").lower()
            if not any(
                sha.startswith(declared) or declared.startswith(sha)
                for declared in declared_shas
                if declared
            ):
                results.append(
                    ClaimResult(
                        doc.surface,
                        index,
                        "main_sha",
                        FAIL,
                        f"prose asserts origin/main at {sha} without a matching "
                        "cdb:live-claim type=main_sha marker",
                    )
                )

        if _PROSE_IN_DELIVERY_RE.search(line):
            referenced = {m.group("issue") for m in _PROSE_ISSUE_REF_RE.finditer(line)}
            missing = sorted(referenced - declared_issues)
            if not referenced:
                results.append(
                    ClaimResult(
                        doc.surface,
                        index,
                        "issue_state",
                        FAIL,
                        "prose claims 'in delivery' without an issue reference to verify",
                    )
                )
            elif missing:
                results.append(
                    ClaimResult(
                        doc.surface,
                        index,
                        "issue_state",
                        FAIL,
                        "prose claims 'in delivery' for "
                        + ", ".join(f"#{n}" for n in missing)
                        + " without a matching cdb:live-claim type=issue_state marker",
                    )
                )

    return results


def _check_cross_surface_main_sha(
    docs: Iterable[SurfaceDocument],
) -> list[ClaimResult]:
    declared: list[tuple[str, int, str]] = []
    for doc in docs:
        for marker in _live_claim_markers(doc):
            if marker.attrs.get("type") != "main_sha":
                continue
            value = marker.attrs.get("value", "").strip().lower()
            if value:
                declared.append((doc.surface, marker.line, value))

    if len(declared) < 2:
        return []

    reference = declared[0][2]
    results: list[ClaimResult] = []
    for surface, line, value in declared[1:]:
        if not (value.startswith(reference) or reference.startswith(value)):
            results.append(
                ClaimResult(
                    surface,
                    line,
                    "main_sha",
                    FAIL,
                    f"declares main SHA {value} while {declared[0][0]} declares "
                    f"{reference}; status surfaces must agree on one confirmed main state",
                )
            )
    if not results:
        results.append(
            ClaimResult(
                declared[0][0],
                declared[0][1],
                "main_sha",
                PASS,
                f"all {len(declared)} surfaces declare the same main state {reference}",
            )
        )
    return results


def validate_documents(
    docs: Sequence[SurfaceDocument],
    git: GitResolver,
    issues: IssueStateResolver,
) -> list[ClaimResult]:
    results: list[ClaimResult] = []
    for doc in docs:
        results.extend(_check_historical_marking(doc))
        results.extend(_check_header_date(doc))
        results.extend(_check_undeclared_prose_claims(doc))
        for marker in _live_claim_markers(doc):
            claim_type = marker.attrs.get("type", "")
            if claim_type == "main_sha":
                results.append(_check_main_sha(doc, marker, git))
            elif claim_type == "issue_state":
                results.append(_check_issue_state(doc, marker, issues))
            else:
                results.append(
                    ClaimResult(
                        doc.surface,
                        marker.line,
                        claim_type or "unknown",
                        FAIL,
                        f"unsupported live-claim type: {claim_type!r}",
                    )
                )
    results.extend(_check_cross_surface_main_sha(docs))
    return results


def load_documents(
    root: Path, surfaces: Sequence[str]
) -> tuple[list[SurfaceDocument], list[ClaimResult]]:
    docs: list[SurfaceDocument] = []
    errors: list[ClaimResult] = []
    for surface in surfaces:
        path = root / surface
        if not path.is_file():
            errors.append(
                ClaimResult(
                    surface, 0, "surface", FAIL, "registered surface is missing"
                )
            )
            continue
        docs.append(
            parse_surface(surface, path.read_text(encoding="utf-8", errors="replace"))
        )
    return docs, errors


def validate_all(
    root: Path | None = None,
    surfaces: Sequence[str] | None = None,
    git: GitResolver | None = None,
    issues: IssueStateResolver | None = None,
) -> list[ClaimResult]:
    r = root or REPO_ROOT
    docs, errors = load_documents(r, surfaces or DEFAULT_SURFACES)
    results = validate_documents(
        docs,
        git or SubprocessGitResolver(r),
        issues or GhIssueStateResolver(r),
    )
    return errors + results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate declared live claims on status surfaces (#4119)."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat UNVERIFIED claims as failures (requires git and gh access)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print machine-readable results",
    )
    parser.add_argument(
        "--surface",
        action="append",
        dest="surfaces",
        help="Restrict validation to the given surface (repeatable)",
    )
    args = parser.parse_args(argv)

    results = validate_all(REPO_ROOT, args.surfaces or DEFAULT_SURFACES)
    failures = [r for r in results if r.status == FAIL]
    unverified = [r for r in results if r.status == UNVERIFIED]

    if args.as_json:
        print(
            json.dumps(
                {
                    "results": [r.as_dict() for r in results],
                    "counts": {
                        PASS: len(results) - len(failures) - len(unverified),
                        FAIL: len(failures),
                        UNVERIFIED: len(unverified),
                    },
                    "strict": args.strict,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for result in results:
            stream = sys.stderr if result.status != PASS else sys.stdout
            print(
                f"{result.status}: {result.surface}:{result.line} "
                f"[{result.claim_type}] {result.detail}",
                file=stream,
            )

    if failures:
        print(
            f"STATUS FRESHNESS VALIDATION FAILED ({len(failures)} failing claim(s))",
            file=sys.stderr,
        )
        return 1
    if unverified and args.strict:
        print(
            f"STATUS FRESHNESS UNVERIFIED under --strict ({len(unverified)} claim(s))",
            file=sys.stderr,
        )
        return 1
    if unverified:
        print(
            f"OK: no failing live claims ({len(unverified)} UNVERIFIED, not counted as PASS)"
        )
        return 0
    print("OK: all declared live claims on status surfaces verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
