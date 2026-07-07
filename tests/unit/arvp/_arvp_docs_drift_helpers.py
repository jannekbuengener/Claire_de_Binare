"""Shared helpers for ARVP docs/evidence drift detection (#3825)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "arvp" / "docs_drift"

ARVP_FLOW_MD = (
    REPO_ROOT
    / "docs"
    / "onboarding"
    / "core-eventflows"
    / "arvp_replay_validation_flow.md"
)
ARVP_ROADMAP = REPO_ROOT / "docs" / "roadmaps" / "ARVP_TO_LIVE_GO_ROADMAP_2026-06.md"
LR050_ARVP_MAPPING = (
    REPO_ROOT
    / "docs"
    / "live-readiness"
    / "LR-050-EVIDENCE-HARVESTER-ARVP-MAPPING.md"
)
P0_CONTRACT_DOC = REPO_ROOT / "knowledge" / "testing" / "ARVP_P0_CONTRACT_TESTS.md"
P1_CONTRACT_DOC = REPO_ROOT / "knowledge" / "testing" / "ARVP_P1_CONTRACT_TESTS.md"
P2_TEST_MAP_JSON = (
    REPO_ROOT
    / ".github"
    / "control-plane"
    / "generated"
    / "agent-arvp-test-map.json"
)

P0_CONTRACT_TEST_PATHS: tuple[str, ...] = (
    "tests/unit/arvp/test_arvp_runtime_event_chain_contract.py",
    "tests/unit/arvp/test_arvp_calibration_gate_regression_contract.py",
    "tests/unit/arvp/test_arvp_campaign_supervisor_state_machine_contract.py",
)

P1_CONTRACT_TEST_PATHS: tuple[str, ...] = (
    "tests/unit/arvp/test_arvp_scenario_pack_matrix_contract.py",
    "tests/unit/arvp/test_arvp_window_qualification_contract.py",
    "tests/unit/arvp/test_arvp_evidence_harvester_mapping_contract.py",
    "tests/unit/arvp/test_arvp_runtime_negative_controls_contract.py",
)

DRIFT_LIMITATIONS: tuple[str, ...] = (
    "Drift detection is fixture-backed and read-only; no automatic doc correction.",
    "ARVP flow docs are onboarding orientation, not authoritative runtime truth.",
    "Roadmap and evidence scans sample active surfaces; not exhaustive.",
    "No live GitHub or SurrealDB dependency in standard CI.",
    "Issue open/closed mismatches are surfaced as findings, not auto-closed.",
)

FORBIDDEN_EVIDENCE_CLAIMS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bLIVE-GO\b", re.I),
    re.compile(r"\bapproved for live trading\b", re.I),
    re.compile(r"\bready for live capital\b", re.I),
    re.compile(r"\bechtgeld.go\b", re.I),
)


@dataclass(frozen=True)
class ArvpDocsDriftFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class ArvpDocsDriftScan:
    missing_contract_tests: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[ArvpDocsDriftFinding, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ArvpDocsDriftFixtureScore:
    has_roadmap_repo_drift: bool
    has_issue_status_mismatch: bool
    has_stale_evidence_ref: bool
    has_evidence_mismatch: bool
    has_missing_paths: bool
    forbidden_claims: tuple[str, ...]
    missing_paths: tuple[str, ...]
    limitations: tuple[str, ...]


def scan_arvp_docs_drift() -> ArvpDocsDriftScan:
    findings: list[ArvpDocsDriftFinding] = []
    missing_contract_tests: list[str] = []

    flow_text = ARVP_FLOW_MD.read_text(encoding="utf-8").lower()
    if "not authoritative" not in flow_text and "docs-only" not in flow_text:
        findings.append(
            ArvpDocsDriftFinding(
                kind="arvp_flow_missing_disclaimer",
                detail="arvp_replay_validation_flow.md must state docs-only / not authoritative",
            )
        )

    for rel in P0_CONTRACT_TEST_PATHS + P1_CONTRACT_TEST_PATHS:
        if not (REPO_ROOT / rel).is_file():
            missing_contract_tests.append(rel)
            findings.append(
                ArvpDocsDriftFinding(kind="contract_test_missing", detail=rel)
            )

    if P1_CONTRACT_DOC.is_file():
        p1_text = P1_CONTRACT_DOC.read_text(encoding="utf-8")
        for rel in P1_CONTRACT_TEST_PATHS:
            if rel not in p1_text:
                findings.append(
                    ArvpDocsDriftFinding(
                        kind="p1_doc_contract_test_drift",
                        detail=f"P1 contract doc missing reference to {rel}",
                    )
                )
    else:
        findings.append(
            ArvpDocsDriftFinding(
                kind="p1_contract_doc_missing",
                detail=str(P1_CONTRACT_DOC.relative_to(REPO_ROOT)),
            )
        )

    if P0_CONTRACT_DOC.is_file():
        p0_text = P0_CONTRACT_DOC.read_text(encoding="utf-8")
        for rel in P0_CONTRACT_TEST_PATHS:
            if rel not in p0_text:
                findings.append(
                    ArvpDocsDriftFinding(
                        kind="p0_doc_contract_test_drift",
                        detail=f"P0 contract doc missing reference to {rel}",
                    )
                )
    else:
        findings.append(
            ArvpDocsDriftFinding(
                kind="p0_contract_doc_missing",
                detail=str(P0_CONTRACT_DOC.relative_to(REPO_ROOT)),
            )
        )

    roadmap_text = ARVP_ROADMAP.read_text(encoding="utf-8")
    if "NO-GO" not in roadmap_text:
        findings.append(
            ArvpDocsDriftFinding(
                kind="arvp_roadmap_lr_drift",
                detail="ARVP roadmap must contain NO-GO live-readiness posture",
            )
        )

    lr_mapping_text = LR050_ARVP_MAPPING.read_text(encoding="utf-8")
    if "NO-GO" not in lr_mapping_text:
        findings.append(
            ArvpDocsDriftFinding(
                kind="lr050_mapping_lr_drift",
                detail="LR-050 ARVP mapping must contain NO-GO verdict",
            )
        )

    if not P2_TEST_MAP_JSON.is_file():
        findings.append(
            ArvpDocsDriftFinding(
                kind="arvp_test_map_missing",
                detail=str(P2_TEST_MAP_JSON.relative_to(REPO_ROOT)),
            )
        )
    else:
        payload = json.loads(P2_TEST_MAP_JSON.read_text(encoding="utf-8"))
        if payload.get("coverage") != "partial":
            findings.append(
                ArvpDocsDriftFinding(
                    kind="arvp_test_map_coverage_drift",
                    detail="agent-arvp-test-map.json must declare partial coverage",
                )
            )

    evidence_claims = scan_arvp_evidence_docs_for_forbidden_claims()
    for claim in evidence_claims:
        findings.append(
            ArvpDocsDriftFinding(kind="evidence_forbidden_claim", detail=claim)
        )

    return ArvpDocsDriftScan(
        missing_contract_tests=tuple(missing_contract_tests),
        limitations=DRIFT_LIMITATIONS,
        findings=tuple(findings),
    )


def scan_arvp_evidence_docs_for_forbidden_claims(
    evidence_dir: Path | None = None,
) -> tuple[str, ...]:
    root = evidence_dir or (REPO_ROOT / "docs" / "evidence")
    if not root.is_dir():
        return ()
    hits: list[str] = []
    for path in sorted(root.glob("arvp*.md")):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EVIDENCE_CLAIMS:
            if pattern.search(text):
                if "NO-GO" in text or "no live" in text.lower():
                    continue
                hits.append(f"{path.name}: forbidden claim {pattern.pattern!r}")
    return tuple(hits)


def score_arvp_docs_drift_fixture(fixture: dict[str, Any]) -> ArvpDocsDriftFixtureScore:
    limitations = tuple(fixture.get("limitations") or DRIFT_LIMITATIONS)

    roadmap_claim = str(fixture.get("roadmap_status_claim") or "")
    repo_status = str(fixture.get("repo_test_status") or "")
    has_roadmap_repo_drift = bool(
        roadmap_claim and repo_status and roadmap_claim != repo_status
    )

    ledger_records = fixture.get("issue_status_ledger") or []
    live_records = fixture.get("issue_status_live") or []
    ledger_by_id = {item["issue_id"]: item["status"] for item in ledger_records}
    live_by_id = {item["issue_id"]: item["status"] for item in live_records}
    has_issue_status_mismatch = any(
        ledger_by_id.get(issue_id) != live_by_id.get(issue_id)
        for issue_id in set(ledger_by_id) | set(live_by_id)
    )

    stale_refs = tuple(fixture.get("stale_evidence_refs") or ())
    repo_existing_refs = set(fixture.get("repo_existing_evidence_refs") or ())
    has_stale_evidence_ref = any(ref not in repo_existing_refs for ref in stale_refs)

    evidence_text = str(fixture.get("evidence_doc_text") or "")
    forbidden: list[str] = []
    for pattern in FORBIDDEN_EVIDENCE_CLAIMS:
        if pattern.search(evidence_text):
            if "NO-GO" not in evidence_text and "no live" not in evidence_text.lower():
                forbidden.append(pattern.pattern)

    declared_paths = tuple(fixture.get("declared_paths") or ())
    repo_paths = set(fixture.get("repo_existing_paths") or ())
    missing_paths = tuple(path for path in declared_paths if path not in repo_paths)

    return ArvpDocsDriftFixtureScore(
        has_roadmap_repo_drift=has_roadmap_repo_drift,
        has_issue_status_mismatch=has_issue_status_mismatch,
        has_stale_evidence_ref=has_stale_evidence_ref,
        has_evidence_mismatch=bool(forbidden),
        has_missing_paths=bool(missing_paths),
        forbidden_claims=tuple(forbidden),
        missing_paths=missing_paths,
        limitations=limitations,
    )


def load_drift_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))
