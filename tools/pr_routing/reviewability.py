"""Shared mirror-aware reviewability assessment for router and merge triggers.

Canon skill bodies under ``docs/skills/<skill>/SKILL.md`` and their expected
surface adapters count as one logical review unit only when path mapping and
content parity (via ``tools.validate_skill_surface_mirror``) both pass.
Unknown paths, drift, incomplete inventory, and API failures stay fail-closed
on physical file counting. Diff-line limits always use raw additions+deletions.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.validate_skill_surface_mirror import (
    EXCLUDED_ADAPTERS,
    SURFACES,
    header_issue,
    normalize_body,
)

ContentReader = Callable[[str], str | None]

CANON_SKILL_RE = re.compile(r"^docs/skills/(?P<skill>[^/]+)/SKILL\.md$")
_SURFACE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        surface,
        re.compile(
            "^"
            + re.escape(template.format(name="__SKILL__")).replace(
                re.escape("__SKILL__"), r"(?P<skill>[^/]+)"
            )
            + "$"
        ),
    )
    for surface, template in SURFACES.items()
)


@dataclass(frozen=True)
class MirrorGroup:
    skill: str
    members: tuple[str, ...]
    parity_status: str


@dataclass(frozen=True)
class ReviewabilityAssessment:
    physical_changed_files: int
    logical_review_units: int
    diff_lines: int
    recognized_mirror_groups: tuple[MirrorGroup, ...]
    unmapped_paths: tuple[str, ...]
    mirror_parity_status: str
    decision_basis: str
    reason_codes: tuple[str, ...]
    files_limit: int
    diff_lines_limit: int
    inventory_complete: bool
    exceeds_files_limit: bool
    exceeds_diff_limit: bool

    @property
    def exceeds_reviewability(self) -> bool:
        return self.exceeds_files_limit or self.exceeds_diff_limit

    def to_evidence(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["recognized_mirror_groups"] = [
            asdict(group) for group in self.recognized_mirror_groups
        ]
        return payload


def classify_skill_path(path: str) -> tuple[str, str] | None:
    """Return ``(skill, kind)`` where kind is ``canon`` or a surface name."""
    normalized = path.replace("\\", "/")
    match = CANON_SKILL_RE.fullmatch(normalized)
    if match:
        return match.group("skill"), "canon"
    for surface, pattern in _SURFACE_PATTERNS:
        surface_match = pattern.fullmatch(normalized)
        if surface_match:
            return surface_match.group("skill"), surface
    return None


def expected_skill_members(skill: str) -> tuple[str, ...]:
    """Canon plus non-excluded adapter paths for ``skill``."""
    members = [f"docs/skills/{skill}/SKILL.md"]
    exclusions = EXCLUDED_ADAPTERS.get(skill, {})
    for surface, template in SURFACES.items():
        if surface in exclusions:
            continue
        members.append(template.format(name=skill))
    return tuple(members)


def _parity_for_group(
    skill: str,
    members: Sequence[str],
    content_reader: ContentReader,
) -> tuple[str, tuple[str, ...]]:
    """Return ``(parity_status, reason_codes)`` for a complete member set."""
    contents: dict[str, str] = {}
    for path in members:
        text = content_reader(path)
        if text is None:
            return "blocked", ("MIRROR_CONTENT_UNAVAILABLE",)
        contents[path] = text

    canon_path = f"docs/skills/{skill}/SKILL.md"
    canon_body = normalize_body(contents[canon_path])
    reasons: list[str] = []
    for path in members:
        if path == canon_path:
            continue
        header_problem = header_issue(skill, contents[path])
        if header_problem is not None:
            reasons.append("MIRROR_HEADER_DRIFT")
            break
        if normalize_body(contents[path]) != canon_body:
            reasons.append("MIRROR_BODY_DRIFT")
            break
    if reasons:
        return "drift", tuple(reasons)
    return "pass", ()


def assess_reviewability(
    *,
    physical_changed_files: int,
    additions: int,
    deletions: int,
    files_limit: int,
    diff_lines_limit: int,
    changed_paths: Sequence[str] | None = None,
    inventory_complete: bool = True,
    content_reader: ContentReader | None = None,
    repo_root: Path | str | None = None,
) -> ReviewabilityAssessment:
    """Assess reviewability using logical skill-mirror units when evidence allows."""
    diff_lines = int(additions) + int(deletions)
    exceeds_diff = diff_lines >= int(diff_lines_limit)
    reason_codes: list[str] = []

    if not inventory_complete and physical_changed_files >= files_limit:
        reason_codes.extend(("INVENTORY_INCOMPLETE", "REVIEWABILITY_PHYSICAL_FALLBACK"))
        return ReviewabilityAssessment(
            physical_changed_files=physical_changed_files,
            logical_review_units=physical_changed_files,
            diff_lines=diff_lines,
            recognized_mirror_groups=(),
            unmapped_paths=(),
            mirror_parity_status="blocked",
            decision_basis="incomplete_inventory_physical_fallback",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            files_limit=files_limit,
            diff_lines_limit=diff_lines_limit,
            inventory_complete=False,
            exceeds_files_limit=True,
            exceeds_diff_limit=exceeds_diff,
        )

    # Fast path: under the physical threshold no mirror compression is required.
    if changed_paths is None and physical_changed_files < files_limit:
        return ReviewabilityAssessment(
            physical_changed_files=physical_changed_files,
            logical_review_units=physical_changed_files,
            diff_lines=diff_lines,
            recognized_mirror_groups=(),
            unmapped_paths=(),
            mirror_parity_status="not_evaluated",
            decision_basis="physical_under_limit",
            reason_codes=(),
            files_limit=files_limit,
            diff_lines_limit=diff_lines_limit,
            inventory_complete=inventory_complete,
            exceeds_files_limit=False,
            exceeds_diff_limit=exceeds_diff,
        )

    if changed_paths is None:
        reason_codes.extend(
            ("FILE_PATHS_UNAVAILABLE", "REVIEWABILITY_PHYSICAL_FALLBACK")
        )
        return ReviewabilityAssessment(
            physical_changed_files=physical_changed_files,
            logical_review_units=physical_changed_files,
            diff_lines=diff_lines,
            recognized_mirror_groups=(),
            unmapped_paths=(),
            mirror_parity_status="blocked",
            decision_basis="missing_paths_physical_fallback",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            files_limit=files_limit,
            diff_lines_limit=diff_lines_limit,
            inventory_complete=inventory_complete,
            exceeds_files_limit=physical_changed_files >= files_limit,
            exceeds_diff_limit=exceeds_diff,
        )

    paths = tuple(dict.fromkeys(p.replace("\\", "/") for p in changed_paths))
    if (
        inventory_complete
        and physical_changed_files
        and len(paths) != physical_changed_files
    ):
        reason_codes.append("PATH_COUNT_MISMATCH")
        inventory_complete = False
        if physical_changed_files >= files_limit:
            reason_codes.append("REVIEWABILITY_PHYSICAL_FALLBACK")
            return ReviewabilityAssessment(
                physical_changed_files=physical_changed_files,
                logical_review_units=physical_changed_files,
                diff_lines=diff_lines,
                recognized_mirror_groups=(),
                unmapped_paths=paths,
                mirror_parity_status="blocked",
                decision_basis="path_count_mismatch_physical_fallback",
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                files_limit=files_limit,
                diff_lines_limit=diff_lines_limit,
                inventory_complete=False,
                exceeds_files_limit=True,
                exceeds_diff_limit=exceeds_diff,
            )

    reader = content_reader
    if reader is None and repo_root is not None:
        root = Path(repo_root)

        def _read_from_repo(path: str) -> str | None:
            candidate = root / path
            try:
                return candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return None

        reader = _read_from_repo
    if reader is None:

        def _unavailable(_path: str) -> str | None:
            return None

        reader = _unavailable

    by_skill: dict[str, list[str]] = {}
    unmapped: list[str] = []
    for path in paths:
        classified = classify_skill_path(path)
        if classified is None:
            unmapped.append(path)
            continue
        skill, _kind = classified
        by_skill.setdefault(skill, []).append(path)

    logical_units = 0
    groups: list[MirrorGroup] = []
    parity_statuses: list[str] = []
    consumed: set[str] = set()

    for skill, present in sorted(by_skill.items()):
        expected = expected_skill_members(skill)
        present_set = set(present)
        expected_set = set(expected)
        canon_path = f"docs/skills/{skill}/SKILL.md"

        if canon_path not in present_set:
            logical_units += len(present)
            reason_codes.append("MIRROR_WITHOUT_CANON")
            parity_statuses.append("fail_closed")
            continue

        if not expected_set.issubset(present_set):
            # Canon or partial mirrors without the full expected adapter set.
            logical_units += len(present)
            reason_codes.append("CANON_WITHOUT_EXPECTED_MIRRORS")
            parity_statuses.append("fail_closed")
            continue

        extras = sorted(present_set - expected_set)
        parity_status, parity_reasons = _parity_for_group(skill, expected, reader)
        reason_codes.extend(parity_reasons)
        if parity_status != "pass":
            logical_units += len(present)
            parity_statuses.append(parity_status)
            continue

        groups.append(
            MirrorGroup(skill=skill, members=tuple(expected), parity_status="pass")
        )
        consumed.update(expected)
        logical_units += 1
        if extras:
            logical_units += len(extras)
            reason_codes.append("SKILL_EXTRA_PATHS_COUNTED")
        parity_statuses.append("pass")

    for path in unmapped:
        if path not in consumed:
            logical_units += 1

    if not parity_statuses:
        mirror_parity_status = "not_evaluated"
    elif all(status == "pass" for status in parity_statuses):
        mirror_parity_status = "pass"
    elif any(status == "drift" for status in parity_statuses):
        mirror_parity_status = "drift"
    elif any(status == "blocked" for status in parity_statuses):
        mirror_parity_status = "blocked"
    else:
        mirror_parity_status = "fail_closed"

    decision_basis = (
        "logical_mirror_units"
        if groups
        else (
            "physical_no_valid_mirror_groups" if by_skill else "physical_no_skill_paths"
        )
    )
    if groups:
        reason_codes.append("MIRROR_GROUPS_COLLAPSED")

    return ReviewabilityAssessment(
        physical_changed_files=(
            physical_changed_files if physical_changed_files else len(paths)
        ),
        logical_review_units=logical_units,
        diff_lines=diff_lines,
        recognized_mirror_groups=tuple(groups),
        unmapped_paths=tuple(unmapped),
        mirror_parity_status=mirror_parity_status,
        decision_basis=decision_basis,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        files_limit=files_limit,
        diff_lines_limit=diff_lines_limit,
        inventory_complete=inventory_complete,
        exceeds_files_limit=logical_units >= files_limit,
        exceeds_diff_limit=exceeds_diff,
    )


def repo_content_reader(repo_root: Path | str) -> ContentReader:
    root = Path(repo_root)

    def _read(path: str) -> str | None:
        try:
            return (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    return _read


def mapping_content_reader(contents: Mapping[str, str]) -> ContentReader:
    normalized = {key.replace("\\", "/"): value for key, value in contents.items()}

    def _read(path: str) -> str | None:
        return normalized.get(path.replace("\\", "/"))

    return _read
