"""Ensure p5_canary_readiness.yaml references are real, consistent, and honest."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "governance" / "p5_canary_readiness.yaml"

# The generic audit-status document that is NOT control-specific evidence.
AUDIT_STATUS_STEM = "LR-AUDIT-STATUS"


def _load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _collect_referenced_paths() -> list[str]:
    """Extract all referenced file paths via regex for path-existence check."""
    text = POLICY_PATH.read_text(encoding="utf-8")
    paths: list[str] = []

    checklist = re.search(r"^checklist_document:\s*(.+)$", text, re.MULTILINE)
    if checklist:
        paths.append(checklist.group(1).strip())

    paths.extend(re.findall(r"^\s*evidence_path:\s*(.+)$", text, re.MULTILINE))
    paths.extend(re.findall(r"^\s*verification_script:\s*(.+)$", text, re.MULTILINE))

    artifacts_match = re.search(
        r"^required_artifacts:\n(?P<body>(?:\s+- .+\n)+)",
        text,
        re.MULTILINE,
    )
    if artifacts_match:
        paths.extend(
            re.findall(r"^\s+-\s+(.+)$", artifacts_match.group("body"), re.MULTILINE)
        )

    return [path.strip() for path in paths]


# --- Path existence (original test, kept) ---


def test_p5_canary_readiness_references_existing_paths() -> None:
    missing = [
        path for path in _collect_referenced_paths() if not (REPO_ROOT / path).exists()
    ]
    assert missing == [], f"Referenced paths not found in repo: {missing}"


# --- Every control must have an explicit status field ---


def test_every_control_has_explicit_status() -> None:
    """Controls without an explicit status field look implicitly green."""
    policy = _load_policy()
    missing_status = [
        ctrl["id"] for ctrl in policy["required_controls"] if "status" not in ctrl
    ]
    assert (
        missing_status == []
    ), f"Controls without explicit status field: {missing_status}"


# --- OPEN controls must have an evidence_note ---


def test_open_controls_have_evidence_note() -> None:
    """OPEN controls pointing to a sammelstatus doc must carry an evidence_note
    explaining why the reference is a tracking placeholder, not real evidence."""
    policy = _load_policy()
    missing_note = [
        ctrl["id"]
        for ctrl in policy["required_controls"]
        if ctrl.get("status") == "OPEN" and not ctrl.get("evidence_note")
    ]
    assert missing_note == [], f"OPEN controls without evidence_note: {missing_note}"


# --- Non-OPEN hard-gate controls should have control-specific evidence ---


def test_non_open_hard_gates_have_specific_evidence() -> None:
    """Hard-gate controls that are IMPLEMENTED or PASS should not point to
    a generic sammelstatus document as their evidence_path."""
    policy = _load_policy()
    generic_evidence = []
    for ctrl in policy["required_controls"]:
        if ctrl.get("status") in ("OPEN", "PARTIAL"):
            continue
        if not ctrl.get("hard_gate"):
            continue
        evidence = ctrl.get("evidence_path", "")
        if AUDIT_STATUS_STEM in evidence:
            generic_evidence.append(ctrl["id"])
    assert generic_evidence == [], (
        f"IMPLEMENTED hard-gate controls using generic audit-status as evidence: "
        f"{generic_evidence}"
    )


# --- PARTIAL controls must explain what is missing ---


def test_partial_controls_have_evidence_note() -> None:
    """PARTIAL controls must carry an evidence_note explaining
    what remains before they can move to IMPLEMENTED."""
    policy = _load_policy()
    missing_note = [
        ctrl["id"]
        for ctrl in policy["required_controls"]
        if ctrl.get("status") == "PARTIAL" and not ctrl.get("evidence_note")
    ]
    assert missing_note == [], f"PARTIAL controls without evidence_note: {missing_note}"


# --- Required artifacts must be real files ---


def test_required_artifacts_are_files() -> None:
    policy = _load_policy()
    not_files = [
        path
        for path in policy.get("required_artifacts", [])
        if not (REPO_ROOT / path).is_file()
    ]
    assert not_files == [], f"Required artifacts not found as files: {not_files}"


# --- Verification scripts referenced by controls must exist ---


def test_verification_scripts_exist() -> None:
    policy = _load_policy()
    missing = []
    for ctrl in policy["required_controls"]:
        script = ctrl.get("verification_script")
        if script and not (REPO_ROOT / script).is_file():
            missing.append(f"{ctrl['id']}: {script}")
    assert missing == [], f"Verification scripts not found: {missing}"
