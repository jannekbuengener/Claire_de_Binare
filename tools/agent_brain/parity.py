"""Dual-run parity harness for Claire legacy vs Agent Brain consumer (#18).

Same controlled fixtures feed both paths. Outputs are normalized, compared,
and classified. ``UNACCEPTED_DELTA`` fails the harness.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from tools.agent_brain.adapter import AgentBrainAdapter, ConsumerResult
from tools.agent_brain.legacy import LegacyContextPath
from tools.agent_brain.pin import PINNED_AGENT_BRAIN_VERSION

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ACCEPTED_DELTAS_PATH = (
    REPO_ROOT / "docs" / "evidence" / "agent_brain_slice18_accepted_deltas.v1.json"
)


class ParityClass(StrEnum):
    EXACT_PARITY = "EXACT_PARITY"
    SEMANTIC_PARITY = "SEMANTIC_PARITY"
    ACCEPTED_CONTRACT_CHANGE = "ACCEPTED_CONTRACT_CHANGE"
    LEGACY_BUG_FIXED = "LEGACY_BUG_FIXED"
    UNACCEPTED_DELTA = "UNACCEPTED_DELTA"
    UNCOMPARABLE = "UNCOMPARABLE"


# Envelope / implementation fields that are path-specific by design.
_PATH_ONLY_FIELDS = frozenset(
    {
        "path",
        "agent_brain_version",
        "limitations",
        "legacy_owner",
        "mode",
    }
)

# Contract renames documented as ACCEPTED_CONTRACT_CHANGE (legacy → agent_brain).
_FIELD_ALIASES: dict[str, str] = {
    "evidence_links": "evidence_refs",
    "decision_replay_links": "decision_refs",
}

_LIMITATION_ALIASES: dict[str, str] = {
    "evidence_links_not_provided": "evidence_refs_not_provided",
    "decision_replay_links_not_provided": "decision_refs_not_provided",
}


@dataclass(frozen=True, slots=True)
class FieldDelta:
    field: str
    legacy_value: Any
    agent_brain_value: Any
    parity_class: ParityClass
    reason: str
    contract_ref: str | None = None
    risk: str = "none"


@dataclass(frozen=True, slots=True)
class DualRunCase:
    case_id: str
    target_scope: str
    summary: str
    legacy_artifacts: list[dict[str, Any]]
    agent_brain_artifacts: list[dict[str, Any]]
    generated_at_or_as_of: str = "2026-10-31T12:00:00Z"
    expect_ok: bool = True
    tags: tuple[str, ...] = ()


@dataclass
class DualRunResult:
    case_id: str
    legacy: ConsumerResult
    agent_brain: ConsumerResult
    deltas: list[FieldDelta] = field(default_factory=list)
    comparable_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def worst_class(self) -> ParityClass:
        priority = {
            ParityClass.UNACCEPTED_DELTA: 5,
            ParityClass.UNCOMPARABLE: 4,
            ParityClass.LEGACY_BUG_FIXED: 3,
            ParityClass.ACCEPTED_CONTRACT_CHANGE: 2,
            ParityClass.SEMANTIC_PARITY: 1,
            ParityClass.EXACT_PARITY: 0,
        }
        if not self.deltas:
            return ParityClass.EXACT_PARITY
        return max(self.deltas, key=lambda d: priority[d.parity_class]).parity_class

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "worst_class": self.worst_class.value,
            "legacy": self.legacy.to_dict(),
            "agent_brain": self.agent_brain.to_dict(),
            "deltas": [
                {
                    "field": d.field,
                    "legacy_value": d.legacy_value,
                    "agent_brain_value": d.agent_brain_value,
                    "parity_class": d.parity_class.value,
                    "reason": d.reason,
                    "contract_ref": d.contract_ref,
                    "risk": d.risk,
                }
                for d in self.deltas
            ],
            "comparable_fields": self.comparable_fields,
        }


@dataclass
class DualRunReport:
    results: list[DualRunResult]
    accepted_delta_catalog: list[dict[str, Any]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        tallies = {item.value: 0 for item in ParityClass}
        for result in self.results:
            for delta in result.deltas or [
                FieldDelta(
                    field="__case__",
                    legacy_value=None,
                    agent_brain_value=None,
                    parity_class=ParityClass.EXACT_PARITY,
                    reason="no deltas",
                )
            ]:
                tallies[delta.parity_class.value] += 1
        return tallies

    @property
    def unaccepted(self) -> int:
        return sum(
            1
            for result in self.results
            for delta in result.deltas
            if delta.parity_class is ParityClass.UNACCEPTED_DELTA
        )

    @property
    def uncomparable_mandatory(self) -> int:
        return sum(
            1
            for result in self.results
            for delta in result.deltas
            if delta.parity_class is ParityClass.UNCOMPARABLE
        )

    def passed(self) -> bool:
        return self.unaccepted == 0 and self.uncomparable_mandatory == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed(),
            "counts": self.counts(),
            "unaccepted_delta": self.unaccepted,
            "uncomparable": self.uncomparable_mandatory,
            "results": [item.to_dict() for item in self.results],
        }


def load_accepted_delta_catalog(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    catalog_path = path or DEFAULT_ACCEPTED_DELTAS_PATH
    if not catalog_path.is_file():
        return []
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = payload.get("accepted_deltas") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("accepted deltas catalog must be a list")
    return [dict(item) for item in items if isinstance(item, Mapping)]


def _normalize_limitations(raw: object) -> list[str]:
    if raw is None:
        return []
    values = list(raw) if isinstance(raw, (list, tuple)) else [raw]
    mapped: list[str] = []
    for item in values:
        text = str(item)
        mapped.append(_LIMITATION_ALIASES.get(text, text))
    return sorted(set(mapped))


def extract_package(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    package = data.get("package")
    if isinstance(package, Mapping):
        return dict(package)
    return None


def normalize_package_for_compare(package: Mapping[str, Any]) -> dict[str, Any]:
    """Project package onto contract-comparable fields.

    Drops path-only noise (package_id / content_hash differ under accepted
    artifact-shape contract change) while keeping authoritative semantics.
    """
    out: dict[str, Any] = {
        "schema_version": package.get("schema_version"),
        "target_scope": package.get("target_scope"),
        "source_priority": list(package.get("source_priority") or []),
        "artifact_count": int(
            (package.get("determinism") or {}).get("artifact_count")
            or len(package.get("artifacts") or [])
        ),
        "hash_algorithm": (package.get("determinism") or {}).get("hash_algorithm"),
        "wall_clock_excluded": (package.get("determinism") or {}).get(
            "wall_clock_excluded"
        ),
        "limitations": _normalize_limitations(package.get("limitations")),
        # package.guardrails compared separately: legacy embeds Claire defaults;
        # Agent Brain keeps the package product-neutral (policy on claire_policy).
        "artifacts_semantic": _artifacts_semantic(package.get("artifacts") or []),
        "has_ranked_context": package.get("ranked_context") is not None,
    }
    # Normalize evidence / decision identities under alias map.
    evidence = package.get("evidence_refs")
    if evidence is None:
        evidence = package.get("evidence_links")
    decisions = package.get("decision_refs")
    if decisions is None:
        decisions = package.get("decision_replay_links")
    out["evidence_refs"] = _ref_identities(evidence or [])
    out["decision_refs"] = _ref_identities(decisions or [])
    return out


def _artifact_id(item: Mapping[str, Any]) -> str | None:
    ref = item.get("ref")
    if isinstance(ref, Mapping) and ref.get("artifact_id"):
        return str(ref["artifact_id"])
    if item.get("artifact_id"):
        return str(item["artifact_id"])
    if item.get("id"):
        return str(item["id"])
    return None


def _artifact_source_path(item: Mapping[str, Any]) -> str | None:
    ref = item.get("ref")
    if isinstance(ref, Mapping) and ref.get("source_path"):
        return str(ref["source_path"])
    if item.get("source_path"):
        return str(item["source_path"])
    return None


def _artifacts_semantic(
    artifacts: Sequence[Mapping[str, Any] | Any],
) -> list[dict[str, str]]:
    """Preserve per-artifact associations (id↔type↔summary↔path)."""
    records: list[dict[str, str]] = []
    for item in artifacts:
        if not isinstance(item, Mapping):
            continue
        artifact_id = _artifact_id(item)
        if not artifact_id:
            continue
        records.append(
            {
                "artifact_id": artifact_id,
                "artifact_type": str(
                    item.get("artifact_type") or item.get("type") or ""
                ),
                "summary": str(item.get("summary") or "").strip(),
                "source_path": str(_artifact_source_path(item) or ""),
            }
        )
    return sorted(records, key=lambda row: row["artifact_id"])


def _ref_identities(refs: Sequence[Any]) -> list[str]:
    """Extract stable identities from evidence/decision refs across wire shapes."""
    identities: list[str] = []
    for item in refs:
        if isinstance(item, Mapping):
            for key in (
                "evidence_id",
                "evidence_ref",
                "ref",
                "id",
                "decision_id",
                "decision_ref",
                "replay_id",
            ):
                value = item.get(key)
                if value is not None and str(value).strip():
                    identities.append(str(value).strip())
                    break
            else:
                identities.append(json.dumps(item, sort_keys=True, default=str))
        elif item is not None and str(item).strip():
            identities.append(str(item).strip())
    return sorted(identities)


def normalize_policy(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    policy = data.get("claire_policy")
    if not isinstance(policy, Mapping):
        return None
    return {
        "policy_owner": policy.get("policy_owner"),
        "live_or_echtgeld": policy.get("live_or_echtgeld"),
        "memory_writes": policy.get("memory_writes"),
        "target_scope": policy.get("target_scope"),
        "guardrails": sorted(str(item) for item in (policy.get("guardrails") or [])),
    }


def compare_context_results(
    *,
    case_id: str,
    legacy: ConsumerResult,
    agent_brain: ConsumerResult,
    accepted_catalog: Sequence[Mapping[str, Any]] | None = None,
) -> DualRunResult:
    deltas: list[FieldDelta] = []
    catalog = list(accepted_catalog or [])

    if legacy.ok != agent_brain.ok:
        deltas.append(
            _classify_or_unaccepted(
                field="ok",
                legacy_value=legacy.ok,
                agent_brain_value=agent_brain.ok,
                catalog=catalog,
                default_reason="success/failure divergence between paths",
            )
        )

    if not legacy.ok and not agent_brain.ok:
        leg_code = (legacy.error or {}).get("code")
        ab_code = (agent_brain.error or {}).get("code")
        if leg_code == ab_code:
            deltas.append(
                FieldDelta(
                    field="error.code",
                    legacy_value=leg_code,
                    agent_brain_value=ab_code,
                    parity_class=ParityClass.EXACT_PARITY,
                    reason="identical failure codes",
                )
            )
        else:
            deltas.append(
                _classify_or_unaccepted(
                    field="error.code",
                    legacy_value=leg_code,
                    agent_brain_value=ab_code,
                    catalog=catalog,
                    default_reason="failure code mismatch",
                )
            )
        return DualRunResult(
            case_id=case_id, legacy=legacy, agent_brain=agent_brain, deltas=deltas
        )

    leg_pkg = extract_package(legacy.data)
    ab_pkg = extract_package(agent_brain.data)
    if leg_pkg is None or ab_pkg is None:
        deltas.append(
            FieldDelta(
                field="package",
                legacy_value=leg_pkg is not None,
                agent_brain_value=ab_pkg is not None,
                parity_class=ParityClass.UNCOMPARABLE,
                reason="one or both paths missing package payload",
                risk="high",
            )
        )
        return DualRunResult(
            case_id=case_id, legacy=legacy, agent_brain=agent_brain, deltas=deltas
        )

    leg_norm = normalize_package_for_compare(leg_pkg)
    ab_norm = normalize_package_for_compare(ab_pkg)
    comparable = {"legacy": leg_norm, "agent_brain": ab_norm}
    leg_policy = normalize_policy(legacy.data)
    ab_policy = normalize_policy(agent_brain.data)

    for key in sorted(set(leg_norm) | set(ab_norm)):
        lv = leg_norm.get(key)
        av = ab_norm.get(key)
        if lv == av:
            deltas.append(
                FieldDelta(
                    field=f"package.{key}",
                    legacy_value=lv,
                    agent_brain_value=av,
                    parity_class=ParityClass.EXACT_PARITY,
                    reason="equal after normalization",
                )
            )
        else:
            deltas.append(
                _classify_or_unaccepted(
                    field=f"package.{key}",
                    legacy_value=lv,
                    agent_brain_value=av,
                    catalog=catalog,
                    default_reason="normalized package field mismatch",
                )
            )

    # Artifact wire-shape difference is an accepted contract change (#13/#15).
    if (leg_pkg.get("artifacts") or []) and (ab_pkg.get("artifacts") or []):
        leg_shape = (
            "flat" if "artifact_id" in (leg_pkg["artifacts"][0] or {}) else "ref"
        )
        ab_shape = "ref" if "ref" in (ab_pkg["artifacts"][0] or {}) else "flat"
        if leg_shape != ab_shape:
            deltas.append(
                FieldDelta(
                    field="package.artifact_wire_shape",
                    legacy_value=leg_shape,
                    agent_brain_value=ab_shape,
                    parity_class=ParityClass.ACCEPTED_CONTRACT_CHANGE,
                    reason="Agent Brain uses ArtifactRef; legacy uses flat artifact_id",
                    contract_ref="artifact-ref/v1 + consumer cutover #13",
                    risk="low",
                )
            )

    leg_guards = list(leg_pkg.get("guardrails") or [])
    ab_guards = list(ab_pkg.get("guardrails") or [])
    if leg_guards != ab_guards:
        # Safety remains on claire_policy for both paths after #13.
        policy_ok = bool(leg_policy and ab_policy and leg_policy == ab_policy)
        deltas.append(
            FieldDelta(
                field="package.guardrails",
                legacy_value=leg_guards,
                agent_brain_value=ab_guards,
                parity_class=(
                    ParityClass.ACCEPTED_CONTRACT_CHANGE
                    if policy_ok
                    else ParityClass.UNACCEPTED_DELTA
                ),
                reason=(
                    "Legacy embeds Claire default guardrails in package; "
                    "Agent Brain keeps package neutral and Claire attaches "
                    "claire_policy.guardrails"
                    if policy_ok
                    else "package guardrails diverge without claire_policy parity"
                ),
                contract_ref="agent-brain context package neutrality + Claire policy",
                risk="low" if policy_ok else "high",
            )
        )
    else:
        deltas.append(
            FieldDelta(
                field="package.guardrails",
                legacy_value=leg_guards,
                agent_brain_value=ab_guards,
                parity_class=ParityClass.EXACT_PARITY,
                reason="package guardrails equal",
            )
        )

    # Evidence / decision field rename.
    for legacy_name, new_name in _FIELD_ALIASES.items():
        if legacy_name in leg_pkg or new_name in ab_pkg:
            deltas.append(
                FieldDelta(
                    field=f"package.field_alias.{legacy_name}->{new_name}",
                    legacy_value=legacy_name in leg_pkg,
                    agent_brain_value=new_name in ab_pkg,
                    parity_class=ParityClass.ACCEPTED_CONTRACT_CHANGE,
                    reason="canonical Agent Brain contract rename",
                    contract_ref="context-package/v2 (agent-brain)",
                    risk="low",
                )
            )

    if leg_policy != ab_policy:
        deltas.append(
            _classify_or_unaccepted(
                field="claire_policy",
                legacy_value=leg_policy,
                agent_brain_value=ab_policy,
                catalog=catalog,
                default_reason="Claire policy envelope mismatch",
            )
        )
    else:
        deltas.append(
            FieldDelta(
                field="claire_policy",
                legacy_value=leg_policy,
                agent_brain_value=ab_policy,
                parity_class=ParityClass.EXACT_PARITY,
                reason="Claire policy envelope equal",
            )
        )

    # Path-only fields recorded as semantic / accepted, never as failures.
    if legacy.path != agent_brain.path:
        deltas.append(
            FieldDelta(
                field="path",
                legacy_value=legacy.path,
                agent_brain_value=agent_brain.path,
                parity_class=ParityClass.SEMANTIC_PARITY,
                reason="path label identifies which consumer ran",
                risk="none",
            )
        )
    if agent_brain.agent_brain_version != PINNED_AGENT_BRAIN_VERSION:
        deltas.append(
            FieldDelta(
                field="agent_brain_version",
                legacy_value=legacy.agent_brain_version,
                agent_brain_value=agent_brain.agent_brain_version,
                parity_class=ParityClass.UNACCEPTED_DELTA,
                reason="agent brain path must report pinned version",
                risk="high",
            )
        )
    else:
        deltas.append(
            FieldDelta(
                field="agent_brain_version",
                legacy_value=legacy.agent_brain_version,
                agent_brain_value=agent_brain.agent_brain_version,
                parity_class=ParityClass.ACCEPTED_CONTRACT_CHANGE,
                reason="legacy has no package pin; agent_brain reports pinned version",
                contract_ref="consumer_cutover.v1 / #17",
                risk="none",
            )
        )

    return DualRunResult(
        case_id=case_id,
        legacy=legacy,
        agent_brain=agent_brain,
        deltas=deltas,
        comparable_fields=comparable,
    )


def _classify_or_unaccepted(
    *,
    field: str,
    legacy_value: Any,
    agent_brain_value: Any,
    catalog: Sequence[Mapping[str, Any]],
    default_reason: str,
) -> FieldDelta:
    for item in catalog:
        if str(item.get("field")) != field:
            continue
        parity = ParityClass(str(item.get("parity_class")))
        if parity is ParityClass.UNACCEPTED_DELTA:
            continue
        return FieldDelta(
            field=field,
            legacy_value=legacy_value,
            agent_brain_value=agent_brain_value,
            parity_class=parity,
            reason=str(item.get("reason") or default_reason),
            contract_ref=(
                str(item["contract_ref"]) if item.get("contract_ref") else None
            ),
            risk=str(item.get("risk") or "low"),
        )
    return FieldDelta(
        field=field,
        legacy_value=legacy_value,
        agent_brain_value=agent_brain_value,
        parity_class=ParityClass.UNACCEPTED_DELTA,
        reason=default_reason,
        risk="high",
    )


def run_dual_context_case(
    case: DualRunCase,
    *,
    legacy: LegacyContextPath | None = None,
    adapter: AgentBrainAdapter | None = None,
    accepted_catalog: Sequence[Mapping[str, Any]] | None = None,
) -> DualRunResult:
    legacy_path = legacy or LegacyContextPath()
    brain = adapter or AgentBrainAdapter()
    legacy_result = legacy_path.context_read(
        target_scope=case.target_scope,
        artifacts=case.legacy_artifacts,
        tags=list(case.tags),
        generated_at_or_as_of=case.generated_at_or_as_of,
    )
    brain_result = brain.context_read(
        target_scope=case.target_scope,
        artifacts=case.agent_brain_artifacts,
        tags=list(case.tags),
        generated_at_or_as_of=case.generated_at_or_as_of,
    )
    compared = compare_context_results(
        case_id=case.case_id,
        legacy=legacy_result,
        agent_brain=brain_result,
        accepted_catalog=accepted_catalog,
    )
    if case.expect_ok and (not legacy_result.ok or not brain_result.ok):
        compared.deltas.append(
            FieldDelta(
                field="expect_ok",
                legacy_value=legacy_result.ok,
                agent_brain_value=brain_result.ok,
                parity_class=ParityClass.UNACCEPTED_DELTA,
                reason=(
                    "case expects successful context on both paths; "
                    "shared or single-path failure must not pass parity"
                ),
                risk="high",
            )
        )
    return compared


def run_dual_suite(
    cases: Sequence[DualRunCase],
    *,
    legacy: LegacyContextPath | None = None,
    adapter: AgentBrainAdapter | None = None,
    accepted_catalog: Sequence[Mapping[str, Any]] | None = None,
) -> DualRunReport:
    catalog = (
        list(accepted_catalog)
        if accepted_catalog is not None
        else load_accepted_delta_catalog()
    )
    results = [
        run_dual_context_case(
            case,
            legacy=legacy,
            adapter=adapter,
            accepted_catalog=catalog,
        )
        for case in cases
    ]
    return DualRunReport(results=results, accepted_delta_catalog=list(catalog))


def assert_parity_pass(report: DualRunReport) -> None:
    if report.passed():
        return
    failed = [
        delta
        for result in report.results
        for delta in result.deltas
        if delta.parity_class
        in {ParityClass.UNACCEPTED_DELTA, ParityClass.UNCOMPARABLE}
    ]
    details = "; ".join(
        f"{d.field}:{d.parity_class.value}:{d.reason}" for d in failed[:12]
    )
    raise AssertionError(
        f"parity harness failed unaccepted={report.unaccepted} "
        f"uncomparable={report.uncomparable_mandatory}: {details}"
    )


# Keep unused import surface stable for type checkers / future failure dual-run.
InvokeFn = Callable[..., Any]

__all__ = [
    "DEFAULT_ACCEPTED_DELTAS_PATH",
    "DualRunCase",
    "DualRunReport",
    "DualRunResult",
    "FieldDelta",
    "ParityClass",
    "assert_parity_pass",
    "compare_context_results",
    "extract_package",
    "load_accepted_delta_catalog",
    "normalize_package_for_compare",
    "normalize_policy",
    "run_dual_context_case",
    "run_dual_suite",
]
