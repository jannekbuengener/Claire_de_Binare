"""Effective-Config snapshot provenance tests (#4151 remainder).

test_id: tc_effective_config_snapshot_001
test_type: schutz
cdb_area: replay/provenance
issue_ref: #4151
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "docs/contracts/cdb_effective_config_snapshot.v1.schema.json"


def test_effective_config_module_importable() -> None:
    """Regression: module must exist so sensitivity preflight can discover it."""
    from core.replay import effective_config_snapshot as efc

    assert efc.SCHEMA_VERSION == "cdb.effective_config_snapshot.v1"
    assert (
        REPO_ROOT / "docs/contracts/cdb_effective_config_snapshot.v1.schema.json"
    ).is_file()


def test_same_resolved_config_yields_stable_fingerprint() -> None:
    from core.replay.effective_config_snapshot import (
        build_effective_config_snapshot,
        fingerprint_snapshot_body,
    )

    first = build_effective_config_snapshot(REPO_ROOT)
    second = build_effective_config_snapshot(REPO_ROOT)
    assert first["snapshot_fingerprint"] == second["snapshot_fingerprint"]
    assert len(first["snapshot_fingerprint"]) == 64
    body = {k: v for k, v in first.items() if k != "snapshot_fingerprint"}
    assert fingerprint_snapshot_body(body) == first["snapshot_fingerprint"]


def test_relevant_override_changes_fingerprint() -> None:
    from core.replay.effective_config_snapshot import build_effective_config_snapshot

    baseline = build_effective_config_snapshot(REPO_ROOT)
    changed = build_effective_config_snapshot(
        REPO_ROOT,
        env_overrides={"MOCK_TRADING": "false"},
    )
    assert changed["snapshot_fingerprint"] != baseline["snapshot_fingerprint"]
    assert changed["execution"]["mock_trading"] is False
    assert baseline["execution"]["mock_trading"] is True


def test_incomplete_snapshot_fail_closed() -> None:
    from core.replay.effective_config_snapshot import (
        EffectiveConfigSnapshotError,
        validate_effective_config_snapshot,
    )

    with pytest.raises(EffectiveConfigSnapshotError):
        validate_effective_config_snapshot(
            {"schema_version": "cdb.effective_config_snapshot.v1"}
        )


def test_secret_keys_redacted_and_rejected() -> None:
    from core.replay.effective_config_snapshot import (
        EffectiveConfigSnapshotError,
        build_effective_config_snapshot,
        validate_effective_config_snapshot,
    )

    snap = build_effective_config_snapshot(REPO_ROOT)
    blob = str(snap).lower()
    for token in ("password", "api_key", "api_secret", "redis_password", "token"):
        assert token not in blob

    dirty = copy.deepcopy(snap)
    dirty["environment_redacted"]["REDIS_PASSWORD"] = "leak"
    with pytest.raises(EffectiveConfigSnapshotError):
        validate_effective_config_snapshot(dirty)


def test_required_sections_and_override_order_present() -> None:
    from core.replay.effective_config_snapshot import (
        REQUIRED_SECTIONS,
        build_effective_config_snapshot,
        validate_effective_config_snapshot,
    )

    snap = build_effective_config_snapshot(REPO_ROOT)
    validate_effective_config_snapshot(snap)
    for key in REQUIRED_SECTIONS:
        assert key in snap
    assert list(snap["override_order"]) == ["code_default", "compose", "env"]
    for section in ("compose", "risk", "allocation", "regime", "signal", "execution"):
        assert isinstance(snap[section], dict) and snap[section]


def test_compose_override_beats_code_default() -> None:
    """Later compose layer must win over code_default for resolved fields."""
    from core.replay.effective_config_snapshot import build_effective_config_snapshot

    baseline = build_effective_config_snapshot(REPO_ROOT)
    changed = build_effective_config_snapshot(
        REPO_ROOT,
        compose_overrides={
            "regime": {"atr_high_vol_threshold": 0.042},
            "signal": {"entry_lookback_minutes": 333},
        },
    )
    assert baseline["regime"]["atr_high_vol_threshold"] != 0.042
    assert changed["regime"]["atr_high_vol_threshold"] == 0.042
    assert changed["signal"]["entry_lookback_minutes"] == 333
    assert changed["snapshot_fingerprint"] != baseline["snapshot_fingerprint"]


def test_env_override_beats_compose() -> None:
    """Explicit env/experiment overrides must beat compose (DEFAULT_OVERRIDE_ORDER)."""
    from core.replay.effective_config_snapshot import build_effective_config_snapshot

    compose_only = build_effective_config_snapshot(
        REPO_ROOT,
        compose_overrides={"execution": {"mock_trading": True}},
    )
    env_wins = build_effective_config_snapshot(
        REPO_ROOT,
        compose_overrides={"execution": {"mock_trading": True}},
        env_overrides={"MOCK_TRADING": "false"},
    )
    assert compose_only["execution"]["mock_trading"] is True
    assert env_wins["execution"]["mock_trading"] is False
    assert env_wins["snapshot_fingerprint"] != compose_only["snapshot_fingerprint"]


def test_built_snapshot_validates_against_json_schema() -> None:
    from core.replay.effective_config_snapshot import build_effective_config_snapshot

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    snap = build_effective_config_snapshot(REPO_ROOT)
    jsonschema.validate(instance=snap, schema=schema)


def test_evidence_links_do_not_alter_snapshot_fingerprint() -> None:
    from core.replay.effective_config_snapshot import (
        build_effective_config_snapshot,
        link_snapshot_to_evidence,
    )

    snap = build_effective_config_snapshot(REPO_ROOT)
    linked = link_snapshot_to_evidence(
        snap,
        experiment_id="exp-test",
        run_id="run-test",
        preflight_report_fingerprint="a" * 64,
    )
    assert linked["snapshot_fingerprint"] == snap["snapshot_fingerprint"]
    assert linked["evidence_links"]["experiment_id"] == "exp-test"
    assert "evidence_links" not in snap
