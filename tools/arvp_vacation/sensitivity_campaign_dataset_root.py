"""Canonical dataset-root resolver for #4153 sensitivity campaign execution.

Resolves and verifies the dataset root supplied at ``execute`` time against the
manifest window bindings. Emits a stable identity dict that is bound into the
execution-surface fingerprint and the campaign envelope.

Fail-closed reason codes:
    DATASET_ROOT_UNBOUND
        No dataset root supplied to execute path.
    DATASET_ROOT_MISSING
        Resolved path does not exist on disk.
    DATASET_ROOT_NOT_ABSOLUTE
        Resolved path is not absolute after realpath resolution.
    DATASET_SYMLINK_ESCAPE
        Resolved path escapes the declared root via symlink or parent-of-symlink.
    DATASET_TRAVERSAL
        Traversal marker (``..``) present in the declared root argument.
    DATASET_WINDOW_MISSING
        A manifest window binding does not resolve under the window-bank layout.
    DATASET_CONTENT_FINGERPRINT_MISMATCH
        On-disk content fingerprint disagrees with the manifest binding.
    DATASET_MANIFEST_INVALID
        Manifest missing / malformed window_bindings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash

DATASET_ROOT_CONTRACT_VERSION = "cdb.sensitivity_campaign_dataset_root.v1"

WINDOW_BANK_SUFFIX = PurePath("window_bank/binance/spot/BTCUSDT/1m")


class SensitivityDatasetRootError(ValueError):
    """Fail-closed dataset-root resolver error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        message = reason_code if not detail else f"{reason_code}: {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class DatasetRootIdentity:
    window_bank_root: str
    window_count: int
    content_fingerprints_hash: str
    dataset_identity_fingerprint: str
    schema_version: str = DATASET_ROOT_CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "window_bank_root": self.window_bank_root,
            "window_count": int(self.window_count),
            "content_fingerprints_hash": self.content_fingerprints_hash,
            "dataset_identity_fingerprint": self.dataset_identity_fingerprint,
        }


def _reject_traversal_component(raw: Path) -> None:
    """Reject any ``..`` component in the declared path before resolving."""
    parts = PurePath(str(raw)).parts
    if any(p == ".." for p in parts):
        raise SensitivityDatasetRootError(
            "DATASET_TRAVERSAL", f"path contains parent traversal: {raw}"
        )


def _resolve_realpath(path: Path) -> Path:
    """Resolve ``..``-free absolute realpath, distinguishing missing from escape."""
    try:
        resolved = Path(os.path.realpath(str(path)))
    except OSError as exc:
        raise SensitivityDatasetRootError(
            "DATASET_ROOT_MISSING", f"{path}: {exc}"
        ) from exc
    return resolved


def _pick_window_bank_root(dataset_root: Path, repo_root: Path) -> Path:
    """Return the resolved absolute window-bank root under the declared root.

    Accepts either the parent ``artifacts/market_data`` (with a
    ``window_bank/binance/spot/BTCUSDT/1m`` child) or a path that already ends
    in the canonical window-bank suffix.
    """
    _reject_traversal_component(dataset_root)

    resolved = _resolve_realpath(dataset_root)
    if not resolved.is_absolute():
        raise SensitivityDatasetRootError("DATASET_ROOT_NOT_ABSOLUTE", str(resolved))
    if not resolved.exists():
        raise SensitivityDatasetRootError("DATASET_ROOT_MISSING", str(resolved))

    resolved_suffix = PurePath(*resolved.parts[-len(WINDOW_BANK_SUFFIX.parts) :])
    candidates: list[Path] = []
    child = resolved / WINDOW_BANK_SUFFIX
    if child.exists():
        candidates.append(child)
    if resolved_suffix.as_posix() == WINDOW_BANK_SUFFIX.as_posix():
        candidates.append(resolved)
    if not candidates:
        raise SensitivityDatasetRootError(
            "DATASET_ROOT_MISSING",
            f"neither {child} nor a canonical window-bank suffix under {resolved}",
        )

    bank = _resolve_realpath(candidates[0])
    if not bank.is_absolute():
        raise SensitivityDatasetRootError("DATASET_ROOT_NOT_ABSOLUTE", str(bank))
    # Reject symlink escapes: the bank realpath must live under the declared
    # dataset-root realpath.
    try:
        bank.relative_to(resolved)
    except ValueError as exc:
        # Accept the case where the caller passed the bank itself (equal path).
        if bank != resolved:
            raise SensitivityDatasetRootError(
                "DATASET_SYMLINK_ESCAPE",
                f"resolved bank {bank} escapes declared root {resolved}",
            ) from exc
    _ = repo_root  # reserved for future repo-relative binding
    return bank


def _load_window_content_fingerprint(bank_root: Path, window_id: str) -> str | None:
    """Read on-disk ``dataset_spec.json`` and return its content_fingerprint."""
    window_dir = bank_root / window_id
    if not window_dir.exists():
        return None
    spec = window_dir / "dataset_spec.json"
    if not spec.exists():
        return None
    try:
        import json

        payload = json.loads(spec.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    # dataset_spec content_fingerprint keys as observed in the bank layout.
    for key in ("content_fingerprint", "candles_content_fingerprint", "fingerprint"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def resolve_and_verify_dataset_root(
    *,
    dataset_root: Path,
    manifest: Mapping[str, Any],
    repo_root: Path,
    trust_manifest_content_fingerprints: bool = False,
) -> DatasetRootIdentity:
    """Resolve the dataset root and verify all manifest bindings.

    Returns a :class:`DatasetRootIdentity` with a stable, path-independent
    ``dataset_identity_fingerprint`` derived from the sorted list of
    ``(window_id, content_fingerprint)`` pairs.

    When ``trust_manifest_content_fingerprints`` is True (governed adoption
    resume only), window directories must still exist, but on-disk
    ``dataset_spec.json`` fingerprints that drifted after primary execution are
    not allowed to block resume. The manifest binding remains the SSOT for the
    identity hash (matching primary run envelopes).
    """
    if dataset_root is None:
        raise SensitivityDatasetRootError(
            "DATASET_ROOT_UNBOUND", "execute path requires --dataset-root"
        )
    bindings = manifest.get("window_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise SensitivityDatasetRootError(
            "DATASET_MANIFEST_INVALID", "manifest.window_bindings missing or empty"
        )

    bank_root = _pick_window_bank_root(Path(dataset_root), Path(repo_root))

    pairs: list[tuple[str, str]] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            raise SensitivityDatasetRootError(
                "DATASET_MANIFEST_INVALID",
                "window_bindings must be a list of objects",
            )
        window_id = str(binding.get("window_id") or "")
        expected_fp = str(binding.get("content_fingerprint") or "")
        if not window_id or not expected_fp:
            raise SensitivityDatasetRootError(
                "DATASET_MANIFEST_INVALID",
                f"window binding missing window_id/content_fingerprint: {binding!r}",
            )
        window_dir = bank_root / window_id
        if not window_dir.exists():
            raise SensitivityDatasetRootError(
                "DATASET_WINDOW_MISSING",
                f"{window_id!r} not present under {bank_root}",
            )
        # Guard symlink escape on the window dir itself.
        try:
            _resolve_realpath(window_dir).relative_to(bank_root)
        except ValueError as exc:
            raise SensitivityDatasetRootError(
                "DATASET_SYMLINK_ESCAPE",
                f"window {window_id!r} escapes bank root",
            ) from exc
        actual_fp = _load_window_content_fingerprint(bank_root, window_id)
        if (
            actual_fp is not None
            and actual_fp != expected_fp
            and not trust_manifest_content_fingerprints
        ):
            raise SensitivityDatasetRootError(
                "DATASET_CONTENT_FINGERPRINT_MISMATCH",
                (
                    f"window {window_id!r}: on-disk {actual_fp!r} != "
                    f"manifest {expected_fp!r}"
                ),
            )
        # When the on-disk spec does not expose a content fingerprint we bind
        # the manifest value; this matches the current window-bank layout where
        # the manifest is the SSOT for content identity.
        pairs.append((window_id, expected_fp))

    pairs_sorted = sorted(pairs, key=lambda entry: entry[0])
    fingerprints_hash = canonical_hash(
        {
            "pairs": [
                {"window_id": w, "content_fingerprint": fp} for w, fp in pairs_sorted
            ]
        }
    )
    identity_body = {
        "schema_version": DATASET_ROOT_CONTRACT_VERSION,
        "window_count": len(pairs_sorted),
        "content_fingerprints_hash": fingerprints_hash,
    }
    identity_fp = canonical_hash(identity_body)

    return DatasetRootIdentity(
        window_bank_root=str(bank_root),
        window_count=len(pairs_sorted),
        content_fingerprints_hash=fingerprints_hash,
        dataset_identity_fingerprint=identity_fp,
    )
