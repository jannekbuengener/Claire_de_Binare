"""Canonical dataset-root resolver unit tests (#4153).

test_id: tc_sensitivity_campaign_dataset_root_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tools.arvp_vacation.sensitivity_campaign_dataset_root import (
    DATASET_ROOT_CONTRACT_VERSION,
    SensitivityDatasetRootError,
    resolve_and_verify_dataset_root,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _fake_manifest(window_ids: list[str]) -> dict:
    return {
        "window_bindings": [
            {"window_id": w, "content_fingerprint": f"fp-{w}"} for w in window_ids
        ]
    }


def _build_bank(tmp_path: Path, window_ids: list[str]) -> Path:
    """Materialize the canonical window-bank layout under ``tmp_path``.

    Returns the ``artifacts/market_data`` parent so callers can pass either that
    or the resolved bank root directly.
    """
    root = tmp_path / "artifacts" / "market_data"
    bank = root / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    bank.mkdir(parents=True, exist_ok=True)
    for w in window_ids:
        (bank / w).mkdir(parents=True, exist_ok=True)
    return root


def test_dataset_root_unbound_raises() -> None:
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=None,  # type: ignore[arg-type]
            manifest=_fake_manifest(["w1"]),
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_ROOT_UNBOUND"


def test_dataset_root_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=tmp_path / "does-not-exist",
            manifest=_fake_manifest(["w1"]),
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_ROOT_MISSING"


def test_dataset_manifest_invalid_when_bindings_missing(tmp_path: Path) -> None:
    root = _build_bank(tmp_path, [])
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=root,
            manifest={"window_bindings": []},
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_MANIFEST_INVALID"


def test_dataset_manifest_invalid_when_binding_incomplete(tmp_path: Path) -> None:
    root = _build_bank(tmp_path, ["w1"])
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=root,
            manifest={"window_bindings": [{"window_id": "w1"}]},  # no fingerprint
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_MANIFEST_INVALID"


def test_dataset_traversal_rejected(tmp_path: Path) -> None:
    root = _build_bank(tmp_path, ["w1"])
    # Deliberate .. component in the declared arg triggers traversal guard
    # before realpath resolution.
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=root / ".." / root.name,
            manifest=_fake_manifest(["w1"]),
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_TRAVERSAL"


def test_dataset_window_missing_raises(tmp_path: Path) -> None:
    root = _build_bank(tmp_path, ["w1"])
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=root,
            manifest=_fake_manifest(["w1", "w-missing"]),
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_WINDOW_MISSING"


def test_dataset_content_fingerprint_mismatch(tmp_path: Path) -> None:
    """On-disk dataset_spec.json disagreeing with manifest raises fail-closed."""
    import json as _json

    root = _build_bank(tmp_path, ["w1"])
    bank = root / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    (bank / "w1" / "dataset_spec.json").write_text(
        _json.dumps({"content_fingerprint": "on-disk-different"}),
        encoding="utf-8",
    )
    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=root,
            manifest=_fake_manifest(["w1"]),
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_CONTENT_FINGERPRINT_MISMATCH"


def test_dataset_identity_bound_and_deterministic(tmp_path: Path) -> None:
    root = _build_bank(tmp_path, ["w1", "w2", "w3"])
    identity_a = resolve_and_verify_dataset_root(
        dataset_root=root,
        manifest=_fake_manifest(["w1", "w2", "w3"]),
        repo_root=REPO_ROOT,
    )
    # Order of manifest bindings must not affect the identity fingerprint.
    identity_b = resolve_and_verify_dataset_root(
        dataset_root=root,
        manifest=_fake_manifest(["w3", "w1", "w2"]),
        repo_root=REPO_ROOT,
    )
    assert (
        identity_a.dataset_identity_fingerprint
        == identity_b.dataset_identity_fingerprint
    )
    assert identity_a.window_count == 3
    assert identity_a.schema_version == DATASET_ROOT_CONTRACT_VERSION
    payload = identity_a.as_dict()
    assert payload["window_bank_root"] == identity_a.window_bank_root
    assert (
        payload["dataset_identity_fingerprint"]
        == identity_a.dataset_identity_fingerprint
    )


def test_dataset_root_accepts_full_bank_path(tmp_path: Path) -> None:
    """Both ``.../artifacts/market_data`` and the full bank suffix are valid."""
    parent = _build_bank(tmp_path, ["w1"])
    bank = parent / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    identity_parent = resolve_and_verify_dataset_root(
        dataset_root=parent,
        manifest=_fake_manifest(["w1"]),
        repo_root=REPO_ROOT,
    )
    identity_bank = resolve_and_verify_dataset_root(
        dataset_root=bank,
        manifest=_fake_manifest(["w1"]),
        repo_root=REPO_ROOT,
    )
    # Content-based identity is stable across both entry points.
    assert (
        identity_parent.dataset_identity_fingerprint
        == identity_bank.dataset_identity_fingerprint
    )
    # Resolved bank realpath equals the on-disk canonical bank root.
    assert Path(identity_parent.window_bank_root).resolve() == bank.resolve()
    assert Path(identity_bank.window_bank_root).resolve() == bank.resolve()


def _windows_symlink_supported(tmp_path: Path) -> bool:
    if sys.platform != "win32":
        return True
    src = tmp_path / "_probe_src"
    dst = tmp_path / "_probe_dst"
    try:
        src.mkdir()
        os.symlink(src, dst, target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    return True


def test_dataset_symlink_escape_raises(tmp_path: Path) -> None:
    """A window directory that is a symlink pointing outside the bank fails closed."""
    if not _windows_symlink_supported(tmp_path):
        pytest.skip("symlink creation not permitted on this platform")

    outside = tmp_path / "outside"
    outside.mkdir()
    root = _build_bank(tmp_path, [])
    bank = root / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    # Symlink `w1` -> outside/, which is outside the declared dataset root.
    try:
        os.symlink(outside, bank / "w1", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform")

    with pytest.raises(SensitivityDatasetRootError) as exc:
        resolve_and_verify_dataset_root(
            dataset_root=root,
            manifest=_fake_manifest(["w1"]),
            repo_root=REPO_ROOT,
        )
    assert exc.value.reason_code == "DATASET_SYMLINK_ESCAPE"
