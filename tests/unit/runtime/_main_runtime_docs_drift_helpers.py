"""Shared helpers for main runtime docs/evidence drift detection (#3842)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "runtime_docs_drift"

EVENTFLOW_MMD = (
    REPO_ROOT
    / "docs"
    / "onboarding"
    / "core-eventflows"
    / "diagrams"
    / "core_runtime_eventflow.mmd"
)
EVENTFLOW_MD = (
    REPO_ROOT / "docs" / "onboarding" / "core-eventflows" / "core_runtime_eventflow.md"
)
MARKET_STATE_CONTRACT = (
    REPO_ROOT / "docs" / "governance" / "MARKET_STATE_CONTRACT_V1.md"
)
LR_AUDIT_STATUS = (
    REPO_ROOT / "docs" / "live-readiness" / "LR-AUDIT-STATUS-2026-03-05.md"
)
P1_CONTRACT_DOC = (
    REPO_ROOT / "knowledge" / "testing" / "MAIN_RUNTIME_P1_CONTRACT_TESTS.md"
)

EVENTFLOW_SERVICE_PATTERN = re.compile(r"cdb_[a-z_]+")

# Repo-backed locations that differ from the default services/<short_name>/ layout.
SERVICE_LOCATION_ALIASES: dict[str, str] = {
    "cdb_paper_runner": "tools/paper_trading",
}

P1_CONTRACT_TEST_PATHS: tuple[str, ...] = (
    "tests/unit/utils/test_runtime_io_ledger_contract.py",
    "tests/unit/config/test_config_safety_gate_contract.py",
    "tests/unit/runtime/test_main_runtime_flow_contract.py",
    "tests/unit/runtime/test_health_metrics_contract.py",
    "tests/unit/validation/test_profitability_validation_regression_contract.py",
)

P0_CONTRACT_TEST_PATHS: tuple[str, ...] = (
    "tests/unit/market/test_market_candles_ingestion_contract.py",
    "tests/unit/regime/test_regime_service_contract.py",
    "tests/unit/regime/test_regime_id_semantics_contract.py",
    "tests/unit/signal/test_signal_core_contract.py",
    "tests/unit/signal/test_optimizer_contract.py",
    "tests/unit/signal/test_market_classifier_contract.py",
    "tests/unit/risk/test_decision_matrix_contract.py",
    "tests/unit/risk/test_reason_codes_contract.py",
    "tests/unit/risk/test_live_trading_gate_contract.py",
    "tests/unit/execution/test_execution_boundary_contract.py",
    "tests/unit/execution/test_state_machine_contract.py",
    "tests/unit/execution/test_paper_order_contract.py",
    "tests/unit/execution/test_init_services_contract.py",
)

DRIFT_LIMITATIONS: tuple[str, ...] = (
    "Drift detection is fixture-backed and read-only; no automatic doc correction.",
    "Eventflow docs are onboarding orientation, not authoritative runtime truth.",
    "Evidence doc scan samples active evidence surfaces; not exhaustive.",
    "No live GitHub or SurrealDB dependency in standard CI.",
    "Known stale patterns may remain visible as explicit findings.",
)

FORBIDDEN_EVIDENCE_CLAIMS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bLIVE-GO\b", re.I),
    re.compile(r"\bapproved for live trading\b", re.I),
    re.compile(r"\bready for live capital\b", re.I),
    re.compile(r"\bechtgeld.go\b", re.I),
)


@dataclass(frozen=True)
class RuntimeDocsDriftFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class RuntimeDocsDriftScan:
    eventflow_services: tuple[str, ...]
    missing_service_dirs: tuple[str, ...]
    missing_contract_tests: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[RuntimeDocsDriftFinding, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuntimeDocsDriftFixtureScore:
    has_eventflow_drift: bool
    has_evidence_mismatch: bool
    has_missing_paths: bool
    forbidden_claims: tuple[str, ...]
    missing_paths: tuple[str, ...]
    limitations: tuple[str, ...]


def extract_eventflow_services(mmd_text: str) -> set[str]:
    return set(EVENTFLOW_SERVICE_PATTERN.findall(mmd_text))


def resolve_service_path(service_name: str) -> Path:
    alias = SERVICE_LOCATION_ALIASES.get(service_name)
    if alias:
        return REPO_ROOT / alias
    short = service_name.removeprefix("cdb_")
    return REPO_ROOT / "services" / short


def service_dir_exists(service_name: str) -> bool:
    return resolve_service_path(service_name).is_dir()


def scan_main_runtime_docs_drift() -> RuntimeDocsDriftScan:
    findings: list[RuntimeDocsDriftFinding] = []
    mmd_text = EVENTFLOW_MMD.read_text(encoding="utf-8")
    eventflow_services = sorted(extract_eventflow_services(mmd_text))

    missing_dirs: list[str] = []
    for service in eventflow_services:
        if not service_dir_exists(service):
            missing_dirs.append(service)
            findings.append(
                RuntimeDocsDriftFinding(
                    kind="eventflow_service_dir_missing",
                    detail=f"{service} referenced in eventflow but services/ dir missing",
                )
            )

    eventflow_md_text = EVENTFLOW_MD.read_text(encoding="utf-8").lower()
    if "not authoritative" not in eventflow_md_text:
        findings.append(
            RuntimeDocsDriftFinding(
                kind="eventflow_missing_disclaimer",
                detail="core_runtime_eventflow.md must state docs-only / not authoritative",
            )
        )

    missing_contract_tests: list[str] = []
    for rel in P0_CONTRACT_TEST_PATHS + P1_CONTRACT_TEST_PATHS:
        if not (REPO_ROOT / rel).is_file():
            missing_contract_tests.append(rel)
            findings.append(
                RuntimeDocsDriftFinding(
                    kind="contract_test_missing",
                    detail=rel,
                )
            )

    if P1_CONTRACT_DOC.is_file():
        p1_text = P1_CONTRACT_DOC.read_text(encoding="utf-8")
        for rel in P1_CONTRACT_TEST_PATHS:
            if rel not in p1_text:
                findings.append(
                    RuntimeDocsDriftFinding(
                        kind="p1_doc_contract_test_drift",
                        detail=f"P1 contract doc missing reference to {rel}",
                    )
                )
    else:
        findings.append(
            RuntimeDocsDriftFinding(
                kind="p1_contract_doc_missing",
                detail=str(P1_CONTRACT_DOC.relative_to(REPO_ROOT)),
            )
        )

    market_contract_text = MARKET_STATE_CONTRACT.read_text(encoding="utf-8")
    if "cdb_risk" not in market_contract_text:
        findings.append(
            RuntimeDocsDriftFinding(
                kind="market_state_contract_drift",
                detail="MARKET_STATE_CONTRACT_V1 must reference cdb_risk consumer",
            )
        )
    if not (REPO_ROOT / "services" / "risk").is_dir():
        findings.append(
            RuntimeDocsDriftFinding(
                kind="market_state_consumer_missing",
                detail="services/risk missing for market_state consumer",
            )
        )

    lr_text = LR_AUDIT_STATUS.read_text(encoding="utf-8")
    if "NO-GO" not in lr_text:
        findings.append(
            RuntimeDocsDriftFinding(
                kind="config_safety_lr_drift",
                detail="LR audit status must contain NO-GO verdict",
            )
        )

    evidence_claims = scan_evidence_docs_for_forbidden_claims()
    for claim in evidence_claims:
        findings.append(
            RuntimeDocsDriftFinding(
                kind="evidence_forbidden_claim",
                detail=claim,
            )
        )

    return RuntimeDocsDriftScan(
        eventflow_services=tuple(eventflow_services),
        missing_service_dirs=tuple(missing_dirs),
        missing_contract_tests=tuple(missing_contract_tests),
        limitations=DRIFT_LIMITATIONS,
        findings=tuple(findings),
    )


def scan_evidence_docs_for_forbidden_claims(
    evidence_dir: Path | None = None,
) -> tuple[str, ...]:
    root = evidence_dir or (REPO_ROOT / "docs" / "evidence")
    if not root.is_dir():
        return ()
    hits: list[str] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EVIDENCE_CLAIMS:
            if pattern.search(text):
                # Allow if same file also states NO-GO (paired disclaimer)
                if "NO-GO" in text or "no live" in text.lower():
                    continue
                hits.append(f"{path.name}: forbidden claim {pattern.pattern!r}")
    return tuple(hits)


def score_runtime_docs_drift_fixture(fixture: dict[str, Any]) -> RuntimeDocsDriftFixtureScore:
    limitations = tuple(fixture.get("limitations") or DRIFT_LIMITATIONS)
    eventflow_services = set(fixture.get("eventflow_services") or ())
    repo_service_dirs = set(fixture.get("repo_service_dirs") or ())
    missing_service_dirs = sorted(eventflow_services - repo_service_dirs)

    evidence_text = str(fixture.get("evidence_doc_text") or "")
    forbidden: list[str] = []
    for pattern in FORBIDDEN_EVIDENCE_CLAIMS:
        if pattern.search(evidence_text):
            if "NO-GO" not in evidence_text and "no live" not in evidence_text.lower():
                forbidden.append(pattern.pattern)

    declared_paths = tuple(fixture.get("declared_paths") or ())
    repo_paths = set(fixture.get("repo_existing_paths") or ())
    missing_paths = tuple(path for path in declared_paths if path not in repo_paths)

    return RuntimeDocsDriftFixtureScore(
        has_eventflow_drift=bool(missing_service_dirs),
        has_evidence_mismatch=bool(forbidden),
        has_missing_paths=bool(missing_paths),
        forbidden_claims=tuple(forbidden),
        missing_paths=missing_paths,
        limitations=limitations,
    )


def load_drift_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))
