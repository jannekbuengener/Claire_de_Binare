"""
Unit-Tests fuer Paper Evidence Probe Toggle.

Governance: Issue #2141 / Phase 3
"""

import pytest

from core.utils.paper_probe_toggle import paper_evidence_probe_enabled


@pytest.mark.unit
class TestPaperProbeToggle:
    def test_off_by_default(self, monkeypatch):
        """Toggle is OFF when neither ENV var is set."""
        monkeypatch.delenv("PAPER_EVIDENCE_PROBE_MODE", raising=False)
        monkeypatch.delenv("MOCK_TRADING", raising=False)
        assert paper_evidence_probe_enabled() is False

    def test_off_when_only_probe_mode_set(self, monkeypatch):
        """Toggle is OFF when PAPER_EVIDENCE_PROBE_MODE=1 but MOCK_TRADING not set."""
        monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
        monkeypatch.delenv("MOCK_TRADING", raising=False)
        assert paper_evidence_probe_enabled() is False

    def test_off_when_only_mock_trading_set(self, monkeypatch):
        """Toggle is OFF when MOCK_TRADING=true but PAPER_EVIDENCE_PROBE_MODE not set."""
        monkeypatch.delenv("PAPER_EVIDENCE_PROBE_MODE", raising=False)
        monkeypatch.setenv("MOCK_TRADING", "true")
        assert paper_evidence_probe_enabled() is False

    def test_on_when_both_set(self, monkeypatch):
        """Toggle is ON only when BOTH PAPER_EVIDENCE_PROBE_MODE=1 AND MOCK_TRADING=true."""
        monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
        monkeypatch.setenv("MOCK_TRADING", "true")
        assert paper_evidence_probe_enabled() is True

    def test_off_when_probe_mode_zero(self, monkeypatch):
        """Toggle is OFF when PAPER_EVIDENCE_PROBE_MODE=0 even with MOCK_TRADING=true."""
        monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "0")
        monkeypatch.setenv("MOCK_TRADING", "true")
        assert paper_evidence_probe_enabled() is False

    def test_off_when_mock_trading_false(self, monkeypatch):
        """Toggle is OFF when MOCK_TRADING=false even with PAPER_EVIDENCE_PROBE_MODE=1."""
        monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
        monkeypatch.setenv("MOCK_TRADING", "false")
        assert paper_evidence_probe_enabled() is False

    def test_on_mock_trading_case_insensitive(self, monkeypatch):
        """MOCK_TRADING is matched case-insensitively (TRUE, True, true all valid)."""
        for value in ("TRUE", "True", "true"):
            monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
            monkeypatch.setenv("MOCK_TRADING", value)
            assert paper_evidence_probe_enabled() is True, f"Failed for MOCK_TRADING={value}"

    def test_off_mock_trading_garbage_value(self, monkeypatch):
        """Toggle is OFF for unexpected MOCK_TRADING values."""
        monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
        monkeypatch.setenv("MOCK_TRADING", "yes")
        assert paper_evidence_probe_enabled() is False

    def test_reads_env_on_every_call(self, monkeypatch):
        """No module-level cache: toggle reflects ENV change between calls."""
        monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
        monkeypatch.setenv("MOCK_TRADING", "true")
        assert paper_evidence_probe_enabled() is True

        monkeypatch.setenv("MOCK_TRADING", "false")
        assert paper_evidence_probe_enabled() is False
