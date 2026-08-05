"""Campaign analyzer unit tests (#4153).

test_id: tc_sensitivity_campaign_analyzer_runtime_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

from pathlib import Path

from tools.arvp_vacation.sensitivity_campaign_analyzer import _classify
from tools.arvp_vacation.sensitivity_campaign_state import CAMPAIGN_PHASE_COMPLETED


def test_classify_blocked_without_reproduction() -> None:
    out = _classify(
        campaign_phase=CAMPAIGN_PHASE_COMPLETED,
        reproduction={"reproduction_pass": False},
        main_effects={"weighted_ranking": [{"slot_id": "a", "net_pnl": 1.0}]},
        interaction_effects={"weighted_ranking": []},
    )
    assert out["classification"] == "BLOCKED"


def test_classify_inconclusive_default(tmp_path: Path) -> None:
    _ = tmp_path
    out = _classify(
        campaign_phase=CAMPAIGN_PHASE_COMPLETED,
        reproduction={"reproduction_pass": True},
        main_effects={
            "weighted_ranking": [
                {
                    "slot_id": "baseline",
                    "net_pnl": 0.0,
                    "expectancy": 0.0,
                    "overfitting_flag_rate": 0.0,
                }
            ]
        },
        interaction_effects={"weighted_ranking": []},
    )
    assert out["classification"] == "INCONCLUSIVE"
