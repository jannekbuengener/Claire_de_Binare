from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = [
    "AGENTS.md",
    "agents/AGENTS.md",
    "DEVELOPER_ONBOARDING.md",
    "README.md",
    "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "knowledge/governance/SERVICE_CATALOG.md",
    "docs/runbooks/legacy_service_drift.md",
    "tools/validate_mcp_config.py",
    "tests/smoke/test_mcp_runtime.py",
    "core/config/trading_mode.py",
]

SCENARIO_TERMS = [
    "ONBOARDING-SCENARIO-001",
    "Fresh Agent Safe-Work Drill",
    "Post-Audit Hardening Addendum",
    "Jannek-Ops-GO",
    "Infra-Mutation-Gate",
    "repo_fallback_reason",
    "insufficient_evidence",
    "missing_record",
    "legacy_service_drift",
    "mockx-valkey",
    "cdb_market_eth",
    "lr030_soak_monitor",
    "lr040_soak_monitor",
    "/onboarding",
    "Definition ist nicht Ausführung",
]

SAFETY_TERMS = [
    "LR remains NO-GO",
    "LR bleibt NO-GO",
    "LR-Status: NO-GO",
]

SAFETY_MEANINGS = [
    "trade-capable",
    "Echtgeld-Go",
    "Live-Go",
]

DRIFT_TERMS = [
    "cdb_node_exporter",
    "cdb_market_eth",
    "lr030_soak_monitor",
    "lr040_soak_monitor",
    "mockx-valkey",
    "absent",
    "Jannek-Ops-GO",
]

ACTIVE_CANON_GORDON_PATHS = [
    "AGENTS.md",
    "agents/AGENTS.md",
    "docs/runbooks/legacy_service_drift.md",
    "knowledge/governance/SERVICE_CATALOG.md",
    "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md",
    "DEVELOPER_ONBOARDING.md",
    "README.md",
]

GORDON_ALLOWED_CONTEXTS = [
    "historical",
    "archive",
    "old",
    "alte",
    "ersetzt",
    "replaced",
    "negative case",
]


def read_text(relative_path: str) -> str:
    full_path = REPO_ROOT / relative_path
    return full_path.read_text(encoding="utf-8")


def assert_terms_in_text(text: str, terms: list[str], source_label: str):
    missing = [t for t in terms if t not in text]
    if missing:
        pytest.fail(
            f"{source_label}: missing required term(s): {missing}"
        )


def assert_terms_absent(text: str, terms: list[str], source_label: str):
    found = [t for t in terms if t in text]
    if found:
        pytest.fail(
            f"{source_label}: forbidden term(s) present: {found}"
        )


class TestOnboardingScenarioPaths:
    def test_required_paths_exist(self):
        for p in REQUIRED_PATHS:
            full = REPO_ROOT / p
            assert full.exists(), f"Required path missing: {p}"

    def test_no_archive_paths_in_required(self):
        for p in REQUIRED_PATHS:
            assert "docs/archive" not in p, (
                f"Archive path found in required paths: {p}"
            )


class TestOnboardingScenarioTerms:
    SCENARIO_DOC = (
        "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md"
    )

    def test_scenario_required_terms(self):
        text = read_text(self.SCENARIO_DOC)
        assert_terms_in_text(text, SCENARIO_TERMS, self.SCENARIO_DOC)

    def test_scenario_contains_safety_terms(self):
        text = read_text(self.SCENARIO_DOC)
        acceptable = SAFETY_TERMS
        found = [t for t in acceptable if t in text]
        if not found:
            pytest.fail(
                f"{self.SCENARIO_DOC}: no acceptable LR NO-GO pattern found. "
                f"Expected one of: {acceptable}"
            )

    def test_scenario_separates_trade_capable_from_live_go(self):
        text = read_text(self.SCENARIO_DOC)
        assert "trade-capable" in text
        for meaning in SAFETY_MEANINGS:
            assert meaning in text, (
                f"{self.SCENARIO_DOC}: missing safety separation term '{meaning}'"
            )

    def test_scenario_no_secrets_output(self):
        text = read_text(self.SCENARIO_DOC)
        secret_patterns = [
            "api_key",
            "api_secret",
            "password",
            "SECRETS_PATH",
        ]
        found = [p for p in secret_patterns if p in text.lower()]
        if found:
            pytest.fail(
                f"{self.SCENARIO_DOC}: potential secret content patterns found: {found}"
            )


class TestSafetyContract:
    LR_DOC = "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"

    def test_lr_doc_is_no_go(self):
        text = read_text(self.LR_DOC)
        no_go_variants = [
            "NO-GO",
            "No-Go",
            "no-go",
            "No Go",
        ]
        found = [t for t in no_go_variants if t in text]
        if not found:
            pytest.fail(
                f"{self.LR_DOC}: no NO-GO pattern found"
            )
        assert "NO-GO" in text or "no-go" in text

    def test_develop_doc_safety_boundaries(self):
        text = read_text("DEVELOPER_ONBOARDING.md")
        assert "LR bleibt NO-GO" in text or "LR remains NO-GO" in text
        assert "trade-capable" in text
        assert "Echtgeld-Go" in text or "Echtgeld" in text
        assert "CURRENT_STATUS.md" in text

    def test_readme_does_not_claim_live_go(self):
        text = read_text("README.md").lower()
        forbidden = ["live go", "live-go", "echtgeld-go"]
        found = [t for t in forbidden if t in text]
        if found:
            pytest.fail(
                f"README.md: contains forbidden term(s): {found}"
            )

    def test_trading_mode_default_is_safe(self):
        from core.config.trading_mode import TradingMode

        assert TradingMode.PAPER.value == "paper"
        assert TradingMode.PAPER.is_safe
        assert not TradingMode.LIVE.is_safe

    def test_board_stage_not_live_go(self):
        text = read_text("docs/runbooks/CONTROL_REGISTER.md")
        assert "trade-capable" in text
        go_phrases = ["LR remains NO-GO", "LR-050" in text and "NO-GO" in text]
        assert any(
            phrase for phrase in ["LR remains NO-GO", "kein Live-Kapital", "LR-050"]
            if phrase in text
        )


class TestDriftContract:
    DRIFT_DOC = "docs/runbooks/legacy_service_drift.md"
    CATALOG = "knowledge/governance/SERVICE_CATALOG.md"

    def test_drift_doc_required_terms(self):
        text = read_text(self.DRIFT_DOC)
        assert_terms_in_text(text, DRIFT_TERMS, self.DRIFT_DOC)

    def test_drift_doc_expected_states(self):
        text = read_text(self.DRIFT_DOC)
        assert "absent" in text
        assert "Jannek-Ops-GO" in text
        assert "Bereinigung" in text
        assert "Read-Only-Prüfung" in text or "Read-Only" in text

    def test_catalog_contains_legacy_services(self):
        text = read_text(self.CATALOG)
        legacy_services = [
            "cdb_node_exporter",
            "cdb_market_eth",
            "lr030_soak_monitor",
            "lr040_soak_monitor",
        ]
        assert_terms_in_text(text, legacy_services, self.CATALOG)

    def test_catalog_contains_mockx_valkey(self):
        text = read_text(self.CATALOG)
        assert "mockx-valkey" in text
        assert "absent by default" in text

    def test_catalog_requires_jannek_ops_go(self):
        text = read_text(self.CATALOG)
        assert "Jannek-Ops-GO" in text


class TestGordonRegression:
    def test_active_canon_uses_jannek_ops_go_not_gordon(self):
        for rel_path in ACTIVE_CANON_GORDON_PATHS:
            full = REPO_ROOT / rel_path
            if not full.exists():
                continue
            text = full.read_text(encoding="utf-8")
            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                if re.search(r"Gordon|gordon", line):
                    lower_line = line.lower()
                    has_allowed = any(
                        ctx in lower_line for ctx in GORDON_ALLOWED_CONTEXTS
                    )
                    is_jannek_gate = "Jannek-Ops-GO" in line
                    if has_allowed or is_jannek_gate:
                        continue
                    pytest.fail(
                        f"{rel_path}:{i}: Gordon mention without allowed context "
                        f"(historical/archive/old/ersetzt/replaced/negative case). "
                        f"Expected Jannek-Ops-GO / Infra-Mutation-Gate instead. "
                        f"Line: {line.strip()}"
                    )

    def test_active_canon_contains_jannek_ops_go(self):
        scenario_doc = (
            "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md"
        )
        text = read_text(scenario_doc)
        assert "Jannek-Ops-GO" in text
        assert "Infra-Mutation-Gate" in text

    def test_legacy_drift_gate_language(self):
        text = read_text("docs/runbooks/legacy_service_drift.md")
        assert "Jannek-Ops-GO" in text


class TestLiveReadinessFile:
    LR_DOC = "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"

    def test_lr_file_contains_explicit_no_go(self):
        text = read_text(self.LR_DOC)
        no_go_variants = ["NO-GO", "No-Go", "no-go"]
        found = [t for t in no_go_variants if t in text]
        if not found:
            pytest.fail(
                f"{self.LR_DOC}: no NO-GO variant found"
            )

    def test_lr_file_structure(self):
        text = read_text(self.LR_DOC)
        expected_sections = [
            "Executive Summary",
            "Phase Status Table",
            "NO-GO",
        ]
        for section in expected_sections:
            assert section in text, (
                f"{self.LR_DOC}: missing expected section '{section}'"
            )


class TestControlRegister:
    CONTROL_DOC = "docs/runbooks/CONTROL_REGISTER.md"

    def test_control_register_board_stage(self):
        text = read_text(self.CONTROL_DOC)
        assert "trade-capable" in text

    def test_control_register_lr_verdict(self):
        text = read_text(self.CONTROL_DOC)
        assert "NO-GO" in text

    def test_control_register_ssot_boundaries(self):
        text = read_text(self.CONTROL_DOC)
        assert "SSOT" in text
        assert "LR-AUDIT-STATUS" in text
