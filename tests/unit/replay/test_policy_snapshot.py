"""Tests for core.replay.policy_snapshot — builder + toggle.

Issue #748 Slice 2: Policy snapshot binding.
"""

import pytest

from core.replay.policy_snapshot import (
    build_policy_snapshot,
    policy_snapshot_binding_enabled,
)
from core.utils.uuid_gen import POLICY_ID


SAMPLE_THRESHOLDS = {
    "return_1m_min": -2.0,
    "return_5m_min": -5.0,
    "price_change_5m_abs_max": 10.0,
    "staleness_s_max": 5.0,
    "allowed_regimes": [0, 1],
}

SAMPLE_TS_MS = 1706000000000  # 2024-01-23T...


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure no toggle/env leaks between tests."""
    monkeypatch.delenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", raising=False)
    monkeypatch.delenv("CDB_GIT_COMMIT", raising=False)
    monkeypatch.delenv("CDB_POLICY_VERSION", raising=False)


# ---------------------------------------------------------------------------
# Toggle tests
# ---------------------------------------------------------------------------

class TestPolicySnapshotBindingEnabled:
    def test_default_off(self):
        """Unset -> OFF."""
        assert policy_snapshot_binding_enabled() is False

    def test_enabled_when_1(self, monkeypatch):
        monkeypatch.setenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", "1")
        assert policy_snapshot_binding_enabled() is True

    def test_disabled_when_0(self, monkeypatch):
        monkeypatch.setenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", "0")
        assert policy_snapshot_binding_enabled() is False

    def test_disabled_on_garbage(self, monkeypatch):
        monkeypatch.setenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", "yes")
        assert policy_snapshot_binding_enabled() is False


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------

class TestBuildPolicySnapshot:
    def test_all_keys_present(self):
        """Snapshot has exactly 5 required keys."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert set(snap.keys()) == {
            "policy_id", "version", "git_commit", "checksum", "effective_at",
        }

    def test_deterministic_checksum(self):
        """Same thresholds -> same checksum."""
        snap1 = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        snap2 = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert snap1["checksum"] == snap2["checksum"]

    def test_checksum_dict_order_independent(self):
        """Checksum is stable regardless of dict insertion order."""
        ordered = {"a": 1, "b": 2, "c": 3}
        reversed_order = {"c": 3, "b": 2, "a": 1}
        snap1 = build_policy_snapshot(ordered, SAMPLE_TS_MS)
        snap2 = build_policy_snapshot(reversed_order, SAMPLE_TS_MS)
        assert snap1["checksum"] == snap2["checksum"]

    def test_different_thresholds_different_checksum(self):
        """Different thresholds -> different checksum."""
        other = {**SAMPLE_THRESHOLDS, "return_1m_min": -999.0}
        snap1 = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        snap2 = build_policy_snapshot(other, SAMPLE_TS_MS)
        assert snap1["checksum"] != snap2["checksum"]

    def test_no_secrets_in_output(self):
        """No env vars, passwords, keys, tokens leaked into snapshot."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        forbidden = {"secret", "token", "password", "api_key", "credential"}
        all_text = " ".join(
            f"{k} {v}" for k, v in snap.items()
        ).lower()
        for word in forbidden:
            assert word not in all_text, f"Forbidden word '{word}' found in snapshot"

    def test_effective_at_iso8601_utc(self):
        """effective_at is valid ISO-8601 with UTC timezone."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        ea = snap["effective_at"]
        assert isinstance(ea, str)
        assert "+00:00" in ea or ea.endswith("Z")
        # Must be parseable
        from datetime import datetime
        dt = datetime.fromisoformat(ea)
        assert dt.tzinfo is not None

    def test_git_commit_from_env(self, monkeypatch):
        """CDB_GIT_COMMIT env var is used."""
        monkeypatch.setenv("CDB_GIT_COMMIT", "abc1234def")
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert snap["git_commit"] == "abc1234def"

    def test_git_commit_fallback_unknown(self):
        """Unset CDB_GIT_COMMIT -> 'unknown'."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert snap["git_commit"] == "unknown"

    def test_policy_id_matches_constant(self):
        """policy_id matches POLICY_ID from uuid_gen."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert snap["policy_id"] == POLICY_ID

    def test_version_from_env(self, monkeypatch):
        """CDB_POLICY_VERSION env var is used."""
        monkeypatch.setenv("CDB_POLICY_VERSION", "2.0.0")
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert snap["version"] == "2.0.0"

    def test_version_fallback_unknown(self):
        """Unset CDB_POLICY_VERSION -> 'unknown'."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert snap["version"] == "unknown"

    def test_all_values_are_strings(self):
        """All values in snapshot are strings (no nested objects)."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        for key, value in snap.items():
            assert isinstance(value, str), f"{key} is {type(value)}, expected str"

    def test_checksum_is_hex_sha256(self):
        """Checksum is a 64-char hex string (SHA256)."""
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert len(snap["checksum"]) == 64
        assert all(c in "0123456789abcdef" for c in snap["checksum"])
