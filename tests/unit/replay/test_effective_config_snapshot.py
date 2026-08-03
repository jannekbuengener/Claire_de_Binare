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
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


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
