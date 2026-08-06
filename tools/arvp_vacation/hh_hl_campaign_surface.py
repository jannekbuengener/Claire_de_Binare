"""hh_hl campaign single-run surface-capability receipt (#4374).

A *surface receipt* is a consumable, tamper-evident proof that the single-run
replay surface was probed for the frozen hh_hl campaign. It never authorizes
execution: ``replays`` and ``campaign_artifacts_written`` are constant ``False``
and ``fixture`` receipts are never eligible for an Owner Execution-GO package.

The capability fingerprint is the ``canonical_hash`` of the receipt body with
the fingerprint field itself (and the optional ``probed_at_utc`` timestamp)
excluded, so any field tamper is detected on reload. A bare 64-char hash is
never accepted — the full receipt body must recompute to the stored
fingerprint.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash, sha256_hex

SURFACE_RECEIPT_SCHEMA_VERSION = "cdb.hh_hl_campaign_surface_receipt.v1"
ALLOWED_EXECUTION_SURFACE_ID = "services.validation.strategy_replay_runner.single_run"

# Deterministic probe-code identity. Bump only when the probe contract changes.
PROBE_CODE_CONTRACT_VERSION = "cdb.hh_hl_campaign_surface_probe.v1"
PROBE_CODE_SHA = sha256_hex(PROBE_CODE_CONTRACT_VERSION.encode("utf-8"))

HH_HL_STRATEGY_ID = "hh_hl_continuation_v1"
HH_HL_ADAPTER_ID = "batch_b_shadow_runner_v1"
EXPECTED_RUN_COUNT = 39

SINGLE_RUN_PROVIDER_MODULE = "services.validation.strategy_replay_runner"
REPRODUCTION_PROVIDER_MODULE = "tools.arvp_vacation.hh_hl_campaign_reproduction"
ANALYZER_PROVIDER_MODULE = "tools.arvp_vacation.hh_hl_campaign_analyzer"

# Body fields (fingerprint scope): everything except the fingerprint itself and
# the optional non-deterministic ``probed_at_utc`` timestamp.
_FINGERPRINT_EXCLUDED = frozenset({"surface_capability_fingerprint", "probed_at_utc"})
REQUIRED_RECEIPT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "execution_surface_id",
    "probe_code_sha",
    "planning_sha",
    "manifest_fingerprint",
    "run_plan_fingerprint",
    "dataset_selection_sha256",
    "dataset_content_fingerprint_digest",
    "strategy_id",
    "adapter_id",
    "run_plan_loadable",
    "single_run_provider_reachable",
    "reproduction_provider_reachable",
    "analyzer_provider_reachable",
    "expected_run_count",
    "resource_budget",
    "free_disk_bytes",
    "fixture",
    "owner_go_package_eligible",
    "replays",
    "campaign_artifacts_written",
)

_SHA64_RE = re.compile(r"^[0-9a-f]{64}$")

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "contracts"
    / "cdb_hh_hl_campaign_surface_receipt.v1.schema.json"
)


class HhHlSurfaceReceiptError(ValueError):
    """Fail-closed surface-receipt error carrying a HOLD reason code."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


def _fingerprint_surface_body(receipt: Mapping[str, Any]) -> str:
    body = {k: v for k, v in receipt.items() if k not in _FINGERPRINT_EXCLUDED}
    return canonical_hash(body)


def _module_reachable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError, AttributeError):
        return False


def probe_provider_reachability() -> dict[str, bool]:
    """Import-check (never execute) the three campaign providers."""
    return {
        "single_run": _module_reachable(SINGLE_RUN_PROVIDER_MODULE),
        "reproduction": _module_reachable(REPRODUCTION_PROVIDER_MODULE),
        "analyzer": _module_reachable(ANALYZER_PROVIDER_MODULE),
    }


def _free_disk_bytes(repo_root: Path | None) -> int:
    target = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
    try:
        return int(shutil.disk_usage(str(target)).free)
    except OSError:
        return 0


def build_surface_receipt(
    *,
    execution_surface_id: str,
    planning_sha: str,
    manifest_fingerprint: str,
    run_plan_fingerprint: str,
    dataset_selection_sha256: str,
    dataset_content_fingerprint_digest: str,
    run_plan_loadable: bool,
    single_run_provider_reachable: bool,
    reproduction_provider_reachable: bool,
    analyzer_provider_reachable: bool,
    resource_budget: Mapping[str, Any],
    free_disk_bytes: int,
    fixture: bool,
    strategy_id: str = HH_HL_STRATEGY_ID,
    adapter_id: str = HH_HL_ADAPTER_ID,
    expected_run_count: int = EXPECTED_RUN_COUNT,
    owner_go_package_eligible: bool | None = None,
    probe_code_sha: str | None = None,
    probed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a full, fingerprint-bound surface receipt (never authorizes runs)."""
    if execution_surface_id != ALLOWED_EXECUTION_SURFACE_ID:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_SURFACE_ID_INVALID", str(execution_surface_id)
        )
    fixture = bool(fixture)
    reachable = (
        bool(single_run_provider_reachable)
        and bool(reproduction_provider_reachable)
        and bool(analyzer_provider_reachable)
    )
    if owner_go_package_eligible is None:
        owner_go_package_eligible = (
            (not fixture) and bool(run_plan_loadable) and reachable
        )
    # A fixture receipt is structurally incapable of authorizing a package.
    if fixture:
        owner_go_package_eligible = False

    receipt: dict[str, Any] = {
        "schema_version": SURFACE_RECEIPT_SCHEMA_VERSION,
        "execution_surface_id": execution_surface_id,
        "probe_code_sha": str(probe_code_sha or PROBE_CODE_SHA),
        "planning_sha": str(planning_sha or ""),
        "manifest_fingerprint": str(manifest_fingerprint or ""),
        "run_plan_fingerprint": str(run_plan_fingerprint or ""),
        "dataset_selection_sha256": str(dataset_selection_sha256 or ""),
        "dataset_content_fingerprint_digest": str(
            dataset_content_fingerprint_digest or ""
        ),
        "strategy_id": str(strategy_id or ""),
        "adapter_id": str(adapter_id or ""),
        "run_plan_loadable": bool(run_plan_loadable),
        "single_run_provider_reachable": bool(single_run_provider_reachable),
        "reproduction_provider_reachable": bool(reproduction_provider_reachable),
        "analyzer_provider_reachable": bool(analyzer_provider_reachable),
        "expected_run_count": int(expected_run_count),
        "resource_budget": dict(resource_budget or {}),
        "free_disk_bytes": int(free_disk_bytes),
        "fixture": fixture,
        "owner_go_package_eligible": bool(owner_go_package_eligible),
        "replays": False,
        "campaign_artifacts_written": False,
    }
    receipt["surface_capability_fingerprint"] = _fingerprint_surface_body(receipt)
    if probed_at_utc:
        receipt["probed_at_utc"] = str(probed_at_utc)
    return receipt


def probe_hh_hl_surface(
    *,
    fixture: bool,
    manifest_fingerprint: str,
    run_plan_fingerprint: str,
    planning_sha: str,
    dataset_selection_sha256: str,
    dataset_content_fingerprint_digest: str,
    run_plan_loadable: bool,
    resource_budget: Mapping[str, Any],
    strategy_id: str = HH_HL_STRATEGY_ID,
    adapter_id: str = HH_HL_ADAPTER_ID,
    expected_run_count: int = EXPECTED_RUN_COUNT,
    repo_root: Path | None = None,
    free_disk_bytes: int | None = None,
    reachability: Mapping[str, bool] | None = None,
    probed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Probe the single-run surface and emit a consumable receipt (no replays)."""
    reach = (
        dict(reachability)
        if reachability is not None
        else (probe_provider_reachability())
    )
    disk = (
        int(free_disk_bytes)
        if free_disk_bytes is not None
        else _free_disk_bytes(repo_root)
    )
    return build_surface_receipt(
        execution_surface_id=ALLOWED_EXECUTION_SURFACE_ID,
        planning_sha=planning_sha,
        manifest_fingerprint=manifest_fingerprint,
        run_plan_fingerprint=run_plan_fingerprint,
        dataset_selection_sha256=dataset_selection_sha256,
        dataset_content_fingerprint_digest=dataset_content_fingerprint_digest,
        run_plan_loadable=run_plan_loadable,
        single_run_provider_reachable=bool(reach.get("single_run")),
        reproduction_provider_reachable=bool(reach.get("reproduction")),
        analyzer_provider_reachable=bool(reach.get("analyzer")),
        resource_budget=resource_budget,
        free_disk_bytes=disk,
        fixture=fixture,
        strategy_id=strategy_id,
        adapter_id=adapter_id,
        expected_run_count=expected_run_count,
        probed_at_utc=probed_at_utc,
    )


def _load_surface_schema() -> dict[str, Any] | None:
    if not _SCHEMA_PATH.exists():
        return None
    import json

    payload = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def load_and_validate_surface_receipt(
    path_or_mapping: str | Path | Mapping[str, Any],
    *,
    allow_fixture_for_owner_go: bool = False,
) -> dict[str, Any]:
    """Load + fully validate a surface receipt. Fail-closed.

    Rejects: wrong schema version, incomplete body (a bare hash), wrong surface
    id, fingerprint tamper, non-constant ``replays``/``campaign_artifacts_written``,
    and — unless ``allow_fixture_for_owner_go`` — fixture receipts or
    non-owner-go-eligible receipts.
    """
    if isinstance(path_or_mapping, Mapping):
        data: dict[str, Any] = dict(path_or_mapping)
    else:
        import json

        path = Path(path_or_mapping)
        if not path.exists():
            raise HhHlSurfaceReceiptError("HOLD_SURFACE_RECEIPT_MISSING", str(path))
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise HhHlSurfaceReceiptError(
                "HOLD_SURFACE_RECEIPT_INVALID", "root not object"
            )
        data = raw

    if data.get("schema_version") != SURFACE_RECEIPT_SCHEMA_VERSION:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_SCHEMA_INVALID",
            str(data.get("schema_version")),
        )
    missing = [k for k in REQUIRED_RECEIPT_FIELDS if k not in data]
    if missing:
        raise HhHlSurfaceReceiptError("HOLD_SURFACE_RECEIPT_INCOMPLETE", str(missing))
    surface_id = str(data.get("execution_surface_id") or "")
    if surface_id != ALLOWED_EXECUTION_SURFACE_ID:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_SURFACE_ID_INVALID", surface_id
        )
    stored_fp = str(data.get("surface_capability_fingerprint") or "")
    if not _SHA64_RE.fullmatch(stored_fp):
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_FINGERPRINT_INVALID", stored_fp
        )
    recomputed = _fingerprint_surface_body(data)
    if recomputed != stored_fp:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_FINGERPRINT_MISMATCH",
            f"stored={stored_fp} recomputed={recomputed}",
        )
    if data.get("replays") is not False:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_REPLAYS_FLAG_INVALID", str(data.get("replays"))
        )
    if data.get("campaign_artifacts_written") is not False:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_ARTIFACTS_FLAG_INVALID",
            str(data.get("campaign_artifacts_written")),
        )

    fixture = bool(data.get("fixture"))
    eligible = bool(data.get("owner_go_package_eligible"))
    if fixture and eligible:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_FIXTURE_ELIGIBILITY_INVALID",
            "fixture receipt marked owner_go_package_eligible",
        )
    if not allow_fixture_for_owner_go:
        if fixture:
            raise HhHlSurfaceReceiptError(
                "HOLD_SURFACE_RECEIPT_FIXTURE_NOT_ELIGIBLE_FOR_OWNER_GO",
                "fixture receipt cannot back an Owner Execution-GO package",
            )
        if not eligible:
            raise HhHlSurfaceReceiptError(
                "HOLD_SURFACE_RECEIPT_NOT_OWNER_GO_ELIGIBLE",
                "owner_go_package_eligible is false",
            )

    if jsonschema is not None:
        schema = _load_surface_schema()
        if schema is not None:
            try:
                jsonschema.validate(instance=data, schema=schema)
            except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
                raise HhHlSurfaceReceiptError(
                    "HOLD_SURFACE_RECEIPT_SCHEMA_VALIDATION_FAILED", exc.message
                ) from exc
    return data
