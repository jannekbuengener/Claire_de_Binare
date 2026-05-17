"""Impact Radar v1 — deterministic impact analysis for planned changes.

Issues:
    #2019 — Define impact radar v1 model
    #2108 — Implement impact radar v1
    Parent: #2103 (Wave-13)
    Epic: #1976

This module implements a minimal, deterministic, fail-closed Impact Radar.
It analyses which artifacts, symbols, tests, docs, decisions, evidence,
and memory refs are affected by a planned change, derives an impact level,
distinguishes hard vs soft impact, surfaces gate risks, and propagates
stop conditions.

Design intent:
    Pure domain logic. No DB access. No MCP. No networking. No file I/O.
    Input: target paths/symbols + dependency edges + artifact/symbol data.
    Output: typed ImpactReport with level, type, confidence, gate risks,
            required validation, and stop conditions.
    Deterministic: same inputs → same outputs.
    Fail-closed: blocking if governance/risk/execution/secrets touched.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

SCHEMA_VERSION = "1.0.0"

# ── Impact level thresholds ─────────────────────────────────────────────────

_BLOCKING_DIRS: tuple[str, ...] = (
    "knowledge/governance/",
    "services/risk/",
    "services/execution/",
    "secrets/",
    "tresor/",
)

_HIGH_DIRS: tuple[str, ...] = (
    "services/",
    "infrastructure/",
    "core/contracts/",
    "docs/contracts/",
    "docs/live-readiness/",
    "knowledge/runbooks/",
)

_MEDIUM_DIRS: tuple[str, ...] = (
    "core/",
    "tools/",
    "tests/",
    "scripts/",
    "infrastructure/config/",
    "knowledge/contracts/",
)

_HARD_DIRS: tuple[str, ...] = (
    "core/",
    "services/",
    "infrastructure/",
    "tools/",
    "scripts/",
)

_GATE_RISK_MAP: dict[tuple[str, ...], str] = {
    ("knowledge/governance/",): "governance_touched",
    ("services/risk/",): "risk_surface_touched",
    ("services/execution/",): "execution_surface_touched",
    ("docs/contracts/", "core/contracts/"): "contract_drift_possible",
    ("secrets/", "tresor/"): "secrets_surface_touched",
    ("docs/live-readiness/",): "lr_surface_touched",
}

# ── Decision / evidence anchor directories ───────────────────────────────────

_DECISION_DIRS: tuple[str, ...] = (
    "knowledge/agent_trust/ledger/",
    "knowledge/governance/",
)

_EVIDENCE_DIRS: tuple[str, ...] = (
    "docs/evidence/",
    "docs/live-readiness/",
    "reports/",
    "docs/runbooks/evidence/",
)

_MEMORY_DIRS: tuple[str, ...] = (
    "knowledge/logs/",
    "knowledge/agent_trust/",
)


# ── Input / Output types ────────────────────────────────────────────────────

@dataclass(frozen=True)
class ImpactRadarInput:
    """Deterministic input for impact analysis."""

    target_paths: tuple[str, ...] = ()
    target_symbols: tuple[str, ...] = ()
    target_issue: str | None = None
    target_concepts: tuple[str, ...] = ()
    operation_mode: str = "read_only"
    dependency_edges: tuple[dict[str, Any], ...] = ()
    code_symbols: tuple[dict[str, Any], ...] = ()
    test_cases: tuple[dict[str, Any], ...] = ()
    artifacts: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ImpactReport:
    """Deterministic impact report."""

    impact_id: str
    target_refs: tuple[str, ...]
    impact_level: str
    impact_type: str
    affected_artifacts: tuple[dict[str, Any], ...]
    affected_symbols: tuple[dict[str, Any], ...]
    affected_tests: tuple[dict[str, Any], ...]
    affected_docs: tuple[dict[str, Any], ...]
    affected_decisions: tuple[str, ...]
    affected_evidence: tuple[str, ...]
    affected_memory_refs_read_only: tuple[str, ...]
    graph_paths: tuple[tuple[str, ...], ...]
    gate_risks: tuple[str, ...]
    confidence: str
    required_validation: dict[str, Any] = field(
        hash=False, compare=False
    )
    stop_conditions: tuple[dict[str, Any], ...] = field(
        hash=False, compare=False
    )
    schema_version: str = SCHEMA_VERSION

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "impact_id": self.impact_id,
            "target_refs": list(self.target_refs),
            "impact_level": self.impact_level,
            "impact_type": self.impact_type,
            "affected_artifacts": list(self.affected_artifacts),
            "affected_symbols": list(self.affected_symbols),
            "affected_tests": list(self.affected_tests),
            "affected_docs": list(self.affected_docs),
            "affected_decisions": list(self.affected_decisions),
            "affected_evidence": list(self.affected_evidence),
            "affected_memory_refs_read_only": list(
                self.affected_memory_refs_read_only
            ),
            "graph_paths": [list(p) for p in self.graph_paths],
            "gate_risks": list(self.gate_risks),
            "confidence": self.confidence,
            "required_validation": self.required_validation,
            "stop_conditions": list(self.stop_conditions),
        }


# ── Helpers ─────────────────────────────────────────────────────────────────

def _stable_id(*parts: str) -> str:
    """Produce a deterministic, short ID from ordered parts."""
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _path_matches(target_path: str, candidate_path: str) -> bool:
    """Check if candidate_path is affected by target_path.

    Matches: exact path, prefix (directory), or same module (Python path).
    """
    tn = target_path.replace("\\", "/").rstrip("/")
    cn = candidate_path.replace("\\", "/").rstrip("/")

    if tn == cn:
        return True
    if cn.startswith(tn + "/"):
        return True

    # Python module matching: core/utils/clock.py matches core/utils/clock
    tn_module = tn.replace("/", ".")
    cn_module = cn.replace("/", ".")
    if cn_module.startswith(tn_module):
        return True

    return False


def _classify_level(paths: tuple[str, ...]) -> str:
    """Derive impact level from affected paths."""
    for p in paths:
        for d in _BLOCKING_DIRS:
            if p.startswith(d):
                return "blocking"
    for p in paths:
        for d in _HIGH_DIRS:
            if p.startswith(d):
                return "high"
    for p in paths:
        for d in _MEDIUM_DIRS:
            if p.startswith(d):
                return "medium"
    return "low"


def _classify_impact_type(paths: tuple[str, ...]) -> str:
    for p in paths:
        for d in _HARD_DIRS:
            if p.startswith(d):
                return "HARD"
    return "SOFT"


def _detect_gate_risks(paths: tuple[str, ...]) -> frozenset[str]:
    risks: set[str] = set()
    for p in paths:
        for prefixes, risk_name in _GATE_RISK_MAP.items():
            if any(p.startswith(prefix) for prefix in prefixes):
                risks.add(risk_name)
    return frozenset(risks)


def _derived_confidence(
    edges: tuple[dict[str, Any], ...],
    symbols: tuple[dict[str, Any], ...],
    artifacts: tuple[dict[str, Any], ...],
) -> str:
    data_count = len(edges) + len(symbols) + len(artifacts)
    if data_count == 0:
        return "low"
    inferred = sum(1 for e in edges if e.get("inferred", False))
    if inferred > 0:
        return "medium"
    return "high"


def _build_stop_conditions(
    impact_level: str,
    impact_type: str,
    operation_mode: str,
    gate_risks: frozenset[str],
    target_paths: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    """Derive stop condition strings, then delegate to stop resolver."""
    raw_conditions: list[str] = []

    is_write = operation_mode.lower().startswith("write")

    if is_write:
        raw_conditions.append("S6: write requires impact report and Human-GO")

    if impact_level == "blocking":
        raw_conditions.append(
            f"S5: blocking impact detected on {', '.join(target_paths[:3])}"
        )

    if impact_type == "HARD" and is_write:
        raw_conditions.append(
            "S7: hard-impact change touches runtime/code surface"
        )

    if "governance_touched" in gate_risks and is_write:
        raw_conditions.append("H1: governance paths touched — write requires Human-GO")

    if "secrets_surface_touched" in gate_risks:
        raw_conditions.append("SECRETS_RISK: secrets/tresor paths in scope")

    if "risk_surface_touched" in gate_risks:
        raw_conditions.append(
            "S7: risk service surface touched"
        )

    if "execution_surface_touched" in gate_risks:
        raw_conditions.append(
            "S7: execution surface touched"
        )

    if "lr_surface_touched" in gate_risks:
        raw_conditions.append(
            "S8: live-readiness surface touched — no LR-go claims without SSOT"
        )

    resolved = resolve_stop_conditions(
        stop_conditions=raw_conditions,
        warnings=[],
        operation_mode=operation_mode,
    )

    return tuple(resolved)


# ── Core computation ────────────────────────────────────────────────────────

def _collect_affected_paths(
    target_paths: tuple[str, ...],
    edges: tuple[dict[str, Any], ...],
    symbols: tuple[dict[str, Any], ...],
    artifacts: tuple[dict[str, Any], ...],
) -> frozenset[str]:
    """Collect all paths affected by target_paths via dependency edges."""
    affected: set[str] = set()

    # Direct matches: artifacts whose source_path matches a target
    for art in artifacts:
        source = (art.get("source_path") or art.get("path") or "")
        for tp in target_paths:
            if _path_matches(tp, source):
                affected.add(source)

    # Edges FROM directly affected artifacts
    for edge in edges:
        from_art = edge.get("from_id", "")
        to_art = edge.get("to_id", "")
        for tp in target_paths:
            if _path_matches(tp, from_art) and to_art:
                affected.add(to_art)

    # Symbol import tracing
    for sym in symbols:
        source = sym.get("source_path", "")
        for tp in target_paths:
            if _path_matches(tp, source):
                affected.add(source)

    return frozenset(affected)


def compute_impact(input_data: ImpactRadarInput) -> ImpactReport:
    """Compute an ImpactReport from deterministic input data.

    Args:
        input_data: Immutable ImpactRadarInput with target paths, symbols,
                    dependency edges, code symbols, test cases, and artifacts.

    Returns:
        ImpactReport with impact_level, affected items, gate risks,
        required validation, and stop conditions.

    Deterministic. Same inputs always produce the same outputs.
    """
    target_paths = input_data.target_paths
    target_symbols = input_data.target_symbols
    edges = input_data.dependency_edges
    symbols = input_data.code_symbols
    tests_data = input_data.test_cases
    artifacts = input_data.artifacts
    operation_mode = input_data.operation_mode

    # --- Build target_refs ---
    refs: list[str] = []
    for p in target_paths:
        refs.append(f"path:{p}")
    for s in target_symbols:
        refs.append(f"symbol:{s}")
    if input_data.target_issue:
        refs.append(f"issue:{input_data.target_issue}")
    target_refs = tuple(refs)

    # --- Collect affected paths ---
    affected_paths = _collect_affected_paths(
        target_paths, edges, symbols, artifacts
    )
    all_paths = tuple(sorted(target_paths) + sorted(affected_paths))

    # --- Impact level ---
    impact_level = _classify_level(all_paths) if all_paths else "low"

    # --- Impact type ---
    impact_type = _classify_impact_type(all_paths) if all_paths else "SOFT"

    # --- Affected artifacts ---
    affected_artifacts_out: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    for art in artifacts:
        source = (art.get("source_path") or art.get("path") or "")
        if source in seen_artifacts:
            continue
        if source in affected_paths or any(
            _path_matches(tp, source) for tp in target_paths
        ):
            seen_artifacts.add(source)
            affected_artifacts_out.append(
                {
                    "artifact_id": art.get("artifact_id", ""),
                    "artifact_type": art.get("artifact_type", ""),
                    "source_path": source,
                    "source_hash": art.get("source_hash", ""),
                }
            )

    # --- Affected symbols ---
    affected_symbols_out: list[dict[str, Any]] = []
    seen_syms: set[str] = set()
    for sym in symbols:
        sym_id = sym.get("symbol_id", "")
        source = sym.get("source_path", "")
        if sym_id in seen_syms:
            continue
        if source in affected_paths or any(
            _path_matches(tp, source) for tp in target_paths
        ):
            seen_syms.add(sym_id)
            affected_symbols_out.append(
                {
                    "symbol_id": sym_id,
                    "name": sym.get("name", ""),
                    "qualified_name": sym.get("qualified_name", ""),
                    "symbol_type": sym.get("symbol_type", ""),
                    "source_path": source,
                }
            )

    # --- Affected tests ---
    affected_tests_out: list[dict[str, Any]] = []
    seen_tests: set[str] = set()
    for tc in tests_data:
        test_id = tc.get("test_id", "")
        source = tc.get("source_path", "")
        if test_id in seen_tests:
            continue
        # Tests are affected if their source file matches a target or an
        # affected path, OR if a target_symbol matches a test name
        if source in affected_paths or any(
            _path_matches(tp, source) for tp in target_paths
        ):
            seen_tests.add(test_id)
            affected_tests_out.append(
                {
                    "test_id": test_id,
                    "test_name": tc.get("test_name", tc.get("name", "")),
                    "source_path": source,
                    "test_type": tc.get("test_type", ""),
                }
            )

    # --- Affected docs ---
    affected_docs_out: list[dict[str, Any]] = []
    seen_docs: set[str] = set()
    for art in artifacts:
        source = (art.get("source_path") or art.get("path") or "")
        atype = art.get("artifact_type", "")
        if source in seen_docs:
            continue
        if (
            source.endswith(".md")
            or atype == "documentation"
            or source.startswith("docs/")
            or source.startswith("knowledge/")
        ):
            if source in affected_paths or any(
                _path_matches(tp, source) for tp in target_paths
            ):
                seen_docs.add(source)
                affected_docs_out.append(
                    {
                        "path": source,
                        "title": art.get("title", source),
                        "section_count": 0,
                    }
                )

    # --- Affected decisions ---
    affected_decisions_out: tuple[str, ...] = ()
    dec_refs: list[str] = []
    for art in artifacts:
        source = (art.get("source_path") or art.get("path") or "")
        for dd in _DECISION_DIRS:
            if source.startswith(dd) and (
                source in affected_paths
                or any(_path_matches(tp, source) for tp in target_paths)
            ):
                dec_refs.append(source)
    affected_decisions_out = tuple(sorted(set(dec_refs)))

    # --- Affected evidence ---
    ev_refs: list[str] = []
    for art in artifacts:
        source = (art.get("source_path") or art.get("path") or "")
        for ed in _EVIDENCE_DIRS:
            if source.startswith(ed) and (
                source in affected_paths
                or any(_path_matches(tp, source) for tp in target_paths)
            ):
                ev_refs.append(source)
    affected_evidence_out: tuple[str, ...] = tuple(sorted(set(ev_refs)))

    # --- Affected memory refs ---
    mem_refs: list[str] = []
    for art in artifacts:
        source = (art.get("source_path") or art.get("path") or "")
        for md in _MEMORY_DIRS:
            if source.startswith(md) and (
                source in affected_paths
                or any(_path_matches(tp, source) for tp in target_paths)
            ):
                mem_refs.append(source)
    affected_memory_out: tuple[str, ...] = tuple(sorted(set(mem_refs)))

    # --- Graph paths (dependency chains) ---
    graph_paths_out: tuple[tuple[str, ...], ...] = ()
    gpaths: list[tuple[str, ...]] = []
    for tp in target_paths:
        chain: list[str] = [tp]
        for edge in edges:
            from_art = edge.get("from_id", "")
            to_art = edge.get("to_id", "")
            if _path_matches(tp, from_art) and to_art:
                chain.append(to_art)
        if len(chain) > 1:
            gpaths.append(tuple(chain))
    graph_paths_out = tuple(gpaths)

    # --- Gate risks ---
    gate_risks_out = _detect_gate_risks(all_paths)

    # --- Confidence ---
    confidence = _derived_confidence(edges, symbols, artifacts)

    # --- Required validation ---
    docs_to_review: list[str] = [
        d["path"] for d in affected_docs_out[:5]
    ]
    suggested_tests: list[str] = [
        t["test_name"] or f"tests for {t['source_path']}"
        for t in affected_tests_out[:10]
    ]
    evidence_to_collect: list[str] = list(affected_evidence_out[:5])

    commands_to_consider: list[str] = []
    if affected_tests_out:
        test_paths = sorted({t["source_path"] for t in affected_tests_out})[:3]
        if test_paths:
            commands_to_consider.append(
                f"pytest -v {' '.join(test_paths)}"
            )
    if any(p.startswith("services/") for p in all_paths):
        commands_to_consider.append(
            "mypy core/ services/"
        )

    manual_review_needed = (
        impact_level in ("blocking", "high")
        or impact_type == "HARD"
        or bool(gate_risks_out)
    )

    blocking_preconditions: list[str] = []
    if impact_level == "blocking":
        blocking_preconditions.append(
            "Blocking impact level — confirm change is authorized"
        )
    if "secrets_surface_touched" in gate_risks_out:
        blocking_preconditions.append(
            "Secrets surface touched — verify no credential exposure"
        )

    required_validation: dict[str, Any] = {
        "docs_to_review": docs_to_review,
        "suggested_tests": suggested_tests,
        "evidence_to_collect": evidence_to_collect,
        "commands_to_consider": commands_to_consider,
        "manual_review_needed": manual_review_needed,
        "blocking_preconditions": blocking_preconditions,
    }

    # --- Stop conditions ---
    stop_cond = _build_stop_conditions(
        impact_level=impact_level,
        impact_type=impact_type,
        operation_mode=operation_mode,
        gate_risks=gate_risks_out,
        target_paths=target_paths,
    )

    # --- Deterministic ID ---
    id_parts = list(target_paths) + list(target_symbols)
    if input_data.target_issue:
        id_parts.append(input_data.target_issue)
    id_parts.append(operation_mode)
    impact_id = _stable_id("impact", *id_parts)

    return ImpactReport(
        impact_id=impact_id,
        target_refs=target_refs,
        impact_level=impact_level,
        impact_type=impact_type,
        affected_artifacts=tuple(affected_artifacts_out),
        affected_symbols=tuple(affected_symbols_out),
        affected_tests=tuple(affected_tests_out),
        affected_docs=tuple(affected_docs_out),
        affected_decisions=affected_decisions_out,
        affected_evidence=affected_evidence_out,
        affected_memory_refs_read_only=affected_memory_out,
        graph_paths=graph_paths_out,
        gate_risks=tuple(sorted(gate_risks_out)),
        confidence=confidence,
        required_validation=required_validation,
        stop_conditions=stop_cond,
    )
