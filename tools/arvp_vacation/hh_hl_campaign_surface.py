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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from core.replay.canonical_json import canonical_hash, sha256_hex

SURFACE_RECEIPT_SCHEMA_VERSION = "cdb.hh_hl_campaign_surface_receipt.v1"
ALLOWED_EXECUTION_SURFACE_ID = "services.validation.strategy_replay_runner.single_run"

# Deterministic probe-code identity. Bump only when the probe contract changes.
PROBE_CODE_CONTRACT_VERSION = "cdb.hh_hl_campaign_surface_probe.v1"
PROBE_CODE_SHA = sha256_hex(PROBE_CODE_CONTRACT_VERSION.encode("utf-8"))

HH_HL_STRATEGY_ID = "hh_hl_continuation_v1"
HH_HL_ADAPTER_ID = "batch_b_shadow_runner_v1"
EXPECTED_RUN_COUNT = 39

# Final-binding + physical-eligibility HOLD reason codes. Any of these keeps a
# surface receipt from backing an Owner Execution-GO package (fail-closed).
HOLD_SURFACE_BINDING_MISMATCH = "HOLD_EXECUTION_SURFACE_BINDING_MISMATCH"
HOLD_SURFACE_DATASET_ROOT_REQUIRED = "HOLD_EXECUTION_SURFACE_DATASET_ROOT_REQUIRED"
HOLD_DATASET_SURFACE_PROOF_REQUIRED = "HOLD_EXECUTION_DATASET_SURFACE_PROOF_REQUIRED"
HOLD_RESOURCE_BUDGET_INVALID = "HOLD_EXECUTION_RESOURCE_BUDGET_INVALID"
HOLD_PROBE_CODE_MISMATCH = "HOLD_SURFACE_RECEIPT_PROBE_CODE_MISMATCH"

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


def measure_free_disk_bytes(repo_root: Path | None = None) -> int:
    """Public free-disk probe for the physical eligibility gate."""
    return _free_disk_bytes(repo_root)


@dataclass(frozen=True)
class PhysicalDatasetProof:
    """Result of the physical local dataset proof for owner-go eligibility."""

    passed: bool
    content_fingerprint_digest: str
    window_count: int
    free_disk_bytes: int
    detail: str = ""


# Injectable physical-proof surface: unit tests without a real window bank pass a
# callable returning a PASS/FAIL :class:`PhysicalDatasetProof`; production resolves
# a real bank root and physically fingerprints the locked 39 windows.
PhysicalProofFn = Callable[[], PhysicalDatasetProof]


def assert_physical_local_eligibility(
    *,
    dataset_root: Path | None,
    expected_content_digest: str,
    resource_budget: Mapping[str, Any],
    free_disk_bytes: int | None = None,
    repo_root: Path | None = None,
    physical_proof_fn: PhysicalProofFn | None = None,
) -> PhysicalDatasetProof:
    """Fail-closed physical eligibility gate for a non-fixture owner-go probe.

    Verifies, in order: sufficient free disk against the resource budget, then a
    physical dataset proof (all locked windows present, recomputed content digest
    equal to ``expected_content_digest``). Never starts a replay and never writes
    a campaign artifact. Returns a passing :class:`PhysicalDatasetProof`; raises
    :class:`HhHlSurfaceReceiptError` with the exact HOLD code on any failure.

    Tests inject ``physical_proof_fn`` (and/or ``free_disk_bytes``) so no real
    window bank is required; production resolves a real ``dataset_root``.
    """
    disk = (
        int(free_disk_bytes)
        if free_disk_bytes is not None
        else _free_disk_bytes(repo_root)
    )
    min_disk = int((resource_budget or {}).get("minimum_free_disk_bytes") or 0)
    if disk < min_disk:
        raise HhHlSurfaceReceiptError(
            HOLD_RESOURCE_BUDGET_INVALID,
            f"free_disk_bytes={disk} < minimum_free_disk_bytes={min_disk}",
        )

    expected = str(expected_content_digest or "")
    if not _SHA64_RE.fullmatch(expected):
        raise HhHlSurfaceReceiptError(
            HOLD_DATASET_SURFACE_PROOF_REQUIRED,
            f"expected content digest not 64-hex: {expected!r}",
        )

    if physical_proof_fn is not None:
        proof = physical_proof_fn()
        if not isinstance(proof, PhysicalDatasetProof):
            raise HhHlSurfaceReceiptError(
                HOLD_DATASET_SURFACE_PROOF_REQUIRED, "physical_proof_fn bad result"
            )
        proof = PhysicalDatasetProof(
            passed=bool(proof.passed),
            content_fingerprint_digest=str(proof.content_fingerprint_digest or ""),
            window_count=int(proof.window_count),
            free_disk_bytes=int(disk),
            detail=str(proof.detail or ""),
        )
    else:
        if dataset_root is None:
            raise HhHlSurfaceReceiptError(
                HOLD_SURFACE_DATASET_ROOT_REQUIRED,
                "non-fixture owner-go probe requires a local dataset root",
            )
        # Lazy import: keep the receipt builder free of the dataset/bank surface.
        from tools.arvp_vacation.hh_hl_campaign_dataset import (
            DATASET_STATUS_PASS,
            HhHlDatasetBindingError,
            prove_local_dataset,
        )

        try:
            receipt = prove_local_dataset(Path(dataset_root), repo_root=repo_root)
        except HhHlDatasetBindingError as exc:
            raise HhHlSurfaceReceiptError(
                HOLD_DATASET_SURFACE_PROOF_REQUIRED, str(exc)
            ) from exc
        proof = PhysicalDatasetProof(
            passed=(receipt.quality_gate_status == DATASET_STATUS_PASS),
            content_fingerprint_digest=str(receipt.content_fingerprint_digest or ""),
            window_count=int(receipt.window_count),
            free_disk_bytes=int(disk),
        )

    if not proof.passed:
        raise HhHlSurfaceReceiptError(
            HOLD_DATASET_SURFACE_PROOF_REQUIRED,
            proof.detail or "physical dataset proof not PASS",
        )
    if proof.content_fingerprint_digest != expected:
        raise HhHlSurfaceReceiptError(
            HOLD_DATASET_SURFACE_PROOF_REQUIRED,
            f"content digest drift: {proof.content_fingerprint_digest} != {expected}",
        )
    if int(proof.window_count) != EXPECTED_RUN_COUNT:
        raise HhHlSurfaceReceiptError(
            HOLD_DATASET_SURFACE_PROOF_REQUIRED,
            f"window_count={proof.window_count} != {EXPECTED_RUN_COUNT}",
        )
    return proof


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
    pre_final: bool = False,
    physical_dataset_proof_passed: bool | None = None,
    probed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a full, fingerprint-bound surface receipt (never authorizes runs).

    Owner-go eligibility is fail-closed: a fixture, a ``pre_final`` (PRE_FINAL)
    plan, an unloadable run plan, an unreachable provider, or a missing/failed
    physical dataset proof all force ``owner_go_package_eligible=False``. A
    non-fixture FINAL receipt is only eligible when ``physical_dataset_proof_passed``
    is explicitly ``True``.
    """
    if execution_surface_id != ALLOWED_EXECUTION_SURFACE_ID:
        raise HhHlSurfaceReceiptError(
            "HOLD_SURFACE_RECEIPT_SURFACE_ID_INVALID", str(execution_surface_id)
        )
    fixture = bool(fixture)
    pre_final = bool(pre_final)
    reachable = (
        bool(single_run_provider_reachable)
        and bool(reproduction_provider_reachable)
        and bool(analyzer_provider_reachable)
    )
    if owner_go_package_eligible is None:
        owner_go_package_eligible = (
            (not fixture)
            and (not pre_final)
            and bool(run_plan_loadable)
            and reachable
            and (physical_dataset_proof_passed is True)
        )
    # Fail-closed overrides: caller-supplied eligible=True cannot bypass fixture,
    # PRE_FINAL, or a missing/failed physical dataset proof.
    if fixture or pre_final:
        owner_go_package_eligible = False
    if physical_dataset_proof_passed is not True:
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
    pre_final: bool = False,
    physical_dataset_proof_passed: bool | None = None,
    probe_code_sha: str | None = None,
    probed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Probe the single-run surface and emit a consumable receipt (no replays).

    ``pre_final`` and ``physical_dataset_proof_passed`` gate owner-go
    eligibility (see :func:`build_surface_receipt`): a non-fixture FINAL probe is
    only eligible when the physical dataset proof passed.
    """
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
        pre_final=pre_final,
        physical_dataset_proof_passed=physical_dataset_proof_passed,
        probe_code_sha=probe_code_sha,
        probed_at_utc=probed_at_utc,
    )


def assert_surface_receipt_binds_final(
    receipt: Mapping[str, Any],
    *,
    planning_sha: str,
    manifest: Mapping[str, Any],
    plan: Any,
) -> None:
    """Exact-match a loaded surface receipt to the FINAL plan + final manifest.

    Every binding must match exactly and no bound identifier may be empty. Any
    divergence raises ``HhHlSurfaceReceiptError(HOLD_EXECUTION_SURFACE_BINDING_MISMATCH,
    detail=<field>)`` so a receipt built against a foreign plan, manifest, or
    dataset can never back an Owner Execution-GO package. ``plan`` is the FINAL
    :class:`HhHlFinalRunPlan` built for the same ``planning_sha``.
    """
    dataset_binding = dict(manifest.get("dataset_binding") or {})
    resource_budget = dict(manifest.get("resource_budget_contract") or {})
    manifest_fp = str(manifest.get("manifest_fingerprint") or "")
    plan_planning = str(getattr(plan, "planning_sha", "") or "")
    plan_manifest_fp = str(getattr(plan, "manifest_fingerprint", "") or "")
    plan_rpf = str(getattr(plan, "run_plan_fingerprint", "") or "")

    def _need(field: str, got: Any, expected: Any) -> None:
        if isinstance(expected, str) and expected == "":
            raise HhHlSurfaceReceiptError(
                HOLD_SURFACE_BINDING_MISMATCH, f"{field}:empty-expected"
            )
        if isinstance(got, str) and got == "":
            raise HhHlSurfaceReceiptError(
                HOLD_SURFACE_BINDING_MISMATCH, f"{field}:empty"
            )
        if got != expected:
            raise HhHlSurfaceReceiptError(HOLD_SURFACE_BINDING_MISMATCH, field)

    ps = str(planning_sha or "")
    _need("planning_sha", str(receipt.get("planning_sha") or ""), ps)
    _need("planning_sha_plan", plan_planning, ps)

    _need(
        "manifest_fingerprint",
        str(receipt.get("manifest_fingerprint") or ""),
        manifest_fp,
    )
    _need("manifest_fingerprint_plan", plan_manifest_fp, manifest_fp)

    _need(
        "run_plan_fingerprint", str(receipt.get("run_plan_fingerprint") or ""), plan_rpf
    )

    _need(
        "dataset_selection_sha256",
        str(receipt.get("dataset_selection_sha256") or ""),
        str(dataset_binding.get("selection_sha256") or ""),
    )
    _need(
        "dataset_content_fingerprint_digest",
        str(receipt.get("dataset_content_fingerprint_digest") or ""),
        str(dataset_binding.get("content_fingerprint_digest") or ""),
    )

    _need("strategy_id", str(receipt.get("strategy_id") or ""), HH_HL_STRATEGY_ID)
    _need("adapter_id", str(receipt.get("adapter_id") or ""), HH_HL_ADAPTER_ID)

    if int(receipt.get("expected_run_count") or 0) != EXPECTED_RUN_COUNT:
        raise HhHlSurfaceReceiptError(
            HOLD_SURFACE_BINDING_MISMATCH, "expected_run_count"
        )

    if not resource_budget:
        raise HhHlSurfaceReceiptError(
            HOLD_SURFACE_BINDING_MISMATCH, "resource_budget:empty-expected"
        )
    if dict(receipt.get("resource_budget") or {}) != resource_budget:
        raise HhHlSurfaceReceiptError(HOLD_SURFACE_BINDING_MISMATCH, "resource_budget")

    _need(
        "execution_surface_id",
        str(receipt.get("execution_surface_id") or ""),
        ALLOWED_EXECUTION_SURFACE_ID,
    )
    _need("probe_code_sha", str(receipt.get("probe_code_sha") or ""), PROBE_CODE_SHA)

    if receipt.get("owner_go_package_eligible") is not True:
        raise HhHlSurfaceReceiptError(
            HOLD_SURFACE_BINDING_MISMATCH, "owner_go_package_eligible"
        )
    if receipt.get("fixture") is not False:
        raise HhHlSurfaceReceiptError(HOLD_SURFACE_BINDING_MISMATCH, "fixture")
    if receipt.get("replays") is not False:
        raise HhHlSurfaceReceiptError(HOLD_SURFACE_BINDING_MISMATCH, "replays")
    if receipt.get("campaign_artifacts_written") is not False:
        raise HhHlSurfaceReceiptError(
            HOLD_SURFACE_BINDING_MISMATCH, "campaign_artifacts_written"
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
    # A receipt that claims owner-go eligibility must carry the canonical probe
    # code identity: a manipulated probe_code_sha can never back a package.
    if eligible and str(data.get("probe_code_sha") or "") != PROBE_CODE_SHA:
        raise HhHlSurfaceReceiptError(
            HOLD_PROBE_CODE_MISMATCH,
            f"probe_code_sha={data.get('probe_code_sha')!r} != {PROBE_CODE_SHA}",
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
        if str(data.get("probe_code_sha") or "") != PROBE_CODE_SHA:
            raise HhHlSurfaceReceiptError(
                HOLD_PROBE_CODE_MISMATCH,
                f"probe_code_sha={data.get('probe_code_sha')!r} != {PROBE_CODE_SHA}",
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
