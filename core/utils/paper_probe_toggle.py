"""
Paper Evidence Probe Toggle.

Aktiviert die Paper-Evidence-Probe, wenn BEIDE Bedingungen erfuellt sind:
  - PAPER_EVIDENCE_PROBE_MODE=1
  - MOCK_TRADING=true

Dual-Guard: Kann nicht ohne explizite Paper/Mock-Konfiguration aktiviert werden.
Betrifft ausschliesslich Paper-Betrieb; nie fuer Live-/Echtgeld-Pfade.

Governance: Issue #2141 / Phase 3
Default: OFF (0). Alle Probe-Bypasses MUESSEN hinter dieser Funktion stehen.

Liest os.getenv bei jedem Aufruf (kein Modul-Level-Cache),
damit Tests via monkeypatch.setenv umschalten koennen.
"""

import os


def paper_evidence_probe_enabled() -> bool:
    """True nur wenn PAPER_EVIDENCE_PROBE_MODE=1 UND MOCK_TRADING=true."""
    return (
        os.getenv("PAPER_EVIDENCE_PROBE_MODE", "0") == "1"
        and os.getenv("MOCK_TRADING", "false").lower() == "true"
    )
